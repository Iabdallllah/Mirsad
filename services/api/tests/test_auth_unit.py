"""JWT validation unit tests — hermetic, no network, no real secrets."""

from __future__ import annotations

import time

import jwt
import pytest
from conftest import UNIT_JWT_SECRET, make_token
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.auth import JwtValidator
from app.config import Settings
from app.errors import ApiError


def _validator(**env: str) -> JwtValidator:
    settings = Settings(
        supabase_jwt_secret=env.get("secret", UNIT_JWT_SECRET),
        supabase_jwks_url=env.get("jwks_url"),
        _env_file=None,  # type: ignore[call-arg]  # pydantic-settings runtime kwarg
    )
    return JwtValidator(settings)


def test_valid_hs256_token() -> None:
    token = make_token("user-1", UNIT_JWT_SECRET)
    payload = _validator().validate(token)
    assert payload["sub"] == "user-1"


def test_expired_token_rejected() -> None:
    token = make_token("user-1", UNIT_JWT_SECRET, exp=int(time.time()) - 10)
    with pytest.raises(ApiError) as exc:
        _validator().validate(token)
    assert exc.value.status_code == 401


def test_wrong_audience_rejected() -> None:
    token = make_token("user-1", UNIT_JWT_SECRET, aud="service_role")
    with pytest.raises(ApiError) as exc:
        _validator().validate(token)
    assert exc.value.status_code == 401


def test_wrong_signature_rejected() -> None:
    token = make_token("user-1", "attacker-secret-not-the-real-one-0123456789")
    with pytest.raises(ApiError) as exc:
        _validator().validate(token)
    assert exc.value.status_code == 401


def test_alg_none_rejected() -> None:
    token = jwt.encode({"sub": "user-1", "aud": "authenticated"}, key="", algorithm="none")
    with pytest.raises(ApiError) as exc:
        _validator().validate(token)
    assert exc.value.status_code == 401


def test_missing_sub_rejected() -> None:
    token = jwt.encode(
        {"aud": "authenticated", "exp": 4102444800}, UNIT_JWT_SECRET, algorithm="HS256"
    )
    with pytest.raises(ApiError) as exc:
        _validator().validate(token)
    assert exc.value.status_code == 401


def test_unconfigured_auth_is_503_not_silent_pass() -> None:
    settings = Settings(
        supabase_jwt_secret=None, supabase_jwks_url=None, _env_file=None  # type: ignore[call-arg]
    )
    with pytest.raises(ApiError) as exc:
        JwtValidator(settings).validate(make_token("user-1", UNIT_JWT_SECRET))
    assert exc.value.status_code == 503


def test_jwks_path_rejects_hs256_confusion(monkeypatch: pytest.MonkeyPatch) -> None:
    """With JWKS configured, an HS256 token signed with the public key must fail."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )

    class FakeJWKClient:
        def __init__(self, url: str, cache_keys: bool = True) -> None:
            pass

        def get_signing_key_from_jwt(self, token: str) -> object:
            class Key:
                key = private_key.public_key()

            return Key()

    monkeypatch.setattr(jwt, "PyJWKClient", FakeJWKClient)
    validator = _validator(jwks_url="https://example.invalid/jwks.json")

    es256_token = jwt.encode(
        {"sub": "user-1", "aud": "authenticated", "exp": 4102444800},
        private_key,
        algorithm="ES256",
    )
    assert validator.validate(es256_token)["sub"] == "user-1"

    confusion_token = _forge_hs256_with_public_key(
        {"sub": "attacker", "aud": "authenticated", "exp": 4102444800}, public_pem
    )
    with pytest.raises(ApiError) as exc:
        validator.validate(confusion_token)
    assert exc.value.status_code == 401


def _forge_hs256_with_public_key(payload: dict[str, object], public_pem: str) -> str:
    """Craft the classic algorithm-confusion token without PyJWT's safe encoder."""
    import base64
    import hashlib
    import hmac
    import json

    def b64(raw: bytes) -> str:
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    header = {"alg": "HS256", "typ": "JWT"}
    signing_input = f"{b64(json.dumps(header).encode())}.{b64(json.dumps(payload).encode())}"
    signature = hmac.new(
        public_pem.encode(), signing_input.encode(), hashlib.sha256
    ).digest()
    return f"{signing_input}.{b64(signature)}"


async def test_me_requires_bearer(unit_client: AsyncClient) -> None:
    response = await unit_client.get("/api/v1/me")
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "UNAUTHENTICATED"
    assert body["error"]["request_id"]


async def test_me_rejects_garbage_token(unit_client: AsyncClient) -> None:
    response = await unit_client.get(
        "/api/v1/me", headers={"Authorization": "Bearer not-a-jwt"}
    )
    assert response.status_code == 401


async def test_docs_disabled_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", UNIT_JWT_SECRET)
    monkeypatch.setenv("DATABASE_URL", "")
    from app.main import create_app

    app: FastAPI = create_app()
    assert app.openapi_url is None
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            assert (await client.get("/openapi.json")).status_code == 404
