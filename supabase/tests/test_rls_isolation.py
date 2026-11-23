"""Two-tenant RLS isolation (plan.md §14.1: cross-tenant data leak control).

Every tenant table must be invisible across workspaces for authenticated
clients, and fully invisible to anon. Writes are restricted to the owner's
own workspace. These tests assert controls; they never disable them.
"""

from __future__ import annotations

import uuid

import psycopg
import pytest

from conftest import Tenant, as_anon, as_service, as_user

# Tables carrying workspace_id directly (plan.md §8.1 general rule).
WORKSPACE_TABLES = [
    "domains",
    "repo_connections",
    "scans",
    "findings",
    "patches",
    "reports",
    "notifications",
    "score_snapshots",
    "plan_limits",
    "audit_logs",
]
# workspaces keys on id; scan_jobs is worker/service-only by design.


@pytest.mark.parametrize("table", WORKSPACE_TABLES)
def test_cross_tenant_select_blocked(
    conn: psycopg.Connection, tenants: tuple[Tenant, Tenant], table: str
) -> None:
    a, b = tenants
    as_user(conn, a.user_id)
    row = conn.execute(
        f"select count(*) from public.{table} where workspace_id = %s",  # noqa: S608
        (b.workspace_id,),
    ).fetchone()
    assert row is not None and row[0] == 0, f"{table}: tenant A sees tenant B rows"


@pytest.mark.parametrize("table", WORKSPACE_TABLES)
def test_own_tenant_select_visible(
    conn: psycopg.Connection, tenants: tuple[Tenant, Tenant], table: str
) -> None:
    a, _ = tenants
    as_user(conn, a.user_id)
    row = conn.execute(
        f"select count(*) from public.{table} where workspace_id = %s",  # noqa: S608
        (a.workspace_id,),
    ).fetchone()
    assert row is not None and row[0] >= 1, f"{table}: owner cannot see own rows"


@pytest.mark.parametrize("table", ["domains", "scans", "findings", "reports", "workspaces", "workspace_members"])
def test_anon_sees_nothing(
    conn: psycopg.Connection, tenants: tuple[Tenant, Tenant], table: str
) -> None:
    a, _ = tenants
    as_anon(conn)
    row = conn.execute(f"select count(*) from public.{table}").fetchone()  # noqa: S608
    assert row is not None and row[0] == 0


def test_child_tables_scoped_via_parent(
    conn: psycopg.Connection, tenants: tuple[Tenant, Tenant]
) -> None:
    a, b = tenants
    as_user(conn, a.user_id)
    events = conn.execute(
        "select count(*) from public.scan_events where scan_id = %s", (b.ids["scan"],)
    ).fetchone()
    assert events is not None and events[0] == 0
    verifications = conn.execute(
        "select count(*) from public.domain_verifications where domain_id = %s",
        (b.ids["domain"],),
    ).fetchone()
    assert verifications is not None and verifications[0] == 0
    own_events = conn.execute(
        "select count(*) from public.scan_events where scan_id = %s", (a.ids["scan"],)
    ).fetchone()
    assert own_events is not None and own_events[0] == 1


@pytest.mark.parametrize(
    "table",
    [
        "workspace_members",
        "domain_verifications",
        "scan_events",
    ],
)
def test_child_and_join_tables_scoped(
    conn: psycopg.Connection, tenants: tuple[Tenant, Tenant], table: str
) -> None:
    """Tables scoped via parent joins must still isolate tenants."""
    a, b = tenants
    as_user(conn, a.user_id)
    if table == "workspace_members":
        rows = conn.execute(
            "select workspace_id from public.workspace_members"
        ).fetchall()
        assert all(str(r[0]) == a.workspace_id for r in rows)
    elif table == "domain_verifications":
        rows = conn.execute(
            "select count(*) from public.domain_verifications where domain_id = %s",
            (b.ids["domain"],),
        ).fetchone()
        assert rows is not None and rows[0] == 0
    else:
        rows = conn.execute(
            "select count(*) from public.scan_events where scan_id = %s", (b.ids["scan"],)
        ).fetchone()
        assert rows is not None and rows[0] == 0


def test_workspaces_visible_by_membership(
    conn: psycopg.Connection, tenants: tuple[Tenant, Tenant]
) -> None:
    a, b = tenants
    as_user(conn, a.user_id)
    row = conn.execute("select id from public.workspaces").fetchall()
    ids = {str(r[0]) for r in row}
    assert a.workspace_id in ids
    assert b.workspace_id not in ids


def test_scan_jobs_service_only(
    conn: psycopg.Connection, tenants: tuple[Tenant, Tenant]
) -> None:
    a, _ = tenants
    as_user(conn, a.user_id)
    rows = conn.execute("select count(*) from public.scan_jobs").fetchone()
    assert rows is not None and rows[0] == 0


def test_cross_tenant_insert_blocked(
    conn: psycopg.Connection, tenants: tuple[Tenant, Tenant]
) -> None:
    a, b = tenants
    as_user(conn, a.user_id)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute(
            """insert into public.domains (workspace_id, name, environment)
               values (%s, %s, 'staging')""",
            (b.workspace_id, f"evil-{uuid.uuid4().hex[:8]}.example.com"),
        )


