"""Audit log immutability (plan.md §8.4, §14.1).

UPDATE/DELETE must fail for every role — including privileged ones — via the
append-only trigger; client INSERT is denied by RLS (service role only).
"""

from __future__ import annotations

import psycopg
import pytest

from conftest import Tenant, as_admin, as_service, as_user


def test_audit_insert_service_only(
    conn: psycopg.Connection, tenants: tuple[Tenant, Tenant]
) -> None:
    a, _ = tenants
    as_service(conn)
    conn.execute(
        """insert into public.audit_logs (workspace_id, actor_user_id, action)
           values (%s, %s, 'test.action')""",
        (a.workspace_id, a.user_id),
    )
    as_user(conn, a.user_id)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute(
            """insert into public.audit_logs (workspace_id, actor_user_id, action)
               values (%s, %s, 'forged.action')""",
            (a.workspace_id, a.user_id),
        )


@pytest.mark.parametrize("role", ["service", "admin"])
def test_audit_update_blocked(
    conn: psycopg.Connection, tenants: tuple[Tenant, Tenant], role: str
) -> None:
    a, _ = tenants
    if role == "service":
        # service_role has UPDATE/DELETE revoked at the grant level (0000),
        # which is the strongest control; the trigger covers roles that hold
        # the privilege (e.g., postgres/admin).
        as_service(conn)
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(
                "update public.audit_logs set action = 'tampered' where id = %s",
                (a.ids["audit"],),
            )
    else:
        as_admin(conn)
        with pytest.raises(psycopg.errors.RaiseException, match="append-only"):
            conn.execute(
                "update public.audit_logs set action = 'tampered' where id = %s",
                (a.ids["audit"],),
            )


@pytest.mark.parametrize("role", ["service", "admin"])
def test_audit_delete_blocked(
    conn: psycopg.Connection, tenants: tuple[Tenant, Tenant], role: str
) -> None:
    a, _ = tenants
    if role == "service":
        as_service(conn)
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("delete from public.audit_logs where id = %s", (a.ids["audit"],))
    else:
        as_admin(conn)
        with pytest.raises(psycopg.errors.RaiseException, match="append-only"):
            conn.execute("delete from public.audit_logs where id = %s", (a.ids["audit"],))


def test_audit_survives_workspace_deletion(
    conn: psycopg.Connection, tenants: tuple[Tenant, Tenant]
) -> None:
    """Minimal legal proof must survive workspace deletion (plan.md §8.5)."""
    a, _ = tenants
    as_admin(conn)
    conn.execute("delete from public.workspaces where id = %s", (a.workspace_id,))
    row = conn.execute(
        "select count(*) from public.audit_logs where workspace_id = %s",
        (a.workspace_id,),
    ).fetchone()
    assert row is not None and row[0] >= 1
