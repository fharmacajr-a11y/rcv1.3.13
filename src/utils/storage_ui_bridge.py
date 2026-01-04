"""Bridge para reutilizar a janela de arquivos dos Clientes no módulo Auditoria."""

from __future__ import annotations

import logging
import os
from typing import Any, Mapping, Optional

logger = logging.getLogger(__name__)

open_files_browser = None  # carregado sob demanda
_OPEN_BROWSER_LOAD_FAILED = False


def _get_open_files_browser():
    """Resolve o open_files_browser apenas quando necessário para evitar import circular."""
    global open_files_browser, _OPEN_BROWSER_LOAD_FAILED
    if open_files_browser is not None or _OPEN_BROWSER_LOAD_FAILED:
        return open_files_browser

    try:
        from src.modules.uploads import open_files_browser as loaded

        open_files_browser = loaded
    except Exception as exc:  # noqa: BLE001
        logger.debug("Falha ao importar open_files_browser: %s", exc)
        _OPEN_BROWSER_LOAD_FAILED = True
        open_files_browser = None
    return open_files_browser


def get_clients_bucket() -> str:
    """
    Retorna o nome do bucket de clientes resolvido a partir de RC_STORAGE_BUCKET_CLIENTS (padrão rc-docs).

    Mantém compatibilidade com o files_browser, que assume "rc-docs" quando não há configuração.
    """
    # O files_browser usa "rc-docs" hardcoded
    bucket = os.getenv("RC_STORAGE_BUCKET_CLIENTS", "rc-docs")
    return bucket.strip() if bucket else "rc-docs"


def client_prefix_for_id(client_id: int | str, org_id: str = "") -> str:
    """
    Monta o prefixo de pasta do cliente no storage.

    Usa formato padrão {org_id}/{client_id} ou RC_STORAGE_CLIENTS_FOLDER_FMT quando presente.
    """
    return build_client_prefix(org_id=org_id, client_id=client_id)


def build_client_prefix(*, org_id: str, client_id: int | str) -> str:
    """
    Retorna o prefixo do cliente no Storage, respeitando RC_STORAGE_CLIENTS_FOLDER_FMT.

    Args:
        org_id: Identificador da organização (pode ser vazio em ambientes antigos).
        client_id: Identificador do cliente (int ou str).
    """
    fmt = os.getenv("RC_STORAGE_CLIENTS_FOLDER_FMT", "").strip()
    base: str
    if fmt:
        base = fmt.format(client_id=client_id, org_id=org_id)
    elif org_id:
        base = f"{org_id}/{client_id}"
    else:
        base = str(client_id)
    return base.strip("/")


def _get_org_id_from_supabase(sb: Any) -> Optional[str]:
    """
    Obtém o org_id do usuário logado via cliente Supabase fornecido.

    Retorna None quando não há usuário ou em caso de exceção.
    """
    try:
        user = sb.auth.get_user()
        if not user or not user.user:
            return None
        uid = user.user.id

        # Busca org_id na tabela public.users
        res = sb.table("users").select("org_id").eq("id", uid).limit(1).execute()
        if getattr(res, "data", None) and res.data[0].get("org_id"):
            return res.data[0]["org_id"]
    except Exception as exc:  # noqa: BLE001
        logger.debug("Falha ao obter org_id via Supabase para janela de arquivos: %s", exc)
    return None


def _client_title(row: Mapping[str, Any]) -> tuple[str, str]:
    """
    Extrai razão social (ou equivalente) e cnpj do cliente a partir do registro retornado do storage/db.

    Usa campos comuns (razao_social/legal_name/name/display_name) com fallback para "Cliente #{id}".
    """
    nome = (
        row.get("razao_social")
        or row.get("legal_name")
        or row.get("name")
        or row.get("display_name")
        or f"Cliente #{row.get('id')}"
    )
    cnpj = row.get("cnpj") or row.get("tax_id") or ""
    return nome, cnpj


def open_client_files_window(parent: Any, sb: Any, client_id: int) -> None:
    """
    Abre a janela de arquivos usada em Clientes para o client_id informado.

    Lida com modo offline, ausência de registro do cliente, exceções de busca
    e falhas ao abrir o browser externo, exibindo mensagens apropriadas.
    """
    if not sb:
        from tkinter import messagebox

        messagebox.showwarning("Arquivos", "Modo offline.")
        return

    # Busca dados do cliente para montar título
    try:
        res = sb.table("clients").select("*").eq("id", client_id).limit(1).execute()
        data = getattr(res, "data", []) or []
        if not data:
            from tkinter import messagebox

            messagebox.showwarning("Arquivos", f"Cliente #{client_id} não encontrado.")
            return
        row = data[0]
    except Exception as e:
        from tkinter import messagebox

        messagebox.showwarning("Arquivos", f"Não foi possível carregar o cliente #{client_id}.\n{e}")
        return

    razao, cnpj = _client_title(row)

    # Obtém org_id do usuário logado
    org_id = _get_org_id_from_supabase(sb) or ""

    from tkinter import messagebox

    browser = _get_open_files_browser()
    if browser is not None:
        try:
            browser(parent, org_id=org_id, client_id=client_id, razao=razao, cnpj=cnpj)
            return
        except Exception:
            messagebox.showwarning("Arquivos", "Falha ao abrir janela de arquivos.")
            return

    messagebox.showwarning("Arquivos", "Falha ao abrir janela de arquivos.")
