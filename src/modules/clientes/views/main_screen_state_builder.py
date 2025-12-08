# -*- coding: utf-8 -*-
"""Builder utilitario para criar instancias de MainScreenState."""

from __future__ import annotations

from collections.abc import Collection, Sequence

from src.modules.clientes.viewmodel import ClienteRow
from src.modules.clientes.views.main_screen_helpers import normalize_order_label
from src.modules.clientes.views.main_screen_state import MainScreenState


def build_main_screen_state(
    *,
    clients: Sequence[ClienteRow],
    raw_order_label: str | None,
    raw_filter_label: str | None,
    raw_search_text: str | None,
    selected_ids: Collection[str],
    is_trash_screen: bool,
    is_online: bool = True,
) -> MainScreenState:
    """Normaliza valores vindos da UI e retorna um MainScreenState."""

    order_label = normalize_order_label(raw_order_label)
    filter_label = (raw_filter_label or "").strip()
    search_text = (raw_search_text or "").strip()

    return MainScreenState(
        clients=clients,
        order_label=order_label,
        filter_label=filter_label,
        search_text=search_text,
        selected_ids=list(selected_ids),
        is_online=is_online,
        is_trash_screen=is_trash_screen,
    )
