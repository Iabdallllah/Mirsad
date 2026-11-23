-- Mirsad v1 Beta — core schema (plan.md §8.1, §8.2, §8.4).
-- Append-only migration: never edit after apply (AGENTS.md §9).
-- All tenant tables carry workspace_id from day 1; workspace_members holds a
-- single owner row in v1 to future-proof RLS for v2 multi-user.

-- ---------------------------------------------------------------------------
-- Enums (plan.md §8.2)
-- ---------------------------------------------------------------------------
create type public.environment as enum ('staging', 'production');
create type public.scan_status as enum (
  'queued', 'running', 'completed', 'partial', 'blocked', 'unreachable', 'failed', 'cancelled'
);
create type public.scan_trigger as enum ('manual', 'push', 'deploy', 'schedule', 'reverify');
create type public.severity as enum ('critical', 'high', 'medium', 'low');
create type public.confidence as enum ('confirmed', 'suspected');
create type public.finding_status as enum (
  'open', 'patch_needs_review', 'pr_open', 'waiting_deploy', 'verifying',
  'verified_fixed', 'still_vulnerable', 'false_positive', 'wont_fix', 'regression'
);
create type public.patch_status as enum (
  'draft', 'pr_open', 'ci_failed', 'changes_requested', 'merged', 'closed',
  'needs_rebase', 'regenerate_requested'
);
create type public.report_status as enum ('generating', 'ready', 'failed');
create type public.scan_mode as enum ('black_box', 'grey_box');

-- Derived enums (values implied by plan.md §8.1 / §10.3 and design.md J8;
-- not enumerated in plan.md §8.2 — flagged in the Phase 0 change report):
create type public.verification_status as enum ('pending', 'verified', 'failed');
create type public.verification_method as enum ('dns_txt', 'well_known_file');

-- ---------------------------------------------------------------------------
-- Shared trigger: updated_at maintenance
-- ---------------------------------------------------------------------------
create function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- ---------------------------------------------------------------------------
-- Identity / tenancy
-- ---------------------------------------------------------------------------
create table public.workspaces (
  id            uuid primary key default gen_random_uuid(),
  name          text not null,
  owner_user_id uuid not null references auth.users (id),
  plan          text not null default 'beta',
  suspended_at  timestamptz,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);
create trigger workspaces_set_updated_at before update on public.workspaces
  for each row execute function public.set_updated_at();

create table public.workspace_members (
  workspace_id uuid not null references public.workspaces (id) on delete cascade,
  user_id      uuid not null references auth.users (id) on delete cascade,
  role         text not null default 'owner' check (role in ('owner')), -- v1: owner only; v2 roles
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  primary key (workspace_id, user_id)
);
create trigger workspace_members_set_updated_at before update on public.workspace_members
  for each row execute function public.set_updated_at();

create table public.profiles (
  id              uuid primary key references auth.users (id) on delete cascade,
  github_username text,
  email           text,
  avatar_url      text,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);
create trigger profiles_set_updated_at before update on public.profiles
  for each row execute function public.set_updated_at();

-- ---------------------------------------------------------------------------
-- GitHub repo connections (created before domains: domains references it)
-- ---------------------------------------------------------------------------
create table public.repo_connections (
  id              uuid primary key default gen_random_uuid(),
  workspace_id    uuid not null references public.workspaces (id) on delete cascade,
  installation_id bigint not null,
  repo_id         bigint not null,
  repo_full_name  text not null,
  default_branch  text,
  status          text not null default 'connected' check (status in ('connected', 'disconnected')),
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  unique (workspace_id, repo_id)
);
create index repo_connections_workspace_created_idx on public.repo_connections (workspace_id, created_at);
create trigger repo_connections_set_updated_at before update on public.repo_connections
  for each row execute function public.set_updated_at();

-- ---------------------------------------------------------------------------
-- Domains + verification + test credentials
-- ---------------------------------------------------------------------------
create table public.domains (
  id                  uuid primary key default gen_random_uuid(),
  workspace_id        uuid not null references public.workspaces (id) on delete cascade,
  name                text not null,
  environment         public.environment not null,
  verification_status public.verification_status not null default 'pending',
  verified_at         timestamptz,
  verification_method public.verification_method,
  consent_version     text,
  consent_at          timestamptz,
  consent_ip          inet,
  repo_connection_id  uuid references public.repo_connections (id) on delete set null,
  next_scan_at        timestamptz,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now(),
  -- design.md §6.2: a domain already claimed by another workspace is an error.
  unique (name)
);
create index domains_workspace_created_idx on public.domains (workspace_id, created_at);
create trigger domains_set_updated_at before update on public.domains
  for each row execute function public.set_updated_at();

create table public.domain_verifications (
  id             uuid primary key default gen_random_uuid(),
  domain_id      uuid not null references public.domains (id) on delete cascade,
  method         public.verification_method not null,
  token_hash     text not null,
  status         public.verification_status not null default 'pending',
  checked_at     timestamptz,
  failure_reason text,
  proof_hash     text,
  created_at     timestamptz not null default now()
);
create index domain_verifications_domain_created_idx on public.domain_verifications (domain_id, created_at);

