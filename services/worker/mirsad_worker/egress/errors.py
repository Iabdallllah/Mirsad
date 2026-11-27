"""Stable egress-guard error codes (plan.md §4.2, §14.1).

Every blocked request raises one of these errors. Messages intentionally
contain only safe context (never full URLs or query strings) so they can be
persisted in scan events without leaking test credentials.
"""

from __future__ import annotations


class EgressError(RuntimeError):
    """Base class for all egress-guard refusals."""

    code: str = "EGRESS_BLOCKED"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.code = type(self).code

    def __repr__(self) -> str:
        return f"{type(self).__name__}(code={self.code!r})"


class PolicyInvalid(EgressError):
    """The requested policy would weaken a hard safety limit."""

    code = "EGRESS_POLICY_INVALID"


class TargetNotVerified(EgressError):
    """The target domain has not passed ownership verification."""

    code = "EGRESS_TARGET_NOT_VERIFIED"


class ConsentRequired(EgressError):
    """Recorded consent is required before any scan request."""

    code = "EGRESS_CONSENT_REQUIRED"


class ModeNotAllowed(EgressError):
    """The requested scan mode is not permitted for the environment."""

    code = "EGRESS_MODE_NOT_ALLOWED"


class UrlInvalid(EgressError):
    """The URL is malformed or contains ambiguous characters."""

    code = "EGRESS_URL_INVALID"


class UrlTooLong(EgressError):
    """The URL exceeds the guard's maximum length."""

    code = "EGRESS_URL_TOO_LONG"


class SchemeBlocked(EgressError):
    """Only HTTP and HTTPS are allowed."""

    code = "EGRESS_SCHEME_BLOCKED"


class UserInfoBlocked(EgressError):
    """URL userinfo (user:password@) and encoded authority tricks are refused."""

    code = "EGRESS_USERINFO_BLOCKED"


class PortBlocked(EgressError):
    """Only TCP 80 and 443 are allowed."""

    code = "EGRESS_PORT_BLOCKED"


class InvalidHost(EgressError):
    """The host is not a valid public DNS name."""

    code = "EGRESS_INVALID_HOST"


class IpLiteralBlocked(EgressError):
    """IP literals and numeric host encodings are refused."""

    code = "EGRESS_IP_LITERAL_BLOCKED"


class HostNotAllowed(EgressError):
    """The host is not exactly the verified target domain."""

    code = "EGRESS_HOST_BLOCKED"


class DnsResolutionFailed(EgressError):
    """DNS did not return a usable public address."""

    code = "EGRESS_DNS_FAILED"


class PrivateAddressBlocked(EgressError):
    """DNS resolved to a private, loopback, link-local, metadata, or reserved IP."""

    code = "EGRESS_PRIVATE_ADDRESS_BLOCKED"


class MethodBlocked(EgressError):
    """The HTTP method is not allowed in the active scan mode."""

    code = "EGRESS_METHOD_BLOCKED"


class RequestBudgetExhausted(EgressError):
    """The per-scan request cap has been reached."""

    code = "EGRESS_REQUEST_BUDGET_EXHAUSTED"


class RedirectBlocked(EgressError):
    """A redirect would leave the verified host or downgrade transport."""

    code = "EGRESS_REDIRECT_BLOCKED"


class TooManyRedirects(EgressError):
    """The redirect chain exceeded the configured maximum."""

    code = "EGRESS_TOO_MANY_REDIRECTS"


class UnixSocketBlocked(EgressError):
    """Unix-domain sockets are never valid scan destinations."""

    code = "EGRESS_UNIX_SOCKET_BLOCKED"


class TransportFailure(EgressError):
    """The pinned transport failed before a response was received."""

    code = "EGRESS_TRANSPORT_FAILED"
