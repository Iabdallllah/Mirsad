"""Error envelope + request id + health (plan.md §10.1)."""

from __future__ import annotations

from httpx import AsyncClient


async def test_health_no_auth(unit_client: AsyncClient) -> None:
    response = await unit_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["x-request-id"]


async def test_request_id_propagated(unit_client: AsyncClient) -> None:
    response = await unit_client.get("/health", headers={"x-request-id": "req-abc-123"})
    assert response.headers["x-request-id"] == "req-abc-123"


async def test_unknown_route_envelope(unit_client: AsyncClient) -> None:
    response = await unit_client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert set(body["error"]) == {"code", "message", "details", "request_id"}
    assert body["error"]["code"] == "NOT_FOUND"


async def test_ready_without_db_is_503(unit_client: AsyncClient) -> None:
    response = await unit_client.get("/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["checks"]["database"] is False
    assert body["worker"] == "not_deployed"


async def test_me_valid_token_without_db_is_503(unit_client: AsyncClient) -> None:
    from conftest import UNIT_JWT_SECRET, make_token

    token = make_token("user-1", UNIT_JWT_SECRET)
    response = await unit_client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "DEPENDENCY_UNAVAILABLE"


async def test_error_body_has_no_stack_trace(unit_client: AsyncClient) -> None:
    response = await unit_client.get("/api/v1/does-not-exist")
    text = response.text
    assert "Traceback" not in text
    assert "File \"" not in text
