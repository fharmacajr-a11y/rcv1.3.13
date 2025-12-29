-- Migração: Notificações "Excluir pra mim"
-- Data: 2025-12-26
-- Descrição: Adiciona tabelas para ocultar notificações por usuário (sem deletar do feed global)

-- ============================================================================
-- TABELA 1: Estado por usuário (para "Excluir todas" via timestamp)
-- ============================================================================
create table if not exists public.org_notifications_user_state (
    org_id uuid not null,
    user_id uuid not null,
    hidden_before timestamptz not null default '1970-01-01T00:00:00Z',
    updated_at timestamptz not null default now(),
    primary key (org_id, user_id)
);

-- ============================================================================
-- TABELA 2: Hides pontuais (para "Excluir selecionada")
-- ============================================================================
create table if not exists public.org_notifications_hidden (
    org_id uuid not null,
    user_id uuid not null,
    notification_id uuid not null,
    created_at timestamptz not null default now(),
    primary key (org_id, user_id, notification_id)
);

-- ============================================================================
-- HABILITAR RLS
-- ============================================================================
alter table public.org_notifications_user_state enable row level security;
alter table public.org_notifications_hidden enable row level security;

-- ============================================================================
-- POLICIES: org_notifications_user_state
-- ============================================================================

-- SELECT: usuário só vê seu próprio registro + deve pertencer à org
drop policy if exists "notif_state_select_own" on public.org_notifications_user_state;
create policy "notif_state_select_own"
on public.org_notifications_user_state
for select
using (
    user_id = auth.uid()
    and exists (
        select 1 from public.memberships m
        where m.user_id = auth.uid()
          and m.org_id = org_notifications_user_state.org_id
    )
);

-- INSERT: usuário só insere para si mesmo + deve pertencer à org
drop policy if exists "notif_state_insert_own" on public.org_notifications_user_state;
create policy "notif_state_insert_own"
on public.org_notifications_user_state
for insert
with check (
    user_id = auth.uid()
    and exists (
        select 1 from public.memberships m
        where m.user_id = auth.uid()
          and m.org_id = org_notifications_user_state.org_id
    )
);

-- UPDATE: usuário só atualiza seu próprio registro
drop policy if exists "notif_state_update_own" on public.org_notifications_user_state;
create policy "notif_state_update_own"
on public.org_notifications_user_state
for update
using (user_id = auth.uid())
with check (user_id = auth.uid());

-- DELETE: usuário só deleta seu próprio registro
drop policy if exists "notif_state_delete_own" on public.org_notifications_user_state;
create policy "notif_state_delete_own"
on public.org_notifications_user_state
for delete
using (user_id = auth.uid());

-- ============================================================================
-- POLICIES: org_notifications_hidden
-- ============================================================================

-- SELECT: usuário só vê seus próprios hides + deve pertencer à org
drop policy if exists "notif_hidden_select_own" on public.org_notifications_hidden;
create policy "notif_hidden_select_own"
on public.org_notifications_hidden
for select
using (
    user_id = auth.uid()
    and exists (
        select 1 from public.memberships m
        where m.user_id = auth.uid()
          and m.org_id = org_notifications_hidden.org_id
    )
);

-- INSERT: usuário só insere para si mesmo + deve pertencer à org
drop policy if exists "notif_hidden_insert_own" on public.org_notifications_hidden;
create policy "notif_hidden_insert_own"
on public.org_notifications_hidden
for insert
with check (
    user_id = auth.uid()
    and exists (
        select 1 from public.memberships m
        where m.user_id = auth.uid()
          and m.org_id = org_notifications_hidden.org_id
    )
);

-- DELETE: usuário só deleta seus próprios hides
drop policy if exists "notif_hidden_delete_own" on public.org_notifications_hidden;
create policy "notif_hidden_delete_own"
on public.org_notifications_hidden
for delete
using (user_id = auth.uid());

-- ============================================================================
-- (Opcional) Se der erro de schema cache, rode:
-- NOTIFY pgrst, 'reload schema';
-- ============================================================================
