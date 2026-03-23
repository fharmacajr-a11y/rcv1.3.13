# -*- coding: utf-8 -*-
"""Definições de layout e algoritmo de dimensionamento de colunas do módulo Clientes.

Isolado de view.py para:
- facilitar testes do algoritmo sem dependência de Tk/CTk;
- centralizar o conhecimento de layout das colunas em um único lugar.

Sem dependências de UI — pure Python, testável sem display.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Colunas da Treeview (ordem canônica)
# ---------------------------------------------------------------------------

COLUMNS: tuple[str, ...] = (
    "id",
    "razao_social",
    "cnpj",
    "nome",
    "whatsapp",
    "status",
    "observacoes",
    "ultima_alteracao",
)

# ---------------------------------------------------------------------------
# Specs de colunas para layout responsivo
# Estrutura de cada valor: (base_width, min_width, stretch, weight)
#   base_width  — largura base preferida (px)
#   min_width   — largura mínima que nunca deve ser violada (px)
#   stretch     — True = coluna flex (absorve espaço extra proporcionalmente)
#   weight      — proporção do espaço flex (somente quando stretch=True)
#
# NOTA: a entrada "ultima_alteracao" pode ser sobrescrita em runtime por
# ClientesV2Frame._create_treeview(), que calcula a largura ideal com base
# na fonte real do Tk.  O valor abaixo é o fallback/default.
# ---------------------------------------------------------------------------

COLUMN_SPECS_DEFAULTS: dict[str, tuple[int, int, bool, float]] = {
    "id": (70, 60, False, 0.0),
    "razao_social": (520, 340, True, 0.80),  # FLEX principal  (80 % do espaço extra)
    "cnpj": (190, 170, False, 0.0),
    "nome": (220, 165, True, 0.20),  # FLEX secundária (20 % do espaço extra)
    "whatsapp": (150, 135, False, 0.0),
    "status": (210, 180, False, 0.0),
    "observacoes": (135, 110, False, 0.0),
    "ultima_alteracao": (215, 180, False, 0.0),  # Sobrescrita em runtime (ver nota acima)
}


# ---------------------------------------------------------------------------
# Algoritmo puro de cálculo de larguras
# ---------------------------------------------------------------------------


def compute_column_widths(
    tree_width: int,
    column_specs: dict[str, tuple[int, int, bool, float]],
) -> tuple[dict[str, int], bool]:
    """Calcula larguras de colunas sem efeito colateral (algoritmo puro).

    Algoritmo:
    1) Começa com minwidth de TODAS as colunas
    2) Calcula espaço extra disponível (tree_width - soma_minwidths)
    3) Completa colunas fixas até base_width (opcional)
    4) Distribui restante entre colunas flex por weight

    Args:
        tree_width: Largura total disponível (pixels).
        column_specs: Dict ``{col_id: (base_width, min_width, stretch, weight)}``.

    Returns:
        Tuple ``(widths_dict, is_clamped)`` onde:

        - *widths_dict*: ``{col_id: largura calculada em pixels}``
        - *is_clamped*: ``True`` se ``tree_width <= total_min``
          (todos os valores são os mínimos — Treeview vai clipar)
    """
    cols = list(column_specs.keys())
    specs = column_specs

    # 1) Começa pelos mínimos
    widths: dict[str, int] = {c: int(specs[c][1]) for c in cols}
    total_min = sum(widths.values())

    if tree_width <= total_min:
        return widths, True

    extra = tree_width - total_min

    # 2) Opcional: completar colunas fixas até base_width
    fixed_cols = [c for c in cols if not specs[c][2]]  # stretch=False
    for c in fixed_cols:
        base_w, _, _, _ = specs[c]
        need = max(0, int(base_w) - widths[c])
        add = min(extra, need)
        widths[c] += add
        extra -= add
        if extra <= 0:
            break

    # 3) Distribuir restante nas colunas flex por weight
    flex_cols = [c for c in cols if specs[c][2]]  # stretch=True
    if flex_cols and extra > 0:
        total_weight = sum(float(specs[c][3]) for c in flex_cols) or float(len(flex_cols))
        remaining = extra
        for i, c in enumerate(flex_cols):
            w = float(specs[c][3]) or 1.0
            if i == len(flex_cols) - 1:
                # Joga o resto na última para fechar certinho
                add = remaining
            else:
                add = int(extra * (w / total_weight))
                add = min(add, remaining)
            widths[c] += add
            remaining -= add

    return widths, False
