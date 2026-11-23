"""GET /me — current user + workspace + plan/usage (plan.md §10.2).

Workspace ownership is resolved server-side from workspace_members; the
client never supplies workspace_id (AGENTS.md §5). v1 has exactly one owner
workspace per user; multi-workspace resolution is a v2 concern.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.auth import get_current_user_id
from app.db import get_pool
from app.errors import ApiError
from app.schemas import MeOut, UsageOut, UserOut, WorkspaceOut

router = APIRouter(prefix="/api/v1", tags=["me"])


@router.get("/me", response_model=MeOut)
async def me(request: Request, user_id: str = Depends(get_current_user_id)) -> MeOut:
    pool = get_pool(request)
    async with pool.acquire() as conn:
        profile = await conn.fetchrow(
            "select id, email, github_username, avatar_url "
            "from public.profiles where id = $1::uuid",
            user_id,
        )
        if profile is None:
            raise ApiError(404, "NOT_FOUND", "Profile not found.")

        membership = await conn.fetchrow(
            """
            select w.id, w.name, w.plan, w.suspended_at, m.role
            from public.workspace_members m
            join public.workspaces w on w.id = m.workspace_id
            where m.user_id = $1::uuid
            order by m.created_at
            limit 1
            """,
            user_id,
        )
        if membership is None:
            raise ApiError(404, "NOT_FOUND", "Workspace not found.")

        workspace_id = str(membership["id"])
        limits = await conn.fetchrow(
            """
            select domains_limit, scans_per_month, scans_used, period_start, period_end
            from public.plan_limits where workspace_id = $1::uuid
            """,
            workspace_id,
        )
        domains_used = await conn.fetchval(
            "select count(*) from public.domains where workspace_id = $1::uuid",
            workspace_id,
        )

    usage = UsageOut(
        domains_used=int(domains_used or 0),
        domains_limit=int(limits["domains_limit"]) if limits else 2,
        scans_used=int(limits["scans_used"]) if limits else 0,
        scans_per_month=int(limits["scans_per_month"]) if limits else 5,
        period_start=limits["period_start"],
        period_end=limits["period_end"],
    )
    return MeOut(
        user=UserOut(
            id=str(profile["id"]),
            email=profile["email"],
            github_username=profile["github_username"],
            avatar_url=profile["avatar_url"],
        ),
        workspace=WorkspaceOut(
            id=workspace_id,
            name=membership["name"],
            plan=membership["plan"],
            role=membership["role"],
            suspended_at=membership["suspended_at"],
        ),
        usage=usage,
    )
