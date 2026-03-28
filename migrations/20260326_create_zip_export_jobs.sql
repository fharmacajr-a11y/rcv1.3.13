-- Migration: zip_export_jobs
-- Tabela de jobs de exportação ZIP com fases, métricas e cancelamento cooperativo.
-- Processamento server-side via Edge Function + EdgeRuntime.waitUntil().
-- Artefato final salvo no Supabase Storage, download via signed URL.

CREATE TABLE IF NOT EXISTS public.zip_export_jobs (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          text NOT NULL,
    client_id       bigint NOT NULL,
    bucket          text NOT NULL,
    prefix          text NOT NULL,
    zip_name        text NOT NULL,

    -- Fase do job (máquina de estados server-side)
    phase           text NOT NULL DEFAULT 'queued'
        CHECK (phase IN (
            'queued',
            'scanning',
            'zipping',
            'uploading_artifact',
            'ready',
            'downloading_artifact',
            'completed',
            'cancelling',
            'cancelled',
            'failed'
        )),

    -- Métricas de progresso reais (persistidas pelo executor server-side)
    total_files           int     NOT NULL DEFAULT 0,
    processed_files       int     NOT NULL DEFAULT 0,
    total_source_bytes    bigint  NOT NULL DEFAULT 0,
    processed_source_bytes bigint NOT NULL DEFAULT 0,
    artifact_bytes_total  bigint  NOT NULL DEFAULT 0,
    artifact_bytes_uploaded bigint NOT NULL DEFAULT 0,

    -- Mensagem de status legível (para UI)
    message         text NOT NULL DEFAULT '',

    -- Caminho do artefato ZIP no Supabase Storage (key relativa ao bucket)
    artifact_storage_path   text,

    -- Erro capturado (em caso de falha)
    error_detail    text,

    -- Flag de cancelamento cooperativo (executor server-side checa periodicamente)
    cancel_requested boolean NOT NULL DEFAULT false,

    -- Timestamps
    created_at      timestamptz NOT NULL DEFAULT now(),
    started_at      timestamptz,
    completed_at    timestamptz,
    updated_at      timestamptz NOT NULL DEFAULT now(),

    -- Quem solicitou
    requested_by    uuid REFERENCES auth.users(id)
);

-- Índice para polling por org_id + client_id (cenário mais comum)
CREATE INDEX IF NOT EXISTS idx_zip_export_jobs_org_client
    ON public.zip_export_jobs (org_id, client_id, created_at DESC);

-- Índice para limpeza de jobs antigos
CREATE INDEX IF NOT EXISTS idx_zip_export_jobs_phase_created
    ON public.zip_export_jobs (phase, created_at);

-- RLS: usuários autenticados só podem SELECT jobs da própria org.
-- INSERT/UPDATE/DELETE são feitos via service role (Edge Function) que bypassa RLS.
ALTER TABLE public.zip_export_jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY zip_export_jobs_select_own_org ON public.zip_export_jobs
    FOR SELECT
    TO authenticated
    USING (
        org_id IN (
            SELECT m.org_id FROM public.memberships m
            WHERE m.user_id = auth.uid()
        )
    );

-- Trigger para atualizar updated_at automaticamente
CREATE OR REPLACE FUNCTION public.trg_zip_export_jobs_updated_at()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS zip_export_jobs_updated_at ON public.zip_export_jobs;
CREATE TRIGGER zip_export_jobs_updated_at
    BEFORE UPDATE ON public.zip_export_jobs
    FOR EACH ROW EXECUTE FUNCTION public.trg_zip_export_jobs_updated_at();
