# core/services/notes_service.py
"""Serviço de anotações compartilhadas por organização (append-only)."""

from __future__ import annotations

import errno
import logging
import random
import time
from typing import Any, Callable, Dict, List

from infra.supabase_client import exec_postgrest, get_supabase

log = logging.getLogger(__name__)

TABLE = "rc_notes"


# -------------------- Exceções Customizadas --------------------


class NotesTableMissingError(Exception):
    """Exceção levantada quando a tabela rc_notes não existe no Supabase."""

    pass


class NotesAuthError(Exception):
    """Exceção levantada quando há erro de permissão RLS (Row Level Security)."""

    pass


class NotesTransientError(Exception):
    """Falha transitória de rede/IO: deve ser re-tentada mais tarde."""

    pass


# -------------------- Helpers de Retry e Detecção de Erros Transitórios --------------------


def _is_transient_net_error(e: Exception) -> bool:
    """
    Detecta se o erro é transitório de rede/IO que deve ser re-tentado.

    Args:
        e: Exceção capturada

    Returns:
        True se for erro transitório (timeout, WinError 10035, connection reset, etc.)
    """
    s = str(e).lower()

    # WSAEWOULDBLOCK (WinError 10035), timeouts, connection resets, etc.
    if "10035" in s or "wouldblock" in s:
        return True
    if "timeout" in s or "timed out" in s:
        return True
    if "connection aborted" in s or "connection reset" in s:
        return True
    if "temporarily unavailable" in s or "temporary failure" in s:
        return True

    # Alguns objetos possuem .errno
    if hasattr(e, "errno") and getattr(e, "errno") in (errno.EWOULDBLOCK, errno.EAGAIN):
        return True

    return False


def _with_retry(fn: Callable[[], Any], *, retries: int = 3, base_sleep: float = 0.25) -> Any:
    """
    Wrapper de retry com backoff exponencial + jitter para erros transitórios.

    Args:
        fn: Função a ser executada (sem argumentos)
        retries: Número máximo de tentativas
        base_sleep: Tempo base de espera (será multiplicado exponencialmente)

    Returns:
        Resultado da função

    Raises:
        NotesTransientError: Se todas as tentativas falharem com erro transitório
        Exception: Se houver erro não transitório (propaga imediatamente)
    """
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            return fn()
        except Exception as ex:
            if _is_transient_net_error(ex):
                # Backoff exponencial + jitter
                sleep = (base_sleep * (2 ** (attempt - 1))) + random.uniform(0.0, 0.15)
                log.debug(
                    "notes_service: falha transitória (%s). retry %d/%d em %.2fs",
                    ex,
                    attempt,
                    retries,
                    sleep,
                )
                time.sleep(sleep)
                last_exc = ex
                continue
            # Não transitório -> propaga imediatamente
            raise

    # Esgotou todas as tentativas
    raise NotesTransientError(str(last_exc) if last_exc else "Falha transitória esgotada")


# -------------------- Helpers de Tratamento de Erro --------------------


def _check_table_missing_error(exception: Exception) -> None:
    """
    Verifica se o erro é devido à tabela ausente (PGRST205).

    Args:
        exception: Exceção capturada do Supabase

    Raises:
        NotesTableMissingError: Se tabela não existir
    """
    error_str = str(exception).lower()

    # Verificar código PGRST205 ou mensagens relacionadas
    if "pgrst205" in error_str or "relation" in error_str and "does not exist" in error_str:
        raise NotesTableMissingError(f"Tabela '{TABLE}' ausente no Supabase. Execute a migration: migrations/rc_notes_migration.sql")

    # Verificar atributos do erro (se disponível)
    if hasattr(exception, "code") and getattr(exception, "code") == "PGRST205":
        raise NotesTableMissingError(f"Tabela '{TABLE}' ausente no Supabase. Execute a migration: migrations/rc_notes_migration.sql")

    # Verificar dict-like errors
    if hasattr(exception, "get"):
        code = exception.get("code")  # type: ignore
        if code == "PGRST205":
            raise NotesTableMissingError(f"Tabela '{TABLE}' ausente no Supabase. Execute a migration: migrations/rc_notes_migration.sql")


