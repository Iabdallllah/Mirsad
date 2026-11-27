"""Unit tests for the deterministic sanitizer (AGENTS.md §7, plan.md §14.1)."""

from __future__ import annotations

import json

import pytest

from mirsad_worker.sanitizer import (
    MAX_EVIDENCE_CHARS,
    REDACTED,
    REDACTED_BINARY,
    REDACTED_CARD,
    REDACTED_EMAIL,
    REDACTED_JWT,
    REDACTED_PHONE,
    REDACTED_PRIVATE_KEY,
    is_sensitive_key,
    luhn_valid,
    sanitize_body,
    sanitize_bytes,
    sanitize_data,
    sanitize_exchange,
    sanitize_for_llm,
    sanitize_form,
    sanitize_header_items,
    sanitize_headers,
    sanitize_text,
    sanitize_url,
)

CANARY = "CANARY_9f3a7c1e"
API_CANARY = "9f3a7c1e5b2d4a6c8e0f"
PHONE_CANARY = "+15550123456"
AWS_CANARY = "AKIA9F3A7C1E5B2D4A6C"
CARD = "4111 1111 1111 1111"
JWT = (
    "eyJhbGciOiJIUzI1NiJ9."
    "eyJzdWIiOiJDQU5BUllfOWYzYTdjMWUifQ."
    "c2lnbmF0dXJl"
)


@pytest.mark.parametrize(
    "key",
    [
        "Authorization",
        "authorization",
        "Proxy-Authorization",
        "Cookie",
        "Set-Cookie",
        "X-Api-Key",
        "X-Auth-Token",
        "X-CSRF-Token",
        "password",
        "passwd",
        "client_secret",
        "clientSecret",
        "accessToken",
        "refresh_token",
        "private_key",
        "card_number",
        "cvv",
        "ssn",
        "session_id",
        "auth",
        "auth_code",
        "oauth_code",
        "passcode",
        "otp",
        "pin",
        "database_url",
        "connection_string",
        "webhook_secret",
        "encryption_key",
        "x_key",
    ],
)
def test_sensitive_keys(key: str) -> None:
    assert is_sensitive_key(key)


@pytest.mark.parametrize(
    "key",
    ["Content-Type", "User-Agent", "Accept", "Server", "Location", "username", "author"],
)
def test_non_sensitive_keys(key: str) -> None:
    assert not is_sensitive_key(key)


def test_luhn() -> None:
    assert luhn_valid("4111111111111111")
    assert luhn_valid("5500005555555559")
    assert not luhn_valid("4111111111111112")
    assert not luhn_valid("1234")


def test_text_redacts_credentials_and_pii() -> None:
    payload = (
        f"password={CANARY}\n"
        f"Authorization: Bearer {CANARY}\n"
        f"Cookie: session={CANARY}\n"
        f"api_key: sk_live_{API_CANARY}\n"
        f"jwt_payload {JWT}\n"
        f"email=user_{CANARY}@example.com\n"
        f"phone={PHONE_CANARY}\n"
        f"card={CARD}\n"
        f"aws={AWS_CANARY}\n"
        f"github=ghp_{API_CANARY}abcdefghijklmnop\n"
    )
    sanitized = sanitize_text(payload)
    for secret in (CANARY, API_CANARY, AWS_CANARY, JWT, CARD, PHONE_CANARY):
        assert secret not in sanitized
    assert "sk_live_" not in sanitized
    assert "AKIA" not in sanitized
    assert "ghp_" not in sanitized
    assert REDACTED in sanitized
    assert REDACTED_JWT in sanitized
    assert REDACTED_CARD in sanitized
    assert REDACTED_EMAIL in sanitized
    assert REDACTED_PHONE in sanitized


def test_private_key_block_is_removed() -> None:
    payload = (
        "before\n"
        "-----BEGIN RSA PRIVATE KEY-----\n"
        f"{CANARY}\n"
        "-----END RSA PRIVATE KEY-----\n"
        "after"
    )
    sanitized = sanitize_text(payload)
    assert CANARY not in sanitized
    assert REDACTED_PRIVATE_KEY in sanitized
    assert "before" in sanitized
    assert "after" in sanitized


