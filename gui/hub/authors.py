# -*- coding: utf-8 -*-
"""Helpers de autores para telas do hub."""

from __future__ import annotations

import threading

# Mapa de e-mail -> nome curto preferido (sempre em minÃºsculas)
AUTHOR_NAMES = {
    "farmacajr@gmail.com": "Junior",
    # "maria@empresa.com": "Maria",
    # "ana@empresa.com": "Ana",
}


def _author_display_name(screen, email: str) -> str:
    """
    Retorna nome do autor com prioridade otimizada e fetch on-demand.
    """
    key = (email or "").strip().lower()
    if not key:
        return "?"

    # 0) se vier sÃ³ prefixo, resolver via mapa de prefixos (se vocÃª jÃ¡ tem)
    if "@" not in key:
        resolved = (getattr(screen, "_email_prefix_map", {}) or {}).get(key)
        if resolved:
            key = resolved

    # 1) cache do Supabase
    dn = (getattr(screen, "_author_names_cache", {}) or {}).get(key)
    if dn:
        return dn

    # 2) mapa local AUTHOR_NAMES
    if "AUTHOR_NAMES" in globals() and key in AUTHOR_NAMES:
        return AUTHOR_NAMES[key]

    # 3) fetch on-demand (apenas UMA thread por e-mail)
    if not hasattr(screen, "_pending_name_fetch"):
        screen._pending_name_fetch = set()
    if "@" in key and key not in screen._pending_name_fetch:
        screen._pending_name_fetch.add(key)

        def _work():
            resolved = None
            try:
                from core.services.profiles_service import get_display_name_by_email

                resolved = get_display_name_by_email(key)
            finally:

                def _ui():
                    try:
                        if resolved:
                            (screen._author_names_cache or {}).update({key: resolved})
                            # forÃ§a re-render UMA vez
                            screen._last_render_hash = None
                            if getattr(screen, "_notes_last_data", None):
                                screen.render_notes(screen._notes_last_data)
                            elif getattr(screen, "_notes_last_snapshot", None):
                                screen.render_notes(screen._notes_last_snapshot)
                    finally:
                        try:
                            screen._pending_name_fetch.remove(key)
                        except KeyError:
                            pass

                try:
                    screen.after(0, _ui)
                except Exception:
                    pass

        threading.Thread(target=_work, daemon=True).start()

    # 4) placeholder (Ãºltimo recurso)
    return key.split("@", 1)[0].replace(".", " ").title()


def _debug_resolve_author(screen, email: str) -> dict:
    """
    Resolve um email de autor e retorna informaÃ§Ãµes de debug sobre o processo.
    """
    raw = email or ""
    key = raw.strip().lower()
    alias_applied = False
    resolved_email = key
    source = "placeholder"
    name = None

    prefix_map = getattr(screen, "_email_prefix_map", {}) or {}
    author_cache = getattr(screen, "_author_names_cache", {}) or {}

    # aliases opcionais
    try:
        from core.services.profiles_service import EMAIL_PREFIX_ALIASES
    except Exception:
        EMAIL_PREFIX_ALIASES = {}

    # Se veio sÃ³ o prefixo, tenta corrigir alias e resolver no mapa de prefixos
    if key and "@" not in key:
        alias = EMAIL_PREFIX_ALIASES.get(key, key)
        alias_applied = alias != key
        resolved_email = prefix_map.get(alias) or prefix_map.get(key) or alias
    else:
        resolved_email = key

    # 1) cache Supabase (por org)
    dn = author_cache.get(resolved_email)
    if dn:
        name = dn
        source = "names_cache"

    # 2) mapa local AUTHOR_NAMES
    if name is None and "AUTHOR_NAMES" in globals():
        dn = (AUTHOR_NAMES or {}).get(resolved_email)
        if dn:
            name = dn
            source = "AUTHOR_NAMES"

    # 3) fetch direto por e-mail
    fetched = None
    if name is None and "@" in resolved_email:
        try:
            from core.services.profiles_service import get_display_name_by_email

            fetched = get_display_name_by_email(resolved_email)
            if fetched:
                name = fetched
                source = "fetch_by_email"
        except Exception as e:
            fetched = f"ERR:{e!r}"

    # 4) fallback: prefixo formatado
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
        "prefix_map_hit": (key in prefix_map)
        or (resolved_email in prefix_map.values()),
    }

