-- Fix Storage reports SELECT policy (migration 0002).
-- The original policy used an unqualified `name` inside the correlated
-- subquery; PL/pgSQL name resolution bound it to public.workspaces.name
-- instead of storage.objects.name, so the membership check always failed.
-- This migration drops and recreates the policy with explicit aliases.
-- Append-only: 0002 is left untouched.

drop policy if exists "members read reports objects" on storage.objects;

create policy "members read reports objects" on storage.objects
  for select using (
    bucket_id = 'reports'
    and exists (
      select 1
      from public.workspaces ws
      where ws.id::text = (storage.foldername(objects.name))[1]
        and public.is_workspace_member(ws.id)
    )
  );
