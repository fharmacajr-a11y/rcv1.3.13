# -*- coding: utf-8 -*-
# data/supabase_repo.py
"""Repositório Supabase para operações CRUD e helpers genéricos.

Este módulo centraliza:
- Helpers genéricos de acesso a tabelas Supabase (get_client, error formatting)
- Autocomplete de clientes

Retry é tratado de forma centralizada por ``exec_postgrest`` (via
``src.infra.retry_policy.retry_call``). Não há retry local neste módulo.

PADRÃO DE IMPORTAÇÃO PARA REPOSITORIES:
---------------------------------------
Os repositories em src/features/* podem usar os helpers genéricos deste módulo:

    from src.db.supabase_repo import (
        get_supabase_client,
        format_api_error,
        PostgrestAPIError,
    )

HELPERS DISPONÍVEIS:
-------------------
- get_supabase_client(): Retorna cliente Supabase único (tenta vários paths)
- format_api_error(exc, operation): Formata erro da API Supabase
- PostgrestAPIError: Exceção base da API Supabase
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any, TypedDict

from src.db.domain_types import ClientRow
from src.infra.supabase_client import exec_postgrest, get_supabase

log = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Supabase response types
# -----------------------------------------------------------------------------
class SupabaseError(TypedDict, total=False):
    """Supabase error response structure."""

    message: str
    details: str | None
    hint: str | None
    code: str | None


class SupabaseResponse(TypedDict, total=False):
    """Supabase execute() response structure."""

    data: Sequence[dict[str, Any]] | None
    error: SupabaseError | None
    count: int | None


# -----------------------------------------------------------------------------
# postgrest APIError (usado em todo o projeto)
# -----------------------------------------------------------------------------
try:
    from postgrest.exceptions import APIError as PostgrestAPIError  # type: ignore[assignment] # supabase-py v2
except Exception:
    # Fallback se lib mudar
    class PostgrestAPIError(Exception):  # type: ignore[no-redef,misc]
        pass


# -----------------------------------------------------------------------------
# Helper genérico: get_supabase_client
# -----------------------------------------------------------------------------
def get_supabase_client() -> Any:
    """
    Retorna o cliente Supabase único do projeto.

    Tenta importar de múltiplos paths para compatibilidade com diferentes layouts:
    1) infra.supabase_client.get_supabase (padrão do projeto)
    2) src.infra.supabase_client.get_supabase (fallback)

    Raises:
        RuntimeError: Se cliente não estiver disponível

    Returns:
        Cliente Supabase configurado
    """
    try:
        client = get_supabase()
        if client is None:
            raise RuntimeError("Cliente Supabase retornou None. Verifique configuração de infra/supabase_client.")
        return client
    except Exception as exc:
        log.exception("Erro ao obter cliente Supabase")
        raise RuntimeError(
            f"Cliente Supabase não disponível: {exc}. Verifique se infra.supabase_client está acessível."
        ) from exc


# -----------------------------------------------------------------------------
# Helper genérico: format_api_error
# -----------------------------------------------------------------------------
def format_api_error(exc: Exception, operation: str) -> RuntimeError:
    """
    Formata erro da API Supabase de forma amigável.

    Extrai code, details e hint do PostgrestAPIError e constrói mensagem padronizada.

    Args:
        exc: Exceção capturada (idealmente PostgrestAPIError)
        operation: Nome da operação (ex: "SELECT", "INSERT", "UPDATE", "DELETE")

    Returns:
        RuntimeError com mensagem formatada

    Example:
        try:
            result = query.execute()
        except PostgrestAPIError as e:
            raise format_api_error(e, "SELECT")
    """
    code: str | None = getattr(exc, "code", None)
    details: str = getattr(exc, "details", None) or getattr(exc, "message", None) or str(exc)
    hint: str | None = getattr(exc, "hint", None)

    msg: str = f"[{operation}] Erro na API: {details}"
    if code:
        msg = f"[{operation}] ({code}) {details}"
    if hint:
        msg += f" | hint: {hint}"

    return RuntimeError(msg)


# -----------------------------------------------------------------------------
# Helper genérico: to_iso_date
# -----------------------------------------------------------------------------
def to_iso_date(d: datetime | Any) -> str:
    """
    Converte date ou datetime para string ISO, ou retorna string como está.

    Args:
        d: date, datetime ou string

    Returns:
        String em formato ISO (YYYY-MM-DD)

    Example:
        >>> from datetime import date
        >>> to_iso_date(date(2025, 1, 15))
        '2025-01-15'
        >>> to_iso_date("2025-01-15")
        '2025-01-15'
    """
    if isinstance(d, str):
        return d
    # Suporta date e datetime
    return d.isoformat() if hasattr(d, "isoformat") else str(d)


# -----------------------------------------------------------------------------
# Helper para autenticação PostgREST
# -----------------------------------------------------------------------------
try:
    from postgrest.exceptions import APIError  # supabase-py v2 usa postgrest
except Exception:
    APIError = Exception  # fallback


def _get_access_token(client: Any) -> str | None:
    """
    supabase-py v2:
      client.auth.get_session() -> objeto com .access_token (ou None)
    """
    try:
        session = client.auth.get_session()
        token = getattr(session, "access_token", None)
        return token if token else None
    except Exception:
        return None


def _ensure_postgrest_auth(client: Any, *, required: bool = False) -> None:
    """
    Se existir token na sessão, injeta no PostgREST.
    Se não existir:
      - loga WARNING
      - se required=True, levanta RuntimeError explicando que sem token o RLS vai negar.
    """
    token = _get_access_token(client)
    if token:
        try:
            client.postgrest.auth(token)
        except Exception as e:
            log.warning("postgrest.auth falhou: %s", e)
    else:
        log.warning("postgrest: sem access_token na sessão; RLS pode negar (auth.uid() = NULL).")
        if required:
            raise RuntimeError("Sessão sem access_token. Faça login novamente para que o RLS reconheça auth.uid().")


# -----------------------------------------------------------------------------
# Cliente Supabase SINGLETON (sempre usar get_supabase do infra)
# -----------------------------------------------------------------------------


# Proxy para compatibilidade com código existente
class _SupabaseProxy:
    def __getattr__(self, name: str) -> Any:
        """Proxy all attribute access to the Supabase singleton."""
        return getattr(get_supabase(), name)


supabase = _SupabaseProxy()


def _now_iso() -> str:
    """Retorna timestamp UTC em formato ISO."""
    return datetime.now(timezone.utc).isoformat()


# -----------------------------------------------------------------------------
# Autocomplete de Clientes
# -----------------------------------------------------------------------------


def search_clients(org_id: str, query: str, limit: int = 20) -> list[ClientRow]:
    """
    Busca clientes por múltiplos campos (razão social, cnpj, nome, telefone, etc).
    Se query < 2 caracteres, retorna resultados sem filtro de texto.
    """
    q = (query or "").strip()
    if not org_id:
        return []

    _ensure_postgrest_auth(supabase)  # Autenticação antes da operação

    def _do() -> Any:
        sel = (
            supabase.table("clients")
            .select("id, org_id, razao_social, cnpj, nome, numero, obs, cnpj_norm")
            .eq("org_id", org_id)
            .is_("deleted_at", None)
        )

        if len(q) >= 2:
            like = f"%{q}%"
            sel = sel.or_(
                ",".join(
                    [
                        f"razao_social.ilike.{like}",
                        f"cnpj.ilike.{like}",
                        f"cnpj_norm.ilike.{like}",
                        f"nome.ilike.{like}",
                        f"numero.ilike.{like}",
                        f"obs.ilike.{like}",
                    ]
                )
            )

        sel = sel.order("razao_social").limit(limit)
        return exec_postgrest(sel)

    try:
        res: Any = _do()
        raw_data = getattr(res, "data", None)
        data: list[ClientRow] = list(raw_data) if raw_data is not None else []
        log.debug("search_clients: %d resultado(s) para query='%s' org_id=%s", len(data), q, org_id)
        return data
    except Exception as e:
        log.warning("search_clients: erro ao buscar, retornando vazio: %s", getattr(e, "args", e))
        return []


def list_clients_for_picker(org_id: str, limit: int = 200) -> list[ClientRow]:
    """
    Lista todos os clientes da organização para exibição no modal picker.
    Usado para carregar lista inicial ao abrir o modal.

    Args:
        org_id: UUID da organização
        limit: Número máximo de resultados (padrão: 200)

    Returns:
        Lista de dicts com: id, org_id, razao_social, cnpj
    """
    if not org_id:
        return []

    _ensure_postgrest_auth(supabase)  # Autenticação antes da operação

    def _do() -> Any:
        return exec_postgrest(
            supabase.table("clients")
            .select("id, org_id, razao_social, cnpj, nome")
            .eq("org_id", org_id)
            .order("razao_social")
            .limit(limit)
        )

    try:
        res: Any = _do()
        raw_data = getattr(res, "data", None)
        data: list[ClientRow] = list(raw_data) if raw_data is not None else []
        log.debug("list_clients_for_picker: %d cliente(s) carregados para org_id=%s", len(data), org_id)
        return data
    except Exception as e:
        log.warning("list_clients_for_picker: erro ao listar, retornando vazio: %s", getattr(e, "args", e))
        return []


# -----------------------------------------------------------------------------
# Public API exports para uso em outros repositories
# -----------------------------------------------------------------------------
__all__ = [
    # Helpers genéricos para repositories
    "get_supabase_client",
    "format_api_error",
    "to_iso_date",
    "PostgrestAPIError",
    # Autocomplete de clientes
    "search_clients",
    "list_clients_for_picker",
]
