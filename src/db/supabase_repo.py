# -*- coding: utf-8 -*-
# data/supabase_repo.py
"""Repositório Supabase para operações CRUD e helpers genéricos.

Este módulo centraliza:
- Helpers genéricos de acesso a tabelas Supabase (get_client, error formatting, retry logic)
- CRUD específico para client_passwords (senhas criptografadas)
- Autocomplete de clientes

PADRÃO DE IMPORTAÇÃO PARA REPOSITORIES:
---------------------------------------
Os repositories em src/features/* podem usar os helpers genéricos deste módulo:

    from src.db.supabase_repo import (
        get_supabase_client,
        format_api_error,
        with_retries,
        PostgrestAPIError,
    )

HELPERS DISPONÍVEIS:
-------------------
- get_supabase_client(): Retorna cliente Supabase único (tenta vários paths)
- format_api_error(exc, operation): Formata erro da API Supabase
- with_retries(fn, tries, base_delay): Executa fn com retry + backoff
- PostgrestAPIError: Exceção base da API Supabase
"""

from __future__ import annotations

import logging
import random
import time
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any, Callable, TypedDict, TypeVar, cast

import httpx
from src.db.domain_types import ClientRow, PasswordRow
from src.infra.supabase_client import exec_postgrest, get_supabase
from src.security.crypto import decrypt_text, encrypt_text

T = TypeVar("T")

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


def _rls_precheck_membership(client: Any, org_id: str, user_id: str) -> None:
    """
    Verifica se o token atual enxerga uma linha em public.memberships para (org_id, user_id).
    Levanta RuntimeError com mensagem amigável se não enxergar.
    """
    _ensure_postgrest_auth(client, required=True)

    def _query() -> Any:
        return exec_postgrest(
            client.table("memberships")
            .select("user_id", count="exact")
            .eq("org_id", org_id)
            .eq("user_id", user_id)
            .limit(1)
        )

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


def with_retries(fn: Callable[[], T], tries: int = 3, base_delay: float = 0.4) -> T:
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
            # jitter de backoff; n?o usado como RNG criptogr?fico
            delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 0.15)  # nosec B311
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


def list_passwords(org_id: str, limit: int | None = None, offset: int = 0) -> list[PasswordRow]:
    """
    Lista todas as senhas da organização com dados do cliente via JOIN.
    Retorna lista de dicts com campos: id, org_id, client_name, service,
    username, password_enc, notes, created_by, created_at, updated_at,
    client_id, razao_social, cnpj, nome (contato), whatsapp (mapeado de numero), client_external_id.

    A senha vem criptografada (password_enc); use decrypt_for_view() para exibir.

    Args:
        org_id: ID da organização
        limit: Número máximo de registros (None = sem limite) - PERF-003
        offset: Número de registros a pular - PERF-003
    """
    if not org_id:
        raise ValueError("org_id é obrigatório")

    try:
        _ensure_postgrest_auth(supabase)  # Autenticação antes da operação

        def _do() -> Any:
            # JOIN com clients para obter dados completos do cliente
            # Campos do client_passwords: *,
            # Campos de clients: id (renomeado), razao_social, cnpj, nome, numero (WhatsApp)
            select_query = "*,clients!client_id(id,razao_social,cnpj,nome,numero)"
            query = (
                supabase.table("client_passwords")
                .select(select_query)
                .eq("org_id", org_id)
                .order("updated_at", desc=True)
            )

            # PERF-003: Aplica paginação se especificado
            if limit is not None:
                query = query.range(offset, offset + limit - 1)

            return exec_postgrest(query)

        res: Any = with_retries(_do)
        raw_data = getattr(res, "data", None)

        # Achata os dados do JOIN para facilitar o uso
        flattened_data: list[PasswordRow] = []
        if raw_data is not None:
            for row in raw_data:
                # Copia os campos do password
                password_dict = dict(row)

                # Extrai dados do cliente (se existir)
                client_data = password_dict.pop("clients", None)
                if client_data and isinstance(client_data, dict):
                    # Adiciona campos do cliente ao dict principal
                    password_dict["client_external_id"] = client_data.get("id", "")
                    password_dict["razao_social"] = client_data.get("razao_social", "")
                    password_dict["cnpj"] = client_data.get("cnpj", "")
                    password_dict["nome"] = client_data.get("nome", "")
                    # Campo "numero" contém o WhatsApp
                    password_dict["whatsapp"] = client_data.get("numero", "")
                else:
                    # Se não houver cliente, preenche com vazios
                    password_dict["client_external_id"] = ""
                    password_dict["razao_social"] = password_dict.get("client_name", "")
                    password_dict["cnpj"] = ""
                    password_dict["nome"] = ""
                    password_dict["whatsapp"] = ""

                flattened_data.append(cast(PasswordRow, password_dict))

        log.info("list_passwords: %d registro(s) encontrado(s) para org_id=%s", len(flattened_data), org_id)
        return flattened_data
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
    client_id: str | None = None,
) -> PasswordRow:
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

        # Adicionar client_id se fornecido
        if client_id is not None:
            payload["client_id"] = client_id

        log.info(
            "pwd.add -> org_id=%s created_by=%s client=%s service=%s username=%s",
            org_id,
            created_by,
            client_name,
            service,
            username,
        )

        def _insert() -> Any:
            return exec_postgrest(supabase.table("client_passwords").insert(payload))

        res: Any = with_retries(_insert)
        raw_data = getattr(res, "data", None)
        data: list[PasswordRow] = list(raw_data) if raw_data is not None else []
        if not data:
            raise RuntimeError("Insert não retornou dados")
        log.info("add_password: registro criado com id=%s", data[0].get("id"))
        return data[0]
    except Exception as e:
        log.exception("Erro ao adicionar senha")
        raise RuntimeError(f"Falha ao adicionar senha: {e}")


