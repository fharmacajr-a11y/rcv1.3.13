# adapters/storage/supabase_storage.py
from __future__ import annotations

import logging
import mimetypes
import os
import random
import re
import time
from pathlib import Path
from typing import Iterable, Optional, Any

# PERF-006: Import em nível de módulo
from src.core.text_normalization import normalize_ascii  # noqa: E402
from src.config.paths import CLOUD_ONLY  # noqa: E402
from src.infra.supabase_client import supabase, baixar_pasta_zip, DownloadCancelledError  # noqa: E402
from src.adapters.storage.port import StoragePort  # noqa: E402

# Alias patchável em testes (sem afetar time.sleep do restante do processo)
_sleep = time.sleep

# Constantes de retry do adapter
_UPLOAD_MAX_ATTEMPTS: int = 3
_UPLOAD_BACKOFF_BASE: float = 0.4  # segundos
_UPLOAD_BACKOFF_MAX: float = 5.0  # segundos

# Garante MIME de .docx em qualquer SO
mimetypes.add_type(
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".docx",
)

logger = logging.getLogger("infra.supabase.storage")

DEFAULT_BUCKET = (os.getenv("SUPABASE_BUCKET") or "rc-docs").strip() or "rc-docs"


class InvalidBucketNameError(ValueError):
    """Levantada quando o nome do bucket não atende às regras S3/DNS."""


# Regex: apenas [a-z0-9.-], começa e termina com [a-z0-9], pelo menos 2 bordas
_BUCKET_VALID_RE = re.compile(r"^[a-z0-9][a-z0-9.\-]*[a-z0-9]$")
# Detecta formato de IP (ex: 192.168.0.1)
_BUCKET_IP_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")


def _normalize_bucket(bucket: Optional[str]) -> str:
    """Normaliza e valida o nome do bucket conforme regras S3/DNS.

    - None  → usa DEFAULT_BUCKET (constante controlada, considerada válida)
    - str vazia/espaços → InvalidBucketNameError
    - Demais strings → lowercase + validação estrutural

    Raises:
        InvalidBucketNameError: se o nome resultante for inválido.
    """
    if bucket is None:
        return DEFAULT_BUCKET

    name = bucket.strip().lower()

    if not name:
        raise InvalidBucketNameError("Nome de bucket inválido: string vazia ou apenas espaços.")
    if len(name) < 3 or len(name) > 63:
        raise InvalidBucketNameError(
            f"Nome de bucket inválido {name!r}: deve ter entre 3 e 63 caracteres " f"(tamanho atual: {len(name)})."
        )
    if ".." in name:
        raise InvalidBucketNameError(f"Nome de bucket inválido {name!r}: não pode conter '..'.")
    if not _BUCKET_VALID_RE.match(name):
        raise InvalidBucketNameError(
            f"Nome de bucket inválido {name!r}: apenas [a-z0-9.-] são permitidos e "
            "o nome deve começar e terminar com [a-z0-9]."
        )
    if _BUCKET_IP_RE.match(name):
        raise InvalidBucketNameError(f"Nome de bucket inválido {name!r}: não pode ser um endereço IP.")
    return name


def normalize_key_for_storage(key: str) -> str:
    """Normaliza key do Storage removendo acentos APENAS do nome do arquivo (ultimo segmento).

    PERF-006: Import movido para nível de módulo.
    """
    key = key.strip("/").replace("\\", "/")
    parts = key.split("/")
    if parts:
        # Remove acentos apenas do nome do arquivo (ultimo segmento)
        filename = parts[-1]
        parts[-1] = normalize_ascii(filename)
    return "/".join(parts)


def _normalize_key(key: str) -> str:
    # Aplica normalizacao completa: remove acentos do filename + strip barras
    return normalize_key_for_storage(key)


def _guess_content_type(remote_key: str, explicit: Optional[str]) -> str:
    if explicit:
        return explicit
    guess, _ = mimetypes.guess_type(remote_key)
    return guess or "application/octet-stream"


def _is_duplicate_exc(exc: Exception) -> bool:
    """Detecta StorageApiError 409/Duplicate ou resposta HTTP 400 com corpo 409."""
    s = str(exc).lower()
    return any(t in s for t in ("duplicate", "already exists", '"409"', "statuscode: 409", "status_code: 409"))


