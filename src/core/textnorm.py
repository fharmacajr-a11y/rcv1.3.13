# -*- coding: utf-8 -*-
"""
Search text normalization helpers (accent/punctuation insensitive).
"""

from __future__ import annotations

import unicodedata as ud

__all__ = [
    "_strip_diacritics",
    "normalize_search",
    "join_and_normalize",
]


def _strip_diacritics(s: str | None) -> str:
    if s is None:
        return ""
    text = str(s)
    decomposed = ud.normalize("NFD", text)
    without_marks = "".join(ch for ch in decomposed if ud.category(ch) != "Mn")
    return ud.normalize("NFC", without_marks)


def normalize_search(value: object) -> str:
    """
    Normalize value for fuzzy comparisons:
    - remove diacritics with Unicode NFD decomposition
    - apply casefold (stronger than lower)
    - drop punctuation / separators / control characters
    """
    stripped = _strip_diacritics("" if value is None else str(value))
    folded = stripped.casefold()
    out_chars: list[str] = []
    for ch in folded:
        cat = ud.category(ch)
        if cat and cat[0] in {"P", "Z", "C", "S"}:
            continue
        out_chars.append(ch)
    return "".join(out_chars)


def join_and_normalize(*parts: object) -> str:
    """
    Join multiple parts separated by spaces and return normalized text.
    """
    combined = " ".join("" if part is None else str(part) for part in parts)
    return normalize_search(combined)
