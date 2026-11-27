"""Guarded HTTP client with explicit, same-host redirect handling.

``httpx`` automatic redirects are disabled. Every hop is re-authorised by
the egress guard, so a 3xx cannot move the scanner to another host, a
disallowed port, or a plaintext downgrade. Each hop also consumes one unit of
the per-scan request budget and obeys the mode's rate limit.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from urllib.parse import urljoin

import httpx

from .errors import (
    EgressError,
    MethodBlocked,
    RedirectBlocked,
    TooManyRedirects,
    TransportFailure,
)
from .guard import AuthorizedRequest, EgressGuard, Resolver, ValidatedUrl, safe_url_for_repr
from .policy import EgressPolicy
from .transport import PinnedTransport

Sender = Callable[[httpx.Request], Awaitable[httpx.Response]]

_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
_BODY_HEADERS = frozenset(
    {"content-length", "content-type", "transfer-encoding", "content-encoding"}
)
_DEFAULT_USER_AGENT = "Mirsad-Scanner/0.1"


@dataclass(frozen=True, repr=False)
class GuardedResponse:
    """Buffered response returned to the scan engine."""

    status_code: int
    headers: tuple[tuple[str, str], ...]
    content: bytes
    url: str
    history: tuple[str, ...] = ()
    truncated: bool = False

    def header(self, name: str) -> str | None:
        lowered = name.lower()
        for key, value in self.headers:
            if key.lower() == lowered:
                return value
        return None

    @property
    def text(self) -> str:
        return self.content.decode("utf-8", errors="replace")

    def __repr__(self) -> str:
        return (
            f"GuardedResponse(status_code={self.status_code}, "
            f"url={safe_url_for_repr(self.url)!r}, "
            f"redirects={len(self.history)}, truncated={self.truncated})"
        )


class GuardedClient:
    """HTTP client that refuses to leave the verified domain."""

    def __init__(
        self,
        guard: EgressGuard,
        sender: Sender,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._guard = guard
        self._sender = sender
        self._client = client

    @classmethod
    def from_policy(
        cls,
        policy: EgressPolicy,
        *,
        resolver: Resolver | None = None,
    ) -> GuardedClient:
        guard = EgressGuard(policy, resolver=resolver)
        transport = PinnedTransport(guard, max_response_bytes=policy.max_response_bytes)
        client = httpx.AsyncClient(
            transport=transport,
            trust_env=False,
            timeout=httpx.Timeout(policy.request_timeout_seconds),
            follow_redirects=False,
            headers={"User-Agent": _DEFAULT_USER_AGENT},
        )

        async def sender(request: httpx.Request) -> httpx.Response:
            try:
                return await client.send(request, stream=False)
            except EgressError:
                raise
            except httpx.HTTPError as exc:
                raise TransportFailure("Egress transport failed.") from exc

        return cls(guard, sender, client=client)

    @property
    def guard(self) -> EgressGuard:
        return self._guard

    async def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        content: bytes | str | None = None,
    ) -> GuardedResponse:
        current_url = url
        if not isinstance(method, str):
            raise MethodBlocked("HTTP method must be a string.")
        current_method = method.upper()
        current_headers = dict(headers or {})
        current_content = content
        history: list[str] = []

        while True:
            authorized = await self._guard.authorize(current_method, current_url)
            request = self._build_request(authorized, current_headers, current_content)
            response = await self._sender(request)

            if response.status_code == 305:
                raise RedirectBlocked("Use-proxy redirects are not allowed.")

            if response.status_code not in _REDIRECT_STATUSES:
                return _to_guarded_response(response, authorized.url, history)

            location = response.headers.get("location")
            if not location:
                return _to_guarded_response(response, authorized.url, history)

            if len(history) >= self._guard.policy.max_redirects:
                raise TooManyRedirects("Redirect chain exceeded the configured maximum.")

            next_url = urljoin(authorized.url.url, location)
            try:
                next_parsed = self._guard.parse_url(next_url)
            except EgressError as exc:
                raise RedirectBlocked("Redirect target is not the verified host.") from exc

            if authorized.url.scheme == "https" and next_parsed.scheme == "http":
                raise RedirectBlocked("HTTPS-to-HTTP redirect downgrades are not allowed.")

            history.append(authorized.url.url)
            current_method, current_content, current_headers = _redirect_follow_up(
                response.status_code,
                current_method,
                current_content,
                current_headers,
            )
            current_url = next_parsed.url

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()

    async def __aenter__(self) -> GuardedClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()

    def _build_request(
        self,
        authorized: AuthorizedRequest,
        headers: Mapping[str, str],
        content: bytes | str | None,
    ) -> httpx.Request:
        request = httpx.Request(
            authorized.method,
            authorized.url.url,
            headers=dict(headers),
            content=content,
        )
        if "user-agent" not in request.headers:
            request.headers["user-agent"] = _DEFAULT_USER_AGENT
        if "accept-encoding" not in request.headers:
            # Avoid compression bombs; the response cap applies to bytes on
            # the wire, not to an unbounded decompressed stream.
            request.headers["accept-encoding"] = "identity"

        # The connection is pinned to a vetted IP, but a caller-supplied Host
        # header must not be allowed to select a different virtual host.
        default_port = 80 if authorized.url.scheme == "http" else 443
        request.headers["host"] = (
            authorized.url.host
            if authorized.url.port == default_port
            else f"{authorized.url.host}:{authorized.url.port}"
        )
        return request


def _redirect_follow_up(
    status_code: int,
    method: str,
    content: bytes | str | None,
    headers: Mapping[str, str],
) -> tuple[str, bytes | str | None, dict[str, str]]:
    """Return the method, body, and headers for the next redirect hop."""

    if status_code == 303 and method != "HEAD":
        return "GET", None, _without_body_headers(headers)

    if status_code in {301, 302} and method == "POST":
        return "GET", None, _without_body_headers(headers)

    return method, content, dict(headers)


def _without_body_headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {
        key: value
        for key, value in headers.items()
        if key.lower() not in _BODY_HEADERS
    }


def _to_guarded_response(
    response: httpx.Response,
    url: ValidatedUrl,
    history: list[str],
) -> GuardedResponse:
    return GuardedResponse(
        status_code=response.status_code,
        headers=tuple(response.headers.multi_items()),
        content=response.content,
        url=url.url,
        history=tuple(history),
        truncated=bool(response.extensions.get("mirsad_truncated", False)),
    )
