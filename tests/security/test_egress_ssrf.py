"""SSRF/egress bypass suite: every attempt must fail closed (plan.md §14.1).

These tests exercise the guard as an attacker would: foreign hosts, IP
literals in every common encoding, private DNS answers, DNS rebinding between
scheduling and connect, cross-domain redirects, method smuggling, and budget
exhaustion. They use fake resolvers/senders, so no real network traffic leaves
the test process.
"""

from __future__ import annotations

import ssl
from collections.abc import AsyncIterator, Awaitable, Callable, Iterable, Sequence
from typing import Any

import httpcore
import httpx
import pytest

from mirsad_worker.egress import (
    DnsResolutionFailed,
    EgressError,
    EgressGuard,
    EgressPolicy,
    GuardedClient,
    GuardedResponse,
    HostNotAllowed,
    IpLiteralBlocked,
    MethodBlocked,
    ModeNotAllowed,
    PinnedTransport,
    PortBlocked,
    PrivateAddressBlocked,
    RedirectBlocked,
    RequestBudgetExhausted,
    ScanMode,
    SchemeBlocked,
    TargetEnvironment,
    TooManyRedirects,
    TransportFailure,
    UnixSocketBlocked,
    UrlInvalid,
    UserInfoBlocked,
    VerifiedTarget,
)
from mirsad_worker.egress.guard import safe_url_for_repr
from mirsad_worker.egress.transport import GuardedNetworkBackend

DOMAIN = "app.example.com"
PUBLIC = "93.184.216.34"
PUBLIC_2 = "1.1.1.1"

Resolver = Callable[[str, int], Awaitable[Sequence[str]]]
Sender = Callable[[httpx.Request], Awaitable[httpx.Response]]


def make_target(
    *,
    domain: str = DOMAIN,
    environment: TargetEnvironment = TargetEnvironment.STAGING,
) -> VerifiedTarget:
    return VerifiedTarget(
        domain=domain,
        environment=environment,
        ownership_verified=True,
        consent_granted=True,
    )


def make_policy(
    *,
    mode: ScanMode = ScanMode.SAFE,
    environment: TargetEnvironment = TargetEnvironment.STAGING,
    **kwargs: Any,
) -> EgressPolicy:
    return EgressPolicy(
        target=make_target(environment=environment),
        mode=mode,
        **kwargs,
    )


def static_resolver(*addresses: str) -> Resolver:
    async def resolve(host: str, port: int) -> Sequence[str]:
        assert host == DOMAIN
        assert port in {80, 443}
        return addresses

    return resolve


def permissive_resolver(*addresses: str) -> Resolver:
    """Return a public answer for any host, so host checks are what block."""

    async def resolve(host: str, port: int) -> Sequence[str]:
        return addresses or (PUBLIC,)

    return resolve


class ExplodingResolver:
    def __init__(self) -> None:
        self.called = False

    async def __call__(self, host: str, port: int) -> Sequence[str]:
        self.called = True
        raise AssertionError("resolver must not be called")


class RecordingStream(httpcore.AsyncNetworkStream):
    def __init__(self) -> None:
        self.closed = False

    async def read(self, max_bytes: int, timeout: float | None = None) -> bytes:
        return b""

    async def write(self, buffer: bytes, timeout: float | None = None) -> None:
        return None

    async def aclose(self) -> None:
        self.closed = True

    async def start_tls(
        self,
        ssl_context: ssl.SSLContext,
        server_hostname: str | None = None,
        timeout: float | None = None,
    ) -> httpcore.AsyncNetworkStream:
        return self


