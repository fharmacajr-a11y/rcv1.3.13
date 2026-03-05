# -*- coding: utf-8 -*-
"""Dashboard center panel builder for HubScreen.

Constrói o painel central do Hub com tarefas pendentes.
"""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter.constants import X, BOTH
from typing import TYPE_CHECKING, Any, Callable

from src.ui.ctk_config import ctk, HAS_CUSTOMTKINTER
from src.ui.ui_tokens import (
    APP_BG,
    SURFACE,
    SURFACE_DARK,
    TEXT_PRIMARY,
    TEXT_MUTED,
    BODY_FONT,
    TITLE_FONT,
    CARD_RADIUS,
)
from src.modules.hub.views.dashboard_center_pure import group_tasks_for_display

if TYPE_CHECKING:
    from src.modules.hub.viewmodels import DashboardViewState

logger = logging.getLogger(__name__)


# ============================================================================
# FUNÇÕES HELPER PARA TYPING E CTk COMPATIBILITY
# ============================================================================


def get_inner_text_widget(textbox: Any) -> tk.Text:
    """Helper para acessar widget Text interno do CTkTextbox."""
    if hasattr(textbox, "_textbox"):
        return textbox._textbox  # type: ignore[attr-defined]
    return textbox  # Fallback genérico


def configure_textbox_readonly(textbox: Any) -> None:
    """Configura CTkTextbox como read-only."""
    inner = get_inner_text_widget(textbox)
    inner.configure(state="disabled")


def configure_textbox_editable(textbox: Any) -> None:
    """Configura CTkTextbox como editável."""
    inner = get_inner_text_widget(textbox)
    inner.configure(state="normal")


# ============================================================================
# FUNÇÕES AUXILIARES (UI)
# ============================================================================


def _clear_children(parent: Any) -> None:  # tk.Frame | ctk.CTkFrame
    """Remove todos os widgets filhos de um frame."""
    for child in parent.winfo_children():  # type: ignore[attr-defined]
        child.destroy()


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

    raise RuntimeError("CustomTkinter é obrigatório para build_section_card")


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

    _clear_children(parent)

    main_container = ctk.CTkFrame(parent, fg_color="transparent")
    main_container.pack(fill=BOTH, expand=True, padx=10, pady=10)

    # -------------------------------------------------------------------------
    # TAREFAS PENDENTES
    # -------------------------------------------------------------------------
    if snapshot.anvisa_only:
        tasks_title_text = "🗂️ ANVISA – Tarefas de hoje"
        tasks_empty_msg = "Nenhuma tarefa ANVISA para hoje."
    else:
        tasks_title_text = "🗂️ Tarefas pendentes"
        tasks_empty_msg = "Nenhuma tarefa pendente no momento."

    tasks_section, tasks_inner = build_section_card(main_container, tasks_title_text)
    tasks_section.pack(fill=X, pady=(0, 16))

    all_today_items = list(snapshot.pending_tasks)

    if not all_today_items:
        lbl_no_tasks = ctk.CTkLabel(
            tasks_inner,
            text=tasks_empty_msg,
            font=BODY_FONT,
            text_color=TEXT_MUTED,
            fg_color="transparent",
        )
        lbl_no_tasks.pack(pady=20)
    else:
        tasks_textbox = ctk.CTkTextbox(
            tasks_inner,
            height=120,
            wrap="word",
            font=BODY_FONT,
            fg_color=SURFACE,
            text_color=TEXT_PRIMARY,
        )
        tasks_textbox.pack(fill=BOTH, expand=True, padx=8, pady=6)

        try:
            tasks_textbox._textbox.configure(padx=8, pady=6)  # type: ignore[attr-defined]
            tasks_textbox._textbox.configure(spacing1=2, spacing3=6)  # type: ignore[attr-defined]
        except (AttributeError, Exception):
            pass

        task_blocks = group_tasks_for_display(
            all_today_items,
            max_clients=50,
            max_items_per_client=3,
        )

        tasks_text = "\n\n".join(task_blocks) if task_blocks else tasks_empty_msg
        tasks_textbox.configure(state="normal")
        tasks_textbox.delete("1.0", "end")
        tasks_textbox.insert("1.0", tasks_text)
        tasks_textbox.configure(state="disabled")


def build_dashboard_error(parent: tk.Frame, message: str | None = None) -> None:
    """Constrói uma mensagem de erro amigável no painel central.

    Args:
        parent: Frame pai onde a mensagem será exibida.
        message: Mensagem de erro customizada. Se None, usa mensagem padrão.
    """
    _clear_children(parent)

    error_msg = message or "Não foi possível carregar o dashboard agora. Tente novamente mais tarde."

    container = ctk.CTkFrame(
        parent,
        fg_color=SURFACE_DARK,
        bg_color=APP_BG,
        border_width=0,
        corner_radius=CARD_RADIUS,
    )
    container.pack(fill=BOTH, expand=True, padx=20, pady=20)

    icon_font: Any = ("Segoe UI", 32)
    lbl_icon = ctk.CTkLabel(
        container,
        text="⚠️",
        font=icon_font,
        fg_color="transparent",
    )
    lbl_icon.pack(pady=(20, 10))

    msg_font: Any = ("Segoe UI", 11)
    lbl_msg = ctk.CTkLabel(
        container,
        text=error_msg,
        font=msg_font,
        wraplength=300,
        justify="center",
        text_color=("#dc2626", "#fca5a5"),
        fg_color="transparent",
    )
    lbl_msg.pack(pady=10)
