# -*- coding: utf-8 -*-
"""Serviço headless para gerenciamento de nomes de autores.

CLEANAPP-HUB-LEGACY-01: Substitui lógica duplicada de src/modules/hub/authors.py

Este serviço consolida:
- Resolução de nomes de autores (cache, AUTHOR_NAMES, fetch remoto)
- Gerenciamento de cache com TTL
- Resolução de prefixos de email
- Debug/diagnóstico de resolução de nomes

Migrado de:
- src/modules/hub/authors.py (_author_display_name, _debug_resolve_author)
- Integrado com src/modules/hub/views/hub_authors_cache.py
"""

from __future__ import annotations

import ast
import functools
import json
import logging
import os
import time
from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from typing import Protocol
    from src.modules.hub.state import HubState

    class ScreenProtocol(Protocol):
        """Protocolo para screen com cache de autores.

        MF-39: Atualizado para usar state.author_cache em vez de _author_names_cache.
        MF-40: state como property para compatibilidade com HubScreen.
        """

        @property
        def state(self) -> HubState: ...

        def after(self, ms: int, func) -> Any: ...


logger = logging.getLogger(__name__)

# Constante para TTL do cache (em segundos)
CACHE_TTL_SECONDS = 60

# Mapa de e-mail -> nome curto preferido (sempre em minúsculas)
AUTHOR_NAMES = {
    "farmacajr@gmail.com": "Junior",
    "fharmaca2013@hotmail.com": "Elisabete",
}


def load_env_author_names() -> Dict[str, str]:
    """Carrega o mapa de nomes de autores do .env (RC_INITIALS_MAP).

    Função pública e robusta para carregar RC_INITIALS_MAP com tolerância
    a diferentes formatos (aspas duplas, aspas simples, aspas externas).

    Lê a variável de ambiente RC_INITIALS_MAP (JSON/dict Python) e retorna
    um dicionário com emails normalizados (lowercase) mapeados para nomes.

    Returns:
        Dict[str, str]: Mapa {email: nome} normalizado (emails em lowercase).
                        Retorna dict vazio em caso de erro ou JSON inválido.

    Examples:
        >>> # No .env: RC_INITIALS_MAP={"user@example.com":"John"}
        >>> load_env_author_names()
        {'user@example.com': 'John'}
    """
    try:
        rc_initials_map = os.getenv("RC_INITIALS_MAP", "").strip()

        if not rc_initials_map:
            return {}

        # Tolerância a aspas externas (alguns .env escapam com '...' ou "...")
        if (rc_initials_map.startswith("'") and rc_initials_map.endswith("'")) or (
            rc_initials_map.startswith('"') and rc_initials_map.endswith('"')
        ):
            rc_initials_map = rc_initials_map[1:-1]

        # Tentar json.loads primeiro (formato padrão)
        try:
            raw_map = json.loads(rc_initials_map)
        except (json.JSONDecodeError, ValueError) as exc:
            # Fallback: ast.literal_eval (suporta aspas simples no dict)
            logger.debug("[authors_service] json.loads falhou, tentando ast.literal_eval", exc_info=exc)
            try:
                raw_map = ast.literal_eval(rc_initials_map)
            except (SyntaxError, ValueError) as e:
                logger.debug(f"[authors_service] Falha ao parsear RC_INITIALS_MAP: {e}")
                return {}

        # Normalizar: emails lowercase, nomes stripped, ignorar vazios
        normalized = {}
        for email, name in raw_map.items():
            email_norm = str(email).strip().lower()
            name_norm = str(name).strip()
            if email_norm and name_norm:
                normalized[email_norm] = name_norm

        return normalized

    except Exception as exc:
        logger.debug(f"[authors_service] Erro ao carregar RC_INITIALS_MAP: {exc}")
        return {}


# Alias privado para compatibilidade com código existente
_load_env_author_names = load_env_author_names


