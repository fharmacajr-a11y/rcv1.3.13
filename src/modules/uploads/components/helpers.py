"""Helpers de prefixo/CNPJ e Supabase para o modulo Uploads.

Extraidos de src.ui.files_browser para permitir reutilizacao e testes.
"""

from __future__ import annotations

import logging
import re

from infra.db_schemas import MEMBERSHIPS_SELECT_ORG_ID
from src.core.string_utils import only_digits
from src.shared.storage_ui_bridge import build_client_prefix

logger = logging.getLogger(__name__)


def _cnpj_only_digits(text: str) -> str:
    """Retorna apenas digitos do CNPJ; se vier None, devolve string vazia.

    Note:
        Esta é uma função wrapper para compatibilidade. A implementação
        canônica está em src.core.string_utils.only_digits
    """
    if text is None:
        return ""
    return only_digits(str(text))


def format_cnpj_for_display(cnpj: str) -> str:
    """
    Formata CNPJ numerico em 00.000.000/0000-00.
    Se nao tiver 14 digitos (ex.: futuro alfanumerico), retorna como veio.

    Wrapper para compatibilidade. Delega para src.helpers.formatters.format_cnpj.
    """
    from src.helpers.formatters import format_cnpj as _format_cnpj_canonical

    return _format_cnpj_canonical(cnpj)


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
    """Retorna o prefixo do cliente delegando para a função canônica."""
    return build_client_prefix(org_id=org_id, client_id=client_id)


def get_current_org_id(sb) -> str:  # type: ignore[no-untyped-def]
    """Obtem org_id do usuario logado via Supabase."""
    try:
        user = sb.auth.get_user()
        if not user or not user.user:
            return ""
        uid = user.user.id

        # Busca org_id na tabela memberships
        res = sb.table("memberships").select(MEMBERSHIPS_SELECT_ORG_ID).eq("user_id", uid).limit(1).execute()
        if getattr(res, "data", None) and res.data and res.data[0].get("org_id"):
            return res.data[0]["org_id"]
    except Exception as exc:  # noqa: BLE001
        logger.debug("Falha ao obter org_id atual via Supabase: %s", exc)
    return ""
