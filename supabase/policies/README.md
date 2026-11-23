# RLS policies

The reviewed RLS policy SQL lives in the append-only migrations so it is
applied atomically with the schema (Supabase CLI only applies `migrations/`):

- `../migrations/20261123000001_rls.sql` — helpers (`is_workspace_member`,
  `is_workspace_owner`), ENABLE + FORCE on every tenant table, per-table
  policies, Realtime publication.
- `../migrations/20261123000002_storage.sql` — private `reports` bucket and
  Storage SELECT policy keyed by workspace membership.

Policy rules (plan.md §9.3, AGENTS.md §5):

- Clients (anon key + `authenticated` role) get **read** access to workspace
  data only through membership; the only client mutations are own-profile
  update, notification mark-read, device-token management, and owner domain
  writes.
- `domain_auth_configs`, `scan_jobs`, `webhook_deliveries` have **no client
  policies** (service role only).
- `audit_logs` is append-only (trigger + revoked UPDATE/DELETE grants).
- Privileged API/worker paths use the service role **after** explicit
  server-side authorization and always filter by `workspace_id`.

Isolation tests: `../tests/` (two-tenant suite, run with
`uv run --project supabase pytest supabase/tests`).
