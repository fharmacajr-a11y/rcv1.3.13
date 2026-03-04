# core/services/notes_service.py

"""ServiÃ§o de anotaÃ§Ãµes compartilhadas por organizaÃ§Ã£o (append-only)."""

from __future__ import annotations


import errno

import logging

from typing import Any


from src.infra.db_schemas import RC_NOTES_SELECT_FIELDS_LIST
from src.infra.supabase_client import exec_postgrest, get_supabase


log = logging.getLogger(__name__)


TABLE = "rc_notes"


# -------------------- ExceÃ§Ãµes Customizadas --------------------


class NotesTableMissingError(Exception):
    """ExceÃ§Ã£o levantada quando a tabela rc_notes nÃ£o existe no Supabase."""

    pass


class NotesAuthError(Exception):
    """ExceÃ§Ã£o levantada quando hÃ¡ erro de permissÃ£o RLS (Row Level Security)."""

    pass


class NotesTransientError(Exception):
    """Falha transitÃ³ria de rede/IO: deve ser re-tentada mais tarde."""

    pass


# -------------------- Helpers de Retry e DetecÃ§Ã£o de Erros TransitÃ³rios --------------------


def _is_transient_net_error(e: BaseException) -> bool:
    """

    Detecta se o erro Ã© transitÃ³rio de rede/IO que deve ser re-tentado.



    Args:

        e: ExceÃ§Ã£o capturada



    Returns:

        True se for erro transitÃ³rio (timeout, WinError 10035, connection reset, etc.)

    """

    s: str = str(e).lower()

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


# -------------------- Helpers de Tratamento de Erro --------------------


def _check_table_missing_error(exception: BaseException) -> None:
    """

    Verifica se o erro Ã© devido Ã  tabela ausente (PGRST205).



    Args:

        exception: ExceÃ§Ã£o capturada do Supabase



    Raises:

        NotesTableMissingError: Se tabela nÃ£o existir

    """

    error_str: str = str(exception).lower()

    # Verificar cÃ³digo PGRST205 ou mensagens relacionadas

    if "pgrst205" in error_str or ("relation" in error_str and "does not exist" in error_str):
        raise NotesTableMissingError(
            f"Tabela '{TABLE}' ausente no Supabase. Execute a migration: migrations/rc_notes_migration.sql"
        )

    # Verificar atributos do erro (se disponÃ­vel)

    if hasattr(exception, "code") and getattr(exception, "code") == "PGRST205":
        raise NotesTableMissingError(
            f"Tabela '{TABLE}' ausente no Supabase. Execute a migration: migrations/rc_notes_migration.sql"
        )

    # Verificar dict-like errors

    if hasattr(exception, "get"):
        code = exception.get("code")  # type: ignore

        if code == "PGRST205":
            raise NotesTableMissingError(
                f"Tabela '{TABLE}' ausente no Supabase. Execute a migration: migrations/rc_notes_migration.sql"
            )


def _check_auth_error(exception: BaseException) -> None:
    """

    Verifica se o erro Ã© devido a falha de permissÃ£o RLS (42501).



    Args:

        exception: ExceÃ§Ã£o capturada do Supabase



    Raises:

        NotesAuthError: Se houver erro de permissÃ£o RLS

    """

    error_str: str = str(exception).lower()

    # Verificar cÃ³digo 42501 (permission denied)

    if "42501" in error_str or "permission denied" in error_str:
        raise NotesAuthError("Sem permissÃ£o (RLS): verifique seu org_id em public.profiles.")

    # Verificar atributos do erro (se disponÃ­vel)

    if hasattr(exception, "code") and getattr(exception, "code") == "42501":
        raise NotesAuthError("Sem permissÃ£o (RLS): verifique seu org_id em public.profiles.")

    # Verificar dict-like errors

    if hasattr(exception, "get"):
        code = exception.get("code")  # type: ignore

        if code == "42501":
            raise NotesAuthError("Sem permissÃ£o (RLS): verifique seu org_id em public.profiles.")


# -------------------- FunÃ§Ãµes PÃºblicas --------------------


# -------------------- Helpers de NormalizaÃ§Ã£o de E-mail Legado --------------------


def _normalize_author_emails(rows: list[dict[str, Any]], org_id: str) -> list[dict[str, Any]]:
    """

    Normaliza author_email de notas legadas (prefixo â†’ email completo).

    Aplica aliases (ex: pharmaca2013 â†’ fharmaca2013).



    Args:

        rows: Lista de notas do Supabase

        org_id: UUID da organizaÃ§Ã£o



    Returns:

        Lista com author_email normalizado (lowercase e completo)

    """

    try:
        from src.core.services.profiles_service import (
            EMAIL_PREFIX_ALIASES,
            get_email_prefix_map,
        )

        emap: dict[str, str] = get_email_prefix_map(org_id) or {}

    except Exception:
        emap = {}

    out: list[dict[str, Any]] = []

    for r in rows:
        email: str = (r.get("author_email") or "").strip()

        if email and "@" not in email:
            email_lc: str = email.lower()

            # Aplicar alias antes de consultar o mapa

            prefix: str = EMAIL_PREFIX_ALIASES.get(email_lc, email_lc)

            email = emap.get(prefix, email)

        nr: dict[str, Any] = dict(r)

        nr["author_email"] = (email or "").strip().lower()

        out.append(nr)

    return out


def _normalize_body(body: str) -> str:
    body = (body or "").strip()

    if not body:
        raise ValueError("Anotação vazia.")

    if len(body) > 1000:
        body = body[:1000]

    return body


