"""Helpers puros para lógica de UI da tela principal de clientes.

Este módulo contém funções puras extraídas de main_screen.py para facilitar
testes e reduzir acoplamento com Tkinter.
"""

from __future__ import annotations

from collections.abc import Collection
from datetime import date, datetime
from typing import TYPE_CHECKING, Any, Literal, Protocol, Sequence

if TYPE_CHECKING:
    from src.modules.clientes.viewmodel import ClienteRow


class ClientWithCreatedAt(Protocol):
    """Protocol para objetos cliente que possuem campo created_at.

    Permite duck typing para dicts e objetos com o campo created_at.
    """

    def get(self, key: str, default: Any = None) -> Any:
        """Método get para acesso estilo dict."""
        ...


ORDER_LABEL_RAZAO = "Razão Social (A→Z)"
ORDER_LABEL_CNPJ = "CNPJ (A→Z)"
ORDER_LABEL_NOME = "Nome (A→Z)"
ORDER_LABEL_ID_ASC = "ID (1→9)"
ORDER_LABEL_ID_DESC = "ID (9→1)"
ORDER_LABEL_UPDATED_RECENT = "Última Alteração (mais recente)"
ORDER_LABEL_UPDATED_OLD = "Última Alteração (mais antiga)"

ORDER_LABEL_ALIASES = {
    "Razao Social (A->Z)": ORDER_LABEL_RAZAO,
    "CNPJ (A->Z)": ORDER_LABEL_CNPJ,
    "Nome (A->Z)": ORDER_LABEL_NOME,
    "Ultima Alteracao (mais recente)": ORDER_LABEL_UPDATED_RECENT,
    "Ultima Alteracao (mais antiga)": ORDER_LABEL_UPDATED_OLD,
    "ID (1→9)": ORDER_LABEL_ID_ASC,
    "ID (1->9)": ORDER_LABEL_ID_ASC,
    "ID (9→1)": ORDER_LABEL_ID_DESC,
    "ID (9->1)": ORDER_LABEL_ID_DESC,
}

DEFAULT_ORDER_LABEL = ORDER_LABEL_RAZAO

ORDER_CHOICES: dict[str, tuple[str | None, bool]] = {
    ORDER_LABEL_RAZAO: ("razao_social", False),
    ORDER_LABEL_CNPJ: ("cnpj", False),
    ORDER_LABEL_NOME: ("nome", False),
    ORDER_LABEL_ID_ASC: ("id", False),
    ORDER_LABEL_ID_DESC: ("id", True),
    ORDER_LABEL_UPDATED_RECENT: ("ultima_alteracao", True),  # True = mais recente primeiro
    ORDER_LABEL_UPDATED_OLD: ("ultima_alteracao", False),  # False = mais antiga primeiro
}


UNICODE_MAX_CODEPOINT = 0x10FFFF


def _normalize_razao_social_value(row: "ClienteRow") -> str:
    """Extrai e normaliza a Razão Social usada para ordenação."""
    return (getattr(row, "razao_social", "") or "").strip()


def _invert_casefold_value(value: str) -> str:
    """Inverte os codepoints para permitir ordenação descendente sem reverse."""
    if not value:
        return value

    max_codepoint = UNICODE_MAX_CODEPOINT
    return "".join(chr(max_codepoint - ord(ch)) for ch in value)


def sort_key_razao_social_asc(row: "ClienteRow") -> tuple[int, str]:
    """Key function para Razão Social (A→Z) mantendo vazios no final."""
    normalized = _normalize_razao_social_value(row)
    is_empty = 1 if not normalized else 0
    return (is_empty, normalized.casefold())


def sort_key_razao_social_desc(row: "ClienteRow") -> tuple[int, str]:
    """Key function para Razão Social (Z→A) mantendo vazios no final."""
    normalized = _normalize_razao_social_value(row)
    is_empty = 1 if not normalized else 0
    casefolded = normalized.casefold()
    return (is_empty, _invert_casefold_value(casefolded))


