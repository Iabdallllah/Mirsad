"""Mirsad FastAPI application (Phase 0 — Foundation).

Scope for this milestone: health/readiness, Supabase JWT validation, GET /me,
request-ID error envelope. Domain/scan/finding/webhook endpoints land in
later phases (plan.md §3.2) — nothing here bypasses future egress/sanitizer
controls because no outbound scanning exists yet.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response

from app.auth import JwtValidator
from app.config import get_settings
from app.db import lifespan_pool
from app.errors import register_error_handlers
from app.routers import health, me


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.settings = settings
        app.state.jwt_validator = JwtValidator(settings)
        async with lifespan_pool(app, settings):
            yield

    app = FastAPI(
        title="Mirsad API",
        version="0.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.app_env != "production" else None,
    )
    app.state.settings = settings

    @app.middleware("http")
    async def request_id_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response

    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(me.router)
    return app


app = create_app()
