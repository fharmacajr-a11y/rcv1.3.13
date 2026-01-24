# -*- coding: utf-8 -*-
"""Dashboard center panel builder for HubScreen.

Builds the central dashboard panel with operational indicators,
hot items, and upcoming deadlines.
"""

from __future__ import annotations

import logging
import re
import tkinter as tk
from tkinter.constants import X, BOTH, LEFT, W
from tkinter.scrolledtext import ScrolledText
from typing import TYPE_CHECKING, Any, Callable

from src.ui.ctk_config import ctk
from src.ui.ui_tokens import (
    APP_BG,
    SURFACE,
    SURFACE_DARK,
    BORDER,
    TEXT_PRIMARY,
    TEXT_MUTED,
    BODY_FONT,
    TITLE_FONT,
    FONT_KPI_VALUE,
    FONT_KPI_LABEL,
    CARD_RADIUS,
)
from PIL import Image

from src.ui.ctk_config import HAS_CUSTOMTKINTER

# ORG-005: Constantes e funções puras extraídas
from src.modules.hub.views.dashboard_center_constants import (
    CARD_LABEL_FONT,
    CARD_PAD_X,
    CARD_PAD_Y,
    MSG_NO_HOT_ITEMS,
    MSG_NO_UPCOMING,
    SECTION_ITEM_FONT,
)
from src.modules.hub.views.dashboard_center_pure import (
    group_deadlines_for_display,
    group_tasks_for_display,
)
from src.utils.paths import resource_path

if TYPE_CHECKING:
    from src.modules.hub.viewmodels import DashboardViewState

logger = logging.getLogger(__name__)

# Cache global de ícones PNG do Hub (para não perder referência)
_HUB_ICON_CACHE: dict[str, Any] = {}  # type: ignore[type-arg]


# ============================================================================
# FUNÇÕES HELPER PARA TYPING E CTk COMPATIBILITY
# ============================================================================


def get_inner_text_widget(textbox: Any) -> tk.Text:
    """Helper para acessar widget Text interno do CTkTextbox."""
    return textbox._textbox  # type: ignore[attr-defined]


def configure_textbox_readonly(textbox: Any) -> None:
    """Configura CTkTextbox como read-only sem usar .config diretamente."""
    inner = get_inner_text_widget(textbox)
    inner.configure(state="disabled")


def configure_textbox_editable(textbox: Any) -> None:
    """Configura CTkTextbox como editável."""
    inner = get_inner_text_widget(textbox)
    inner.configure(state="normal")


# ============================================================================
# FUNÇÕES AUXILIARES (UI)
# ============================================================================


def _get_hub_icon(name: str, rel_path: str, master: tk.Misc | None = None) -> Any:  # type: ignore[type-arg]
    """Carrega ícone PNG do Hub com cache.

    Args:
        name: Nome identificador do ícone (para cache).
        rel_path: Caminho relativo do asset (ex: 'assets/modulos/hub/radar.png').
        master: Widget master para o CTkImage (opcional).

    Returns:
        CTkImage ou None se falhar.
    """
    if name in _HUB_ICON_CACHE:
        return _HUB_ICON_CACHE[name]

    try:
        abs_path = resource_path(rel_path)
        img = ctk.CTkImage(light_image=Image.open(abs_path), dark_image=Image.open(abs_path))  # type: ignore[attr-defined]
        _HUB_ICON_CACHE[name] = img
        return img
    except Exception:
        # Fallback silencioso: sem ícone
        return None


def _clear_children(parent: Any) -> None:  # tk.Frame | ctk.CTkFrame
    """Remove todos os widgets filhos de um frame."""
    for child in parent.winfo_children():  # type: ignore[attr-defined]
        child.destroy()


def _render_text_with_status_highlight(
    parent: tk.Frame,
    text: str,
    font: tuple[str, int] | None = None,
    justify: str = "left",
    wraplength: int = 900,
) -> None:
    """Renderiza texto com destaque colorido para status específicos.

    Detecta tokens de status entre parênteses e aplica cores:
    - (Atrasada Xd) -> vermelho (danger)
    - (Hoje) -> azul (info)

    Normaliza os tokens removendo espaços internos desnecessários.

    Args:
        parent: Frame pai onde os labels serão criados.
        text: Texto (pode ser multi-linha) a ser renderizado.
        font: Fonte opcional para os labels.
        justify: Justificação do texto.
        wraplength: Largura máxima para quebra de linha.
    """
    import re

    # Dividir texto em linhas
    lines = text.split("\n")

    for line in lines:
        # Padrões de status a detectar (com possíveis espaços internos)
        # 1. (Atrasada Xd) ou ( Atrasada Xd )
        # 2. (Hoje) ou ( Hoje )
        status_pattern = r"\(\s*(Atrasada\s+\d+d?|Hoje)\s*\)"

        match = re.search(status_pattern, line, re.IGNORECASE)

        if match:
            # Extrair o status e normalizar
            status_content = match.group(1).strip()  # Ex: "Atrasada 1d"
            normalized_status = f"({status_content})"  # Ex: "(Atrasada 1d)"

            # Determinar cor baseado no conteúdo
            if "atrasada" in status_content.lower():
                fg_color = "red"  # vermelho
            elif "hoje" in status_content.lower():
                fg_color = "blue"  # azul
            else:
                fg_color = None  # padrão

            # Dividir a linha em 3 partes: prefixo, status, sufixo
            idx_start = match.start()
            idx_end = match.end()
            prefix = line[:idx_start]
            suffix = line[idx_end:]

            # Criar frame para a linha
            if HAS_CUSTOMTKINTER and ctk is not None:
                line_frame = ctk.CTkFrame(parent)
            else:
                line_frame = tk.Frame(parent)
            line_frame.pack(anchor="w", pady=1)

            # Label para o prefixo (normal)
            if prefix:
                if HAS_CUSTOMTKINTER and ctk is not None:
                    lbl_prefix = ctk.CTkLabel(
                        line_frame,
                        text=prefix,
                        font=font or SECTION_ITEM_FONT,
                    )
                else:
                    lbl_prefix = tk.Label(  # type: ignore[attr-defined]
                        line_frame,
                        text=prefix,
                        font=font or SECTION_ITEM_FONT,
                    )
                lbl_prefix.pack(side="left")

            # Label para o status (colorido e normalizado)
            if HAS_CUSTOMTKINTER and ctk is not None:
                lbl_status = ctk.CTkLabel(
                    line_frame,
                    text=normalized_status,
                    font=font or SECTION_ITEM_FONT,
                    text_color=fg_color if fg_color else None,
                )
            else:
                lbl_status = tk.Label(  # type: ignore[attr-defined]
                    line_frame,
                    text=normalized_status,
                    font=font or SECTION_ITEM_FONT,
                    fg=fg_color if fg_color else "black",
                )
            lbl_status.pack(side="left")

            # Label para o sufixo (normal)
            if suffix:
                if HAS_CUSTOMTKINTER and ctk is not None:
                    lbl_suffix = ctk.CTkLabel(
                        line_frame,
                        text=suffix,
                        font=font or SECTION_ITEM_FONT,
                    )
                else:
                    lbl_suffix = tk.Label(  # type: ignore[attr-defined]
                        line_frame,
                        text=suffix,
                        font=font or SECTION_ITEM_FONT,
                    )
                lbl_suffix.pack(side="left")
        else:
            # Linha sem status - renderizar normalmente
            if HAS_CUSTOMTKINTER and ctk is not None:
                lbl = ctk.CTkLabel(
                    parent,
                    text=line,
                    font=font or SECTION_ITEM_FONT,
                    justify=justify,
                    wraplength=wraplength,
                )
            else:
                lbl = tk.Label(  # type: ignore[attr-defined]
                    parent,
                    text=line,
                    font=font or SECTION_ITEM_FONT,
                    justify=justify,
                    wraplength=wraplength,
                )
            lbl.pack(anchor="w", pady=1)