def _is_transient_exc(exc: Exception) -> bool:
    """Retorna True se o erro é transitório e merece retry.

    Transitórios: timeouts, erros de conexão, 429, 5xx.
    Não-transitórios: 4xx (exc. 429), 409 duplicado, erros de permissão.
    """
    if _is_duplicate_exc(exc):
        return False

    s = str(exc).lower()

    # Bloqueio explícito de 400/401/403/404 (erros lógicos)
    for code in ("400", "401", "403", "404"):
        if code in s:
            return False

    # 429 rate-limit → transitório
    if "429" in s or "rate limit" in s or "too many requests" in s:
        return True

    # 5xx → transitório
    for code in range(500, 600):
        if str(code) in s:
            return True
    for kw in ("internal server", "bad gateway", "service unavailable", "gateway timeout"):
        if kw in s:
            return True

    # Erros de conexão / timeout pelo nome da classe ou mensagem
    exc_cls = type(exc).__name__.lower()
    transient_names = ("connection", "timeout", "network", "socket", "read", "write", "protocol", "dns")
    if any(t in exc_cls for t in transient_names):
        return True
    if any(t in s for t in ("connection", "timeout", "network unreachable")):
        return True

    import socket  # import local: evita poluir namespace do módulo

    if isinstance(exc, (socket.error, socket.timeout, OSError, TimeoutError, ConnectionError)):
        return True

    return False


def _read_data(source: Any) -> bytes:
    if isinstance(source, (bytes, bytearray)):
        return bytes(source)
    path = Path(source)
    with path.open("rb") as handle:
        return handle.read()


def _upload(
    client: Any,
    bucket: str,
    source: Any,
    remote_key: str,
    content_type: Optional[str],
    *,
    upsert: bool = True,
) -> str:
    key = _normalize_key(remote_key)
    file_options = {
        "content-type": _guess_content_type(key, content_type),
        # storage3 espera string, não bool (evita erro 'bool'.encode)
        "upsert": "true" if upsert else "false",
    }
    data = _read_data(source)
    data_size = len(data)

    start = time.perf_counter()
    logger.info(
        "storage.op.start: op=upload, bucket=%s, key=%s, size=%d",
        bucket,
        key,
        data_size,
    )

    last_exc: Exception | None = None
    for attempt in range(1, _UPLOAD_MAX_ATTEMPTS + 1):
        try:
            response = client.storage.from_(bucket).upload(key, data, file_options=file_options)
            if isinstance(response, dict):
                data_obj = response.get("data")
                if isinstance(data_obj, dict):
                    result_path = data_obj.get("path", key)
                else:
                    result_path = key
            else:
                result_path = key

            duration_ms = (time.perf_counter() - start) * 1000
            if attempt > 1:
                logger.info(
                    "storage.op.success (tentativa %d/%d): op=upload, bucket=%s, key=%s, size=%d, duration_ms=%.2f",
                    attempt,
                    _UPLOAD_MAX_ATTEMPTS,
                    bucket,
                    key,
                    data_size,
                    duration_ms,
                )
            else:
                logger.info(
                    "storage.op.success: op=upload, bucket=%s, key=%s, size=%d, duration_ms=%.2f",
                    bucket,
                    key,
                    data_size,
                    duration_ms,
                )
            return result_path

        except Exception as exc:
            last_exc = exc
            duration_ms = (time.perf_counter() - start) * 1000

            if _is_duplicate_exc(exc):
                logger.warning(
                    "storage.op.duplicate: op=upload, bucket=%s, key=%s, size=%d, duration_ms=%.2f"
                    " — arquivo já existe no storage (upsert não aplicado).",
                    bucket,
                    key,
                    data_size,
                    duration_ms,
                )
                raise  # duplicado não é transitório

            if not _is_transient_exc(exc):
                logger.error(
                    "storage.op.error (não-transitório): op=upload, bucket=%s, key=%s, size=%d,"
                    " duration_ms=%.2f, attempt=%d/%d, error=%s",
                    bucket,
                    key,
                    data_size,
                    duration_ms,
                    attempt,
                    _UPLOAD_MAX_ATTEMPTS,
                    type(exc).__name__,
                    exc_info=True,
                )
                raise  # sem retry

            if attempt < _UPLOAD_MAX_ATTEMPTS:
                delay = min(_UPLOAD_BACKOFF_BASE * (2 ** (attempt - 1)), _UPLOAD_BACKOFF_MAX)
                delay += random.uniform(0, delay * 0.2)  # jitter 20%  # nosec B311
                logger.warning(
                    "storage.op.retry: op=upload, bucket=%s, key=%s, attempt=%d/%d," " delay=%.2fs, error=%s — %s",
                    bucket,
                    key,
                    attempt,
                    _UPLOAD_MAX_ATTEMPTS,
                    delay,
                    type(exc).__name__,
                    exc,
                )
                _sleep(delay)
            else:
                logger.error(
                    "storage.op.error: op=upload, bucket=%s, key=%s, size=%d, duration_ms=%.2f,"
                    " tentativas_esgotadas=%d, error=%s",
                    bucket,
                    key,
                    data_size,
                    duration_ms,
                    _UPLOAD_MAX_ATTEMPTS,
                    type(exc).__name__,
                    exc_info=True,
                )

    # Relança última exceção após esgotar tentativas
    assert last_exc is not None
    raise last_exc


