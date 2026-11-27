"""Canary leak suite: no planted secret may survive sanitization.

Each canary is unique, so a single surviving value is unambiguous evidence of
a sanitizer gap. The suite checks every storage/LLM boundary helper, not just
``sanitize_text`` (plan.md §14.1, AGENTS.md §7).
"""

from __future__ import annotations

import json

import pytest

from mirsad_worker.sanitizer import (
    MAX_EVIDENCE_CHARS,
    REDACTED_BINARY,
    sanitize_body,
    sanitize_bytes,
    sanitize_data,
    sanitize_exchange,
    sanitize_for_llm,
    sanitize_form,
    sanitize_headers,
    sanitize_text,
    sanitize_url,
)

DOMAIN = "app.example.com"

CANARIES = {
    "password": "CANARY_PASSWORD_7f3a9c1d",
    "cookie": "CANARY_COOKIE_2b8e4f6a",
    "bearer": "CANARY_BEARER_9d1c3e5f",
    "jwt": (
        "eyJhbGciOiJIUzI1NiJ9."
        "eyJzdWIiOiJDQU5BUllfSldUXzdmM2E5YzFkIn0."
        "c2lnbmF0dXJl"
    ),
    "api": "sk_live_CANARYAPI9f3a7c1e5b2d",
    "github": "ghp_CANARYGITHUB9f3a7c1e5b2d4a6c",
    "aws": "AKIA9F3A7C1E5B2D4A6C",
    "email": "canary.email.7f3a9c1d@example.com",
    "phone": "+15550123456",
    "card": "4111111111111111",
    "private_key": "CANARY_PRIVATE_KEY_5e2d4c6b",
    "query": "CANARY_QUERY_1a2b3c4d",
    "form": "CANARY_FORM_8e9f0a1b",
    "json": "CANARY_JSON_3c4d5e6f",
}


def _text_payload() -> str:
    return (
        f"password={CANARIES['password']}\n"
        f"Authorization: Bearer {CANARIES['bearer']}\n"
        f"Cookie: session={CANARIES['cookie']}\n"
        f"jwt_payload {CANARIES['jwt']}\n"
        f"api_key: {CANARIES['api']}\n"
        f"github={CANARIES['github']}\n"
        f"aws={CANARIES['aws']}\n"
        f"contact {CANARIES['email']}\n"
        f"phone={CANARIES['phone']}\n"
        f"card={CANARIES['card']}\n"
        "-----BEGIN RSA PRIVATE KEY-----\n"
        f"{CANARIES['private_key']}\n"
        "-----END RSA PRIVATE KEY-----\n"
    )


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {CANARIES['bearer']}",
        "Cookie": f"session={CANARIES['cookie']}",
        "Set-Cookie": f"token={CANARIES['cookie']}; HttpOnly",
        "X-Api-Key": CANARIES["api"],
        "X-Debug": f"token={CANARIES['query']}",
        "Content-Type": "application/json",
    }


def _url() -> str:
    return (
        f"https://{DOMAIN}/path?token={CANARIES['query']}"
        f"&email={CANARIES['email']}"
        f"&card={CANARIES['card']}"
        f"&phone={CANARIES['phone']}"
        f"&q=hello"
    )


def _json_payload() -> dict[str, object]:
    return {
        "user": "alice",
        "password": CANARIES["json"],
        "access_token": CANARIES["jwt"],
        "nested": {
            "api_key": CANARIES["api"],
            "email": CANARIES["email"],
            "items": [{"secret": CANARIES["cookie"]}],
        },
    }


def _form_payload() -> str:
    return (
        "username=alice"
        f"&password={CANARIES['form']}"
        f"&api_key={CANARIES['api']}"
        "&next=%2Fhome"
    )


def _outputs() -> dict[str, str]:
    json_payload = _json_payload()
    exchange = sanitize_exchange(
        method="POST",
        url=_url(),
        request_headers=_headers(),
        request_body=json.dumps(json_payload),
        status_code=200,
        response_headers={
            "Set-Cookie": f"session={CANARIES['cookie']}",
            "Content-Type": "application/json",
        },
        response_body=json.dumps(
            {
                "ok": True,
                "password": CANARIES["password"],
                "contact": CANARIES["email"],
            }
        ),
    )

    return {
        "text": sanitize_text(_text_payload()),
        "headers": json.dumps(sanitize_headers(_headers())),
        "url": sanitize_url(_url()),
        "json": json.dumps(sanitize_data(json_payload)),
        "json_body": sanitize_body(json.dumps(json_payload), "application/json"),
        "form": sanitize_form(_form_payload()),
        "exchange": json.dumps(exchange),
        "llm": json.dumps(sanitize_for_llm({"body": _text_payload(), "json": json_payload})),
    }


def test_zero_canary_survival_across_all_boundaries() -> None:
    outputs = _outputs()
    survivors = [
        (canary_name, output_name)
        for output_name, output in outputs.items()
        for canary_name, canary in CANARIES.items()
        if canary in output
    ]

    assert survivors == []
    total_checks = len(outputs) * len(CANARIES)
    survival_rate = len(survivors) / total_checks
    assert survival_rate == 0.0


def test_canary_in_private_key_is_removed() -> None:
    output = sanitize_text(_text_payload())
    assert CANARIES["private_key"] not in output
    assert "PRIVATE KEY" not in output


def test_canary_in_binary_body_is_removed() -> None:
    body = b"\xff\xfe" + CANARIES["password"].encode()
    assert sanitize_bytes(body) == REDACTED_BINARY
    assert sanitize_body(body, "application/octet-stream") == REDACTED_BINARY


def test_canary_in_huge_evidence_body_is_removed_before_truncation() -> None:
    canary = CANARIES["password"]
    body = f"password={canary} " + ("A" * 200_000) + f" password={canary}"
    exchange = sanitize_exchange(
        method="POST",
        url=f"https://{DOMAIN}/login",
        request_headers={"Content-Type": "text/plain"},
        request_body=body,
        status_code=200,
        response_headers={"Content-Type": "text/plain"},
        response_body=body,
    )
    serialized = json.dumps(exchange)
    assert canary not in serialized
    assert len(serialized) <= MAX_EVIDENCE_CHARS


def test_canary_in_userinfo_is_removed() -> None:
    url = f"https://user:{CANARIES['password']}@{DOMAIN}/path?q=1"
    sanitized = sanitize_url(url)
    assert CANARIES["password"] not in sanitized
    assert sanitized == f"https://{DOMAIN}/path?q=1"


def test_canary_in_header_assignment_is_removed() -> None:
    headers = {"X-Debug": f"token={CANARIES['query']}"}
    sanitized = sanitize_headers(headers)
    assert CANARIES["query"] not in sanitized["X-Debug"]


def test_canary_in_cookie_free_text_is_removed() -> None:
    sanitized = sanitize_text(
        f"Cookie: theme=dark; session={CANARIES['cookie']}; lang=en"
    )
    assert CANARIES["cookie"] not in sanitized


def test_sanitized_output_is_json_serializable() -> None:
    outputs = _outputs()
    for value in outputs.values():
        assert isinstance(value, str)
        json.dumps(value)


@pytest.mark.parametrize("canary_name", list(CANARIES))
def test_each_canary_is_present_in_at_least_one_raw_input(canary_name: str) -> None:
    """Guard against a canary silently dropping out of the fixture."""

    canary = CANARIES[canary_name]
    raw = "\n".join(
        [
            _text_payload(),
            json.dumps(_headers()),
            _url(),
            json.dumps(_json_payload()),
            _form_payload(),
        ]
    )
    assert canary in raw