def _build_scrollable_text_list(
    parent: tk.Frame,
    *,
    height_lines: int = 5,
) -> ScrolledText | ctk.CTkTextbox:
    """Cria widget scrollável para lista rolável.

    Args:
        parent: Frame pai onde o widget será criado.
        height_lines: Altura do widget em linhas (padrão 5).

    Returns:
        Widget ScrolledText ou CTkTextbox configurado.
    """
    if HAS_CUSTOMTKINTER and ctk is not None:
        text_widget = ctk.CTkTextbox(
            parent,
            height=height_lines * 20,  # Aproximação: 20px por linha
            wrap="word",
            font=SECTION_ITEM_FONT,
        )
        # Para CTkTextbox, configurar como read-only usando helper
        from src.ui.ctk_text_compat import configure_text_readonly

        configure_text_readonly(text_widget)
    else:
        text_widget = ScrolledText(
            parent,
            height=height_lines,
            wrap="word",
            font=SECTION_ITEM_FONT,
            state="disabled",
        )

    # Dar foco ao passar mouse (para scroll funcionar no Windows)
    text_widget.bind("<Enter>", lambda e: text_widget.focus_set())

    return text_widget


def _render_lines_with_status_highlight(
    text_widget: ScrolledText | ctk.CTkTextbox,
    lines: list[str],
) -> None:
    """Renderiza linhas no Text widget com tags para colorir status.

    Aplica destaque:
    - "Atrasada Xd" => vermelho (#dc3545)
    - "Hoje" => azul (#0d6efd)

    Args:
        text_widget: Widget Text/ScrolledText/CTkTextbox onde renderizar.
        lines: Lista de strings (uma por linha) a serem exibidas.
    """
    from src.ui.ctk_text_compat import get_inner_text_widget, configure_text_readonly

    # Para CTkTextbox, usar widget interno para operações de texto/tags
    inner_widget = get_inner_text_widget(text_widget)

    # Configurar tags para colorização
    inner_widget.tag_configure("status_overdue", foreground="#dc3545")  # type: ignore[attr-defined]
    inner_widget.tag_configure("status_today", foreground="#0d6efd")  # type: ignore[attr-defined]

    # Desabilitar read-only temporariamente para edição
    if hasattr(text_widget, "_textbox"):
        # CTkTextbox: desabilitar binds temporariamente
        inner_widget.unbind("<Key>")  # type: ignore[attr-defined]
        inner_widget.unbind("<<Paste>>")  # type: ignore[attr-defined]
    else:
        # ScrolledText: usar configure normal
        text_widget.configure(state="normal")  # type: ignore[attr-defined]

    inner_widget.delete("1.0", "end")

    full_text = "\n".join(lines)
    inner_widget.insert("1.0", full_text)

    # Aplicar tags usando search (robusto para multi-linha)
    # Padrão 1: "Atrasada Xd" (captura "Atrasada 1d", "Atrasada 2d", etc.)
    pattern_overdue = r"Atrasada\s+\d+d"
    # Padrão 2: "Hoje" (isolado ou entre parênteses)
    pattern_today = r"\(\s*Hoje\s*\)|\bHoje\b"

    # Colorir "Atrasada Xd"
    idx = "1.0"
    while True:
        pos = inner_widget.search(pattern_overdue, idx, "end", regexp=True)  # type: ignore[attr-defined]
        if not pos:
            break
        match_text = inner_widget.get(pos, f"{pos} lineend")
        match_obj = re.match(pattern_overdue, match_text)
        if match_obj:
            end_offset = f"+{len(match_obj.group(0))}c"
            end_pos = f"{pos}{end_offset}"
            inner_widget.tag_add("status_overdue", pos, end_pos)  # type: ignore[attr-defined]
            idx = end_pos
        else:
            idx = f"{pos}+1c"

    # Colorir "Hoje"
    idx = "1.0"
    while True:
        pos = inner_widget.search(pattern_today, idx, "end", regexp=True)  # type: ignore[attr-defined]
        if not pos:
            break
        match_text = inner_widget.get(pos, f"{pos} lineend")
        match_obj = re.search(pattern_today, match_text)
        if match_obj:
            end_offset = f"+{len(match_obj.group(0))}c"
            end_pos = f"{pos}{end_offset}"
            inner_widget.tag_add("status_today", pos, end_pos)  # type: ignore[attr-defined]
            idx = end_pos
        else:
            idx = f"{pos}+1c"

    # Voltar para read-only
    if hasattr(text_widget, "_textbox"):
        # CTkTextbox: reconfigurar como read-only
        configure_text_readonly(text_widget)
    else:
        # ScrolledText: usar state disabled
        text_widget.configure(state="disabled")  # type: ignore[attr-defined]

    # Garantir que está no topo
    inner_widget.see("1.0")  # type: ignore[attr-defined]


