"""
Servicos de dominio do modulo Auditoria.

Este modulo concentra:
- operacoes de dados (listar/iniciar/atualizar/excluir auditorias e clientes) via Supabase;
- operacoes de storage (resolver bucket/prefixo, garantir pastas e enviar/remover arquivos);
- wrappers para utilitarios de arquivos definidos em infra.archive_utils (ZIP/RAR/7z).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

try:
    from infra.supabase_client import get_supabase  # type: ignore[import-untyped]
except Exception:

    def get_supabase():  # type: ignore[no-redef]
        return None


from . import archives, repository, storage
from .archives import (
    ArchiveError,
    AuditoriaArchiveEntry,
    AuditoriaArchivePlan,
    AuditoriaUploadProgress,
    AuditoriaUploadResult,
)
from .storage import AuditoriaStorageContext, AuditoriaUploadContext

_ORG_ID_CACHE: str = ""

# Re-exportações para API pública do módulo
__all__ = [
    "ArchiveError",
    "AuditoriaArchiveEntry",
    "AuditoriaArchivePlan",
    "AuditoriaUploadProgress",
    "AuditoriaUploadResult",
    "AuditoriaStorageContext",
    "AuditoriaUploadContext",
]


class AuditoriaServiceError(RuntimeError):
    """Erro generico da camada de servico de Auditoria."""


class AuditoriaOfflineError(AuditoriaServiceError):
    """Erro levantado quando o Supabase nao esta disponivel."""


def _get_supabase_client() -> Any | None:
    try:
        return get_supabase()
    except Exception:
        return None


def _require_supabase() -> Any:
    sb = _get_supabase_client()
    if not sb:
        raise AuditoriaOfflineError("Supabase client is not available.")
    return sb


def get_supabase_client() -> Any | None:
    return _get_supabase_client()


def is_online() -> bool:
    return get_supabase_client() is not None


# --- API de dados (CRUD Auditoria) ---


def fetch_clients() -> list[dict[str, Any]]:
    sb = _require_supabase()
    try:
        return repository.fetch_clients(sb)
    except Exception as exc:
        raise AuditoriaServiceError(f"Falha ao carregar clientes: {exc}") from exc


def list_clients_minimal() -> list[dict[str, Any]]:
    return fetch_clients()


def fetch_auditorias() -> list[dict[str, Any]]:
    sb = _require_supabase()
    try:
        return repository.fetch_auditorias(sb)
    except Exception as exc:
        raise AuditoriaServiceError(f"Falha ao carregar auditorias: {exc}") from exc


def list_auditorias() -> list[dict[str, Any]]:
    return fetch_auditorias()


def start_auditoria(cliente_id: int, *, status: str = "em_andamento") -> dict[str, Any]:
    sb = _require_supabase()
    payload = {"cliente_id": cliente_id, "status": status}
    try:
        res = repository.insert_auditoria(sb, payload)
    except Exception as exc:
        raise AuditoriaServiceError(f"Nao foi possivel iniciar auditoria: {exc}") from exc
    data = getattr(res, "data", None) or []
    if not data:
        raise AuditoriaServiceError("Supabase nao retornou dados da auditoria criada.")
    return data[0]


def update_auditoria_status(auditoria_id: str, status: str) -> dict[str, Any]:
    sb = _require_supabase()
    try:
        res = repository.update_auditoria(sb, auditoria_id, status)
    except Exception as exc:
        raise AuditoriaServiceError(f"Nao foi possivel atualizar status: {exc}") from exc
    data = getattr(res, "data", None) or []
    if not data:
        raise AuditoriaServiceError("Auditoria nao encontrada para atualizacao.")
    return data[0]


def delete_auditorias(auditoria_ids: Iterable[str | int]) -> None:
    ids: list[str] = []
    for raw_id in auditoria_ids:
        if raw_id in (None, ""):
            continue
        text = str(raw_id).strip()
        if text:
            ids.append(text)
    if not ids:
        return
    sb = _require_supabase()
    try:
        repository.delete_auditorias(sb, ids)
    except Exception as exc:
        raise AuditoriaServiceError(f"Falha ao excluir auditorias: {exc}") from exc


# --- API de storage (Supabase + buckets) ---


def get_current_org_id(*, force_refresh: bool = False) -> str:
    global _ORG_ID_CACHE
    if _ORG_ID_CACHE and not force_refresh:
        return _ORG_ID_CACHE
    sb = _require_supabase()
    try:
        uid = repository.fetch_current_user_id(sb)
        org_id = repository.fetch_org_id_for_user(sb, uid)
        _ORG_ID_CACHE = str(org_id)
        return _ORG_ID_CACHE
    except LookupError as exc:
        raise AuditoriaServiceError(str(exc)) from exc
    except Exception as exc:
        raise AuditoriaServiceError(f"Nao foi possivel determinar o org_id: {exc}") from exc


def reset_org_cache() -> None:
    global _ORG_ID_CACHE
    _ORG_ID_CACHE = ""


def get_clients_bucket() -> str:
    return storage.get_clients_bucket()


def build_client_prefix(client_id: int, org_id: str) -> str:
    return storage.build_client_prefix(client_id, org_id)


def get_storage_context(client_id: int, *, org_id: str | None = None) -> AuditoriaStorageContext:
    resolved_org = org_id or get_current_org_id()
    return storage.make_storage_context(client_id, resolved_org)


def ensure_auditoria_folder(client_id: int, *, org_id: str | None = None) -> None:
    ctx = get_storage_context(client_id, org_id=org_id)
    sb = _require_supabase()
    try:
        storage.ensure_auditoria_folder(sb, ctx)
    except Exception as exc:
        raise AuditoriaServiceError(f"Falha ao criar pasta de Auditoria: {exc}") from exc


def list_existing_file_names(bucket: str, prefix: str, *, page_size: int = 1000) -> set[str]:
    sb = _require_supabase()
    try:
        return storage.list_existing_file_names(sb, bucket, prefix, page_size=page_size)
    except Exception as exc:
        raise AuditoriaServiceError(f"Falha ao listar arquivos existentes: {exc}") from exc


def upload_storage_bytes(
    bucket: str,
    dest_path: str,
    data: bytes,
    *,
    content_type: str,
    upsert: bool = False,
    cache_control: str = "3600",
) -> None:
    sb = _require_supabase()
    try:
        storage.upload_storage_bytes(
            sb,
            bucket,
            dest_path,
            data,
            content_type=content_type,
            upsert=upsert,
            cache_control=cache_control,
        )
    except Exception as exc:
        raise AuditoriaServiceError(f"Falha ao enviar arquivo para o Storage: {exc}") from exc


def remove_storage_objects(bucket: str, paths: Sequence[str]) -> None:
    if not paths:
        return
    sb = _require_supabase()
    try:
        storage.remove_storage_objects(sb, bucket, paths)
    except Exception as exc:
        raise AuditoriaServiceError(f"Falha ao remover arquivos do Storage: {exc}") from exc


# --- Pipeline de upload/arquivos de auditoria ---


def ensure_storage_ready() -> None:
    if not is_online():
        raise AuditoriaOfflineError("Supabase client is not available.")
    bucket = get_clients_bucket()
    if not bucket:
        raise AuditoriaServiceError("Defina RC_STORAGE_BUCKET_CLIENTS para habilitar o Storage.")


def prepare_upload_context(client_id: int, *, org_id: str | None = None) -> AuditoriaUploadContext:
    ctx = get_storage_context(client_id, org_id=org_id)
    return AuditoriaUploadContext(bucket=ctx.bucket, base_prefix=ctx.auditoria_prefix, org_id=ctx.org_id, client_id=client_id)


def prepare_archive_plan(archive_path: str | Path) -> AuditoriaArchivePlan:
    try:
        return archives.prepare_archive_plan(archive_path, extract_func=extract_archive_to)
    except ValueError as exc:
        raise AuditoriaServiceError(str(exc)) from exc


def cleanup_archive_plan(plan: AuditoriaArchivePlan | None) -> None:
    archives.cleanup_archive_plan(plan)


def list_existing_names_for_context(context: AuditoriaUploadContext) -> set[str]:
    return list_existing_file_names(context.bucket, context.base_prefix)


def detect_duplicate_file_names(plan: AuditoriaArchivePlan, existing_names: set[str]) -> set[str]:
    return archives.detect_duplicate_file_names(plan, existing_names)


def execute_archive_upload(
    plan: AuditoriaArchivePlan,
    context: AuditoriaUploadContext,
    *,
    strategy: str,
    existing_names: set[str],
    duplicates: set[str],
    cancel_check: Callable[[], bool] | None = None,
    progress_callback: Callable[[AuditoriaUploadProgress], None] | None = None,
) -> AuditoriaUploadResult:
    try:
        return archives.execute_archive_upload(
            plan,
            context,
            strategy=strategy,
            existing_names=existing_names,
            duplicates=duplicates,
            upload_callback=upload_storage_bytes,
            cancel_check=cancel_check,
            progress_callback=progress_callback,
        )
    except ValueError as exc:
        raise AuditoriaServiceError(str(exc)) from exc


def rollback_uploaded_paths(context: AuditoriaUploadContext, uploaded_paths: Iterable[str]) -> None:
    remove_storage_objects(context.bucket, list(uploaded_paths))


def extract_archive_to(source: str | Path, target_folder: str | Path) -> Path:
    return archives.extract_archive_to(source, target_folder)


def is_supported_archive(path: str | Path) -> bool:
    return archives.is_supported_archive(path)


# --- Fachadas publicas ----------------------------------------------------------


@dataclass(frozen=True)
class AuditoriaDataService:
    fetch_clients = staticmethod(fetch_clients)
    fetch_auditorias = staticmethod(fetch_auditorias)
    start_auditoria = staticmethod(start_auditoria)
    update_auditoria_status = staticmethod(update_auditoria_status)
    delete_auditorias = staticmethod(delete_auditorias)


@dataclass(frozen=True)
class AuditoriaStorageService:
    is_online = staticmethod(is_online)
    get_supabase_client = staticmethod(get_supabase_client)
    get_current_org_id = staticmethod(get_current_org_id)
    reset_org_cache = staticmethod(reset_org_cache)
    get_clients_bucket = staticmethod(get_clients_bucket)
    build_client_prefix = staticmethod(build_client_prefix)
    get_storage_context = staticmethod(get_storage_context)
    ensure_auditoria_folder = staticmethod(ensure_auditoria_folder)
    list_existing_file_names = staticmethod(list_existing_file_names)
    upload_storage_bytes = staticmethod(upload_storage_bytes)
    remove_storage_objects = staticmethod(remove_storage_objects)
    extract_archive_to = staticmethod(extract_archive_to)
    is_supported_archive = staticmethod(is_supported_archive)
    ensure_storage_ready = staticmethod(ensure_storage_ready)
    prepare_upload_context = staticmethod(prepare_upload_context)
    prepare_archive_plan = staticmethod(prepare_archive_plan)
    cleanup_archive_plan = staticmethod(cleanup_archive_plan)
    list_existing_names_for_context = staticmethod(list_existing_names_for_context)
    detect_duplicate_file_names = staticmethod(detect_duplicate_file_names)
    execute_archive_upload = staticmethod(execute_archive_upload)
    rollback_uploaded_paths = staticmethod(rollback_uploaded_paths)