def test_structured_values_of_sensitive_keys_are_removed() -> None:
    payload = (
        '{"tokens": ["TOKEN_ONE_CANARY", "TOKEN_TWO_CANARY"], '
        '"session": {"id": "SESSION_CANARY"}, "ok": true}'
    )
    sanitized = sanitize_text(payload)
    assert "TOKEN_ONE_CANARY" not in sanitized
    assert "TOKEN_TWO_CANARY" not in sanitized
    assert "SESSION_CANARY" not in sanitized


def test_sensitive_key_with_spaces_is_removed() -> None:
    sanitized = sanitize_text("api key=SPACE_KEY_CANARY\nnext=1")
    assert "SPACE_KEY_CANARY" not in sanitized
    assert "next=1" in sanitized


def test_credential_urls_and_auth_codes_are_removed() -> None:
    payload = (
        "DATABASE_URL=postgres://user:pass@db.internal/app\n"
        "auth_code=AUTH_CODE_CANARY\n"
        "x_key=X_KEY_CANARY\n"
        "next=1"
    )
    sanitized = sanitize_text(payload)
    assert "postgres://" not in sanitized
    assert "AUTH_CODE_CANARY" not in sanitized
    assert "X_KEY_CANARY" not in sanitized
    assert "next=1" in sanitized


def test_text_redaction_is_idempotent() -> None:
    payload = f"password={CANARY}&email=user@example.com&card={CARD}"
    once = sanitize_text(payload)
    assert sanitize_text(once) == once


def test_benign_text_is_preserved() -> None:
    payload = (
        "GET /health HTTP/1.1\n"
        "Server: nginx/1.24.0\n"
        "Content-Type: application/json\n"
        '{"status":"ok","version":"1.2.3","user":"alice"}'
    )
    assert sanitize_text(payload) == payload


def test_invalid_card_number_is_preserved() -> None:
    payload = "reference=4111 1111 1111 1112"
    assert sanitize_text(payload) == payload


def test_url_drops_userinfo_and_redacts_query() -> None:
    sanitized = sanitize_url(
        f"https://user:{CANARY}@app.example.com/path?token={CANARY}&q=hello#frag"
    )
    assert CANARY not in sanitized
    assert "user" not in sanitized.split("app.example.com", 1)[0]
    assert "q=hello" in sanitized
    assert "#frag" not in sanitized


def test_url_redacts_token_like_path_segments() -> None:
    uuid = "550e8400-e29b-41d4-a716-446655440000"
    hex_token = "abcdef0123456789abcdef0123456789"
    mixed_token = "AbCdEf0123456789AbCdEf0123456789"
    sanitized = sanitize_url(
        f"https://app.example.com/reset/{uuid}/{hex_token}/{mixed_token}/done"
    )
    assert uuid not in sanitized
    assert hex_token not in sanitized
    assert mixed_token not in sanitized
    assert sanitized.endswith("/done")


def test_url_preserves_ordinary_path_slugs() -> None:
    path = "/blog/this-is-a-long-but-harmless-page-slug"
    assert sanitize_url(f"https://app.example.com{path}").endswith(path)


def test_headers_redact_sensitive_names_and_values() -> None:
    headers = {
        "Authorization": f"Bearer {CANARY}",
        "Cookie": f"session={CANARY}",
        "Set-Cookie": f"token={CANARY}; HttpOnly",
        "X-Api-Key": CANARY,
        "X-Request-Id": f"token={CANARY}",
        "Content-Type": "application/json",
    }
    sanitized = sanitize_headers(headers)
    assert sanitized["Authorization"] == REDACTED
    assert sanitized["Cookie"] == REDACTED
    assert sanitized["Set-Cookie"] == REDACTED
    assert sanitized["X-Api-Key"] == REDACTED
    assert sanitized["Content-Type"] == "application/json"
    assert CANARY not in sanitized["X-Request-Id"]


def test_duplicate_headers_are_preserved() -> None:
    headers = [("Set-Cookie", f"a={CANARY}"), ("Set-Cookie", f"b={CANARY}")]
    sanitized = sanitize_header_items(headers)
    assert sanitized == [("Set-Cookie", REDACTED), ("Set-Cookie", REDACTED)]


