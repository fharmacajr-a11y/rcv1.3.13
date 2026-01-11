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


def build_row_tags(row: ClienteRow, row_index: int = 0) -> tuple[str, ...]:
    """Determina tags visuais para a linha na Treeview.

    Esta função replica a lógica de tags do _render_clientes,
    mas de forma headless e testável.

    Atualmente suporta:
    - "has_obs": Aplicada quando o cliente tem observações não vazias
    - "zebra_odd" / "zebra_even": Para linhas alternadas (zebra striping)
    - "status_<nome>": Tag de cor baseada no status do cliente

    Args:
        row: ClienteRow com os dados do cliente
        row_index: Índice da linha para zebra striping (padrão: 0)

    Returns:
        Tupla de tags para aplicar na linha

    Examples:
        >>> row = ClienteRow(observacoes="Cliente VIP", status="Novo cliente", ...)
        >>> build_row_tags(row, row_index=0)
        ('has_obs', 'zebra_even', 'status_novo_cliente')

        >>> row = ClienteRow(observacoes="", status="", ...)
        >>> build_row_tags(row, row_index=1)
        ('zebra_odd',)

        >>> row = ClienteRow(observacoes="   ", ...)  # Apenas espaços
        >>> build_row_tags(row, row_index=0)
        ('zebra_even',)
    """
    tags: list[str] = []

    # Tag "has_obs" quando há observações não vazias
    if row.observacoes.strip():
        tags.append("has_obs")

    # Zebra striping (linhas alternadas)
    if row_index % 2 == 0:
        tags.append("zebra_even")
    else:
        tags.append("zebra_odd")

    # Tag de status (colorização dinâmica)
    if row.status and row.status.strip():
        # Sanitizar nome do status para usar como tag
        status_tag = _sanitize_status_for_tag(row.status.strip())
        tags.append(status_tag)

    return tuple(tags)


def _sanitize_status_for_tag(status: str) -> str:
    """Converte nome de status em tag válida para Treeview.

    Args:
        status: Nome do status (ex.: "Novo cliente", "Análise da Caixa")

    Returns:
        Tag sanitizada (ex.: "status_novo_cliente", "status_analise_da_caixa")
    """
    # Converter para minúsculas e substituir caracteres especiais
    tag = status.lower()
    tag = tag.replace(" ", "_")
    tag = tag.replace("á", "a").replace("ã", "a").replace("â", "a")
    tag = tag.replace("é", "e").replace("ê", "e")
    tag = tag.replace("í", "i")
    tag = tag.replace("ó", "o").replace("õ", "o").replace("ô", "o")
    tag = tag.replace("ú", "u")
    tag = tag.replace("ç", "c")
    tag = tag.replace("-", "_")
    return f"status_{tag}"


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
