# -*- coding: utf-8 -*-
# data/supabase_repo.py
"""Repositório Supabase para operações CRUD na tabela client_passwords."""

from __future__ import annotations

import time
import random
import logging
from datetime import datetime, timezone
from typing import Any, Callable, TypedDict
from collections.abc import Sequence

import httpx

from infra.supabase_client import exec_postgrest, get_supabase
from security.crypto import encrypt_text, decrypt_text

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


# Type aliases for client records
ClientRow = dict[str, Any]  # Generic client row (future: can be TypedDict)
PasswordRow = dict[str, Any]  # Generic password row (future: can be TypedDict)


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
        sess = client.auth.get_session()
        token = getattr(sess, "access_token", None)
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


def _rls_precheck_membership(client: Any, org_id: str, user_id: str) -> None:
    """
    Verifica se o token atual enxerga uma linha em public.memberships para (org_id, user_id).
    Levanta RuntimeError com mensagem amigável se não enxergar.
    """
    _ensure_postgrest_auth(client, required=True)

    def _query() -> Any:
        return exec_postgrest(client.table("memberships").select("user_id", count="exact").eq("org_id", org_id).eq("user_id", user_id).limit(1))

    res: Any = with_retries(_query)  # Type: APIResponse from postgrest

    # res pode ser None se a lib lançar algo estranho; trate tudo defensivamente
    data = getattr(res, "data", None)
    if not data:
        msg = (
            "RLS precheck: a API NÃO enxerga membership para este token. "
            f"(org_id={org_id}, user_id={user_id}). "
            "Sem isso, o INSERT em client_passwords cairá em 42501."
        )
        raise RuntimeError(msg)

    log.info("RLS precheck OK: membership visível para org_id=%s user_id=%s", org_id, user_id)


# -----------------------------------------------------------------------------
# Cliente Supabase SINGLETON (sempre usar get_supabase do infra)
# -----------------------------------------------------------------------------


# Proxy para compatibilidade com código existente
class _SupabaseProxy:
    def __getattr__(self, name: str) -> Any:
        """Proxy all attribute access to the Supabase singleton."""
        return getattr(get_supabase(), name)


supabase = _SupabaseProxy()


# -----------------------------------------------------------------------------
# Retry helper com backoff exponencial
# -----------------------------------------------------------------------------
RETRY_ERRORS = (
    httpx.ReadError,
    httpx.WriteError,
    httpx.ConnectError,
    httpx.ConnectTimeout,
    OSError,
)


def with_retries(fn: Callable[[], Any], tries: int = 3, base_delay: float = 0.4) -> Any:
    """
    Executa fn() com tentativas e backoff exponencial + jitter.
    Re-tenta em erros de rede/transientes (inclui WinError 10035) e 5xx.
    """
    last_exc = None
    for attempt in range(1, tries + 1):
        try:
            return fn()
        except RETRY_ERRORS as e:
            # WinError 10035 é transitório
            if isinstance(e, OSError) and getattr(e, "errno", None) not in (10035,):
                last_exc = e
            else:
                last_exc = e
        except Exception as e:
            msg = str(e).lower()
            # respostas 5xx às vezes chegam encapsuladas
            if "502" in msg or "bad gateway" in msg or "5xx" in msg or "503" in msg:
                last_exc = e
            else:
                raise

        if attempt < tries:
            delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 0.15)
            time.sleep(delay)

    if last_exc is None:
        raise RuntimeError("Unexpected None error from Postgrest")
    raise last_exc


def _now_iso() -> str:
    """Retorna timestamp UTC em formato ISO."""
    return datetime.now(timezone.utc).isoformat()


# -----------------------------------------------------------------------------
# CRUD para client_passwords (ORG-aware)
# -----------------------------------------------------------------------------


