-- Migration: Adicionar coluna display_name em profiles
-- Data: 2025-10-19
-- Descrição: Permite configurar nome de exibição personalizado para cada usuário

-- Adicionar coluna display_name (idempotente)
alter table public.profiles
add column if not exists display_name text;

-- Comentário da coluna
comment on column public.profiles.display_name is
'Nome de exibição personalizado do usuário (ex: "Junior", "Maria Silva")';

-- Índice para performance (opcional)
create index if not exists idx_profiles_display_name
on public.profiles(display_name)
where display_name is not null;
