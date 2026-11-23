"""Database access (asyncpg pool).

Privileged paths use the service-role connection string, but every query
that touches workspace data includes workspace_id explicitly — RLS is a
backstop, not the only control (AGENTS.md §5).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI, Request

from app.config import Settings
from app.errors import ApiError


@asynccontextmanager
async def lifespan_pool(app: FastAPI, settings: Settings) -> AsyncIterator[None]:
    pool: asyncpg.Pool | None = None
    if settings.database_url:
        pool = await asyncpg.create_pool(
            settings.database_url, min_size=1, max_size=5, timeout=5.0
        )
    app.state.pool = pool
    try:
        yield
    finally:
        if pool is not None:
            await pool.close()


def get_pool(request: Request) -> asyncpg.Pool:
    pool: asyncpg.Pool | None = getattr(request.app.state, "pool", None)
    if pool is None:
        raise ApiError(503, "DEPENDENCY_UNAVAILABLE", "Database is not configured.")
    return pool