-- Customer test cookies/Bearer tokens: encrypted at rest by the API
-- (AES-256-GCM or Vault, plan.md §9.4). Never returned raw; no client RLS
-- policies exist for this table (service role only).
create table public.domain_auth_configs (
  id              uuid primary key default gen_random_uuid(),
  domain_id       uuid not null references public.domains (id) on delete cascade,
  type            text not null check (type in ('cookie', 'bearer')),
  encrypted_value text not null,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  unique (domain_id)
);
create trigger domain_auth_configs_set_updated_at before update on public.domain_auth_configs
  for each row execute function public.set_updated_at();

-- ---------------------------------------------------------------------------
-- Scans (episodes) + queue + events
-- ---------------------------------------------------------------------------
create table public.scans (
  id                  uuid primary key default gen_random_uuid(),
  workspace_id        uuid not null references public.workspaces (id) on delete cascade,
  domain_id           uuid not null references public.domains (id) on delete cascade,
  repo_connection_id  uuid references public.repo_connections (id) on delete set null,
  mode                public.scan_mode not null default 'black_box',
  environment         public.environment not null,
  trigger             public.scan_trigger not null default 'manual',
  status              public.scan_status not null default 'queued',
  started_at          timestamptz,
  finished_at         timestamptz,
  coverage            jsonb,
  score_before        integer check (score_before between 0 and 100),
  score_after         integer check (score_after between 0 and 100),
  llm_tokens          integer not null default 0,
  llm_calls           integer not null default 0,
  cost_estimate_usd   numeric(10, 4) not null default 0,
  deterministic_ratio numeric(5, 4) check (deterministic_ratio between 0 and 1),
  parent_scan_id      uuid references public.scans (id) on delete set null,
  target_finding_id   uuid, -- FK added after findings exists (circular reference)
  error_code          text,
  error_message       text,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now()
);
create index scans_domain_created_idx on public.scans (domain_id, created_at desc);
create index scans_workspace_status_idx on public.scans (workspace_id, status);
create index scans_workspace_created_idx on public.scans (workspace_id, created_at);
create trigger scans_set_updated_at before update on public.scans
  for each row execute function public.set_updated_at();

-- Postgres queue (plan.md §4.3): FOR UPDATE SKIP LOCKED; no Redis in v1.
-- Job status values are derived (plan.md §8.1 does not enumerate them).
create table public.scan_jobs (
  id               uuid primary key default gen_random_uuid(),
  scan_id          uuid not null unique references public.scans (id) on delete cascade,
  workspace_id     uuid not null references public.workspaces (id) on delete cascade,
  status           text not null default 'queued'
                   check (status in ('queued', 'leased', 'completed', 'failed', 'cancelled')),
  priority         integer not null default 0,
  attempts         integer not null default 0,
  lease_expires_at timestamptz,
  heartbeat_at     timestamptz,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now()
);
create index scan_jobs_queued_idx on public.scan_jobs (priority desc, created_at)
  where status = 'queued';
create index scan_jobs_workspace_created_idx on public.scan_jobs (workspace_id, created_at);
create trigger scan_jobs_set_updated_at before update on public.scan_jobs
  for each row execute function public.set_updated_at();

create table public.scan_events (
  id         uuid primary key default gen_random_uuid(),
  scan_id    uuid not null references public.scans (id) on delete cascade,
  phase      text,
  level      text not null default 'info' check (level in ('debug', 'info', 'warn', 'error')),
  message    text not null,
  metadata   jsonb,
  created_at timestamptz not null default now()
);
create index scan_events_scan_created_idx on public.scan_events (scan_id, created_at);
create index scan_events_created_idx on public.scan_events (created_at); -- 14-day prune (§8.5)

-- ---------------------------------------------------------------------------
-- Findings (UI label: "Issue") + patches + reports
-- ---------------------------------------------------------------------------
create table public.findings (
  id                 uuid primary key default gen_random_uuid(),
  workspace_id       uuid not null references public.workspaces (id) on delete cascade,
  domain_id          uuid not null references public.domains (id) on delete cascade,
  first_seen_scan_id uuid references public.scans (id) on delete set null,
  last_seen_scan_id  uuid references public.scans (id) on delete set null,
  fingerprint        text not null,
  vuln_type          text not null,
  severity           public.severity not null,
  confidence         public.confidence not null,
  status             public.finding_status not null default 'open',
  endpoint_path      text,
  http_method        text,
  parameter          text,
  title              text not null,
  description        text,
  impact             text,
  owasp_category     text,
  -- Sanitized PoC evidence only; never raw traffic (AGENTS.md §7). ≤ 50 KB.
  evidence           jsonb check (octet_length(evidence::text) <= 51200),
  verified_at        timestamptz,
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now(),
  unique (domain_id, fingerprint)
);
create index findings_workspace_severity_status_idx on public.findings (workspace_id, severity, status);
create index findings_workspace_created_idx on public.findings (workspace_id, created_at);
create trigger findings_set_updated_at before update on public.findings
  for each row execute function public.set_updated_at();