class FakeInnerBackend(httpcore.AsyncNetworkBackend):
    def __init__(self, failures: int = 0) -> None:
        self.calls: list[tuple[str, int]] = []
        self.failures = failures

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[httpcore.SOCKET_OPTION] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        self.calls.append((host, port))
        if self.failures:
            self.failures -= 1
            raise OSError("connect failed")
        return RecordingStream()

    async def connect_unix_socket(
        self,
        path: str,
        timeout: float | None = None,
        socket_options: Iterable[httpcore.SOCKET_OPTION] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        raise AssertionError("unix socket must not be used")

    async def sleep(self, seconds: float) -> None:
        return None


class ChunkStream:
    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = chunks
        self.closed = False

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for chunk in self.chunks:
            yield chunk

    async def aclose(self) -> None:
        self.closed = True


class FakePool:
    def __init__(self, response: httpcore.Response) -> None:
        self.response = response
        self.requests: list[httpcore.Request] = []
        self.closed = False

    async def handle_async_request(self, request: httpcore.Request) -> httpcore.Response:
        self.requests.append(request)
        return self.response

    async def aclose(self) -> None:
        self.closed = True


def scripted_sender(
    script: list[tuple[int, dict[str, str], bytes]],
) -> tuple[Sender, list[httpx.Request]]:
    requests: list[httpx.Request] = []

    async def sender(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        status, headers, body = script.pop(0)
        return httpx.Response(status, headers=headers, content=body, request=request)

    return sender, requests


def make_client(
    *,
    policy: EgressPolicy | None = None,
    resolver: Resolver | None = None,
    sender: Sender | None = None,
    clock: Callable[[], float] | None = None,
    sleeper: Callable[[float], Awaitable[None]] | None = None,
) -> tuple[GuardedClient, EgressGuard]:
    resolved = policy or make_policy()
    guard_kwargs: dict[str, Any] = {}
    if clock is not None:
        guard_kwargs["clock"] = clock
    if sleeper is not None:
        guard_kwargs["sleeper"] = sleeper

    guard = EgressGuard(
        resolved,
        resolver=resolver or permissive_resolver(),
        **guard_kwargs,
    )

    async def default_sender(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"ok", request=request)

    return GuardedClient(guard, sender or default_sender), guard


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("url", "error"),
    [
        ("https://evil.com/", HostNotAllowed),
        ("https://app.example.com.evil.com/", HostNotAllowed),
        ("https://evil-app.example.com/", HostNotAllowed),
        ("https://app.example.com@evil.com/", UserInfoBlocked),
        ("https://app.example.com%2eevil.com/", UrlInvalid),
        ("https://app.example.com\\@evil.com/", UrlInvalid),
        ("https://app.example.com:8443/", PortBlocked),
        ("http://app.example.com:22/", PortBlocked),
        ("https://app.example.com:+443/", UrlInvalid),
        ("ftp://app.example.com/", SchemeBlocked),
        ("file:///etc/passwd", SchemeBlocked),
        ("gopher://app.example.com/", SchemeBlocked),
        ("ws://app.example.com/", SchemeBlocked),
        ("//app.example.com/", SchemeBlocked),
        ("https:///path", UrlInvalid),
        ("https://app.example.com/%0d%0aX-Injected:%20yes", UrlInvalid),
        ("https://app.example.com/%00", UrlInvalid),
        ("https://app.example.com/%5c", UrlInvalid),
        ("https://app.example.com/ path", UrlInvalid),
        ("https://app.example.com/\n", UrlInvalid),
        ("https://app.example.com/\x9f", UrlInvalid),
    ],
)
async def test_foreign_or_malformed_urls_are_blocked(
    url: str,
    error: type[EgressError],
) -> None:
    guard = EgressGuard(make_policy(), resolver=permissive_resolver())
    with pytest.raises(error):
        await guard.authorize("GET", url)


@pytest.mark.asyncio
async def test_foreign_host_is_rejected_before_dns() -> None:
    resolver = ExplodingResolver()
    guard = EgressGuard(make_policy(), resolver=resolver)

    with pytest.raises(HostNotAllowed):
        await guard.authorize("GET", "https://evil.com/")

    assert resolver.called is False


@pytest.mark.asyncio
async def test_disallowed_port_is_rejected_before_dns() -> None:
    resolver = ExplodingResolver()
    guard = EgressGuard(make_policy(), resolver=resolver)

    with pytest.raises(PortBlocked):
        await guard.authorize("GET", f"https://{DOMAIN}:8443/")

    assert resolver.called is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://127.1/",
        "http://2130706433/",
        "http://0x7f000001/",
        "http://017700000001/",
        "http://0/",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]/",
        "http://[::ffff:127.0.0.1]/",
        "http://[0:0:0:0:0:0:0:1]/",
        "http://[fd00:ec2::254]/",
    ],
)
async def test_ip_literal_encodings_are_blocked(url: str) -> None:
    guard = EgressGuard(make_policy(), resolver=static_resolver(PUBLIC))
    with pytest.raises(IpLiteralBlocked):
        await guard.authorize("GET", url)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "address",
    [
        "0.0.0.0",
        "10.0.0.1",
        "100.64.0.1",
        "127.0.0.1",
        "169.254.169.254",
        "172.16.0.1",
        "192.0.0.1",
        "192.0.2.1",
        "192.168.1.1",
        "198.18.0.1",
        "198.51.100.1",
        "203.0.113.1",
        "224.0.0.1",
        "240.0.0.1",
        "255.255.255.255",
        "::",
        "::1",
        "::ffff:127.0.0.1",
        "64:ff9b::7f00:1",
        "100::1",
        "2001::1",
        "2001:db8::1",
        "2002:7f00:1::",
        "fc00::1",
        "fd00:ec2::254",
        "fe80::1",
        "ff02::1",
    ],
)
async def test_private_dns_answers_are_blocked(address: str) -> None:
    guard = EgressGuard(make_policy(), resolver=static_resolver(address))
    with pytest.raises(PrivateAddressBlocked):
        await guard.authorize("GET", f"https://{DOMAIN}/")


