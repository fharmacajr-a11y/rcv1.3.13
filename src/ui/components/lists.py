# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import re
import tkinter as tk
import tkinter.font as tkfont
from typing import Any, Callable

import ttkbootstrap as tb
from ttkbootstrap import colorutils

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

__all__ = ["create_clients_treeview", "CLIENTS_COL_ANCHOR", "normalize_cell_text"]


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
        r, g, b = colorutils.color_to_rgb(hex_color)
        # Fórmula de luminância relativa (ITU-R BT.709)
        return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
    except Exception:
        return 0.5  # fallback neutro


def _adjust_lightness(hex_color: str, delta: float) -> str:
    """Ajusta lightness de uma cor HSL. delta positivo = mais claro."""
    try:
        h, s, l_val = colorutils.color_to_hsl(hex_color)
        new_l = max(0.0, min(1.0, l_val + delta))
        return colorutils.update_hsl_value(hex_color, lum=new_l)
    except Exception:
        return hex_color  # retorna original se falhar


def _configure_clients_treeview_style(style: tb.Style) -> tuple[str, str]:
    """Configura style exclusivo para Treeview de clientes.

    Retorna as cores de fundo para zebra striping (even_bg, odd_bg).
    """
    # Obter cor de fundo do tema atual
    try:
        base_bg = style.colors.bg
    except Exception:
        base_bg = "#ffffff"  # fallback

    # Calcular cor alternada baseada na luminância
    try:
        luminance = _get_luminance(base_bg)
        # Tema escuro (baixa luminância): clarear levemente
        # Tema claro (alta luminância): escurecer levemente
        if luminance < 0.5:
            # Tema escuro: clarear para zebra mais visível
            alt_bg = _adjust_lightness(base_bg, ZEBRA_LIGHTNESS_DELTA_DARK)
        else:
            # Tema claro: usar cor cinza fixa bem visível
            # O cálculo dinâmico pode não funcionar bem em alguns temas
            alt_bg = "#e0e0e0"  # cinza bem visível (fallback sólido)
            # Tentar ajuste dinâmico também
            try:
                dynamic_alt = _adjust_lightness(base_bg, ZEBRA_LIGHTNESS_DELTA_LIGHT)
                # Usar o mais escuro entre dinâmico e fixo
                if _get_luminance(dynamic_alt) < _get_luminance(alt_bg):
                    alt_bg = dynamic_alt
            except Exception:
                pass
    except Exception:
        # Fallback para cores estáticas com bom contraste
        alt_bg = "#e0e0e0" if base_bg == "#ffffff" else "#404040"

    even_bg = base_bg
    odd_bg = alt_bg

    # Configurar fonte base: +1 ponto em relação ao TkDefaultFont
    try:
        default_font = tkfont.nametofont("TkDefaultFont")
        font_family = default_font.cget("family")
        font_size = default_font.cget("size")
        new_size = font_size + 1 if font_size > 0 else 11
    except Exception:
        font_family = "Segoe UI"
        new_size = 11

    # Calcular rowheight: altura da fonte + padding GENEROSO
    # Padding de 14 e mínimo de 34 para linhas bem espaçadas
    try:
        temp_font = tkfont.Font(family=font_family, size=new_size)
        font_height = temp_font.metrics("linespace")
        rowheight = max(34, font_height + 14)
    except Exception:
        rowheight = 36  # fallback seguro com espaçamento bom

    # Configurar style exclusivo (não afeta outras Treeviews)
    try:
        style.configure(
            CLIENTS_TREEVIEW_STYLE,
            font=(font_family, new_size),
            rowheight=rowheight,
        )
        style.configure(
            f"{CLIENTS_TREEVIEW_STYLE}.Heading",
            font=(font_family, new_size, "bold"),
        )
        # Garantir que a seleção seja legível sobre as tags zebra (even/odd)
        # Cores de seleção explícitas que sobrescrevem o background das tags
        try:
            sel_bg = style.colors.selectbg  # cor de seleção do tema
            sel_fg = style.colors.selectfg  # texto da seleção
        except Exception:
            sel_bg = "#0d6efd"  # azul padrão
            sel_fg = "#ffffff"

        style.map(
            CLIENTS_TREEVIEW_STYLE,
            background=[("selected", sel_bg)],
            foreground=[("selected", sel_fg)],
        )
    except Exception as exc:
        log.debug("Falha ao configurar style do Clientes.Treeview: %s", exc)

    return even_bg, odd_bg


