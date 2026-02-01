# -*- coding: utf-8 -*-

"""Factories/builders para construção de MainScreenState em testes.

Este módulo fornece funções helper para criar instâncias de MainScreenState
com defaults sensatos, reduzindo duplicação nos testes.

Fase MS-6: Criação de builders tipados para estados de testes.
"""

from __future__ import annotations

from collections.abc import Collection, Sequence

from src.modules.clientes.core.viewmodel import ClienteRow
from src.modules.clientes.views.main_screen_state import MainScreenState


def make_main_screen_state(
    *,
    clients: Sequence[ClienteRow] | None = None,
    order_label: str = "Razão Social (A→Z)",
    filter_label: str = "Todos",
    search_text: str = "",
    selected_ids: Collection[str] | None = None,
    is_online: bool = True,
    is_trash_screen: bool = False,
) -> MainScreenState:
    """Factory para criar MainScreenState com defaults sensatos.

    Args:
        clients: Lista de clientes (default: lista vazia)
        order_label: Label de ordenação (default: "Razão Social (A→Z)")
        filter_label: Label de filtro de status (default: "Todos")
        search_text: Texto de busca (default: "")
        selected_ids: IDs selecionados (default: set vazio)
        is_online: Se está online (default: True)
        is_trash_screen: Se está na tela de lixeira (default: False)

    Returns:
        Instância de MainScreenState configurada

    Examples:
        >>> # Estado vazio padrão
        >>> state = make_main_screen_state()
        >>> len(state.clients)
        0
        >>> state.order_label
        'Razão Social (A→Z)'

        >>> # Estado com clientes e seleção
        >>> from src.modules.clientes.core.viewmodel import ClienteRow
        >>> clients = [ClienteRow(...), ClienteRow(...)]
        >>> state = make_main_screen_state(
        ...     clients=clients,
        ...     selected_ids={"1", "2"},
        ...     is_online=False,
        ... )
        >>> len(state.selected_ids)
        2
        >>> state.is_online
        False
    """
    if clients is None:
        clients = []

    if selected_ids is None:
        selected_ids = set()

    return MainScreenState(
        clients=clients,
        order_label=order_label,
        filter_label=filter_label,
        search_text=search_text,
        selected_ids=selected_ids,
        is_online=is_online,
        is_trash_screen=is_trash_screen,
    )
