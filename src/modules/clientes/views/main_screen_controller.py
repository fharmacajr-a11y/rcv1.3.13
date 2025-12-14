# -*- coding: utf-8 -*-

"""Main screen controller - headless business logic.

Este módulo contém a lógica de negócio pura da tela principal de clientes,
sem dependências do Tkinter. Facilita testes e separação de responsabilidades.

Fase MS-1: Extração inicial de lógica de filtros, ordenação e batch operations.
Fase MS-8: Adição de Protocols para interfaces de dados computados.
Fase MS-32: Centralização de estados de botões no controller headless.
Fase MS-33: Decisões headless para operações em lote (delete/restore/export).
"""

from __future__ import annotations

from collections.abc import Collection, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any, Literal, Protocol

from src.modules.clientes.controllers import batch_operations
from src.modules.clientes.viewmodel import ClienteRow
from src.modules.clientes.views.main_screen_state_builder import build_main_screen_state
from src.modules.clientes.views.main_screen_helpers import (
    apply_combined_filters,
    calculate_button_states,
    calculate_new_clients_stats,
    format_clients_summary,
    get_selection_count,
    normalize_order_label,
    normalize_status_filter_value,
    ORDER_CHOICES,
    sort_key_razao_social_asc,
    sort_key_razao_social_desc,
)
from src.modules.clientes.views.main_screen_state import (
    MainScreenState,  # noqa: F401 - usado em doctests  # pyright: ignore[reportUnusedImport]
    MainScreenStateLike,
)


# ============================================================================
# PROTOCOLS (INTERFACES)
# ============================================================================


