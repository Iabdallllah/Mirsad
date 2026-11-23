"""Error envelope (plan.md §10.1).

Every error carries a request_id; bodies never contain secrets or stack
traces. Codes are stable strings consumed by web/mobile clients.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    """Domain error mapped to the §10.1 envelope."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}


_STATUS_CODES: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHENTICATED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    500: "INTERNAL",
    503: "DEPENDENCY_UNAVAILABLE",
}


def _envelope(
    request: Request, code: str, message: str, details: dict[str, Any] | None = None
) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
            "request_id": getattr(request.state, "request_id", "unknown"),
        }
    }


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(request, exc.code, exc.message, exc.details),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        code = _STATUS_CODES.get(exc.status_code, "INTERNAL")
        message = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return JSONResponse(
            status_code=exc.status_code, content=_envelope(request, code, message)
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Pydantic messages only; never echo raw input values that could
        # carry secrets (AGENTS.md §4).
        details = {
            "fields": [
                {"loc": [str(part) for part in err["loc"]], "type": err["type"]}
                for err in exc.errors()
            ]
        }
        return JSONResponse(
            status_code=422,
            content=_envelope(request, "VALIDATION_ERROR", "Request validation failed.", details),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        # Log server-side with the request id; respond without internals.
        request_id = getattr(request.state, "request_id", "unknown")
        print(f"[{request_id}] unhandled error: {type(exc).__name__}")  # noqa: T201
        return JSONResponse(
            status_code=500,
            content=_envelope(request, "INTERNAL", "An internal error occurred."),
        )