def list_passwords(org_id: str) -> list[dict[str, Any]]:
    """
    Lista todas as senhas da organização.
    Retorna lista de dicts com campos: id, org_id, client_name, service,
    username, password_enc, notes, created_by, created_at, updated_at.

    A senha vem criptografada (password_enc); use decrypt_for_view() para exibir.
    """
    if not org_id:
        raise ValueError("org_id é obrigatório")

    try:
        _ensure_postgrest_auth(supabase)  # Autenticação antes da operação

        def _do() -> Any:
            return exec_postgrest(supabase.table("client_passwords").select("*").eq("org_id", org_id).order("updated_at", desc=True))

        res: Any = with_retries(_do)
        raw_data = getattr(res, "data", None)
        data: list[dict[str, Any]] = list(raw_data) if raw_data is not None else []
        log.info("list_passwords: %d registro(s) encontrado(s) para org_id=%s", len(data), org_id)
        return data
    except Exception as e:
        log.exception("Erro ao listar senhas para org_id=%s", org_id)
        raise RuntimeError(f"Falha ao listar senhas: {e}")


def add_password(
    org_id: str,
    client_name: str,
    service: str,
    username: str,
    password_plain: str,
    notes: str,
    created_by: str,
) -> dict[str, Any]:
    """
    Adiciona uma nova senha na tabela.
    A senha é criptografada antes de ser inserida.
    Retorna o registro criado.
    """
    if not org_id or not client_name or not service:
        raise ValueError("org_id, client_name e service são obrigatórios")

    try:
        # 1) Garante autenticação (required=True levanta erro se sem token)
        _ensure_postgrest_auth(supabase, required=True)

        # 2) Precheck RLS - confere membership com o token atual
        _rls_precheck_membership(supabase, org_id, created_by)

        # 3) Criptografia
        password_enc = encrypt_text(password_plain) if password_plain else ""

        payload = {
            "org_id": org_id,
            "client_name": client_name,
            "service": service,
            "username": username or "",
            "password_enc": password_enc,
            "notes": notes or "",
            "created_by": created_by or "",
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }

        log.info("pwd.add -> org_id=%s created_by=%s client=%s service=%s username=%s", org_id, created_by, client_name, service, username)

        def _insert() -> Any:
            return exec_postgrest(supabase.table("client_passwords").insert(payload))

        res: Any = with_retries(_insert)
        raw_data = getattr(res, "data", None)
        data: list[dict[str, Any]] = list(raw_data) if raw_data is not None else []
        if not data:
            raise RuntimeError("Insert não retornou dados")
        log.info("add_password: registro criado com id=%s", data[0].get("id"))
        return data[0]
    except Exception as e:
        log.exception("Erro ao adicionar senha")
        raise RuntimeError(f"Falha ao adicionar senha: {e}")