FILTER_LABEL_TODOS = "Todos"

DEFAULT_FILTER_LABEL = FILTER_LABEL_TODOS

FILTER_LABEL_ALIASES: dict[str, str] = {
    "todos": FILTER_LABEL_TODOS,
    "TODOS": FILTER_LABEL_TODOS,
    "all": FILTER_LABEL_TODOS,
    "All": FILTER_LABEL_TODOS,
    "ALL": FILTER_LABEL_TODOS,
}


def normalize_filter_label(label: str | None) -> str:
    """Normaliza um rótulo de filtro.

    - None ou string vazia -> "" (string vazia)
    - Aliases conhecidos (ex.: "todos", "ALL") -> label canônico (FILTER_LABEL_TODOS)
    - Qualquer outro texto -> retornado como está, stripado

    Args:
        label: Rótulo de filtro a normalizar

    Returns:
        Rótulo normalizado

    Examples:
        >>> normalize_filter_label("todos")
        'Todos'
        >>> normalize_filter_label("ALL")
        'Todos'
        >>> normalize_filter_label("  Novo cliente  ")
        'Novo cliente'
        >>> normalize_filter_label(None)
        ''
    """
    normalized = (label or "").strip()
    return FILTER_LABEL_ALIASES.get(normalized, normalized)


def normalize_status_filter_value(status_value: str | None) -> str | None:
    """Normaliza valor de filtro de status para uso interno.

    Converte "Todos" (e variações) para None, indicando sem filtro.
    Outros valores são retornados com strip aplicado.

    Args:
        status_value: Valor do filtro de status da UI

    Returns:
        None se for "Todos" ou vazio, caso contrário o valor normalizado

    Examples:
        >>> normalize_status_filter_value("Todos")
        None
        >>> normalize_status_filter_value("todos")
        None
        >>> normalize_status_filter_value("Novo cliente")
        'Novo cliente'
        >>> normalize_status_filter_value("")
        None
        >>> normalize_status_filter_value(None)
        None
    """
    if not status_value:
        return None

    normalized = status_value.strip()
    if not normalized:
        return None

    # Se for "Todos" (case-insensitive), retorna None
    if normalized.lower() == FILTER_LABEL_TODOS.lower():
        return None

    return normalized


def build_filter_choices_with_all_option(status_options: Sequence[str]) -> list[str]:
    """Constrói lista de opções para combobox de filtro de status.

    Adiciona "Todos" no início da lista de opções.

    Args:
        status_options: Lista de opções de status disponíveis

    Returns:
        Lista com "Todos" + status_options

    Examples:
        >>> build_filter_choices_with_all_option(["Novo cliente", "Finalizado"])
        ['Todos', 'Novo cliente', 'Finalizado']
        >>> build_filter_choices_with_all_option([])
        ['Todos']
    """
    return [FILTER_LABEL_TODOS] + list(status_options)


def resolve_filter_choice_from_options(
    current_value: str | None,
    available_choices: Sequence[str],
) -> str:
    """Resolve qual filtro deve estar selecionado dadas as opções disponíveis.

    Faz matching case-insensitive. Se o valor atual não está nas opções,
    retorna o filtro padrão ("Todos").

    Args:
        current_value: Valor atualmente selecionado
        available_choices: Opções disponíveis na combobox

    Returns:
        Opção válida a ser selecionada (com case correto)

    Examples:
        >>> choices = ["Todos", "Novo cliente", "Finalizado"]
        >>> resolve_filter_choice_from_options("novo cliente", choices)
        'Novo cliente'
        >>> resolve_filter_choice_from_options("TODOS", choices)
        'Todos'
        >>> resolve_filter_choice_from_options("Inexistente", choices)
        'Todos'
        >>> resolve_filter_choice_from_options(None, choices)
        'Todos'
    """
    if not current_value:
        return DEFAULT_FILTER_LABEL

    current_normalized = current_value.strip().lower()
    if not current_normalized:
        return DEFAULT_FILTER_LABEL

    # Cria mapa case-insensitive
    available_map = {choice.lower(): choice for choice in available_choices}

    # Tenta encontrar match
    if current_normalized in available_map:
        return available_map[current_normalized]

    # Fallback para padrão
    return DEFAULT_FILTER_LABEL


