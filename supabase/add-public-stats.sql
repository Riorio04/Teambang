-- Landing page statistics for RDNIS.
--
-- Visitors are not signed in and cannot read the project tables, so the four
-- figures on the landing page come from this function instead. It is security
-- definer so it can count the rows, and it returns only the counts.
--
-- The stage of a project mirrors projectStage() in index.html; keep the two in
-- step if either changes.

create or replace function public.rdnis_public_stats()
returns jsonb
language sql
security definer
stable
set search_path = public
as $$
  with stage as (
    select
      p.project_type::text as project_type,
      case
        when coalesce((
          select pg.percent_complete
          from public.project_progress pg
          where pg.project_id = p.id
          order by pg.entry_date desc, pg.id desc
          limit 1
        ), 0) >= 100 then 'completed'

        when (
          select count(*)
          from jsonb_array_elements(
            case
              when jsonb_typeof(coalesce(p.scurve_plan, '[]')::jsonb) = 'array'
                then coalesce(p.scurve_plan, '[]')::jsonb
              else '[]'::jsonb
            end
          ) as point
          where nullif(point ->> 'date', '') is not null
        ) >= 2 then 'ongoing'

        when exists (
          select 1 from public.project_requirements r where r.project_id = p.id
        ) and not exists (
          select 1 from public.project_requirements r
          where r.project_id = p.id and r.status is distinct from 'complete'
        ) then 'for_implementation'

        else 'pending'
      end as stage
    from public.projects p
  )
  select jsonb_build_object(
    'total',              (select count(*) from stage),
    'for_implementation', (select count(*) from stage where stage = 'for_implementation'),
    'ongoing',            (select count(*) from stage where stage = 'ongoing'),
    'completed',          (select count(*) from stage where stage = 'completed'),
    'pending',            (select count(*) from stage where stage = 'pending'),
    'by_type', coalesce((
      select jsonb_object_agg(project_type, n)
      from (
        select project_type, count(*) as n
        from stage
        where project_type is not null
        group by project_type
      ) counts
    ), '{}'::jsonb)
  );
$$;

grant execute on function public.rdnis_public_stats() to anon, authenticated;
