from __future__ import annotations

import unicodedata as _ud


def _strip_diacritics(s: str) -> str:
    s = _ud.normalize("NFD", s)
    s = "".join(ch for ch in s if _ud.category(ch) != "Mn")
    return _ud.normalize("NFC", s)


def normalize_cnpj(raw: object) -> str:
    """Normaliza CNPJ (numérico ou alfanumérico) para comparação/índice.

    - Remove máscara, pontuação e diacríticos
    - Mantém apenas caracteres A–Z e 0–9
    - Converte para uppercase
    """
    s = "" if raw is None else str(raw)
    s = _strip_diacritics(s).upper()
    out: list[str] = []
    for ch in s:
        if "A" <= ch <= "Z" or "0" <= ch <= "9":
            out.append(ch)
    return "".join(out)
