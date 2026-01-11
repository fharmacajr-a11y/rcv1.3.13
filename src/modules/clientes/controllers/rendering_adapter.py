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


def build_row_tags(row: ClienteRow, row_index: int | None = None) -> tuple[str, ...]:
    """Determina tags visuais para a linha na Treeview.

    Esta função replica a lógica de tags do _render_clientes,
    mas de forma headless e testável.

    OTIMIZAÇÃO: Para evitar loops extras sobre os dados, o zebra striping
    é aplicado no momento do build das tags (passando row_index).
    Tags de status têm prioridade sobre zebra.

    Tags suportadas:
    - "has_obs": Aplicada quando o cliente tem observações não vazias
    - "status_novo_cliente": Verde (cliente novo)
    - "status_sem_resposta": Laranja (sem resposta)
    - "status_analise": Azul (em análise)
    - "status_aguardando": Cinza (aguardando documento/pagamento)
    - "status_finalizado": Verde (finalizado)
    - "status_followup": Roxo (follow-up)
    - "zebra_even"/"zebra_odd": Linhas alternadas (quando não há status)

    Args:
        row: ClienteRow com os dados do cliente
        row_index: Índice da linha (opcional, para zebra striping)

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

    # Tags de status dinâmico (badges visuais)
    status_tag = _get_status_tag(row.status)
    if status_tag:
        tags.append(status_tag)
    elif row_index is not None:
        # Zebra striping apenas se NÃO tiver tag de status (status tem prioridade visual)
        zebra_tag = "zebra_even" if row_index % 2 == 0 else "zebra_odd"
        tags.append(zebra_tag)

    return tuple(tags)


def _get_status_tag(status_text: str) -> str | None:
    """Retorna a tag de status apropriada baseado no texto do status.

    Mapeamento de status para tags visuais (cores):
    - "Novo cliente" → status_novo_cliente (verde)
    - "Sem resposta" → status_sem_resposta (laranja)
    - "Análise..." → status_analise (azul)
    - "Aguardando..." → status_aguardando (cinza)
    - "Finalizado" → status_finalizado (verde)
    - "Follow-up..." → status_followup (roxo)

    Args:
        status_text: Texto do status do cliente

    Returns:
        Nome da tag de status ou None se não houver match
    """
    if not status_text:
        return None

    status_lower = status_text.lower().strip()

    # Mapeamento de status para tags
    if "novo cliente" in status_lower:
        return "status_novo_cliente"
    elif "sem resposta" in status_lower:
        return "status_sem_resposta"
    elif "análise" in status_lower or "analise" in status_lower:
        return "status_analise"
    elif "aguardando" in status_lower:
        return "status_aguardando"
    elif "finalizado" in status_lower:
        return "status_finalizado"
    elif "follow-up" in status_lower or "follow up" in status_lower or "followup" in status_lower:
        return "status_followup"

    return None


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
