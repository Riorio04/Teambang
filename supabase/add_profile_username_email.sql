alter table public.profiles
  add column if not exists username text,
  add column if not exists email text;

create unique index if not exists profiles_username_lower_unique
  on public.profiles (lower(username))
  where username is not null and username <> '';

create unique index if not exists profiles_email_lower_unique
  on public.profiles (lower(email))
  where email is not null and email <> '';

create or replace function public.profile_email_for_username(username_input text)
returns text
language sql
security definer
set search_path = public
as $$
  select p.email
  from public.profiles p
  where lower(p.username) = lower(username_input)
  limit 1
$$;

grant execute on function public.profile_email_for_username(text) to anon, authenticated;

-- Accounts created before sign-up started recording the address have a null
-- profiles.email, which leaves them unable to sign in by username and
-- invisible to any lookup that reads this column. Auth holds the real
-- address, so copy it across. Safe to re-run; it only fills the gaps.
update public.profiles p
   set email = u.email
  from auth.users u
 where u.id = p.id
   and u.email is not null
   and (p.email is null or p.email = '');
