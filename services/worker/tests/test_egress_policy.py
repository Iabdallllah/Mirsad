"""Unit tests for scan-mode policy and address validation (plan.md §6, §14.1)."""

from __future__ import annotations

import pytest

from mirsad_worker.egress import (
    DEEP_MAX_REQUESTS,
    DEEP_REQUESTS_PER_SECOND,
    SAFE_MAX_REQUESTS,
    SAFE_REQUESTS_PER_SECOND,
    ConsentRequired,
    DnsResolutionFailed,
    EgressPolicy,
    HostNotAllowed,
    InvalidHost,
    IpLiteralBlocked,
    ModeNotAllowed,
    PolicyInvalid,
    PrivateAddressBlocked,
    ScanMode,
    TargetEnvironment,
    TargetNotVerified,
    VerifiedTarget,
    assert_public_ip,
    is_public_ip,
    normalize_hostname,
)


def _target(
    *,
    domain: str = "app.example.com",
    environment: TargetEnvironment = TargetEnvironment.STAGING,
) -> VerifiedTarget:
    return VerifiedTarget(
        domain=domain,
        environment=environment,
        ownership_verified=True,
        consent_granted=True,
    )


def test_verified_target_requires_ownership() -> None:
    with pytest.raises(TargetNotVerified):
        VerifiedTarget(
            domain="app.example.com",
            environment=TargetEnvironment.STAGING,
            ownership_verified=False,
            consent_granted=True,
        )


def test_verified_target_requires_consent() -> None:
    with pytest.raises(ConsentRequired):
        VerifiedTarget(
            domain="app.example.com",
            environment=TargetEnvironment.STAGING,
            ownership_verified=True,
            consent_granted=False,
        )


def test_truthy_strings_do_not_satisfy_ownership_or_consent() -> None:
    with pytest.raises(TargetNotVerified):
        VerifiedTarget(
            domain="app.example.com",
            environment=TargetEnvironment.STAGING,
            ownership_verified="true",  # type: ignore[arg-type]
            consent_granted=True,
        )
    with pytest.raises(ConsentRequired):
        VerifiedTarget(
            domain="app.example.com",
            environment=TargetEnvironment.STAGING,
            ownership_verified=True,
            consent_granted="true",  # type: ignore[arg-type]
        )


def test_string_mode_is_rejected() -> None:
    with pytest.raises(PolicyInvalid):
        EgressPolicy(
            target=_target(),
            mode="deep",  # type: ignore[arg-type]
        )


def test_string_environment_is_rejected() -> None:
    with pytest.raises(PolicyInvalid):
        VerifiedTarget(
            domain="app.example.com",
            environment="production",  # type: ignore[arg-type]
            ownership_verified=True,
            consent_granted=True,
        )


def test_safe_mode_defaults_match_plan() -> None:
    policy = EgressPolicy(
        target=_target(environment=TargetEnvironment.PRODUCTION),
        mode=ScanMode.SAFE,
    )
    assert policy.effective_max_requests == SAFE_MAX_REQUESTS == 300
    assert policy.effective_rate == SAFE_REQUESTS_PER_SECOND == 2.0
    assert policy.allowed_methods == frozenset({"GET", "HEAD", "OPTIONS"})


def test_deep_mode_defaults_match_plan() -> None:
    policy = EgressPolicy(target=_target(), mode=ScanMode.DEEP)
    assert policy.effective_max_requests == DEEP_MAX_REQUESTS == 600
    assert policy.effective_rate == DEEP_REQUESTS_PER_SECOND == 10.0
    assert policy.allowed_methods == frozenset({"GET", "HEAD", "OPTIONS", "POST", "PUT", "PATCH"})


def test_deep_mode_rejected_on_production() -> None:
    with pytest.raises(ModeNotAllowed):
        EgressPolicy(
            target=_target(environment=TargetEnvironment.PRODUCTION),
            mode=ScanMode.DEEP,
        )


def test_limits_can_be_tightened_but_not_raised() -> None:
    tightened = EgressPolicy(
        target=_target(environment=TargetEnvironment.PRODUCTION),
        mode=ScanMode.SAFE,
        max_requests=100,
        requests_per_second=1.0,
    )
    assert tightened.effective_max_requests == 100
    assert tightened.effective_rate == 1.0

    with pytest.raises(PolicyInvalid):
        EgressPolicy(
            target=_target(environment=TargetEnvironment.PRODUCTION),
            mode=ScanMode.SAFE,
            max_requests=SAFE_MAX_REQUESTS + 1,
        )
    with pytest.raises(PolicyInvalid):
        EgressPolicy(
            target=_target(environment=TargetEnvironment.PRODUCTION),
            mode=ScanMode.SAFE,
            requests_per_second=SAFE_REQUESTS_PER_SECOND + 0.1,
        )
    with pytest.raises(PolicyInvalid):
        EgressPolicy(
            target=_target(),
            mode=ScanMode.DEEP,
            max_requests=DEEP_MAX_REQUESTS + 1,
        )
    with pytest.raises(PolicyInvalid):
        EgressPolicy(
            target=_target(),
            mode=ScanMode.DEEP,
            requests_per_second=DEEP_REQUESTS_PER_SECOND + 0.1,
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_requests": 0},
        {"requests_per_second": 0},
        {"max_redirects": -1},
        {"max_redirects": 11},
        {"request_timeout_seconds": 0.5},
        {"request_timeout_seconds": 31.0},
        {"max_response_bytes": 15},
        {"max_response_bytes": 5_000_001},
    ],
)
def test_invalid_policy_limits(kwargs: dict[str, float]) -> None:
    with pytest.raises(PolicyInvalid):
        EgressPolicy(
            target=_target(environment=TargetEnvironment.PRODUCTION),
            mode=ScanMode.SAFE,
            **kwargs,  # type: ignore[arg-type]
        )


