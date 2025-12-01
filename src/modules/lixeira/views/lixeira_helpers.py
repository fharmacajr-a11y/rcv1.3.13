# -*- coding: utf-8 -*-
"""
Helpers puros para lixeira.py - Lógica testável sem Tkinter.

Este módulo contém funções puras extraídas da tela da Lixeira para permitir
testes unitários sem dependências de GUI.
"""

from __future__ import annotations

from typing import Any


def format_trash_status_text(item_count: int) -> str:
    """
    Formata texto de status da lixeira baseado na quantidade de itens.

    Args:
        item_count: Número de itens na lixeira

    Returns:
        str: Texto formatado para exibição

    Examples:
        >>> format_trash_status_text(0)
        '0 item(ns) na lixeira'
        >>> format_trash_status_text(1)
        '1 item(ns) na lixeira'
        >>> format_trash_status_text(42)
        '42 item(ns) na lixeira'
    """
    return f"{item_count} item(ns) na lixeira"


def calculate_trash_button_states(
    has_selection: bool,
    is_busy: bool = False,
) -> dict[str, bool]:
    """
    Calcula estados de botões da lixeira baseado em seleção e estado de busy.

    Args:
        has_selection: Se há pelo menos um item selecionado
        is_busy: Se a tela está em estado de carregamento/processamento

    Returns:
        dict com chaves:
            - restore_enabled (bool): Se botão "Restaurar" está habilitado
            - purge_enabled (bool): Se botão "Apagar" está habilitado
            - refresh_enabled (bool): Se botão "Refresh" está habilitado
            - close_enabled (bool): Se botão "Fechar" está habilitado

    Examples:
        >>> calculate_trash_button_states(has_selection=False, is_busy=False)
        {'restore_enabled': False, 'purge_enabled': False, 'refresh_enabled': True, 'close_enabled': True}
        >>> calculate_trash_button_states(has_selection=True, is_busy=False)
        {'restore_enabled': True, 'purge_enabled': True, 'refresh_enabled': True, 'close_enabled': True}
        >>> calculate_trash_button_states(has_selection=True, is_busy=True)
        {'restore_enabled': False, 'purge_enabled': False, 'refresh_enabled': False, 'close_enabled': False}
        >>> calculate_trash_button_states(has_selection=False, is_busy=True)
        {'restore_enabled': False, 'purge_enabled': False, 'refresh_enabled': False, 'close_enabled': False}
    """
    if is_busy:
        # Durante busy, todos os botões desabilitados
        return {
            "restore_enabled": False,
            "purge_enabled": False,
            "refresh_enabled": False,
            "close_enabled": False,
        }

    # Normal (não-busy): restaurar/apagar dependem de seleção
    return {
        "restore_enabled": has_selection,
        "purge_enabled": has_selection,
        "refresh_enabled": True,
        "close_enabled": True,
    }


def validate_selection_for_action(
    selected_count: int,
    action_name: str = "ação",
) -> tuple[bool, str]:
    """
    Valida se há seleção suficiente para uma ação e retorna mensagem apropriada.

    Args:
        selected_count: Número de itens selecionados
        action_name: Nome da ação para mensagem (ex: "restaurar", "apagar")

    Returns:
        tuple (is_valid, message):
            - is_valid (bool): True se seleção é válida (> 0)
            - message (str): Mensagem de erro (vazia se válido)

    Examples:
        >>> validate_selection_for_action(0, "restaurar")
        (False, 'Selecione pelo menos um registro para restaurar.')
        >>> validate_selection_for_action(1, "restaurar")
        (True, '')
        >>> validate_selection_for_action(5, "apagar")
        (True, '')
        >>> validate_selection_for_action(0)
        (False, 'Selecione pelo menos um registro para ação.')
    """
    if selected_count <= 0:
        return False, f"Selecione pelo menos um registro para {action_name}."
    return True, ""


def extract_field_value(obj: Any, *field_names: str) -> Any:
    """
    Extrai valor de um campo de objeto ou dict, tentando múltiplos nomes.

    Útil para compatibilidade com diferentes estruturas de dados (objetos Supabase,
    dicts, etc.) que podem ter nomes de campos variados.

    Args:
        obj: Objeto ou dict do qual extrair o valor
        *field_names: Nomes de campos a tentar (em ordem de prioridade)

    Returns:
        Any: Primeiro valor não-None encontrado, ou None se nenhum campo existe

    Examples:
        >>> class Cliente:
        ...     def __init__(self):
        ...         self.razao_social = "Empresa X"
        >>> extract_field_value(Cliente(), "razao_social")
        'Empresa X'
        >>> extract_field_value({"nome": "João"}, "nome", "name")
        'João'
        >>> extract_field_value({"name": "John"}, "nome", "name")
        'John'
        >>> extract_field_value({}, "nome", "name") is None
        True
        >>> extract_field_value(None, "campo") is None
        True
    """
    if obj is None:
        return None

    for name in field_names:
        # Tentar como atributo
        try:
            if hasattr(obj, name):
                val = getattr(obj, name)
                if val is not None:
                    return val
        except Exception:  # noqa: S110  # nosec B110 - Safe: Fallback é retornar None
            # hasattr ou getattr podem falhar com properties quebradas
            pass

        # Tentar como dict key
        if isinstance(obj, dict) and name in obj:
            val = obj.get(name)
            if val is not None:
                return val

    return None


