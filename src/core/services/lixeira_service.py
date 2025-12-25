# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import os
import tkinter as tk
from tempfile import NamedTemporaryFile
from tkinter import messagebox
from typing import Iterable

from adapters.storage.api import delete_file as storage_delete_file
from adapters.storage.api import list_files as storage_list_files
from adapters.storage.api import upload_file as storage_upload_file
from adapters.storage.api import using_storage_backend
from adapters.storage.supabase_storage import SupabaseStorageAdapter
from data.supabase_repo import delete_passwords_by_client
from infra.db_schemas import MEMBERSHIPS_SELECT_ORG_ID
from infra.supabase_client import exec_postgrest
from src.utils.subpastas_config import get_mandatory_subpastas, join_prefix

logger = logging.getLogger(__name__)
log = logger

BUCKET_DOCS = "rc-docs"


# ----------------- Helpers Supabase -----------------
def _get_supabase_and_org() -> tuple[object, str]:
    """Retorna (supabase, org_id) do usuário logado, ou lança RuntimeError."""
    from infra.supabase_client import supabase

    try:
        # compat: get_user() pode retornar .user ou já o user
        resp = supabase.auth.get_user()
        u = getattr(resp, "user", None) or resp
        uid = getattr(u, "id", None)
        if not uid:
            raise RuntimeError("Usuário não autenticado no Supabase.")
        res = exec_postgrest(
            supabase.table("memberships").select(MEMBERSHIPS_SELECT_ORG_ID).eq("user_id", uid).limit(1)
        )
        org_id = res.data[0]["org_id"] if getattr(res, "data", None) else None
        if not org_id:
            raise RuntimeError("Organização não encontrada para o usuário atual.")
        return supabase, org_id
    except Exception as e:
        raise RuntimeError(f"Falha ao obter usuário/organização: {e}")


# ---- Listagem recursiva no Storage (usando list + chamada recursiva) ----
def _list_storage_children(bucket: str, prefix: str) -> list[dict]:
    """Lista UM nível de filhos em `prefix`. Retorna dicts com pelo menos {name, is_folder?}."""
    adapter = SupabaseStorageAdapter(bucket=bucket)
    with using_storage_backend(adapter):
        items = storage_list_files(prefix)
    out = []
    for it in items or []:
        if not isinstance(it, dict):
            continue
        # Heurística: objetos com metadata None são "pastas" (chaves virtuais)
        name = it.get("name")
        meta = it.get("metadata")
        is_folder = meta is None
        out.append({"name": name, "is_folder": is_folder})
    return out


def _gather_all_paths(bucket: str, root_prefix: str) -> list[str]:
    """Collect every file path under root_prefix recursively."""
    paths: list[str] = []

    def walk(prefix: str) -> None:
        for obj in _list_storage_children(bucket, prefix):
            name = obj.get("name")
            if not name:
                continue
            if obj.get("is_folder"):
                walk(f"{prefix}/{name}")
            else:
                paths.append(f"{prefix}/{name}")

    walk(root_prefix)
    return paths


def _remove_storage_prefix(org_id: str, client_id: int) -> int:
    """Delete all objects for <org_id>/<client_id>, returning how many were removed."""
    root = f"{org_id}/{client_id}"
    paths = _gather_all_paths(BUCKET_DOCS, root)

    if not paths:
        return 0

    removed = 0
    adapter = SupabaseStorageAdapter(bucket=BUCKET_DOCS)
    with using_storage_backend(adapter):
        for key in paths:
            if storage_delete_file(key):
                removed += 1
    return removed


def _ensure_mandatory_subfolders(prefix: str) -> None:
    """
    Garante que as subpastas obrigatórias existam sob `prefix`.
    Como o Supabase é orientado a objetos e 'pastas' são prefixos,
    cria um placeholder `.keep` quando não houver nenhum objeto no prefixo.
    """
    adapter = SupabaseStorageAdapter(bucket=BUCKET_DOCS)
    with using_storage_backend(adapter):
        for name in get_mandatory_subpastas():
            sub_prefix = join_prefix(prefix, name)
            has_any = False
            for _ in storage_list_files(sub_prefix):
                has_any = True
                break
            if has_any:
                continue
            keep_key = f"{sub_prefix}.keep"
            tmp_name: str | None = None
            with NamedTemporaryFile("wb", delete=False) as tmp:
                tmp.write(b"")
                tmp.flush()
                tmp_name = tmp.name
            try:
                storage_upload_file(tmp_name, keep_key, "text/plain")
            finally:
                if tmp_name:
                    try:
                        os.unlink(tmp_name)
                    except OSError as exc:
                        logger.debug("Falha ao limpar arquivo temporário %s", tmp_name, exc_info=exc)


# ----------------- Ações públicas -----------------
def restore_clients(client_ids: Iterable[int], parent: tk.Misc | None = None) -> tuple[int, list[tuple[int, str]]]:
    """Restore clients from trash, returning (successes, [(client_id, error), ...])."""
    ok = 0
    errs: list[tuple[int, str]] = []
    parent_widget: tk.Misc | None = parent if isinstance(parent, tk.Misc) else None
    try:
        supabase, org_id = _get_supabase_and_org()
    except Exception as e:
        messagebox.showerror("Erro", str(e), parent=parent_widget)
        return 0, [(0, str(e))]

    for cid in client_ids:
        try:
            exec_postgrest(supabase.table("clients").update({"deleted_at": None}).eq("id", int(cid)))
            prefix = f"{org_id}/{int(cid)}"
            try:
                _ensure_mandatory_subfolders(prefix)
            except Exception as guard_err:
                log.warning(
                    "Falha ao garantir subpastas obrigatórias para %s: %s",
                    prefix,
                    guard_err,
                )
            ok += 1
        except Exception as e:
            errs.append((int(cid), str(e)))

    return ok, errs


def hard_delete_clients(client_ids: Iterable[int], parent: tk.Misc | None = None) -> tuple[int, list[tuple[int, str]]]:
    """Hard-delete clients across storage and DB, returning (successes, error list)."""
    ok = 0
    errs: list[tuple[int, str]] = []

    parent_widget: tk.Misc | None = parent if isinstance(parent, tk.Misc) else None
    try:
        supabase, org_id = _get_supabase_and_org()
    except Exception as e:
        messagebox.showerror("Erro", str(e), parent=parent_widget)
        return 0, [(0, str(e))]

    for cid in client_ids:
        cid = int(cid)
        try:
            # 1) Limpa Storage
            try:
                removed = _remove_storage_prefix(org_id, cid)
                log.info("Storage: removidos %s objeto(s) de %s/%s", removed, org_id, cid)
            except Exception as e:
                log.exception("Falha ao limpar Storage de %s/%s", org_id, cid)
                errs.append((cid, f"Storage: {e}"))

            # 2) FIX-SENHAS-015: Apaga todas as senhas do cliente
            try:
                deleted_count = delete_passwords_by_client(org_id, str(cid))
                log.info("Senhas: removidas %d senha(s) do cliente %s", deleted_count, cid)
            except Exception as e:
                log.exception("Falha ao apagar senhas do cliente %s", cid)
                errs.append((cid, f"Senhas: {e}"))

            # 3) Remove do DB (linha do cliente)
            exec_postgrest(supabase.table("clients").delete().eq("id", cid))

            ok += 1
        except Exception as e:
            errs.append((cid, str(e)))

    return ok, errs
