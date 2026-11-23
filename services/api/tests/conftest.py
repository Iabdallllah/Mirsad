"""Shared API test fixtures."""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app

UNIT_JWT_SECRET = "unit-test-secret-not-a-real-value-0123456789"
INTEGRATION_JWT_SECRET = "integration-test-secret-not-a-real-value-0123456789"
DB_URL = os.environ.get(
    "SUPABASE_DB_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
)


def make_token(sub: str, secret: str, **overrides: object) -> str:
    payload: dict[str, object] = {
        "sub": sub,
        "aud": "authenticated",
        "role": "authenticated",
        "exp": 4102444800,  # 2100-01-01, fixed for determinism
        **overrides,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


@pytest.fixture()
async def unit_app(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[object]:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", UNIT_JWT_SECRET)
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.delenv("SUPABASE_JWKS_URL", raising=False)
    app = create_app()
    async with app.router.lifespan_context(app):
        yield app


@pytest.fixture()
async def unit_client(unit_app: object) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=unit_app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture()
async def integration_app(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[object]:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("SUPABASE_JWT_SECRET", INTEGRATION_JWT_SECRET)
    monkeypatch.delenv("SUPABASE_JWKS_URL", raising=False)
    app = create_app()
    async with app.router.lifespan_context(app):
        yield app


@pytest.fixture()
async def integration_client(integration_app: object) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=integration_app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture()
async def integration_user(integration_app: object) -> AsyncIterator[dict[str, str]]:
    """Create a user directly in auth.users (local harness); bootstrap fires."""
    pool = integration_app.state.pool  # type: ignore[attr-defined]
    user_id = str(uuid.uuid4())
    username = f"api-{uuid.uuid4().hex[:8]}"
    async with pool.acquire() as conn:
        await conn.execute(
            """
            insert into auth.users (
              id, instance_id, aud, role, email,
              raw_app_meta_data, raw_user_meta_data,
              email_confirmed_at, created_at, updated_at
            ) values (
              $1::uuid, '00000000-0000-0000-0000-000000000000',
              'authenticated', 'authenticated', $2,
              '{"provider": "github"}'::jsonb, $3::jsonb, now(), now(), now()
            )
            """,
            user_id,
            f"{username}@users.noreply.github.com",
            f'{{"user_name": "{username}"}}',
        )
        workspace_id = await conn.fetchval(
            "select id from public.workspaces where owner_user_id = $1::uuid", user_id
        )
    yield {
        "user_id": user_id,
        "username": username,
        "workspace_id": str(workspace_id),
        "token": make_token(user_id, INTEGRATION_JWT_SECRET),
    }
