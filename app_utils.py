"""Utility helpers shared across the Gestor de Clientes application."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Tuple
import re

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
    """Format an ISO datetime string into 'DD/MM/YYYY - HH:MM:SS'."""
    if not iso_str:
        return ""

    cleaned = iso_str.strip()
    if not cleaned:
        return ""

    normalized = cleaned.replace("Z", "+00:00")
    try:
        dt_obj = datetime.fromisoformat(normalized)
        if dt_obj.tzinfo is None:
            dt_obj = dt_obj.replace(tzinfo=timezone.utc)
        return dt_obj.astimezone().strftime("%d/%m/%Y - %H:%M:%S")
    except Exception:
        return cleaned


def only_digits(value: str | None) -> str:
    """Return only the numeric characters from the provided string."""
    return re.sub(r"\D", "", value or "")


def slugify_name(value: str | None) -> str:
    """Create a filesystem-friendly slug limited to 60 ASCII characters."""
    if not value:
        return ""
    slug = re.sub(r"[^A-Za-z0-9_]+", "_", value.strip())
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
    cnpj_digits = only_digits(cnpj)
    if len(cnpj_digits) == 14:
        base = cnpj_digits
    else:
        numero_digits = only_digits(numero)
        if len(numero_digits) >= 10:
            base = numero_digits
        else:
            base = slugify_name(razao) or f"id_{pk}"

    if base.upper() in RESERVED_WIN_NAMES:
        base = f"id_{pk}_{base}"
    return base


def split_meta(meta: str) -> Tuple[str, str]:
    """Split a folder suffix into (razao_social, contato) using common separators."""
    if not meta:
        return "", ""

    parts = [segment.strip() for segment in _META_SEPARATOR.split(meta) if segment.strip()]
    razao = parts[0] if len(parts) >= 1 else ""
    contato = parts[1] if len(parts) >= 2 else ""
    return razao, contato


def parse_pasta(nome: str) -> Dict[str, str]:
    """
    Infer client metadata from a folder name.
    Returns a dict with the keys: cnpj, numero, razao and pessoa.
    """
    base = (nome or "").strip()
    digits = only_digits(base)

    if len(digits) == 14:
        match = re.search(r"^\D*(\d{14})\D*(.*)$", base)
        suffix = (match.group(2) if match else "").strip()
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
