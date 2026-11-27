"""Sanitized HTTP exchange records for evidence storage (AGENTS.md §7).

Findings may keep a sanitized proof-of-concept, but raw request/response
traffic is never stored (plan.md §4.2). These helpers produce a compact,
JSON-serializable record that is safe for the ``findings.evidence`` jsonb
column (≤ 50 KB) and for LLM prompts.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from typing import Any

from .core import sanitize_body, sanitize_header_items, sanitize_url

MAX_EVIDENCE_CHARS = 50_000
MAX_BODY_CHARS = 16_000
MAX_HEADER_VALUE_CHARS = 2_048
MAX_URL_CHARS = 8_192
MAX_HEADERS = 100
TRUNCATED_MARKER = "[TRUNCATED]"

HeaderSource = Mapping[str, str] | Iterable[tuple[str, str]]


def sanitize_request(
    *,
    method: str,
    url: str,
    headers: HeaderSource | None = None,
    body: bytes | str | None = None,
) -> dict[str, Any]:
    """Return a safe evidence record for one request."""

    header_items = list(_header_items(headers))
    return {
        "method": _clip(method.upper(), 32),
        "url": _clip(sanitize_url(url), MAX_URL_CHARS),
        "headers": _sanitize_evidence_headers(header_items),
        "body": _sanitize_evidence_body(body, _content_type(header_items)),
    }


def sanitize_response(
    *,
    status_code: int,
    headers: HeaderSource | None = None,
    body: bytes | str | None = None,
) -> dict[str, Any]:
    """Return a safe evidence record for one response."""

    header_items = list(_header_items(headers))
    return {
        "status_code": status_code,
        "headers": _sanitize_evidence_headers(header_items),
        "body": _sanitize_evidence_body(body, _content_type(header_items)),
    }


def sanitize_exchange(
    *,
    method: str,
    url: str,
    request_headers: HeaderSource | None = None,
    request_body: bytes | str | None = None,
    status_code: int,
    response_headers: HeaderSource | None = None,
    response_body: bytes | str | None = None,
) -> dict[str, Any]:
    """Return a safe request/response pair capped to the evidence size budget."""

    document = {
        "request": sanitize_request(
            method=method,
            url=url,
            headers=request_headers,
            body=request_body,
        ),
        "response": sanitize_response(
            status_code=status_code,
            headers=response_headers,
            body=response_body,
        ),
    }

    if _serialized_length(document) <= MAX_EVIDENCE_CHARS:
        return document

    # Re-clip already-sanitized bodies until the document fits. Clipping after
    # sanitization cannot expose an original value.
    for limit in (MAX_BODY_CHARS // 2, MAX_BODY_CHARS // 8, 512, 0):
        document["request"]["body"] = _clip(document["request"]["body"], limit)
        document["response"]["body"] = _clip(document["response"]["body"], limit)
        if _serialized_length(document) <= MAX_EVIDENCE_CHARS:
            return document

    document["request"]["headers"] = []
    document["response"]["headers"] = []
    document["request"]["url"] = TRUNCATED_MARKER
    return document


def _header_items(headers: HeaderSource | None) -> Iterable[tuple[str, str]]:
    if headers is None:
        return ()
    if isinstance(headers, Mapping):
        return headers.items()
    return headers


def _content_type(headers: Iterable[tuple[str, str]]) -> str | None:
    for name, value in headers:
        if name.lower() == "content-type":
            return value
    return None


def _sanitize_evidence_headers(headers: list[tuple[str, str]]) -> list[dict[str, str]]:
    sanitized = sanitize_header_items(headers[:MAX_HEADERS])
    return [
        {"name": name, "value": _clip(value, MAX_HEADER_VALUE_CHARS)}
        for name, value in sanitized
    ]


def _sanitize_evidence_body(body: bytes | str | None, content_type: str | None) -> str:
    if body is None:
        return ""
    return _clip(sanitize_body(body, content_type), MAX_BODY_CHARS)


def _clip(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    if limit <= 0:
        return TRUNCATED_MARKER
    return f"{value[:limit]}{TRUNCATED_MARKER}"


def _serialized_length(value: Any) -> int:
    return len(
        json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    )
