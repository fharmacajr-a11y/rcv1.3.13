"""Utilitários de prefix/bucket para storage de clientes."""

from __future__ import annotations

import os


def get_clients_bucket() -> str:
    """
    Retorna o nome do bucket de clientes resolvido a partir de RC_STORAGE_BUCKET_CLIENTS (padrão rc-docs).

    Mantém compatibilidade com o files_browser, que assume "rc-docs" quando não há configuração.
    """
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