@pytest.mark.asyncio
async def test_one_private_answer_blocks_a_mixed_response() -> None:
    guard = EgressGuard(
        make_policy(),
        resolver=static_resolver(PUBLIC, "127.0.0.1"),
    )
    with pytest.raises(PrivateAddressBlocked):
        await guard.authorize("GET", f"https://{DOMAIN}/")


@pytest.mark.asyncio
async def test_public_dns_answers_are_allowed_and_deduplicated() -> None:
    guard = EgressGuard(
        make_policy(),
        resolver=static_resolver(PUBLIC, PUBLIC, "2606:4700:4700::1111"),
    )
    authorized = await guard.authorize("GET", f"https://{DOMAIN}/")
    assert authorized.addresses == (PUBLIC, "2606:4700:4700::1111")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "resolver",
    [
        static_resolver(),
        static_resolver("not-an-ip"),
        static_resolver("fe80::1%eth0"),
        static_resolver("1.2.3.999"),
    ],
)
async def test_unusable_dns_answers_fail_closed(resolver: Resolver) -> None:
    guard = EgressGuard(make_policy(), resolver=resolver)
    with pytest.raises(DnsResolutionFailed):
        await guard.authorize("GET", f"https://{DOMAIN}/")


@pytest.mark.asyncio
async def test_dns_exception_fails_closed() -> None:
    async def broken(host: str, port: int) -> Sequence[str]:
        raise OSError("resolver down")

    guard = EgressGuard(make_policy(), resolver=broken)
    with pytest.raises(DnsResolutionFailed):
        await guard.authorize("GET", f"https://{DOMAIN}/")


@pytest.mark.asyncio
async def test_dns_rebinding_is_blocked_at_connect_time() -> None:
    """The second resolution (inside the backend) sees a private answer."""

    calls = 0

    async def rebinding(host: str, port: int) -> Sequence[str]:
        nonlocal calls
        calls += 1
        return (PUBLIC,) if calls == 1 else ("127.0.0.1",)

    guard = EgressGuard(make_policy(), resolver=rebinding)
    await guard.authorize("GET", f"https://{DOMAIN}/")

    inner = FakeInnerBackend()
    backend = GuardedNetworkBackend(guard, inner=inner)
    with pytest.raises(PrivateAddressBlocked):
        await backend.connect_tcp(DOMAIN, 443)

    assert inner.calls == []
    assert calls == 2


@pytest.mark.asyncio
async def test_backend_connects_to_the_vetted_ip_not_the_hostname() -> None:
    guard = EgressGuard(make_policy(), resolver=static_resolver(PUBLIC))
    inner = FakeInnerBackend()
    backend = GuardedNetworkBackend(guard, inner=inner)

    await backend.connect_tcp(DOMAIN, 443)

    assert inner.calls == [(PUBLIC, 443)]


@pytest.mark.asyncio
async def test_backend_fails_over_across_vetted_addresses() -> None:
    guard = EgressGuard(make_policy(), resolver=static_resolver(PUBLIC, PUBLIC_2))
    inner = FakeInnerBackend(failures=1)
    backend = GuardedNetworkBackend(guard, inner=inner)

    await backend.connect_tcp(DOMAIN, 443)

    assert inner.calls == [(PUBLIC, 443), (PUBLIC_2, 443)]


