-- Run in Supabase SQL Editor (Dashboard → SQL → New query)
-- Creates a public bucket for Site Admin partner + marketplace images.

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'partner-images',
  'partner-images',
  true,
  5242880,
  array['image/jpeg', 'image/png', 'image/webp', 'image/gif']
)
on conflict (id) do update set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

drop policy if exists "Public read partner images" on storage.objects;
create policy "Public read partner images"
on storage.objects
for select
to public
using (bucket_id = 'partner-images');

-- Allow uploads when using the service_role key (and authenticated sessions if needed).
drop policy if exists "Service role write partner images" on storage.objects;
create policy "Service role write partner images"
on storage.objects
for insert
to authenticated, service_role
with check (bucket_id = 'partner-images');

drop policy if exists "Service role update partner images" on storage.objects;
create policy "Service role update partner images"
on storage.objects
for update
to authenticated, service_role
using (bucket_id = 'partner-images')
with check (bucket_id = 'partner-images');

drop policy if exists "Service role delete partner images" on storage.objects;
create policy "Service role delete partner images"
on storage.objects
for delete
to authenticated, service_role
using (bucket_id = 'partner-images');
