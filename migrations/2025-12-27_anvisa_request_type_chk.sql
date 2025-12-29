-- Migration: Atualiza CHECK constraint de request_type na tabela client_anvisa_requests
-- Data: 2025-12-27
-- Descrição: Adiciona novos tipos de demanda ANVISA:
--   - "Alteração de Endereço"
--   - "Alteração de Nome Fantasia"
--   - "Ampliação de Atividades"
--   - "Redução de Atividades"
--   - "Concessão de AFE (Inicial)"
--   - "AFE ANVISA"
--   - "Importação de Cannabidiol"
--   - "Concessão de AE Manipulação"
--
-- Executar no Supabase SQL Editor (Dashboard > SQL Editor > New Query)

BEGIN;

-- Remove constraint antiga (se existir)
ALTER TABLE public.client_anvisa_requests
  DROP CONSTRAINT IF EXISTS client_anvisa_requests_request_type_chk;

-- Adiciona constraint atualizada com todos os tipos (ordem alfabética)
ALTER TABLE public.client_anvisa_requests
  ADD CONSTRAINT client_anvisa_requests_request_type_chk
  CHECK (
    request_type = ANY (ARRAY[
      'AFE ANVISA'::text,
      'Alteração da Razão Social'::text,
      'Alteração de Endereço'::text,
      'Alteração de Nome Fantasia'::text,
      'Alteração de Porte'::text,
      'Alteração do Responsável Legal'::text,
      'Alteração do Responsável Técnico'::text,
      'Ampliação de Atividades'::text,
      'Associação ao SNGPC'::text,
      'Cancelamento de AFE'::text,
      'Concessão de AE Manipulação'::text,
      'Concessão de AFE (Inicial)'::text,
      'Importação de Cannabidiol'::text,
      'Redução de Atividades'::text
    ])
  );

COMMIT;