def test_cross_tenant_update_delete_noop(
    conn: psycopg.Connection, tenants: tuple[Tenant, Tenant]
) -> None:
    a, b = tenants
    as_user(conn, a.user_id)
    cur = conn.execute(
        "update public.domains set name = 'hijacked' where id = %s", (b.ids["domain"],)
    )
    assert cur.rowcount == 0
    cur = conn.execute("delete from public.domains where id = %s", (b.ids["domain"],))
    assert cur.rowcount == 0
    as_service(conn)
    still_there = conn.execute(
        "select count(*) from public.domains where id = %s", (b.ids["domain"],)
    ).fetchone()
    assert still_there is not None and still_there[0] == 1


def test_owner_can_write_own_domain(
    conn: psycopg.Connection, tenants: tuple[Tenant, Tenant]
) -> None:
    a, _ = tenants
    as_user(conn, a.user_id)
    name = f"own-{uuid.uuid4().hex[:8]}.example.com"
    conn.execute(
        "insert into public.domains (workspace_id, name, environment) values (%s, %s, 'staging')",
        (a.workspace_id, name),
    )
    row = conn.execute(
        "select count(*) from public.domains where workspace_id = %s and name = %s",
        (a.workspace_id, name),
    ).fetchone()
    assert row is not None and row[0] == 1


def test_auth_configs_never_client_readable(
    conn: psycopg.Connection, tenants: tuple[Tenant, Tenant]
) -> None:
    a, _ = tenants
    as_user(conn, a.user_id)
    row = conn.execute("select count(*) from public.domain_auth_configs").fetchone()
    assert row is not None and row[0] == 0, "encrypted test credentials must be service-only"


def test_queue_and_webhooks_service_only(
    conn: psycopg.Connection, tenants: tuple[Tenant, Tenant]
) -> None:
    a, _ = tenants
    as_service(conn)
    conn.execute(
        "insert into public.webhook_deliveries (delivery_id, event) values (%s, 'push')",
        (str(uuid.uuid4()),),
    )
    as_user(conn, a.user_id)
    jobs = conn.execute("select count(*) from public.scan_jobs").fetchone()
    deliveries = conn.execute("select count(*) from public.webhook_deliveries").fetchone()
    assert jobs is not None and jobs[0] == 0
    assert deliveries is not None and deliveries[0] == 0


def test_notifications_own_only_and_mark_read(
    conn: psycopg.Connection, tenants: tuple[Tenant, Tenant]
) -> None:
    a, b = tenants
    as_user(conn, a.user_id)
    row = conn.execute(
        "select count(*) from public.notifications where user_id = %s", (b.user_id,)
    ).fetchone()
    assert row is not None and row[0] == 0
    cur = conn.execute(
        "update public.notifications set read_at = now() where id = %s",
        (a.ids["notification"],),
    )
    assert cur.rowcount == 1
    cur = conn.execute(
        "update public.notifications set read_at = now() where id = %s",
        (b.ids["notification"],),
    )
    assert cur.rowcount == 0


def test_notification_content_not_updatable(
    conn: psycopg.Connection, tenants: tuple[Tenant, Tenant]
) -> None:
    a, _ = tenants
    as_user(conn, a.user_id)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute(
            "update public.notifications set title = 'tampered' where id = %s",
            (a.ids["notification"],),
        )


def test_plan_limits_not_client_writable(
    conn: psycopg.Connection, tenants: tuple[Tenant, Tenant]
) -> None:
    a, _ = tenants
    as_user(conn, a.user_id)
    cur = conn.execute(
        "update public.plan_limits set scans_used = 0 where workspace_id = %s",
        (a.workspace_id,),
    )
    assert cur.rowcount == 0, "clients must never tamper with quota counters"


def test_profiles_self_only(
    conn: psycopg.Connection, tenants: tuple[Tenant, Tenant]
) -> None:
    a, b = tenants
    as_user(conn, a.user_id)
    row = conn.execute(
        "select count(*) from public.profiles where id = %s", (b.user_id,)
    ).fetchone()
    assert row is not None and row[0] == 0
    own = conn.execute(
        "select count(*) from public.profiles where id = %s", (a.user_id,)
    ).fetchone()
    assert own is not None and own[0] == 1


def test_device_tokens_own_only(
    conn: psycopg.Connection, tenants: tuple[Tenant, Tenant]
) -> None:
    a, b = tenants
    as_user(conn, a.user_id)
    row = conn.execute(
        "select count(*) from public.device_tokens where user_id = %s", (b.user_id,)
    ).fetchone()
    assert row is not None and row[0] == 0
    conn.execute(
        "insert into public.device_tokens (user_id, token) values (%s, %s)",
        (a.user_id, f"fcm-new-{uuid.uuid4().hex[:8]}"),
    )
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute(
            "insert into public.device_tokens (user_id, token) values (%s, %s)",
            (b.user_id, f"fcm-evil-{uuid.uuid4().hex[:8]}"),
        )
