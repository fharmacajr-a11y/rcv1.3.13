
-- Tabela de clientes (snake_case)
create table if not exists public.clientes (
  id bigserial primary key,
  numero text,
  nome text,
  razao_social text,
  cnpj text,
  obs text,
  ultima_alteracao timestamptz default now(),
  deleted_at timestamptz,
  org_id uuid null,   -- opcional: se usar organizações
  user_id uuid null   -- quem criou/alterou (preencher do lado cliente, opcional)
);

-- Índices úteis
create index if not exists idx_clientes_cnpj on public.clientes (cnpj);
create index if not exists idx_clientes_numero on public.clientes (numero);
create index if not exists idx_clientes_deleted_at on public.clientes (deleted_at);

-- Habilita RLS
alter table public.clientes enable row level security;

-- Política simples: qualquer usuário autenticado pode acessar.
-- Reforce conforme seu modelo (org_id/memberships).
do $$
begin
  if not exists (
    select 1 from pg_policies
     where schemaname='public' and tablename='clientes' and policyname='auth users can read'
  ) then
    create policy "auth users can read"
      on public.clientes for select
      to authenticated
      using ( true );
  end if;

  if not exists (
    select 1 from pg_policies
     where schemaname='public' and tablename='clientes' and policyname='auth users can insert'
  ) then
    create policy "auth users can insert"
      on public.clientes for insert
      to authenticated
      with check ( true );
  end if;

  if not exists (
    select 1 from pg_policies
     where schemaname='public' and tablename='clientes' and policyname='auth users can update own org'
  ) then
    create policy "auth users can update own org"
      on public.clientes for update
      to authenticated
      using ( true )
      with check ( true );
  end if;

  if not exists (
    select 1 from pg_policies
     where schemaname='public' and tablename='clientes' and policyname='auth users can delete soft'
  ) then
    create policy "auth users can delete soft"
      on public.clientes for delete
      to authenticated
      using ( true );
  end if;
end $$;

-- Exemplo de política multi-tenant por organização (se usar tabela memberships(user_id, org_id)):
-- substitute policies above with:
-- create policy "org members select"
--   on public.clientes for select
--   to authenticated
--   using ( exists (select 1 from public.memberships m where m.user_id = auth.uid() and m.org_id = clientes.org_id) );
-- create policy "org members ins/upd/del"
--   on public.clientes for all
--   to authenticated
--   using ( exists (select 1 from public.memberships m where m.user_id = auth.uid() and m.org_id = clientes.org_id) )
--   with check ( exists (select 1 from public.memberships m where m.user_id = auth.uid() and m.org_id = clientes.org_id) );
