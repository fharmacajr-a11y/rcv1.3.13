# -*- coding: utf-8 -*-

"""Main screen controller - headless business logic.

Este módulo contém a lógica de negócio pura da tela principal de clientes,
sem dependências do Tkinter. Facilita testes e separação de responsabilidades.

Fase MS-1: Extração inicial de lógica de filtros, ordenação e batch operations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from src.modules.clientes.viewmodel import ClienteRow
from src.modules.clientes.views.main_screen_helpers import (
    apply_combined_filters,
    can_batch_delete,
    can_batch_export,
    can_batch_restore,
    normalize_order_label,
    normalize_status_filter_value,
    ORDER_CHOICES,
)


@dataclass
class MainScreenState:
    """Estado atual da tela principal de clientes.

    Attributes:
        clients: Lista completa de clientes (antes de filtros)
        order_label: Label de ordenação atual (ex.: "Razão Social (A→Z)")
        filter_label: Label de filtro de status atual (ex.: "Ativo", "Todos")
        search_text: Texto de busca atual
        selected_ids: IDs dos clientes selecionados
        is_online: Se está conectado ao Supabase
        is_trash_screen: Se está na tela de lixeira
    """

    clients: Sequence[ClienteRow]
    order_label: str
    filter_label: str
    search_text: str
    selected_ids: Sequence[str]
    is_online: bool = True
    is_trash_screen: bool = False


@dataclass
class MainScreenComputed:
    """Resultado computado do estado da tela principal.

    Attributes:
        visible_clients: Clientes visíveis após aplicar filtros e ordenação
        can_batch_delete: Se a ação de exclusão em massa está disponível
        can_batch_restore: Se a ação de restauração em massa está disponível
        can_batch_export: Se a ação de exportação em massa está disponível
        selection_count: Quantidade de itens selecionados
        has_selection: Se há pelo menos um item selecionado
    """

    visible_clients: Sequence[ClienteRow]
    can_batch_delete: bool
    can_batch_restore: bool
    can_batch_export: bool
    selection_count: int
    has_selection: bool


def compute_main_screen_state(state: MainScreenState) -> MainScreenComputed:
    """Aplica filtros, ordenação e calcula disponibilidade de ações em lote.

    Esta é a função principal do controller. Recebe o estado atual da tela
    e retorna os dados computados (clientes visíveis + flags de ações).

    Args:
        state: Estado atual da tela principal

    Returns:
        Dados computados prontos para exibição

    Examples:
        >>> from src.modules.clientes.viewmodel import ClienteRow
        >>> clients = [
        ...     ClienteRow(id="1", razao_social="ACME", cnpj="", nome="",
        ...                whatsapp="", observacoes="", status="Ativo",
        ...                ultima_alteracao="", search_norm="acme ativo"),
        ...     ClienteRow(id="2", razao_social="Beta", cnpj="", nome="",
        ...                whatsapp="", observacoes="", status="Inativo",
        ...                ultima_alteracao="", search_norm="beta inativo"),
        ... ]
        >>> state = MainScreenState(
        ...     clients=clients,
        ...     order_label="Razão Social (A→Z)",
        ...     filter_label="Ativo",
        ...     search_text="",
        ...     selected_ids=["1"],
        ...     is_online=True,
        ...     is_trash_screen=False,
        ... )
        >>> result = compute_main_screen_state(state)
        >>> len(result.visible_clients)
        1
        >>> result.visible_clients[0].razao_social
        'ACME'
        >>> result.can_batch_delete
        True
    """
    # 1. Aplicar filtros
    filtered_clients = filter_clients(
        state.clients,
        filter_label=state.filter_label,
        search_text=state.search_text,
    )

    # 2. Aplicar ordenação
    ordered_clients = order_clients(
        filtered_clients,
        order_label=state.order_label,
    )

    # 3. Calcular flags de batch operations
    selected_set = set(state.selected_ids)

    batch_delete = can_batch_delete(
        selected_set,
        is_trash_screen=state.is_trash_screen,
        is_online=state.is_online,
    )

    batch_restore = can_batch_restore(
        selected_set,
        is_trash_screen=state.is_trash_screen,
        is_online=state.is_online,
    )

    batch_export = can_batch_export(selected_set)

    # 4. Calcular estatísticas de seleção
    selection_count = len(selected_set)
    has_selection = selection_count > 0

    return MainScreenComputed(
        visible_clients=ordered_clients,
        can_batch_delete=batch_delete,
        can_batch_restore=batch_restore,
        can_batch_export=batch_export,
        selection_count=selection_count,
        has_selection=has_selection,
    )


def filter_clients(
    clients: Sequence[ClienteRow],
    *,
    filter_label: str,
    search_text: str = "",
) -> list[ClienteRow]:
    """Aplica filtros de status e texto de busca aos clientes.

    Args:
        clients: Lista de clientes a filtrar
        filter_label: Label de filtro de status (ex.: "Ativo", "Todos")
        search_text: Texto de busca (opcional)

    Returns:
        Lista filtrada de clientes

    Examples:
        >>> clients = [
        ...     ClienteRow(id="1", razao_social="ACME", status="Ativo", search_norm="acme ativo"),
        ...     ClienteRow(id="2", razao_social="Beta", status="Inativo", search_norm="beta inativo"),
        ... ]
        >>> filtered = filter_clients(clients, filter_label="Ativo")
        >>> len(filtered)
        1
        >>> filtered[0].razao_social
        'ACME'
    """
    # Normalizar filtro de status
    status_filter = normalize_status_filter_value(filter_label)

    # Converter ClienteRow para dict para compatibilidade com helpers
    clients_dicts = [
        {
            "id": c.id,
            "razao_social": c.razao_social,
            "cnpj": c.cnpj,
            "nome": c.nome,
            "whatsapp": c.whatsapp,
            "observacoes": c.observacoes,
            "status": c.status,
            "ultima_alteracao": c.ultima_alteracao,
            "search_norm": c.search_norm,
            "raw": c.raw,
        }
        for c in clients
    ]

    # Aplicar filtros combinados usando helper
    filtered_dicts = apply_combined_filters(
        clients_dicts,
        status_filter=status_filter,
        search_text=search_text,
        search_field="search_norm",
    )

    # Converter de volta para ClienteRow
    return [
        ClienteRow(
            id=d["id"],
            razao_social=d["razao_social"],
            cnpj=d["cnpj"],
            nome=d["nome"],
            whatsapp=d["whatsapp"],
            observacoes=d["observacoes"],
            status=d["status"],
            ultima_alteracao=d["ultima_alteracao"],
            search_norm=d["search_norm"],
            raw=d["raw"],
        )
        for d in filtered_dicts
    ]


def order_clients(
    clients: Sequence[ClienteRow],
    *,
    order_label: str,
) -> list[ClienteRow]:
    """Ordena clientes de acordo com o label de ordenação.

    Args:
        clients: Lista de clientes a ordenar
        order_label: Label de ordenação (ex.: "Razão Social (A→Z)")

    Returns:
        Lista ordenada de clientes

    Examples:
        >>> clients = [
        ...     ClienteRow(id="2", razao_social="Beta", ...),
        ...     ClienteRow(id="1", razao_social="ACME", ...),
        ... ]
        >>> ordered = order_clients(clients, order_label="Razão Social (A→Z)")
        >>> ordered[0].razao_social
        'ACME'
    """
    # Normalizar label de ordenação
    normalized_label = normalize_order_label(order_label)

    # Resolver campo e direção usando ORDER_CHOICES
    if normalized_label not in ORDER_CHOICES:
        # Ordenação desconhecida, retornar lista sem ordenar
        return list(clients)

    field, reverse = ORDER_CHOICES[normalized_label]

    if not field:
        return list(clients)

    # Criar lista mutável para ordenar
    result = list(clients)

    # Ordenar usando o campo apropriado
    if field == "razao_social":
        result.sort(key=lambda c: (c.razao_social or "").casefold(), reverse=reverse)
    elif field == "cnpj":
        # Ordenar por CNPJ (apenas dígitos)
        result.sort(
            key=lambda c: "".join(ch for ch in (c.cnpj or "") if ch.isdigit()),
            reverse=reverse,
        )
    elif field == "nome":
        result.sort(key=lambda c: (c.nome or "").casefold(), reverse=reverse)
    elif field == "id":
        # Ordenar por ID numérico
        def id_key(client: ClienteRow) -> tuple[bool, int]:
            try:
                return (False, int(client.id))
            except (ValueError, TypeError):
                # IDs inválidos vão pro final
                return (True, 0)

        result.sort(key=id_key, reverse=reverse)
    elif field == "ultima_alteracao":
        # Ordenar por data de última alteração
        # (implementação simplificada - pode ser melhorada em fases futuras)
        result.sort(key=lambda c: c.ultima_alteracao or "", reverse=reverse)

    return result


def compute_batch_flags(
    selected_ids: Sequence[str],
    *,
    is_online: bool,
    is_trash_screen: bool,
) -> tuple[bool, bool, bool]:
    """Calcula flags de disponibilidade das ações em lote.

    Args:
        selected_ids: IDs dos clientes selecionados
        is_online: Se está conectado ao Supabase
        is_trash_screen: Se está na tela de lixeira

    Returns:
        Tupla (can_delete, can_restore, can_export)

    Examples:
        >>> compute_batch_flags(["1", "2"], is_online=True, is_trash_screen=False)
        (True, False, True)

        >>> compute_batch_flags(["1"], is_online=True, is_trash_screen=True)
        (True, True, True)

        >>> compute_batch_flags([], is_online=True, is_trash_screen=False)
        (False, False, False)
    """
    selected_set = set(selected_ids)

    delete_flag = can_batch_delete(
        selected_set,
        is_trash_screen=is_trash_screen,
        is_online=is_online,
    )

    restore_flag = can_batch_restore(
        selected_set,
        is_trash_screen=is_trash_screen,
        is_online=is_online,
    )

    export_flag = can_batch_export(selected_set)

    return (delete_flag, restore_flag, export_flag)