def normalize_order_label(label: str | None) -> str:
    """Normaliza um rótulo de ordenação usando ORDER_LABEL_ALIASES.

    - None ou string vazia -> "" (string vazia)
    - Aliases conhecidos (ex.: "Razao Social (A->Z)") -> label canônico (ex.: ORDER_LABEL_RAZAO)
    - Qualquer outro texto -> retornado como está, stripado.

    Args:
        label: Rótulo de ordenação a normalizar

    Returns:
        Rótulo normalizado

    Examples:
        >>> normalize_order_label("Razao Social (A->Z)")
        'Razão Social (A→Z)'
        >>> normalize_order_label("  Outro label  ")
        'Outro label'
        >>> normalize_order_label(None)
        ''
    """
    normalized = (label or "").strip()
    return ORDER_LABEL_ALIASES.get(normalized, normalized)


def normalize_order_choices(
    order_choices: dict[str, tuple[str | None, bool]],
) -> dict[str, tuple[str | None, bool]]:
    """Normaliza as chaves do dict de opções de ordenação usando normalize_order_label.

    Mantém os valores (campo, reverse) intocados.

    Args:
        order_choices: Dicionário de opções de ordenação

    Returns:
        Dicionário com chaves normalizadas

    Examples:
        >>> raw = {
        ...     "Razao Social (A->Z)": ("razao_social", False),
        ...     "ID (9->1)": ("id", True),
        ... }
        >>> normalized = normalize_order_choices(raw)
        >>> ORDER_LABEL_RAZAO in normalized
        True
        >>> normalized[ORDER_LABEL_RAZAO]
        ('razao_social', False)
    """
    normalized: dict[str, tuple[str | None, bool]] = {}
    for key, value in order_choices.items():
        normalized_label = normalize_order_label(key)
        normalized[normalized_label] = value
    return normalized


SelectionStatus = Literal["none", "single", "multiple"]
SelectionResult = tuple[SelectionStatus, str | None]


def classify_selection(selected_ids: Collection[str]) -> SelectionResult:
    """Classifica a seleção atual de clientes.

    Retorna uma tupla (status, client_id):
    - ("none", None)        → nenhuma seleção
    - ("single", client_id) → exatamente um cliente selecionado
    - ("multiple", None)    → mais de um cliente selecionado

    Args:
        selected_ids: Coleção de IDs selecionados (set, list, tuple, etc.)

    Returns:
        Tupla (status, client_id ou None)

    Examples:
        >>> classify_selection([])
        ('none', None)
        >>> classify_selection(["123"])
        ('single', '123')
        >>> classify_selection(["123", "456"])
        ('multiple', None)
        >>> classify_selection(set())
        ('none', None)
        >>> classify_selection({"abc"})
        ('single', 'abc')

    Notes:
        - Não depende de Tkinter, trabalha apenas com tipos básicos
        - Aceita qualquer coleção (set, list, tuple)
        - Para "single", retorna o primeiro item da coleção
    """
    if not selected_ids:
        return ("none", None)

    count = len(selected_ids)

    if count == 1:
        # Pega o único item (funciona para set, list, tuple)
        client_id = next(iter(selected_ids))
        return ("single", client_id)

    return ("multiple", None)


def can_perform_single_item_action(selection_status: SelectionStatus) -> bool:
    """Decide se pode executar ação que requer exatamente 1 item selecionado.

    Args:
        selection_status: Status da seleção ("none", "single", "multiple")

    Returns:
        True se status == "single", False caso contrário

    Examples:
        >>> can_perform_single_item_action("single")
        True
        >>> can_perform_single_item_action("none")
        False
        >>> can_perform_single_item_action("multiple")
        False
    """
    return selection_status == "single"


