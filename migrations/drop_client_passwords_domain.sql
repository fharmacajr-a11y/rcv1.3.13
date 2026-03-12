-- migration: drop_client_passwords_domain.sql
-- Fase C: Remoção completa do domínio legado de Senhas (client_passwords)
--
-- QUANDO APLICAR:
--   Após o deploy do código da Fase C — o app não faz mais nenhuma consulta
--   à tabela client_passwords. Esta migration remove a tabela e todos os
--   objetos exclusivos do domínio Senhas no Supabase.
--
-- COMO APLICAR:
--   Execute no SQL Editor do Supabase Dashboard, ou via psql:
--     psql "$DATABASE_URL" -f migrations/drop_client_passwords_domain.sql
--
-- IRREVERSÍVEL: faça backup antes de aplicar em produção.
-- Não afeta nenhuma outra tabela (clients, memberships, organizations, etc.).

-- 1) Remover políticas RLS exclusivas da tabela
do $$
declare
  pol record;
begin
  for pol in
    select policyname
      from pg_policies
     where schemaname = 'public'
       and tablename  = 'client_passwords'
  loop
    execute format('drop policy if exists %I on public.client_passwords', pol.policyname);
  end loop;
end $$;

-- 2) Remover índices exclusivos (o DROP TABLE abaixo os remove automaticamente,
--    mas listamos explicitamente para clareza)
drop index if exists public.idx_client_passwords_org_id;
drop index if exists public.idx_client_passwords_client_id;

-- 3) Remover a tabela
drop table if exists public.client_passwords cascade;

-- 4) Nenhuma view, função ou trigger exclusivo do domínio Senhas foi
--    identificado nas migrations versionadas do repositório.
--    Se existirem objetos adicionais criados diretamente no Supabase,
--    liste-os aqui antes de aplicar em produção.
