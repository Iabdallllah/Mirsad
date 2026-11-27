"""The code-level egress guard (plan.md §4.2, §14.1).

Every outbound scan request must obtain an ``AuthorizedRequest`` here before
it reaches the transport. Validation happens twice: once before the request
is scheduled and again inside the pinned TCP backend at connect time. The
second check is what closes the DNS-rebinding window — the backend resolves
the name, validates *every* answer, and connects to the vetted IP while TLS
keeps the original hostname for SNI and certificate validation.
"""

from __future__ import annotations

import asyncio
import re
import socket
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from urllib.parse import urlsplit

from .addresses import assert_public_ip, normalize_hostname
from .errors import (
    DnsResolutionFailed,
    EgressError,
    HostNotAllowed,
    InvalidHost,
    IpLiteralBlocked,
    MethodBlocked,
    PortBlocked,
    RequestBudgetExhausted,
    SchemeBlocked,
    UrlInvalid,
    UrlTooLong,
    UserInfoBlocked,
)
from .policy import ALLOWED_PORTS, DEFAULT_PORTS, EgressPolicy

MAX_URL_LENGTH = 8192
_ENCODED_CONTROL = re.compile(r"%(?:00|0a|0d|5c)", re.IGNORECASE)

Resolver = Callable[[str, int], Awaitable[Sequence[str]]]
Clock = Callable[[], float]
Sleeper = Callable[[float], Awaitable[None]]


@dataclass(frozen=True)
class ValidatedUrl:
    """Canonical URL that passed scheme, host, port, and charset checks."""

    scheme: str
    host: str
    port: int
    path: str
    query: str

    @property
    def url(self) -> str:
        default_port = DEFAULT_PORTS[self.scheme]
        netloc = self.host if self.port == default_port else f"{self.host}:{self.port}"
        query = f"?{self.query}" if self.query else ""
        return f"{self.scheme}://{netloc}{self.path}{query}"

    def __repr__(self) -> str:
        return f"ValidatedUrl(scheme={self.scheme!r}, host={self.host!r}, port={self.port})"


@dataclass(frozen=True)
class AuthorizedRequest:
    """A request that has passed policy, URL, DNS, and rate-limit checks."""

    method: str
    url: ValidatedUrl
    addresses: tuple[str, ...]


