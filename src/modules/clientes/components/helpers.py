"""Helpers de status da tela principal de Clientes.

Extraidos de src.ui.main_screen para reutilizacao e testes.
"""

from __future__ import annotations

import json
import os
import re
import tkinter as tk
from typing import Callable

DEFAULT_STATUS_GROUPS: list[tuple[str, list[str]]] = [
    (
        "Status gerais",
        [
            "Novo cliente",
            "Sem resposta",
            "Aguardando documento",
            "Aguardando pagamento",
            "Em cadastro",
            "Finalizado",
            "Follow-up hoje",
            "Follow-up amanhã",
        ],
    ),
    (
        "SIFAP",
        [
            "Análise da Caixa",
            "Análise do Ministério",
            "Cadastro pendente",
        ],
    ),
]
DEFAULT_STATUS_CHOICES = [label for _, values in DEFAULT_STATUS_GROUPS for label in values]


def _load_status_choices() -> list[str]:
    raw = (os.getenv("RC_STATUS_CHOICES") or "").strip()
    if not raw:
        return list(DEFAULT_STATUS_CHOICES)
    try:
        if raw.startswith("["):
            choices = json.loads(raw)
        else:
            choices = [s.strip() for s in raw.split(",") if s.strip()]
        return [str(s) for s in choices if s]
    except Exception:
        return list(DEFAULT_STATUS_CHOICES)


def _load_status_groups() -> list[tuple[str, list[str]]]:
    """Load grouped statuses from RC_STATUS_GROUPS or fall back to the defaults."""
    raw = (os.getenv("RC_STATUS_GROUPS") or "").strip()
    if raw:
        try:
            data = json.loads(raw)
            if isinstance(data, dict) and data:
                groups: list[tuple[str, list[str]]] = []
                for key, values in data.items():
                    if not values:
                        continue
                    if not isinstance(values, (list, tuple)):
                        continue
                    items = [str(v).strip() for v in values if str(v).strip()]
                    if items:
                        groups.append((str(key), items))
                if groups:
                    return groups
        except Exception:
            pass
    return list(DEFAULT_STATUS_GROUPS)


def _build_status_menu(menu: tk.Menu, on_pick: Callable[[str], None]) -> None:
    """Rebuild the status menu adding group headers, separators, and clear option."""
    menu.delete(0, "end")

    groups = _load_status_groups()
    for gi, (name, items) in enumerate(groups):
        if gi > 0:
            menu.add_separator()
        menu.add_command(label=f"-- {name} --", state="disabled")
        for label in items:
            menu.add_command(label=label, command=lambda l=label: on_pick(l))  # noqa: E741

    menu.add_separator()
    menu.add_command(label="Limpar", command=lambda: on_pick(""))


STATUS_GROUPS = _load_status_groups()
STATUS_CHOICES = [label for _, values in STATUS_GROUPS for label in values]
STATUS_PREFIX_RE = re.compile(r"^\s*\[(?P<st>[^\]]+)\]\s*")

__all__ = [
    "_load_status_choices",
    "_load_status_groups",
    "_build_status_menu",
    "STATUS_CHOICES",
    "STATUS_PREFIX_RE",
]
