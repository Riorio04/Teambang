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
