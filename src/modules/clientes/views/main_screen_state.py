# -*- coding: utf-8 -*-

"""Main screen state definition.

Este módulo contém a definição do estado da tela principal de clientes,
extraído do controller para facilitar reutilização e composição.

Fase MS-6: Extração de MainScreenState para módulo dedicado.
Fase MS-8: Adição de Protocols para interfaces de leitura.
"""

from __future__ import annotations

from collections.abc import Collection, Sequence
from dataclasses import dataclass
from typing import Protocol

from src.modules.clientes.viewmodel import ClienteRow


# ============================================================================
# PROTOCOLS (INTERFACES)
# ============================================================================


class MainScreenStateLike(Protocol):
    """Interface de leitura para o estado da Main Screen.

    Qualquer objeto com esses atributos é considerado um 'estado' válido.
    Permite structural subtyping e facilita testes com mocks.

    Attributes:
        clients: Lista completa de clientes (antes de filtros)
        order_label: Label de ordenação atual
        filter_label: Label de filtro de status atual
        search_text: Texto de busca atual
        selected_ids: IDs dos clientes selecionados
        is_online: Se está conectado ao Supabase
        is_trash_screen: Se está na tela de lixeira
    """

    clients: Sequence[ClienteRow]
    order_label: str
    filter_label: str
    search_text: str
    selected_ids: Collection[str]
    is_online: bool
    is_trash_screen: bool


# ============================================================================
# CONCRETE IMPLEMENTATIONS
# ============================================================================


@dataclass
class MainScreenState:
    """Estado atual da tela principal de clientes.

    Attributes:
        clients: Lista completa de clientes (antes de filtros)
        order_label: Label de ordenação atual (ex.: "Razão Social (A→Z)")
        filter_label: Label de filtro de status atual (ex.: "Ativo", "Todos")
        search_text: Texto de busca atual
        selected_ids: IDs dos clientes selecionados (aceita list, tuple, set)
        is_online: Se está conectado ao Supabase
        is_trash_screen: Se está na tela de lixeira
    """

    clients: Sequence[ClienteRow]
    order_label: str
    filter_label: str
    search_text: str
    selected_ids: Collection[str]
    is_online: bool = True
    is_trash_screen: bool = False
