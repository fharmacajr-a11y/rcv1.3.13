/**
 * Edge Function: zip-export
 *
 * Exportação ZIP server-side com progresso real e cancelamento cooperativo.
 *
 * POST  /zip-export — Cria job e inicia processamento em background
 * GET   /zip-export?job_id=X — Status/progresso (inclui download_url quando ready)
 * PATCH /zip-export — Solicita cancelamento de um job
 *
 * Segurança:
 *   - POST valida JWT e verifica membership na org_id (403 se não membro)
 *   - requested_by é derivado do JWT (NUNCA aceito do body)
 *   - GET/PATCH usam auth client (RLS) para garantir isolamento por org
 *   - Bucket de exports é privado; signed URL gerado server-side no GET
 *
 * Fluxo (background via EdgeRuntime.waitUntil):
 *   queued → scanning → zipping → uploading_artifact → ready
 *
 * completed_at é setado apenas em fases terminais (completed, cancelled, failed),
 * NUNCA em ready (o client ainda precisa baixar o artefato).
 */

import "@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "@supabase/supabase-js";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_ANON_KEY = Deno.env.get("SUPABASE_ANON_KEY")!;
const EXPORT_BUCKET = Deno.env.get("ZIP_EXPORT_BUCKET") || "zip-exports";

// Service role key: aceita SUPABASE_SERVICE_ROLE_KEY ou SUPABASE_SECRET_KEY.
// Pelo menos uma DEVE estar definida no --env-file passado ao `functions serve`.
const SUPABASE_SERVICE_ROLE_KEY = (() => {
  const key =
    Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ||
    Deno.env.get("SUPABASE_SECRET_KEY");
  if (!key) {
    throw new Error(
      "Missing service role key. Set SUPABASE_SERVICE_ROLE_KEY or SUPABASE_SECRET_KEY in your --env-file.",
    );
  }
  return key;
})();

/**
 * Limite de segurança para geração in-memory (200 MB de source files).
 * Acima disso o job falha com mensagem clara. Para volumes maiores,
 * seria necessário streaming ZIP via /tmp (Supabase Edge Functions expõe
 * /tmp com escrita) usando uma lib como fflate — mas o caso típico do
 * RC Gestor (< 50 MB por pasta de cliente) fica bem dentro deste limite.
 *
 * Nota: Edge Functions no plano Pro têm ~256 MB de memória disponível.
 * Com overhead de runtime + buffers, 200 MB de source é um teto seguro.
 */
const MAX_SOURCE_BYTES = 200 * 1024 * 1024;

const TABLE = "zip_export_jobs";

/**
 * Buckets de origem permitidos para exportação.
 * Impede que o client, via body do POST, force a Edge Function (service role)
 * a ler de buckets arbitrários.
 */
const ALLOWED_SOURCE_BUCKETS: ReadonlySet<string> = new Set([
  "rc-docs",
  // Adicionar outros buckets legítimos aqui se necessário.
]);

// Admin client (service role — bypassa RLS para INSERT/UPDATE do job)
function getAdminClient() {
  return createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);
}

// Auth client (respeita RLS — usado para SELECT em GET/PATCH)
function getAuthClient(authHeader: string) {
  const token = authHeader.replace("Bearer ", "");
  return createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
    global: { headers: { Authorization: `Bearer ${token}` } },
  });
}

// ─── Types ──────────────────────────────────────────────────────────

interface JobRow {
  id: string;
  org_id: string;
  client_id: number;
  bucket: string;
  prefix: string;
  zip_name: string;
  phase: string;
  cancel_requested: boolean;
  artifact_storage_path?: string;
  [key: string]: unknown;
}

interface FileEntry {
  /** Caminho completo no Storage (bucket-relative). */
  storagePath: string;
  /** Caminho relativo ao prefix do job — preservado dentro do ZIP. */
  relativePath: string;
  /** Tamanho em bytes (metadata.size). */
  size: number;
}

// ─── Helpers ────────────────────────────────────────────────────────

async function updateJob(
  admin: ReturnType<typeof getAdminClient>,
  jobId: string,
  patch: Record<string, unknown>,
): Promise<void> {
  const { error } = await admin.from(TABLE).update(patch).eq("id", jobId);
  if (error) console.error(`Failed to update job ${jobId}:`, error.message);
}

