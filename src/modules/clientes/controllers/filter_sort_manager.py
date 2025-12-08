# -*- coding: utf-8 -*-
"""Filter/Sort Manager headless para gerenciamento de filtros e ordenação.

FASE MS-16: Extração da lógica de filtros/ordenação/pesquisa da God Class MainScreenFrame.

Este módulo concentra a lógica de "como aplicar filtros/ordenação/pesquisa em uma lista"
sem dependências de Tkinter/UI.

Responsabilidades:
- Receber parâmetros brutos (strings de filtro/ordem/busca)
- Construir MainScreenState via build_main_screen_state
- Chamar compute_main_screen_state para aplicar filtros
- Retornar resultado pronto para renderização

NÃO faz:
- Manipular widgets Tkinter (Combobox, Entry, etc)
- Renderizar Treeview
- Acessar diretamente ViewModel ou Service
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Collection, Sequence

from src.modules.clientes.viewmodel import ClienteRow
from src.modules.clientes.views.main_screen_controller import (
    MainScreenComputedLike,
    MainScreenState,
    compute_main_screen_state,
)
from src.modules.clientes.views.main_screen_state_builder import build_main_screen_state


# ============================================================================
# DATA STRUCTURES
# ============================================================================


@dataclass(frozen=True)
class FilterSortInput:
    """Entrada para o FilterSortManager.

    Agrupa todos os parâmetros necessários para computar estado filtrado/ordenado.

    Attributes:
        clients: Lista completa de clientes (antes de filtros)
        raw_order_label: Label de ordenação (ex: "Razão Social (A→Z)")
        raw_filter_label: Label de filtro de status (ex: "Ativo", "Todos")
        raw_search_text: Texto de busca (aplicado em múltiplos campos)
        selected_ids: IDs atualmente selecionados na UI
        is_trash_screen: Se True, está na tela de lixeira (muda comportamento de batch)
    """

    clients: Sequence[ClienteRow]
    raw_order_label: str | None
    raw_filter_label: str | None
    raw_search_text: str | None
    selected_ids: Collection[str]
    is_trash_screen: bool


@dataclass(frozen=True)
class FilterSortResult:
    """Resultado do FilterSortManager.

    Contém estado normalizado e resultado computado, pronto para aplicação na UI.

    Attributes:
        state: Estado normalizado construído via build_main_screen_state
        computed: Resultado computado com lista filtrada/ordenada e flags de batch
    """

    state: MainScreenState
    computed: MainScreenComputedLike


# ============================================================================
# FILTER/SORT MANAGER
# ============================================================================


class FilterSortManager:
    """Gerenciador headless de filtros, ordenação e pesquisa.

    Responsável por:
    - Normalizar parâmetros de filtro/ordem/busca
    - Aplicar filtros e ordenação via controller
    - Retornar resultado pronto para renderização

    Não gerencia:
    - Widgets Tkinter (Combobox, Entry)
    - Treeview ou outros componentes de UI
    - Carregamento de dados do backend

    Examples:
        >>> manager = FilterSortManager()
        >>> inp = FilterSortInput(
        ...     clients=[...],
        ...     raw_order_label="Razão Social (A→Z)",
        ...     raw_filter_label="Todos",
        ...     raw_search_text="empresa",
        ...     selected_ids=set(),
        ...     is_trash_screen=False
        ... )
        >>> result = manager.compute(inp)
        >>> # result.computed.visible_clients contém lista filtrada/ordenada
        >>> # result.computed.can_batch_delete indica se pode deletar em lote
    """

    def __init__(self) -> None:
        """Inicializa o FilterSortManager.

        Este manager é stateless - todo o estado vem via FilterSortInput.
        """
        pass

    def compute(self, inp: FilterSortInput) -> FilterSortResult:
        """Computa estado filtrado/ordenado a partir dos parâmetros de entrada.

        Este é o método principal do manager. Ele:
        1. Constrói MainScreenState normalizado via build_main_screen_state
        2. Aplica filtros/ordenação via compute_main_screen_state
        3. Retorna resultado pronto para UI

        Args:
            inp: Parâmetros de entrada (clientes, filtros, ordem, busca)

        Returns:
            FilterSortResult com estado normalizado e resultado computado

        Examples:
            >>> manager = FilterSortManager()
            >>> clients = [
            ...     ClienteRow(id="1", razao_social="Empresa A", status="Ativo", ...),
            ...     ClienteRow(id="2", razao_social="Empresa B", status="Inativo", ...),
            ... ]
            >>> inp = FilterSortInput(
            ...     clients=clients,
            ...     raw_order_label="Razão Social (A→Z)",
            ...     raw_filter_label="Ativo",
            ...     raw_search_text="",
            ...     selected_ids=set(),
            ...     is_trash_screen=False
            ... )
            >>> result = manager.compute(inp)
            >>> len(result.computed.visible_clients)  # Apenas "Empresa A"
            1
        """
        # 1. Construir estado normalizado via build_main_screen_state
        #    (normaliza order_label, filter_label, search_text)
        state = build_main_screen_state(
            clients=inp.clients,
            raw_order_label=inp.raw_order_label,
            raw_filter_label=inp.raw_filter_label,
            raw_search_text=inp.raw_search_text,
            selected_ids=inp.selected_ids,
            is_trash_screen=inp.is_trash_screen,
        )

        # 2. Computar estado filtrado/ordenado via controller headless
        computed = compute_main_screen_state(state)

        # 3. Retornar resultado pronto para UI
        return FilterSortResult(state=state, computed=computed)

    def compute_for_selection_change(
        self,
        current_visible_clients: Sequence[ClienteRow],
        inp: FilterSortInput,
    ) -> FilterSortResult:
        """Recomputa apenas para mudança de seleção (otimização).

        Quando apenas a seleção muda (sem alterar filtros/ordem/busca),
        podemos reusar a lista de clientes visíveis atual ao invés de
        reprocessar a lista completa.

        Args:
            current_visible_clients: Lista atualmente visível na UI
            inp: Parâmetros de entrada (principalmente selected_ids)

        Returns:
            FilterSortResult com flags de batch atualizadas

        Examples:
            >>> manager = FilterSortManager()
            >>> # Primeira computação completa
            >>> result1 = manager.compute(inp1)
            >>> visible = result1.computed.visible_clients
            >>>
            >>> # Usuário seleciona itens, recomputar apenas batch flags
            >>> inp2 = FilterSortInput(..., selected_ids={"1", "2"}, ...)
            >>> result2 = manager.compute_for_selection_change(visible, inp2)
            >>> # result2.computed.can_batch_delete reflete nova seleção
        """
        # Usar clientes visíveis atuais ao invés de reprocessar
        state = build_main_screen_state(
            clients=current_visible_clients,
            raw_order_label=inp.raw_order_label,
            raw_filter_label=inp.raw_filter_label,
            raw_search_text=inp.raw_search_text,
            selected_ids=inp.selected_ids,
            is_trash_screen=inp.is_trash_screen,
        )

        computed = compute_main_screen_state(state)

        return FilterSortResult(state=state, computed=computed)
