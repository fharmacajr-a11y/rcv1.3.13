# -*- coding: utf-8 -*-
"""Service layer para jobs de exportação ZIP (client-side only).

Responsabilidades do desktop app:
- Chamar Edge Function para criar/iniciar job
- Polling de status do job
- Cancelamento cooperativo (sinalizar ao servidor)
- Obter signed URL do artefato pronto
- Baixar artefato final para disco local
- Marcar job como concluído

O processamento pesado (scanning, zipping, upload ao Storage)
acontece inteiramente no servidor via Edge Function zip-export.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Callable, Optional

from src.modules.uploads.zip_job_models import (
    ZipJob,
    ZipJobPhase,
)

_log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceções
# ---------------------------------------------------------------------------


class ZipJobError(Exception):
    """Erro genérico de ZIP job."""


class ZipJobNotFoundError(ZipJobError):
    """Job não encontrado."""


class ZipJobInvalidTransitionError(ZipJobError):
    """Transição de fase inválida."""


class ZipJobCancelledError(ZipJobError):
    """Job foi cancelado."""


class ZipJobFailedError(ZipJobError):
    """Job falhou no servidor."""


# ---------------------------------------------------------------------------
# Acesso ao Supabase (lazy imports para evitar ciclos)
# ---------------------------------------------------------------------------


def _get_supabase():
    from src.infra.supabase.db_client import get_supabase

    return get_supabase()


def _exec(builder: Any) -> Any:
    from src.infra.supabase.db_client import exec_postgrest

    return exec_postgrest(builder)


_TABLE = "zip_export_jobs"

# ---------------------------------------------------------------------------
# Edge Function URL
# ---------------------------------------------------------------------------

_zip_url_logged = False


def _get_zip_export_url() -> str:
    """Resolve a URL da Edge Function 'zip-export'.

    Prioridade:
      1. ZIP_EXPORT_FUNCTION_URL (dev local) — se definida no ambiente.
      2. SUPABASE_URL + /functions/v1/zip-export (produção/executável).
    """
    global _zip_url_logged  # noqa: PLW0603
    override = os.getenv("ZIP_EXPORT_FUNCTION_URL")
    if override:
        final = override.rstrip("/")
        if not _zip_url_logged:
            _log.info("[zip-export] URL: %s (dev override via ZIP_EXPORT_FUNCTION_URL)", final)
            _zip_url_logged = True
        return final
    from src.infra.supabase import types as supa_types

    url = os.getenv("SUPABASE_URL") or supa_types.SUPABASE_URL
    if not url:
        raise RuntimeError("SUPABASE_URL não está configurada.")
    final = f"{url}/functions/v1/zip-export"
    if not _zip_url_logged:
        _log.info("[zip-export] URL: %s (remoto via SUPABASE_URL)", final)
        _zip_url_logged = True
    return final


def _get_auth_headers() -> dict[str, str]:
    """Retorna headers de autenticação para Edge Function.

    Usa o access_token da sessão do user logado (JWT real) no Authorization,
    e a anon key no apikey (exigido pelo Supabase API Gateway).
    """
    from src.infra.supabase import types as supa_types

    anon_key = os.getenv("SUPABASE_ANON_KEY") or supa_types.SUPABASE_ANON_KEY or ""

    # Obter JWT da sessão do user logado
    access_token = ""
    try:
        sb = _get_supabase()
        session = sb.auth.get_session()
        if session:
            access_token = getattr(session, "access_token", "") or ""
    except Exception:
        pass

    # Fallback: se sem sessão, usa anon key (vai falhar na Edge Function com 401)
    bearer = access_token or anon_key

    return {
        "Authorization": f"Bearer {bearer}",
        "apikey": anon_key,
        "Content-Type": "application/json",
    }


# ---------------------------------------------------------------------------
# CRUD (leitura direta do Postgres)
# ---------------------------------------------------------------------------


def get_zip_job(job_id: str) -> ZipJob:
    """Obtém o estado atual de um job pelo ID."""
    sb = _get_supabase()
    resp = _exec(sb.table(_TABLE).select("*").eq("id", job_id).limit(1))
    rows = resp.data if hasattr(resp, "data") else resp
    if not rows:
        raise ZipJobNotFoundError(f"Job {job_id} não encontrado")
    return ZipJob.from_row(rows[0])


def update_zip_job(
    job_id: str,
    *,
    phase: Optional[ZipJobPhase] = None,
    message: Optional[str] = None,
    progress: Optional[dict[str, Any]] = None,
    artifact_storage_path: Optional[str] = None,
    error_detail: Optional[str] = None,
    cancel_requested: Optional[bool] = None,
    started_at: Optional[str] = None,
    completed_at: Optional[str] = None,
) -> ZipJob:
    """Atualiza campos de um job no Postgres."""
    patch: dict[str, Any] = {}

    if phase is not None:
        patch["phase"] = phase.value
    if message is not None:
        patch["message"] = message
    if progress is not None:
        patch.update(progress)
    if artifact_storage_path is not None:
        patch["artifact_storage_path"] = artifact_storage_path
    if error_detail is not None:
        patch["error_detail"] = error_detail
    if cancel_requested is not None:
        patch["cancel_requested"] = cancel_requested
    if started_at is not None:
        patch["started_at"] = started_at
    if completed_at is not None:
        patch["completed_at"] = completed_at

    if not patch:
        return get_zip_job(job_id)

    sb = _get_supabase()
    _exec(sb.table(_TABLE).update(patch).eq("id", job_id))
    # Reler o job atualizado (select após update não suportado nesta versão do client)
    return get_zip_job(job_id)


def delete_zip_job(job_id: str) -> bool:
    """Remove um job terminal (limpeza)."""
    sb = _get_supabase()
    try:
        _exec(sb.table(_TABLE).delete().eq("id", job_id))
        return True
    except Exception:
        _log.exception("Erro ao deletar job %s", job_id)
        return False


# ---------------------------------------------------------------------------
# Operações de alto nível (client → server)
# ---------------------------------------------------------------------------


def start_zip_export(
    *,
    org_id: str,
    client_id: int,
    bucket: str,
    prefix: str,
    zip_name: str,
) -> ZipJob:
    """Cria e inicia um job de exportação ZIP no servidor.

    Chama a Edge Function zip-export via POST. O servidor cria o registro
    na tabela zip_export_jobs e dispara o processamento em background
    com EdgeRuntime.waitUntil().

    requested_by é derivado do JWT server-side — não enviado pelo client.

    Returns:
        ZipJob criado com fase 'queued' (ou 'scanning' se já iniciou).
    """
    from src.infra.net_session import make_session

    payload: dict[str, Any] = {
        "org_id": org_id,
        "client_id": client_id,
        "bucket": bucket,
        "prefix": prefix,
        "zip_name": zip_name,
    }

    sess = make_session()
    url = _get_zip_export_url()
    headers = _get_auth_headers()

    _log.info("[zip-export] POST %s  payload=%s", url, payload)
    resp = sess.post(url, json=payload, headers=headers, timeout=(10, 30))
    _log.info("[zip-export] Resposta: HTTP %s", resp.status_code)

    if resp.status_code not in (200, 201):
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text[:500]
        raise ZipJobError(f"Falha ao criar job de exportação ZIP (HTTP {resp.status_code}): {detail}")

    data = resp.json()
    job_id = data.get("job_id") or data.get("id")
    if not job_id:
        raise ZipJobError("Resposta do servidor não contém job_id")

    return get_zip_job(job_id)


def cancel_zip_job(job_id: str) -> ZipJob:
    """Solicita cancelamento cooperativo de um job.

    Seta cancel_requested=True. O executor server-side checa periodicamente
    e transita para cancelling → cancelled.
    """
    _log.info("[zip-export] cancel_zip_job solicitado para job %s", job_id[:8])
    job = get_zip_job(job_id)

    if job.phase.is_terminal:
        _log.info("[zip-export] cancel_zip_job: job %s já terminal (%s) — ignorado", job_id[:8], job.phase.value)
        return job

    if not job.phase.is_cancellable:
        _log.warning("[zip-export] cancel_zip_job: job %s fase %s não cancelável", job_id[:8], job.phase.value)
        return job

    updated = update_zip_job(
        job_id,
        cancel_requested=True,
        message="Cancelamento solicitado…",
    )
    _log.info("[zip-export] cancel_zip_job: PATCH enviado, fase atual=%s", updated.phase.value)
    return updated


def poll_zip_job(
    job_id: str,
    *,
    interval_s: float = 1.5,
    timeout_s: float = 600.0,
    on_progress: Optional[Callable[[ZipJob], None]] = None,
    cancel_event: Optional[threading.Event] = None,
) -> ZipJob:
    """Faz polling do status de um job até que ele atinja uma fase terminal ou 'ready'.

    Args:
        job_id: ID do job a acompanhar.
        interval_s: Intervalo entre polls (segundos).
        timeout_s: Timeout máximo de espera (segundos).
        on_progress: Callback chamado a cada poll com estado atualizado.
        cancel_event: Event para interromper o polling (cancelamento local).

    Returns:
        ZipJob na fase 'ready' ou terminal.

    Raises:
        ZipJobCancelledError: Se job foi cancelado.
        ZipJobFailedError: Se job falhou.
        TimeoutError: Se timeout expirou sem atingir fase terminal/ready.
    """
    deadline = time.monotonic() + timeout_s
    _prev_phase: str | None = None
    _poll_count = 0
    _last_heartbeat = time.monotonic()
    _heartbeat_interval = 30  # segundos entre heartbeats no console

    while True:
        if cancel_event and cancel_event.is_set():
            _log.info("[zip-export] Polling cancelado localmente (job %s, polls=%d)", job_id[:8], _poll_count)
            raise ZipJobCancelledError("Polling cancelado pelo cliente")

        job = get_zip_job(job_id)
        _poll_count += 1

        # Log quando a fase muda (evita spam)
        cur_phase = job.phase.value
        if cur_phase != _prev_phase:
            _log.info(
                "[zip-export] job %s fase: %s → %s (poll #%d)", job_id[:8], _prev_phase or "—", cur_phase, _poll_count
            )
            _prev_phase = cur_phase
            _last_heartbeat = time.monotonic()
        elif time.monotonic() - _last_heartbeat >= _heartbeat_interval:
            elapsed = int(time.monotonic() - (deadline - timeout_s))
            _log.info("[zip-export] job %s ainda em %s (poll #%d, %ds)", job_id[:8], cur_phase, _poll_count, elapsed)
            _last_heartbeat = time.monotonic()

        if on_progress:
            on_progress(job)

        if job.phase == ZipJobPhase.READY:
            _log.info("[zip-export] job %s pronto após %d polls", job_id[:8], _poll_count)
            return job

        if job.phase == ZipJobPhase.CANCELLED:
            _log.info("[zip-export] job %s cancelado pelo servidor (polls=%d)", job_id[:8], _poll_count)
            raise ZipJobCancelledError(job.message or "Job cancelado")

        if job.phase == ZipJobPhase.FAILED:
            _log.error("[zip-export] job %s FALHOU: %s", job_id[:8], job.error_detail or job.message)
            raise ZipJobFailedError(job.error_detail or job.message or "Job falhou")

        if job.phase == ZipJobPhase.COMPLETED:
            return job

        if time.monotonic() >= deadline:
            _log.error("[zip-export] job %s TIMEOUT após %ds (%d polls)", job_id[:8], timeout_s, _poll_count)
            raise TimeoutError(f"Timeout ({timeout_s}s) aguardando job {job_id}")

        time.sleep(interval_s)


def get_artifact_url(
    job_id: str,
    *,
    expires_in: int = 300,
    cancel_event: Optional[threading.Event] = None,
) -> str:
    """Obtém signed URL para download do artefato ZIP pronto.

    A URL é gerada server-side pela Edge Function (service role),
    mantendo o bucket de exports privado sem storage policies para o user.

    Args:
        job_id: ID do job.
        expires_in: Ignorado — validade controlada pela Edge Function (5 min).
        cancel_event: Se setado antes OU durante o request HTTP, levanta
            ZipJobCancelledError imediatamente, sem retornar a URL.

    Returns:
        URL assinada para download direto.
    """
    from src.infra.net_session import make_session

    # Guarda de corrida: abortar ANTES do request se já cancelado.
    if cancel_event and cancel_event.is_set():
        raise ZipJobCancelledError("Signed URL abortada: cancelamento solicitado antes do request")

    url = _get_zip_export_url()
    headers = _get_auth_headers()
    sess = make_session()

    _log.info("[zip-export] GET signed URL para job %s", job_id[:8])
    resp = sess.get(f"{url}?job_id={job_id}", headers=headers, timeout=(10, 30))

    # Guarda de corrida: cancel pode ter sido setado DURANTE o request HTTP.
    # Sem esta verificação, o log "Signed URL recebida" e o download iniciariam
    # mesmo após o usuário cancelar ou fechar a janela.
    if cancel_event and cancel_event.is_set():
        raise ZipJobCancelledError("Signed URL abortada: cancelamento solicitado durante o request")

    if resp.status_code == 404:
        raise ZipJobNotFoundError(f"Job {job_id} não encontrado")
    if resp.status_code != 200:
        _log.error("[zip-export] Falha signed URL job %s: HTTP %s", job_id[:8], resp.status_code)
        raise ZipJobError(f"Falha ao consultar job {job_id} (HTTP {resp.status_code})")

    data = resp.json()
    download_url = data.get("download_url")
    _log.info("[zip-export] Signed URL recebida para job %s", job_id[:8])

    if not download_url:
        phase = data.get("phase", "?")
        raise ZipJobError(
            f"Job {job_id} não possui download_url (fase: {phase}). " "O artefato pode ainda não estar pronto."
        )

    return download_url


def download_artifact(
    job_id: str,
    save_path: str,
    *,
    cancel_event: Optional[threading.Event] = None,
    progress_cb: Optional[Callable[[int, int], None]] = None,
) -> Path:
    """Baixa o artefato ZIP pronto para o disco local via signed URL.

    Args:
        job_id: ID do job.
        save_path: Caminho local de destino.
        cancel_event: Event para cancelar o download.
        progress_cb: Callback (bytes_escritos, bytes_esperados).

    Returns:
        Path do arquivo salvo.
    """
    from src.infra.supabase.storage_client import DownloadCancelledError
    from src.infra.net_session import make_session

    # Verificar cancelamento ANTES de consumir a signed URL (quota no servidor)
    if cancel_event and cancel_event.is_set():
        raise DownloadCancelledError("Download cancelado antes de obter signed URL")

    # Passa cancel_event para get_artifact_url: ela verifica antes e depois do
    # request HTTP, fechando a janela de race entre o polling retornar READY e
    # o usuário cancelar/fechar enquanto o GET de signed URL está em voo.
    url = get_artifact_url(job_id, cancel_event=cancel_event)
    _log.info("[zip-export] Iniciando download do artefato (job %s) → %s", job_id[:8], save_path)

    # Marcar job como downloading_artifact
    try:
        job = get_zip_job(job_id)
        if job.phase == ZipJobPhase.READY:
            update_zip_job(
                job_id,
                phase=ZipJobPhase.DOWNLOADING_ARTIFACT,
                message="Baixando artefato…",
            )
    except Exception:
        _log.debug("Erro ao marcar job %s como downloading_artifact", job_id)

    dest = Path(save_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = dest.with_suffix(dest.suffix + ".part")

    sess = make_session()
    _promoted = False

    try:
        with sess.get(url, stream=True, timeout=(15, 300)) as resp:
            if resp.status_code != 200:
                raise ZipJobError(f"Falha ao baixar artefato (HTTP {resp.status_code})")

            expected = 0
            try:
                expected = int(resp.headers.get("Content-Length") or "0")
            except (ValueError, TypeError):
                pass

            written = 0
            with open(tmp_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=256 * 1024):
                    if cancel_event and cancel_event.is_set():
                        raise DownloadCancelledError("Download cancelado pelo usuário")

                    if not chunk:
                        continue

                    f.write(chunk)
                    written += len(chunk)

                    if progress_cb:
                        try:
                            progress_cb(written, expected)
                        except Exception:
                            pass

            if cancel_event and cancel_event.is_set():
                raise DownloadCancelledError("Download cancelado no final")

            if expected and written != expected:
                raise IOError(f"Download truncado: {written}B != {expected}B")

            os.replace(tmp_path, dest)
            _promoted = True
            _log.info("[zip-export] Download concluído: %s (%d bytes)", dest.name, written)

    finally:
        if not _promoted:
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass

    # Marcar job como completed
    try:
        update_zip_job(
            job_id,
            phase=ZipJobPhase.COMPLETED,
            message="Download concluído",
            completed_at="now()",
        )
    except Exception:
        _log.debug("Erro ao marcar job %s como completed", job_id)

    return dest
