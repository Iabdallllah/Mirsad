"""Pydantic v2 response/request schemas (plan.md §10).

Shared API types for web/mobile are generated from the OpenAPI document
(packages/shared), not hand-written twice (plan.md §6).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class UserOut(BaseModel):
    id: str
    email: str | None = None
    github_username: str | None = None
    avatar_url: str | None = None


class WorkspaceOut(BaseModel):
    id: str
    name: str
    plan: str
    role: str
    suspended_at: datetime | None = None


class UsageOut(BaseModel):
    domains_used: int
    domains_limit: int
    scans_used: int
    scans_per_month: int
    period_start: datetime
    period_end: datetime


class MeOut(BaseModel):
    user: UserOut
    workspace: WorkspaceOut
    usage: UsageOut


class HealthOut(BaseModel):
    status: str = "ok"
    app_env: str


class ReadyChecks(BaseModel):
    database: bool
    queue: bool


class ReadyOut(BaseModel):
    status: str
    checks: ReadyChecks
    # Phase 0 has no worker yet (Phase 1). Reported honestly, never faked
    # (flagged gap C7: worker heartbeat mechanism is undefined in plan.md §8).
    worker: str = "not_deployed"
