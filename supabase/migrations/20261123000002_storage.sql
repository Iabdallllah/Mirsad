-- Mirsad v1 Beta — private reports bucket + Storage RLS (plan.md §9.3).
-- Object path: {workspace_id}/{domain_id}/{report_id}.pdf
-- Downloads use backend-generated signed URLs (~60s); the SELECT policy also
-- gates any direct client access by workspace membership.

insert into storage.buckets (id, name, public)
values ('reports', 'reports', false)
on conflict (id) do nothing;

-- Membership check without casting arbitrary path segments to uuid (avoids
-- policy errors on malformed paths): compare workspaces.id::text instead.
create policy "members read reports objects" on storage.objects
  for select using (
    bucket_id = 'reports'
    and exists (
      select 1 from public.workspaces w
      where w.id::text = (storage.foldername(name))[1]
        and public.is_workspace_member(w.id)
    )
  );

-- INSERT/UPDATE/DELETE: service role only (worker generates PDFs; API deletes
-- on domain deletion). No client write policies are created.