class EgressGuard:
    """Validates destinations and enforces per-mode safety limits."""

    def __init__(
        self,
        policy: EgressPolicy,
        *,
        resolver: Resolver | None = None,
        clock: Clock = time.monotonic,
        sleeper: Sleeper = asyncio.sleep,
    ) -> None:
        self._policy = policy
        self._resolver = resolver or _default_resolver
        self._clock = clock
        self._sleeper = sleeper
        self._lock = asyncio.Lock()
        self._last_started: float | None = None
        self._requests_made = 0

    @property
    def policy(self) -> EgressPolicy:
        return self._policy

    @property
    def requests_made(self) -> int:
        return self._requests_made

    @property
    def remaining_requests(self) -> int:
        return max(self._policy.effective_max_requests - self._requests_made, 0)

    async def authorize(self, method: str, url: str) -> AuthorizedRequest:
        """Validate one request hop and reserve budget/rate capacity."""

        if not isinstance(method, str):
            raise MethodBlocked("HTTP method must be a string.")

        normalized_method = method.upper()
        if normalized_method not in self._policy.allowed_methods:
            raise MethodBlocked("HTTP method is not allowed in this scan mode.")

        parsed = self.parse_url(url)
        addresses = await self.assert_connect_target(parsed.host, parsed.port)
        await self._acquire_slot()
        return AuthorizedRequest(method=normalized_method, url=parsed, addresses=addresses)

    def parse_url(self, url: str) -> ValidatedUrl:
        """Validate and canonicalise a URL without performing DNS work."""

        if not isinstance(url, str) or not url:
            raise UrlInvalid("URL is empty.")

        if len(url) > MAX_URL_LENGTH:
            raise UrlTooLong("URL exceeds the maximum length.")

        if url != url.strip() or any(
            ord(char) < 32 or 127 <= ord(char) <= 159 or char.isspace() for char in url
        ):
            raise UrlInvalid("URL contains whitespace or control characters.")

        if "\\" in url:
            raise UrlInvalid("URL contains a backslash.")

        if _ENCODED_CONTROL.search(url):
            raise UrlInvalid("URL contains an encoded control character.")

        try:
            parsed = urlsplit(url)
        except ValueError as exc:
            raise UrlInvalid("URL could not be parsed.") from exc

        scheme = parsed.scheme.lower()
        if scheme not in DEFAULT_PORTS:
            raise SchemeBlocked("Only http and https URLs are allowed.")

        netloc = parsed.netloc
        if not netloc:
            raise UrlInvalid("URL has no host.")
        if "@" in netloc:
            raise UserInfoBlocked("URL userinfo is not allowed.")
        if "%" in netloc or "\\" in netloc:
            raise UrlInvalid("URL authority contains an ambiguous character.")

        try:
            hostname = parsed.hostname
            explicit_port = parsed.port
        except ValueError as exc:
            raise UrlInvalid("URL host or port is malformed.") from exc

        if hostname is None:
            raise UrlInvalid("URL has no host.")

        host = normalize_hostname(hostname)
        if host != self._policy.target.domain:
            raise HostNotAllowed("Host is not the verified target domain.")

        port = DEFAULT_PORTS[scheme] if explicit_port is None else explicit_port
        if port not in ALLOWED_PORTS:
            raise PortBlocked("Only ports 80 and 443 are allowed.")

        path = parsed.path or "/"
        query = parsed.query

        return ValidatedUrl(scheme=scheme, host=host, port=port, path=path, query=query)

    async def assert_connect_target(self, host: str, port: int) -> tuple[str, ...]:
        """Validate a host/port pair and return the vetted resolved addresses."""

        try:
            normalized_host = normalize_hostname(host)
        except (InvalidHost, IpLiteralBlocked) as exc:
            raise HostNotAllowed("Connect target is not a valid DNS name.") from exc

        if normalized_host != self._policy.target.domain:
            raise HostNotAllowed("Connect target is not the verified target domain.")

        if not isinstance(port, int) or port not in ALLOWED_PORTS:
            raise PortBlocked("Only ports 80 and 443 are allowed.")

        return await self._resolve_and_verify(normalized_host, port)

    async def _resolve_and_verify(self, host: str, port: int) -> tuple[str, ...]:
        try:
            answers = await self._resolver(host, port)
        except EgressError:
            raise
        except Exception as exc:
            raise DnsResolutionFailed("DNS resolution failed.") from exc

        addresses: list[str] = []
        for answer in answers:
            ip = assert_public_ip(answer)
            normalized = str(ip)
            if normalized not in addresses:
                addresses.append(normalized)

        if not addresses:
            raise DnsResolutionFailed("DNS returned no addresses.")

        return tuple(addresses)

    async def _acquire_slot(self) -> None:
        async with self._lock:
            if self._requests_made >= self._policy.effective_max_requests:
                raise RequestBudgetExhausted("Per-scan request budget is exhausted.")

            now = self._clock()
            if self._last_started is not None:
                wait_seconds = self._policy.minimum_interval_seconds - (
                    now - self._last_started
                )
                if wait_seconds > 0:
                    await self._sleeper(wait_seconds)
                    now = self._clock()

            self._requests_made += 1
            self._last_started = now

    def __repr__(self) -> str:
        return (
            f"EgressGuard(target={self._policy.target.domain!r}, "
            f"mode={self._policy.mode.value!r}, requests={self._requests_made})"
        )


async def _default_resolver(host: str, port: int) -> Sequence[str]:
    """Resolve all A/AAAA answers on a worker thread (fail closed)."""

    infos = await asyncio.to_thread(
        socket.getaddrinfo,
        host,
        port,
        0,
        socket.SOCK_STREAM,
    )
    addresses: list[str] = []
    for info in infos:
        address = info[4][0]
        if isinstance(address, str):
            addresses.append(address)
    return addresses


def safe_url_for_repr(url: str) -> str:
    """Return a URL suitable for logs: no userinfo and no query string."""

    try:
        parsed = urlsplit(url)
        host = parsed.hostname or ""
        if ":" in host:
            host = f"[{host}]"
        path = parsed.path or "/"
        path = "".join(
            char if 32 <= ord(char) < 127 else "?" for char in path
        )
        if len(path) > 200:
            path = f"{path[:200]}..."
        return f"{parsed.scheme}://{host}{path}"
    except ValueError:
        return "<invalid-url>"
