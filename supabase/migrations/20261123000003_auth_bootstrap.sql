-- Mirsad v1 Beta — first-sign-in bootstrap.
-- Resolves flagged gap C4: plan.md §10.2 has GET /me and PATCH /workspace but
-- no workspace-creation endpoint. On GitHub OAuth sign-in, Supabase Auth
-- inserts auth.users; this trigger provisions profile + workspace + single
-- owner membership + beta plan limits (plan.md §2.3, §8.1, §9.2).
-- SECURITY DEFINER owned by the migration role so it can write through the
-- forced RLS policies; it never trusts client-supplied identifiers.

create function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  wid uuid;
  display_name text;
begin
  display_name := coalesce(
    new.raw_user_meta_data ->> 'user_name',
    new.raw_user_meta_data ->> 'preferred_username',
    new.raw_user_meta_data ->> 'name',
    'owner'
  );

  insert into public.profiles (id, github_username, email, avatar_url)
  values (
    new.id,
    new.raw_user_meta_data ->> 'user_name',
    new.email,
    new.raw_user_meta_data ->> 'avatar_url'
  )
  on conflict (id) do nothing;

  insert into public.workspaces (name, owner_user_id)
  values (display_name || '''s workspace', new.id)
  returning id into wid;

  insert into public.workspace_members (workspace_id, user_id, role)
  values (wid, new.id, 'owner');

  insert into public.plan_limits (
    workspace_id, plan, domains_limit, scans_per_month,
    scans_used, period_start, period_end, overage_policy
  )
  values (
    wid, 'beta', 2, 5,
    0, date_trunc('month', now()), date_trunc('month', now()) + interval '1 month',
    'hard_stop'
  );

  insert into public.audit_logs (workspace_id, actor_user_id, action, resource_type, resource_id)
  values (wid, new.id, 'workspace.created', 'workspace', wid);

  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();