alter table public.scans
  add constraint scans_target_finding_id_fkey
  foreign key (target_finding_id) references public.findings (id) on delete set null;

create table public.patches (
  id                 uuid primary key default gen_random_uuid(),
  -- workspace_id per the §8.1 general rule ("all tenant tables include
  -- workspace_id"); the patches key-column list omits it — flagged in report.
  workspace_id       uuid not null references public.workspaces (id) on delete cascade,
  finding_id         uuid not null references public.findings (id) on delete cascade,
  scan_id            uuid references public.scans (id) on delete set null,
  repo_connection_id uuid references public.repo_connections (id) on delete set null,
  branch_name        text not null,
  commit_sha         text,
  pr_number          integer,
  pr_url             text,
  status             public.patch_status not null default 'draft',
  ci_status          text,
  merged_at          timestamptz,
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now(),
  unique (repo_connection_id, branch_name),
  unique (finding_id, pr_number)
);
create index patches_workspace_created_idx on public.patches (workspace_id, created_at);
create trigger patches_set_updated_at before update on public.patches
  for each row execute function public.set_updated_at();

create table public.reports (
  id           uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id) on delete cascade,
  domain_id    uuid not null references public.domains (id) on delete cascade,
  scan_id      uuid not null references public.scans (id) on delete cascade,
  storage_path text not null,
  status       public.report_status not null default 'generating',
  generated_at timestamptz,
  expires_at   timestamptz,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);
create index reports_workspace_created_idx on public.reports (workspace_id, created_at);
create trigger reports_set_updated_at before update on public.reports
  for each row execute function public.set_updated_at();

-- ---------------------------------------------------------------------------
-- Notifications / devices
-- ---------------------------------------------------------------------------
create table public.notifications (
  id           uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id) on delete cascade,
  user_id      uuid not null references auth.users (id) on delete cascade,
  type         text not null,
  title        text not null,
  body         text, -- no sensitive payloads (plan.md §8.1)
  read_at      timestamptz,
  metadata     jsonb,
  created_at   timestamptz not null default now()
);
create index notifications_user_created_idx on public.notifications (user_id, created_at desc);
create index notifications_workspace_created_idx on public.notifications (workspace_id, created_at);

create table public.device_tokens (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null references auth.users (id) on delete cascade,
  token        text not null unique,
  platform     text not null default 'android' check (platform in ('android')),
  created_at   timestamptz not null default now(),
  last_seen_at timestamptz
);

-- ---------------------------------------------------------------------------
-- Audit log — append-only (plan.md §8.4, §14.1)
-- workspace_id / actor_user_id intentionally have no FK: minimal legal proof
-- must survive domain/workspace deletion and GDPR anonymization (§8.5).
-- ---------------------------------------------------------------------------
create table public.audit_logs (
  id            uuid primary key default gen_random_uuid(),
  workspace_id  uuid,
  actor_user_id uuid,
  action        text not null,
  resource_type text,
  resource_id   uuid,
  ip            inet,
  metadata      jsonb,
  created_at    timestamptz not null default now()
);
create index audit_logs_workspace_created_idx on public.audit_logs (workspace_id, created_at);

create function public.audit_logs_append_only()
returns trigger
language plpgsql
as $$
begin
  raise exception 'audit_logs is append-only: % is prohibited', tg_op;
end;
$$;

create trigger audit_logs_no_update before update on public.audit_logs
  for each row execute function public.audit_logs_append_only();
create trigger audit_logs_no_delete before delete on public.audit_logs
  for each row execute function public.audit_logs_append_only();

revoke update, delete on public.audit_logs from public, anon, authenticated, service_role;

-- ---------------------------------------------------------------------------
-- Score snapshots / webhook deliveries / plan limits
-- ---------------------------------------------------------------------------
create table public.score_snapshots (
  id           uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id) on delete cascade,
  domain_id    uuid not null references public.domains (id) on delete cascade,
  scan_id      uuid references public.scans (id) on delete set null,
  score        integer not null check (score between 0 and 100),
  coverage     jsonb,
  created_at   timestamptz not null default now()
);
create index score_snapshots_domain_created_idx on public.score_snapshots (domain_id, created_at);
create index score_snapshots_workspace_created_idx on public.score_snapshots (workspace_id, created_at);

create table public.webhook_deliveries (
  id           uuid primary key default gen_random_uuid(),
  delivery_id  text not null unique,
  event        text not null,
  received_at  timestamptz not null default now(),
  processed_at timestamptz
);
create index webhook_deliveries_received_idx on public.webhook_deliveries (received_at); -- 7-day prune (§8.5)

create table public.plan_limits (
  workspace_id    uuid primary key references public.workspaces (id) on delete cascade,
  plan            text not null default 'beta',
  domains_limit   integer not null default 2,
  scans_per_month integer not null default 5,
  scans_used      integer not null default 0,
  period_start    timestamptz not null,
  period_end      timestamptz not null,
  overage_policy  text not null default 'hard_stop',
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);
create trigger plan_limits_set_updated_at before update on public.plan_limits
  for each row execute function public.set_updated_at();
