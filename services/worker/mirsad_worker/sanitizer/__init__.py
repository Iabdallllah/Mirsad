"""Deterministic PII/secret sanitizer (Phase 1, plan.md §14.1).

Nothing in this package calls a model or the network. The same rules must run
before evidence is persisted and before any target content is placed in an LLM
prompt (AGENTS.md §7, §8).
"""

from __future__ import annotations

from .core import (
    sanitize_body,
    sanitize_bytes,
    sanitize_data,
    sanitize_for_llm,
    sanitize_form,
    sanitize_header_items,
    sanitize_headers,
    sanitize_text,
    sanitize_url,
)
from .evidence import (
    MAX_EVIDENCE_CHARS,
    sanitize_exchange,
    sanitize_request,
    sanitize_response,
)
from .rules import (
    REDACTED,
    REDACTED_BINARY,
    REDACTED_CARD,
    REDACTED_EMAIL,
    REDACTED_JWT,
    REDACTED_PHONE,
    REDACTED_PRIVATE_KEY,
    is_sensitive_key,
    luhn_valid,
)

__all__ = [
    "MAX_EVIDENCE_CHARS",
    "REDACTED",
    "REDACTED_BINARY",
    "REDACTED_CARD",
    "REDACTED_EMAIL",
    "REDACTED_JWT",
    "REDACTED_PHONE",
    "REDACTED_PRIVATE_KEY",
    "is_sensitive_key",
    "luhn_valid",
    "sanitize_body",
    "sanitize_bytes",
    "sanitize_data",
    "sanitize_exchange",
    "sanitize_for_llm",
    "sanitize_form",
    "sanitize_header_items",
    "sanitize_headers",
    "sanitize_request",
    "sanitize_response",
    "sanitize_text",
    "sanitize_url",
]
