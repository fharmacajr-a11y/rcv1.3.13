# -*- coding: utf-8 -*-
"""Dashboard center panel builder for HubScreen.

Builds the central dashboard panel with operational indicators,
hot items, and upcoming deadlines.
"""

from __future__ import annotations

import logging
import re
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from typing import TYPE_CHECKING, Any, Callable

import ttkbootstrap as tb
from ttkbootstrap.constants import BOTH, LEFT, W, X

# ORG-005: Constantes e funções puras extraídas
from src.modules.hub.views.dashboard_center_constants import (
    CARD_LABEL_FONT,
    CARD_PAD_X,
    CARD_PAD_Y,
    CARD_VALUE_FONT,
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
_HUB_ICON_CACHE: dict[str, tk.PhotoImage] = {}


# ============================================================================
# FUNÇÕES AUXILIARES (UI)
# ============================================================================


def _get_hub_icon(name: str, rel_path: str, master: tk.Misc | None = None) -> tk.PhotoImage | None:
    """Carrega ícone PNG do Hub com cache.

    Args:
        name: Nome identificador do ícone (para cache).
        rel_path: Caminho relativo do asset (ex: 'assets/modulos/hub/radar.png').
        master: Widget master para o PhotoImage (opcional).

    Returns:
        PhotoImage ou None se falhar.
    """
    if name in _HUB_ICON_CACHE:
        return _HUB_ICON_CACHE[name]

    try:
        abs_path = resource_path(rel_path)
        img = tk.PhotoImage(file=abs_path, master=master)
        _HUB_ICON_CACHE[name] = img
        return img
    except Exception:
        # Fallback silencioso: sem ícone
        return None


def _clear_children(parent: tb.Frame) -> None:
    """Remove todos os widgets filhos de um frame."""
    for child in parent.winfo_children():
        child.destroy()


def _render_text_with_status_highlight(
    parent: tb.Frame,
    text: str,
    font: tuple[str, int] | None = None,
    justify: str = LEFT,
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

            # Determinar bootstyle baseado no conteúdo
            if "atrasada" in status_content.lower():
                bootstyle = "danger"  # vermelho
            elif "hoje" in status_content.lower():
                bootstyle = "info"  # azul
            else:
                bootstyle = None  # padrão

            # Dividir a linha em 3 partes: prefixo, status, sufixo
            idx_start = match.start()
            idx_end = match.end()
            prefix = line[:idx_start]
            suffix = line[idx_end:]

            # Criar frame para a linha
            line_frame = tb.Frame(parent)
            line_frame.pack(anchor=W, pady=1)

            # Label para o prefixo (normal)
            if prefix:
                lbl_prefix = tb.Label(
                    line_frame,
                    text=prefix,
                    font=font or SECTION_ITEM_FONT,
                )
                lbl_prefix.pack(side=LEFT)

            # Label para o status (colorido e normalizado)
            lbl_status = tb.Label(
                line_frame,
                text=normalized_status,
                font=font or SECTION_ITEM_FONT,
                bootstyle=bootstyle,
            )
            lbl_status.pack(side=LEFT)

            # Label para o sufixo (normal)
            if suffix:
                lbl_suffix = tb.Label(
                    line_frame,
                    text=suffix,
                    font=font or SECTION_ITEM_FONT,
                )
                lbl_suffix.pack(side=LEFT)
        else:
            # Linha sem status - renderizar normalmente
            lbl = tb.Label(
                parent,
                text=line,
                font=font or SECTION_ITEM_FONT,
                justify=justify,
                wraplength=wraplength,
            )
            lbl.pack(anchor=W, pady=1)


def _build_scrollable_text_list(
    parent: tb.Frame,
    *,
    height_lines: int = 5,
) -> ScrolledText:
    """Cria widget ScrolledText para lista rolável.

    Args:
        parent: Frame pai onde o ScrolledText será criado.
        height_lines: Altura do widget em linhas (padrão 5).

    Returns:
        Widget ScrolledText configurado.
    """
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
    text_widget: ScrolledText,
    lines: list[str],
) -> None:
    """Renderiza linhas no Text widget com tags para colorir status.

    Aplica destaque:
    - "Atrasada Xd" => vermelho (#dc3545)
    - "Hoje" => azul (#0d6efd)

    Args:
        text_widget: Widget Text/ScrolledText onde renderizar.
        lines: Lista de strings (uma por linha) a serem exibidas.
    """
    # Configurar tags para colorização
    text_widget.tag_configure("status_overdue", foreground="#dc3545")  # vermelho
    text_widget.tag_configure("status_today", foreground="#0d6efd")  # azul

    # Inserir texto
    text_widget.configure(state="normal")
    text_widget.delete("1.0", "end")

    full_text = "\n".join(lines)
    text_widget.insert("1.0", full_text)

    # Aplicar tags usando search (robusto para multi-linha)
    # Padrão 1: "Atrasada Xd" (captura "Atrasada 1d", "Atrasada 2d", etc.)
    pattern_overdue = r"Atrasada\s+\d+d"
    # Padrão 2: "Hoje" (isolado ou entre parênteses)
    pattern_today = r"\(\s*Hoje\s*\)|\bHoje\b"

    # Colorir "Atrasada Xd"
    idx = "1.0"
    while True:
        pos = text_widget.search(pattern_overdue, idx, "end", regexp=True)
        if not pos:
            break
        match_text = text_widget.get(pos, f"{pos} lineend")
        match_obj = re.match(pattern_overdue, match_text)
        if match_obj:
            end_offset = f"+{len(match_obj.group(0))}c"
            end_pos = f"{pos}{end_offset}"
            text_widget.tag_add("status_overdue", pos, end_pos)
            idx = end_pos
        else:
            idx = f"{pos}+1c"

    # Colorir "Hoje"
    idx = "1.0"
    while True:
        pos = text_widget.search(pattern_today, idx, "end", regexp=True)
        if not pos:
            break
        match_text = text_widget.get(pos, f"{pos} lineend")
        match_obj = re.search(pattern_today, match_text)
        if match_obj:
            end_offset = f"+{len(match_obj.group(0))}c"
            end_pos = f"{pos}{end_offset}"
            text_widget.tag_add("status_today", pos, end_pos)
            idx = end_pos
        else:
            idx = f"{pos}+1c"

    # Voltar para read-only
    text_widget.configure(state="disabled")
    # Garantir que está no topo
    text_widget.see("1.0")


def _build_scrollable_status_list(
    parent: tb.Frame,
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
    text_widget.pack(fill=BOTH, expand=True)
    _render_lines_with_status_highlight(text_widget, lines)


def _build_indicator_card(
    parent: tb.Frame,
    label: str,
    value: int | float,
    bootstyle: str = "primary",
    value_text: str | None = None,  # Texto customizado para o valor (com ícones, etc.)
    on_click: Callable[[], None] | None = None,  # Callback ao clicar no card
) -> tb.Frame:
    """Constrói um card de indicador com valor e label.

    Args:
        parent: Frame pai onde o card será criado.
        label: Texto descritivo do indicador.
        value: Valor numérico a ser exibido.
        bootstyle: Estilo do card (primary, success, warning, danger, etc.).
        value_text: Texto customizado para exibir no lugar do valor (ex: "2 ⚠").
        on_click: Callback opcional quando o card é clicado (navegação contextual).

    Returns:
        Frame contendo o card criado.
    """
    card = tb.Frame(parent, bootstyle=bootstyle, padding=(CARD_PAD_X, CARD_PAD_Y))

    # Tornar card clicável se callback fornecido
    if on_click is not None:
        card.configure(cursor="hand2")
        # Bind no frame e em todos os labels internos para capturar clique em qualquer parte
        card.bind("<Button-1>", lambda e: on_click())

    # Valor grande (usa value_text se fornecido, senão converte value)
    display_text = (
        value_text if value_text is not None else (str(int(value)) if isinstance(value, float) else str(value))
    )
    value_label = tb.Label(
        card,
        text=display_text,
        font=CARD_VALUE_FONT,
        bootstyle=f"{bootstyle}-inverse",
    )
    value_label.pack(anchor="center")

    # Propagar evento de clique para labels também
    if on_click is not None:
        value_label.bind("<Button-1>", lambda e: on_click())

    # Label descritivo
    text_label = tb.Label(
        card,
        text=label,
        font=CARD_LABEL_FONT,
        bootstyle=f"{bootstyle}-inverse",
    )
    text_label.pack(anchor="center")

    # Propagar evento de clique para labels também
    if on_click is not None:
        text_label.bind("<Button-1>", lambda e: on_click())

    return card


def _build_section_frame(
    parent: tb.Frame,
    title: str,
) -> tuple[tb.Labelframe, tb.Frame]:
    """Constrói um frame de seção com título.

    Args:
        parent: Frame pai.
        title: Título da seção.

    Returns:
        Tupla (section_frame, content_frame) para adicionar conteúdo.
    """
    section = tb.Labelframe(parent, text=title, padding=10)

    content = tb.Frame(section)
    content.pack(fill=X)

    return section, content


# ORG-005: Funções de formatação movidas para dashboard_center_pure.py
# _format_deadline_line, _format_task_line, _format_day_label


def _build_risk_radar_section(
    parent: tb.Frame,
    radar: dict[str, dict[str, Any]],
) -> None:
    """Constrói a seção do radar de riscos regulatórios.

    Args:
        parent: Frame pai onde a seção será construída.
        radar: Dicionário com 3 quadrantes (ANVISA, SNGPC, SIFAP).
    """
    # Criar Labelframe sem text (usaremos labelwidget com PNG)
    section = tb.Labelframe(parent, padding=10)

    # Criar label customizado com ícone PNG
    radar_icon = _get_hub_icon("radar", "assets/modulos/hub/radar.png", master=parent)
    title_label = tb.Label(section, text="Radar de riscos regulatórios")
    if radar_icon:
        title_label.configure(image=radar_icon, compound="left")
    section.configure(labelwidget=title_label)

    section.pack(fill=X, pady=(0, 15))

    content = tb.Frame(section)
    content.pack(fill=X)

    # Grid 1x3 para os quadrantes (uma linha com 3 colunas)
    grid_frame = tb.Frame(content)
    grid_frame.pack(fill=X)

    quadrants = [
        ("ANVISA", 0, 0),
        ("Farmácia Popular", 0, 1),
        ("SIFAP", 0, 2),
    ]

    for name, row, col in quadrants:
        data = radar.get(name, {"pending": 0, "overdue": 0, "status": "green", "enabled": True})
        pending = data.get("pending", 0)
        overdue = data.get("overdue", 0)
        status = data.get("status", "green")
        enabled = bool(data.get("enabled", True))

        # Map status to bootstyle
        bootstyle_map = {
            "green": "success",
            "yellow": "warning",
            "red": "danger",
            "disabled": "secondary",
        }

        # If disabled, override to secondary style
        if not enabled:
            bootstyle = "secondary"
            text = "Desativado"
        else:
            bootstyle = bootstyle_map.get(status, "secondary")
            text = f"Pendentes: {pending} – Atrasadas: {overdue}"

        # Create quadrant frame
        quad_frame = tb.Frame(grid_frame, bootstyle=bootstyle, padding=10)
        quad_frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

        # Quadrant name
        name_font: Any = ("Segoe UI", 10, "bold")
        lbl_name = tb.Label(
            quad_frame,
            text=name,
            font=name_font,
            bootstyle=f"{bootstyle}-inverse",
        )
        lbl_name.pack(anchor="center")

        # Counts
        counts_font: tuple[str, int] = ("Segoe UI", 9)
        lbl_counts = tb.Label(
            quad_frame,
            text=text,
            font=counts_font,
            bootstyle=f"{bootstyle}-inverse",
        )
        lbl_counts.pack(anchor="center")

    # Configure grid weights for equal sizing (3 colunas)
    grid_frame.columnconfigure(0, weight=1)
    grid_frame.columnconfigure(1, weight=1)
    grid_frame.columnconfigure(2, weight=1)


def _build_recent_activity_section(
    parent: tb.Frame,
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
    from tkinter.scrolledtext import ScrolledText
    from src.modules.hub.recent_activity_store import get_recent_activity_store
    from src.modules.hub.async_runner import HubAsyncRunner
    from src.helpers.auth_utils import resolve_org_id

    section, content = _build_section_frame(parent, title="📋 Atividade recente da equipe")
    section.pack(fill=X, pady=(0, 15))

    # Criar ScrolledText read-only
    activity_text = ScrolledText(
        content,
        height=8,
        wrap="word",
        font=("Segoe UI", 9),
        bg="#f8f9fa",
        relief="flat",
        padx=8,
        pady=8,
    )
    activity_text.pack(fill=BOTH, expand=True)

    # Configurar tags para colorir ações específicas
    # Tag para "REGULARIZAÇÃO CANCELADA" (vermelho + bold)
    bold_font = ("Segoe UI", 9, "bold")

    activity_text.tag_configure(
        "status_cancelada",
        foreground="#dc3545",  # Vermelho (danger)
        font=bold_font,
    )

    # Tag para "REGULARIZAÇÃO CONCLUÍDA" (verde + bold)
    activity_text.tag_configure(
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
        activity_text.config(state="normal")
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
            idx = "1.0"
            while True:
                pos = activity_text.search(needle, idx, stopindex="end")
                if not pos:
                    break
                end_pos = f"{pos}+{len(needle)}c"
                activity_text.tag_add(tag, pos, end_pos)
                idx = end_pos

        # Aplicar tags para ações específicas
        apply_status_tags("REGULARIZAÇÃO CANCELADA", "status_cancelada")
        apply_status_tags("REGULARIZAÇÃO CONCLUÍDA", "status_concluida")

        activity_text.config(state="disabled")
        activity_text.see("end")  # Auto-scroll para o final

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
    parent: tb.Frame,
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

    # Container principal com padding
    main_container = tb.Frame(parent, padding=10)
    main_container.pack(fill=BOTH, expand=True)

    # -------------------------------------------------------------------------
    # 1. LINHA DE CARDS DE INDICADORES (usando DashboardCardView do state)
    # -------------------------------------------------------------------------
    cards_frame = tb.Frame(main_container)
    cards_frame.pack(fill=X, pady=(0, 15))

    # Card: Clientes ativos (consome state.card_clientes)
    if state.card_clientes:
        card_clientes = _build_indicator_card(
            cards_frame,
            label=state.card_clientes.label,
            value=state.card_clientes.value,
            bootstyle=state.card_clientes.bootstyle,
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
            bootstyle=state.card_pendencias.bootstyle,
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
            bootstyle=state.card_tarefas.bootstyle,
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
            lbl_no_hot = tb.Label(
                hot_content,
                text=MSG_NO_HOT_ITEMS,
                font=SECTION_ITEM_FONT,
            )
            lbl_no_hot.pack(anchor=W, pady=2)
        else:
            # Exibir cada hot_item com prefixo de alerta
            for item in snapshot.hot_items:
                lbl_item = tb.Label(
                    hot_content,
                    text=f"⚠ {item}",  # Adiciona ícone de alerta
                    font=SECTION_ITEM_FONT,
                    bootstyle="danger",
                )
                lbl_item.pack(anchor=W, pady=2)

    # -------------------------------------------------------------------------
    # 2.1. BLOCO "TAREFAS PENDENTES" (rolagem habilitada)
    # -------------------------------------------------------------------------
    # Ajustar título e mensagem vazia baseado no modo ANVISA-only
    if snapshot.anvisa_only:
        tasks_title_text = "ANVISA – Tarefas de hoje"
        tasks_empty_msg = "Nenhuma tarefa ANVISA para hoje."
    else:
        tasks_title_text = "Tarefas pendentes"
        tasks_empty_msg = "Nenhuma tarefa pendente no momento."

    # Criar Labelframe sem text (usaremos labelwidget com PNG)
    tasks_section = tb.Labelframe(main_container, padding=10)

    # Criar label customizado com ícone PNG
    tasks_icon = _get_hub_icon(
        "tasks_checklist",
        "assets/modulos/hub/lista-de-verificacao-de-tarefas.png",
        master=main_container,
    )
    tasks_title_label = tb.Label(tasks_section, text=tasks_title_text)
    if tasks_icon:
        tasks_title_label.configure(image=tasks_icon, compound="left")
    tasks_section.configure(labelwidget=tasks_title_label)

    tasks_section.pack(fill=X, pady=(0, 15))

    tasks_content = tb.Frame(tasks_section)
    tasks_content.pack(fill=X, expand=True)

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

    # Renderizar tarefas de hoje com ScrolledText
    if not all_today_items:
        # Nenhuma tarefa pendente
        lbl_no_tasks = tb.Label(
            tasks_content,
            text=tasks_empty_msg,
            font=SECTION_ITEM_FONT,
        )
        lbl_no_tasks.pack(anchor=W, pady=2)
    else:
        # Agrupar tarefas por cliente
        task_blocks = group_tasks_for_display(
            all_today_items,
            max_clients=50,  # Aumentar limite para scroll
            max_items_per_client=3,
        )

        # Criar ScrolledText para renderizar
        text_today = _build_scrollable_text_list(tasks_content, height_lines=5)
        text_today.pack(fill=X, expand=False, pady=2)

        # Renderizar com destaque de cores
        _render_lines_with_status_highlight(text_today, task_blocks)

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
            lbl_no_clients = tb.Label(
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
                lbl_client = tb.Label(
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

    deadlines_section, deadlines_content = _build_section_frame(
        main_container,
        title=deadlines_title,
    )
    deadlines_section.pack(fill=X, pady=(0, 10))

    if not future_deadlines:
        # Nenhum vencimento futuro
        lbl_no_deadlines = tb.Label(
            deadlines_content,
            text=deadlines_empty_msg,
            font=SECTION_ITEM_FONT,
        )
        lbl_no_deadlines.pack(anchor=W, pady=2)
    else:
        # Agrupar prazos por cliente (limite aumentado para 50 com scroll)
        deadline_blocks = group_deadlines_for_display(
            future_deadlines,
            max_clients=50,
            max_items_per_client=2,
            hide_kind=snapshot.anvisa_only,  # No ANVISA-only, esconde 'kind' (redundante)
        )

        # Renderizar com ScrolledText (colorização automática de status)
        _build_scrollable_status_list(deadlines_content, deadline_blocks, height=7)

    # -------------------------------------------------------------------------
    # 3.1. BLOCO "ATIVIDADE RECENTE DA EQUIPE" (movido para depois dos prazos)
    # -------------------------------------------------------------------------
    _build_recent_activity_section(
        main_container,
        snapshot.recent_activity,
        on_view_all=on_view_all_activity,
        tk_root=tk_root,
    )


def build_dashboard_error(parent: tb.Frame, message: str | None = None) -> None:
    """Constrói uma mensagem de erro amigável no painel central.

    Args:
        parent: Frame pai onde a mensagem será exibida.
        message: Mensagem de erro customizada. Se None, usa mensagem padrão.
    """
    _clear_children(parent)

    error_msg = message or "Não foi possível carregar o dashboard agora. Tente novamente mais tarde."

    container = tb.Frame(parent, padding=20)
    container.pack(fill=BOTH, expand=True)

    # Ícone de erro
    icon_font: Any = ("Segoe UI", 32)
    lbl_icon = tb.Label(
        container,
        text="⚠️",
        font=icon_font,
    )
    lbl_icon.pack(pady=(20, 10))

    # Mensagem
    msg_font: Any = ("Segoe UI", 11)
    lbl_msg = tb.Label(
        container,
        text=error_msg,
        font=msg_font,
        wraplength=300,
        justify="center",
    )
    lbl_msg.pack(pady=10)