def format_confirmation_message(
    action: str,
    count: int,
    is_destructive: bool = False,
) -> str:
    """
    Formata mensagem de confirmação para ações da lixeira.

    Args:
        action: Nome da ação (ex: "Restaurar", "Apagar")
        count: Número de registros afetados
        is_destructive: Se True, adiciona aviso de ação irreversível

    Returns:
        str: Mensagem de confirmação formatada

    Examples:
        >>> format_confirmation_message("Restaurar", 1, False)
        'Restaurar 1 registro(s) para a lista principal?'
        >>> format_confirmation_message("Restaurar", 5, False)
        'Restaurar 5 registro(s) para a lista principal?'
        >>> msg = format_confirmation_message("Apagar", 3, True)
        >>> "APAGAR DEFINITIVAMENTE" in msg
        True
        >>> "não pode ser desfeita" in msg
        True
    """
    if is_destructive:
        return f"APAGAR DEFINITIVAMENTE {count} registro(s)? " "Esta ação não pode ser desfeita."

    return f"{action} {count} registro(s) para a lista principal?"


def format_progress_text(current: int, total: int, action: str = "Apagando") -> str:
    """
    Formata texto de progresso para operações em lote.

    Args:
        current: Número de itens processados
        total: Total de itens a processar
        action: Verbo da ação em andamento

    Returns:
        str: Texto formatado para exibição

    Examples:
        >>> format_progress_text(0, 10)
        'Apagando 0/10 registro(s)... Aguarde.'
        >>> format_progress_text(5, 10)
        'Apagando 5/10 registro(s)... Aguarde.'
        >>> format_progress_text(10, 10)
        'Apagando 10/10 registro(s)... Aguarde.'
        >>> format_progress_text(3, 7, "Restaurando")
        'Restaurando 3/7 registro(s)... Aguarde.'
    """
    return f"{action} {current}/{total} registro(s)... Aguarde."


def format_result_message(
    success_count: int,
    error_list: list[tuple[int, str]] | None = None,
    action_past: str = "apagado(s)",
) -> tuple[str, str, bool]:
    """
    Formata mensagem de resultado após operação em lote.

    Args:
        success_count: Número de itens processados com sucesso
        error_list: Lista de tuplas (id, erro) para falhas
        action_past: Verbo no particípio (ex: "restaurado(s)", "apagado(s)")

    Returns:
        tuple (title, message, is_error):
            - title (str): Título da mensagem
            - message (str): Mensagem completa
            - is_error (bool): True se houve erros

    Examples:
        >>> title, msg, is_err = format_result_message(5, None, "restaurado(s)")
        >>> title
        'Pronto'
        >>> msg
        '5 registro(s) restaurado(s).'
        >>> is_err
        False
        >>> title, msg, is_err = format_result_message(3, [(1, "Erro X"), (2, "Erro Y")], "apagado(s)")
        >>> title
        'Falha parcial'
        >>> "3 apagado(s)" in msg
        True
        >>> "ID 1: Erro X" in msg
        True
        >>> is_err
        True
    """
    errors = error_list or []

    if errors:
        formatted_errors = [f"ID {err_id}: {err_msg}" for err_id, err_msg in errors]
        error_text = "\n".join(formatted_errors)
        message = f"{success_count} {action_past}, erros:\n{error_text}"
        return "Falha parcial", message, True

    message = f"{success_count} registro(s) {action_past}."
    return "Pronto", message, False


# ==============================================================================
# FASE 02: Singleton Management, Progress Dialog, Data Transformation
# ==============================================================================


def should_open_new_trash_window(window_exists: bool) -> bool:
    """
    Determina se deve criar nova janela da lixeira ou reusar existente.

    Args:
        window_exists: Se já existe uma janela aberta da lixeira

    Returns:
        bool: True se deve criar nova janela, False se deve reusar existente

    Examples:
        >>> should_open_new_trash_window(window_exists=False)
        True
        >>> should_open_new_trash_window(window_exists=True)
        False
    """
    return not window_exists


def should_refresh_trash_window(
    window_exists: bool,
    has_pending_changes: bool = False,
) -> bool:
    """
    Determina se deve recarregar a janela da lixeira.

    Args:
        window_exists: Se a janela está aberta
        has_pending_changes: Se há mudanças pendentes que requerem refresh

    Returns:
        bool: True se deve fazer refresh

    Examples:
        >>> should_refresh_trash_window(window_exists=False)
        False
        >>> should_refresh_trash_window(window_exists=True)
        True
        >>> should_refresh_trash_window(window_exists=True, has_pending_changes=True)
        True
        >>> should_refresh_trash_window(window_exists=False, has_pending_changes=True)
        False
    """
    return window_exists