def test_nested_data_is_sanitized_without_losing_shape() -> None:
    payload = {
        "user": {
            "name": "alice",
            "password": CANARY,
            "contact": {"email": f"{CANARY}@example.com"},
        },
        "items": [{"token": CANARY}, {"safe": "value"}],
        "ok": True,
        "count": 3,
    }
    sanitized = sanitize_data(payload)
    assert sanitized["user"]["name"] == "alice"
    assert sanitized["user"]["password"] == REDACTED
    assert sanitized["user"]["contact"]["email"] == REDACTED_EMAIL
    assert sanitized["items"][0]["token"] == REDACTED
    assert sanitized["items"][1]["safe"] == "value"
    assert sanitized["ok"] is True
    assert sanitized["count"] == 3
    assert CANARY not in json.dumps(sanitized)


def test_form_body_is_sanitized() -> None:
    body = f"username=alice&password={CANARY}&api_key={CANARY}&next=%2Fhome"
    sanitized = sanitize_form(body)
    assert CANARY not in sanitized
    assert "username=alice" in sanitized
    assert "next=%2Fhome" in sanitized


def test_json_body_is_sanitized() -> None:
    body = json.dumps({"user": "alice", "password": CANARY, "nested": {"token": CANARY}})
    sanitized = sanitize_body(body, "application/json; charset=utf-8")
    assert CANARY not in sanitized
    parsed = json.loads(sanitized)
    assert parsed["user"] == "alice"
    assert parsed["password"] == REDACTED
    assert parsed["nested"]["token"] == REDACTED


def test_binary_body_is_dropped() -> None:
    assert sanitize_bytes(b"\xff\xfe" + CANARY.encode()) == REDACTED_BINARY
    assert sanitize_bytes(b"text\x00" + CANARY.encode()) == REDACTED_BINARY
    assert sanitize_body(b"\xff\xfe" + CANARY.encode(), "application/octet-stream") == (
        REDACTED_BINARY
    )
    assert sanitize_body(
        f"password={CANARY}".encode(),
        "application/octet-stream",
    ) == REDACTED_BINARY
    assert sanitize_body(
        f"password={CANARY}",
        "multipart/form-data; boundary=xyz",
    ) == REDACTED_BINARY
    assert sanitize_body(f"password={CANARY}\x00", "text/plain") == REDACTED_BINARY


def test_for_llm_marks_content_untrusted() -> None:
    envelope = sanitize_for_llm({"body": f"password={CANARY}", "status": 200})
    assert envelope["trust"] == "untrusted_target_data"
    assert CANARY not in json.dumps(envelope)
    assert envelope["data"]["status"] == 200


def test_exchange_is_sanitized_and_size_capped() -> None:
    exchange = sanitize_exchange(
        method="POST",
        url=f"https://app.example.com/login?token={CANARY}",
        request_headers={"Authorization": f"Bearer {CANARY}", "Content-Type": "application/json"},
        request_body=json.dumps({"password": CANARY, "padding": "A" * 100_000}),
        status_code=200,
        response_headers={"Set-Cookie": f"session={CANARY}", "Content-Type": "text/plain"},
        response_body=f"ok password={CANARY} " + "B" * 100_000,
    )
    serialized = json.dumps(exchange)
    assert CANARY not in serialized
    assert len(serialized) <= MAX_EVIDENCE_CHARS
    assert exchange["request"]["method"] == "POST"
    assert exchange["response"]["status_code"] == 200


def test_exchange_header_count_is_capped() -> None:
    headers = [(f"X-Header-{index}", "value") for index in range(200)]
    exchange = sanitize_exchange(
        method="GET",
        url="https://app.example.com/",
        request_headers=headers,
        status_code=200,
        response_headers=headers,
    )
    assert len(exchange["request"]["headers"]) == 100
    assert len(exchange["response"]["headers"]) == 100


def test_exchange_huge_url_is_capped() -> None:
    exchange = sanitize_exchange(
        method="GET",
        url="https://app.example.com/" + ("a" * 200_000),
        status_code=200,
    )
    serialized = json.dumps(exchange).encode("utf-8")
    assert len(serialized) <= MAX_EVIDENCE_CHARS