def can_perform_multi_item_action(selection_status: SelectionStatus) -> bool:
    """Decide se pode executar ação que aceita um ou mais itens selecionados.

    Args:
        selection_status: Status da seleção ("none", "single", "multiple")

    Returns:
        True se status == "single" ou "multiple", False se "none"

    Examples:
        >>> can_perform_multi_item_action("single")
        True
        >>> can_perform_multi_item_action("multiple")
        True
        >>> can_perform_multi_item_action("none")
        False
    """
    return selection_status in ("single", "multiple")


def validate_single_selection(
    selected_ids: Collection[str],
) -> tuple[bool, str | None, str | None]:
    """Valida seleção para ações que requerem exatamente 1 item.

    Combina classificação e validação em um único helper conveniente.

    Args:
        selected_ids: Coleção de IDs selecionados

    Returns:
        Tupla (is_valid, client_id, error_key):
        - is_valid: True se seleção é válida (exatamente 1 item)
        - client_id: ID do cliente se válido, None caso contrário
        - error_key: Chave de erro ("none_selected", "multiple_selected", ou None)

    Examples:
        >>> validate_single_selection(["123"])
        (True, '123', None)
        >>> validate_single_selection([])
        (False, None, 'none_selected')
        >>> validate_single_selection(["123", "456"])
        (False, None, 'multiple_selected')

    Notes:
        - Helper conveniente que combina classify_selection + validação
        - error_key pode ser usado para buscar mensagens apropriadas
    """
    status, client_id = classify_selection(selected_ids)

    if status == "none":
        return (False, None, "none_selected")

    if status == "multiple":
        return (False, None, "multiple_selected")

    # status == "single"
    return (True, client_id, None)


def get_selection_count(selected_ids: Collection[str]) -> int:
    """Retorna a quantidade de itens selecionados.

    Helper simples mas útil para padronizar acesso à contagem.

    Args:
        selected_ids: Coleção de IDs selecionados

    Returns:
        Número de itens selecionados

    Examples:
        >>> get_selection_count([])
        0
        >>> get_selection_count(["123"])
        1
        >>> get_selection_count({"123", "456", "789"})
        3
    """
    return len(selected_ids)


def has_selection(selected_ids: Collection[str]) -> bool:
    """Verifica se há pelo menos um item selecionado.

    Args:
        selected_ids: Coleção de IDs selecionados

    Returns:
        True se há seleção, False caso contrário

    Examples:
        >>> has_selection([])
        False
        >>> has_selection(["123"])
        True
        >>> has_selection({"123", "456"})
        True
    """
    return len(selected_ids) > 0


def calculate_button_states(
    *,
    has_selection: bool,
    is_online: bool,
    is_uploading: bool,
    is_pick_mode: bool = False,
) -> dict[str, bool]:
    """Calcula estados (enabled/disabled) dos botões da tela principal.

    Args:
        has_selection: Se há um cliente selecionado na lista
        is_online: Se está conectado ao Supabase (estado "online")
        is_uploading: Se está em processo de upload
        is_pick_mode: Se está em modo de seleção (pick)

    Returns:
        Dicionário com chaves: 'editar', 'subpastas', 'enviar', 'novo', 'lixeira', 'select'
        e valores booleanos indicando se devem estar habilitados

    Examples:
        >>> calculate_button_states(has_selection=True, is_online=True, is_uploading=False)
        {'editar': True, 'subpastas': True, 'enviar': True, 'novo': True, 'lixeira': True, 'select': False}

        >>> calculate_button_states(has_selection=False, is_online=True, is_uploading=False)
        {'editar': False, 'subpastas': False, 'enviar': False, 'novo': True, 'lixeira': True, 'select': False}

        >>> calculate_button_states(has_selection=True, is_online=False, is_uploading=False)
        {'editar': False, 'subpastas': False, 'enviar': False, 'novo': False, 'lixeira': False, 'select': False}
    """
    # Em pick mode, botões do footer devem estar desabilitados
    if is_pick_mode:
        return {
            "editar": False,
            "subpastas": False,
            "enviar": False,
            "novo": False,
            "lixeira": False,
            "select": has_selection,
        }

    allow_send = has_selection and is_online and not is_uploading

    return {
        "editar": has_selection and is_online,
        "subpastas": has_selection and is_online,
        "enviar": allow_send,
        "novo": is_online,
        "lixeira": is_online,
        "select": is_pick_mode and has_selection,
    }


