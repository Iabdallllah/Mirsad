-- Mirsad v1 Beta — row level security (plan.md §9.3).
-- RLS is enabled AND forced on every tenant table; helpers are SECURITY
-- DEFINER to avoid recursive policy evaluation on workspace_members.
-- Privileged API/worker paths use the service role AFTER explicit server-side
-- authorization, and always include workspace_id in queries (AGENTS.md §5).
-- Client-direct access (web/mobile) uses the anon key + these policies.

-- ---------------------------------------------------------------------------
-- Helper functions
-- ---------------------------------------------------------------------------
create function public.is_workspace_member(wid uuid)
returns boolean
language sql
stable
security definer
set search_path = public, pg_temp
as $$
  select exists (
    select 1 from public.workspace_members m
    where m.workspace_id = wid and m.user_id = auth.uid()
  );
$$;

create function public.is_workspace_owner(wid uuid)
returns boolean
language sql
stable
security definer
set search_path = public, pg_temp
as $$
  select exists (
    select 1 from public.workspace_members m
    where m.workspace_id = wid and m.user_id = auth.uid() and m.role = 'owner'
  );
$$;

-- Policy expressions execute with the querying role's privileges, so anon
-- must be able to EXECUTE the helpers for policies to evaluate (they return
-- booleans derived from auth.uid(), which is null for anon — no data leak).
revoke execute on function public.is_workspace_member(uuid) from public;
revoke execute on function public.is_workspace_owner(uuid) from public;
grant execute on function public.is_workspace_member(uuid) to anon, authenticated, service_role;
grant execute on function public.is_workspace_owner(uuid) to anon, authenticated, service_role;

-- ---------------------------------------------------------------------------
-- workspaces / workspace_members / profiles
-- ---------------------------------------------------------------------------
alter table public.workspaces enable row level security;
alter table public.workspaces force row level security;

create policy "members read workspaces" on public.workspaces
  for select using (public.is_workspace_member(id));
create policy "owner updates workspaces" on public.workspaces
  for update using (public.is_workspace_owner(id))
  with check (public.is_workspace_owner(id));
-- Inserts happen via the auth bootstrap trigger (service-side); deletes are
-- an API-only danger-zone flow. No client insert/delete policies.

alter table public.workspace_members enable row level security;
alter table public.workspace_members force row level security;

create policy "members read membership" on public.workspace_members
  for select using (public.is_workspace_member(workspace_id));
-- v1: single owner row created by the bootstrap trigger; no client writes.

alter table public.profiles enable row level security;
alter table public.profiles force row level security;

create policy "users read own profile" on public.profiles
  for select using (id = auth.uid());
create policy "users update own profile" on public.profiles
  for update using (id = auth.uid()) with check (id = auth.uid());

-- ---------------------------------------------------------------------------
-- domains (plan.md §9.3 example policy)
-- ---------------------------------------------------------------------------
alter table public.domains enable row level security;
alter table public.domains force row level security;

create policy "members read domains" on public.domains
  for select using (public.is_workspace_member(workspace_id));
create policy "owner writes domains" on public.domains
  for all using (public.is_workspace_owner(workspace_id))
  with check (public.is_workspace_owner(workspace_id));

-- ---------------------------------------------------------------------------
-- domain_verifications: member read via parent domain; writes service-only
-- (verification checks run server-side, plan.md §10.2).
-- ---------------------------------------------------------------------------
alter table public.domain_verifications enable row level security;
alter table public.domain_verifications force row level security;

create policy "members read verifications" on public.domain_verifications
  for select using (
    exists (
      select 1 from public.domains d
      where d.id = domain_id and public.is_workspace_member(d.workspace_id)
    )
  );

-- ---------------------------------------------------------------------------
-- domain_auth_configs: NO client policies. Encrypted test credentials are
-- service-role only and never returned raw (AGENTS.md §4, plan.md §9.4).
-- ---------------------------------------------------------------------------
alter table public.domain_auth_configs enable row level security;
alter table public.domain_auth_configs force row level security;

-- ---------------------------------------------------------------------------
-- repo_connections: member read; linking/disconnection is API-only.
-- ---------------------------------------------------------------------------
alter table public.repo_connections enable row level security;
alter table public.repo_connections force row level security;