def calculate_progress_percentage(current: int, total: int) -> float:
    """
    Calcula percentual de progresso para operação em lote.

    Args:
        current: Número de itens processados
        total: Total de itens

    Returns:
        float: Percentual de 0.0 a 100.0

    Examples:
        >>> calculate_progress_percentage(0, 10)
        0.0
        >>> calculate_progress_percentage(5, 10)
        50.0
        >>> calculate_progress_percentage(10, 10)
        100.0
        >>> calculate_progress_percentage(3, 0)
        0.0
        >>> calculate_progress_percentage(5, 3)
        100.0
    """
    if total <= 0:
        return 0.0
    if current >= total:
        return 100.0
    return (current / total) * 100.0


def normalize_trash_row_data(
    row: Any,
    field_mappings: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    """
    Normaliza dados de uma row da lixeira para estrutura consistente.

    Extrai campos de objetos/dicts usando múltiplos nomes possíveis.

    Args:
        row: Row do Supabase (objeto ou dict)
        field_mappings: Mapeamento de campo -> lista de nomes possíveis
                       Se None, usa mapeamento padrão

    Returns:
        dict com campos normalizados: id, razao_social, cnpj, nome,
        whatsapp, obs, ultima_alteracao, ultima_por

    Examples:
        >>> row = {"id": 1, "razao_social": "Empresa X", "cnpj": "12345"}
        >>> result = normalize_trash_row_data(row)
        >>> result["id"]
        1
        >>> result["razao_social"]
        'Empresa X'
        >>> result["cnpj"]
        '12345'
    """
    if field_mappings is None:
        field_mappings = {
            "id": ["id"],
            "razao_social": ["razao_social"],
            "cnpj": ["cnpj"],
            "nome": ["nome"],
            "whatsapp": ["whatsapp", "numero"],
            "obs": ["obs", "observacoes", "Observacoes"],
            "ultima_alteracao": ["ultima_alteracao", "updated_at"],
            "ultima_por": ["ultima_por"],
        }

    result: dict[str, Any] = {}
    for key, possible_names in field_mappings.items():
        result[key] = extract_field_value(row, *possible_names) or ""

    return result


def format_author_initial(
    author_id: str,
    initials_mapping: dict[str, str] | None = None,
    display_name_fallback: str = "",
) -> str:
    """
    Formata inicial do autor para exibição.

    Args:
        author_id: ID do autor (user_id do Supabase)
        initials_mapping: Mapeamento de user_id -> sigla
        display_name_fallback: Nome de exibição se não houver mapping

    Returns:
        str: Inicial maiúscula do autor (1 caractere)

    Examples:
        >>> format_author_initial("user-123", {"user-123": "JD"})
        'J'
        >>> format_author_initial("user-456", {}, "John Doe")
        'J'
        >>> format_author_initial("user-789", {})
        ''
        >>> format_author_initial("")
        ''
    """
    if not author_id:
        return ""

    # Tentar mapping primeiro
    if initials_mapping and author_id in initials_mapping:
        alias = initials_mapping[author_id]
        if alias:
            return (alias[:1] or "").upper()

    # Fallback para display_name
    if display_name_fallback:
        return (display_name_fallback[:1] or "").upper()

    # Fallback para primeiro char do ID
    return (author_id[:1] or "").upper()


def format_timestamp_with_author(
    timestamp: str,
    author_initial: str,
) -> str:
    """
    Formata timestamp com inicial do autor.

    Args:
        timestamp: Timestamp já formatado (ex: "28/11/2025 18:30")
        author_initial: Inicial do autor (1 caractere)

    Returns:
        str: Timestamp formatado com autor (ex: "28/11/2025 18:30 (J)")

    Examples:
        >>> format_timestamp_with_author("28/11/2025 18:30", "J")
        '28/11/2025 18:30 (J)'
        >>> format_timestamp_with_author("28/11/2025 18:30", "")
        '28/11/2025 18:30'
        >>> format_timestamp_with_author("", "J")
        ''
    """
    if not timestamp:
        return ""

    if author_initial:
        return f"{timestamp} ({author_initial})"

    return timestamp


def parse_error_list_for_display(
    error_list: Any,
) -> list[str]:
    """
    Converte lista de erros em formato para exibição.

    Args:
        error_list: Lista/tupla de erros em formato variado:
                   - list[tuple[int, str]]: [(id, msg), ...]
                   - list[Any]: [item, ...]
                   - str: mensagem única

    Returns:
        list[str]: Lista de strings formatadas para exibição

    Examples:
        >>> parse_error_list_for_display([(1, "Erro A"), (2, "Erro B")])
        ['ID 1: Erro A', 'ID 2: Erro B']
        >>> parse_error_list_for_display(["Erro genérico"])
        ['Erro genérico']
        >>> parse_error_list_for_display("Erro único")
        ['Erro único']
        >>> parse_error_list_for_display([])
        []
        >>> parse_error_list_for_display(None)
        []
    """
    if not error_list:
        return []

    if isinstance(error_list, str):
        return [error_list]

    if not isinstance(error_list, (list, tuple)):
        return [str(error_list)]

    formatted = []
    for item in error_list:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            # Formato (id, msg)
            formatted.append(f"ID {item[0]}: {item[1]}")
        else:
            formatted.append(str(item))

    return formatted