def _check_auth_error(exception: Exception) -> None:
    """
    Verifica se o erro é devido a falha de permissão RLS (42501).

    Args:
        exception: Exceção capturada do Supabase

    Raises:
        NotesAuthError: Se houver erro de permissão RLS
    """
    error_str = str(exception).lower()

    # Verificar código 42501 (permission denied)
    if "42501" in error_str or "permission denied" in error_str:
        raise NotesAuthError("Sem permissão (RLS): verifique seu org_id em public.profiles.")

    # Verificar atributos do erro (se disponível)
    if hasattr(exception, "code") and getattr(exception, "code") == "42501":
        raise NotesAuthError("Sem permissão (RLS): verifique seu org_id em public.profiles.")

    # Verificar dict-like errors
    if hasattr(exception, "get"):
        code = exception.get("code")  # type: ignore
        if code == "42501":
            raise NotesAuthError("Sem permissão (RLS): verifique seu org_id em public.profiles.")


# -------------------- Funções Públicas --------------------

# -------------------- Helpers de Normalização de E-mail Legado --------------------


def _normalize_author_emails(rows: List[dict], org_id: str) -> List[dict]:
    """
    Normaliza author_email de notas legadas (prefixo → email completo).
    Aplica aliases (ex: pharmaca2013 → fharmaca2013).

    Args:
        rows: Lista de notas do Supabase
        org_id: UUID da organização

    Returns:
        Lista com author_email normalizado (lowercase e completo)
    """
    try:
        from src.core.services.profiles_service import (
            EMAIL_PREFIX_ALIASES,
            get_email_prefix_map,
        )

        emap = get_email_prefix_map(org_id) or {}
    except Exception:
        emap = {}

    out = []
    for r in rows:
        email = (r.get("author_email") or "").strip()
        if email and "@" not in email:
            email_lc = email.lower()
            # Aplicar alias antes de consultar o mapa
            prefix = EMAIL_PREFIX_ALIASES.get(email_lc, email_lc)
            email = emap.get(prefix, email)
        nr = dict(r)
        nr["author_email"] = (email or "").strip().lower()
        out.append(nr)
    return out


def list_notes(org_id: str, limit: int = 500) -> List[Dict[str, Any]]:
    """
    Lista todas as anotações da organização, ordenadas cronologicamente (mais antigas primeiro).

    Args:
        org_id: UUID da organização
        limit: Número máximo de registros

    Returns:
        Lista de dicionários com: id, author_email, body, created_at

    Raises:
        NotesTableMissingError: Se a tabela rc_notes não existir no Supabase
        NotesTransientError: Se houver falha transitória de rede após retries
    """

    def _call():
        supa = get_supabase()
        resp = exec_postgrest(supa.table(TABLE).select("id, author_email, body, created_at").eq("org_id", org_id).order("created_at", desc=False).limit(limit))
        rows = resp.data or []
        # Normalizar emails legados (prefixo → email completo, com aliases)
        return _normalize_author_emails(rows, org_id)

    try:
        return _with_retry(_call, retries=3, base_sleep=0.25)
    except NotesTransientError as e:
        # Reduzir ruído: WARNING único
        log.warning("Falha transitória ao listar notas: %s", e)
        raise
    except NotesTableMissingError:
        # Re-raise para tratamento específico no caller
        raise
    except Exception as e:
        # Verificar se é erro de tabela ausente
        try:
            _check_table_missing_error(e)
        except NotesTableMissingError:
            log.warning("Tabela %s não encontrada no Supabase (PGRST205)", TABLE)
            raise

        # Outro tipo de erro
        log.error("Erro ao listar notas: %s", e)
        return []


