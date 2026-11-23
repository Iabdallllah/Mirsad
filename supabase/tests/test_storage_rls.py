"""Storage RLS for the private reports bucket (plan.md §9.3).

Path layout {workspace_id}/{domain_id}/{report_id}.pdf; members may only read
objects under their own workspace prefix; writes are service-role only.
"""

from __future__ import annotations

import uuid

import psycopg
import pytest

from conftest import Tenant, as_admin, as_service, as_user


def _put_object(conn: psycopg.Connection, workspace_id: str, name: str) -> None:
    as_service(conn)
    conn.execute(
        """insert into storage.objects (bucket_id, name, owner, metadata)
           values ('reports', %s, %s, '{}'::jsonb)""",
        (name, workspace_id),
    )


def test_reports_bucket_is_private(conn: psycopg.Connection) -> None:
    as_admin(conn)
    row = conn.execute(
        "select public from storage.buckets where id = 'reports'"
    ).fetchone()
    assert row is not None and row[0] is False


def test_members_read_own_reports_only(
    conn: psycopg.Connection, tenants: tuple[Tenant, Tenant]
) -> None:
    a, b = tenants
    _put_object(conn, a.workspace_id, f"{a.workspace_id}/{a.ids['domain']}/r1.pdf")
    _put_object(conn, b.workspace_id, f"{b.workspace_id}/{b.ids['domain']}/r1.pdf")

    as_user(conn, a.user_id)
    rows = conn.execute(
        "select name from storage.objects where bucket_id = 'reports'"
    ).fetchall()
    names = [r[0] for r in rows]
    assert f"{a.workspace_id}/{a.ids['domain']}/r1.pdf" in names
    assert all(not n.startswith(b.workspace_id) for n in names)


def test_client_cannot_write_reports(
    conn: psycopg.Connection, tenants: tuple[Tenant, Tenant]
) -> None:
    a, _ = tenants
    as_user(conn, a.user_id)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute(
            """insert into storage.objects (bucket_id, name, owner, metadata)
               values ('reports', %s, %s, '{}'::jsonb)""",
            (f"{a.workspace_id}/evil.pdf", a.user_id),
        )


def test_malformed_path_does_not_error(
    conn: psycopg.Connection, tenants: tuple[Tenant, Tenant]
) -> None:
    a, _ = tenants
    _put_object(conn, a.workspace_id, f"not-a-uuid/{uuid.uuid4().hex}.pdf")
    as_user(conn, a.user_id)
    rows = conn.execute(
        "select count(*) from storage.objects where bucket_id = 'reports' and name like 'not-a-uuid%'"
    ).fetchone()
    assert rows is not None and rows[0] == 0