# Cache TTL de 60s para nomes provisórios (fallback), usando tick por minuto
@functools.lru_cache(maxsize=1024)
def _author_display_name_ttl(key: str, _tick: int) -> str:  # noqa: ARG001 (tick usado para cache TTL)
    """Gera nome de fallback com cache baseado em tick de minuto.

    Args:
        key: Email normalizado (lowercase)
        _tick: Tick de tempo (minuto) para invalidação de cache

    Returns:
        Nome formatado a partir do prefixo do email
    """
    return key.split("@", 1)[0].replace(".", " ").title()


def get_author_display_name(
    screen: ScreenProtocol,
    email: str,
    start_async_fetch: bool = True,
) -> str:
    """Retorna nome do autor com prioridade otimizada e fetch on-demand.

    Estratégia de resolução (em ordem):
    1. Cache Supabase com TTL (screen.state.author_cache)
    2. Mapa local AUTHOR_NAMES
    3. Fetch assíncrono on-demand (se start_async_fetch=True)
    4. Placeholder formatado (fallback)

    Args:
        screen: Instância do screen com atributos de cache
        email: Email do autor a resolver
        start_async_fetch: Se True, inicia fetch assíncrono para emails desconhecidos

    Returns:
        Nome do autor (ou "?" se email vazio)
    """
    key = (email or "").strip().lower()
    if not key:
        return "?"

    # 0) Se vier só prefixo, resolver via mapa de prefixos
    if "@" not in key:
        resolved = (screen.state.email_prefix_map or {}).get(key)
        if resolved:
            key = resolved

    # Garante dict real
    author_cache = getattr(screen, "_author_names_cache", None)
    if author_cache is None:
        author_cache = {}
        setattr(screen, "_author_names_cache", author_cache)

    # 1) Cache Supabase com TTL (+ compat str)
    cached = author_cache.get(key)
    now = time.time()
    if isinstance(cached, tuple):
        name, expiry = cached
        if now < expiry:
            return name
        else:
            del author_cache[key]
    elif isinstance(cached, str):
        expiry = now + CACHE_TTL_SECONDS
        author_cache[key] = (cached, expiry)
        return cached

    # 2) Mapa do .env (RC_INITIALS_MAP) - PRIORIDADE MÁXIMA
    env_names = _load_env_author_names()
    if key in env_names:
        return env_names[key]

    # 3) Mapa local AUTHOR_NAMES (fallback)
    if key in AUTHOR_NAMES:
        return AUTHOR_NAMES[key]

    # 4) Fetch on-demand (apenas UMA thread por e-mail)
    if start_async_fetch and "@" in key:
        _start_author_fetch_async(screen, key, author_cache)

    # 5) Placeholder (último recurso) — com TTL de 60s
    return _author_display_name_ttl(key, int(time.time()) // 60)


def _start_author_fetch_async(screen: ScreenProtocol, email: str, author_cache: Dict[str, Any]) -> None:
    """Inicia fetch assíncrono de nome de autor (evita duplicação).

    Args:
        screen: Screen para callbacks e pending tracking
        email: Email normalizado (lowercase) a buscar
        author_cache: Cache de autores compartilhado
    """
    if not hasattr(screen.state, "pending_name_fetch"):
        # MF-19: Usar método público do HubScreen (que usa StateManager)
        screen.clear_pending_name_fetch()

    if email in screen.state.pending_name_fetch:
        return  # Já está buscando

    # MF-19: Usar método público do HubScreen (que usa StateManager)
    screen.add_pending_name_fetch(email)

    def _work():
        resolved = None
        try:
            from src.core.services.profiles_service import get_display_name_by_email

            resolved = get_display_name_by_email(email)
        except Exception as exc:
            logger.debug(f"Falha ao buscar nome para {email}: {exc}", exc_info=exc)
        finally:

            def _ui():
                try:
                    if resolved:
                        expiry = time.time() + CACHE_TTL_SECONDS
                        author_cache[email] = (resolved, expiry)
                        # Força re-render UMA vez (invalidar hash)
                        if hasattr(screen, "_last_render_hash"):
                            screen._last_render_hash = None
                        # Tentar re-renderizar notas se houver dados
                        if hasattr(screen, "render_notes"):
                            if screen.state.notes_last_data:
                                screen.render_notes(screen.state.notes_last_data)
                            elif screen.state.notes_last_snapshot:
                                screen.render_notes(screen.state.notes_last_snapshot)
                finally:
                    # MF-19: Usar método público do HubScreen (que usa StateManager)
                    screen.remove_pending_name_fetch(email)

            try:
                screen.after(0, _ui)
            except Exception as exc:
                logger.debug(f"Falha ao agendar atualização de autor: {exc}", exc_info=exc)

    import threading

    threading.Thread(target=_work, daemon=True).start()


def debug_resolve_author(screen: ScreenProtocol, email: str) -> Dict[str, Any]:
    """Resolve um email de autor e retorna informações de debug.

    Args:
        screen: Screen com cache de autores
        email: Email a resolver (pode ser prefixo ou email completo)

    Returns:
        Dict com campos:
        - input: Email original
        - normalized: Email normalizado (lowercase)
        - alias_applied: Se alias foi aplicado ao prefixo
        - resolved_email: Email final resolvido
        - name: Nome do autor resolvido
        - source: Origem do nome ("names_cache", "AUTHOR_NAMES", "fetch_by_email", "placeholder")
        - cache_hit: Se encontrou no cache
        - prefix_map_hit: Se usou _email_prefix_map
    """
    raw = email or ""
    key = raw.strip().lower()
    alias_applied = False
    resolved_email = key
    source = "placeholder"
    name = None

    prefix_map = screen.state.email_prefix_map or {}

    author_cache = getattr(screen, "_author_names_cache", None)
    if author_cache is None:
        author_cache = {}
        setattr(screen, "_author_names_cache", author_cache)

    # Aliases opcionais
    try:
        from src.core.services.profiles_service import EMAIL_PREFIX_ALIASES

        email_prefix_aliases = EMAIL_PREFIX_ALIASES  # noqa: N806
    except Exception as exc:
        logger.debug("[authors_service] Falha ao carregar EMAIL_PREFIX_ALIASES, usando dict vazio", exc_info=exc)
        email_prefix_aliases = {}

    # Se veio só o prefixo, tenta corrigir alias e resolver no mapa de prefixos
    if key and "@" not in key:
        alias = email_prefix_aliases.get(key, key)
        alias_applied = alias != key
        resolved_email = prefix_map.get(alias) or prefix_map.get(key) or alias
    else:
        resolved_email = key

    # 1) Cache Supabase (por org) com TTL (+ compat str)
    cached = author_cache.get(resolved_email)
    now = time.time()
    if isinstance(cached, tuple):
        dn, expiry = cached
        if now < expiry:
            name = dn
            source = "names_cache"
        else:
            del author_cache[resolved_email]
    elif isinstance(cached, str):
        expiry = now + CACHE_TTL_SECONDS
        author_cache[resolved_email] = (cached, expiry)
        name = cached
        source = "names_cache"

    # 2) Mapa do .env (RC_INITIALS_MAP)
    env_names = _load_env_author_names()
    if name is None and resolved_email in env_names:
        name = env_names[resolved_email]
        source = "RC_INITIALS_MAP"

    # 3) Mapa local AUTHOR_NAMES (fallback)
    if name is None and resolved_email in AUTHOR_NAMES:
        name = AUTHOR_NAMES[resolved_email]
        source = "AUTHOR_NAMES"

    # 4) Fetch direto por e-mail (SÍNCRONO para debug)
    fetched = None
    if name is None and "@" in resolved_email:
        try:
            from src.core.services.profiles_service import get_display_name_by_email

            fetched = get_display_name_by_email(resolved_email)
            if fetched:
                name = fetched
                source = "fetch_by_email"
        except Exception as e:
            logger.debug(f"Erro ao buscar nome para debug: {e}", exc_info=e)

    # 5) Fallback: prefixo formatado
    if name is None:
        name = resolved_email.split("@", 1)[0].replace(".", " ").title()

    return {
        "input": raw,
        "normalized": key,
        "alias_applied": alias_applied,
        "resolved_email": resolved_email,
        "name": name,
        "source": source,
        "cache_hit": resolved_email in author_cache,
        "prefix_map_hit": (key in prefix_map) or (resolved_email in prefix_map.values()),
    }