@pytest.mark.asyncio
async def test_backend_rejects_foreign_host_before_connecting() -> None:
    guard = EgressGuard(make_policy(), resolver=permissive_resolver())
    inner = FakeInnerBackend()
    backend = GuardedNetworkBackend(guard, inner=inner)

    with pytest.raises(HostNotAllowed):
        await backend.connect_tcp("evil.com", 443)

    assert inner.calls == []


@pytest.mark.asyncio
async def test_backend_rejects_non_standard_ports() -> None:
    guard = EgressGuard(make_policy(), resolver=static_resolver(PUBLIC))
    inner = FakeInnerBackend()
    backend = GuardedNetworkBackend(guard, inner=inner)

    with pytest.raises(PortBlocked):
        await backend.connect_tcp(DOMAIN, 8443)

    assert inner.calls == []


@pytest.mark.asyncio
async def test_unix_sockets_are_never_allowed() -> None:
    guard = EgressGuard(make_policy(), resolver=static_resolver(PUBLIC))
    backend = GuardedNetworkBackend(guard, inner=FakeInnerBackend())

    with pytest.raises(UnixSocketBlocked):
        await backend.connect_unix_socket("/var/run/docker.sock")


@pytest.mark.asyncio
async def test_safe_mode_blocks_mutating_methods_before_dns() -> None:
    resolver = ExplodingResolver()
    guard = EgressGuard(make_policy(), resolver=resolver)

    for method in ("POST", "PUT", "PATCH", "DELETE", "TRACE", "CONNECT"):
        with pytest.raises(MethodBlocked):
            await guard.authorize(method, f"https://{DOMAIN}/")

    assert resolver.called is False


@pytest.mark.asyncio
async def test_deep_mode_blocks_delete_and_trace() -> None:
    guard = EgressGuard(
        make_policy(mode=ScanMode.DEEP),
        resolver=static_resolver(PUBLIC),
    )

    for method in ("DELETE", "TRACE", "CONNECT"):
        with pytest.raises(MethodBlocked):
            await guard.authorize(method, f"https://{DOMAIN}/")


@pytest.mark.asyncio
async def test_deep_mode_is_refused_on_production_targets() -> None:
    with pytest.raises(ModeNotAllowed):
        make_policy(
            mode=ScanMode.DEEP,
            environment=TargetEnvironment.PRODUCTION,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "location",
    [
        "https://evil.com/",
        "https://app.example.com.evil.com/",
        "https://evil-app.example.com/",
        "https://api.app.example.com/",
        "http://169.254.169.254/latest/meta-data/",
        "https://app.example.com:8443/",
        "http://app.example.com/",
        "//evil.com/",
        "javascript:alert(1)",
        "data:text/html,hello",
    ],
)
async def test_cross_domain_redirects_are_blocked(location: str) -> None:
    client, _ = make_client(sender=scripted_sender([(302, {"Location": location}, b"")])[0])

    with pytest.raises(RedirectBlocked):
        await client.request("GET", f"https://{DOMAIN}/start")


@pytest.mark.asyncio
async def test_same_host_redirect_is_followed_and_counted() -> None:
    sender, requests = scripted_sender(
        [
            (302, {"Location": "/next?token=secret"}, b""),
            (200, {"Content-Type": "text/plain"}, b"ok"),
        ]
    )
    client, guard = make_client(sender=sender)

    response = await client.request("GET", f"https://{DOMAIN}/start")

    assert response.status_code == 200
    assert response.content == b"ok"
    assert response.history == (f"https://{DOMAIN}/start",)
    assert response.url == f"https://{DOMAIN}/next?token=secret"
    assert len(requests) == 2
    assert guard.requests_made == 2
    assert guard.remaining_requests == 298


@pytest.mark.asyncio
async def test_redirect_without_location_is_returned_to_the_caller() -> None:
    client, _ = make_client(sender=scripted_sender([(302, {}, b"")])[0])
    response = await client.request("GET", f"https://{DOMAIN}/")
    assert response.status_code == 302


@pytest.mark.asyncio
async def test_redirect_chain_limit_is_enforced() -> None:
    sender, requests = scripted_sender(
        [
            (302, {"Location": "/one"}, b""),
            (302, {"Location": "/two"}, b""),
            (200, {}, b"never"),
        ]
    )
    client, _ = make_client(policy=make_policy(max_redirects=1), sender=sender)

    with pytest.raises(TooManyRedirects):
        await client.request("GET", f"https://{DOMAIN}/")

    assert len(requests) == 2