def add_note(org_id: str, author_email: str, body: str) -> Dict[str, Any]:
    """
    Adiciona nova anotação (append-only).

    Args:
        org_id: UUID da organização
        author_email: Email do autor
        body: Texto da anotação (max 1000 chars)

    Returns:
        Registro inserido

    Raises:
        ValueError: Se anotação vazia ou inválida
        NotesTableMissingError: Se a tabela rc_notes não existir no Supabase
        NotesAuthError: Se houver erro de permissão RLS
        NotesTransientError: Se houver falha transitória de rede após retries
    """
    body = (body or "").strip()
    if not body:
        raise ValueError("Anotação vazia.")

    # Limitar tamanho (server também valida)
    if len(body) > 1000:
        body = body[:1000]

    # Normalizar author_email: corrigir alias e garantir e-mail completo
    author_email = (author_email or "").strip().lower()
    # Se vier só o prefixo (sem @), corrigir alias e resolver e-mail completo
    if "@" not in author_email:
        from src.core.services.profiles_service import (
            EMAIL_PREFIX_ALIASES,
            get_email_prefix_map,
        )

        prefix = EMAIL_PREFIX_ALIASES.get(author_email, author_email)
        emap = {}
        try:
            emap = get_email_prefix_map(org_id) or {}
        except Exception:
            pass
        author_email = emap.get(prefix, author_email)

    # Log de diagnóstico
    email_prefix = author_email.split("@")[0][:8] if "@" in author_email else author_email[:8]
    log.info("notes.add", extra={"org_id": org_id, "author_email_prefix": email_prefix})

    payload = {"org_id": org_id, "author_email": author_email, "body": body}

    def _call():
        supa = get_supabase()
        resp = exec_postgrest(supa.table(TABLE).insert(payload))
        return (resp.data or [{}])[0]

    try:
        return _with_retry(_call, retries=3, base_sleep=0.25)
    except NotesTransientError as e:
        log.warning("Falha transitória ao adicionar nota: %s", e)
        raise
    except NotesTableMissingError:
        # Re-raise para tratamento específico no caller
        raise
    except NotesAuthError:
        # Re-raise para tratamento específico no caller
        raise
    except Exception as e:
        # Verificar se é erro de tabela ausente
        try:
            _check_table_missing_error(e)
        except NotesTableMissingError:
            log.warning("Tabela %s não encontrada no Supabase (PGRST205)", TABLE)
            raise

        # Verificar se é erro de permissão RLS
        try:
            _check_auth_error(e)
        except NotesAuthError:
            log.warning(
                "Erro de permissão RLS (42501): org_id=%s, author=%s",
                org_id,
                email_prefix,
            )
            raise

        # Outro tipo de erro
        log.error("Erro ao adicionar nota: %s", e)
        raise


def list_notes_since(org_id: str, since_iso: str | None) -> list[dict]:
    """
    Retorna notas da org mais novas que 'since_iso' (ISO-8601).
    Se since_iso for None, retorna [] (porque o Hub já carrega o histórico completo em outro fluxo).

    Args:
        org_id: UUID da organização
        since_iso: Timestamp ISO-8601 para filtrar notas mais recentes

    Returns:
        Lista de notas mais recentes que since_iso, ordenadas crescente por created_at
    """
    if not since_iso:
        return []

    def _call():
        supa = get_supabase()
        # created_at > since_iso, ordenado crescente
        resp = exec_postgrest(
            supa.table(TABLE)
            .select("id,created_at,author_email,author_name,body")
            .eq("org_id", org_id)
            .gt("created_at", since_iso)
            .order("created_at", desc=False)
            .limit(100)
        )
        rows = resp.data or []
        # Normalizar emails legados (prefixo → email completo, com aliases)
        return _normalize_author_emails(rows, org_id)

    try:
        return _with_retry(_call, retries=2, base_sleep=0.1)
    except Exception as e:
        log.debug("Erro ao buscar notas incrementais: %s", e)
        return []
