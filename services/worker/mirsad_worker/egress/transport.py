"""Pinned HTTP transport for the egress guard (plan.md §4.2, §14.1).

The custom network backend resolves the verified hostname at TCP-connect
time, validates every answer, and connects to the vetted IP. TLS still uses
the original hostname for SNI and certificate verification, so pinning does
not disable certificate checks. A DNS answer that changes from public to
private between scheduling and connect therefore fails before a socket is
opened.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

import httpcore
import httpx

from .errors import (
    DnsResolutionFailed,
    EgressError,
    MethodBlocked,
    TransportFailure,
    UnixSocketBlocked,
)
from .guard import EgressGuard


class AsyncPool(Protocol):
    """Subset of ``httpcore.AsyncConnectionPool`` used by the transport."""

    async def handle_async_request(self, request: httpcore.Request) -> httpcore.Response: ...

    async def aclose(self) -> None: ...


class GuardedNetworkBackend(httpcore.AsyncNetworkBackend):
    """Validate and pin every TCP destination before the socket is opened."""

    def __init__(
        self,
        guard: EgressGuard,
        *,
        inner: httpcore.AsyncNetworkBackend | None = None,
    ) -> None:
        self._guard = guard
        self._inner = inner or httpcore.AnyIOBackend()

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[httpcore.SOCKET_OPTION] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        addresses = await self._guard.assert_connect_target(host, port)
        last_error: Exception | None = None

        for address in addresses:
            try:
                return await self._inner.connect_tcp(
                    address,
                    port,
                    timeout,
                    local_address,
                    socket_options,
                )
            except EgressError:
                raise
            except Exception as exc:  # Try the next vetted address, if any.
                last_error = exc

        if last_error is not None:
            raise last_error
        raise DnsResolutionFailed("No vetted address was available to connect.")

    async def connect_unix_socket(
        self,
        path: str,
        timeout: float | None = None,
        socket_options: Iterable[httpcore.SOCKET_OPTION] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        raise UnixSocketBlocked("Unix-domain sockets are not valid scan destinations.")

    async def sleep(self, seconds: float) -> None:
        await self._inner.sleep(seconds)


class PinnedTransport(httpx.AsyncBaseTransport):
    """Buffered httpx transport backed by a DNS-pinned httpcore pool."""

    def __init__(
        self,
        guard: EgressGuard,
        *,
        max_response_bytes: int,
        pool: AsyncPool | None = None,
    ) -> None:
        self._guard = guard
        self._max_response_bytes = max_response_bytes
        self._pool: AsyncPool = pool or httpcore.AsyncConnectionPool(
            ssl_context=httpx.create_ssl_context(trust_env=False),
            network_backend=GuardedNetworkBackend(guard),
            max_connections=10,
            max_keepalive_connections=5,
            keepalive_expiry=30.0,
            http1=True,
            http2=False,
            retries=0,
        )

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        # Defence in depth: the client already parsed the URL and method, but
        # the transport refuses anything that is not the verified host or an
        # allowed method.
        validated = self._guard.parse_url(str(request.url))
        if request.method.upper() not in self._guard.policy.allowed_methods:
            raise MethodBlocked("HTTP method is not allowed in this scan mode.")

        raw_host = request.url.raw_host
        if raw_host is None:
            raise TransportFailure("Request URL has no host.")

        if not isinstance(request.stream, httpx.AsyncByteStream):
            raise TransportFailure("Request stream is not asynchronous.")

        # Never let a caller-supplied Host header select a different virtual
        # host on the vetted IP (the client already normalises this, but the
        # transport is also usable directly).
        default_port = 80 if validated.scheme == "http" else 443
        host_header = (
            validated.host
            if validated.port == default_port
            else f"{validated.host}:{validated.port}"
        )
        raw_headers = [
            (name, value)
            for name, value in request.headers.raw
            if name.lower() != b"host"
        ]
        raw_headers.append((b"host", host_header.encode("ascii")))

        core_request = httpcore.Request(
            method=request.method,
            url=httpcore.URL(
                scheme=request.url.raw_scheme,
                host=raw_host,
                port=request.url.port,
                target=request.url.raw_path,
            ),
            headers=raw_headers,
            content=request.stream,
            extensions=request.extensions,
        )

        try:
            core_response = await self._pool.handle_async_request(core_request)
        except EgressError:
            raise
        except (
            httpcore.NetworkError,
            httpcore.TimeoutException,
            httpcore.ProtocolError,
            httpcore.UnsupportedProtocol,
            httpcore.ProxyError,
            httpcore.ConnectionNotAvailable,
        ) as exc:
            raise TransportFailure("Egress transport failed.") from exc

        chunks: list[bytes] = []
        total = 0
        truncated = False

        try:
            async for chunk in core_response.aiter_stream():
                remaining = self._max_response_bytes - total
                if len(chunk) > remaining:
                    if remaining > 0:
                        chunks.append(chunk[:remaining])
                        total += remaining
                    truncated = True
                    break
                chunks.append(chunk)
                total += len(chunk)
        except EgressError:
            raise
        except (
            httpcore.NetworkError,
            httpcore.TimeoutException,
            httpcore.ProtocolError,
        ) as exc:
            await core_response.aclose()
            raise TransportFailure(
                "Egress transport failed while reading the response."
            ) from exc

        if truncated:
            await core_response.aclose()

        extensions = dict(core_response.extensions)
        extensions["mirsad_truncated"] = truncated

        return httpx.Response(
            status_code=core_response.status,
            headers=core_response.headers,
            content=b"".join(chunks),
            extensions=extensions,
            request=request,
        )

    async def aclose(self) -> None:
        await self._pool.aclose()
