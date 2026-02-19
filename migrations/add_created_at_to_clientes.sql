-- Adicionar coluna created_at à tabela clientes
ALTER TABLE public.clientes ADD COLUMN IF NOT EXISTS created_at timestamptz DEFAULT now();
