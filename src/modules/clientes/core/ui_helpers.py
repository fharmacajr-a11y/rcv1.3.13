"""Helpers puros para lógica de UI da tela principal de clientes.

Este módulo contém funções puras extraídas de main_screen.py para facilitar
testes e reduzir acoplamento com Tkinter.
"""

from __future__ import annotations

from collections.abc import Collection
from typing import Any, Literal, Protocol


class ClientWithCreatedAt(Protocol):
    """Protocol para objetos cliente que possuem campo created_at.

    Permite duck typing para dicts e objetos com o campo created_at.
    """

    def get(self, key: str, default: Any = None) -> Any:
        """Método get para acesso estilo dict."""
        ...


ORDER_LABEL_RAZAO = "Razão Social (A→Z)"
ORDER_LABEL_RAZAO_DESC = "Razão Social (Z→A)"
ORDER_LABEL_CNPJ = "CNPJ (A→Z)"
ORDER_LABEL_NOME = "Nome (A→Z)"
ORDER_LABEL_NOME_DESC = "Nome (Z→A)"
ORDER_LABEL_ID_ASC = "ID (1→9)"
ORDER_LABEL_ID_DESC = "ID (9→1)"
ORDER_LABEL_UPDATED_RECENT = "Última Alteração (+)"
ORDER_LABEL_UPDATED_OLD = "Última Alteração (-)"
ORDER_LABEL_TELEFONE_DDD_ASC = "WhatsApp (DDD - → +)"
ORDER_LABEL_TELEFONE_DDD_DESC = "WhatsApp (DDD + → -)"

ORDER_LABEL_ALIASES = {
    # ASCII-arrow variants e sem-acento (prefs antigas, compat com toolbar pre-unicode)
    "Razao Social (A->Z)": ORDER_LABEL_RAZAO,
    "CNPJ (A->Z)": ORDER_LABEL_CNPJ,
    "Nome (A->Z)": ORDER_LABEL_NOME,
    "Nome (Z->A)": ORDER_LABEL_NOME_DESC,
    "Ultima Alteracao (mais recente)": ORDER_LABEL_UPDATED_RECENT,
    "Ultima Alteracao (mais antiga)": ORDER_LABEL_UPDATED_OLD,
    "ID (1->9)": ORDER_LABEL_ID_ASC,
    "ID (9->1)": ORDER_LABEL_ID_DESC,
    # Aliases legacy com símbolo de seta alternativo (↑↓)
    "ID (↑)": ORDER_LABEL_ID_ASC,
    "ID (↓)": ORDER_LABEL_ID_DESC,
    "Última Alteração ↓": ORDER_LABEL_UPDATED_RECENT,
    "Última Alteração ↑": ORDER_LABEL_UPDATED_OLD,
    # Alias com hífen em vez de seta unicode (labels de toolbar intermediário)
    "ID (1-9)": ORDER_LABEL_ID_ASC,
    "ID (9-1)": ORDER_LABEL_ID_DESC,
    # Compat case-variant (toolbar antigo gravava MAIS RECENTE/ANTIGA em maiúsculas)
    "Última Alteração (MAIS RECENTE)": ORDER_LABEL_UPDATED_RECENT,
    "Última Alteração (MAIS ANTIGA)": ORDER_LABEL_UPDATED_OLD,
    # Aliases antigos "Telefone" → label atual "WhatsApp" (prefs salvas pelo usuário)
    "Telefone (DDD menor→maior)": ORDER_LABEL_TELEFONE_DDD_ASC,
    "Telefone (DDD menor->maior)": ORDER_LABEL_TELEFONE_DDD_ASC,
    "Telefone (DDD maior→menor)": ORDER_LABEL_TELEFONE_DDD_DESC,
    "Telefone (DDD maior->menor)": ORDER_LABEL_TELEFONE_DDD_DESC,
    # ASCII-arrow variant dos labels WhatsApp atuais
    "WhatsApp (DDD menor->maior)": ORDER_LABEL_TELEFONE_DDD_ASC,
    "WhatsApp (DDD maior->menor)": ORDER_LABEL_TELEFONE_DDD_DESC,
    # Labels canônicos antigos (antes da renomeação visual)
    "Última Alteração (mais recente)": ORDER_LABEL_UPDATED_RECENT,
    "Última Alteração (mais antiga)": ORDER_LABEL_UPDATED_OLD,
    "WhatsApp (DDD menor→maior)": ORDER_LABEL_TELEFONE_DDD_ASC,
    "WhatsApp (DDD maior→menor)": ORDER_LABEL_TELEFONE_DDD_DESC,
}

DEFAULT_ORDER_LABEL = ORDER_LABEL_RAZAO

ORDER_CHOICES: dict[str, tuple[str | None, bool]] = {
    ORDER_LABEL_RAZAO: ("razao_social", False),
    ORDER_LABEL_RAZAO_DESC: ("razao_social", True),
    ORDER_LABEL_CNPJ: ("cnpj", False),
    # Nome: campos dedicados garantem vazios sempre no fim em ambas as direções
    ORDER_LABEL_NOME: ("nome_asc", False),
    ORDER_LABEL_NOME_DESC: ("nome_desc", False),
    ORDER_LABEL_ID_ASC: ("id", False),
    ORDER_LABEL_ID_DESC: ("id", True),
    ORDER_LABEL_UPDATED_RECENT: ("ultima_alteracao", True),  # True = mais recente primeiro
    ORDER_LABEL_UPDATED_OLD: ("ultima_alteracao", False),  # False = mais antiga primeiro
    # Telefone: campos dedicados garantem vazios sempre no fim
    ORDER_LABEL_TELEFONE_DDD_ASC: ("telefone_ddd_asc", False),
    ORDER_LABEL_TELEFONE_DDD_DESC: ("telefone_ddd_desc", False),
}


FILTER_LABEL_TODOS = "Todos"

DEFAULT_FILTER_LABEL = FILTER_LABEL_TODOS

FILTER_LABEL_ALIASES: dict[str, str] = {
    "todos": FILTER_LABEL_TODOS,
    "TODOS": FILTER_LABEL_TODOS,
    "all": FILTER_LABEL_TODOS,
    "All": FILTER_LABEL_TODOS,
    "ALL": FILTER_LABEL_TODOS,
}


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
