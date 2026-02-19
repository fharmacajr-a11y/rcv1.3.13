# -*- coding: utf-8 -*-
"""Pure formatting helpers for HubScreen notes."""

from __future__ import annotations

from datetime import datetime, timezone

try:
    _LOCAL_TZ = datetime.now().astimezone().tzinfo or timezone.utc
except Exception:
    _LOCAL_TZ = timezone.utc


def _format_timestamp(ts_iso: str | None) -> str:
    """Convert Supabase ISO timestamp to local time string dd/mm/YYYY - HH:MM.

    BUG-006: Valida None, strings vazias e formatos inválidos.
    """
    try:
        # BUG-006: Validação explícita de None e string vazia
        if ts_iso is None or not isinstance(ts_iso, str) or not ts_iso.strip():
            return "?"

        value = ts_iso.replace("Z", "+00:00")
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt_local = dt.astimezone(_LOCAL_TZ)
        return dt_local.strftime("%d/%m/%Y - %H:%M")
    except (ValueError, AttributeError, TypeError):
        # Log específico para debug se necessário
        return "?"
    except Exception:
        return "?"


def _format_note_line(created_at: str, author_display: str, text: str) -> str:
    """Compose the standard note line representation."""
    ts = _format_timestamp(created_at)
    return f"[{ts}] {author_display}: {text}"