def parse_created_at_date(created_at: str | None) -> date | None:
    """Parse string ISO de created_at para objeto date.

    Args:
        created_at: String ISO 8601 ou None

    Returns:
        Objeto date ou None se parsing falhar

    Examples:
        >>> parse_created_at_date("2025-11-28T15:30:00")
        datetime.date(2025, 11, 28)
        >>> parse_created_at_date(None)
        None
        >>> parse_created_at_date("invalid")
        None
    """
    if not created_at:
        return None

    try:
        return datetime.fromisoformat(created_at).date()
    except Exception:
        return None


def extract_created_at_from_client(client: ClientWithCreatedAt | Any) -> str | None:
    """Extrai campo created_at de um objeto cliente (dict ou objeto).

    Args:
        client: Objeto cliente (pode ser dict ou objeto com atributos)

    Returns:
        String do created_at ou None

    Examples:
        >>> extract_created_at_from_client({"created_at": "2025-11-28"})
        '2025-11-28'
        >>> extract_created_at_from_client({})
        None
    """
    # Tenta como atributo primeiro
    created_str = getattr(client, "created_at", None)

    # Se não encontrou e é dict-like, tenta como dict
    if not created_str and hasattr(client, "get"):
        created_str = client.get("created_at")

    return created_str


def calculate_new_clients_stats(
    clients: Sequence[ClientWithCreatedAt | Any],
    today: date,
) -> tuple[int, int]:
    """Calcula quantos clientes foram criados hoje e no mês atual.

    Args:
        clients: Sequência de clientes (dict ou objetos com created_at)
        today: Data de referência (normalmente date.today())

    Returns:
        Tupla (novos_hoje, novos_no_mes)

    Examples:
        >>> from datetime import date
        >>> clients = [
        ...     {"created_at": "2025-11-28T10:00:00"},
        ...     {"created_at": "2025-11-28T15:00:00"},
        ...     {"created_at": "2025-11-15T10:00:00"},
        ...     {"created_at": "2025-10-28T10:00:00"},
        ... ]
        >>> today = date(2025, 11, 28)
        >>> calculate_new_clients_stats(clients, today)
        (2, 3)
    """
    if not clients:
        return 0, 0

    first_of_month = today.replace(day=1)

    # Extrai e parse datas
    created_dates: list[date | None] = []
    for client in clients:
        created_str = extract_created_at_from_client(client)
        created_date = parse_created_at_date(created_str)
        created_dates.append(created_date)

    # Conta novos hoje e novos no mês
    new_today = sum(1 for d in created_dates if d and d == today)
    new_month = sum(1 for d in created_dates if d and d >= first_of_month)

    return new_today, new_month


def format_clients_summary(
    total: int,
    new_today: int,
    new_month: int,
) -> str:
    """Formata texto de resumo de clientes para exibição.

    Args:
        total: Total de clientes
        new_today: Novos clientes criados hoje
        new_month: Novos clientes criados no mês

    Returns:
        String formatada para exibição

    Examples:
        >>> format_clients_summary(100, 5, 20)
        '100 clientes (5 hoje, 20 este mês)'
        >>> format_clients_summary(1, 0, 0)
        '1 cliente'
        >>> format_clients_summary(0, 0, 0)
        '0 clientes'
    """
    if total == 1:
        base = "1 cliente"
    else:
        base = f"{total} clientes"

    if new_today > 0 or new_month > 0:
        return f"{base} ({new_today} hoje, {new_month} este mês)"

    return base


