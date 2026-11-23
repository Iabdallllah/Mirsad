"""Integration tests against Supabase local (schema + bootstrap + /me + /ready).

Run: supabase start && supabase db reset, then
     uv run pytest -m integration
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


async def test_ready_with_database(integration_client: AsyncClient) -> None:
    response = await integration_client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"] == {"database": True, "queue": True}
    assert body["worker"] == "not_deployed"


async def test_me_returns_workspace_and_beta_usage(
    integration_client: AsyncClient, integration_user: dict[str, str]
) -> None:
    response = await integration_client.get(
        "/api/v1/me", headers={"Authorization": f"Bearer {integration_user['token']}"}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["user"]["id"] == integration_user["user_id"]
    assert body["user"]["github_username"] == integration_user["username"]
    assert body["workspace"]["id"] == integration_user["workspace_id"]
    assert body["workspace"]["plan"] == "beta"
    assert body["workspace"]["role"] == "owner"
    assert body["usage"]["domains_used"] == 0
    assert body["usage"]["domains_limit"] == 2
    assert body["usage"]["scans_used"] == 0
    assert body["usage"]["scans_per_month"] == 5


async def test_me_is_self_scoped(
    integration_client: AsyncClient,
    integration_user: dict[str, str],
    integration_app: object,
) -> None:
    """A second user's token must resolve to their own workspace, never the first's."""
    import uuid

    from conftest import INTEGRATION_JWT_SECRET, make_token

    pool = integration_app.state.pool  # type: ignore[attr-defined]
    other_id = str(uuid.uuid4())
    async with pool.acquire() as conn:
        await conn.execute(
            """
            insert into auth.users (
              id, instance_id, aud, role, email, raw_app_meta_data, raw_user_meta_data,
              email_confirmed_at, created_at, updated_at
            ) values (
              $1::uuid, '00000000-0000-0000-0000-000000000000',
              'authenticated', 'authenticated', $2,
              '{"provider": "github"}'::jsonb, '{"user_name": "other"}'::jsonb,
              now(), now(), now()
            )
            """,
            other_id,
            f"other-{uuid.uuid4().hex[:8]}@users.noreply.github.com",
        )
        other_ws = await conn.fetchval(
            "select id from public.workspaces where owner_user_id = $1::uuid", other_id
        )

    response = await integration_client.get(
        "/api/v1/me",
        headers={"Authorization": f"Bearer {make_token(other_id, INTEGRATION_JWT_SECRET)}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["workspace"]["id"] == str(other_ws)
    assert body["workspace"]["id"] != integration_user["workspace_id"]


async def test_me_unknown_user_404(
    integration_client: AsyncClient,
) -> None:
    import uuid

    from conftest import INTEGRATION_JWT_SECRET, make_token

    token = make_token(str(uuid.uuid4()), INTEGRATION_JWT_SECRET)
    response = await integration_client.get(
        "/api/v1/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
