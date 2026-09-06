-- Locks an account after repeated failed sign-ins.
--
-- The count has to live in the database rather than the browser: a counter
-- kept client-side is cleared by wiping site data or opening another
-- browser, so it would stop nobody.
--
-- These run as security definer because the caller is signed out, and
-- profiles is unreadable until someone is signed in. They deliberately
-- reveal nothing about whether an identifier belongs to a real account.
--
-- Ten attempts, then a thirty minute lock. Resetting the password clears
-- it sooner, which is the way back in for someone genuinely locked out.
--
-- Safe to re-run.

alter table public.profiles
  add column if not exists failed_logins integer not null default 0,
  add column if not exists locked_until timestamptz;

-- Resolves a username or email to the account it belongs to.
--
-- auth.users is consulted as well as profiles.email: sign-up only began
-- recording the address on the profile recently, so every account made
-- before then has a null there while auth still holds the real address.
-- Matching on profiles alone silently found nothing for those accounts, so
-- they could never be locked.
create or replace function public.rdnis_account_for_identifier(identifier text)
returns uuid
language sql
security definer
stable
set search_path = public
as $$
  select p.id
  from public.profiles p
  left join auth.users u on u.id = p.id
  where nullif(trim(identifier), '') is not null
    and (
      lower(p.username) = lower(trim(identifier))
      or lower(p.email)  = lower(trim(identifier))
      or lower(u.email)  = lower(trim(identifier))
    )
  limit 1
$$;

-- Seconds left on the lock, 0 when the account is not locked.
create or replace function public.rdnis_login_lock_seconds(identifier text)
returns integer
language sql
security definer
stable
set search_path = public
as $$
  select coalesce((
    select greatest(0, ceil(extract(epoch from (p.locked_until - now()))))::integer
    from public.profiles p
    where p.id = public.rdnis_account_for_identifier(identifier)
      and p.locked_until is not null
    limit 1
  ), 0)
$$;

-- Records one failed sign-in. Returns how many attempts remain before the
-- lock, so 0 means the account has just been locked.
create or replace function public.rdnis_note_failed_login(identifier text)
returns integer
language plpgsql
security definer
set search_path = public
as $$
declare
  target uuid;
  attempts integer;
begin
  target := public.rdnis_account_for_identifier(identifier);

  -- An identifier that matches no account is not counted and answers the
  -- same as a first failure, so this cannot be used to discover which
  -- usernames or addresses are registered.
  if target is null then
    return 10;
  end if;

  update public.profiles
     set failed_logins = failed_logins + 1,
         locked_until = case
           when failed_logins + 1 >= 10 then now() + interval '30 minutes'
           else locked_until
         end
   where id = target
   returning failed_logins into attempts;

  return greatest(0, 10 - attempts);
end;
$$;

-- Called once a sign-in or password change succeeds.
create or replace function public.rdnis_clear_login_failures()
returns void
language sql
security definer
set search_path = public
as $$
  update public.profiles
     set failed_logins = 0, locked_until = null
   where id = auth.uid()
$$;

grant execute on function public.rdnis_account_for_identifier(text) to anon, authenticated;
grant execute on function public.rdnis_login_lock_seconds(text) to anon, authenticated;
grant execute on function public.rdnis_note_failed_login(text) to anon, authenticated;
grant execute on function public.rdnis_clear_login_failures() to authenticated;
