"""Deterministic PII/secret sanitizer for storage and LLM boundaries.

All evidence, scan events, PDF inputs, and LLM payloads must pass through
these functions first (AGENTS.md §7, plan.md §14.1). The sanitizer preserves
structure where possible so downstream schemas keep working, while replacing
sensitive values with fixed markers that contain no part of the original.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from typing import Any
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

from .rules import (
    REDACTED,
    REDACTED_BINARY,
    is_sensitive_key,
    redact_api_keys,
    redact_assignments,
    redact_auth_schemes,
    redact_cards,
    redact_emails,
    redact_jwts,
    redact_phones,
    redact_private_keys,
)


def sanitize_text(value: str) -> str:
    """Redact credentials and PII embedded in free-form text."""

    if not isinstance(value, str):
        raise TypeError("sanitize_text expects a string")

    result = redact_private_keys(value)
    result = redact_assignments(result)
    result = redact_jwts(result)
    result = redact_auth_schemes(result)
    result = redact_api_keys(result)
    result = redact_emails(result)
    result = redact_cards(result)
    result = redact_phones(result)
    return result


def sanitize_bytes(value: bytes) -> str:
    """Decode textual bytes and sanitize; binary-looking bytes are dropped."""

    try:
        text = value.decode("utf-8")
    except UnicodeDecodeError:
        return REDACTED_BINARY
    if "\x00" in text:
        return REDACTED_BINARY
    return sanitize_text(text)


def sanitize_headers(
    headers: Mapping[str, str] | Iterable[tuple[str, str]],
) -> dict[str, str]:
    """Redact sensitive headers and sanitize the values of the rest."""

    return dict(sanitize_header_items(headers))


def sanitize_header_items(
    headers: Mapping[str, str] | Iterable[tuple[str, str]],
) -> list[tuple[str, str]]:
    """Like ``sanitize_headers`` but preserves duplicate header names."""

    items = headers.items() if isinstance(headers, Mapping) else headers
    sanitized: list[tuple[str, str]] = []

    for name, value in items:
        if is_sensitive_key(name):
            sanitized.append((name, REDACTED))
        elif name.lower() in {"location", "origin", "referer"}:
            sanitized.append((name, _sanitize_header_url(value)))
        else:
            sanitized.append((name, sanitize_text(value)))

    return sanitized


def sanitize_url(url: str) -> str:
    """Drop userinfo and redact sensitive query parameters."""

    if not isinstance(url, str) or not url:
        return REDACTED

    try:
        parsed = urlsplit(url)
        host = parsed.hostname
        port = parsed.port
    except ValueError:
        return REDACTED

    if not parsed.scheme or host is None:
        return sanitize_text(url)

    netloc_host = f"[{host}]" if ":" in host else host
    if port is not None:
        netloc_host = f"{netloc_host}:{port}"

    return urlunsplit(
        (
            parsed.scheme,
            netloc_host,
            _sanitize_path(parsed.path),
            _sanitize_pairs(parse_qsl(parsed.query, keep_blank_values=True)),
            "",
        )
    )


def sanitize_form(body: str) -> str:
    """Redact sensitive fields in an ``application/x-www-form-urlencoded`` body."""

    if not isinstance(body, str):
        raise TypeError("sanitize_form expects a string")

    pairs = parse_qsl(body, keep_blank_values=True)
    if not pairs:
        return sanitize_text(body)
    return _sanitize_pairs(pairs)


def sanitize_body(body: bytes | str, content_type: str | None = None) -> str:
    """Sanitize a request/response body according to its declared media type.

    JSON and form bodies keep their structure (with sensitive values replaced);
    everything else is treated as free-form text. Non-UTF-8 bytes are dropped
    rather than passed through, because binary payloads can hide credentials.
    """

    media_type = (content_type or "").split(";", 1)[0].strip().lower()
    if _is_binary_media_type(media_type):
        return REDACTED_BINARY

    if isinstance(body, bytes):
        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError:
            return REDACTED_BINARY
    elif isinstance(body, str):
        text = body
    else:
        raise TypeError("sanitize_body expects bytes or a string")

    if "\x00" in text:
        return REDACTED_BINARY

    if media_type == "application/json" or media_type.endswith("+json"):
        try:
            parsed = json.loads(text)
        except (TypeError, ValueError):
            return sanitize_text(text)
        return json.dumps(
            sanitize_data(parsed),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

    if media_type == "application/x-www-form-urlencoded":
        return sanitize_form(text)

    return sanitize_text(text)


def sanitize_data(value: Any) -> Any:
    """Recursively sanitize JSON-like data while preserving its shape."""

    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, bytes):
        return sanitize_bytes(value)
    if isinstance(value, Mapping):
        sanitized: dict[str, Any] = {}
        for raw_key, raw_value in value.items():
            key = str(raw_key)
            safe_key = sanitize_text(key)
            if is_sensitive_key(key):
                sanitized[safe_key] = REDACTED
            else:
                sanitized[safe_key] = sanitize_data(raw_value)
        return sanitized
    if isinstance(value, list | tuple | set | frozenset):
        return [sanitize_data(item) for item in value]
    return value


def sanitize_for_llm(value: Any) -> dict[str, Any]:
    """Return a sanitized, explicitly untrusted envelope for an LLM call.

    The envelope makes the trust boundary explicit: target content is data,
    never instructions (AGENTS.md §8).
    """

    return {"trust": "untrusted_target_data", "data": sanitize_data(value)}


_BINARY_MEDIA_TYPES = frozenset(
    {
        "application/cbor",
        "application/gzip",
        "application/msgpack",
        "application/octet-stream",
        "application/pdf",
        "application/protobuf",
        "application/wasm",
        "application/x-7z-compressed",
        "application/x-gzip",
        "application/x-protobuf",
        "application/x-rar-compressed",
        "application/x-shockwave-flash",
        "application/x-tar",
        "application/zip",
    }
)
_BINARY_MEDIA_PREFIXES = (
    "audio/",
    "font/",
    "image/",
    "multipart/",
    "video/",
)


def _is_binary_media_type(media_type: str) -> bool:
    if not media_type:
        return False
    if media_type in _BINARY_MEDIA_TYPES:
        return True
    if media_type.startswith(_BINARY_MEDIA_PREFIXES):
        return True
    return media_type.startswith(
        (
            "application/vnd.ms-",
            "application/vnd.oasis.opendocument.",
            "application/vnd.openxmlformats-",
        )
    )


def _sanitize_header_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return sanitize_text(value)
    if parsed.scheme.lower() in {"http", "https"} and parsed.hostname:
        return sanitize_url(value)
    return sanitize_text(value)


_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
_HEX_TOKEN_RE = re.compile(r"^[0-9a-fA-F]{32,}$")
_MIXED_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{32,}$")


def _sanitize_path(path: str) -> str:
    if not path:
        return path
    return "/".join(_sanitize_path_segment(segment) for segment in path.split("/"))


def _sanitize_path_segment(segment: str) -> str:
    """Redact path segments that look like identifiers or bearer tokens.

    Query strings are the usual secret carrier, but reset/session tokens also
    appear in paths. UUIDs and long hex/mixed-case values are treated as
    secrets; ordinary slugs are preserved.
    """

    sanitized = sanitize_text(segment)
    if _UUID_RE.fullmatch(segment) or _HEX_TOKEN_RE.fullmatch(segment):
        return REDACTED
    if (
        _MIXED_TOKEN_RE.fullmatch(segment)
        and any(char.isdigit() for char in segment)
        and any(char.isupper() for char in segment)
        and any(char.islower() for char in segment)
    ):
        return REDACTED
    return sanitized


def _sanitize_pairs(pairs: Iterable[tuple[str, str]]) -> str:
    sanitized = [
        (
            sanitize_text(key),
            REDACTED if is_sensitive_key(key) else sanitize_text(value),
        )
        for key, value in pairs
    ]
    if not sanitized:
        return ""
    return urlencode(sanitized, doseq=True, quote_via=quote, safe="[]")
