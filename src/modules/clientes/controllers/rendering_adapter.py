# -*- coding: utf-8 -*-
"""Rendering adapter headless para conversão de ClienteRow em valores da Treeview.

FASE MS-14: Extração da lógica de rendering da God Class MainScreenFrame.

Este módulo concentra a lógica de "como ClienteRow vira valores/tags para Treeview"
sem dependências de Tkinter/UI.

Responsabilidades:
- Mapear campos de ClienteRow para colunas específicas
- Aplicar mascaramento de colunas ocultas
- Determinar tags visuais (ex.: "has_obs")

NÃO faz:
- Manipular widgets Tkinter/Treeview
- Gerenciar estado de visibilidade (usa o que é passado)
- Persistir configurações
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Mapping, Sequence

if TYPE_CHECKING:
    from src.modules.clientes.viewmodel import ClienteRow


# ============================================================================
# DATA STRUCTURES
# ============================================================================


@dataclass
class RowRenderingContext:
    """Contexto necessário para renderizar uma linha da Treeview.

    Attributes:
        column_order: Ordem das colunas na Treeview (ex.: ["ID", "Razao Social", ...])
        visible_columns: Mapeamento coluna → visível (ex.: {"ID": True, "Nome": False})
    """

    column_order: Sequence[str]
    visible_columns: Mapping[str, bool]


# ============================================================================
# COLUMN MAPPING
# ============================================================================


def _build_column_mapping(row: ClienteRow) -> dict[str, str]:
    """Constrói mapeamento de nome de coluna para valor do ClienteRow.

    Args:
        row: ClienteRow com os dados do cliente

    Returns:
        Dict mapeando nomes de colunas para valores

    Examples:
        >>> row = ClienteRow(id="123", razao_social="Empresa X", ...)
        >>> mapping = _build_column_mapping(row)
        >>> mapping["ID"]
        '123'
        >>> mapping["Razao Social"]
        'Empresa X'
    """
    return {
        "ID": row.id,
        "Razao Social": row.razao_social,
        "CNPJ": row.cnpj,
        "Nome": row.nome,
        "WhatsApp": row.whatsapp,
        "Observacoes": row.observacoes,
        "Status": row.status,
        "Ultima Alteracao": row.ultima_alteracao,
    }


# ============================================================================
# PUBLIC API
# ============================================================================


def build_row_values(row: ClienteRow, ctx: RowRenderingContext) -> tuple[Any, ...]:
    """Constrói tupla de valores para inserção na Treeview.

    Esta função replica a lógica de _row_values_masked do MainScreenFrame,
    mas de forma headless e testável.

    Aplica mascaramento de colunas:
    - Colunas invisíveis (visible_columns[col] == False) retornam string vazia
    - Colunas visíveis retornam o valor mapeado do ClienteRow

    Args:
        row: ClienteRow com os dados do cliente
        ctx: Contexto de renderização (ordem e visibilidade das colunas)

    Returns:
        Tupla de valores na ordem de ctx.column_order

    Examples:
        >>> row = ClienteRow(id="1", razao_social="Empresa", cnpj="12345", ...)
        >>> ctx = RowRenderingContext(
        ...     column_order=["ID", "Razao Social", "CNPJ"],
        ...     visible_columns={"ID": True, "Razao Social": False, "CNPJ": True}
        ... )
        >>> build_row_values(row, ctx)
        ('1', '', '12345')
    """
    # Mapeia colunas para valores do ClienteRow
    mapping = _build_column_mapping(row)

    values: list[str] = []

    # Itera na ordem especificada pelo contexto
    for col in ctx.column_order:
        # Obtém o valor da coluna (ou vazio se não existir)
        value = mapping.get(col, "")

        # Mascara colunas invisíveis
        if not ctx.visible_columns.get(col, True):
            value = ""

        values.append(value)

    return tuple(values)


def build_row_tags(row: ClienteRow) -> tuple[str, ...]:
    """Determina tags visuais para a linha na Treeview.

    Esta função replica a lógica de tags do _render_clientes,
    mas de forma headless e testável.

    Atualmente suporta:
    - "has_obs": Aplicada quando o cliente tem observações não vazias

    Args:
        row: ClienteRow com os dados do cliente

    Returns:
        Tupla de tags para aplicar na linha

    Examples:
        >>> row = ClienteRow(observacoes="Cliente VIP", ...)
        >>> build_row_tags(row)
        ('has_obs',)

        >>> row = ClienteRow(observacoes="", ...)
        >>> build_row_tags(row)
        ()

        >>> row = ClienteRow(observacoes="   ", ...)  # Apenas espaços
        >>> build_row_tags(row)
        ()
    """
    tags: list[str] = []

    # Tag "has_obs" quando há observações não vazias
    if row.observacoes.strip():
        tags.append("has_obs")

    return tuple(tags)


# ============================================================================
# UTILITIES (para extensão futura)
# ============================================================================


def build_rendering_context_from_ui(
    column_order: Sequence[str],
    visible_vars: Mapping[str, Any],  # tk.BooleanVar ou qualquer objeto com .get()
) -> RowRenderingContext:
    """Constrói RowRenderingContext a partir de variáveis da UI.

    Helper para facilitar a criação do contexto a partir de tk.BooleanVar.

    Args:
        column_order: Ordem das colunas
        visible_vars: Dict de coluna → BooleanVar (ou qualquer objeto com .get())

    Returns:
        RowRenderingContext pronto para uso

    Examples:
        >>> from unittest.mock import Mock
        >>> var_id = Mock()
        >>> var_id.get.return_value = True
        >>> var_nome = Mock()
        >>> var_nome.get.return_value = False
        >>> ctx = build_rendering_context_from_ui(
        ...     ["ID", "Nome"],
        ...     {"ID": var_id, "Nome": var_nome}
        ... )
        >>> ctx.visible_columns["ID"]
        True
        >>> ctx.visible_columns["Nome"]
        False
    """
    visible_columns = {col: bool(visible_vars[col].get()) for col in column_order}

    return RowRenderingContext(
        column_order=column_order,
        visible_columns=visible_columns,
    )
