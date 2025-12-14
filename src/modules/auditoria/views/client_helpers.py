"""Funções utilitárias relacionadas a clientes na tela de Auditoria."""

from __future__ import annotations

from helpers.formatters import format_cnpj


def cliente_display_id_first(cliente_id, razao, cnpj) -> str:
    """Mostra: ID 123 — RAZÃO — 00.000.000/0001-00."""
    parts: list[str] = []
    if cliente_id not in (None, "", 0):
        parts.append(f"ID {cliente_id}")
    if razao:
        parts.append(str(razao).strip())
    c = format_cnpj(cnpj or "")
    if c:
        parts.append(c)
    return " — ".join(parts)


def cliente_razao_from_row(row: dict | None) -> str:
    """Extrai a razão social/nome mais representativo do registro do cliente."""
    if not isinstance(row, dict):
        return ""
    return (
        row.get("display_name")
        or row.get("razao_social")
        or row.get("Razao Social")
        or row.get("legal_name")
        or row.get("name")
        or ""
    ).strip()


def cliente_cnpj_from_row(row: dict | None) -> str:
    """Extrai o CNPJ (ou tax_id) cru do registro do cliente."""
    if not isinstance(row, dict):
        return ""
    return (row.get("cnpj") or row.get("tax_id") or "").strip()
