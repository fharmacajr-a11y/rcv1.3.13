# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
from typing import Iterable, List, Tuple

from tkinter import messagebox

logger = logging.getLogger(__name__)
log = logger

BUCKET_DOCS = "rc-docs"


# ----------------- Helpers Supabase -----------------
def _get_supabase_and_org():
    """
    Retorna (supabase, org_id) do usuário logado.
    """
    from infra.supabase_client import supabase

    try:
        # compat: get_user() pode retornar .user ou já o user
        resp = supabase.auth.get_user()
        u = getattr(resp, "user", None) or resp
        uid = getattr(u, "id", None)
        if not uid:
            raise RuntimeError("Usuário não autenticado no Supabase.")
        res = supabase.table("memberships").select("org_id").eq("user_id", uid).limit(1).execute()
        org_id = res.data[0]["org_id"] if getattr(res, "data", None) else None
        if not org_id:
            raise RuntimeError("Organização não encontrada para o usuário atual.")
        return supabase, org_id
    except Exception as e:
        raise RuntimeError(f"Falha ao obter usuário/organização: {e}")


# ---- Listagem recursiva no Storage (usando list + chamada recursiva) ----
def _list_storage_children(bucket, prefix: str) -> List[dict]:
    """
    Lista UM nível de filhos em `prefix`. Retorna dicts com pelo menos {name, is_folder?}.
    Usa a API do supabase.storage.from_(bucket).list(prefix).
    """
    from infra.supabase_client import supabase
    client = supabase.storage.from_(bucket)
    items = client.list(prefix)  # retorna apenas um nível
    out = []
    for it in items or []:
        # Heurística: objetos com metadata None são "pastas" (chaves virtuais)
        name = it.get("name")
        meta = it.get("metadata")
        is_folder = meta is None
        out.append({"name": name, "is_folder": is_folder})
    return out


def _gather_all_paths(bucket: str, root_prefix: str) -> List[str]:
    """
    Coleta todos os caminhos de arquivos sob root_prefix, recursivamente.
    Retorna caminhos completos (ex.: "<org>/<client>/SIFAP/arquivo.pdf").
    """
    paths: List[str] = []

    def walk(prefix: str):
        for obj in _list_storage_children(bucket, prefix):
            name = obj["name"]
            if not name:
                continue
            if obj.get("is_folder"):
                walk(f"{prefix}/{name}")
            else:
                paths.append(f"{prefix}/{name}")

    walk(root_prefix)
    return paths


def _remove_storage_prefix(org_id: str, client_id: int) -> int:
    """
    Remove todos os objetos do bucket sob <org_id>/<client_id>.
    Retorna quantidade de objetos removidos.
    """
    from infra.supabase_client import supabase
    client = supabase.storage.from_(BUCKET_DOCS)
    root = f"{org_id}/{client_id}"
    paths = _gather_all_paths(BUCKET_DOCS, root)

    if not paths:
        return 0

    # A API aceita remover em lote
    res = client.remove(paths)
    # se não estourou exceção, consideramos removido
    return len(paths)


# ----------------- Ações públicas -----------------
def restore_clients(client_ids: Iterable[int], parent=None) -> Tuple[int, List[Tuple[int, str]]]:
    """
    Restaura clientes (deleted_at = null).
    Retorna: (qtd_ok, [(client_id, err), ...])
    """
    ok = 0
    errs: List[Tuple[int, str]] = []
    try:
        supabase, _ = _get_supabase_and_org()
    except Exception as e:
        messagebox.showerror("Erro", str(e), parent=parent)
        return 0, [(0, str(e))]

    for cid in client_ids:
        try:
            supabase.table("clients").update({"deleted_at": None}).eq("id", int(cid)).execute()
            ok += 1
        except Exception as e:
            errs.append((int(cid), str(e)))

    return ok, errs


def hard_delete_clients(client_ids: Iterable[int], parent=None) -> Tuple[int, List[Tuple[int, str]]]:
    """
    Apaga DEFINITIVAMENTE clientes (DB + Storage).
    - Remove do Storage: bucket rc-docs/<org_id>/<client_id>/**
    - Deleta a linha na tabela clients
    Retorna: (qtd_ok, [(client_id, err), ...])
    """
    ok = 0
    errs: List[Tuple[int, str]] = []

    try:
        supabase, org_id = _get_supabase_and_org()
    except Exception as e:
        messagebox.showerror("Erro", str(e), parent=parent)
        return 0, [(0, str(e))]

    for cid in client_ids:
        cid = int(cid)
        try:
            # 1) Limpa Storage
            try:
                removed = _remove_storage_prefix(org_id, cid)
                log.info("Storage: removidos %s objeto(s) de %s/%s", removed, org_id, cid)
            except Exception as e:
                # Não aborta; reporta erro mas tenta seguir para DB
                log.exception("Falha ao limpar Storage de %s/%s", org_id, cid)
                errs.append((cid, f"Storage: {e}"))

            # 2) Remove do DB (linha do cliente)
            supabase.table("clients").delete().eq("id", cid).execute()

            ok += 1
        except Exception as e:
            errs.append((cid, str(e)))

    return ok, errs
