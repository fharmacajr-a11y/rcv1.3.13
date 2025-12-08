# -*- coding: utf-8 -*-
"""
Utilities to build Supabase Storage object keys using a safe ASCII subset.
"""

from __future__ import annotations

import hashlib
import re
from typing import Final

from src.core.text_normalization import normalize_ascii, strip_diacritics as _strip_diacritics

_ALLOWED_RE: Final[re.Pattern[str]] = re.compile(r"^(\w|/|!|-|\.|\*|'|\(|\)| |&|\$|@|=|;|:|\+|,|\?)*$")

__all__ = [
    "storage_slug_part",
    "storage_slug_filename",
    "make_storage_key",
]


def _ascii_only(value: str | None) -> str:
    """
    Converts a value to string, strips diacritics, and encodes as ASCII.

    Wrapper mantido para compatibilidade interna. Delega para normalize_ascii do core.
    """
    return normalize_ascii(value)


def storage_slug_part(part: str | None) -> str:
    """
    Sanitize a single path segment to the ASCII subset accepted by Supabase storage.
    """
    raw = "" if part is None else str(part)
    raw = _ascii_only(_strip_diacritics(raw))
    raw = raw.replace("%", "")
    raw = re.sub(r"\s+", " ", raw)
    return raw.strip(" /\\")


def storage_slug_filename(filename: str | None) -> str:
    """
    Sanitize a file name, preserving common punctuation while stripping diacritics.
    """
    if not filename:
        return "arquivo"
    name = storage_slug_part(filename)
    return name or "arquivo"


def make_storage_key(*parts: str | None, filename: str | None) -> str:
    safe_parts: list[str] = []
    for part in parts:
        cleaned = storage_slug_part(part)
        if cleaned:
            safe_parts.append(cleaned)

    fname = storage_slug_filename(filename)
    key = "/".join(safe_parts + [fname]).replace("\\", "/")
    key = re.sub(r"/{2,}", "/", key).strip("/")

    if not _ALLOWED_RE.match(key):
        base, dot, ext = fname.rpartition(".")
        digest = hashlib.sha256(fname.encode("utf-8")).hexdigest()[:8]
        fname_fallback = (base or "arquivo") + "-" + digest + (("." + ext) if dot else "")
        key = "/".join(safe_parts + [fname_fallback]).replace("\\", "/")
        key = re.sub(r"/{2,}", "/", key).strip("/")

    return key