def is_single_selection(selection_tuple: Sequence[str]) -> bool:
    """Verifica se há exatamente 1 item selecionado."""
    return len(selection_tuple) == 1


def is_multiple_selection(selection_tuple: Sequence[str]) -> bool:
    """Verifica se há múltiplos itens selecionados."""
    return len(selection_tuple) >= 2


def get_first_selected_id(selection_tuple: Sequence[str]) -> str | None:
    """Retorna ID do primeiro item selecionado (ou None se vazio)."""
    return selection_tuple[0] if selection_tuple else None


def can_edit_selection(
    selection_tuple: Sequence[str],
    *,
    is_online: bool = True,
) -> bool:
    """Determina se pode editar a seleção atual (1 selecionado e online)."""
    return is_single_selection(selection_tuple) and is_online


def can_delete_selection(
    selection_tuple: Sequence[str],
    *,
    is_online: bool = True,
) -> bool:
    """Determina se pode excluir a seleção atual (pelo menos 1 selecionado e online)."""
    return has_selection(selection_tuple) and is_online


def can_open_folder_for_selection(
    selection_tuple: Sequence[str],
) -> bool:
    """Determina se pode abrir pasta para a seleção atual (exatamente 1 selecionado)."""
    return is_single_selection(selection_tuple)


ClientRow = dict[str, Any]


def filter_by_status(
    clients: Sequence[ClientRow],
    status_filter: str | None,
) -> list[ClientRow]:
    """Filtra clientes por status (case-insensitive).

    Args:
        clients: Lista de clientes (dicts com campo 'status')
        status_filter: Status para filtrar (None = sem filtro)

    Returns:
        Lista filtrada de clientes

    Examples:
        >>> clients = [{"id": "1", "status": "Ativo"}, {"id": "2", "status": "Inativo"}]
        >>> filter_by_status(clients, "ativo")
        [{"id": "1", "status": "Ativo"}]

        >>> filter_by_status(clients, None)
        [{"id": "1", "status": "Ativo"}, {"id": "2", "status": "Inativo"}]
    """
    if not status_filter:
        return list(clients)

    status_norm = status_filter.strip().lower()
    if not status_norm:
        return list(clients)

    return [client for client in clients if str(client.get("status", "")).strip().lower() == status_norm]


def filter_by_search_text(
    clients: Sequence[ClientRow],
    search_text: str | None,
    *,
    search_field: str = "search_norm",
) -> list[ClientRow]:
    """Filtra clientes por texto de busca (case-insensitive).

    Args:
        clients: Lista de clientes (dicts)
        search_text: Texto para buscar (None = sem filtro)
        search_field: Campo onde buscar (default: 'search_norm')

    Returns:
        Lista filtrada de clientes

    Examples:
        >>> clients = [
        ...     {"id": "1", "search_norm": "acme corporation"},
        ...     {"id": "2", "search_norm": "beta industries"}
        ... ]
        >>> filter_by_search_text(clients, "acme")
        [{"id": "1", "search_norm": "acme corporation"}]

        >>> filter_by_search_text(clients, None)
        [{"id": "1", "search_norm": "acme corporation"}, {"id": "2", "search_norm": "beta industries"}]
    """
    if not search_text:
        return list(clients)

    search_norm = search_text.strip().lower()
    if not search_norm:
        return list(clients)

    return [client for client in clients if search_norm in str(client.get(search_field, "")).lower()]