class MainScreenComputedLike(Protocol):
    """Interface de leitura para os dados computados da Main Screen.

    Permite structural subtyping e facilita testes com mocks.

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


# ============================================================================
# CONCRETE IMPLEMENTATIONS
# ============================================================================


@dataclass(frozen=True)
class FilterOrderInput:
    """Entrada para computação de filtro/ordem/busca (MS-34).

    Agrupa todos os parâmetros necessários para filtrar, ordenar e pesquisar
    clientes na tela principal.

    Attributes:
        raw_clients: Lista completa de clientes (antes de filtros)
        order_label: Label de ordenação (ex: "Razão Social (A→Z)")
        filter_label: Label de filtro de status (ex: "Ativo", "Todos")
        search_text: Texto de busca (aplicado em múltiplos campos)
        selected_ids: IDs atualmente selecionados na UI
        is_trash_screen: Se True, está na tela de lixeira
        is_online: Se está conectado ao Supabase
    """

    raw_clients: Sequence[ClienteRow]
    order_label: str
    filter_label: str
    search_text: str
    selected_ids: Collection[str]
    is_trash_screen: bool
    is_online: bool


@dataclass(frozen=True)
class ButtonStates:
    """Estados calculados de botões da tela principal (MS-32).

    Centraliza toda a lógica de enabled/disabled de botões no controller headless,
    removendo essa responsabilidade da View.

    Attributes:
        editar: Botão Editar habilitado (requer seleção + online)
        subpastas: Botão Subpastas habilitado (requer seleção + online)
        enviar: Botão Enviar habilitado (requer seleção + online + não uploading)
        novo: Botão Novo habilitado (requer online)
        lixeira: Botão Lixeira habilitado (requer online)
        select: Botão Selecionar habilitado (modo pick + seleção)
        enviar_text: Texto dinâmico do botão Enviar (muda com conectividade)
    """

    editar: bool
    subpastas: bool
    enviar: bool
    novo: bool
    lixeira: bool
    select: bool
    enviar_text: str


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


@dataclass(frozen=True)
class BatchDecision:
    """Decisão headless para operações em lote (delete/restore/export)."""

    kind: Literal["noop", "warning", "confirm", "execute"]
    message: str | None = None
    operation: Literal["delete", "restore", "export"] | None = None


@dataclass(frozen=True)
class StatusChangeDecision:
    """Decisão headless para mudança de status na main screen (MS-35).

    Encapsula toda a lógica de validação e decisão sobre mudança de status
    de clientes, removendo essa responsabilidade da view.

    Attributes:
        kind: Tipo de decisão (noop/error/execute)
        message: Mensagem de erro ou sucesso (se aplicável)
        new_status: Novo status a ser aplicado (se kind=execute)
        target_id: ID do cliente alvo (se kind=execute)
    """

    kind: Literal["noop", "error", "execute"]
    message: str | None = None
    new_status: str | None = None
    target_id: int | None = None


@dataclass(frozen=True)
class CountSummary:
    """Resumo de contagem para a barra de status/rodapé (MS-35).

    Centraliza toda a lógica de cálculo de estatísticas de clientes,
    removendo essa responsabilidade da view.

    Attributes:
        total: Total de clientes visíveis
        new_today: Clientes criados hoje
        new_this_month: Clientes criados este mês
        text: Texto formatado pronto para exibição
    """

    total: int
    new_today: int
    new_this_month: int
    text: str


def decide_batch_delete(
    *,
    selected_ids: Collection[str],
    is_trash_screen: bool,
    is_online: bool,
) -> BatchDecision:
    """Decide fluxo para exclusão em lote mantendo mensagens atuais."""
    if not selected_ids:
        return BatchDecision(kind="noop", operation="delete")

    selected_set = set(selected_ids)

    if not batch_operations.can_batch_delete(selected_set, is_trash_screen=is_trash_screen, is_online=is_online):
        return BatchDecision(
            kind="warning",
            message=(
                "A exclusão em lote não está disponível no momento.\n"
                "Verifique sua conexão ou se há clientes selecionados."
            ),
            operation="delete",
        )

    count = get_selection_count(selected_set)
    confirm_message = (
        f"Você deseja excluir definitivamente {count} cliente(s) selecionado(s)?\n\n"
        f"⚠️ Esta operação NÃO pode ser desfeita!\n"
        f"Os dados e arquivos associados serão removidos permanentemente."
    )
    return BatchDecision(kind="confirm", message=confirm_message, operation="delete")


def decide_batch_restore(
    *,
    selected_ids: Collection[str],
    is_trash_screen: bool,
    is_online: bool,
) -> BatchDecision:
    """Decide fluxo para restauração em lote mantendo mensagens atuais."""
    if not selected_ids:
        return BatchDecision(kind="noop", operation="restore")

    selected_set = set(selected_ids)

    if not batch_operations.can_batch_restore(selected_set, is_trash_screen=is_trash_screen, is_online=is_online):
        return BatchDecision(
            kind="warning",
            message=(
                "A restauração em lote não está disponível nesta tela.\nUse a tela de Lixeira para restaurar clientes."
            ),
            operation="restore",
        )

    count = get_selection_count(selected_set)
    confirm_message = f"Você deseja restaurar {count} cliente(s) selecionado(s) da lixeira?"
    return BatchDecision(kind="confirm", message=confirm_message, operation="restore")


def decide_batch_export(
    *,
    selected_ids: Collection[str],
) -> BatchDecision:
    """Decide fluxo para exportação em lote mantendo mensagens atuais."""
    if not selected_ids:
        return BatchDecision(kind="noop", operation="export")

    selected_set = set(selected_ids)

    if not batch_operations.can_batch_export(selected_set):
        return BatchDecision(
            kind="warning",
            message=("A exportação em lote não está disponível no momento.\nVerifique se há clientes selecionados."),
            operation="export",
        )

    return BatchDecision(kind="execute", operation="export")


def compute_main_screen_state(state: MainScreenStateLike) -> MainScreenComputed:
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

    batch_delete = batch_operations.can_batch_delete(
        selected_set,
        is_trash_screen=state.is_trash_screen,
        is_online=state.is_online,
    )

    batch_restore = batch_operations.can_batch_restore(
        selected_set,
        is_trash_screen=state.is_trash_screen,
        is_online=state.is_online,
    )

    batch_export = batch_operations.can_batch_export(selected_set)

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
            "ultima_alteracao_ts": c.ultima_alteracao_ts,  # Preservar timestamp
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
            ultima_alteracao_ts=d.get("ultima_alteracao_ts"),  # Preservar timestamp
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
        if reverse:
            result.sort(key=sort_key_razao_social_desc)
        else:
            result.sort(key=sort_key_razao_social_asc)
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
        # Ordenar por data de última alteração usando timestamp
        from datetime import datetime

        def ts_key(client: ClienteRow) -> tuple[int, Any]:
            ts = client.ultima_alteracao_ts
            if ts is None:
                # Clientes sem data vão para o final sempre
                # Quando reverse=False (crescente), grupo 1 vai pro final
                # Quando reverse=True (decrescente), grupo 0 vai pro final, então invertemos
                grupo = 0 if reverse else 1
                return (grupo, datetime.min)

            # Clientes com data ficam no outro grupo
            grupo = 1 if reverse else 0
            if isinstance(ts, datetime):
                return (grupo, ts)

            # Se for string, tentar converter
            if isinstance(ts, str):
                try:
                    # Tentar parsear ISO 8601 com datetime.fromisoformat
                    return (grupo, datetime.fromisoformat(ts.replace("Z", "+00:00")))
                except (ValueError, AttributeError):
                    # Se falhar, tentar outros formatos comuns
                    for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
                        try:
                            return (grupo, datetime.strptime(ts, fmt))
                        except ValueError:
                            continue

            # Se falhar o parsing, vai pro final
            grupo_final = 0 if reverse else 1
            return (grupo_final, datetime.min)

        result.sort(key=ts_key, reverse=reverse)

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

    delete_flag = batch_operations.can_batch_delete(
        selected_set,
        is_trash_screen=is_trash_screen,
        is_online=is_online,
    )

    restore_flag = batch_operations.can_batch_restore(
        selected_set,
        is_trash_screen=is_trash_screen,
        is_online=is_online,
    )

    export_flag = batch_operations.can_batch_export(selected_set)

    return (delete_flag, restore_flag, export_flag)


# ============================================================================
# BUTTON STATES COMPUTATION (MS-32)
# ============================================================================


def compute_button_states(
    *,
    has_selection: bool,
    is_online: bool,
    is_uploading: bool,
    is_pick_mode: bool = False,
    connectivity_state: Literal["online", "unstable", "offline"] = "online",
) -> ButtonStates:
    """Calcula estados de todos os botões da tela principal (MS-32).

    Centraliza a lógica de enabled/disabled de botões no controller headless,
    consolidando a responsabilidade que estava espalhada entre UiStateManager
    e helpers.

    Args:
        has_selection: Se há cliente selecionado na lista
        is_online: Se está conectado ao Supabase (estado "online")
        is_uploading: Se está em processo de upload
        is_pick_mode: Se está em modo de seleção (pick)
        connectivity_state: Estado detalhado de conectividade

    Returns:
        ButtonStates com todos os campos de estado de botões.

    Examples:
        >>> compute_button_states(has_selection=True, is_online=True, is_uploading=False)
        ButtonStates(editar=True, subpastas=True, enviar=True, novo=True, lixeira=True, select=False, enviar_text='Enviar Para SupaBase')

        >>> compute_button_states(has_selection=False, is_online=True, is_uploading=False)
        ButtonStates(editar=False, subpastas=False, enviar=False, novo=True, lixeira=True, select=False, enviar_text='Enviar Para SupaBase')

        >>> compute_button_states(has_selection=True, is_online=True, is_uploading=False, is_pick_mode=True)
        ButtonStates(editar=False, subpastas=False, enviar=False, novo=False, lixeira=False, select=True, enviar_text='Enviar Para SupaBase')

        >>> compute_button_states(has_selection=True, is_online=True, is_uploading=True)
        ButtonStates(editar=True, subpastas=True, enviar=False, novo=True, lixeira=True, select=False, enviar_text='Enviando...')

        >>> compute_button_states(has_selection=True, is_online=True, is_uploading=False, connectivity_state="unstable")
        ButtonStates(editar=True, subpastas=True, enviar=True, novo=True, lixeira=True, select=False, enviar_text='Envio suspenso - Conexao instavel')
    """
    # Delegar cálculo de estados booleanos ao helper puro (reutilização)
    raw_states = calculate_button_states(
        has_selection=has_selection,
        is_online=is_online,
        is_uploading=is_uploading,
        is_pick_mode=is_pick_mode,
    )

    # Calcular texto do botão Enviar baseado em conectividade
    enviar_text = _compute_enviar_text(
        connectivity_state=connectivity_state,
        is_uploading=is_uploading,
    )

    return ButtonStates(
        editar=raw_states["editar"],
        subpastas=raw_states["subpastas"],
        enviar=raw_states["enviar"],
        novo=raw_states["novo"],
        lixeira=raw_states["lixeira"],
        select=raw_states["select"],
        enviar_text=enviar_text,
    )


def _compute_enviar_text(
    *,
    connectivity_state: Literal["online", "unstable", "offline"],
    is_uploading: bool,
) -> str:
    """Calcula o texto do botão Enviar baseado em conectividade.

    Args:
        connectivity_state: Estado de conectividade ("online", "unstable", "offline")
        is_uploading: Se está em processo de upload

    Returns:
        Texto apropriado para o botão Enviar.

    Examples:
        >>> _compute_enviar_text(connectivity_state="online", is_uploading=False)
        'Enviar Para SupaBase'

        >>> _compute_enviar_text(connectivity_state="online", is_uploading=True)
        'Enviando...'

        >>> _compute_enviar_text(connectivity_state="unstable", is_uploading=False)
        'Envio suspenso - Conexao instavel'

        >>> _compute_enviar_text(connectivity_state="offline", is_uploading=False)
        'Envio suspenso - Offline'
    """
    if is_uploading:
        return "Enviando..."

    if connectivity_state == "online":
        return "Enviar Para SupaBase"
    elif connectivity_state == "unstable":
        return "Envio suspenso - Conexao instavel"
    else:  # offline
        return "Envio suspenso - Offline"


# ============================================================================
# FILTER/ORDER/SEARCH COMPUTATION (MS-34)
# ============================================================================


def compute_filtered_and_ordered(inp: FilterOrderInput) -> MainScreenComputed:
    """Aplica filtros, ordenação e busca centralizados no controller (MS-34).

    Esta função centraliza toda a lógica de filtro/ordem/busca que antes estava
    espalhada entre view e FilterSortManager. A view apenas coleta inputs e
    aplica o resultado.

    Args:
        inp: Entrada com clientes, filtros, ordenação, seleção e contexto

    Returns:
        MainScreenComputed com lista filtrada/ordenada e flags de batch operations.

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
        >>> inp = FilterOrderInput(
        ...     raw_clients=clients,
        ...     order_label="Razão Social (A→Z)",
        ...     filter_label="Ativo",
        ...     search_text="",
        ...     selected_ids=["1"],
        ...     is_trash_screen=False,
        ...     is_online=True,
        ... )
        >>> result = compute_filtered_and_ordered(inp)
        >>> len(result.visible_clients)
        1
        >>> result.visible_clients[0].razao_social
        'ACME'
        >>> result.can_batch_delete
        True
    """
    # Construir estado normalizado usando builder
    state = build_main_screen_state(
        clients=inp.raw_clients,
        raw_order_label=inp.order_label,
        raw_filter_label=inp.filter_label,
        raw_search_text=inp.search_text,
        selected_ids=inp.selected_ids,
        is_online=inp.is_online,
        is_trash_screen=inp.is_trash_screen,
    )

    # Delegar para compute_main_screen_state que já faz filtro/ordem/batch
    return compute_main_screen_state(state)


# ============================================================================
# STATUS CHANGE COMPUTATION (MS-35)
# ============================================================================


def decide_status_change(
    *,
    cliente_id: int | None,
    chosen_status: str,
) -> StatusChangeDecision:
    """Decide se pode mudar o status de um cliente (MS-35).

    Centraliza toda a lógica de validação de mudança de status que antes
    estava na view. A view apenas interpreta a decisão.

    Args:
        cliente_id: ID do cliente (None se não houver seleção válida)
        chosen_status: Novo status desejado

    Returns:
        StatusChangeDecision com tipo de decisão e contexto.

    Examples:
        >>> decide_status_change(cliente_id=None, chosen_status="Ativo")
        StatusChangeDecision(kind='noop', message=None, new_status=None, target_id=None)

        >>> decide_status_change(cliente_id=123, chosen_status="Ativo")
        StatusChangeDecision(kind='execute', message=None, new_status='Ativo', target_id=123)
    """
    # Validação: se não tem cliente selecionado, não faz nada
    if cliente_id is None:
        return StatusChangeDecision(
            kind="noop",
            message=None,
            new_status=None,
            target_id=None,
        )

    # Validação básica: status escolhido não pode ser vazio
    if not chosen_status or not chosen_status.strip():
        return StatusChangeDecision(
            kind="error",
            message="Status inválido selecionado.",
            new_status=None,
            target_id=None,
        )

    # Decisão: pode executar a mudança
    return StatusChangeDecision(
        kind="execute",
        message=None,
        new_status=chosen_status,
        target_id=cliente_id,
    )


# ============================================================================
# COUNT/STATISTICS COMPUTATION (MS-35)
# ============================================================================


def compute_count_summary(
    *,
    visible_clients: Sequence[ClienteRow],
    raw_clients_for_stats: Sequence[Any] | None = None,
) -> CountSummary:
    """Calcula resumo de contagem para a barra de status (MS-35).

    Centraliza toda a lógica de cálculo de estatísticas de clientes,
    incluindo contagem de novos hoje e no mês.

    Args:
        visible_clients: Clientes visíveis após filtros (para total)
        raw_clients_for_stats: Clientes raw com created_at (para estatísticas)

    Returns:
        CountSummary com total, novos hoje, novos mês e texto formatado.

    Examples:
        >>> from src.modules.clientes.viewmodel import ClienteRow
        >>> clients = [
        ...     ClienteRow(id="1", razao_social="ACME", cnpj="", nome="",
        ...                whatsapp="", observacoes="", status="Ativo",
        ...                ultima_alteracao="", search_norm="acme"),
        ... ]
        >>> summary = compute_count_summary(visible_clients=clients)
        >>> summary.total
        1
        >>> summary.text
        '1 cliente'
    """
    total = len(visible_clients)
    new_today = 0
    new_month = 0

    # Calcular estatísticas se temos dados raw
    if raw_clients_for_stats:
        today = date.today()
        new_today, new_month = calculate_new_clients_stats(
            raw_clients_for_stats,
            today,
        )

    # Formatar texto usando helper
    text = format_clients_summary(total, new_today, new_month)

    return CountSummary(
        total=total,
        new_today=new_today,
        new_this_month=new_month,
        text=text,
    )
