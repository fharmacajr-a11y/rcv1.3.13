-- RPC ping para health-check leve e estável
create or replace function public.ping()
returns text
language sql
stable
set search_path = public
as $$
  select 'ok'::text;
$$;

grant execute on function public.ping() to anon, authenticated;
