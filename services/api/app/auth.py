"""Supabase JWT validation (plan.md §9.2).

FastAPI validates the Supabase access token on every authenticated request:
JWKS (asymmetric) when SUPABASE_JWKS_URL is set, otherwise the HS256 project
secret. The client-supplied token is the only identity input; workspace
ownership is resolved server-side from the database, never from the client.
"""

from __future__ import annotations

from typing import Any

import jwt
from fastapi import Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings
from app.errors import ApiError

_bearer = HTTPBearer(auto_error=False)

_ALLOWED_ASYMMETRIC = ["RS256", "ES256"]
_AUDIENCE = "authenticated"


class JwtValidator:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._jwks_client: jwt.PyJWKClient | None = None
        if settings.supabase_jwks_url:
            self._jwks_client = jwt.PyJWKClient(settings.supabase_jwks_url, cache_keys=True)

    def validate(self, token: str) -> dict[str, Any]:
        try:
            if self._jwks_client is not None:
                key = self._jwks_client.get_signing_key_from_jwt(token).key
                payload: dict[str, Any] = jwt.decode(
                    token,
                    key,
                    algorithms=_ALLOWED_ASYMMETRIC,
                    audience=_AUDIENCE,
                )
            elif self._settings.supabase_jwt_secret:
                payload = jwt.decode(
                    token,
                    self._settings.supabase_jwt_secret,
                    algorithms=["HS256"],
                    audience=_AUDIENCE,
                )
            else:
                raise ApiError(
                    503,
                    "DEPENDENCY_UNAVAILABLE",
                    "Authentication is not configured on this deployment.",
                )
        except jwt.PyJWTError as exc:
            raise ApiError(401, "UNAUTHENTICATED", "Invalid or expired access token.") from exc

        sub = payload.get("sub")
        if not isinstance(sub, str) or not sub:
            raise ApiError(401, "UNAUTHENTICATED", "Invalid or expired access token.")
        return payload


async def get_current_user_id(request: Request) -> str:
    """Dependency: resolve the authenticated user id from the Bearer token."""
    credentials: HTTPAuthorizationCredentials | None = await _bearer(request)
    if credentials is None or not credentials.credentials:
        raise ApiError(401, "UNAUTHENTICATED", "Authentication required.")
    validator: JwtValidator = request.app.state.jwt_validator
    payload = validator.validate(credentials.credentials)
    return str(payload["sub"])