def test_target_domain_must_be_a_public_dns_name() -> None:
    with pytest.raises(IpLiteralBlocked):
        _target(domain="127.0.0.1")
    with pytest.raises(HostNotAllowed):
        _target(domain="localhost")
    with pytest.raises(InvalidHost):
        _target(domain="not a host")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("APP.Example.COM", "app.example.com"),
        ("app.example.com.", "app.example.com"),
        ("xn--bcher-kva.example", "xn--bcher-kva.example"),
    ],
)
def test_normalize_hostname_accepts_dns_names(raw: str, expected: str) -> None:
    assert normalize_hostname(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        " app.example.com",
        "app.example.com ",
        "app.example.com\n",
        "app example.com",
        "app.example.com/path",
        "app.example.com\\path",
        "user@app.example.com",
        "app.example.com%2eevil.com",
        "app.example.com#fragment",
        "app.example.com?query",
        "app.example.com:443",
        "[::1]",
        "app..example.com",
        "-app.example.com",
        "app-.example.com",
        "app.example.com..",
        "bücher.example",
    ],
)
def test_normalize_hostname_rejects_ambiguous_input(raw: str) -> None:
    with pytest.raises((InvalidHost, IpLiteralBlocked, HostNotAllowed)):
        normalize_hostname(raw)


@pytest.mark.parametrize(
    "raw",
    [
        "127.0.0.1",
        "127.1",
        "10.0.0.1",
        "0.0.0.0",
        "0",
        "2130706433",
        "0x7f000001",
        "017700000001",
        "169.254.169.254",
        "::1",
        "::ffff:127.0.0.1",
        "fd00:ec2::254",
    ],
)
def test_ip_literals_are_rejected(raw: str) -> None:
    with pytest.raises(IpLiteralBlocked):
        normalize_hostname(raw)


@pytest.mark.parametrize(
    "host",
    [
        "localhost",
        "localhost.localdomain",
        "metadata",
        "metadata.google.internal",
        "metadata.azure.internal",
        "instance-data",
        "foo.localhost",
        "app.localhost",
    ],
)
def test_local_and_metadata_hostnames_are_rejected(host: str) -> None:
    with pytest.raises(HostNotAllowed):
        normalize_hostname(host)


@pytest.mark.parametrize(
    "host",
    [
        "127.0.0.1.nip.io",
        "localtest.me",
        "foo.sslip.io",
        "xip.io",
        "app.lvh.me",
        "traefik.me",
    ],
)
def test_wildcard_dns_services_are_rejected(host: str) -> None:
    with pytest.raises(HostNotAllowed):
        normalize_hostname(host)


@pytest.mark.parametrize(
    "address",
    [
        "8.8.8.8",
        "1.1.1.1",
        "93.184.216.34",
        "2606:4700:4700::1111",
        "::ffff:8.8.8.8",
    ],
)
def test_public_addresses_are_accepted(address: str) -> None:
    assert is_public_ip(address)
    assert str(assert_public_ip(address))


@pytest.mark.parametrize(
    "address",
    [
        "0.0.0.0",
        "10.0.0.1",
        "10.255.255.255",
        "100.64.0.1",
        "127.0.0.1",
        "127.255.255.255",
        "169.254.169.254",
        "172.16.0.1",
        "172.31.255.255",
        "192.0.0.1",
        "192.0.2.1",
        "192.88.99.1",
        "192.168.0.1",
        "198.18.0.1",
        "198.51.100.1",
        "203.0.113.1",
        "224.0.0.1",
        "240.0.0.1",
        "255.255.255.255",
        "::",
        "::1",
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
def test_private_and_reserved_addresses_are_rejected(address: str) -> None:
    assert not is_public_ip(address)
    with pytest.raises(PrivateAddressBlocked):
        assert_public_ip(address)


@pytest.mark.parametrize(
    "address",
    ["", "not-an-ip", "fe80::1%eth0", "1.2.3.999", "999.1.1.1"],
)
def test_malformed_resolver_answers_are_rejected(address: str) -> None:
    with pytest.raises(DnsResolutionFailed):
        assert_public_ip(address)