async function isCancelled(
  admin: ReturnType<typeof getAdminClient>,
  jobId: string,
): Promise<boolean> {
  const { data } = await admin
    .from(TABLE)
    .select("cancel_requested")
    .eq("id", jobId)
    .single();
  return data?.cancel_requested === true;
}

async function failJob(
  admin: ReturnType<typeof getAdminClient>,
  jobId: string,
  detail: string,
): Promise<void> {
  await updateJob(admin, jobId, {
    phase: "failed",
    error_detail: detail.slice(0, 500),
    message: "Falha na geração do ZIP",
    completed_at: new Date().toISOString(),
  });
}

async function cancelJob(
  admin: ReturnType<typeof getAdminClient>,
  jobId: string,
): Promise<void> {
  await updateJob(admin, jobId, {
    phase: "cancelling",
    message: "Cancelando…",
  });
  await updateJob(admin, jobId, {
    phase: "cancelled",
    message: "Cancelado pelo usuário",
    completed_at: new Date().toISOString(),
  });
}

// ─── Recursive file listing ─────────────────────────────────────────

/**
 * Lista recursivamente todos os arquivos sob `prefix` no bucket.
 *
 * O Supabase Storage `.list()` retorna apenas um nível. Itens sem `id`
 * (ou com metadata nulo) são tratados como pastas e percorridos recursivamente.
 *
 * `basePrefix` é o prefix original do job — usado para calcular o caminho
 * relativo que será preservado dentro do ZIP.
 */
