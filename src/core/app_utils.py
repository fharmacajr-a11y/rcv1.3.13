"""Utility helpers shared across the Gestor de Clientes application."""

from __future__ import annotations

import re

from src.core.string_utils import only_digits

# Windows reserves specific directory names; keep them uppercase for lookups.
RESERVED_WIN_NAMES: set[str] = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}
RESERVED_WIN_NAMES = {name.upper() for name in RESERVED_WIN_NAMES}

# Accept common separators when splitting folder metadata (hyphen, slash, underscore, pipe).
_META_SEPARATOR = re.compile(r"\s*[-_/|]\s*")


def fmt_data(iso_str: str | None) -> str:
    """[DEPRECATED] Formata data ISO para DD/MM/YYYY - HH:MM:SS.

    **DEPRECADO**: Use fmt_datetime_br de src.utils.formatters.
    Esta função é mantida apenas para compatibilidade com código legado.
    Delega para fmt_datetime_br que é mais robusta e aceita mais tipos.

    Args:
        iso_str: String ISO datetime ou None.

    Returns:
        String formatada no padrão brasileiro ou vazio se None/inválido.
    """
    from src.utils.formatters import fmt_datetime_br

    return fmt_datetime_br(iso_str)


# only_digits agora importado de src.core.string_utils


def slugify_name(value: str | None) -> str:
    """Create a filesystem-friendly slug limited to 60 ASCII characters."""
    if not value:
        return ""
    slug: str = re.sub(r"[^A-Za-z0-9_]+", "_", value.strip())
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug[:60]


def safe_base_from_fields(cnpj: str, numero: str, razao: str, pk: int) -> str:
    """
    Build a deterministic folder name from client metadata while avoiding Windows reserved names.
    Priority order:
      1. Valid 14-digit CNPJ
      2. Phone/Whatsapp number with at least 10 digits
      3. Slugified company name
      4. Fallback to the database identifier
    """
    cnpj_digits: str = only_digits(cnpj)
    if len(cnpj_digits) == 14:
        base: str = cnpj_digits
    else:
        numero_digits: str = only_digits(numero)
        if len(numero_digits) >= 10:
            base = numero_digits
        else:
            base = slugify_name(razao) or f"id_{pk}"

    if base.upper() in RESERVED_WIN_NAMES:
        base = f"id_{pk}_{base}"
    return base


def split_meta(meta: str) -> tuple[str, str]:
    """Split a folder suffix into (razao_social, contato) using common separators."""
    if not meta:
        return "", ""

    parts: list[str] = [segment.strip() for segment in _META_SEPARATOR.split(meta) if segment.strip()]
    razao: str = parts[0] if len(parts) >= 1 else ""
    contato: str = parts[1] if len(parts) >= 2 else ""
    return razao, contato


def parse_pasta(nome: str) -> dict[str, str]:
    """
    Infer client metadata from a folder name.
    Returns a dict with the keys: cnpj, numero, razao and pessoa.
    """
    base: str = (nome or "").strip()
    digits: str = only_digits(base)

    if len(digits) == 14:
        match = re.search(r"^\D*(\d{14})\D*(.*)$", base)
        suffix: str = (match.group(2) if match else "").strip()
        razao: str
        pessoa: str
        razao, pessoa = split_meta(suffix)
        return {"cnpj": digits, "numero": "", "razao": razao, "pessoa": pessoa}

    if 10 <= len(digits) <= 15:
        match = re.search(r"^\D*(\d{10,15})\D*(.*)$", base)
        suffix = (match.group(2) if match else "").strip()
        razao, pessoa = split_meta(suffix)
        return {"cnpj": "", "numero": digits, "razao": razao, "pessoa": pessoa}

    razao, pessoa = split_meta(base)
    return {"cnpj": "", "numero": "", "razao": razao, "pessoa": pessoa}


__all__ = [
    "fmt_data",
    "only_digits",
    "slugify_name",
    "safe_base_from_fields",
    "split_meta",
    "parse_pasta",
]