def _normalize_author_email_for_org(author_email: str, org_id: str) -> str:
    author_email = (author_email or "").strip().lower()

    if "@" not in author_email:
        from src.core.services.profiles_service import (
            EMAIL_PREFIX_ALIASES,
            get_email_prefix_map,
        )

        prefix: str = EMAIL_PREFIX_ALIASES.get(author_email, author_email)

        emap: dict[str, str] = {}

        try:
            emap = get_email_prefix_map(org_id) or {}

        except Exception as exc:
            log.debug("notes_service: falha ao carregar mapa de aliases", exc_info=exc)

        author_email = emap.get(prefix, author_email)

    return author_email


def _email_prefix(author_email: str) -> str:
    return author_email.split("@")[0][:8] if "@" in author_email else author_email[:8]


def _handle_table_missing_error_logged(exception: BaseException) -> None:
    try:
        _check_table_missing_error(exception)

    except NotesTableMissingError:
        log.warning("Tabela %s nÇœo encontrada no Supabase (PGRST205)", TABLE)

        raise


def _handle_auth_error_logged(exception: BaseException, org_id: str, email_prefix: str) -> None:
    try:
        _check_auth_error(exception)

    except NotesAuthError:
        log.warning(
            "Erro de permissÇœo RLS (42501): org_id=%s, author=%s",
            org_id,
            email_prefix,
        )

        raise


def _fetch_notes(org_id: str, limit: int) -> list[dict[str, Any]]:
    supa = get_supabase()

    resp = exec_postgrest(
        supa.table(TABLE)
        .select(RC_NOTES_SELECT_FIELDS_LIST)
        .eq("org_id", org_id)
        .order("created_at", desc=True)
        .limit(limit)
    )

    rows: list[dict[str, Any]] = resp.data or []

    return _normalize_author_emails(rows, org_id)


def _insert_note_with_retry(payload: dict[str, str], org_id: str, email_prefix: str) -> dict[str, Any]:
    def _call() -> dict[str, Any]:
        supa = get_supabase()

        resp = exec_postgrest(supa.table(TABLE).insert(payload))

        return (resp.data or [{}])[0]

    try:
        return _call()

    except NotesTableMissingError:
        raise

    except NotesAuthError:
        raise

    except Exception as e:
        _handle_table_missing_error_logged(e)

        _handle_auth_error_logged(e, org_id, email_prefix)

        if _is_transient_net_error(e):
            log.warning("Falha transitória ao adicionar nota: %s", e)
            raise NotesTransientError(str(e)) from e

        log.error("Erro ao adicionar nota: %s", e)

        raise


def list_notes(org_id: str, limit: int = 500) -> list[dict[str, Any]]:
    """

    Lista todas as anota????es da organiza???o, ordenadas cronologicamente (mais antigas primeiro).



    Args:

        org_id: UUID da organiza???o

        limit: N?mero m?ximo de registros



    Returns:

        Lista de dicion?rios com: id, author_email, body, created_at



    Raises:

        NotesTableMissingError: Se a tabela rc_notes n?o existir no Supabase

        NotesTransientError: Se houver falha transit??ria de rede ap??s retries

    """

    try:
        return _fetch_notes(org_id, limit)

    except NotesTableMissingError:
        raise

    except Exception as e:
        _handle_table_missing_error_logged(e)

        if _is_transient_net_error(e):
            log.warning("Falha transitória ao listar notas: %s", e)
            raise NotesTransientError(str(e)) from e

        log.error("Erro ao listar notas: %s", e)

        return []


def add_note(org_id: str, author_email: str, body: str) -> dict[str, Any]:
    """

    Adiciona nova anota???o (append-only).



    Args:

        org_id: UUID da organiza???o

        author_email: Email do autor

        body: Texto da anota???o (max 1000 chars)



    Returns:

        Registro inserido



    Raises:

        ValueError: Se anota???o vazia ou inv?lida

        NotesTableMissingError: Se a tabela rc_notes n?o existir no Supabase

        NotesAuthError: Se houver erro de permiss?o RLS

        NotesTransientError: Se houver falha transit??ria de rede ap??s retries

    """

    body = _normalize_body(body)

    author_email = _normalize_author_email_for_org(author_email, org_id)

    # Log de diagn??stico

    email_prefix: str = _email_prefix(author_email)

    log.info("notes.add", extra={"org_id": org_id, "author_email_prefix": email_prefix})

    payload: dict[str, str] = {"org_id": org_id, "author_email": author_email, "body": body}

    return _insert_note_with_retry(payload, org_id, email_prefix)


def list_notes_since(org_id: str, since_iso: str | None) -> list[dict[str, Any]]:
    """

    Retorna notas da org mais novas que 'since_iso' (ISO-8601).

    Se since_iso for None, retorna [] (porque o Hub jÃ¡ carrega o histÃ³rico completo em outro fluxo).



    Args:

        org_id: UUID da organizaÃ§Ã£o

        since_iso: Timestamp ISO-8601 para filtrar notas mais recentes



    Returns:

        Lista de notas mais recentes que since_iso, ordenadas crescente por created_at

    """

    if not since_iso:
        return []

    def _call() -> list[dict[str, Any]]:
        supa = get_supabase()

        # created_at > since_iso, ordenado crescente

        resp = exec_postgrest(
            supa.table(TABLE)
            .select(RC_NOTES_SELECT_FIELDS_LIST)
            .eq("org_id", org_id)
            .gt("created_at", since_iso)
            .order("created_at", desc=True)
            .limit(100)
        )

        rows: list[dict[str, Any]] = resp.data or []

        # Normalizar emails legados (prefixo â†’ email completo, com aliases)

        return _normalize_author_emails(rows, org_id)

    try:
        return _call()

    except Exception as e:
        log.debug("Erro ao buscar notas incrementais: %s", e)

        return []
