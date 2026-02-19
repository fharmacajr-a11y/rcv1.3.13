-- Migration: Adicionar colunas is_pinned e is_done à tabela rc_notes
-- Arquivo: migrations/rc_notes_add_pin_done_columns.sql
-- Data: 2025-01-10
-- Descrição: Permite marcar notas como fixadas ou concluídas (Micro-fase 5)

-- Adicionar coluna is_pinned (padrão: false)
ALTER TABLE rc_notes
ADD COLUMN IF NOT EXISTS is_pinned boolean NOT NULL DEFAULT false;

-- Adicionar coluna is_done (padrão: false)
ALTER TABLE rc_notes
ADD COLUMN IF NOT EXISTS is_done boolean NOT NULL DEFAULT false;

-- Adicionar política de UPDATE para permitir alteração de is_pinned e is_done
-- Apenas da mesma org e apenas essas colunas específicas
CREATE POLICY IF NOT EXISTS rc_notes_update_flags_same_org
ON rc_notes FOR UPDATE
TO authenticated
USING (org_id = (current_setting('request.jwt.claims', true)::jsonb ->> 'org_id')::uuid)
WITH CHECK (org_id = (current_setting('request.jwt.claims', true)::jsonb ->> 'org_id')::uuid);

-- Comentários nas novas colunas
COMMENT ON COLUMN rc_notes.is_pinned IS 'Nota fixada no topo (destacada)';
COMMENT ON COLUMN rc_notes.is_done IS 'Nota marcada como concluída';