create policy "members read repo connections" on public.repo_connections
  for select using (public.is_workspace_member(workspace_id));

-- ---------------------------------------------------------------------------
-- scans / scan_jobs / scan_events
-- ---------------------------------------------------------------------------
alter table public.scans enable row level security;
alter table public.scans force row level security;

create policy "members read scans" on public.scans
  for select using (public.is_workspace_member(workspace_id));
-- Scan creation/cancellation is API-only (quota + concurrency enforced
-- server-side, plan.md §11.2). No client write policies.

alter table public.scan_jobs enable row level security;
alter table public.scan_jobs force row level security;
-- Queue is worker/service-role only: no client policies.

alter table public.scan_events enable row level security;
alter table public.scan_events force row level security;

create policy "members read scan events" on public.scan_events
  for select using (
    exists (
      select 1 from public.scans s
      where s.id = scan_id and public.is_workspace_member(s.workspace_id)
    )
  );
-- Realtime channel scan:{scan_id} relies on this SELECT policy (plan.md §10.4).

-- ---------------------------------------------------------------------------
-- findings / patches / reports: member read; mutations are API-only.
-- ---------------------------------------------------------------------------
alter table public.findings enable row level security;
alter table public.findings force row level security;

create policy "members read findings" on public.findings
  for select using (public.is_workspace_member(workspace_id));

alter table public.patches enable row level security;
alter table public.patches force row level security;

create policy "members read patches" on public.patches
  for select using (public.is_workspace_member(workspace_id));

alter table public.reports enable row level security;
alter table public.reports force row level security;

create policy "members read reports" on public.reports
  for select using (public.is_workspace_member(workspace_id));

-- ---------------------------------------------------------------------------
-- notifications: own rows only; mark-read is the only client mutation.
-- ---------------------------------------------------------------------------
alter table public.notifications enable row level security;
alter table public.notifications force row level security;

create policy "users read own notifications" on public.notifications
  for select using (user_id = auth.uid());
create policy "users mark own notifications read" on public.notifications
  for update using (user_id = auth.uid()) with check (user_id = auth.uid());

revoke update on public.notifications from authenticated;
grant update (read_at) on public.notifications to authenticated;

-- ---------------------------------------------------------------------------
-- device_tokens: own rows only (register/remove, plan.md §10.2).
-- ---------------------------------------------------------------------------
alter table public.device_tokens enable row level security;
alter table public.device_tokens force row level security;

create policy "users manage own device tokens" on public.device_tokens
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

-- ---------------------------------------------------------------------------
-- audit_logs: member read; insert service-role only; UPDATE/DELETE blocked
-- by trigger + revoked grants (migration 0000). No client write policies.
-- ---------------------------------------------------------------------------
alter table public.audit_logs enable row level security;
alter table public.audit_logs force row level security;

create policy "members read audit logs" on public.audit_logs
  for select using (
    workspace_id is not null and public.is_workspace_member(workspace_id)
  );

-- ---------------------------------------------------------------------------
-- score_snapshots: member read.
-- ---------------------------------------------------------------------------
alter table public.score_snapshots enable row level security;
alter table public.score_snapshots force row level security;

create policy "members read score snapshots" on public.score_snapshots
  for select using (public.is_workspace_member(workspace_id));

-- ---------------------------------------------------------------------------
-- webhook_deliveries: service-role only (no workspace_id, no client access).
-- ---------------------------------------------------------------------------
alter table public.webhook_deliveries enable row level security;
alter table public.webhook_deliveries force row level security;

-- ---------------------------------------------------------------------------
-- plan_limits: member read; quota writes are service-role only so clients
-- can never tamper with usage counters (AGENTS.md §5).
-- ---------------------------------------------------------------------------
alter table public.plan_limits enable row level security;
alter table public.plan_limits force row level security;

create policy "members read plan limits" on public.plan_limits
  for select using (public.is_workspace_member(workspace_id));

-- ---------------------------------------------------------------------------
-- Realtime publication (plan.md §10.4): scan events + scan status changes.
-- ---------------------------------------------------------------------------
alter publication supabase_realtime add table public.scan_events;
alter publication supabase_realtime add table public.scans;
