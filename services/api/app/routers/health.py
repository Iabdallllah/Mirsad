"""Liveness/readiness (plan.md §10.2, §15).

Mounted at the root: monitoring probes /health and /ready per plan.md §17.2.
(The §10.2 table lists them under the /api/v1 base — flagged inconsistency;
root-level matches the monitoring/deployment sections.)
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.db import get_pool
from app.errors import ApiError
from app.schemas import HealthOut, ReadyChecks, ReadyOut

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOut)
async def health(request: Request) -> HealthOut:
    return HealthOut(app_env=request.app.state.settings.app_env)


@router.get("/ready", response_model=ReadyOut)
async def ready(request: Request) -> JSONResponse:
    try:
        pool = get_pool(request)
    except ApiError:
        body = ReadyOut(status="not_ready", checks=ReadyChecks(database=False, queue=False))
        return JSONResponse(status_code=503, content=body.model_dump(mode="json"))

    database_ok = False
    queue_ok = False
    try:
        async with pool.acquire() as conn:
            await conn.fetchval("select 1")
            database_ok = True
            # Queue table exists and is queryable (worker consumption is Phase 1).
            await conn.fetchval("select count(*) from public.scan_jobs where status = 'queued'")
            queue_ok = True
    except Exception as exc:  # noqa: BLE001 - readiness must degrade, not crash
        # Log the failure class only: no stack, connection string, or row data.
        logger.warning("readiness dependency check failed: %s", type(exc).__name__)

    body = ReadyOut(
        status="ok" if database_ok and queue_ok else "not_ready",
        checks=ReadyChecks(database=database_ok, queue=queue_ok),
    )
    return JSONResponse(
        status_code=200 if body.status == "ok" else 503, content=body.model_dump(mode="json")
    )