async function listFilesRecursive(
  admin: ReturnType<typeof getAdminClient>,
  bucket: string,
  prefix: string,
  basePrefix: string,
): Promise<FileEntry[]> {
  const results: FileEntry[] = [];

  const { data: entries, error } = await admin.storage
    .from(bucket)
    .list(prefix, { limit: 10000 });

  if (error || !entries) return results;

  for (const entry of entries) {
    const fullPath = prefix ? `${prefix}/${entry.name}` : entry.name;

    if (entry.id && !entry.name.endsWith("/")) {
      // Arquivo — calcular path relativo preservando subpastas
      const relativePath = fullPath.slice(basePrefix.length).replace(/^\//, "");
      results.push({
        storagePath: fullPath,
        relativePath,
        size: (entry.metadata as Record<string, number>)?.size || 0,
      });
    } else {
      // Pasta — recursar
      const subFiles = await listFilesRecursive(admin, bucket, fullPath, basePrefix);
      results.push(...subFiles);
    }
  }

  return results;
}

// ─── Core processing ────────────────────────────────────────────────

async function processJob(jobId: string, job: JobRow): Promise<void> {
  const admin = getAdminClient();
  const t0 = Date.now();
  const log = (msg: string) => console.log(`[zip-export][${jobId.slice(0, 8)}] ${msg}`);
  const elapsed = () => `${((Date.now() - t0) / 1000).toFixed(1)}s`;

  try {
    // ── Phase: scanning ──
    if (await isCancelled(admin, jobId)) {
      await cancelJob(admin, jobId);
      return;
    }

    log(`Iniciando job (bucket=${job.bucket}, prefix=${job.prefix})`);

    await updateJob(admin, jobId, {
      phase: "scanning",
      message: "Escaneando arquivos…",
      started_at: new Date().toISOString(),
    });

    const fileEntries = await listFilesRecursive(
      admin,
      job.bucket,
      job.prefix,
      job.prefix,
    );

    const totalFiles = fileEntries.length;
    const totalSourceBytes = fileEntries.reduce((sum, f) => sum + f.size, 0);

    log(`Scanning concluído: ${totalFiles} arquivos, ${(totalSourceBytes / 1024 / 1024).toFixed(1)} MB (${elapsed()})`);

    await updateJob(admin, jobId, {
      total_files: totalFiles,
      total_source_bytes: totalSourceBytes,
      processed_files: 0,
      processed_source_bytes: 0,
      message: `Encontrados ${totalFiles} arquivo(s)…`,
    });

    if (totalFiles === 0) {
      await failJob(admin, jobId, "Nenhum arquivo encontrado no prefix");
      return;
    }

    // Guard: rejeitar se source total exceder limite para in-memory
    if (totalSourceBytes > MAX_SOURCE_BYTES) {
      const mbTotal = (totalSourceBytes / 1024 / 1024).toFixed(0);
      const mbLimit = (MAX_SOURCE_BYTES / 1024 / 1024).toFixed(0);
      await failJob(
        admin,
        jobId,
        `Tamanho total (${mbTotal} MB) excede o limite de ${mbLimit} MB para exportação ZIP.`,
      );
      return;
    }

    // ── Phase: zipping ──
    if (await isCancelled(admin, jobId)) {
      await cancelJob(admin, jobId);
      return;
    }

    await updateJob(admin, jobId, {
      phase: "zipping",
      message: "Gerando arquivo ZIP…",
    });

    log(`Iniciando download+zip de ${totalFiles} arquivos (${elapsed()})`);

    /*
     * ZIP gerado em memória via fflate — ~10x mais eficiente em CPU do que JSZip.
     * JSZip causava "CPU Time exceeded" no Supabase Edge Functions para pastas
     * maiores (ex: 37 MB / 12 arquivos) porque seu CRC32 em JS puro consumia
     * todo o orçamento de CPU antes de concluir generateAsync.
     * fflate usa operações TypedArray otimizadas e CRC32 com lookup table,
     * ficando bem dentro do limite mesmo para o caso problemático (cliente 312/sifap).
     * Todos os arquivos usam level:0 (STORE) — PDFs, imagens e Office já são
     * comprimidos; DEFLATE não reduziria tamanho mas aumentaria CPU.
     */
    type FflateFiles = Record<string, [Uint8Array, { level: number }]>;
    const fflateFiles: FflateFiles = {};

    let processedFiles = 0;
    let processedBytes = 0;

    for (const file of fileEntries) {
      if (processedFiles % 5 === 0 && (await isCancelled(admin, jobId))) {
        await cancelJob(admin, jobId);
        return;
      }

      const { data: fileData, error: dlError } = await admin.storage
        .from(job.bucket)
        .download(file.storagePath);

      if (dlError) {
        await failJob(
          admin,
          jobId,
          `Falha ao baixar arquivo ${file.storagePath}: ${dlError.message}`,
        );
        return;
      }

      if (fileData) {
        const arrayBuffer = await fileData.arrayBuffer();
        fflateFiles[file.relativePath] = [new Uint8Array(arrayBuffer), { level: 0 }];
        processedBytes += arrayBuffer.byteLength;
      }

      processedFiles++;

      if (processedFiles % 5 === 0 || processedFiles === totalFiles) {
        await updateJob(admin, jobId, {
          processed_files: processedFiles,
          processed_source_bytes: processedBytes,
          message: `Comprimindo… ${processedFiles}/${totalFiles} — ${file.relativePath}`,
        });
      }
    }

    // ── Generate ZIP blob ──
    if (await isCancelled(admin, jobId)) {
      await cancelJob(admin, jobId);
      return;
    }

    log(`Todos os ${totalFiles} arquivos adicionados (${(processedBytes / 1024 / 1024).toFixed(1)} MB). Iniciando zip (fflate)… (${elapsed()})`);
    await updateJob(admin, jobId, {
      message: `Gerando arquivo ZIP final… (${totalFiles} arquivo(s), ${(processedBytes / 1024 / 1024).toFixed(1)} MB)`,
    });

    let zipBlob: ArrayBuffer;
    try {
      const { zip: fflateZip } = await import("https://esm.sh/fflate@0.8.2");
      const zipData = await new Promise<Uint8Array>((resolve, reject) => {
        fflateZip(fflateFiles, (err, data) => {
          if (err) reject(err);
          else resolve(data);
        });
      });
      zipBlob = zipData.buffer as ArrayBuffer;
    } catch (genErr) {
      log(`ERRO em fflate.zip: ${genErr} (${elapsed()})`);
      await failJob(admin, jobId, `Falha ao gerar ZIP: ${String(genErr)}`);
      return;
    }

    const artifactSize = zipBlob.byteLength;
    log(`Blob ZIP gerado: ${(artifactSize / 1024 / 1024).toFixed(1)} MB (${elapsed()})`);

    // ── Phase: uploading_artifact ──
    if (await isCancelled(admin, jobId)) {
      await cancelJob(admin, jobId);
      return;
    }

    log(`Iniciando upload do artefato (${(artifactSize / 1024 / 1024).toFixed(1)} MB)… (${elapsed()})`);
    await updateJob(admin, jobId, {
      phase: "uploading_artifact",
      message: "Enviando artefato para Storage…",
      artifact_bytes_total: artifactSize,
      artifact_bytes_uploaded: 0,
    });

    const storagePath = `exports/${jobId}/${job.zip_name}`;

    const { error: uploadError } = await admin.storage
      .from(EXPORT_BUCKET)
      .upload(storagePath, zipBlob, {
        contentType: "application/zip",
        upsert: true,
      });

    if (uploadError) {
      log(`ERRO no upload: ${uploadError.message} (${elapsed()})`);
      await failJob(admin, jobId, `Erro ao fazer upload: ${uploadError.message}`);
      return;
    }

    log(`Upload concluído (${elapsed()})`);

    // ── Phase: ready ──
    // NÃO seta completed_at: o job só está "pronto para download",
    // completed_at será setado quando o client concluir o download (fase completed).
    await updateJob(admin, jobId, {
      phase: "ready",
      message: "ZIP pronto para download",
      artifact_storage_path: storagePath,
      artifact_bytes_uploaded: artifactSize,
      processed_files: totalFiles,
      processed_source_bytes: processedBytes,
    });

    log(`Job READY. Artefato: ${storagePath} (${elapsed()})`);
  } catch (err) {
    log(`ERRO FATAL: ${err} (${elapsed()})`);
    await failJob(admin, jobId, String(err));
  }
}

// ─── HTTP Handler ───────────────────────────────────────────────────

const CORS_HEADERS: Record<string, string> = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, PATCH, OPTIONS",
  "Access-Control-Allow-Headers": "Authorization, apikey, Content-Type",
};

