-- Migration: Adicionar colunas de status secundário na tabela public.clients
-- Data: 2026-03-15
-- Descrição: Adiciona status_anvisa e status_farmacia_popular como colunas
--            independentes (text null).  O status principal continua sendo
--            extraído do campo obs (prefixo legado [Status] texto).
--
-- Como aplicar:
--   python scripts/apply_migration.py migrations/20260315_add_status_anvisa_farmacia_popular.sql

ALTER TABLE public.clients
    ADD COLUMN IF NOT EXISTS status_anvisa           text NULL,
    ADD COLUMN IF NOT EXISTS status_farmacia_popular text NULL;

COMMENT ON COLUMN public.clients.status_anvisa
    IS 'Status do processo Anvisa. NULL ou ausente = sem processo ativo.';

COMMENT ON COLUMN public.clients.status_farmacia_popular
    IS 'Status do processo Farmácia Popular. NULL ou ausente = sem processo ativo.';
