"""API configuration — environment variables per plan.md §12.2.

Values come from the environment / platform secret store; nothing is
hard-coded. Missing optional integrations stay None until their phase lands.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    api_base_url: str = "http://localhost:8000"

    database_url: str | None = None
    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    # Server-only. Never exposed to clients, logs, or error bodies.
    supabase_service_role_key: str | None = None
    supabase_jwt_secret: str | None = None
    supabase_jwks_url: str | None = None

    sentry_dsn: str | None = None


def get_settings() -> Settings:
    return Settings()