def update_password(
    id: int,
    client_name: str | None = None,
    service: str | None = None,
    username: str | None = None,
    password_plain: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """
    Atualiza um registro existente.
    Se password_plain for fornecido, atualiza o password_enc criptografado.
    Retorna o registro atualizado.
    """
    if not id:
        raise ValueError("id é obrigatório")

    try:
        _ensure_postgrest_auth(supabase)  # Autenticação antes da operação

        payload: dict[str, Any] = {"updated_at": _now_iso()}

        if client_name is not None:
            payload["client_name"] = client_name
        if service is not None:
            payload["service"] = service
        if username is not None:
            payload["username"] = username
        if notes is not None:
            payload["notes"] = notes
        if password_plain is not None:
            payload["password_enc"] = encrypt_text(password_plain) if password_plain else ""

        def _do() -> Any:
            return exec_postgrest(supabase.table("client_passwords").update(payload).eq("id", id))

        res: Any = with_retries(_do)
        raw_data = getattr(res, "data", None)
        data: list[dict[str, Any]] = list(raw_data) if raw_data is not None else []
        if not data:
            raise RuntimeError("Update não retornou dados")
        log.info("update_password: registro id=%s atualizado", id)
        return data[0]
    except Exception as e:
        log.exception("Erro ao atualizar senha id=%s", id)
        raise RuntimeError(f"Falha ao atualizar senha: {e}")


def delete_password(id: int) -> None:
    """
    Remove um registro da tabela.
    """
    if not id:
        raise ValueError("id é obrigatório")

    try:
        _ensure_postgrest_auth(supabase)  # Autenticação antes da operação

        def _do() -> Any:
            return exec_postgrest(supabase.table("client_passwords").delete().eq("id", id))

        with_retries(_do)
        log.info("delete_password: registro id=%s removido", id)
    except Exception as e:
        log.exception("Erro ao excluir senha id=%s", id)
        raise RuntimeError(f"Falha ao excluir senha: {e}")


def decrypt_for_view(token: str) -> str:
    """
    Helper para descriptografar uma senha criptografada (token base64).
    Usado principalmente para copiar senha para o clipboard.
    """
    try:
        return decrypt_text(token)
    except Exception as e:
        log.exception("Erro ao descriptografar senha")
        raise RuntimeError(f"Falha ao descriptografar: {e}")


# -----------------------------------------------------------------------------
# Autocomplete de Clientes
# -----------------------------------------------------------------------------


def search_clients(org_id: str, query: str, limit: int = 20) -> list[dict[str, Any]]:
    """
    Busca clientes por razão social, nome fantasia ou CNPJ (ORG-aware).
    Retorna lista de dicts com: id, org_id, razao_social, nome_fantasia, cnpj.
    Se query < 2 caracteres, retorna resultados sem filtro de texto.
    """
    q = (query or "").strip()
    if not org_id:
        return []

    _ensure_postgrest_auth(supabase)  # Autenticação antes da operação

    ilike = f"%{q}%"

    def _do() -> Any:
        sel = supabase.table("clients").select("id, org_id, razao_social, nome_fantasia, cnpj").eq("org_id", org_id)

        if len(q) >= 2:
            sel = sel.or_(f"razao_social.ilike.{ilike},nome_fantasia.ilike.{ilike},cnpj.ilike.{ilike}").order("razao_social").limit(limit)
        else:
            sel = sel.order("razao_social").limit(limit)

        return exec_postgrest(sel)

    try:
        res: Any = with_retries(_do)
        raw_data = getattr(res, "data", None)
        data: list[dict[str, Any]] = list(raw_data) if raw_data is not None else []
        log.debug("search_clients: %d resultado(s) para query='%s' org_id=%s", len(data), q, org_id)
        return data
    except Exception as e:
        log.warning("search_clients: erro ao buscar, retornando vazio: %s", getattr(e, "args", e))
        return []


def list_clients_for_picker(org_id: str, limit: int = 200) -> list[dict[str, Any]]:
    """
    Lista todos os clientes da organização para exibição no modal picker.
    Usado para carregar lista inicial ao abrir o modal.

    Args:
        org_id: UUID da organização
        limit: Número máximo de resultados (padrão: 200)

    Returns:
        Lista de dicts com: id, org_id, razao_social, nome_fantasia, cnpj
    """
    if not org_id:
        return []

    _ensure_postgrest_auth(supabase)  # Autenticação antes da operação

    def _do() -> Any:
        return exec_postgrest(
            supabase.table("clients").select("id, org_id, razao_social, nome_fantasia, cnpj").eq("org_id", org_id).order("razao_social").limit(limit)
        )

    try:
        res: Any = with_retries(_do)
        raw_data = getattr(res, "data", None)
        data: list[dict[str, Any]] = list(raw_data) if raw_data is not None else []
        log.debug("list_clients_for_picker: %d cliente(s) carregados para org_id=%s", len(data), org_id)
        return data
    except Exception as e:
        log.warning("list_clients_for_picker: erro ao listar, retornando vazio: %s", getattr(e, "args", e))
        return []