def _build_scrollable_status_list(
    parent: tk.Frame,
    lines: list[str],
    height: int = 7,
) -> None:
    """[DEPRECATED] Usa _build_scrollable_text_list + _render_lines_with_status_highlight.

    Mantido para compatibilidade. Criar ScrolledText e renderizar linhas com tags.

    Args:
        parent: Frame pai onde o ScrolledText será criado.
        lines: Lista de strings (uma por linha) a serem exibidas.
        height: Altura do widget em linhas (padrão 7).
    """
    text_widget = _build_scrollable_text_list(parent, height_lines=height)
    text_widget.pack(fill="both", expand=True)
    _render_lines_with_status_highlight(text_widget, lines)


def _build_indicator_card(
    parent: tk.Frame,
    label: str,
    value: int | float,
    value_text: str | None = None,  # Texto customizado para o valor (com ícones, etc.)
    on_click: Callable[[], None] | None = None,  # Callback ao clicar no card
    card_color: str | tuple[str, str] | None = None,  # MICROFASE 35: cor do card
) -> Any:  # tk.Frame | ctk.CTkFrame
    """Constrói um card de indicador com valor e label.

    Args:
        parent: Frame pai onde o card será criado.
        label: Texto descritivo do indicador.
        value: Valor numérico a ser exibido.
        value_text: Texto customizado para exibir no lugar do valor (ex: "2 ⚠").
        on_click: Callback opcional quando o card é clicado (navegação contextual).
        card_color: Cor de fundo do card (para cards KPI coloridos).

    Returns:
        Frame contendo o card criado.
    """
    # MICROFASE 35: Definir cores baseado no label para KPI cards
    if card_color is None:
        label_lower = label.lower()
        if "cliente" in label_lower:
            card_color = ("#3b82f6", "#2563eb")  # Azul
        elif "pendências" in label_lower or "pendencia" in label_lower:
            card_color = ("#ef4444", "#dc2626")  # Vermelho
        elif "tarefa" in label_lower:
            card_color = ("#f97316", "#ea580c")  # Laranja
        else:
            card_color = ("#ffffff", "#1f2937")  # Branco/escuro padrão

    # Determinar cor do texto baseado na cor do card
    is_colored_card = card_color not in [("#ffffff", "#1f2937"), ("#ffffff", "#141414"), "transparent"]
    text_color = "#ffffff" if is_colored_card else ("#1f2937", "#f3f4f6")

    if HAS_CUSTOMTKINTER and ctk is not None:
        card = ctk.CTkFrame(
            parent,
            fg_color=card_color,
            bg_color=APP_BG,  # MICROFASE 35: evita vazamento nos cantos
            corner_radius=10,
            border_width=0 if is_colored_card else 1,
            border_color=BORDER,
        )
    else:
        card = ctk.CTkFrame(parent)
    card.pack(padx=CARD_PAD_X, pady=CARD_PAD_Y)

    # Tornar card clicável se callback fornecido
    if on_click is not None:
        card.configure(cursor="hand2")
        # Bind no frame e em todos os labels internos para capturar clique em qualquer parte
        card.bind("<Button-1>", lambda e: on_click())

    # Valor grande (usa value_text se fornecido, senão converte value)
    display_text = (
        value_text if value_text is not None else (str(int(value)) if isinstance(value, float) else str(value))
    )
    if HAS_CUSTOMTKINTER and ctk is not None:
        value_label = ctk.CTkLabel(
            card,
            text=display_text,
            font=FONT_KPI_VALUE,
            text_color=text_color,
            fg_color="transparent",
        )
    else:
        value_label = tk.Label(  # type: ignore[attr-defined]
            card,
            text=display_text,
            font=FONT_KPI_VALUE,
        )
    value_label.pack(anchor="center", pady=(12, 4))

    # Propagar evento de clique para labels também
    if on_click is not None:
        value_label.bind("<Button-1>", lambda e: on_click())

    # Label descritivo
    if HAS_CUSTOMTKINTER and ctk is not None:
        text_label = ctk.CTkLabel(
            card,
            text=label,
            font=FONT_KPI_LABEL,
            text_color=text_color,
            fg_color="transparent",
        )
    else:
        text_label = tk.Label(  # type: ignore[attr-defined]
            card,
            text=label,
            font=CARD_LABEL_FONT,
        )
    text_label.pack(anchor="center", pady=(0, 8))

    # Propagar evento de clique para labels também
    if on_click is not None:
        text_label.bind("<Button-1>", lambda e: on_click())

    return card


def build_section_card(
    parent: tk.Frame, title: str, *, corner: int = 16
) -> tuple[Any, Any]:  # (outer_frame, inner_frame)
    """Builder único padrão para cards do Hub.

    Args:
        parent: Frame pai
        title: Título do card
        corner: Raio dos cantos do card externo

    Returns:
        Tupla (outer_frame, inner_frame) - usar inner_frame como container de conteúdo
    """
    if HAS_CUSTOMTKINTER and ctk is not None:
        # Card externo cinza
        outer = ctk.CTkFrame(parent, fg_color=SURFACE_DARK, corner_radius=corner, border_width=0, bg_color=APP_BG)

        # Título/header
        title_label = ctk.CTkLabel(outer, text=title, font=TITLE_FONT, text_color=TEXT_PRIMARY, fg_color="transparent")
        title_label.pack(anchor="w", padx=14, pady=(12, 6))

        # Frame interno branco/escuro para conteúdo
        inner = ctk.CTkFrame(
            outer, fg_color=SURFACE, corner_radius=max(10, corner - 4), border_width=0, bg_color=SURFACE_DARK
        )
        inner.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        return outer, inner
    else:
        # Fallback
        outer = ctk.CTkFrame(parent)
        inner = ctk.CTkFrame(outer)
        inner.pack(fill="both", expand=True)
        return outer, inner


