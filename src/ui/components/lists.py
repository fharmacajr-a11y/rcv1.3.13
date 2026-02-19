# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import re
import tkinter as tk
import tkinter.font as tkfont
from typing import Any, Callable

from src.ui.ctk_config import ctk

from src.config.constants import (
    COL_CNPJ_WIDTH,
    COL_ID_WIDTH,
    COL_NOME_MINWIDTH,
    COL_NOME_WIDTH,
    COL_OBS_WIDTH,
    COL_RAZAO_MINWIDTH,
    COL_RAZAO_WIDTH,
    COL_STATUS_WIDTH,
    COL_ULTIMA_WIDTH,
    COL_WHATSAPP_WIDTH,
)

OBS_FG = "#0d6efd"

# Style name exclusivo para Treeview de clientes (não afeta outras telas)
CLIENTS_TREEVIEW_STYLE = "Clientes.Treeview"

# Configuração de alinhamento por coluna (facilita customização)
# 'w' = esquerda, 'center' = centro, 'e' = direita
# Razão Social e Nome: CENTRALIZADOS
# WhatsApp: ALINHADO À ESQUERDA (para visual mais próximo à esquerda)
# Status e Observações: CENTRALIZADOS (conforme solicitado)
CLIENTS_COL_ANCHOR: dict[str, str] = {
    "ID": "center",
    "Razao Social": "center",
    "CNPJ": "center",
    "Nome": "center",
    "WhatsApp": "w",  # Alinhado à esquerda
    "Observacoes": "center",  # Centralizado
    "Status": "center",  # Centralizado
    "Ultima Alteracao": "center",
}

# Pesos para distribuição proporcional das colunas flex
# Apenas Razão Social e Nome são flex (crescem com a janela)
# Razão Social=7 (maior), Nome=3
FLEX_COLUMN_WEIGHTS: dict[str, int] = {
    "Razao Social": 7,
    "Nome": 3,
}

# Delta de luminosidade para zebra (valores maiores = mais contraste)
# Aumentado para 0.18 para zebra BEM visível (cinza escuro)
ZEBRA_LIGHTNESS_DELTA_LIGHT = -0.18  # Tema claro: escurecer odd (cinza bem visível)
ZEBRA_LIGHTNESS_DELTA_DARK = 0.18  # Tema escuro: clarear odd

# Regex para colapsar espaços múltiplos
_MULTI_SPACE_RE = re.compile(r"\s+")

logger = logging.getLogger(__name__)
log = logger

__all__ = [
    "create_clients_treeview",
    "CLIENTS_COL_ANCHOR",
    "normalize_cell_text",
    "reapply_clientes_treeview_tags",
]


