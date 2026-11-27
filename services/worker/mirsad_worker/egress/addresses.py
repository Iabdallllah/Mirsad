"""Host canonicalisation and blocked-address checks (plan.md §14.1).

The guard accepts only DNS names that are exactly the verified domain. IP
literals — including decimal, hexadecimal, octal, dotted-shorthand, and
IPv6 forms — are rejected before any socket work. Resolved addresses are
validated against explicit private/internal ranges *and* ``is_global`` as a
second layer, so a target cannot pivot to localhost, link-local cloud
metadata, RFC1918 space, CGNAT, multicast, documentation ranges, or IPv6
equivalents.
"""

from __future__ import annotations

import ipaddress
import re

from .errors import (
    DnsResolutionFailed,
    HostNotAllowed,
    InvalidHost,
    IpLiteralBlocked,
    PrivateAddressBlocked,
)

# Hostnames that are never legitimate public scan targets. The exact-domain
# allowlist already blocks these, but an explicit denial documents intent and
# protects future callers that build policies from less trustworthy input.
_BLOCKED_HOSTNAMES = frozenset(
    {
        "instance-data",
        "instance-data.ec2.internal",
        "localhost",
        "localhost.localdomain",
        "metadata",
        "metadata.azure.internal",
        "metadata.google.internal",
        "metadata.goog",
    }
)

# Wildcard DNS services can map a hostname straight to an embedded IP
# (commonly 127.0.0.1) without the workspace controlling a zone. Refuse them
# even if an upstream verification bug ever lets one into a policy.
_BLOCKED_DYNAMIC_DNS_SUFFIXES = (
    "lvh.me",
    "localtest.me",
    "nip.io",
    "sslip.io",
    "traefik.me",
    "xip.io",
)

_HOST_LABEL = re.compile(r"^(?!-)[a-z0-9-]{1,63}(?<!-)$")
_NUMERIC_PART = re.compile(r"^(?:0[xX][0-9a-fA-F]+|[0-9]+)$")
_MAX_HOST_LENGTH = 253

# Explicit networks are kept even where ``is_global`` already returns false,
# because the property is version-sensitive and the capability is security
# critical. The list is intentionally fail-closed.
_BLOCKED_IPV4_NETWORKS = tuple(
    ipaddress.ip_network(network)
    for network in (
        "0.0.0.0/8",
        "10.0.0.0/8",
        "100.64.0.0/10",
        "127.0.0.0/8",
        "169.254.0.0/16",
        "172.16.0.0/12",
        "192.0.0.0/24",
        "192.0.2.0/24",
        "192.88.99.0/24",
        "192.168.0.0/16",
        "198.18.0.0/15",
        "198.51.100.0/24",
        "203.0.113.0/24",
        "224.0.0.0/4",
        "240.0.0.0/4",
    )
)

_BLOCKED_IPV6_NETWORKS = tuple(
    ipaddress.ip_network(network)
    for network in (
        "::/128",
        "::1/128",
        "64:ff9b::/96",
        "64:ff9b:1::/48",
        "100::/64",
        "2001::/32",
        "2001:db8::/32",
        "2002::/16",
        "fc00::/7",
        "fe80::/10",
        "ff00::/8",
    )
)

IpAddress = ipaddress.IPv4Address | ipaddress.IPv6Address


def normalize_hostname(raw: str) -> str:
    """Return the canonical ASCII hostname or raise a guard error.

    Supported input is a lowercase-able ASCII DNS name with at least two
    labels. A single trailing root dot is tolerated; all other ambiguity
    (userinfo, percent encoding, whitespace, control characters, IP literals,
    metadata names, wildcard-DNS services) is rejected. Internationalised
    domains must reach the guard as punycode from the domain record.
    """

    if not isinstance(raw, str):
        raise InvalidHost("Host must be a string.")

    if not raw or raw != raw.strip():
        raise InvalidHost("Host is empty or contains surrounding whitespace.")

    if any(ord(char) < 33 or ord(char) == 127 for char in raw):
        raise InvalidHost("Host contains whitespace or control characters.")

    if raw.endswith("."):
        raw = raw[:-1]

    if not raw:
        raise InvalidHost("Host is empty.")

    if not raw.isascii():
        raise InvalidHost("Host must be ASCII punycode.")

    if _looks_like_ip_literal(raw):
        raise IpLiteralBlocked("IP literals and numeric host encodings are not allowed.")

    if any(char in raw for char in ("/", "\\", "@", "#", "?", "%", "[", "]")):
        raise InvalidHost("Host contains forbidden characters.")

    host = raw.lower()

    if host in _BLOCKED_HOSTNAMES or host.endswith(".localhost"):
        raise HostNotAllowed("Host is a local or metadata hostname.")

    for suffix in _BLOCKED_DYNAMIC_DNS_SUFFIXES:
        if host == suffix or host.endswith(f".{suffix}"):
            raise HostNotAllowed("Wildcard DNS hostnames are not allowed.")

    if len(host) > _MAX_HOST_LENGTH:
        raise InvalidHost("Host is too long.")

    labels = host.split(".")
    if len(labels) < 2:
        raise InvalidHost("Host must be a fully-qualified DNS name.")

    for label in labels:
        if not _HOST_LABEL.fullmatch(label):
            raise InvalidHost("Host contains an invalid DNS label.")

    return host


def _looks_like_ip_literal(host: str) -> bool:
    """Detect numeric IP encodings that DNS resolvers may accept.

    ``urlsplit`` does not expose whether a host was written as ``2130706433``
    or ``0x7f000001``; all of them can resolve to loopback. Any all-numeric
    dotted host with one to four parts is treated as an IP literal, valid or
    not, because there is no legitimate public DNS reason to scan one.
    """

    if ":" in host:
        return True

    parts = host.split(".")
    if parts and all(_NUMERIC_PART.fullmatch(part) for part in parts):
        return True

    return False


def assert_public_ip(address: str) -> IpAddress:
    """Validate one resolver answer and return the parsed IP address."""

    if not isinstance(address, str) or not address or "%" in address:
        raise DnsResolutionFailed("Resolver returned a scoped or empty address.")

    try:
        ip = ipaddress.ip_address(address)
    except ValueError as exc:
        raise DnsResolutionFailed("Resolver returned a non-IP address.") from exc

    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        if _is_blocked_ip(ip.ipv4_mapped):
            raise PrivateAddressBlocked("Resolved address is private, internal, or reserved.")
        return ip

    if _is_blocked_ip(ip):
        raise PrivateAddressBlocked("Resolved address is private, internal, or reserved.")

    return ip


def is_public_ip(address: str) -> bool:
    """Convenience predicate used by tests and future telemetry."""

    try:
        assert_public_ip(address)
    except (DnsResolutionFailed, PrivateAddressBlocked):
        return False
    return True


def _is_blocked_ip(ip: IpAddress) -> bool:
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        return True

    # ``is_global`` is false for much of the reserved/documentation space and
    # is a useful defensive backstop for ranges added in future Python
    # versions. It is deliberately combined with explicit networks.
    if not ip.is_global:
        return True

    if isinstance(ip, ipaddress.IPv4Address):
        return any(ip in network for network in _BLOCKED_IPV4_NETWORKS)

    return any(ip in network for network in _BLOCKED_IPV6_NETWORKS)
