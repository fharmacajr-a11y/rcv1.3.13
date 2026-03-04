-- ============================================================================
-- Migration: RPC atômica para salvar contatos de cliente
-- Data: 2026-03-03
-- Autor: PR4 – Integridade de dados
--
-- COMO APLICAR:
--   1. Abra o Supabase Dashboard → SQL Editor
--   2. Cole o conteúdo deste arquivo e clique em "Run"
--   3. Verifique na aba "Functions" que rc_save_cliente_contatos aparece
--
-- O QUE FAZ:
--   Substitui a sequência DELETE + INSERT por uma ÚNICA transação atômica.
--   Se o INSERT falhar, o DELETE é revertido automaticamente (rollback).
--
-- SEGURANÇA:
--   SECURITY INVOKER (padrão) — executa com as permissões do usuário
--   que chama a função, respeitando todas as políticas RLS existentes.
-- ============================================================================

CREATE OR REPLACE FUNCTION public.rc_save_cliente_contatos(
  p_cliente_id bigint,
  p_contatos   jsonb
)
RETURNS void
LANGUAGE plpgsql
SECURITY INVOKER
AS $$
BEGIN
  -- 1. Validação
  IF p_cliente_id IS NULL THEN
    RAISE EXCEPTION 'cliente_id é obrigatório';
  END IF;

  -- 2. Deletar contatos antigos do cliente
  DELETE FROM public.cliente_contatos
  WHERE cliente_id = p_cliente_id;

  -- 3. Se não há contatos novos, encerra (só fez o delete)
  IF p_contatos IS NULL
     OR jsonb_typeof(p_contatos) <> 'array'
     OR jsonb_array_length(p_contatos) = 0
  THEN
    RETURN;
  END IF;

  -- 4. Inserir novos contatos a partir do array JSONB
  INSERT INTO public.cliente_contatos (cliente_id, nome, whatsapp)
  SELECT
    p_cliente_id,
    r.nome,
    r.whatsapp
  FROM jsonb_to_recordset(p_contatos) AS r(
    nome     text,
    whatsapp text
  );
END;
$$;

-- Permissão para usuários autenticados chamarem a função
GRANT EXECUTE ON FUNCTION public.rc_save_cliente_contatos(bigint, jsonb)
  TO authenticated;
