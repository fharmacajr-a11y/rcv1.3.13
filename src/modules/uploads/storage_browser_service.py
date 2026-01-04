# -*- coding: utf-8 -*-
"""
Service layer para navegação e download de arquivos do Storage.

Este módulo centraliza a lógica de negócio (não-UI) para:
- Listar objetos/arquivos no bucket do Supabase
- Fazer download de arquivos do Storage
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from src.adapters.storage.api import download_file as storage_download_file
from src.adapters.storage.api import list_files as storage_list_files
from src.adapters.storage.api import using_storage_backend
from src.adapters.storage.supabase_storage import SupabaseStorageAdapter
from src.helpers.storage_utils import get_bucket_name

log = logging.getLogger(__name__)


def list_storage_objects_service(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lista arquivos do Storage para um determinado cliente/prefixo.

    Este service implementa a lógica de negócio (sem UI) para:
    1. Normalizar bucket e prefix
    2. Listar arquivos via adapter Supabase
    3. Processar resposta e montar lista de objetos
    4. Classificar objetos (pasta vs arquivo)

    Parâmetros:
        ctx: dicionário com dados necessários:
            - bucket_name: str | None (nome do bucket ou None para usar padrão)
            - prefix: str (prefixo/caminho dentro do bucket, ex: "org/client/GERAL")

    Retorna:
        dict com resultado:
            {
                "ok": True/False,
                "objects": [
                    {"name": str, "is_folder": bool, "full_path": str},
                    ...
                ],
                "errors": [str, ...],
                "message": str,
                "error_type": "bucket_not_found" | "generic" | None
            }
    """
    result: Dict[str, Any] = {
        "ok": False,
        "objects": [],
        "errors": [],
        "message": "",
        "error_type": None,
    }

    try:
        # 1. Normalizar bucket e prefix
        bucket_name = ctx.get("bucket_name")
        prefix = ctx.get("prefix", "")

        provided_bucket = (bucket_name or "").strip()
        normalized_prefix = (prefix or "").strip("/")

        # Chamadas legadas frequentemente enviam apenas o prefixo como primeiro argumento.
        if provided_bucket and not normalized_prefix and "/" in provided_bucket:
            normalized_prefix = provided_bucket
            provided_bucket = ""

        bucket = get_bucket_name(provided_bucket)

        log.info("Service: Listando arquivos no bucket=%s prefix=%s", bucket, normalized_prefix)

        # 2. Listar arquivos via adapter Supabase
        adapter = SupabaseStorageAdapter(bucket=bucket)
        with using_storage_backend(adapter):
            response = list(storage_list_files(normalized_prefix))

        # 3. Processar resposta e montar lista de objetos
        objects = []
        for obj in response:
            if isinstance(obj, dict):
                is_folder = obj.get("metadata") is None
                name = obj.get("name")
                full_path = obj.get("full_path") or (
                    f"{normalized_prefix}/{name}".strip("/") if normalized_prefix else name
                )
                objects.append({"name": name, "is_folder": is_folder, "full_path": full_path})

        result["ok"] = True
        result["objects"] = objects
        result["message"] = f"Listados {len(objects)} objeto(s) em {bucket}/{normalized_prefix}"

        log.info("Service: %d objeto(s) listado(s)", len(objects))
        return result

    except Exception as e:
        log.error("Service: Erro ao listar objetos: %s", e, exc_info=True)

        err_text = str(e).lower()
        result["ok"] = False
        result["errors"].append(str(e))

        if "bucket not found" in err_text:
            result["error_type"] = "bucket_not_found"
            result["message"] = "Bucket não encontrado no Storage"
        else:
            result["error_type"] = "generic"
            result["message"] = f"Erro ao listar objetos: {e}"

        return result


def download_file_service(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Faz download de um arquivo do Storage.

    Este service implementa a lógica de negócio (sem UI) para:
    1. Validar parâmetros (file_path, local_path)
    2. Resolver bucket
    3. Executar download via adapter Supabase

    Parâmetros:
        ctx: dicionário com dados necessários:
            - bucket_name: str | None (nome do bucket ou None para usar padrão)
            - file_path: str (caminho do arquivo no Storage)
            - local_path: str (caminho local onde salvar)
            - compact_call: bool (opcional, para chamadas compactas download_file(remote, local))

    Retorna:
        dict com resultado:
            {
                "ok": True/False,
                "errors": [str, ...],
                "message": str,
                "local_path": str | None (caminho onde foi salvo, se sucesso)
            }
    """
    result: Dict[str, Any] = {
        "ok": False,
        "errors": [],
        "message": "",
        "local_path": None,
    }

    try:
        # 1. Obter parâmetros do contexto
        bucket_name = ctx.get("bucket_name")
        file_path = ctx.get("file_path")
        local_path = ctx.get("local_path")

        # Suporte para chamada compacta: download_file(remote_key, destino)
        # onde bucket_name vira file_path e file_path vira local_path
        if ctx.get("compact_call") and local_path is None:
            file_path, local_path = bucket_name, file_path
            bucket_name = None

        # 2. Validar parâmetros
        if not file_path or not local_path:
            result["errors"].append("file_path e local_path são obrigatórios")
            result["message"] = "Parâmetros inválidos para download"
            log.error("Service: Parâmetros inválidos - file_path=%s local_path=%s", file_path, local_path)
            return result

        # 3. Resolver bucket
        bucket = get_bucket_name((bucket_name or "").strip())

        log.info("Service: Baixando arquivo bucket=%s key=%s -> %s", bucket, file_path, local_path)

        # 4. Executar download via adapter Supabase
        adapter = SupabaseStorageAdapter(bucket=bucket)
        with using_storage_backend(adapter):
            storage_download_file(file_path, local_path)

        result["ok"] = True
        result["local_path"] = local_path
        result["message"] = f"Arquivo baixado com sucesso: {local_path}"

        log.info("Service: Arquivo baixado: %s", local_path)
        return result

    except Exception as e:
        log.error("Service: Erro ao baixar %s: %s", ctx.get("file_path"), e, exc_info=True)

        result["ok"] = False
        result["errors"].append(str(e))
        result["message"] = f"Erro ao baixar arquivo: {e}"

        return result
