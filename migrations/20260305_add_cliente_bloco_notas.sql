-- =============================================================================
-- Migration: 20260305_add_cliente_bloco_notas
-- Descrição: Cria tabela e RPC para o campo "Bloco de notas" por cliente.
-- Tabela de clientes: public.clients (padrão do projeto)
-- =============================================================================

-- 1) Tabela (1:1 por cliente)
create table if not exists public.cliente_bloco_notas (
  cliente_id bigint primary key references public.clients(id) on delete cascade,
  org_id     uuid        not null,
  body       text        not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_cliente_bloco_notas_org_id
  on public.cliente_bloco_notas (org_id);

alter table public.cliente_bloco_notas enable row level security;

-- 2) Políticas RLS (mesmo padrão do rc_notes: org_id vindo do JWT claim)
do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename  = 'cliente_bloco_notas'
      and policyname = 'cliente_bloco_notas_select_same_org'
  ) then
    create policy cliente_bloco_notas_select_same_org
      on public.cliente_bloco_notas for select
      to authenticated
      using (org_id = (current_setting('request.jwt.claims', true)::jsonb ->> 'org_id')::uuid);
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename  = 'cliente_bloco_notas'
      and policyname = 'cliente_bloco_notas_ins_same_org'
  ) then
    create policy cliente_bloco_notas_ins_same_org
      on public.cliente_bloco_notas for insert
      to authenticated
      with check (org_id = (current_setting('request.jwt.claims', true)::jsonb ->> 'org_id')::uuid);
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename  = 'cliente_bloco_notas'
      and policyname = 'cliente_bloco_notas_upd_same_org'
  ) then
    create policy cliente_bloco_notas_upd_same_org
      on public.cliente_bloco_notas for update
      to authenticated
      using     (org_id = (current_setting('request.jwt.claims', true)::jsonb ->> 'org_id')::uuid)
      with check (org_id = (current_setting('request.jwt.claims', true)::jsonb ->> 'org_id')::uuid);
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename  = 'cliente_bloco_notas'
      and policyname = 'cliente_bloco_notas_del_same_org'
  ) then
    create policy cliente_bloco_notas_del_same_org
      on public.cliente_bloco_notas for delete
      to authenticated
      using (org_id = (current_setting('request.jwt.claims', true)::jsonb ->> 'org_id')::uuid);
  end if;
end $$;

-- 3) Trigger para updated_at
create or replace function public.rc_set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

drop trigger if exists trg_cliente_bloco_notas_updated_at on public.cliente_bloco_notas;
create trigger trg_cliente_bloco_notas_updated_at
before update on public.cliente_bloco_notas
for each row execute function public.rc_set_updated_at();

-- 4) RPC de salvar (upsert) / apagar (se vazio)
create or replace function public.rc_save_cliente_bloco_notas(
  p_cliente_id bigint,
  p_body       text
)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v_org_id uuid;
begin
  if p_cliente_id is null then
    raise exception 'cliente_id é obrigatório';
  end if;

  -- Pega org_id a partir do cliente
  select c.org_id into v_org_id
  from public.clients c
  where c.id = p_cliente_id;

  if v_org_id is null then
    raise exception 'Cliente % não encontrado ou sem org_id', p_cliente_id;
  end if;

  -- Se vazio, remove o registro (equivalente a "limpar notas")
  if p_body is null or btrim(p_body) = '' then
    delete from public.cliente_bloco_notas
    where cliente_id = p_cliente_id;
    return;
  end if;

  insert into public.cliente_bloco_notas (cliente_id, org_id, body)
  values (p_cliente_id, v_org_id, p_body)
  on conflict (cliente_id) do update
    set body       = excluded.body,
        updated_at = now();
end;
$$;

grant execute on function public.rc_save_cliente_bloco_notas(bigint, text)
  to authenticated;

-- 5) RPC de leitura (SECURITY DEFINER para bypassar RLS)
create or replace function public.rc_get_cliente_bloco_notas(
  p_cliente_id bigint
)
returns text
language plpgsql
security definer
set search_path = public
as $$
declare
  v_body text;
begin
  if p_cliente_id is null then
    return '';
  end if;

  select body into v_body
  from public.cliente_bloco_notas
  where cliente_id = p_cliente_id;

  return coalesce(v_body, '');
end;
$$;

grant execute on function public.rc_get_cliente_bloco_notas(bigint)
  to authenticated;