def apply_combined_filters(
    clients: Sequence[ClientRow],
    *,
    status_filter: str | None = None,
    search_text: str | None = None,
    search_field: str = "search_norm",
) -> list[ClientRow]:
    """Aplica filtros combinados (status + texto de busca).

    Ordem de aplicação:
    1. Filtro de status (se fornecido)
    2. Filtro de texto de busca (se fornecido)

    Args:
        clients: Lista de clientes (dicts)
        status_filter: Status para filtrar (None = sem filtro)
        search_text: Texto para buscar (None = sem filtro)
        search_field: Campo onde buscar (default: 'search_norm')

    Returns:
        Lista filtrada de clientes

    Examples:
        >>> clients = [
        ...     {"id": "1", "status": "Ativo", "search_norm": "acme corp"},
        ...     {"id": "2", "status": "Inativo", "search_norm": "beta corp"},
        ...     {"id": "3", "status": "Ativo", "search_norm": "gamma corp"}
        ... ]
        >>> apply_combined_filters(clients, status_filter="ativo", search_text="acme")
        [{"id": "1", "status": "Ativo", "search_norm": "acme corp"}]
    """
    result = list(clients)

    if status_filter:
        result = filter_by_status(result, status_filter)

    if search_text:
        result = filter_by_search_text(result, search_text, search_field=search_field)

    return result


def extract_unique_status_values(
    clients: Sequence[ClientRow],
    *,
    sort: bool = True,
) -> list[str]:
    """Extrai valores únicos de status dos clientes.

    Args:
        clients: Lista de clientes (dicts com campo 'status')
        sort: Se deve ordenar alfabeticamente (case-insensitive)

    Returns:
        Lista de status únicos (não vazio)

    Examples:
        >>> clients = [
        ...     {"id": "1", "status": "Ativo"},
        ...     {"id": "2", "status": "Inativo"},
        ...     {"id": "3", "status": "Ativo"}
        ... ]
        >>> extract_unique_status_values(clients)
        ['Ativo', 'Inativo']

        >>> extract_unique_status_values([])
        []
    """
    status_map: dict[str, str] = {}

    for client in clients:
        status = str(client.get("status", "")).strip()
        if not status:
            continue

        status_key = status.lower()
        if status_key not in status_map:
            status_map[status_key] = status

    statuses = list(status_map.values())

    if sort:
        statuses.sort(key=str.lower)

    return statuses


def build_status_filter_choices(
    clients: Sequence[ClientRow],
    *,
    include_all_option: bool = True,
    all_option_label: str = "Todos",
) -> list[str]:
    """Constrói lista de opções para filtro de status (combobox/menu).

    Args:
        clients: Lista de clientes
        include_all_option: Se deve incluir opção "Todos" no início
        all_option_label: Label da opção "todos" (default: "Todos")

    Returns:
        Lista de opções para popular combobox/menu

    Examples:
        >>> clients = [{"status": "Ativo"}, {"status": "Inativo"}]
        >>> build_status_filter_choices(clients)
        ['Todos', 'Ativo', 'Inativo']

        >>> build_status_filter_choices(clients, include_all_option=False)
        ['Ativo', 'Inativo']

        >>> build_status_filter_choices([])
        ['Todos']
    """
    statuses = extract_unique_status_values(clients, sort=True)

    if include_all_option:
        return [all_option_label] + statuses

    return statuses


def normalize_status_choice(
    current_choice: str | None,
    available_choices: Sequence[str],
    *,
    all_option_label: str = "Todos",
) -> str:
    """Normaliza escolha de status contra opções disponíveis.

    Resolve case-insensitive e retorna a versão correta ou fallback.

    Args:
        current_choice: Escolha atual do usuário
        available_choices: Opções válidas (ex.: de build_status_filter_choices)
        all_option_label: Label da opção "todos" (default: "Todos")

    Returns:
        Escolha normalizada ou all_option_label se inválida

    Examples:
        >>> normalize_status_choice("ativo", ["Todos", "Ativo", "Inativo"])
        'Ativo'

        >>> normalize_status_choice("invalido", ["Todos", "Ativo", "Inativo"])
        'Todos'

        >>> normalize_status_choice(None, ["Todos", "Ativo"])
        'Todos'
    """
    if not current_choice:
        return all_option_label

    current_norm = current_choice.strip().lower()
    if not current_norm:
        return all_option_label

    # Mapa case-insensitive
    choices_map = {choice.lower(): choice for choice in available_choices}

    return choices_map.get(current_norm, all_option_label)


