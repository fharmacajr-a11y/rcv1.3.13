# -*- coding: utf-8 -*-
"""INTERNAL: implementação particionada do pipeline de clientes; API pública exposta por pipeline.py."""

from __future__ import annotations

import hashlib
import mimetypes
import os
import shutil
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from typing import Any

from adapters.storage.api import delete_file as storage_delete_file
from adapters.storage.api import upload_file as storage_upload_file
from adapters.storage.api import using_storage_backend
from infra.supabase_client import exec_postgrest, supabase
from src.config.paths import CLOUD_ONLY
from src.core.logger import get_logger
from src.core.storage_key import make_storage_key
from src.helpers.storage_errors import classify_storage_error
from src.helpers.datetime_utils import now_iso_z

from ._prepare import DEFAULT_IMPORT_SUBFOLDER, UploadCtx, _unpack_call
from ._finalize import finalize_state

LOGGER_NAME = "src.modules.clientes.forms.pipeline"
logger = get_logger(LOGGER_NAME)


def _build_document_version_payload(
    *,
    document_id: int,
    storage_path: str,
    size_bytes: int,
    sha256_hash: str,
    ctx: UploadCtx,
) -> dict[str, Any]:
    return {
        "document_id": document_id,
        "path": storage_path,
        "size_bytes": size_bytes,
        "sha256": sha256_hash,
        "uploaded_by": ctx.user_id or "unknown",
        "created_at": ctx.created_at or now_iso_z(),
    }