def update_password(
    id: str,
    client_name: str | None = None,
    service: str | None = None,
    username: str | None = None,
    password_plain: str | None = None,
    notes: str | None = None,
    client_id: str | None = None,
) -> PasswordRow:
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
        if client_id is not None:
            payload["client_id"] = client_id

        def _do() -> Any:
            return exec_postgrest(supabase.table("client_passwords").update(payload).eq("id", id))

        res: Any = with_retries(_do)
        raw_data = getattr(res, "data", None)
        data: list[PasswordRow] = list(raw_data) if raw_data is not None else []
        if not data:
            raise RuntimeError("Update não retornou dados")
        log.info("update_password: registro id=%s atualizado", id)
        return data[0]
    except Exception as e:
        log.exception("Erro ao atualizar senha id=%s", id)
        raise RuntimeError(f"Falha ao atualizar senha: {e}")


def delete_password(id: str) -> None:
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


def delete_passwords_by_client(org_id: str, client_id: str) -> int:
    """
    Remove todas as senhas de um cliente específico.

    Args:
        org_id: ID da organização proprietária
        client_id: ID do cliente cujas senhas serão excluídas

    Returns:
        Número de senhas excluídas
    """
    if not org_id:
        raise ValueError("org_id é obrigatório")
    if not client_id:
        raise ValueError("client_id é obrigatório")

    try:
        _ensure_postgrest_auth(supabase)  # Autenticação antes da operação

        def _do() -> Any:
            return exec_postgrest(
                supabase.table("client_passwords").delete().eq("org_id", org_id).eq("client_id", client_id)
            )

        res: Any = with_retries(_do)
        # O Supabase retorna os registros deletados em res.data
        raw_data = getattr(res, "data", None)
        count = len(raw_data) if raw_data else 0
        log.info("delete_passwords_by_client: %d senha(s) removida(s) para client_id=%s", count, client_id)
        return count
    except Exception as e:
        log.exception("Erro ao excluir senhas do client_id=%s", client_id)
        raise RuntimeError(f"Falha ao excluir senhas do cliente: {e}")


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
        res: Any = with_retries(_do)
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
        res: Any = with_retries(_do)
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
    "with_retries",
    "PostgrestAPIError",
    # CRUD de senhas (específico deste módulo)
    "list_passwords",
    "add_password",
    "update_password",
    "delete_password",
    "delete_passwords_by_client",
    "decrypt_for_view",
    # Autocomplete de clientes
    "search_clients",
    "list_clients_for_picker",
]
