"""First-sign-in bootstrap: profile + workspace + owner + beta plan limits.

Resolves gap C4 (no workspace-creation endpoint in plan.md §10.2): the
auth.users trigger must provision exactly one workspace per owner with the
beta limits from plan.md §2.3.
"""

from __future__ import annotations

import uuid

import psycopg

from conftest import as_admin, as_service, create_user, workspace_of


def test_bootstrap_provisions_workspace(conn: psycopg.Connection) -> None:
    username = f"carol-{uuid.uuid4().hex[:6]}"
    user_id = create_user(conn, username)
    workspace_id = workspace_of(conn, user_id)

    as_admin(conn)
    profile = conn.execute(
        "select github_username, email, avatar_url from public.profiles where id = %s",
        (user_id,),
    ).fetchone()
    assert profile is not None
    assert profile[0] == username
    assert profile[1] == f"{username}@users.noreply.github.com"
    assert profile[2] == "https://example.com/a.png"

    workspace = conn.execute(
        "select name, owner_user_id, plan from public.workspaces where id = %s",
        (workspace_id,),
    ).fetchone()
    assert workspace is not None
    assert workspace[0] == f"{username}'s workspace"
    assert str(workspace[1]) == user_id
    assert workspace[2] == "beta"

    members = conn.execute(
        "select user_id, role from public.workspace_members where workspace_id = %s",
        (workspace_id,),
    ).fetchall()
    assert len(members) == 1, "v1: exactly one owner row"
    assert str(members[0][0]) == user_id
    assert members[0][1] == "owner"

    limits = conn.execute(
        """select plan, domains_limit, scans_per_month, scans_used, overage_policy,
                  period_start < period_end
           from public.plan_limits where workspace_id = %s""",
        (workspace_id,),
    ).fetchone()
    assert limits == ("beta", 2, 5, 0, "hard_stop", True)

    audit = conn.execute(
        """select action from public.audit_logs
           where workspace_id = %s and action = 'workspace.created'""",
        (workspace_id,),
    ).fetchone()
    assert audit is not None


def test_bootstrap_one_workspace_per_owner(conn: psycopg.Connection) -> None:
    user_id = create_user(conn, f"dave-{uuid.uuid4().hex[:6]}")
    as_service(conn)
    count = conn.execute(
        "select count(*) from public.workspaces where owner_user_id = %s", (user_id,)
    ).fetchone()
    assert count is not None and count[0] == 1
