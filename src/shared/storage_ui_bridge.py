"""Bridge para reutilizar a janela de arquivos dos Clientes no módulo Auditoria."""

from __future__ import annotations

import os
from typing import Any, Optional

# Tenta importar a janela de arquivos usada pelo módulo Clientes
try:
    from src.modules.uploads import open_files_browser
except Exception:
    open_files_browser = None  # type: ignore[assignment]


def get_clients_bucket() -> str:
    """Retorna o nome do bucket de clientes."""
    # O files_browser usa "rc-docs" hardcoded
    bucket = os.getenv("RC_STORAGE_BUCKET_CLIENTS", "rc-docs")
    return bucket.strip() if bucket else "rc-docs"


def client_prefix_for_id(client_id: int | str, org_id: str = "") -> str:
    """
    Monta o prefixo do cliente no Storage.

    O padrão do files_browser é: {org_id}/{client_id}
    Mas suporta override via RC_STORAGE_CLIENTS_FOLDER_FMT.
    """
    fmt = os.getenv("RC_STORAGE_CLIENTS_FOLDER_FMT", "").strip()
    if fmt:
        # Formato customizado
        return fmt.format(client_id=client_id, org_id=org_id)
    else:
        # Formato padrão do files_browser
        if org_id:
            return f"{org_id}/{client_id}".strip("/")
        else:
            return str(client_id)


def _get_org_id_from_supabase(sb) -> Optional[str]:  # type: ignore[no-untyped-def]
    """Obtém org_id do usuário logado via Supabase."""
    try:
        user = sb.auth.get_user()
        if not user or not user.user:
            return None
        uid = user.user.id

        # Busca org_id na tabela public.users
        res = sb.table("users").select("org_id").eq("id", uid).limit(1).execute()
        if getattr(res, "data", None) and res.data[0].get("org_id"):
            return res.data[0]["org_id"]
    except Exception:
        pass
    return None


def _client_title(row: dict[str, Any]) -> tuple[str, str]:
    """Extrai razao_social e cnpj do cliente."""
    nome = row.get("razao_social") or row.get("legal_name") or row.get("name") or row.get("display_name") or f"Cliente #{row.get('id')}"
    cnpj = row.get("cnpj") or row.get("tax_id") or ""
    return nome, cnpj


def open_client_files_window(parent, sb, client_id: int) -> None:  # type: ignore[no-untyped-def]
    """
    Abre a mesma janela de arquivos usada em Clientes para o client_id informado.

    Usa open_files_browser de src.ui.files_browser (janela completa com visualizar PDF,
    baixar arquivo, baixar pasta .zip, etc). Se a janela não puder ser aberta, exibe
    um aviso informando a falha.
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

    if open_files_browser is not None:
        try:
            open_files_browser(parent, org_id=org_id, client_id=client_id, razao=razao, cnpj=cnpj)
            return
        except Exception:
            messagebox.showwarning("Arquivos", "Falha ao abrir janela de arquivos.")
            return

    messagebox.showwarning("Arquivos", "Falha ao abrir janela de arquivos.")
