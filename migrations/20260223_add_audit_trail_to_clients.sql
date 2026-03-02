-- Migration: Audit trail para tabela public.clients
-- Data: 2026-02-23
-- Descrição: Adiciona colunas de rastreamento de autoria (UUID) e trigger
--            PL/pgSQL que as preenche automaticamente usando auth.uid().
--            A coluna ultima_por (texto/e-mail) existente é MANTIDA para
--            compatibilidade com clientes antigos.

-- ---------------------------------------------------------------------------
-- Passo 1 — Adicionar colunas de auditoria
-- ---------------------------------------------------------------------------

ALTER TABLE public.clients
    ADD COLUMN IF NOT EXISTS updated_by  uuid NULL,
    ADD COLUMN IF NOT EXISTS deleted_by  uuid NULL,
    ADD COLUMN IF NOT EXISTS restored_by uuid NULL;

COMMENT ON COLUMN public.clients.updated_by  IS 'auth.uid() de quem fez o último UPDATE (preenchido por trigger).';
COMMENT ON COLUMN public.clients.deleted_by  IS 'auth.uid() de quem moveu para a lixeira (preenchido por trigger).';
COMMENT ON COLUMN public.clients.restored_by IS 'auth.uid() de quem restaurou da lixeira (preenchido por trigger).';

-- ---------------------------------------------------------------------------
-- Passo 2 — Função PL/pgSQL do trigger
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.fn_clients_audit_trail()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER          -- roda com os privilégios do owner, mas usa auth.uid() para o JWT atual
SET search_path = public  -- evita path injection
AS $$
DECLARE
    _uid uuid;
BEGIN
    -- Obtém o UUID do usuário autenticado via JWT (disponível quando a
    -- requisição chega com Authorization: Bearer <supabase-jwt>).
    -- Em chamadas server-side sem JWT, auth.uid() retorna NULL.
    _uid := auth.uid();

    -- Sempre registra quem fez a última alteração
    NEW.updated_by := _uid;

    -- Detecta transição de lixeira (soft-delete)
    IF TG_OP = 'UPDATE' THEN
        IF NEW.deleted_at IS NOT NULL AND OLD.deleted_at IS NULL THEN
            -- Cliente foi movido para a lixeira nesta operação
            NEW.deleted_by  := _uid;
            NEW.restored_by := NULL;   -- limpa restauração anterior, se houver
        ELSIF NEW.deleted_at IS NULL AND OLD.deleted_at IS NOT NULL THEN
            -- Cliente foi restaurado da lixeira nesta operação
            NEW.restored_by := _uid;
            NEW.deleted_by  := NULL;   -- limpa deleted_by ao restaurar
        END IF;
    END IF;

    -- Em INSERT, limpa campos que não fazem sentido ainda
    IF TG_OP = 'INSERT' THEN
        NEW.deleted_by  := NULL;
        NEW.restored_by := NULL;
    END IF;

    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION public.fn_clients_audit_trail() IS
    'Preenche updated_by/deleted_by/restored_by com auth.uid() antes de cada INSERT ou UPDATE em public.clients.';

-- ---------------------------------------------------------------------------
-- Passo 3 — Criar o trigger (idempotente via DROP IF EXISTS)
-- ---------------------------------------------------------------------------

DROP TRIGGER IF EXISTS trg_clients_audit_trail ON public.clients;

CREATE TRIGGER trg_clients_audit_trail
    BEFORE INSERT OR UPDATE
    ON public.clients
    FOR EACH ROW
    EXECUTE FUNCTION public.fn_clients_audit_trail();

-- ---------------------------------------------------------------------------
-- Passo 4 — Índices para consultas de auditoria
-- ---------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_clients_updated_by  ON public.clients (updated_by);
CREATE INDEX IF NOT EXISTS idx_clients_deleted_by  ON public.clients (deleted_by);
CREATE INDEX IF NOT EXISTS idx_clients_restored_by ON public.clients (restored_by);

-- ---------------------------------------------------------------------------
-- Nota sobre ambientes sem trigger (desenvolvimento local sem Supabase Auth):
-- As colunas aceitam NULL; o app NÃO precisa setá-las manualmente.
-- O campo ultima_por (texto) continua sendo gravado app-side para
-- compatibilidade com telas legadas e ambientes offline.
-- ---------------------------------------------------------------------------