def reapply_clientes_treeview_tags(
    tree: Any,
    even_bg: str,
    odd_bg: str,
    fg: str = "",
) -> None:
    """Reaplica tags de zebra (even/odd) na Treeview do módulo Clientes.

    Esta função é idempotente e pode ser chamada sempre que o tema muda.

    MICROFASE 31: Simplificado - apenas tags, sem Style legado.

    Args:
        tree: Instância da Treeview (CTkTreeview)
        even_bg: Cor de fundo para linhas pares
        odd_bg: Cor de fundo para linhas ímpares
        fg: Cor de texto para ambas (opcional)
    """
    try:
        if fg:
            tree.tag_configure("even", background=even_bg, foreground=fg)
            tree.tag_configure("odd", background=odd_bg, foreground=fg)
        else:
            tree.tag_configure("even", background=even_bg)
            tree.tag_configure("odd", background=odd_bg)
        log.debug("Tags de zebra reaplicadas na Treeview")
    except Exception:
        log.exception("Erro ao reaplicar tags de zebra")


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Converte cor hex para RGB."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    """Converte RGB para hex."""
    return f"#{r:02x}{g:02x}{b:02x}"


def normalize_cell_text(value: Any) -> str:
    """Normaliza texto para exibição em célula de Treeview.

    Remove quebras de linha e espaços múltiplos para evitar que o texto
    quebre em duas linhas ou apareça cortado.

    Args:
        value: Valor a normalizar (pode ser None, str, ou qualquer tipo)

    Returns:
        String normalizada (sem \\n, \\r, espaços múltiplos)

    Examples:
        >>> normalize_cell_text("Empresa\\nLtda")
        'Empresa Ltda'
        >>> normalize_cell_text("  Múltiplos   espaços  ")
        'Múltiplos espaços'
        >>> normalize_cell_text(None)
        ''
    """
    if value is None:
        return ""
    text = str(value)
    # Substituir quebras de linha por espaço
    text = text.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    # Colapsar espaços múltiplos
    text = _MULTI_SPACE_RE.sub(" ", text)
    return text.strip()


def _get_luminance(hex_color: str) -> float:
    """Calcula luminância de uma cor hex (0.0 = escuro, 1.0 = claro)."""
    try:
        r, g, b = _hex_to_rgb(hex_color)
        # Fórmula de luminância relativa (ITU-R BT.709)
        return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
    except Exception:
        return 0.5  # fallback neutro


def _adjust_lightness(hex_color: str, delta: float) -> str:
    """Ajusta lightness de uma cor hex. delta positivo = mais claro."""
    try:
        r, g, b = _hex_to_rgb(hex_color)
        # Ajuste simples: aumentar/diminuir cada componente proporcionalmente
        factor = 1.0 + delta
        r = max(0, min(255, int(r * factor)))
        g = max(0, min(255, int(g * factor)))
        b = max(0, min(255, int(b * factor)))
        return _rgb_to_hex(r, g, b)
    except Exception:
        return hex_color  # retorna original se falhar


def _get_zebra_colors() -> tuple[str, str]:
    """Calcula cores para zebra striping baseado no modo CTk atual.

    MICROFASE 31: Substituiu _configure_clients_treeview_style (que usava Style legado).

    Returns:
        Tupla (even_bg, odd_bg) com cores de fundo para zebra striping.
    """
    # Detectar modo atual do CTk
    try:
        appearance_mode = ctk.get_appearance_mode()  # "Light" ou "Dark"
        is_dark = appearance_mode == "Dark"
    except Exception:
        is_dark = False  # fallback para modo claro

    # Cores base para zebra striping
    if is_dark:
        # Modo escuro: fundo escuro + alternado mais claro
        even_bg = "#2b2b2b"  # cinza escuro
        odd_bg = "#3c3c3c"  # cinza levemente mais claro
    else:
        # Modo claro: fundo branco + alternado cinza
        even_bg = "#ffffff"  # branco
        odd_bg = "#e8e8e8"  # cinza claro

    return even_bg, odd_bg


def create_clients_treeview(
    parent: tk.Misc,
    *,
    on_double_click: Callable[[Any], Any] | None,
    on_select: Callable[[Any], Any] | None,
    on_delete: Callable[[Any], Any] | None,
    on_click: Callable[[Any], Any] | None,
) -> Any:
    """Create the main clients Treeview configured with column widths and bindings.

    MICROFASE 31: Migrado para CTkTreeview (ZERO widgets legados).
    """
    # Definição das colunas: (key, heading, width, minwidth, stretch)
    # FIXAS: ID, CNPJ, WhatsApp, Observações, Status, Última Alteração
    # FLEX: Razão Social, Nome (crescem com a janela)
    columns = (
        ("ID", "ID", COL_ID_WIDTH, 45, False),
        ("Razao Social", "Razão Social", COL_RAZAO_WIDTH, COL_RAZAO_MINWIDTH, True),
        ("CNPJ", "CNPJ", COL_CNPJ_WIDTH, 120, False),
        ("Nome", "Nome", COL_NOME_WIDTH, COL_NOME_MINWIDTH, True),
        ("WhatsApp", "WhatsApp", COL_WHATSAPP_WIDTH, 120, False),
        ("Observacoes", "Observações", COL_OBS_WIDTH, 140, False),
        ("Status", "Status", COL_STATUS_WIDTH, 180, False),
        ("Ultima Alteracao", "Última Alteração", COL_ULTIMA_WIDTH, 170, False),
    )

    # Importar CTkTreeview (biblioteca vendorizada, API-compatível com Treeview)
    try:
        from src.third_party.ctktreeview import CTkTreeview  # MICROFASE 32: Vendor
    except ImportError:
        log.error("CTkTreeview vendor não encontrado em src/third_party/ctktreeview")
        raise

    # Calcular cores para zebra striping baseado no modo CTk
    even_bg, odd_bg = _get_zebra_colors()

    # Criar CTkTreeview (substitui Treeview legado)
    tree = CTkTreeview(
        parent,
        columns=[c[0] for c in columns],
        show="headings",
    )

    # Configurar headings (maioria centralizado, WhatsApp alinhado à esquerda)
    for key, heading, _, _, _ in columns:
        heading_anchor = "w" if key == "WhatsApp" else "center"
        tree.heading(key, text=heading, anchor=heading_anchor)

    # Configurar colunas com larguras, minwidths e alinhamento
    for key, _, width, minwidth, can_stretch in columns:
        anchor = CLIENTS_COL_ANCHOR.get(key, "center")
        tree.column(key, width=width, minwidth=minwidth, anchor=anchor, stretch=can_stretch)

    # Bloquear resize manual das colunas pelo usuário
    def _block_header_resize(event: Any) -> str | None:
        if tree.identify_region(event.x, event.y) == "separator":
            return "break"
        return None

    tree.bind("<Button-1>", _block_header_resize, add="+")

    # Configurar tags de zebra striping
    try:
        tree.tag_configure("even", background=even_bg)
        tree.tag_configure("odd", background=odd_bg)
    except Exception as exc:
        log.debug("Falha ao configurar tags de zebra: %s", exc)

    # Configurar tag "has_obs" (negrito + cor azul)
    try:
        default_font = tkfont.nametofont("TkDefaultFont")
        font_family = default_font.cget("family")
        font_size = default_font.cget("size")
        new_size = font_size + 1 if font_size > 0 else 11
        bold_font = tkfont.Font(family=font_family, size=new_size, weight="bold")
        tree.tag_configure("has_obs", font=bold_font, foreground=OBS_FG)
    except Exception as exc:
        log.debug("Falha ao configurar fonte em negrito: %s", exc)

    # Bindings de eventos
    if on_double_click:
        tree.bind("<Double-1>", on_double_click, add="+")
    if on_select:
        tree.bind("<<TreeviewSelect>>", on_select, add="+")
    if on_delete:
        tree.bind("<Delete>", on_delete, add="+")
    if on_click:
        tree.bind("<ButtonRelease-1>", on_click, add="+")

    # Cursor de mão para coluna WhatsApp
    def _on_motion_hand_cursor(event: Any) -> None:
        try:
            col = tree.identify_column(event.x)
            tree.configure(cursor="hand2" if col in ("#5",) else "")
        except Exception:
            tree.configure(cursor="")

    tree.bind("<Motion>", _on_motion_hand_cursor, add="+")
    tree.bind("<Leave>", lambda _e: tree.configure(cursor=""), add="+")

    # === TOOLTIP para texto truncado ===
    _setup_treeview_tooltip(tree, columns)

    # === REDIMENSIONAMENTO PROPORCIONAL automático ===
    _setup_flex_column_resize(tree, columns)

    return tree


def _setup_treeview_tooltip(tree: Any, columns: tuple) -> None:
    """Configura tooltip para mostrar texto completo de células truncadas."""
    tooltip_window: tk.Toplevel | None = None
    tooltip_label: tk.Label | None = None

    # Colunas que podem ter texto truncado
    tooltip_columns = {"Razao Social", "Nome", "Observacoes"}

    def show_tooltip(event: Any) -> None:
        nonlocal tooltip_window, tooltip_label

        try:
            # Identificar linha e coluna
            row_id = tree.identify_row(event.y)
            col_id = tree.identify_column(event.x)

            if not row_id or not col_id:
                hide_tooltip()
                return

            # Converter #N para índice
            col_index = int(col_id.replace("#", "")) - 1
            if col_index < 0 or col_index >= len(columns):
                hide_tooltip()
                return

            col_key = columns[col_index][0]
            if col_key not in tooltip_columns:
                hide_tooltip()
                return

            # Obter valor da célula
            values = tree.item(row_id, "values")
            if not values or col_index >= len(values):
                hide_tooltip()
                return

            cell_text = str(values[col_index])
            if not cell_text or len(cell_text) < 15:
                hide_tooltip()
                return

            # Verificar se texto está truncado (comparar com largura da coluna)
            col_width = tree.column(col_key, "width")
            # Estimativa: ~7 pixels por caractere
            if len(cell_text) * 7 <= col_width:
                hide_tooltip()
                return

            # Criar/atualizar tooltip
            if tooltip_window is None:
                tooltip_window = tk.Toplevel(tree)
                tooltip_window.wm_overrideredirect(True)
                tooltip_window.wm_attributes("-topmost", True)
                tooltip_label = tk.Label(
                    tooltip_window,
                    text=cell_text,
                    background="#ffffe0",
                    foreground="#000000",
                    relief="solid",
                    borderwidth=1,
                    font=("Segoe UI", 9),
                    wraplength=400,
                    justify="left",
                    padx=5,
                    pady=3,
                )
                tooltip_label.pack()
            else:
                tooltip_label.configure(text=cell_text)  # type: ignore

            # Posicionar tooltip
            x = event.x_root + 15
            y = event.y_root + 10
            tooltip_window.wm_geometry(f"+{x}+{y}")
            tooltip_window.deiconify()

        except Exception:
            hide_tooltip()

    def hide_tooltip(event: Any = None) -> None:
        nonlocal tooltip_window
        if tooltip_window is not None:
            try:
                tooltip_window.withdraw()
            except Exception:
                pass

    def destroy_tooltip(event: Any = None) -> None:
        nonlocal tooltip_window, tooltip_label
        if tooltip_window is not None:
            try:
                tooltip_window.destroy()
            except Exception:
                pass
            tooltip_window = None
            tooltip_label = None

    tree.bind("<Motion>", show_tooltip, add="+")
    tree.bind("<Leave>", hide_tooltip, add="+")
    tree.bind("<Destroy>", destroy_tooltip, add="+")


def _setup_flex_column_resize(tree: Any, columns: tuple) -> None:
    """Configura redimensionamento proporcional das colunas flex."""
    # Identificar colunas fixas e flex
    fixed_cols = [(c[0], c[2]) for c in columns if not c[4]]  # (key, width)
    flex_cols = [(c[0], c[3]) for c in columns if c[4]]  # (key, minwidth)

    total_fixed_width = sum(w for _, w in fixed_cols)
    total_flex_weight = sum(FLEX_COLUMN_WEIGHTS.get(k, 1) for k, _ in flex_cols)

    # ID do after para debounce
    tree._resize_after_id = None  # type: ignore[attr-defined]

    def _do_resize() -> None:
        """Recalcula e aplica larguras das colunas flex."""
        tree._resize_after_id = None  # type: ignore[attr-defined]

        try:
            if not tree.winfo_exists():
                return

            # Largura disponível para flex
            tree_width = tree.winfo_width()
            if tree_width < 100:  # Janela ainda não renderizada
                return

            # Margem para scrollbar e padding
            available = tree_width - total_fixed_width - 20

            if available < 100:
                # Espaço insuficiente, usar minwidths
                for col_key, minwidth in flex_cols:
                    tree.column(col_key, width=minwidth)
                return

            # Distribuir proporcionalmente por peso
            for col_key, minwidth in flex_cols:
                weight = FLEX_COLUMN_WEIGHTS.get(col_key, 1)
                new_width = max(minwidth, int(available * weight / total_flex_weight))
                tree.column(col_key, width=new_width)

        except Exception as exc:
            log.debug("Erro ao redimensionar colunas: %s", exc)

    def _on_configure(event: Any) -> None:
        """Handler de <Configure> com debounce."""
        # Cancelar resize anterior se existir
        if tree._resize_after_id is not None:  # type: ignore[attr-defined]
            try:
                tree.after_cancel(tree._resize_after_id)  # type: ignore[attr-defined]
            except Exception:
                pass

        # Agendar novo resize com debounce de 50ms
        try:
            tree._resize_after_id = tree.after(50, _do_resize)  # type: ignore[attr-defined]
        except Exception:
            pass

    def _on_destroy(event: Any) -> None:
        """Cancelar after pendente ao destruir."""
        if tree._resize_after_id is not None:  # type: ignore[attr-defined]
            try:
                tree.after_cancel(tree._resize_after_id)  # type: ignore[attr-defined]
            except Exception:
                pass
            tree._resize_after_id = None  # type: ignore[attr-defined]

    tree.bind("<Configure>", _on_configure, add="+")
    tree.bind("<Destroy>", _on_destroy, add="+")

    # Fazer resize inicial após a janela ser mapeada
    tree.after(100, _do_resize)


# =============================================================================
# Microfase 4: Funções de reaplicação de estilos da Treeview
# =============================================================================


def reapply_clientes_treeview_tags(
    tree: Any,
    even_bg: str,
    odd_bg: str,
    fg: str = "",
) -> None:
    """Reaplica tags de zebra (even/odd) na Treeview do módulo Clientes.

    Esta função é idempotente e pode ser chamada sempre que o tema muda.

    Args:
        tree: Instância da Treeview
        even_bg: Cor de fundo para linhas pares
        odd_bg: Cor de fundo para linhas ímpares
        fg: Cor de texto para ambas (opcional)
    """
    try:
        if fg:
            tree.tag_configure("even", background=even_bg, foreground=fg)
            tree.tag_configure("odd", background=odd_bg, foreground=fg)
        else:
            tree.tag_configure("even", background=even_bg)
            tree.tag_configure("odd", background=odd_bg)
        log.debug("Tags de zebra reaplicadas na Treeview")
    except Exception:
        log.exception("Erro ao reaplicar tags de zebra")
