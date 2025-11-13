# -*- coding: utf-8 -*-
"""Utilitários puros para HubScreen (funções sem estado)."""

from __future__ import annotations

import colorsys
import hashlib
import json
from typing import Any, Dict


def _hsl_to_hex(h: float, s: float, lightness: float) -> str:
    """Converte HSL para HEX. h: 0..360, s/l: 0..1."""
    r, g, b = colorsys.hls_to_rgb(h / 360.0, lightness, s)
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


def _hash_dict(d: dict) -> str:
    """Calcula hash MD5 de um dicionário para comparação."""
    try:
        payload = json.dumps(d or {}, sort_keys=True, ensure_ascii=False)
    except Exception:
        payload = str(sorted((d or {}).items()))
    return hashlib.md5(payload.encode("utf-8", errors="ignore")).hexdigest()


def _normalize_note(n: Any) -> Dict[str, str]:
    """
    Converte diferentes formatos de nota para dict:
    {'id': str, 'created_at': str, 'author_email': str, 'body': str}.
    Aceita: dict, tuple/list (nas formas mais comuns).
    Nunca quebra: sempre devolve um dict seguro.
    """
    if isinstance(n, dict):
        return {
            "id": n.get("id") or "",
            "created_at": n.get("created_at") or n.get("ts") or n.get("timestamp") or "",
            "author_email": n.get("author_email") or n.get("author") or n.get("email") or "",
            "body": n.get("body") or n.get("text") or n.get("message") or "",
        }

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
            "body": str(body or ""),
        }

    return {"id": "", "created_at": "", "author_email": "", "body": str(n)}
