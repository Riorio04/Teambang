-- Lets an administrator decline an account request.
--
-- Declining is kept as a flag rather than deleting the profile: the sign-up
-- still exists in Supabase Auth either way, so a deleted profile would leave
-- someone able to sign in with nothing to explain why RDNIS is empty. The
-- flag also keeps a record of requests that were refused.
--
-- A request is pending while it is neither approved nor declined, which is
-- what the admin queue lists.
--
-- Safe to re-run.

alter table public.profiles
  add column if not exists declined boolean not null default false,
  add column if not exists declined_at timestamptz;

-- The queue reads exactly this pair on every load.
create index if not exists profiles_pending_idx
  on public.profiles (created_at)
  where approved = false and declined = false;
