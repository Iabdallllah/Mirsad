"""Worker configuration — defaults per plan.md §12.3.

Hard caps are product safety requirements (AGENTS.md §6); defaults must
match the plan and may only be tightened, never loosened, by environment.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    database_url: str | None = None

    scan_max_duration_min: int = 15
    scan_max_tokens: int = 100_000
    scan_max_llm_calls: int = 25
    scan_max_requests_safe: int = 300
    scan_max_requests_deep: int = 600
    worker_concurrency: int = 2
    worker_lease_timeout_sec: int = 120