function jsonResponse(body: unknown, status: number): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
  });
}

// ─── Diagnóstico defensivo: worker lifecycle ──────────────────────
// Em Supabase Edge Functions (Deno), o evento "unload" pode sinalizar
// encerramento por WORKER_LIMIT, timeout da plataforma ou shutdown inesperado.
// Ajuda a diferenciar: lentidão real | timeout | WORKER_LIMIT | crash pré-upload.
try {
  globalThis.addEventListener("unload", () => {
    console.warn(
      "[zip-export] AVISO: evento 'unload' disparado no worker — " +
      "possível WORKER_LIMIT, timeout da plataforma ou shutdown inesperado. " +
      "Se um job estava em 'zipping'/'uploading_artifact', verifique se ficou preso sem error_detail.",
    );
  });
} catch {
  // unload pode não estar disponível em todos os runtimes — ignorar silenciosamente.
}

Deno.serve(async (req: Request) => {
  const url = new URL(req.url);
  const method = req.method.toUpperCase();

  if (method === "OPTIONS") {
    return new Response(null, { headers: CORS_HEADERS });
  }

  const authHeader = req.headers.get("Authorization") || "";
  if (!authHeader) {
    return jsonResponse({ error: "Missing Authorization header" }, 401);
  }

  try {
    // ─── POST: Create job and start processing ───
    if (method === "POST") {
      // 1. Validar JWT e extrair user
      const authClient = getAuthClient(authHeader);
      const {
        data: { user },
        error: userError,
      } = await authClient.auth.getUser();

      if (userError || !user) {
        return jsonResponse({ error: "Token inválido ou expirado" }, 401);
      }

      const body = await req.json();
      const { org_id, client_id, bucket, prefix, zip_name } = body;
      // requested_by é SEMPRE derivado do JWT — nunca aceito do body

      if (!org_id || !client_id || !bucket || !prefix || !zip_name) {
        return jsonResponse(
          {
            error:
              "Missing required fields: org_id, client_id, bucket, prefix, zip_name",
          },
          400,
        );
      }

      // Validar bucket contra lista permitida (impede leitura de buckets arbitrários via service role)
      if (!ALLOWED_SOURCE_BUCKETS.has(bucket)) {
        return jsonResponse(
          { error: `Bucket não permitido para exportação: ${bucket}` },
          403,
        );
      }

      // 2. Verificar membership na org
      const admin = getAdminClient();
      const { data: membership } = await admin
        .from("memberships")
        .select("org_id")
        .eq("user_id", user.id)
        .eq("org_id", org_id)
        .limit(1)
        .maybeSingle();

      if (!membership) {
        return jsonResponse(
          { error: "Forbidden: user is not a member of this org" },
          403,
        );
      }

      // 3. Criar registro do job (requested_by vem do JWT)
      const { data: rows, error: insertError } = await admin
        .from(TABLE)
        .insert({
          org_id,
          client_id,
          bucket,
          prefix,
          zip_name,
          phase: "queued",
          message: "Aguardando início…",
          requested_by: user.id,
        })
        .select("*");

      if (insertError || !rows || rows.length === 0) {
        return jsonResponse(
          {
            error: `Failed to create job: ${insertError?.message || "unknown"}`,
          },
          500,
        );
      }

      const jobRow = rows[0] as JobRow;

      // EdgeRuntime.waitUntil mantém o worker vivo enquanto processJob roda.
      // Em dev local (deno run), EdgeRuntime não existe — fire-and-forget.
      const bgPromise = processJob(jobRow.id, jobRow);
      try {
        // @ts-ignore - EdgeRuntime disponível no Supabase Edge Functions
        EdgeRuntime.waitUntil(bgPromise);
      } catch {
        // dev local: deixa a promise rodar em background sem waitUntil
        bgPromise.catch((e: unknown) =>
          console.error(`Background job ${jobRow.id} failed:`, e),
        );
      }

      return jsonResponse({ job_id: jobRow.id, phase: jobRow.phase }, 201);
    }

    // ─── GET: Poll job status ───
    if (method === "GET") {
      const jobId = url.searchParams.get("job_id");
      if (!jobId) {
        return jsonResponse({ error: "Missing job_id parameter" }, 400);
      }

      // RLS garante isolamento por org
      const client = getAuthClient(authHeader);
      const { data, error } = await client
        .from(TABLE)
        .select("*")
        .eq("id", jobId)
        .single();

      if (error || !data) {
        return jsonResponse(
          { error: `Job not found: ${error?.message || "unknown"}` },
          404,
        );
      }

      // Gerar signed URL server-side quando artefato está pronto
      // (bucket é privado — client nunca acessa Storage diretamente)
      const responseData: Record<string, unknown> = { ...data };
      if (data.phase === "ready" && data.artifact_storage_path) {
        const admin = getAdminClient();
        const { data: signedData } = await admin.storage
          .from(EXPORT_BUCKET)
          .createSignedUrl(data.artifact_storage_path as string, 300);

        if (signedData?.signedUrl) {
          responseData.download_url = signedData.signedUrl;
        }
      }

      return jsonResponse(responseData, 200);
    }

    // ─── PATCH: Request cancellation ───
    if (method === "PATCH") {
      const body = await req.json();
      const { job_id } = body;

      if (!job_id) {
        return jsonResponse({ error: "Missing job_id" }, 400);
      }

      // RLS check via auth client
      const client = getAuthClient(authHeader);
      const { data: existing, error: fetchError } = await client
        .from(TABLE)
        .select("id, phase")
        .eq("id", job_id)
        .single();

      if (fetchError || !existing) {
        return jsonResponse({ error: "Job not found" }, 404);
      }

      const admin = getAdminClient();
      const { error: updateError } = await admin
        .from(TABLE)
        .update({
          cancel_requested: true,
          message: "Cancelamento solicitado…",
        })
        .eq("id", job_id);

      if (updateError) {
        return jsonResponse(
          { error: `Failed to cancel: ${updateError.message}` },
          500,
        );
      }

      return jsonResponse({ job_id, cancel_requested: true }, 200);
    }

    return jsonResponse({ error: "Method not allowed" }, 405);
  } catch (err) {
    console.error("zip-export error:", err);
    return jsonResponse({ error: String(err) }, 500);
  }
});