def _download(client: Any, bucket: str, remote_key: str, local_path: Optional[str]) -> str | bytes:
    key = _normalize_key(remote_key)

    start = time.perf_counter()
    logger.info(
        "storage.op.start: op=download, bucket=%s, key=%s",
        bucket,
        key,
    )

    try:
        data = client.storage.from_(bucket).download(key)
        if isinstance(data, dict) and "data" in data:
            data = data["data"]

        data_size = len(data) if isinstance(data, (bytes, bytearray)) else 0

        if local_path:
            target = Path(local_path)
            if not CLOUD_ONLY:
                target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("wb") as handle:
                handle.write(data)  # pyright: ignore[reportArgumentType]

            duration_ms = (time.perf_counter() - start) * 1000
            logger.info(
                "storage.op.success: op=download, bucket=%s, key=%s, size=%d, duration_ms=%.2f, local_path=%s",
                bucket,
                key,
                data_size,
                duration_ms,
                str(target),
            )
            return str(target)

        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "storage.op.success: op=download, bucket=%s, key=%s, size=%d, duration_ms=%.2f",
            bucket,
            key,
            data_size,
            duration_ms,
        )
        return data  # pyright: ignore[reportReturnType]

    except Exception as exc:
        duration_ms = (time.perf_counter() - start) * 1000
        logger.error(
            "storage.op.error: op=download, bucket=%s, key=%s, duration_ms=%.2f, error=%s",
            bucket,
            key,
            duration_ms,
            type(exc).__name__,
            exc_info=True,
        )
        raise


def _delete(client: Any, bucket: str, remote_key: str) -> bool:
    key = _normalize_key(remote_key)

    start = time.perf_counter()
    logger.info(
        "storage.op.start: op=delete, bucket=%s, key=%s",
        bucket,
        key,
    )

    try:
        response = client.storage.from_(bucket).remove([key])

        success = True
        if isinstance(response, dict):
            error = response.get("error")
            success = not error

        duration_ms = (time.perf_counter() - start) * 1000

        if success:
            logger.info(
                "storage.op.success: op=delete, bucket=%s, key=%s, duration_ms=%.2f",
                bucket,
                key,
                duration_ms,
            )
        else:
            logger.warning(
                "storage.op.error: op=delete, bucket=%s, key=%s, duration_ms=%.2f, error=RemoveFailed",
                bucket,
                key,
                duration_ms,
            )

        return success

    except Exception as exc:
        duration_ms = (time.perf_counter() - start) * 1000
        logger.error(
            "storage.op.error: op=delete, bucket=%s, key=%s, duration_ms=%.2f, error=%s",
            bucket,
            key,
            duration_ms,
            type(exc).__name__,
            exc_info=True,
        )
        raise


def _remove_batch(
    client: Any,
    bucket: str,
    keys: list[str],
    *,
    chunk_size: int = 1000,
) -> int:
    """Remove múltiplos arquivos do storage em lotes de até *chunk_size*.

    Returns:
        Quantidade de chaves enviadas para remoção com sucesso.
    """
    if not keys:
        return 0

    normalized = [_normalize_key(k) for k in keys]
    total = len(normalized)
    removed = 0

    start = time.perf_counter()
    logger.info(
        "storage.op.start: op=remove_batch, bucket=%s, total_keys=%d",
        bucket,
        total,
    )

    try:
        for i in range(0, total, chunk_size):
            chunk = normalized[i : i + chunk_size]
            client.storage.from_(bucket).remove(chunk)
            removed += len(chunk)

        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "storage.op.success: op=remove_batch, bucket=%s, removed=%d, duration_ms=%.2f",
            bucket,
            removed,
            duration_ms,
        )
        return removed

    except Exception as exc:
        duration_ms = (time.perf_counter() - start) * 1000
        logger.error(
            "storage.op.error: op=remove_batch, bucket=%s, removed=%d/%d, duration_ms=%.2f, error=%s",
            bucket,
            removed,
            total,
            duration_ms,
            type(exc).__name__,
            exc_info=True,
        )
        raise


