"""Scan-mode policy and hard limits (plan.md §6, §7; AGENTS.md §6).

Safe Mode (production) is non-mutating, capped at 2 requests/second and 300
requests. Deep Mode (staging only) permits non-destructive active checks,
capped at 10 requests/second and 600 requests. Callers may tighten these
limits through configuration; they may never raise them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .addresses import normalize_hostname
from .errors import ConsentRequired, ModeNotAllowed, PolicyInvalid, TargetNotVerified

SAFE_MAX_REQUESTS = 300
DEEP_MAX_REQUESTS = 600
SAFE_REQUESTS_PER_SECOND = 2.0
DEEP_REQUESTS_PER_SECOND = 10.0
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
DEEP_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "POST", "PUT", "PATCH"})
ALLOWED_PORTS = frozenset({80, 443})
DEFAULT_PORTS = {"http": 80, "https": 443}
MAX_REDIRECTS = 10
MAX_REQUEST_TIMEOUT_SECONDS = 30.0
MAX_RESPONSE_BYTES = 5_000_000


class ScanMode(str, Enum):
    """Approved scan modes; production is always forced to Safe Mode."""

    SAFE = "safe"
    DEEP = "deep"


class TargetEnvironment(str, Enum):
    """Customer-declared environment attached to a verified domain."""

    STAGING = "staging"
    PRODUCTION = "production"


@dataclass(frozen=True)
class VerifiedTarget:
    """A domain whose ownership and consent were checked before scanning.

    The two booleans are deliberately required at construction time. They are
    not inferred from the domain string, and a caller cannot silently create a
    scannable target by omitting them.
    """

    domain: str
    environment: TargetEnvironment
    ownership_verified: bool
    consent_granted: bool

    def __post_init__(self) -> None:
        if not isinstance(self.environment, TargetEnvironment):
            raise PolicyInvalid("environment must be a TargetEnvironment value.")
        if self.ownership_verified is not True:
            raise TargetNotVerified("Domain ownership must be verified before scanning.")
        if self.consent_granted is not True:
            raise ConsentRequired("Recorded consent is required before scanning.")
        object.__setattr__(self, "domain", normalize_hostname(self.domain))


@dataclass(frozen=True)
class EgressPolicy:
    """Immutable guard configuration for one scan episode.

    ``max_requests`` and ``requests_per_second`` are optional *tightenings*.
    Values above the mode's hard cap raise ``PolicyInvalid`` instead of being
    silently clamped, so a misconfiguration cannot weaken the guard.
    """

    target: VerifiedTarget
    mode: ScanMode
    max_requests: int | None = None
    requests_per_second: float | None = None
    max_redirects: int = 5
    request_timeout_seconds: float = 15.0
    max_response_bytes: int = 2_000_000
    effective_max_requests: int = field(init=False, repr=False)
    effective_rate: float = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.mode, ScanMode):
            raise PolicyInvalid("mode must be a ScanMode value.")

        if self.mode is ScanMode.DEEP and self.target.environment is TargetEnvironment.PRODUCTION:
            raise ModeNotAllowed("Deep Mode is not allowed on production targets.")

        hard_request_cap = (
            SAFE_MAX_REQUESTS if self.mode is ScanMode.SAFE else DEEP_MAX_REQUESTS
        )
        hard_rate = (
            SAFE_REQUESTS_PER_SECOND
            if self.mode is ScanMode.SAFE
            else DEEP_REQUESTS_PER_SECOND
        )

        if self.max_requests is None:
            max_requests = hard_request_cap
        else:
            if self.max_requests < 1 or self.max_requests > hard_request_cap:
                raise PolicyInvalid("max_requests must be between 1 and the mode hard cap.")
            max_requests = self.max_requests

        if self.requests_per_second is None:
            rate = hard_rate
        else:
            if self.requests_per_second <= 0 or self.requests_per_second > hard_rate:
                raise PolicyInvalid(
                    "requests_per_second must be positive and within the mode hard cap."
                )
            rate = self.requests_per_second

        if self.max_redirects < 0 or self.max_redirects > MAX_REDIRECTS:
            raise PolicyInvalid("max_redirects is outside the allowed range.")

        if not 1.0 <= self.request_timeout_seconds <= MAX_REQUEST_TIMEOUT_SECONDS:
            raise PolicyInvalid("request_timeout_seconds is outside the allowed range.")

        if not 16 <= self.max_response_bytes <= MAX_RESPONSE_BYTES:
            raise PolicyInvalid("max_response_bytes is outside the allowed range.")

        object.__setattr__(self, "effective_max_requests", max_requests)
        object.__setattr__(self, "effective_rate", rate)

    @property
    def allowed_methods(self) -> frozenset[str]:
        return SAFE_METHODS if self.mode is ScanMode.SAFE else DEEP_METHODS

    @property
    def minimum_interval_seconds(self) -> float:
        return 1.0 / self.effective_rate