def _build_section_frame(
    parent: tk.Frame,
    title: str,
) -> tuple[Any, Any]:  # (section_frame, content_frame)
    """Constrói um frame de seção com título.

    Args:
        parent: Frame pai.
        title: Título da seção.

    Returns:
        Tupla (section_frame, content_frame) para adicionar conteúdo.
    """
    # MICROFASE 35: Seções com fundo cinza escuro sem borda
    if HAS_CUSTOMTKINTER and ctk is not None:
        section = ctk.CTkFrame(
            parent,
            fg_color=SURFACE_DARK,
            bg_color=APP_BG,  # MICROFASE 35: evita vazamento nos cantos
            border_width=0,
            corner_radius=CARD_RADIUS,
        )

        # Título da seção - usando novo token TITLE_FONT
        title_label = ctk.CTkLabel(
            section,
            text=title,
            font=TITLE_FONT,
            text_color=TEXT_PRIMARY,
            fg_color="transparent",
        )
        title_label.pack(anchor="w", padx=12, pady=(12, 6))

        content = ctk.CTkFrame(section, fg_color="transparent")
    else:
        # Fallback: usar CTkFrame sem estilo especial
        section = ctk.CTkFrame(parent)
        content = ctk.CTkFrame(section, fg_color="transparent")
    content.pack(fill=X, padx=12, pady=(0, 12))

    return section, content


