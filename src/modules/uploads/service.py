"""Servicos de dominio do modulo Uploads / Arquivos.

Concentra helpers de upload/listagem e a logica de integracao com
Supabase/Storage. Arquivos legados (uploader_supabase.py e
src/core/services/upload_service.py) passam a delegar para este modulo.
"""

from __future__ import annotations

import hashlib
import logging
import os
import shutil
import subprocess  # nosec B404  # Uso controlado: abrir arquivos locais do app, sem shell=True
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Optional, Sequence, Tuple

from adapters.storage.api import (
    DownloadCancelledError as _DownloadCancelledError,
    delete_file as _delete_file,
    download_folder_zip as _download_folder_zip,
    using_storage_backend,
)
from adapters.storage.supabase_storage import SupabaseStorageAdapter
from infra.supabase.storage_helpers import download_bytes as _download_bytes
from src.modules.uploads.components.helpers import (
    _cnpj_only_digits,
    client_prefix_for_id,
    format_cnpj_for_display,
    get_clients_bucket,
    get_current_org_id,
    strip_cnpj_from_razao,
)
from src.modules.uploads.temp_files import create_temp_file

from . import repository, validation

try:
    from src.utils.hash_utils import sha256_file as _sha256
except Exception:  # pragma: no cover

    def _sha256(path: Path | str) -> str:
        digest = hashlib.sha256()
        with Path(path).open("rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        return digest.hexdigest()


logger = logging.getLogger(__name__)
DownloadCancelledError = _DownloadCancelledError


@dataclass(slots=True)
class UploadItem:
    """Representa um arquivo local pronto para upload."""

    path: Path
    relative_path: str


def _make_upload_item(path: Path, relative_path: str) -> UploadItem:
    return UploadItem(path=path, relative_path=relative_path)


def upload_folder_to_supabase(
    folder: str | Path,
    client_id: int,
    *,
    subdir: str = "SIFAP",
) -> list[dict[str, Any]]:
    base = validation.ensure_existing_folder(folder)

    user_id = repository.current_user_id()
    if not user_id:
        raise RuntimeError("Usuario nao autenticado no Supabase. Faca login antes de enviar.")

    org_id = repository.resolve_org_id()
    results: list[dict[str, Any]] = []
    prepared_entries = validation.prepare_folder_entries(base, client_id, subdir, org_id, _sha256)

    for entry in prepared_entries:
        logger.info("Upload Storage: original=%r -> key=%s", entry.relative_path, entry.storage_path)
        repository.ensure_storage_object_absent(entry.storage_path)
        repository.upload_local_file(entry.path, entry.storage_path, entry.mime_type)

        document_row = repository.insert_document_record(
            client_id=int(client_id),
            title=entry.path.name,
            mime_type=entry.mime_type,
            user_id=user_id,
        )
        document_id = document_row["id"]

        version_row = repository.insert_document_version_record(
            document_id=document_id,
            storage_path=entry.storage_path,
            size_bytes=entry.size_bytes,
            sha_value=entry.sha256,
            uploaded_by=user_id,
        )
        version_id = version_row["id"]

        repository.update_document_current_version(document_id, version_id)

        results.append(
            {
                "relative_path": entry.safe_relative_path,
                "storage_path": entry.storage_path,
                "document_id": document_id,
                "version_id": version_id,
                "size_bytes": entry.size_bytes,
                "sha256": entry.sha256,
                "mime": entry.mime_type,
            }
        )

    return results


def collect_pdfs_from_folder(dirpath: str) -> list[UploadItem]:
    return validation.collect_pdf_items_from_folder(dirpath, _make_upload_item)


def build_items_from_files(paths: Sequence[str]) -> list[UploadItem]:
    return validation.build_items_from_files(paths, _make_upload_item)


def upload_items_for_client(
    items: Sequence[UploadItem],
    *,
    cnpj_digits: str,
    bucket: Optional[str] = None,
    supabase_client: Any | None = None,
    subfolder: Optional[str] = None,
    progress_callback: Optional[Callable[[UploadItem], None]] = None,
    client_id: int | None = None,
    org_id: str | None = None,
) -> Tuple[int, list[Tuple[UploadItem, Exception]]]:
    adapter = repository.build_storage_adapter(
        bucket=repository.normalize_bucket(bucket),
        supabase_client=supabase_client,
    )
    return repository.upload_items_with_adapter(
        adapter,
        items,
        cnpj_digits,
        subfolder,
        progress_callback=progress_callback,
        remote_path_builder=validation.build_remote_path,
        client_id=client_id,
        org_id=org_id,
    )


def download_folder_zip(*args: Any, **kwargs: Any) -> Any:
    return _download_folder_zip(*args, **kwargs)


def delete_file(*args: Any, **kwargs: Any) -> Any:
    return _delete_file(*args, **kwargs)


def download_bytes(*args: Any, **kwargs: Any) -> Any:
    return _download_bytes(*args, **kwargs)


def download_file(*args: Any, **kwargs: Any) -> Any:
    from src.modules.forms.view import download_file as _download_file  # lazy import

    return _download_file(*args, **kwargs)


def list_storage_objects(*args: Any, **kwargs: Any) -> Iterable[Any]:
    from src.modules.forms.view import list_storage_objects as _list_storage_objects  # lazy import

    return _list_storage_objects(*args, **kwargs)


def list_browser_items(prefix: str, *, bucket: str | None = None) -> Iterable[Any]:
    """
    Lista objetos para o navegador de arquivos.

    FIX: versões >=1.1.86 estavam repassando apenas `prefix` para
    src.modules.forms.view.list_storage_objects, fazendo o `prefix` cair
    como `bucket_name`. O adapter então tentava listar um bucket com o
    nome do prefixo (ex.: 'org/cliente'), retornando lista vazia.
    """
    # Bucket de clientes (padrão: rc-docs), usa o informado se vier.
    bn = (bucket or get_clients_bucket()).strip()
    normalized_prefix = (prefix or "").strip("/")
    return list_storage_objects(bn, normalized_prefix)


def download_storage_object(remote_key: str, destination: str, *, bucket: str | None = None) -> dict[str, Any]:
    """
    Baixa um objeto do storage no bucket de clientes.

    Retorna:
        dict com {"ok": bool, "errors": list, "message": str, "local_path": str | None}
    """
    bn = (bucket or get_clients_bucket()).strip()
    # usa src.modules.forms.actions.download_file(bucket, file, local)
    return download_file(bn, remote_key, destination)


def delete_storage_object(remote_key: str, *, bucket: str | None = None) -> bool:
    """
    Remove um objeto do storage no bucket de clientes.

    Retorna:
        bool: True se deletado com sucesso, False caso contrário
    """
    from adapters.storage.api import using_storage_backend  # lazy import para evitar efeitos colaterais

    bn = (bucket or get_clients_bucket()).strip()
    adapter = SupabaseStorageAdapter(bucket=bn)

    try:
        with using_storage_backend(adapter):
            # _delete_file já está importado no topo (adapters.storage.api.delete_file as _delete_file)
            result = _delete_file(remote_key)

        if not result:
            logger.warning("Falha ao deletar %s do bucket %s (retorno False)", remote_key, bn)
            return False

        logger.info("Arquivo deletado com sucesso: %s (bucket=%s)", remote_key, bn)
        return True

    except Exception as exc:
        logger.error("Erro ao deletar %s do bucket %s: %s", remote_key, bn, exc, exc_info=True)
        return False


def _collect_storage_keys(bucket: str, prefix: str) -> list[str]:
    entries = list_storage_objects(bucket, prefix=prefix) or []
    collected: list[str] = []
    for entry in entries:
        full_path = (entry.get("full_path") or "").strip("/")
        if not full_path:
            continue
        if entry.get("is_folder"):
            collected.extend(_collect_storage_keys(bucket, full_path))
        else:
            collected.append(full_path)
    return collected


def delete_storage_folder(prefix: str, *, bucket: str | None = None) -> dict[str, Any]:
    """
    Remove recursivamente todos os arquivos dentro de um prefixo (pasta) no bucket.

    Retorna dict com:
        {"ok": bool, "deleted": int, "errors": list[str], "message": str}
    """
    bn = (bucket or get_clients_bucket()).strip()
    target_prefix = (prefix or "").strip("/")
    result: dict[str, Any] = {"ok": False, "deleted": 0, "errors": [], "message": ""}

    if not target_prefix:
        result["errors"].append("prefix vazio")
        result["message"] = "Prefixo da pasta não informado"
        logger.warning("delete_storage_folder chamado sem prefixo (bucket=%s)", bn)
        return result

    try:
        keys = _collect_storage_keys(bn, target_prefix)
    except Exception as exc:  # pragma: no cover - log e propaga erro tratado
        logger.error("Erro ao coletar objetos para exclusão recursiva: %s", exc, exc_info=True)
        result["errors"].append(str(exc))
        result["message"] = f"Erro ao listar objetos sob {target_prefix}"
        return result

    adapter = SupabaseStorageAdapter(bucket=bn)
    deleted_count = 0

    try:
        with using_storage_backend(adapter):
            for key in keys:
                try:
                    if _delete_file(key):
                        deleted_count += 1
                    else:
                        result["errors"].append(f"Falha ao excluir {key}")
                except Exception as exc:  # noqa: BLE001
                    result["errors"].append(f"{key}: {exc}")

        result["deleted"] = deleted_count
        result["ok"] = not result["errors"]
        result["message"] = (
            f"Removidos {deleted_count} arquivo(s) de {target_prefix}"
            if result["ok"]
            else "Falha ao excluir alguns arquivos da pasta"
        )

        if result["ok"]:
            logger.info("Pasta excluída: %s (bucket=%s, %d arquivos)", target_prefix, bn, deleted_count)
        else:
            logger.warning(
                "Exclusão parcial da pasta %s (bucket=%s). Removidos=%d Erros=%d",
                target_prefix,
                bn,
                deleted_count,
                len(result["errors"]),
            )
        return result
    except Exception as exc:  # pragma: no cover - log de falha inesperada
        logger.error("Erro ao excluir pasta %s no bucket %s: %s", target_prefix, bn, exc, exc_info=True)
        result["errors"].append(str(exc))
        result["message"] = f"Erro ao excluir pasta: {exc}"
        return result


def download_and_open_file(remote_key: str, *, bucket: str | None = None, mode: str = "external") -> dict[str, Any]:
    """
    Baixa um arquivo do Supabase para um temporário e abre no visualizador padrão.

    Args:
        remote_key: Caminho completo do arquivo no bucket
        bucket: Nome do bucket (opcional, usa padrão se None)
        mode: Modo de abertura - "external" (padrão, usa viewer do SO) ou "internal" (futuro: PDF preview)

    Returns:
        Dict com resultado da operação:
        - ok: bool - True se sucesso, False se erro
        - message: str - Mensagem de resultado
        - temp_path: str (opcional) - Caminho do arquivo temporário criado
        - error: str (opcional) - Detalhes do erro, se houver

    Raises:
        ValueError: Se mode for inválido
    """
    if mode not in ("external", "internal"):
        raise ValueError(f"Modo inválido: {mode}. Use 'external' ou 'internal'.")

    bn = (bucket or get_clients_bucket()).strip()
    remote_filename = os.path.basename(remote_key)

    logger.info(
        "Iniciando download de arquivo: bucket=%s, remote_key=%s, mode=%s",
        bn,
        remote_key,
        mode,
    )

    # Criar arquivo temporário gerenciado
    try:
        temp_info = create_temp_file(remote_filename)
        local_path = temp_info.path
    except Exception as exc:
        logger.error("Erro ao criar arquivo temporário: %s", exc, exc_info=True)
        return {
            "ok": False,
            "message": f"Erro ao preparar arquivo temporário: {exc}",
            "error": str(exc),
        }

    # Baixar arquivo
    start_time = time.time()
    result = download_file(bn, remote_key, local_path)
    download_time = time.time() - start_time

    if not result.get("ok"):
        error_msg = result.get("message", "Erro desconhecido ao baixar arquivo")
        logger.error(
            "Falha no download: bucket=%s, remote_key=%s, erro=%s",
            bn,
            remote_key,
            error_msg,
        )
        return {
            "ok": False,
            "message": error_msg,
            "error": error_msg,
        }

    # Log de sucesso do download
    try:
        file_size = os.path.getsize(local_path)
        logger.info(
            "Download concluído: arquivo=%s, tamanho=%d bytes, tempo=%.2fs",
            remote_filename,
            file_size,
            download_time,
        )
    except Exception:  # noqa: BLE001
        logger.debug("Não foi possível obter estatísticas do arquivo baixado")

    # Mode "internal": retorna path para caller abrir no PDF viewer interno
    if mode == "internal":
        logger.info("Arquivo preparado para viewer interno: %s", local_path)
        return {
            "ok": True,
            "message": "Arquivo baixado com sucesso (modo interno)",
            "temp_path": local_path,
            "display_name": remote_filename,
            "mode": "internal",
        }

    # Mode "external": abrir no visualizador padrão do sistema
    try:
        if sys.platform.startswith("win"):
            # Windows: usar startfile (caminho controlado pelo app, não input externo)
            os.startfile(local_path)  # type: ignore[attr-defined]  # nosec B606
        elif sys.platform == "darwin":
            # macOS: resolver 'open' com which() para evitar injeção de PATH
            open_cmd = shutil.which("open")
            if open_cmd:
                subprocess.Popen([open_cmd, local_path])  # nosec B603
            else:
                raise FileNotFoundError("Executável 'open' não encontrado no PATH")
        else:
            # Linux: resolver 'xdg-open' com which() para evitar injeção de PATH
            xdg_cmd = shutil.which("xdg-open")
            if xdg_cmd:
                subprocess.Popen([xdg_cmd, local_path])  # nosec B603
            else:
                raise FileNotFoundError("Executável 'xdg-open' não encontrado no PATH")

        logger.info("Arquivo aberto no visualizador externo: %s", local_path)

        return {
            "ok": True,
            "message": "Arquivo aberto com sucesso",
            "temp_path": local_path,
        }

    except Exception as exc:
        logger.error(
            "Erro ao abrir arquivo no visualizador: path=%s, erro=%s",
            local_path,
            exc,
            exc_info=True,
        )
        return {
            "ok": False,
            "message": f"Arquivo baixado, mas não foi possível abri-lo: {exc}",
            "temp_path": local_path,
            "error": str(exc),
        }


__all__ = [
    "UploadItem",
    "collect_pdfs_from_folder",
    "build_items_from_files",
    "upload_items_for_client",
    "upload_folder_to_supabase",
    "_cnpj_only_digits",
    "client_prefix_for_id",
    "format_cnpj_for_display",
    "get_clients_bucket",
    "get_current_org_id",
    "strip_cnpj_from_razao",
    "DownloadCancelledError",
    "download_folder_zip",
    "delete_file",
    "download_bytes",
    "download_file",
    "list_storage_objects",
    "list_browser_items",
    "delete_storage_object",
    "download_and_open_file",
    "download_storage_object",
    "delete_storage_folder",
]
