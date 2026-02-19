# -*- coding: utf-8 -*-
"""Utilitários puros para HubScreen (funções sem estado)."""

from __future__ import annotations

import colorsys
import hashlib
import json
import logging
from dataclasses import is_dataclass
from typing import Any, Dict

logger = logging.getLogger(__name__)


def _hsl_to_hex(h: float, s: float, lightness: float) -> str:
    """Converte HSL para HEX. h: 0..360, s/l: 0..1."""
    r, g, b = colorsys.hls_to_rgb(h / 360.0, lightness, s)
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


def _hash_dict(d: dict) -> str:
    """Calcula hash estável de um dicionário para comparação."""
    try:
        payload = json.dumps(d or {}, sort_keys=True, ensure_ascii=False)
    except Exception:
        payload = str(sorted((d or {}).items()))
    return hashlib.sha256(payload.encode("utf-8", errors="ignore")).hexdigest()


def _normalize_note(n: Any) -> Dict[str, Any]:
    """
    Converte diferentes formatos de nota para dict seguro.

    Retorna SEMPRE as chaves:
      id, created_at, author_email, author_name, body,
      is_pinned, is_done, formatted_line, tag_name.

    Aceita:
      - dict
      - tuple/list (formatos antigos)
      - dataclass/objeto com atributos (ex.: NoteItemView)
    """
    # 1) dict (mais comum)
    if isinstance(n, dict):
        return {
            "id": n.get("id") or "",
            "created_at": n.get("created_at") or n.get("ts") or n.get("timestamp") or "",
            "author_email": n.get("author_email") or n.get("author") or n.get("email") or "",
            "author_name": n.get("author_name") or n.get("author_display_name") or n.get("name") or "",
            "body": n.get("body") or n.get("text") or n.get("message") or "",
            "is_pinned": bool(n.get("is_pinned", False)),
            "is_done": bool(n.get("is_done", False)),
            "formatted_line": n.get("formatted_line") or "",
            "tag_name": n.get("tag_name") or "",
        }

    # 2) tuple/list (formatos posicionais antigos)
    if isinstance(n, (tuple, list)):
        note_id = ts = author = body = ""
        length = len(n)
        if length >= 4:
            note_id, ts, author, body = n[0], n[1], n[2], n[3]
        elif length >= 3:
            ts, author, body = n[0], n[1], n[2]
        elif length == 2:
            author, body = n[0], n[1]
        elif length == 1:
            body = n[0]

        return {
            "id": str(note_id or ""),
            "created_at": str(ts or ""),
            "author_email": str(author or ""),
            "author_name": "",
            "body": str(body or ""),
            "is_pinned": False,
            "is_done": False,
            "formatted_line": "",
            "tag_name": "",
        }

    # 3) dataclass/objeto com atributos (ex.: NoteItemView)
    try:
        is_dc = is_dataclass(n)
    except Exception:
        is_dc = False

    if is_dc or any(hasattr(n, attr) for attr in ("body", "created_at", "author_email", "author_name", "id")):
        try:
            note_id = getattr(n, "id", "") or ""
            created_at = getattr(n, "created_at", None) or getattr(n, "ts", None) or getattr(n, "timestamp", None) or ""
            author_email = (
                getattr(n, "author_email", None) or getattr(n, "author", None) or getattr(n, "email", None) or ""
            )
            author_name = (
                getattr(n, "author_name", None)
                or getattr(n, "author_display_name", None)
                or getattr(n, "name", None)
                or ""
            )
            body = getattr(n, "body", None) or getattr(n, "text", None) or getattr(n, "message", None) or ""

            return {
                "id": note_id,
                "created_at": str(created_at or ""),
                "author_email": str(author_email or ""),
                "author_name": str(author_name or ""),
                "body": str(body or ""),
                "is_pinned": bool(getattr(n, "is_pinned", False)),
                "is_done": bool(getattr(n, "is_done", False)),
                "formatted_line": str(getattr(n, "formatted_line", "") or ""),
                "tag_name": str(getattr(n, "tag_name", "") or ""),
            }
        except Exception:
            logger.debug("Erro ao extrair campos do dataclass NoteItemView", exc_info=True)
            pass

    # 4) fallback final (nunca quebrar)
    return {
        "id": "",
        "created_at": "",
        "author_email": "",
        "author_name": "",
        "body": str(n),
        "is_pinned": False,
        "is_done": False,
        "formatted_line": "",
        "tag_name": "",
    }
