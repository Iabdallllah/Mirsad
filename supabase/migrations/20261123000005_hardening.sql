-- Hardening follow-ups from the Phase 0 security review.
-- Append-only: 0000 is left untouched.

-- 1) audit INSERT is service-role only. RLS already has no client INSERT
--    policy; revoking the table grant is defense-in-depth (clients use the API,
--    which writes audit rows with the service role).
revoke insert on public.audit_logs from anon, authenticated;

-- 2) Owner deletion must not cascade-delete the workspace or its audit proof.
--    v1 account deletion is an API flow; author_id is nulled, data retention
--    follows plan.md §8.5.
alter table public.workspaces alter column owner_user_id drop not null;
alter table public.workspaces drop constraint workspaces_owner_user_id_fkey;
alter table public.workspaces
  add constraint workspaces_owner_user_id_fkey
  foreign key (owner_user_id) references auth.users (id) on delete set null;

-- 3) Finding/scan integrity: a reverify scan may only target a finding in the
--    same workspace. Enforced by the API; documented here for reviewers.
comment on column public.scans.target_finding_id is
  'Focused reverify target. API must verify same workspace_id before setting.';