class UploadProgressDialog:
    def __init__(self, parent: Any, total_files: int, total_bytes: int):
        self.total_files = max(int(total_files or 0), 1)
        self.total_bytes = max(int(total_bytes or 0), 1)
        self.current_file_index = 0
        self.sent_bytes = 0
        fixed_width = 340

        dlg = tk.Toplevel(parent)
        try:
            dlg.title("Aguarde...")
            dlg.transient(parent)
            dlg.grab_set()
            dlg.resizable(False, False)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao configurar dialogo de upload: %s", exc)

        self.label = ttk.Label(
            dlg,
            text="Preparando envio para o Supabase...",
            wraplength=fixed_width - 40,
            justify="left",
        )
        self.label.pack(padx=20, pady=(15, 5))

        self.bar = ttk.Progressbar(dlg, mode="determinate", maximum=self.total_files, value=0)
        self.bar.pack(fill="x", padx=20, pady=(0, 15))

        try:
            dlg.update_idletasks()
            x = parent.winfo_rootx() + (parent.winfo_width() // 2 - dlg.winfo_width() // 2)
            y = parent.winfo_rooty() + (parent.winfo_height() // 2 - dlg.winfo_height() // 2)
            dlg.minsize(fixed_width, dlg.winfo_height())
            dlg.geometry(f"{fixed_width}x{dlg.winfo_height()}+{x}+{y}")
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao posicionar dialogo de upload: %s", exc)

        try:
            dlg.protocol("WM_DELETE_WINDOW", lambda: None)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao registrar protocolo de fechamento do dialogo de upload: %s", exc)

        self.win = dlg

    def update_for_file(self, filename: str, file_size: int) -> None:
        self.current_file_index += 1
        self.sent_bytes += max(int(file_size or 0), 0)

        arquivos_txt = f"{self.current_file_index}/{self.total_files}"
        enviados_kb = self.sent_bytes // 1024
        total_kb = self.total_bytes // 1024

        try:
            self.label.configure(
                text=(
                    f"Enviando arquivo {arquivos_txt}: {os.path.basename(filename)}\n"
                    f"{enviados_kb} KB de {total_kb} KB enviados..."
                )
            )
            self.bar["value"] = min(self.current_file_index, self.total_files)
            self.win.update_idletasks()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao atualizar dialogo de progresso: %s", exc)

    def close(self) -> None:
        try:
            self.win.destroy()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao fechar dialogo de upload: %s", exc)


def perform_uploads(*args, **kwargs) -> tuple[tuple, dict[str, Any]]:
    self, row, ents, arquivos, win = _unpack_call(args, kwargs)
    ctx: UploadCtx | None = getattr(self, "_upload_ctx", None)
    if not ctx or ctx.abort:
        return args, kwargs

    parent_win = ctx.parent_win or self

    total_files = len(ctx.files) if ctx.files else 0
    total_bytes = 0
    for lp, _rel in ctx.files:
        try:
            total_bytes += os.path.getsize(lp)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao obter tamanho de arquivo para upload: %s", exc)
            continue

    progress = UploadProgressDialog(parent_win, total_files or 1, total_bytes or 0)
    ctx.busy_dialog = progress

    if not ctx.pasta_local:
        raise ValueError("pasta_local não configurada no contexto de upload")

    base_local = (
        os.path.join(
            ctx.pasta_local,
            DEFAULT_IMPORT_SUBFOLDER,
            ctx.subpasta,
        )
        if ctx.subpasta
        else os.path.join(ctx.pasta_local, DEFAULT_IMPORT_SUBFOLDER)
    )
    ctx.base_local = base_local

    def worker():
        falhas = 0
        arquivos_falhados = []

        if ctx.src_dir and ctx.pasta_local:
            base_local_inner = (
                os.path.join(ctx.pasta_local, DEFAULT_IMPORT_SUBFOLDER, ctx.subpasta)
                if ctx.subpasta
                else os.path.join(ctx.pasta_local, DEFAULT_IMPORT_SUBFOLDER)
            )
            try:
                if not CLOUD_ONLY:
                    os.makedirs(base_local_inner, exist_ok=True)
                for lp, rel in ctx.files:
                    dest = (
                        os.path.join(base_local_inner, rel)
                        if ctx.src_dir and rel
                        else os.path.join(base_local_inner, os.path.basename(lp))
                    )
                    if not CLOUD_ONLY:
                        os.makedirs(os.path.dirname(dest), exist_ok=True)
                    try:
                        shutil.copy2(lp, dest)
                    except Exception as exc:  # noqa: BLE001
                        logger.debug("Falha ao copiar arquivo local para staging: %s", exc)
            except Exception as exc:
                logger.error("Falha ao copiar local: %s", exc)

        def _after_step(filename: str, size_bytes: int):
            self.after(0, lambda: progress.update_for_file(filename, size_bytes))

        with using_storage_backend(ctx.storage_adapter):
            base_parts = [ctx.org_id, ctx.client_id, DEFAULT_IMPORT_SUBFOLDER]
            if ctx.subpasta:
                base_parts.append(ctx.subpasta)

            for local_path, rel in ctx.files:
                try:
                    rel_path = (rel or "").replace("\\", "/").strip("/")
                    segments = [seg for seg in rel_path.split("/") if seg] if rel_path else []
                    if segments:
                        filename_original = segments[-1]
                        dir_segments = segments[:-1]
                    else:
                        filename_original = os.path.basename(local_path)
                        dir_segments = []

                    key_parts = base_parts + dir_segments
                    storage_path = make_storage_key(*key_parts, filename=filename_original)
                    logger.info(
                        "Upload Storage: original=%r -> key=%s (bucket=%s)",
                        rel or filename_original,
                        storage_path,
                        ctx.bucket,
                    )

                    data = Path(local_path).read_bytes()
                    sanitized_filename = storage_path.split("/")[-1]
                    content_type = mimetypes.guess_type(sanitized_filename)[0] or "application/octet-stream"
                    storage_delete_file(storage_path)
                    storage_upload_file(data, storage_path, content_type)

                    size_bytes = len(data)
                    sha256_hash = hashlib.sha256(data).hexdigest()

                    doc = exec_postgrest(
                        supabase.table("documents").insert(
                            {
                                "client_id": ctx.client_id,
                                "title": os.path.basename(local_path),
                                "kind": os.path.splitext(local_path)[1].lstrip("."),
                                "current_version": None,
                            }
                        )
                    )
                    document_id = doc.data[0]["id"]

                    version_payload = _build_document_version_payload(
                        document_id=document_id,
                        storage_path=storage_path,
                        size_bytes=size_bytes,
                        sha256_hash=sha256_hash,
                        ctx=ctx,
                    )
                    ver = exec_postgrest(supabase.table("document_versions").insert(version_payload))
                    version_id = ver.data[0]["id"]
                    exec_postgrest(
                        supabase.table("documents").update({"current_version": version_id}).eq("id", document_id)
                    )

                    logger.info("Upload OK: %s", storage_path)
                    _after_step(filename_original, size_bytes)
                except Exception as exc:
                    falhas += 1
                    arquivo_nome = os.path.basename(local_path)
                    arquivos_falhados.append(arquivo_nome)
                    kind = classify_storage_error(exc)
                    if kind == "invalid_key":
                        logger.error(
                            "Nome/caminho inválido: %s | arquivo: %s",
                            storage_path,
                            arquivo_nome,
                        )
                    elif kind == "rls":
                        logger.error(
                            "Permissão negada (RLS) no upload de %s | arquivo: %s",
                            storage_path,
                            arquivo_nome,
                        )
                    elif kind == "exists":
                        logger.warning(
                            "Chave já existia: %s | arquivo: %s",
                            storage_path,
                            arquivo_nome,
                        )
                    else:
                        logger.exception(
                            "Falha upload/registro (%s) | arquivo: %s: %s",
                            local_path,
                            arquivo_nome,
                            exc,
                        )
                    _after_step(arquivo_nome or filename_original, 0)

        ctx.falhas = falhas
        ctx.misc["arquivos_falhados"] = arquivos_falhados
        ctx.finalize_ready = True
        self.after(
            0,
            lambda: finalize_state(self, row, ents, arquivos, win, ctx_override=ctx),
        )

    threading.Thread(target=worker, daemon=True).start()
    return args, kwargs


__all__ = ["perform_uploads", "UploadProgressDialog"]
