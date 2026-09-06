-- Storage for project requirement files and progress photos.
--
-- The app calls storage.from('documents'), and bucket names are case
-- sensitive, so a bucket named 'Documents' does not answer those calls.
--
-- A private bucket denies every request until policies allow it, so the
-- grants below are what actually make uploads and downloads work. Files are
-- reached through signed URLs the app mints per download, which is why no
-- policy is granted to anon.
--
-- Safe to re-run.

insert into storage.buckets (id, name, public)
values ('documents', 'documents', false)
on conflict (id) do nothing;

drop policy if exists documents_read on storage.objects;
create policy documents_read on storage.objects
  for select to authenticated
  using (bucket_id = 'documents');

drop policy if exists documents_insert on storage.objects;
create policy documents_insert on storage.objects
  for insert to authenticated
  with check (bucket_id = 'documents');

drop policy if exists documents_update on storage.objects;
create policy documents_update on storage.objects
  for update to authenticated
  using (bucket_id = 'documents')
  with check (bucket_id = 'documents');

drop policy if exists documents_delete on storage.objects;
create policy documents_delete on storage.objects
  for delete to authenticated
  using (bucket_id = 'documents');
