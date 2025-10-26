-- Migration: Criar tabela de notas compartilhadas por organização
-- Arquivo: migrations/rc_notes_migration.sql

-- Tabela de notas (compartilhada por org, append-only)
create table if not exists rc_notes (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null,
  author_email text not null,
  body text not null check (char_length(body) between 1 and 1000),
  created_at timestamptz not null default now()
);

-- Índice para busca eficiente por org + ordenação por data
create index if not exists rc_notes_org_created_idx
  on rc_notes (org_id, created_at desc);

-- Habilitar Row Level Security (RLS)
alter table rc_notes enable row level security;

-- Política: SELECT apenas notas da mesma org (via JWT claim)
create policy rc_notes_select_same_org
on rc_notes for select
to authenticated
using (org_id = (current_setting('request.jwt.claims', true)::jsonb ->> 'org_id')::uuid);

-- Política: INSERT apenas para mesma org (via JWT claim)
create policy rc_notes_insert_same_org
on rc_notes for insert
to authenticated
with check (org_id = (current_setting('request.jwt.claims', true)::jsonb ->> 'org_id')::uuid);

-- NÃO criar políticas de UPDATE/DELETE
-- Isso força o comportamento append-only: usuários podem apenas ler e inserir,
-- mas não podem editar ou apagar notas existentes.

-- Comentários na tabela
comment on table rc_notes is 'Notas compartilhadas por organização (append-only)';
comment on column rc_notes.org_id is 'UUID da organização proprietária';
comment on column rc_notes.author_email is 'Email do autor da anotação';
comment on column rc_notes.body is 'Texto da anotação (1-1000 chars)';
comment on column rc_notes.created_at is 'Data/hora de criação (UTC)';