def _apply_treeview_fixed_map(style: tb.Style) -> None:
    """Aplica workaround para bug do Tk 8.6.9 onde tags não pintam background.

    Em algumas versões do Tk, os estados ('!disabled', '!selected') no style.map
    impedem que as tags de background funcionem corretamente.

    Este workaround remove esses estados problemáticos do mapeamento,
    permitindo que as tags even/odd pintem o background corretamente.

    Referência: https://core.tcl-lang.org/tk/tktview?name=509cafafae
    """
    try:
        # Obter mapeamento atual do style base (Treeview)
        # e filtrar estados problemáticos
        def _fixed_map(option: str) -> list:
            """Remove estados problemáticos do mapeamento."""
            try:
                # Obter mapa atual
                current_map = style.map("Treeview", query_opt=option)
                if not current_map:
                    return []

                # Filtrar estados que interferem com tags
                # Remover entradas com '!disabled' e '!selected'
                filtered = []
                for item in current_map:
                    if isinstance(item, tuple) and len(item) >= 2:
                        state = item[0] if isinstance(item[0], str) else str(item[0])
                        if "!disabled" not in state and "!selected" not in state:
                            filtered.append(item)
                return filtered
            except Exception:
                return []

        # Aplicar mapeamento filtrado ao style exclusivo
        style.map(
            CLIENTS_TREEVIEW_STYLE,
            background=_fixed_map("background"),
            foreground=_fixed_map("foreground"),
        )
    except Exception as exc:
        log.debug("Falha ao aplicar fixed_map para Treeview: %s", exc)


def create_clients_treeview(
    parent: tk.Misc,
    *,
    on_double_click: Callable[[Any], Any] | None,
    on_select: Callable[[Any], Any] | None,
    on_delete: Callable[[Any], Any] | None,
    on_click: Callable[[Any], Any] | None,
) -> tb.Treeview:
    """Create the main clients Treeview configured with column widths and bindings."""
    # Definição das colunas: (key, heading, width, minwidth, stretch)
    # FIXAS: ID, CNPJ, WhatsApp, Observações, Status, Última Alteração
    # FLEX: Razão Social, Nome (crescem com a janela)
    columns = (
        ("ID", "ID", COL_ID_WIDTH, 45, False),
        ("Razao Social", "Razão Social", COL_RAZAO_WIDTH, COL_RAZAO_MINWIDTH, True),
        ("CNPJ", "CNPJ", COL_CNPJ_WIDTH, 120, False),
        ("Nome", "Nome", COL_NOME_WIDTH, COL_NOME_MINWIDTH, True),
        ("WhatsApp", "WhatsApp", COL_WHATSAPP_WIDTH, 120, False),  # Aumentado para criar espaço
        ("Observacoes", "Observações", COL_OBS_WIDTH, 140, False),  # FIXA - compacta
        ("Status", "Status", COL_STATUS_WIDTH, 180, False),  # FIXA - compacta, perto da Última Alteração
        ("Ultima Alteracao", "Última Alteração", COL_ULTIMA_WIDTH, 170, False),  # FIXA - visível completa
    )

    # Configurar style exclusivo e obter cores para zebra
    style = tb.Style()
    even_bg, odd_bg = _configure_clients_treeview_style(style)

    # === WORKAROUND para bug do Tk 8.6.9 onde tags não pintam background ===
    # Aplicar fixed_map ANTES de criar o Treeview para garantir que zebra funcione
    _apply_treeview_fixed_map(style)

    # Criar Treeview com style exclusivo
    tree = tb.Treeview(
        parent,
        columns=[c[0] for c in columns],
        show="headings",
        style=CLIENTS_TREEVIEW_STYLE,
    )

    # Configurar headings (sempre centralizados)
    for key, heading, _, _, _ in columns:
        tree.heading(key, text=heading, anchor="center")

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


def _setup_treeview_tooltip(tree: tb.Treeview, columns: tuple) -> None:
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


def _setup_flex_column_resize(tree: tb.Treeview, columns: tuple) -> None:
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
