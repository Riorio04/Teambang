-- Progress reporting and S-curve planning for RDNIS.
--
-- Run this BEFORE add-public-stats.sql: the statistics function counts rows in
-- project_progress and reads projects.scurve_plan, so it cannot be created
-- until both exist.
--
-- Safe to re-run.

-- The planned S-curve: an array of { date, percent } points held on the
-- project itself, since a plan is revised as a whole rather than per point.
alter table public.projects
  add column if not exists scurve_plan jsonb not null default '[]'::jsonb;

-- One row per progress report filed against a project. photo_lat/photo_lng and
-- distance_m come from the photo's EXIF data, and are null when a report is
-- filed without a geotagged photo.
create table if not exists public.project_progress (
  id               uuid primary key default gen_random_uuid(),
  project_id       uuid not null references public.projects(id) on delete cascade,
  entry_date       date not null,
  percent_complete numeric not null,
  photo_path       text,
  photo_taken_at   timestamptz,
  photo_lat        double precision,
  photo_lng        double precision,
  distance_m       double precision,
  remarks          text,
  created_by       uuid references public.profiles(id) on delete set null,
  created_at       timestamptz not null default now()
);

-- Reports are always read per project and in date order.
create index if not exists project_progress_project_id_entry_date_idx
  on public.project_progress (project_id, entry_date);

alter table public.project_progress enable row level security;

-- Progress reports are only ever read or written from inside the signed-in
-- app; the landing page reaches its figures through rdnis_public_stats
-- instead, which is security definer and so bypasses these policies.
drop policy if exists project_progress_select on public.project_progress;
create policy project_progress_select on public.project_progress
  for select to authenticated using (true);

drop policy if exists project_progress_insert on public.project_progress;
create policy project_progress_insert on public.project_progress
  for insert to authenticated with check (true);

drop policy if exists project_progress_update on public.project_progress;
create policy project_progress_update on public.project_progress
  for update to authenticated using (true) with check (true);

drop policy if exists project_progress_delete on public.project_progress;
create policy project_progress_delete on public.project_progress
  for delete to authenticated using (true);
