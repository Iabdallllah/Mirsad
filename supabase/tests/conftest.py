"""Shared fixtures for Supabase security tests.

Runs against Supabase local (`supabase start` + `supabase db reset`).
Connection defaults to the local CLI database; override with SUPABASE_DB_URL.

Client roles are emulated the way PostgREST does it: SET ROLE +
request.jwt.claims, so auth.uid() resolves to the test user. These tests
never weaken RLS; they assert it (AGENTS.md §10).
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from typing import Any

import psycopg
import pytest

DB_URL = os.environ.get(
    "SUPABASE_DB_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
)


@dataclass
class Tenant:
    user_id: str
    workspace_id: str
    ids: dict[str, str] = field(default_factory=dict)


@pytest.fixture(scope="session")
def db_url() -> str:
    return DB_URL


@pytest.fixture()
def conn(db_url: str) -> Any:
    with psycopg.connect(db_url, autocommit=True) as connection:
        yield connection
        connection.execute("reset role")
        connection.execute("select set_config('request.jwt.claims', '{}', false)")


def _reset_role(conn: psycopg.Connection) -> None:
    conn.execute("reset role")
    conn.execute("select set_config('request.jwt.claims', '{}', false)")


def as_user(conn: psycopg.Connection, user_id: str) -> None:
    """Emulate an authenticated Supabase client for the given user."""
    _reset_role(conn)
    conn.execute("set role authenticated")
    claims = json.dumps({"sub": user_id, "role": "authenticated"})
    conn.execute("select set_config('request.jwt.claims', %s, false)", (claims,))


def as_anon(conn: psycopg.Connection) -> None:
    _reset_role(conn)
    conn.execute("set role anon")


def as_service(conn: psycopg.Connection) -> None:
    """Service role: bypasses RLS (server-only privileged path)."""
    _reset_role(conn)
    conn.execute("set role service_role")


def as_admin(conn: psycopg.Connection) -> None:
    _reset_role(conn)


def create_user(conn: psycopg.Connection, username: str) -> str:
    """Insert an auth user directly (local test harness only).

    The on_auth_user_created trigger provisions profile/workspace/member/
    plan_limits, exactly as a GitHub OAuth sign-in would.
    """
    as_admin(conn)
    user_id = str(uuid.uuid4())
    conn.execute(
        """
        insert into auth.users (
          id, instance_id, aud, role, email,
          raw_app_meta_data, raw_user_meta_data,
          email_confirmed_at, created_at, updated_at
        ) values (
          %s, '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', %s,
          '{"provider": "github", "providers": ["github"]}'::jsonb, %s::jsonb,
          now(), now(), now()
        )
        """,
        (
            user_id,
            f"{username}@users.noreply.github.com",
            json.dumps({"user_name": username, "avatar_url": "https://example.com/a.png"}),
        ),
    )
    return user_id


def workspace_of(conn: psycopg.Connection, user_id: str) -> str:
    as_admin(conn)
    row = conn.execute(
        "select id from public.workspaces where owner_user_id = %s", (user_id,)
    ).fetchone()
    assert row is not None, "bootstrap trigger did not create a workspace"
    return str(row[0])


def seed_workspace(conn: psycopg.Connection, tenant: Tenant) -> None:
    """Seed one row per tenant table as the service role (explicit workspace_id)."""
    as_service(conn)
    wid = tenant.workspace_id
    uid = tenant.user_id
    suffix = uuid.uuid4().hex[:8]

    def ins(sql: str, params: tuple[Any, ...]) -> str:
        row = conn.execute(sql + " returning id", params).fetchone()
        assert row is not None
        return str(row[0])

    tenant.ids["repo"] = ins(
        """insert into public.repo_connections
           (workspace_id, installation_id, repo_id, repo_full_name, default_branch)
           values (%s, 1, %s, %s, 'main')""",
        (wid, int(uuid.uuid4().int % 10**9), f"acme/{suffix}"),
    )
    tenant.ids["domain"] = ins(
        """insert into public.domains (workspace_id, name, environment, verification_status)
           values (%s, %s, 'staging', 'verified')""",
        (wid, f"{suffix}.example.com"),
    )
    tenant.ids["verification"] = ins(
        """insert into public.domain_verifications (domain_id, method, token_hash, status)
           values (%s, 'dns_txt', %s, 'verified')""",
        (tenant.ids["domain"], f"hash-{suffix}"),
    )
    tenant.ids["auth_config"] = ins(
        """insert into public.domain_auth_configs (domain_id, type, encrypted_value)
           values (%s, 'cookie', %s)""",
        (tenant.ids["domain"], f"encrypted-{suffix}"),
    )
    tenant.ids["scan"] = ins(
        """insert into public.scans (workspace_id, domain_id, mode, environment, status)
           values (%s, %s, 'black_box', 'staging', 'completed')""",
        (wid, tenant.ids["domain"]),
    )
    tenant.ids["job"] = ins(
        """insert into public.scan_jobs (scan_id, workspace_id, status, heartbeat_at)
           values (%s, %s, 'completed', now())""",
        (tenant.ids["scan"], wid),
    )
    tenant.ids["event"] = ins(
        """insert into public.scan_events (scan_id, phase, level, message)
           values (%s, 'recon', 'info', 'seeded event')""",
        (tenant.ids["scan"],),
    )
    tenant.ids["finding"] = ins(
        """insert into public.findings
           (workspace_id, domain_id, first_seen_scan_id, last_seen_scan_id,
            fingerprint, vuln_type, severity, confidence, title)
           values (%s, %s, %s, %s, %s, 'sqli', 'high', 'confirmed', 'Seeded finding')""",
        (
            wid,
            tenant.ids["domain"],
            tenant.ids["scan"],
            tenant.ids["scan"],
            f"fp-{suffix}",
        ),
    )
    tenant.ids["patch"] = ins(
        """insert into public.patches
           (workspace_id, finding_id, scan_id, repo_connection_id, branch_name, status)
           values (%s, %s, %s, %s, %s, 'pr_open')""",
        (
            wid,
            tenant.ids["finding"],
            tenant.ids["scan"],
            tenant.ids["repo"],
            f"mirsad/fix-{suffix}",
        ),
    )
    tenant.ids["report"] = ins(
        """insert into public.reports (workspace_id, domain_id, scan_id, storage_path, status)
           values (%s, %s, %s, %s, 'ready')""",
        (wid, tenant.ids["domain"], tenant.ids["scan"], f"{wid}/{tenant.ids['domain']}/r.pdf"),
    )
    tenant.ids["notification"] = ins(
        """insert into public.notifications (workspace_id, user_id, type, title)
           values (%s, %s, 'scan_completed', 'Scan completed')""",
        (wid, uid),
    )
    tenant.ids["device_token"] = ins(
        "insert into public.device_tokens (user_id, token, platform) values (%s, %s, 'android')",
        (uid, f"fcm-{suffix}"),
    )
    tenant.ids["score"] = ins(
        """insert into public.score_snapshots (workspace_id, domain_id, scan_id, score)
           values (%s, %s, %s, 88)""",
        (wid, tenant.ids["domain"], tenant.ids["scan"]),
    )
    tenant.ids["audit"] = ins(
        """insert into public.audit_logs (workspace_id, actor_user_id, action, resource_type)
           values (%s, %s, 'scan.completed', 'scan')""",
        (wid, uid),
    )


@pytest.fixture()
def tenants(conn: psycopg.Connection) -> tuple[Tenant, Tenant]:
    """Two independent tenants, each with a full set of seeded rows."""
    a_user = create_user(conn, f"alice-{uuid.uuid4().hex[:6]}")
    b_user = create_user(conn, f"bob-{uuid.uuid4().hex[:6]}")
    a = Tenant(user_id=a_user, workspace_id=workspace_of(conn, a_user))
    b = Tenant(user_id=b_user, workspace_id=workspace_of(conn, b_user))
    seed_workspace(conn, a)
    seed_workspace(conn, b)
    yield a, b
