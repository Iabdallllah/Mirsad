"""Deterministic redaction rules for the PII sanitizer (AGENTS.md §7).

Rules are intentionally conservative: over-redacting a benign value is
preferable to persisting a credential, cookie, token, email, phone number, or
payment-card number. Nothing here calls a model or depends on network access.
"""

from __future__ import annotations

import re

REDACTED = "[REDACTED]"
REDACTED_EMAIL = "[REDACTED_EMAIL]"
REDACTED_PHONE = "[REDACTED_PHONE]"
REDACTED_CARD = "[REDACTED_CARD]"
REDACTED_JWT = "[REDACTED_JWT]"
REDACTED_PRIVATE_KEY = "[REDACTED_PRIVATE_KEY]"
REDACTED_BINARY = "[BINARY_DATA_REDACTED]"

_PRIVATE_KEY_RE = re.compile(
    r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?-----END [A-Z0-9 ]*PRIVATE KEY-----",
    re.DOTALL,
)

_ASSIGNMENT_RE = re.compile(
    r"""
    (?P<key>
        (?:
            password|passwd|pwd|secret|token|api[ _-]?key|apikey|x[ _-]?key|
            authorization|cookie|session|jwt|client[ _-]?secret|
            access[ _-]?key|refresh[ _-]?token|private[ _-]?key|
            credential|card[ _-]?number|cvv|cvc|ssn|
            auth[ _-]?code|oauth[ _-]?code|passcode|
            database[ _-]?url|db[ _-]?url|dsn|connection[ _-]?string|
            redis[ _-]?url|smtp[ _-]?url|webhook[ _-]?secret|
            signing[ _-]?key|encryption[ _-]?key
        )
        [A-Za-z0-9_. -]{0,64}
    )
    (?P<keyquote>["']?)
    (?P<sep>\s*[:=]\s*)
    (?P<value>
        "(?:[^"\\]|\\.)*"
        | '(?:[^'\\]|\\.)*'
        | [^\r\n]+
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

_JWT_RE = re.compile(r"eyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]*")

_AUTH_SCHEME_RE = re.compile(
    r"(?i)\b(?:Bearer|Basic|Digest|Token)\s+[A-Za-z0-9._~+/=-]{6,}"
)

_API_KEY_RE = re.compile(
    r"""
    (?<![A-Za-z0-9])(?:sk|pk|rk)[_-](?:(?:live|test|proj)_)?[A-Za-z0-9_-]{8,}
    |(?<![A-Za-z0-9])gh[pousr]_[A-Za-z0-9]{20,}
    |(?<![A-Za-z0-9])github_pat_[A-Za-z0-9_]{20,}
    |(?<![A-Za-z0-9])AKIA[0-9A-Z]{16}(?![A-Za-z0-9])
    |(?<![A-Za-z0-9])ASIA[0-9A-Z]{16}(?![A-Za-z0-9])
    |(?<![A-Za-z0-9])AIza[0-9A-Za-z_-]{35}(?![A-Za-z0-9])
    |(?<![A-Za-z0-9])xox[baprs]-[A-Za-z0-9-]{10,}
    |(?<![A-Za-z0-9])glpat-[A-Za-z0-9_-]{20,}
    |(?<![A-Za-z0-9])GOCSPX-[A-Za-z0-9_-]{20,}
    |(?<![A-Za-z0-9])whsec_[A-Za-z0-9_-]{10,}
    """,
    re.VERBOSE,
)

_EMAIL_RE = re.compile(
    r"(?<![A-Za-z0-9._%+-])"
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
    r"(?![A-Za-z0-9.-])"
)

_CARD_RE = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")

_E164_RE = re.compile(r"(?<![\d+])\+\d{7,15}(?!\d)")
_PHONE_FORMATTED_RE = re.compile(
    r"(?<!\d)(?:\(\d{3}\)\s?|\d{3}[-. ])\d{3}[-. ]\d{4}(?!\d)"
)
_PHONE_INTERNATIONAL_RE = re.compile(
    r"(?<!\d)\+\d{1,3}(?:[\s.-]?\d{2,4}){2,4}(?!\d)"
)

_SENSITIVE_KEYS = frozenset(
    {
        "access_key",
        "access_token",
        "api_key",
        "apikey",
        "auth",
        "auth_code",
        "auth_token",
        "authorization",
        "authorization_code",
        "aws_access_key_id",
        "aws_secret_access_key",
        "card_number",
        "client_secret",
        "connection_string",
        "cookie",
        "credit_card",
        "csrf_token",
        "cvc",
        "cvv",
        "database_url",
        "db_url",
        "dsn",
        "encryption_key",
        "id_token",
        "jwt",
        "key",
        "oauth_code",
        "one_time_password",
        "otp",
        "passcode",
        "passwd",
        "password",
        "pin",
        "private_key",
        "proxy_authorization",
        "pwd",
        "redis_url",
        "refresh_token",
        "secret",
        "secret_key",
        "session",
        "session_id",
        "sessionid",
        "set_cookie",
        "signing_key",
        "smtp_url",
        "ssn",
        "token",
        "webhook_secret",
        "x_api_key",
        "x_auth_token",
        "x_key",
        "xsrf_token",
    }
)

_SENSITIVE_KEY_PARTS = (
    "access_key",
    "api_key",
    "apikey",
    "auth_code",
    "authorization",
    "authorization_code",
    "card_number",
    "connection_string",
    "cookie",
    "credential",
    "credit_card",
    "cvc",
    "cvv",
    "database_url",
    "encryption_key",
    "jwt",
    "oauth_code",
    "passcode",
    "password",
    "passwd",
    "private_key",
    "secret",
    "session",
    "signing_key",
    "ssn",
    "token",
    "webhook_secret",
)


def normalize_key(key: str) -> str:
    """Normalize a header/JSON/form key for sensitive-name matching."""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", key)
    return re.sub(r"[^a-z0-9]+", "_", spaced.lower()).strip("_")


def is_sensitive_key(key: str) -> bool:
    """Return true for credential-bearing keys (fail closed on ambiguity)."""

    normalized = normalize_key(key)
    if not normalized:
        return False
    if normalized in _SENSITIVE_KEYS:
        return True
    return any(part in normalized for part in _SENSITIVE_KEY_PARTS)


def luhn_valid(digits: str) -> bool:
    """Validate a payment-card candidate using the Luhn checksum."""

    if not digits.isdigit() or not 13 <= len(digits) <= 19:
        return False

    total = 0
    parity = len(digits) % 2
    for index, char in enumerate(digits):
        value = int(char)
        if index % 2 == parity:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0


def redact_private_keys(value: str) -> str:
    return _PRIVATE_KEY_RE.sub(REDACTED_PRIVATE_KEY, value)


def redact_assignments(value: str) -> str:
    def replacement(match: re.Match[str]) -> str:
        return (
            f"{match.group('key')}{match.group('keyquote')}"
            f"{match.group('sep')}{REDACTED}"
        )

    return _ASSIGNMENT_RE.sub(replacement, value)


def redact_jwts(value: str) -> str:
    return _JWT_RE.sub(REDACTED_JWT, value)


def redact_auth_schemes(value: str) -> str:
    return _AUTH_SCHEME_RE.sub(lambda match: f"{match.group(0).split()[0]} {REDACTED}", value)


def redact_api_keys(value: str) -> str:
    return _API_KEY_RE.sub(REDACTED, value)


def redact_emails(value: str) -> str:
    return _EMAIL_RE.sub(REDACTED_EMAIL, value)


def redact_cards(value: str) -> str:
    def replacement(match: re.Match[str]) -> str:
        digits = re.sub(r"\D", "", match.group(0))
        return REDACTED_CARD if luhn_valid(digits) else match.group(0)

    return _CARD_RE.sub(replacement, value)


def redact_phones(value: str) -> str:
    value = _E164_RE.sub(REDACTED_PHONE, value)
    value = _PHONE_INTERNATIONAL_RE.sub(REDACTED_PHONE, value)
    return _PHONE_FORMATTED_RE.sub(REDACTED_PHONE, value)
