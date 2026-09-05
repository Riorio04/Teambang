create or replace function public.landing_project_type_counts()
returns table (
  project_type text,
  project_count bigint
)
language sql
security definer
set search_path = public
as $$
  select
    p.project_type::text,
    count(*)::bigint
  from public.projects as p
  where p.project_type in ('infra', 'machineries', 'ssip', 'fmr')
  group by p.project_type
$$;

grant execute on function public.landing_project_type_counts() to anon, authenticated;