def _build_inner_content_area(
    content_parent: tk.Frame, height: int = 180, **textbox_kwargs
) -> Any:  # ctk.CTkTextbox | tk.ScrolledText
    """Constrói área interna de conteúdo branca/escura para textbox/lista.

    Args:
        content_parent: Frame pai (vem de _build_section_frame)
        height: Altura do textbox
        **textbox_kwargs: Argumentos adicionais para CTkTextbox

    Returns:
        CTkTextbox configurado com padrão uniforme
    """
    if HAS_CUSTOMTKINTER and ctk is not None:
        # Textbox direto sem frame adicional
        textbox = ctk.CTkTextbox(
            content_parent,
            height=height,
            wrap="word",
            font=BODY_FONT,
            fg_color=SURFACE,
            text_color=TEXT_PRIMARY,
            **textbox_kwargs,
        )
        textbox.pack(fill="both", expand=True, padx=8, pady=6)

        # Ajustar padding interno e line spacing
        try:
            textbox._textbox.configure(padx=8, pady=6)  # type: ignore[attr-defined]
            textbox._textbox.configure(spacing1=2, spacing3=6)  # type: ignore[attr-defined]
        except (AttributeError, Exception):
            pass

        return textbox
    else:
        # Fallback
        from tkinter.scrolledtext import ScrolledText

        return ScrolledText(content_parent, height=height // 15, wrap="word")  # type: ignore[return-value]


# ORG-005: Funções de formatação movidas para dashboard_center_pure.py
# _format_deadline_line, _format_task_line, _format_day_label


def _build_risk_radar_section(
    parent: tk.Frame,
    radar: dict[str, dict[str, Any]],
) -> None:
    """Constrói a seção do radar de riscos regulatórios.

    Args:
        parent: Frame pai onde a seção será construída.
        radar: Dicionário com 3 quadrantes (ANVISA, SNGPC, SIFAP).
    """
    # Usar builder padrão
    section, inner_content = build_section_card(parent, "📡 Radar de riscos regulatórios")
    section.pack(fill=X, pady=(0, 16))

    # Grid 1x3 para os quadrantes (uma linha com 3 colunas)
    if HAS_CUSTOMTKINTER and ctk is not None:
        grid_frame = ctk.CTkFrame(inner_content, fg_color="transparent")
    else:
        # Fallback
        grid_frame = ctk.CTkFrame(inner_content, fg_color="transparent")
    grid_frame.pack(fill=X, padx=8, pady=6)

    quadrants = [
        ("ANVISA", 0, 0),
        ("Farmácia Popular", 0, 1),
        ("SIFAP", 0, 2),
    ]

    # MICROFASE 35: Cores para cada status
    color_map = {
        "green": ("#22c55e", "#16a34a"),  # Verde
        "yellow": ("#eab308", "#ca8a04"),  # Amarelo
        "red": ("#ef4444", "#dc2626"),  # Vermelho
        "disabled": ("#9ca3af", "#6b7280"),  # Cinza
    }

    for name, row, col in quadrants:
        data = radar.get(name, {"pending": 0, "overdue": 0, "status": "green", "enabled": True})
        pending = data.get("pending", 0)
        overdue = data.get("overdue", 0)
        status = data.get("status", "green")
        enabled = bool(data.get("enabled", True))

        # If disabled, override to secondary style
        if not enabled:
            bg_color = color_map["disabled"]
            text = "Desativado"
        else:
            bg_color = color_map.get(status, color_map["disabled"])
            text = f"Pendentes: {pending} – Atrasadas: {overdue}"

        # Create quadrant frame - MICROFASE 35: colorido
        if HAS_CUSTOMTKINTER and ctk is not None:
            quad_frame = ctk.CTkFrame(
                grid_frame,
                fg_color=bg_color,
                corner_radius=8,
            )
        else:
            quad_frame = ctk.CTkFrame(grid_frame)
        quad_frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

        # Quadrant name - texto branco
        name_font: Any = ("Segoe UI", 10, "bold")
        if HAS_CUSTOMTKINTER and ctk is not None:
            lbl_name = ctk.CTkLabel(
                quad_frame,
                text=name,
                font=name_font,
                text_color="#ffffff",
                fg_color="transparent",
            )
        else:
            lbl_name = tk.Label(  # type: ignore[attr-defined]
                quad_frame,
                text=name,
                font=name_font,
            )
        lbl_name.pack(anchor="center", pady=(8, 2))

        # Counts - texto branco
        counts_font: tuple[str, int] = ("Segoe UI", 9)
        if HAS_CUSTOMTKINTER and ctk is not None:
            lbl_counts = ctk.CTkLabel(
                quad_frame,
                text=text,
                font=counts_font,
                text_color="#ffffff",
                fg_color="transparent",
            )
        else:
            lbl_counts = tk.Label(  # type: ignore[attr-defined]
                quad_frame,
                text=text,
                font=counts_font,
            )
        lbl_counts.pack(anchor="center", pady=(0, 8))

    # Configure grid weights for equal sizing (3 colunas)
    grid_frame.columnconfigure(0, weight=1)
    grid_frame.columnconfigure(1, weight=1)
    grid_frame.columnconfigure(2, weight=1)


def _build_recent_activity_section(
    parent: tk.Frame,
    _activities: list[dict[str, Any]],
    *,
    _on_view_all: Callable[[], None] | None = None,
    tk_root: tk.Misc | None = None,
) -> None:
    """Constrói a seção de atividade recente da equipe.

    Agora usa ScrolledText para exibir histórico de atividades em tempo real,
    conectado ao RecentActivityStore e carrega do Supabase.

    Args:
        parent: Frame pai onde a seção será construída.
        activities: Lista de atividades recentes (DEPRECATED - não usado).
        on_view_all: Callback opcional para visualizar todas as atividades.
        tk_root: Widget Tkinter root para async runner (opcional).
    """
    from src.modules.hub.recent_activity_store import get_recent_activity_store
    from src.modules.hub.async_runner import HubAsyncRunner
    from src.utils.auth_utils import resolve_org_id

    # Usar builder padrão
    section, inner_content = build_section_card(parent, "📋 Atividade recente da equipe")
    section.pack(fill=X, pady=(0, 16))

    # Criar textbox direto no inner content
    if HAS_CUSTOMTKINTER and ctk is not None:
        activity_text = ctk.CTkTextbox(
            inner_content,
            height=180,
            wrap="word",
            font=BODY_FONT,
            fg_color=SURFACE,
            text_color=TEXT_PRIMARY,
        )
        activity_text.pack(fill=BOTH, expand=True, padx=8, pady=6)

        # Ajustar padding interno e line spacing
        try:
            activity_text._textbox.configure(padx=8, pady=6)  # type: ignore[attr-defined]
            activity_text._textbox.configure(spacing1=2, spacing3=6)  # type: ignore[attr-defined]
        except (AttributeError, Exception):
            pass

    # Configurar função de atualização baseada no tipo
    if HAS_CUSTOMTKINTER and ctk is not None:
        # Para CTkTextbox, usar métodos diferentes
        def set_activity_text(full_text: str) -> None:
            """Atualiza o conteúdo do CTkTextbox."""
            configure_textbox_editable(activity_text)
            activity_text.delete("1.0", "end")
            if full_text:
                activity_text.insert("1.0", full_text)
            else:
                activity_text.insert("1.0", "Nenhuma atividade recente.")
            configure_textbox_readonly(activity_text)

    # Configurar tags para colorir ações específicas (apenas para ScrolledText)
    # MICROFASE 35: CTkTextbox não suporta tags, então pulamos colorização inline
    bold_font = ("Segoe UI", 9, "bold")

    if not (HAS_CUSTOMTKINTER and ctk is not None):
        # Tags apenas para ScrolledText (fallback)
        inner_text = get_inner_text_widget(activity_text)
        inner_text.tag_configure(
            "status_cancelada",
            foreground="#dc3545",  # Vermelho (danger)
            font=bold_font,
        )

        inner_text.tag_configure(
            "status_concluida",
            foreground="#28a745",  # Verde (success)
            font=bold_font,
        )

        # Função helper para atualizar o texto com colorização
        def set_activity_text(full_text: str) -> None:
            """Atualiza o conteúdo do ScrolledText com colorização de ações.

            Cada entrada agora tem 2 linhas, separadas por linha em branco.
            Usa Text.search() para aplicar tags de forma robusta.
            """
            configure_textbox_editable(activity_text)
            activity_text.delete("1.0", "end")

            # Inserir texto completo
            if full_text:
                # Cada entrada já vem com \n interno (2 linhas)
                # Adicionar \n\n entre entradas
                entries = full_text.split("\n\n") if "\n\n" in full_text else [full_text]
                for i, entry in enumerate(entries):
                    activity_text.insert("end", entry)
                    # Adicionar linha em branco entre entradas (exceto última)
                    if i < len(entries) - 1:
                        activity_text.insert("end", "\n\n")
            else:
                activity_text.insert("end", "Nenhuma atividade recente.")

            # Aplicar tags usando Text.search() para robustez
            def apply_status_tags(needle: str, tag: str) -> None:
                """Aplica tag em todas as ocorrências de needle."""
                inner = get_inner_text_widget(activity_text)
                idx = "1.0"
                while True:
                    pos = inner.search(needle, idx, stopindex="end")  # type: ignore[attr-defined]
                    if not pos:
                        break
                    end_pos = f"{pos}+{len(needle)}c"
                    inner.tag_add(tag, pos, end_pos)  # type: ignore[attr-defined]
                    idx = end_pos

            # Aplicar tags para ações específicas
            apply_status_tags("REGULARIZAÇÃO CANCELADA", "status_cancelada")
            apply_status_tags("REGULARIZAÇÃO CONCLUÍDA", "status_concluida")

            configure_textbox_readonly(activity_text)
            inner = get_inner_text_widget(activity_text)
            inner.see("end")  # type: ignore[attr-defined]

    # Função para renderizar atividades do store
    def render_activity() -> None:
        """Renderiza atividades do store."""
        store = get_recent_activity_store()
        lines = store.get_lines()
        # Juntar entradas com linha em branco dupla
        text = "\n\n".join(lines) if lines else "Nenhuma atividade recente."
        set_activity_text(text)

    # Renderização inicial
    render_activity()

    # Inscrever no store para atualizações em tempo real
    store = get_recent_activity_store()
    unsubscribe = store.subscribe(render_activity)

    # Guardar referência ao unsubscribe no widget para cleanup
    activity_text._activity_unsubscribe = unsubscribe  # type: ignore[attr-defined]

    # Configurar cleanup ao destruir o widget
    def on_destroy(event: Any) -> None:
        """Cleanup ao destruir o widget."""
        if hasattr(activity_text, "_activity_unsubscribe"):
            activity_text._activity_unsubscribe()  # type: ignore[attr-defined]

    activity_text.bind("<Destroy>", on_destroy)

    # Bootstrap: carregar eventos do Supabase
    # Hardening: qualquer erro é capturado, store fica vazio, UI mostra "Nenhuma atividade recente."
    if tk_root:
        try:
            org_id = resolve_org_id()
            runner = HubAsyncRunner(tk_root=tk_root, logger=logger)
            store.bootstrap_from_db(org_id, runner)
        except Exception as exc:
            logger.warning(
                f"[Hub] Erro ao iniciar bootstrap de histórico (org_id/runner): {exc}. Store permanece vazio."
            )
            # Continuar normalmente - UI já mostra "Nenhuma atividade recente."


# ORG-005: Função _format_day_label movida para dashboard_center_pure.py


# ============================================================================
# BUILDER PRINCIPAL
# ============================================================================


def build_dashboard_center(
    parent: tk.Frame,
    state: "DashboardViewState",
    *,
    on_new_task: Callable[[], None] | None = None,
    on_new_obligation: Callable[[], None] | None = None,
    on_view_all_activity: Callable[[], None] | None = None,
    on_card_clients_click: Callable[["DashboardViewState"], None] | None = None,
    on_card_pendencias_click: Callable[["DashboardViewState"], None] | None = None,
    on_card_tarefas_click: Callable[["DashboardViewState"], None] | None = None,
    tk_root: tk.Misc | None = None,
) -> None:
    """Constrói o painel central do dashboard na HubScreen.

    Limpa o parent e constrói:
    1. Linha de cards de indicadores (Clientes ativos, Pendências, Tarefas hoje)
    2. Botões de ação ("+ Nova Tarefa", "+ Nova Obrigação")
    3. Bloco "O que está bombando hoje" (hot_items)
    4. Bloco "Próximos vencimentos" (upcoming_deadlines)

    Args:
        parent: Frame pai onde o dashboard será construído.
        state: DashboardViewState com dados agregados e cards formatados.
        on_new_task: Callback opcional para criar nova tarefa.
        on_new_obligation: Callback opcional para criar nova obrigação.
        on_view_all_activity: Callback opcional para visualizar todas as atividades.
        on_card_clients_click: Callback opcional para clique no card de Clientes Ativos.
            Recebe DashboardViewState como parâmetro.
        on_card_pendencias_click: Callback opcional para clique no card de Pendências.
            Recebe DashboardViewState como parâmetro.
        on_card_tarefas_click: Callback opcional para clique no card de Tarefas Hoje.
            Recebe DashboardViewState como parâmetro.
        tk_root: Widget Tkinter root para carregar histórico do Supabase (opcional).
    """
    import logging

    logger = logging.getLogger(__name__)
    logger.debug("[build_dashboard_center] Iniciando construção do dashboard...")

    # Extrair snapshot para uso em seções que ainda precisam dele
    snapshot = state.snapshot
    if snapshot is None:
        # Estado inválido, não renderizar nada
        logger.warning("[build_dashboard_center] snapshot é None, não renderizando")
        return

    # Limpar widgets existentes
    _clear_children(parent)

    # Container principal sem padding - MICROFASE 35: fundo transparente
    if HAS_CUSTOMTKINTER and ctk is not None:
        main_container = ctk.CTkFrame(parent, fg_color="transparent")
    else:
        # Fallback
        main_container = ctk.CTkFrame(parent, fg_color="transparent")
    main_container.pack(fill=BOTH, expand=True, padx=10, pady=10)

    # -------------------------------------------------------------------------
    # 1. LINHA DE CARDS DE INDICADORES (usando DashboardCardView do state)
    # -------------------------------------------------------------------------
    # MICROFASE 35: Usar CTkFrame transparente
    if HAS_CUSTOMTKINTER and ctk is not None:
        cards_frame = ctk.CTkFrame(main_container, fg_color="transparent")
    else:
        # Fallback
        cards_frame = ctk.CTkFrame(main_container, fg_color="transparent")
    cards_frame.pack(fill=X, pady=(0, 15))

    # Card: Clientes ativos (consome state.card_clientes)
    if state.card_clientes:
        card_clientes = _build_indicator_card(
            cards_frame,
            label=state.card_clientes.label,
            value=state.card_clientes.value,
            value_text=state.card_clientes.value_text,
            on_click=(lambda s=state: on_card_clients_click(s)) if on_card_clients_click else None,
        )
        card_clientes.pack(side=LEFT, padx=(0, 10), fill=X, expand=True)

    # Card: Pendências regulatórias (consome state.card_pendencias)
    if state.card_pendencias:
        card_pendencias = _build_indicator_card(
            cards_frame,
            label=state.card_pendencias.label,
            value=state.card_pendencias.value,
            value_text=state.card_pendencias.value_text,
            on_click=(lambda s=state: on_card_pendencias_click(s)) if on_card_pendencias_click else None,
        )
        card_pendencias.pack(side=LEFT, padx=(0, 10), fill=X, expand=True)

    # Card: Tarefas hoje (consome state.card_tarefas)
    if state.card_tarefas:
        card_tarefas = _build_indicator_card(
            cards_frame,
            label=state.card_tarefas.label,
            value=state.card_tarefas.value,
            value_text=state.card_tarefas.value_text,
            on_click=(lambda s=state: on_card_tarefas_click(s)) if on_card_tarefas_click else None,
        )
        card_tarefas.pack(side=LEFT, fill=X, expand=True)

    # -------------------------------------------------------------------------
    # 1.1. RADAR DE RISCOS REGULATÓRIOS
    # -------------------------------------------------------------------------
    _build_risk_radar_section(main_container, snapshot.risk_radar)

    # -------------------------------------------------------------------------
    # 2. BLOCO "O QUE ESTÁ BOMBANDO HOJE"
    # -------------------------------------------------------------------------
    # No ANVISA-only, esconder completamente se vazio (evitar ruído visual)
    if not (snapshot.anvisa_only and not snapshot.hot_items):
        hot_section, hot_content = _build_section_frame(
            main_container,
            title="🔥 O que está bombando hoje",
        )
        hot_section.pack(fill=X, pady=(0, 15))

        if not snapshot.hot_items:
            # Nenhum alerta
            if HAS_CUSTOMTKINTER and ctk is not None:
                lbl_no_hot = ctk.CTkLabel(
                    hot_content,
                    text=MSG_NO_HOT_ITEMS,
                    font=SECTION_ITEM_FONT,
                )
            else:
                lbl_no_hot = tk.Label(  # type: ignore[attr-defined]
                    hot_content,
                    text=MSG_NO_HOT_ITEMS,
                    font=SECTION_ITEM_FONT,
                )
            lbl_no_hot.pack(anchor=W, pady=2)
        else:
            # Exibir cada hot_item com prefixo de alerta
            for item in snapshot.hot_items:
                if HAS_CUSTOMTKINTER and ctk is not None:
                    lbl_item = ctk.CTkLabel(
                        hot_content,
                        text=f"⚠ {item}",  # Adiciona ícone de alerta
                        font=SECTION_ITEM_FONT,
                        text_color=("#dc2626", "#fca5a5"),  # Vermelho
                        fg_color="transparent",
                    )
                else:
                    lbl_item = tk.Label(  # type: ignore[attr-defined]
                        hot_content,
                        text=f"⚠ {item}",
                        font=SECTION_ITEM_FONT,
                    )
                lbl_item.pack(anchor=W, pady=2)

    # -------------------------------------------------------------------------
    # 2.1. BLOCO "TAREFAS PENDENTES" (rolagem habilitada)
    # -------------------------------------------------------------------------
    # Ajustar título e mensagem vazia baseado no modo ANVISA-only
    # Definir título baseado no modo
    if snapshot.anvisa_only:
        tasks_title_text = "🗂️ ANVISA – Tarefas de hoje"
        tasks_empty_msg = "Nenhuma tarefa ANVISA para hoje."
    else:
        tasks_title_text = "🗂️ Tarefas pendentes"
        tasks_empty_msg = "Nenhuma tarefa pendente no momento."

    # Usar builder padrão
    tasks_section, tasks_inner = build_section_card(main_container, tasks_title_text)
    tasks_section.pack(fill=X, pady=(0, 16))

    # Separar deadlines em today (prazo <= hoje) e future (prazo > hoje)
    from datetime import date as date_type

    today_deadlines = []
    future_deadlines = []

    for deadline in snapshot.upcoming_deadlines:
        due_date_str = deadline.get("due_date", "")
        try:
            # Parse ISO date (YYYY-MM-DD) ou BR date (dd/mm/YYYY)
            if "-" in due_date_str:
                due_date = date_type.fromisoformat(due_date_str.strip())
            else:
                # Tentar formato BR
                from datetime import datetime as dt_type

                due_date = dt_type.strptime(due_date_str.strip(), "%d/%m/%Y").date()

            delta_days = (due_date - date_type.today()).days

            if delta_days <= 0:
                today_deadlines.append(deadline)
            else:
                future_deadlines.append(deadline)
        except (ValueError, AttributeError):
            # Se não conseguir parsear, assumir futuro (evitar duplicação)
            future_deadlines.append(deadline)

    # Combinar pending_tasks + today_deadlines (com deduplicação)
    all_today_items = list(snapshot.pending_tasks)  # Copiar lista

    # Criar set de chaves para deduplicação (request_id + client_id + due_date)
    existing_keys = set()
    for task in all_today_items:
        key = (
            task.get("request_id"),
            task.get("client_id"),
            task.get("due_date"),
        )
        existing_keys.add(key)

    # Adicionar today_deadlines sem duplicação
    for deadline in today_deadlines:
        key = (
            deadline.get("request_id"),
            deadline.get("client_id"),
            deadline.get("due_date"),
        )
        if key not in existing_keys:
            all_today_items.append(deadline)
            existing_keys.add(key)

    # Renderizar tarefas no inner content
    if not all_today_items:
        # Nenhuma tarefa pendente
        if HAS_CUSTOMTKINTER and ctk is not None:
            lbl_no_tasks = ctk.CTkLabel(
                tasks_inner,
                text=tasks_empty_msg,
                font=BODY_FONT,
                text_color=TEXT_MUTED,
                fg_color="transparent",
            )
            lbl_no_tasks.pack(pady=20)
        else:
            lbl_no_tasks = tk.Label(  # type: ignore[attr-defined]
                tasks_inner,
                text=tasks_empty_msg,
                font=BODY_FONT,
            )
            lbl_no_tasks.pack(pady=20)
    else:
        # Criar textbox de tarefas
        if HAS_CUSTOMTKINTER and ctk is not None:
            tasks_textbox = ctk.CTkTextbox(
                tasks_inner,
                height=120,
                wrap="word",
                font=BODY_FONT,
                fg_color=SURFACE,
                text_color=TEXT_PRIMARY,
            )
            tasks_textbox.pack(fill=BOTH, expand=True, padx=8, pady=6)

            # Ajustar padding interno e line spacing
            try:
                tasks_textbox._textbox.configure(padx=8, pady=6)  # type: ignore[attr-defined]
                tasks_textbox._textbox.configure(spacing1=2, spacing3=6)  # type: ignore[attr-defined]
            except (AttributeError, Exception):
                pass
        else:
            from tkinter.scrolledtext import ScrolledText

            tasks_textbox = ScrolledText(tasks_inner, height=8, wrap="word")
            tasks_textbox.pack(fill=BOTH, expand=True)

        # Agrupar tarefas por cliente
        task_blocks = group_tasks_for_display(
            all_today_items,
            max_clients=50,  # Aumentar limite para scroll
            max_items_per_client=3,
        )

        # Renderizar tarefas no textbox
        tasks_text = "\n\n".join(task_blocks) if task_blocks else tasks_empty_msg

        if HAS_CUSTOMTKINTER and ctk is not None:
            tasks_textbox.configure(state="normal")
            tasks_textbox.delete("1.0", "end")
            tasks_textbox.insert("1.0", tasks_text)
            tasks_textbox.configure(state="disabled")
        else:
            tasks_textbox.delete("1.0", "end")
            tasks_textbox.insert("1.0", tasks_text)

    # -------------------------------------------------------------------------
    # 2.2. BLOCO "CLIENTES DO DIA" (oculto em ANVISA-only)
    # -------------------------------------------------------------------------
    if not snapshot.anvisa_only:
        clients_title = "📌 Clientes do dia"
        clients_empty_msg = "Nenhum cliente com obrigação para hoje."

        clients_section, clients_content = _build_section_frame(
            main_container,
            title=clients_title,
        )
        clients_section.pack(fill=X, pady=(0, 15))

        if not snapshot.clients_of_the_day:
            # Nenhum cliente com obrigação hoje
            if HAS_CUSTOMTKINTER and ctk is not None:
                lbl_no_clients = ctk.CTkLabel(
                    clients_content,
                    text=clients_empty_msg,
                    font=SECTION_ITEM_FONT,
                    text_color=("#6b7280", "#9ca3af"),
                    fg_color="transparent",
                )
            else:
                lbl_no_clients = tk.Label(  # type: ignore[attr-defined]
                    clients_content,
                    text=clients_empty_msg,
                    font=SECTION_ITEM_FONT,
                )
            lbl_no_clients.pack(anchor=W, pady=2)
        else:
            # Exibir cada cliente
            for item in snapshot.clients_of_the_day:
                client_name = item.get("client_name") or f"Cliente #{item.get('client_id')}"
                kinds = item.get("obligation_kinds") or []
                kinds_str = ", ".join(kinds) if kinds else "obrigação"
                text = f"{client_name} – {kinds_str}"
                if HAS_CUSTOMTKINTER and ctk is not None:
                    lbl_client = ctk.CTkLabel(
                        clients_content,
                        text=text,
                        font=SECTION_ITEM_FONT,
                        text_color=("#1f2937", "#f3f4f6"),
                        fg_color="transparent",
                    )
                else:
                    lbl_client = tk.Label(  # type: ignore[attr-defined]
                        clients_content,
                        text=text,
                        font=SECTION_ITEM_FONT,
                    )
                lbl_client.pack(anchor=W, pady=2)

    # -------------------------------------------------------------------------
    # 3. BLOCO "PRÓXIMOS VENCIMENTOS"
    # -------------------------------------------------------------------------
    # Ajustar título e mensagem vazia baseado no modo ANVISA-only
    if snapshot.anvisa_only:
        deadlines_title = "📅 ANVISA – Próximos prazos"
        deadlines_empty_msg = "Nenhuma regularização ANVISA com prazo cadastrado."
    else:
        deadlines_title = "📅 Próximos vencimentos"
        deadlines_empty_msg = MSG_NO_UPCOMING

    # Usar builder padrão
    deadlines_section, deadlines_inner = build_section_card(
        main_container,
        deadlines_title,
    )
    deadlines_section.pack(fill=X, pady=(0, 10))

    if not future_deadlines:
        # Nenhum vencimento futuro
        if HAS_CUSTOMTKINTER and ctk is not None:
            lbl_no_deadlines = ctk.CTkLabel(
                deadlines_inner,
                text=deadlines_empty_msg,
                font=BODY_FONT,
                text_color=TEXT_MUTED,
                fg_color="transparent",
            )
        else:
            lbl_no_deadlines = tk.Label(  # type: ignore[attr-defined]
                deadlines_inner,
                text=deadlines_empty_msg,
                font=BODY_FONT,
            )
        lbl_no_deadlines.pack(pady=20)
    else:
        # Criar textbox para prazos
        if HAS_CUSTOMTKINTER and ctk is not None:
            deadlines_textbox = ctk.CTkTextbox(
                deadlines_inner,
                height=140,
                wrap="word",
                font=BODY_FONT,
                fg_color=SURFACE,
                text_color=TEXT_PRIMARY,
            )
            deadlines_textbox.pack(fill=BOTH, expand=True, padx=8, pady=6)

            # Ajustar padding interno e line spacing
            try:
                deadlines_textbox._textbox.configure(padx=8, pady=6)
                deadlines_textbox._textbox.configure(spacing1=2, spacing3=6)
            except (AttributeError, Exception):
                pass
        else:
            from tkinter.scrolledtext import ScrolledText

            deadlines_textbox = ScrolledText(deadlines_inner, height=8, wrap="word")
            deadlines_textbox.pack(fill=BOTH, expand=True)

        # Agrupar prazos por cliente (limite aumentado para 50 com scroll)
        deadline_blocks = group_deadlines_for_display(
            future_deadlines,
            max_clients=50,
            max_items_per_client=2,
            hide_kind=snapshot.anvisa_only,  # No ANVISA-only, esconde 'kind' (redundante)
        )

        # Renderizar prazos no textbox
        deadlines_text = "\n".join(deadline_blocks) if deadline_blocks else deadlines_empty_msg

        if HAS_CUSTOMTKINTER and ctk is not None:
            deadlines_textbox.configure(state="normal")
            deadlines_textbox.delete("1.0", "end")
            deadlines_textbox.insert("1.0", deadlines_text)
            deadlines_textbox.configure(state="disabled")
        else:
            deadlines_textbox.delete("1.0", "end")
            deadlines_textbox.insert("1.0", deadlines_text)

    # -------------------------------------------------------------------------
    # 3.1. BLOCO "ATIVIDADE RECENTE DA EQUIPE" (movido para depois dos prazos)
    # -------------------------------------------------------------------------
    _build_recent_activity_section(
        main_container,
        snapshot.recent_activity,
        _on_view_all=on_view_all_activity,
        tk_root=tk_root,
    )


def build_dashboard_error(parent: tk.Frame, message: str | None = None) -> None:
    """Constrói uma mensagem de erro amigável no painel central.

    Args:
        parent: Frame pai onde a mensagem será exibida.
        message: Mensagem de erro customizada. Se None, usa mensagem padrão.
    """
    _clear_children(parent)

    error_msg = message or "Não foi possível carregar o dashboard agora. Tente novamente mais tarde."

    # MICROFASE 35: Container com estilo CTk
    if HAS_CUSTOMTKINTER and ctk is not None:
        container = ctk.CTkFrame(
            parent,
            fg_color=SURFACE_DARK,
            bg_color=APP_BG,  # MICROFASE 35: evita vazamento nos cantos
            border_width=0,
            corner_radius=CARD_RADIUS,
        )
    else:
        container = ctk.CTkFrame(parent)
    container.pack(fill=BOTH, expand=True, padx=20, pady=20)

    # Ícone de erro
    icon_font: Any = ("Segoe UI", 32)
    if HAS_CUSTOMTKINTER and ctk is not None:
        lbl_icon = ctk.CTkLabel(
            container,
            text="⚠️",
            font=icon_font,
            fg_color="transparent",
        )
    else:
        lbl_icon = tk.Label(  # type: ignore[attr-defined]
            container,
            text="⚠️",
            font=icon_font,
        )
    lbl_icon.pack(pady=(20, 10))

    # Mensagem
    msg_font: Any = ("Segoe UI", 11)
    if HAS_CUSTOMTKINTER and ctk is not None:
        lbl_msg = ctk.CTkLabel(
            container,
            text=error_msg,
            font=msg_font,
            wraplength=300,
            justify="center",
            text_color=("#dc2626", "#fca5a5"),
            fg_color="transparent",
        )
    else:
        lbl_msg = tk.Label(  # type: ignore[attr-defined]
            container,
            text=error_msg,
            font=msg_font,
            wraplength=300,
            justify="center",
        )
    lbl_msg.pack(pady=10)
