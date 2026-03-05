-- =============================================================================
-- Migration: 20260305_unique_cnpj_norm_per_org
-- Descrição: Cria unique partial index em (org_id, cnpj_norm) para clientes
--            ativos (deleted_at IS NULL) com CNPJ preenchido.
--            Previne inserções duplicadas de CNPJ na mesma organização.
-- =============================================================================

-- Unique partial index: impede duplicação de cnpj_norm por org_id,
-- apenas para clientes ativos (deleted_at IS NULL) e com CNPJ preenchido.
CREATE UNIQUE INDEX IF NOT EXISTS uq_clients_org_cnpj_norm_active
  ON public.clients (org_id, cnpj_norm)
  WHERE deleted_at IS NULL
    AND cnpj_norm IS NOT NULL
    AND cnpj_norm <> '';
