"""Helpers de prefixo/CNPJ e Supabase para o modulo Uploads.

Extraidos de src.ui.files_browser para permitir reutilizacao e testes.
"""

from __future__ import annotations

import re


def _cnpj_only_digits(text: str) -> str:
    """Retorna apenas digitos do CNPJ; se vier None, devolve string vazia."""
    if text is None:
        return ""
    return re.sub(r"\D", "", str(text))


def format_cnpj_for_display(cnpj: str) -> str:
    """
    Formata CNPJ numerico em 00.000.000/0000-00.
    Se nao tiver 14 digitos (ex.: futuro alfanumerico), retorna como veio.
    """
    digits = _cnpj_only_digits(cnpj)
    if len(digits) == 14:
        return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"
    return str(cnpj or "")


def strip_cnpj_from_razao(razao: str, cnpj: str) -> str:
    """
    Remove do fim da razao social um CNPJ "cru" (14 digitos) que tenha sido
    acidentalmente concatenado (com ou sem tracos/'-').
    """
    if not razao:
        return ""
    raw = _cnpj_only_digits(cnpj or "")
    s = str(razao).strip()
    if raw:
        s = re.sub(rf"\s*[-_/\"']?\s*{re.escape(raw)}\s*$", "", s)
    return s.strip()


def get_clients_bucket() -> str:
    """Retorna o nome do bucket de clientes."""
    return "rc-docs"


def client_prefix_for_id(client_id: int, org_id: str) -> str:
    """
    Monta o prefixo do cliente no Storage.
    Formato: {org_id}/{client_id}
    """
    return f"{org_id}/{client_id}".strip("/")


def get_current_org_id(sb) -> str:  # type: ignore[no-untyped-def]
    """Obtem org_id do usuario logado via Supabase."""
    try:
        user = sb.auth.get_user()
        if not user or not user.user:
            return ""
        uid = user.user.id

        # Busca org_id na tabela memberships
        res = sb.table("memberships").select("org_id").eq("user_id", uid).limit(1).execute()
        if getattr(res, "data", None) and res.data and res.data[0].get("org_id"):
            return res.data[0]["org_id"]
    except Exception:
        pass
    return ""