def can_batch_delete(
    selected_ids: Collection[str],
    *,
    is_trash_screen: bool,
    is_online: bool = True,
    max_items: int | None = None,
) -> bool:
    """Determina se a ação 'excluir em massa' deve ser habilitada.

    Regras:
    - Requer ao menos 1 item selecionado
    - Requer conexão online
    - Respeita limite máximo de itens (se configurado)
    - Funciona tanto na lista principal quanto na lixeira

    Args:
        selected_ids: Coleção de IDs selecionados
        is_trash_screen: Se está na tela de lixeira
        is_online: Se está conectado ao backend
        max_items: Limite máximo de itens para exclusão em massa (None = sem limite)

    Returns:
        True se pode executar exclusão em massa

    Examples:
        >>> can_batch_delete({"1", "2"}, is_trash_screen=False, is_online=True)
        True

        >>> can_batch_delete(set(), is_trash_screen=False, is_online=True)
        False

        >>> can_batch_delete({"1"}, is_trash_screen=False, is_online=False)
        False

        >>> can_batch_delete({"1", "2", "3"}, is_trash_screen=False, is_online=True, max_items=2)
        False

        >>> can_batch_delete({"1", "2"}, is_trash_screen=True, is_online=True)
        True
    """
    if not selected_ids:
        return False

    if not is_online:
        return False

    if max_items is not None and len(selected_ids) > max_items:
        return False

    return True


def can_batch_restore(
    selected_ids: Collection[str],
    *,
    is_trash_screen: bool,
    is_online: bool = True,
) -> bool:
    """Determina se a ação 'restaurar em massa' deve ser habilitada.

    Regras:
    - Requer ao menos 1 item selecionado
    - Requer conexão online
    - Só disponível na tela de lixeira

    Args:
        selected_ids: Coleção de IDs selecionados
        is_trash_screen: Se está na tela de lixeira
        is_online: Se está conectado ao backend

    Returns:
        True se pode executar restauração em massa

    Examples:
        >>> can_batch_restore({"1", "2"}, is_trash_screen=True, is_online=True)
        True

        >>> can_batch_restore({"1", "2"}, is_trash_screen=False, is_online=True)
        False

        >>> can_batch_restore(set(), is_trash_screen=True, is_online=True)
        False

        >>> can_batch_restore({"1"}, is_trash_screen=True, is_online=False)
        False
    """
    if not selected_ids:
        return False

    if not is_online:
        return False

    if not is_trash_screen:
        return False

    return True


def can_batch_export(
    selected_ids: Collection[str],
    *,
    max_items: int | None = None,
) -> bool:
    """Determina se a ação 'exportar em massa' deve ser habilitada.

    Regras:
    - Requer ao menos 1 item selecionado
    - Respeita limite máximo de itens (se configurado)
    - Não depende de conexão online (exportação local)

    Args:
        selected_ids: Coleção de IDs selecionados
        max_items: Limite máximo de itens para exportação (None = sem limite)

    Returns:
        True se pode executar exportação em massa

    Examples:
        >>> can_batch_export({"1", "2"})
        True

        >>> can_batch_export(set())
        False

        >>> can_batch_export({"1", "2", "3"}, max_items=2)
        False

        >>> can_batch_export({"1", "2"}, max_items=10)
        True

        >>> can_batch_export({"1", "2"}, max_items=2)
        True
    """
    if not selected_ids:
        return False

    if max_items is not None and len(selected_ids) > max_items:
        return False

    return True
