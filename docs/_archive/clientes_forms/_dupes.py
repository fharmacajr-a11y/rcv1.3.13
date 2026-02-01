# -*- coding: utf-8 -*-
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from typing import Any, Iterable, Mapping, Tuple


def _extract_conflict_attr(cliente: Any, attr: str) -> Any:
    if isinstance(cliente, dict):
        return cliente.get(attr)
    return getattr(cliente, attr, None)


def _format_conflict_line(cliente: Any) -> str:
    return (
        f"- ID {_extract_conflict_attr(cliente, 'id') or '?'} - "
        f"{_extract_conflict_attr(cliente, 'razao_social') or '-'} "
        f"(CNPJ: {_extract_conflict_attr(cliente, 'cnpj') or '-'})"
    )


def _normalized_conflicts(entries: Iterable[Any] | None) -> list[Any]:
    if entries is None:
        return []
    if isinstance(entries, list):
        return entries
    return list(entries)


def has_cnpj_conflict(info: Mapping[str, Any] | None) -> bool:
    return bool(info and info.get("cnpj_conflict"))


def has_razao_conflict(info: Mapping[str, Any] | None) -> bool:
    if not info:
        return False
    return bool(_normalized_conflicts(info.get("razao_conflicts")))


def build_cnpj_warning(info: Mapping[str, Any]) -> Tuple[str, str]:
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
    if isinstance(parent, tk.Misc):
        return {"parent": parent}
    return {}


def show_cnpj_warning_and_abort(parent: Any, info: Mapping[str, Any]) -> bool:
    title, message = build_cnpj_warning(info)
    messagebox.showwarning(title, message, **_parent_kwargs(parent))
    return False


def ask_razao_confirm(parent: Any, info: Mapping[str, Any]) -> bool:
    title, message = build_razao_confirm(info)
    return messagebox.askokcancel(title, message, **_parent_kwargs(parent))
