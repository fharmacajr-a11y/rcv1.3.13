# -*- coding: utf-8 -*-
"""Helpers para detecção e tratamento de duplicidades (CNPJ/Razão Social).

Este módulo foi extraído do client_form para reutilização e modularização.
Contém lógica de validação de conflitos de CNPJ e Razão Social.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from typing import Any, Iterable, Mapping, Tuple


def _extract_conflict_attr(cliente: Any, attr: str) -> Any:
    """Extrai atributo de cliente (suporta dict e objeto)."""
    if isinstance(cliente, dict):
        return cliente.get(attr)
    return getattr(cliente, attr, None)


def _format_conflict_line(cliente: Any) -> str:
    """Formata linha de conflito para exibição."""
    return (
        f"- ID {_extract_conflict_attr(cliente, 'id') or '?'} - "
        f"{_extract_conflict_attr(cliente, 'razao_social') or '-'} "
        f"(CNPJ: {_extract_conflict_attr(cliente, 'cnpj') or '-'})"
    )


def _normalized_conflicts(entries: Iterable[Any] | None) -> list[Any]:
    """Normaliza lista de conflitos (aceita None, list, ou iterable)."""
    if entries is None:
        return []
    if isinstance(entries, list):
        return entries
    return list(entries)


def has_cnpj_conflict(info: Mapping[str, Any] | None) -> bool:
    """Verifica se há conflito de CNPJ nos dados de duplicidade.

    Args:
        info: Dicionário retornado pelo service com informações de duplicidade

    Returns:
        True se há conflito de CNPJ
    """
    return bool(info and info.get("cnpj_conflict"))


def has_razao_conflict(info: Mapping[str, Any] | None) -> bool:
    """Verifica se há conflito de Razão Social nos dados de duplicidade.

    Args:
        info: Dicionário retornado pelo service com informações de duplicidade

    Returns:
        True se há conflito de Razão Social
    """
    if not info:
        return False
    return bool(_normalized_conflicts(info.get("razao_conflicts")))


def build_cnpj_warning(info: Mapping[str, Any]) -> Tuple[str, str]:
    """Constrói título e mensagem de warning para conflito de CNPJ.

    Args:
        info: Dicionário com informações de duplicidade

    Returns:
        Tupla (título, mensagem) para messagebox
    """
    conflict = info.get("cnpj_conflict")
    if not conflict:
        return ("CNPJ duplicado", "")
    message = (
        "CNPJ já cadastrado para o cliente ID "
        f"{_extract_conflict_attr(conflict, 'id') or '?'} - "
        f"{_extract_conflict_attr(conflict, 'razao_social') or '-'}\n"
        f"CNPJ registrado: {_extract_conflict_attr(conflict, 'cnpj') or '-'}"
    )
    return ("CNPJ duplicado", message)


def build_razao_confirm(info: Mapping[str, Any]) -> Tuple[str, str]:
    """Constrói título e mensagem de confirmação para conflito de Razão Social.

    Args:
        info: Dicionário com informações de duplicidade

    Returns:
        Tupla (título, mensagem) para messagebox
    """
    conflicts = _normalized_conflicts(info.get("razao_conflicts"))
    lines: list[str] = []
    for idx, cliente in enumerate(conflicts, start=1):
        if idx > 3:
            break
        lines.append(_format_conflict_line(cliente))
    remaining = max(0, len(conflicts) - len(lines))
    if remaining:
        lines.append(f"- ... e mais {remaining} registro(s)")
    header = "Existe outro cliente com a mesma Razão Social mas CNPJ diferente. Deseja continuar?\n\n"
    message = header + "\n".join(lines)
    return ("Razão Social repetida", message)


def _parent_kwargs(parent: Any) -> dict:
    """Retorna kwargs para messagebox (parent se for widget Tkinter)."""
    if isinstance(parent, tk.Misc):
        return {"parent": parent}
    return {}


def show_cnpj_warning_and_abort(parent: Any, info: Mapping[str, Any]) -> bool:
    """Mostra warning de CNPJ duplicado e retorna False (abortando operação).

    Args:
        parent: Widget pai para messagebox
        info: Dicionário com informações de duplicidade

    Returns:
        False (sempre aborta por ser erro)
    """
    title, message = build_cnpj_warning(info)
    messagebox.showwarning(title, message, **_parent_kwargs(parent))
    return False


def ask_razao_confirm(parent: Any, info: Mapping[str, Any]) -> bool:
    """Pergunta ao usuário se deseja continuar apesar de Razão Social duplicada.

    Args:
        parent: Widget pai para messagebox
        info: Dicionário com informações de duplicidade

    Returns:
        True se usuário confirmou, False caso contrário
    """
    title, message = build_razao_confirm(info)
    return messagebox.askokcancel(title, message, **_parent_kwargs(parent))


__all__ = [
    "ask_razao_confirm",
    "build_cnpj_warning",
    "build_razao_confirm",
    "has_cnpj_conflict",
    "has_razao_conflict",
    "show_cnpj_warning_and_abort",
]