def _list(client: Any, bucket: str, prefix: str = "") -> list[dict[str, Any]]:
    base = prefix.strip("/")
    path = f"{base}/" if base else ""

    start = time.perf_counter()
    logger.info(
        "storage.op.start: op=list, bucket=%s, prefix=%s",
        bucket,
        base,
    )

    try:
        response = client.storage.from_(bucket).list(
            path=path,
            options={
                "limit": 1000,
                "offset": 0,
                "sortBy": {"column": "name", "order": "asc"},
            },
        )

        results: list[dict[str, Any]] = []
        for obj in response or []:
            if not isinstance(obj, dict):
                continue
            entry = dict(obj)
            name = entry.get("name") or ""
            entry["full_path"] = f"{base}/{name}".strip("/") if base else name
            results.append(entry)

        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "storage.op.success: op=list, bucket=%s, prefix=%s, count=%d, duration_ms=%.2f",
            bucket,
            base,
            len(results),
            duration_ms,
        )

        return results

    except Exception as exc:
        duration_ms = (time.perf_counter() - start) * 1000
        logger.error(
            "storage.op.error: op=list, bucket=%s, prefix=%s, duration_ms=%.2f, error=%s",
            bucket,
            base,
            duration_ms,
            type(exc).__name__,
            exc_info=True,
        )
        raise


class SupabaseStorageAdapter(StoragePort):
    """Concrete implementation of StoragePort backed by the shared supabase client."""

    def __init__(
        self,
        client: Any | None = None,
        bucket: Optional[str] = None,
        *,
        overwrite: bool = True,
    ) -> None:
        self._client = client or supabase
        self._bucket = _normalize_bucket(bucket)
        self._overwrite = overwrite

    def upload_file(self, local_path: Any, remote_key: str, content_type: Optional[str] = None) -> str:
        return _upload(
            self._client,
            self._bucket,
            local_path,
            remote_key,
            content_type,
            upsert=self._overwrite,
        )

    def download_file(self, remote_key: str, local_path: Optional[str] = None) -> str | bytes:
        return _download(self._client, self._bucket, remote_key, local_path)

    def delete_file(self, remote_key: str) -> bool:
        return _delete(self._client, self._bucket, remote_key)

    def remove_files(self, keys: list[str], *, chunk_size: int = 1000) -> int:
        """Remove múltiplos arquivos em lotes (max *chunk_size* por chamada API)."""
        return _remove_batch(self._client, self._bucket, keys, chunk_size=chunk_size)

    def list_files(self, prefix: str = "") -> list[dict[str, Any]]:
        return _list(self._client, self._bucket, prefix)

    def download_folder_zip(
        self,
        prefix: str,
        *,
        zip_name: Optional[str] = None,
        out_dir: Optional[str] = None,
        timeout_s: int = 300,
        cancel_event: Optional[Any] = None,
        progress_cb: Optional[Any] = None,
    ):
        normalized_prefix = prefix.strip("/")
        return baixar_pasta_zip(
            self._bucket,
            normalized_prefix,
            zip_name=zip_name,
            out_dir=out_dir,
            timeout_s=timeout_s,
            cancel_event=cancel_event,
            progress_cb=progress_cb,
        )


_default_adapter = SupabaseStorageAdapter()


def upload_file(local_path: Any, remote_key: str, content_type: Optional[str] = None) -> str:
    return _default_adapter.upload_file(local_path, remote_key, content_type)


def download_file(remote_key: str, local_path: Optional[str] = None) -> str | bytes:
    return _default_adapter.download_file(remote_key, local_path)


def delete_file(remote_key: str) -> bool:
    return _default_adapter.delete_file(remote_key)


def remove_files(keys: list[str], *, chunk_size: int = 1000) -> int:
    """Remove múltiplos arquivos do bucket padrão em lotes."""
    return _default_adapter.remove_files(keys, chunk_size=chunk_size)


def list_files(prefix: str = "") -> Iterable[dict[str, Any]]:
    return _default_adapter.list_files(prefix)


def download_folder_zip(
    prefix: str,
    *,
    bucket: Optional[str] = None,
    zip_name: Optional[str] = None,
    out_dir: Optional[str] = None,
    timeout_s: int = 300,
    cancel_event: Optional[Any] = None,
    progress_cb: Optional[Any] = None,
):
    adapter = _default_adapter if bucket is None else SupabaseStorageAdapter(bucket=bucket)
    return adapter.download_folder_zip(
        prefix,
        zip_name=zip_name,
        out_dir=out_dir,
        timeout_s=timeout_s,
        cancel_event=cancel_event,
        progress_cb=progress_cb,
    )


def get_default_adapter() -> SupabaseStorageAdapter:
    return _default_adapter


__all__ = [
    "SupabaseStorageAdapter",
    "InvalidBucketNameError",
    "upload_file",
    "download_file",
    "delete_file",
    "remove_files",
    "list_files",
    "download_folder_zip",
    "DownloadCancelledError",
    "get_default_adapter",
    "normalize_key_for_storage",
]