@pytest.mark.asyncio
async def test_redirects_consume_the_request_budget() -> None:
    sender, requests = scripted_sender([(302, {"Location": "/next"}, b"")])
    client, _ = make_client(policy=make_policy(max_requests=1), sender=sender)

    with pytest.raises(RequestBudgetExhausted):
        await client.request("GET", f"https://{DOMAIN}/")

    assert len(requests) == 1


@pytest.mark.asyncio
async def test_use_proxy_redirect_is_blocked() -> None:
    client, _ = make_client(sender=scripted_sender([(305, {}, b"")])[0])
    with pytest.raises(RedirectBlocked):
        await client.request("GET", f"https://{DOMAIN}/")


@pytest.mark.asyncio
async def test_303_redirect_converts_post_to_get_and_drops_the_body() -> None:
    sender, requests = scripted_sender(
        [
            (303, {"Location": "/done"}, b""),
            (200, {}, b"ok"),
        ]
    )
    client, _ = make_client(policy=make_policy(mode=ScanMode.DEEP), sender=sender)

    await client.request(
        "POST",
        f"https://{DOMAIN}/login",
        content=b"password=secret",
    )

    assert [request.method for request in requests] == ["POST", "GET"]
    assert requests[0].content == b"password=secret"
    assert requests[1].content == b""


@pytest.mark.asyncio
async def test_307_redirect_preserves_method_and_body() -> None:
    sender, requests = scripted_sender(
        [
            (307, {"Location": "/retry"}, b""),
            (200, {}, b"ok"),
        ]
    )
    client, _ = make_client(policy=make_policy(mode=ScanMode.DEEP), sender=sender)

    await client.request("POST", f"https://{DOMAIN}/login", content=b"password=secret")

    assert [request.method for request in requests] == ["POST", "POST"]
    assert requests[1].content == b"password=secret"


@pytest.mark.asyncio
async def test_caller_cannot_override_the_host_header() -> None:
    sender, requests = scripted_sender([(200, {}, b"ok")])
    client, _ = make_client(sender=sender)

    await client.request("GET", f"https://{DOMAIN}/", headers={"Host": "evil.com"})

    assert requests[0].headers["host"] == DOMAIN
    assert requests[0].headers["accept-encoding"] == "identity"


@pytest.mark.asyncio
async def test_request_budget_is_enforced() -> None:
    sender, requests = scripted_sender([(200, {}, b"ok"), (200, {}, b"ok")])
    client, guard = make_client(policy=make_policy(max_requests=2), sender=sender)

    await client.request("GET", f"https://{DOMAIN}/")
    await client.request("GET", f"https://{DOMAIN}/")

    with pytest.raises(RequestBudgetExhausted):
        await client.request("GET", f"https://{DOMAIN}/")

    assert len(requests) == 2
    assert guard.requests_made == 2
    assert guard.remaining_requests == 0


@pytest.mark.asyncio
async def test_safe_mode_rate_limit_is_enforced() -> None:
    now = 1000.0
    sleeps: list[float] = []

    def clock() -> float:
        return now

    async def sleeper(seconds: float) -> None:
        nonlocal now
        sleeps.append(seconds)
        now += seconds

    sender, _ = scripted_sender([(200, {}, b"ok"), (200, {}, b"ok"), (200, {}, b"ok")])
    client, _ = make_client(
        policy=make_policy(max_requests=3, requests_per_second=2.0),
        sender=sender,
        clock=clock,
        sleeper=sleeper,
    )

    for _ in range(3):
        await client.request("GET", f"https://{DOMAIN}/")

    assert sleeps == [0.5, 0.5]


@pytest.mark.asyncio
async def test_deep_mode_rate_limit_is_enforced() -> None:
    now = 1000.0
    sleeps: list[float] = []

    def clock() -> float:
        return now

    async def sleeper(seconds: float) -> None:
        nonlocal now
        sleeps.append(seconds)
        now += seconds

    sender, _ = scripted_sender([(200, {}, b"ok"), (200, {}, b"ok")])
    client, _ = make_client(
        policy=make_policy(mode=ScanMode.DEEP),
        sender=sender,
        clock=clock,
        sleeper=sleeper,
    )

    await client.request("GET", f"https://{DOMAIN}/")
    await client.request("GET", f"https://{DOMAIN}/")

    assert sleeps == [0.1]


@pytest.mark.asyncio
async def test_transport_refuses_foreign_urls_before_the_pool() -> None:
    guard = EgressGuard(make_policy(), resolver=static_resolver(PUBLIC))
    pool = FakePool(httpcore.Response(200, content=b"ok"))
    transport = PinnedTransport(guard, max_response_bytes=1024, pool=pool)

    request = httpx.Request("GET", "https://evil.com/")
    with pytest.raises(HostNotAllowed):
        await transport.handle_async_request(request)

    assert pool.requests == []


@pytest.mark.asyncio
async def test_transport_refuses_mutating_methods_in_safe_mode() -> None:
    guard = EgressGuard(make_policy(), resolver=static_resolver(PUBLIC))
    pool = FakePool(httpcore.Response(200, content=b"ok"))
    transport = PinnedTransport(guard, max_response_bytes=1024, pool=pool)

    request = httpx.Request("POST", f"https://{DOMAIN}/")
    with pytest.raises(MethodBlocked):
        await transport.handle_async_request(request)

    assert pool.requests == []


@pytest.mark.asyncio
async def test_transport_overrides_caller_host_header() -> None:
    guard = EgressGuard(make_policy(), resolver=static_resolver(PUBLIC))
    pool = FakePool(httpcore.Response(200, content=b"ok"))
    transport = PinnedTransport(guard, max_response_bytes=1024, pool=pool)

    request = httpx.Request(
        "GET",
        f"https://{DOMAIN}/",
        headers={"Host": "evil.com", "X-Test": "1"},
    )
    await transport.handle_async_request(request)

    host_values = [
        value for name, value in pool.requests[0].headers if name == b"host"
    ]
    assert host_values == [DOMAIN.encode()]
    assert all(b"evil.com" not in value for _, value in pool.requests[0].headers)


@pytest.mark.asyncio
async def test_transport_caps_response_size_and_marks_truncation() -> None:
    guard = EgressGuard(make_policy(), resolver=static_resolver(PUBLIC))
    pool = FakePool(
        httpcore.Response(
            200,
            headers=[(b"content-type", b"text/plain")],
            content=ChunkStream([b"a" * 10, b"b" * 10]),
        )
    )
    transport = PinnedTransport(guard, max_response_bytes=15, pool=pool)

    request = httpx.Request("GET", f"https://{DOMAIN}/")
    response = await transport.handle_async_request(request)

    assert response.content == b"a" * 10 + b"b" * 5
    assert response.extensions["mirsad_truncated"] is True


@pytest.mark.asyncio
async def test_transport_does_not_mark_exact_size_as_truncated() -> None:
    guard = EgressGuard(make_policy(), resolver=static_resolver(PUBLIC))
    pool = FakePool(
        httpcore.Response(
            200,
            content=ChunkStream([b"a" * 10, b"b" * 10]),
        )
    )
    transport = PinnedTransport(guard, max_response_bytes=20, pool=pool)

    request = httpx.Request("GET", f"https://{DOMAIN}/")
    response = await transport.handle_async_request(request)

    assert response.content == b"a" * 10 + b"b" * 10
    assert response.extensions["mirsad_truncated"] is False


@pytest.mark.asyncio
async def test_transport_maps_network_errors_to_a_guard_error() -> None:
    class FailingPool(FakePool):
        async def handle_async_request(self, request: httpcore.Request) -> httpcore.Response:
            raise httpcore.ConnectError("connection refused")

    guard = EgressGuard(make_policy(), resolver=static_resolver(PUBLIC))
    transport = PinnedTransport(
        guard,
        max_response_bytes=1024,
        pool=FailingPool(httpcore.Response(200)),
    )

    request = httpx.Request("GET", f"https://{DOMAIN}/")
    with pytest.raises(TransportFailure):
        await transport.handle_async_request(request)


def test_guarded_response_header_lookup_is_case_insensitive() -> None:
    response = GuardedResponse(
        status_code=200,
        headers=(("Content-Type", "text/plain"),),
        content=b"ok",
        url=f"https://{DOMAIN}/",
    )
    assert response.header("content-type") == "text/plain"
    assert response.header("missing") is None


def test_safe_url_for_repr_drops_query_and_userinfo() -> None:
    safe = safe_url_for_repr(
        f"https://user:password@{DOMAIN}/path?token=secret&email=user@example.com"
    )
    assert safe == f"https://{DOMAIN}/path"
    assert "secret" not in safe
    assert "password" not in safe
