# -*- coding: utf-8 -*-
"""
Main Window Layout Builder.

Responsável por construir toda a estrutura visual do MainWindow (frames, separadores,
topbar, menu, footer) SEM lógica de negócio ou navegação.

Extraído de main_window.py como parte de P2-MF "MainWindow Layout Extraction"
para reduzir MainWindow a ~500 linhas (apenas orquestrador).

MICROFASE 24: Removido sistema de múltiplos temas ttkbootstrap.
Agora usa CustomTkinter como sistema principal de temas (light/dark).
"""

from __future__ import annotations

import logging
import os
import tkinter as tk
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.ui.ctk_config import ctk
from src.ui.ui_tokens import APP_BG, SEP

from src.ui.topbar import TopBar
from src.ui.menu_bar import AppMenuBar
from src.ui.status_footer import StatusFooter
from src.core.navigation_controller import NavigationController

if TYPE_CHECKING:
    from src.modules.main_window.views.main_window import App

log = logging.getLogger("app_gui.layout")


@dataclass
class MainWindowLayoutRefs:
    """Referências aos componentes visuais criados pelo layout builder.

    Usado para MainWindow acessar os widgets após build_main_window_layout().
    """

    # Separadores
    sep_menu_toolbar: ctk.CTkFrame
    sep_toolbar_main: ctk.CTkFrame

    # Componentes principais
    topbar: TopBar
    menu: AppMenuBar
    content_container: tk.Frame  # MICROFASE 24: Pode ser tk.Frame ou ctk.CTkFrame
    nav: NavigationController
    footer: StatusFooter

    # Variáveis Tkinter
    clients_count_var: tk.StringVar
    status_var_dot: tk.StringVar
    status_var_text: tk.StringVar


def build_main_window_layout(
    app: App,
    *,
    start_hidden: bool = False,
) -> MainWindowLayoutRefs:
    """Constrói toda a estrutura visual do MainWindow.

    FASE 5A PASSO 3: Refatorado para construção em 2 fases:
    1. Skeleton: estrutura mínima para janela aparecer rápido
    2. Deferred: componentes complexos (topbar, menu, footer) agendados via after(0)

    Args:
        app: Instância de MainWindow (App)
        start_hidden: Se True, oculta janela após construção

    Returns:
        MainWindowLayoutRefs com referências (alguns None até deferred completar)
    """
    # Criar skeleton imediatamente
    refs = _build_layout_skeleton(app, start_hidden=start_hidden)
    
    # Agendar deferred para próximo tick (libera UI thread)
    app.after(0, lambda: _build_layout_deferred(app, refs))
    
    return refs


def _build_layout_skeleton(
    app: App,
    *,
    start_hidden: bool = False,
) -> MainWindowLayoutRefs:
    """FASE 1: Cria estrutura mínima para janela aparecer (skeleton).

    Cria apenas:
    - Container de conteúdo vazio
    - Variáveis Tkinter
    - Configurações básicas da janela

    Componentes complexos criados em _build_layout_deferred().
    """
    from src.modules.main_window.views.constants import APP_ICON_PATH, APP_TITLE, APP_VERSION
    from src.modules.main_window.views.state_helpers import (
        build_app_title,
        format_version_string,
    )
    from src.ui.window_policy import apply_fit_policy
    import src.core.status as app_status

    # 0. Configurar fundo da janela principal
    if ctk is not None:
        try:
            app.configure(fg_color=APP_BG)
        except (AttributeError, Exception):
            pass

    # 1. Título da janela
    version_str = format_version_string(APP_VERSION)
    window_title = build_app_title(APP_TITLE, version_str)
    app.title(window_title)

    # 2. Ícone da aplicação
    _apply_window_icon(app, APP_ICON_PATH)

    # 3. Protocol WM_DELETE_WINDOW
    app.protocol("WM_DELETE_WINDOW", app._confirm_exit)

    # 4. Aplicar política Fit-to-WorkArea
    apply_fit_policy(app)

    # 5. Ocultar janela se start_hidden
    if start_hidden:
        try:
            app.withdraw()
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao ocultar janela: %s", exc)

    # 6. Container de conteúdo VAZIO (será populado em deferred)
    if ctk is not None:
        content_container = ctk.CTkFrame(app, fg_color=APP_BG, corner_radius=0)
    else:
        content_container = tk.Frame(app)
    content_container.pack(fill="both", expand=True)

    # 7. Variáveis Tkinter
    clients_count_var = tk.StringVar(master=app, value="0 clientes")
    status_var_dot = tk.StringVar(master=app, value="")
    status_var_text = tk.StringVar(
        master=app,
        value=(getattr(app_status, "status_text", None) or "LOCAL"),
    )

    # Criar separadores como placeholders
    SEP_H = 2
    sep_menu_toolbar = ctk.CTkFrame(app, height=SEP_H, corner_radius=0, fg_color=SEP)
    sep_toolbar_main = ctk.CTkFrame(app, height=SEP_H, corner_radius=0, fg_color=SEP)

    return MainWindowLayoutRefs(
        sep_menu_toolbar=sep_menu_toolbar,
        sep_toolbar_main=sep_toolbar_main,
        topbar=None,  # type: ignore[arg-type]  # Será criado em deferred
        menu=None,  # type: ignore[arg-type]  # Será criado em deferred
        content_container=content_container,
        nav=None,  # type: ignore[arg-type]  # Será criado em deferred
        footer=None,  # type: ignore[arg-type]  # Será criado em deferred
        clients_count_var=clients_count_var,
        status_var_dot=status_var_dot,
        status_var_text=status_var_text,
    )


def _build_layout_deferred(app: App, refs: MainWindowLayoutRefs) -> None:
    """FASE 2: Cria componentes complexos (topbar, menu, footer, nav).

    Executado via after(0) para não bloquear renderização inicial.
    Instrumentado com perf_timer quando RC_PROFILE_STARTUP=1.
    """
    from src.core.utils.perf_timer import perf_timer
    from src.ui.topbar import TopBar
    from src.ui.menu_bar import AppMenuBar
    from src.ui.status_footer import StatusFooter
    from src.core.navigation_controller import NavigationController

    with perf_timer("startup.build_layout_deferred", log, threshold_ms=100):
        # Verificar se app ainda existe (evitar crash se fechou rápido)
        if not app.winfo_exists():
            log.warning("App foi fechado antes de deferred completar")
            return

        # 1. Separadores
        refs.sep_menu_toolbar.pack(side="top", fill="x", pady=0)
        try:
            refs.sep_menu_toolbar.pack_propagate(False)
        except (AttributeError, Exception):
            pass

        # 2. TopBar
        topbar = TopBar(
            app,
            on_home=app.show_hub_screen,
            on_pdf_converter=app.run_pdf_batch_converter,
            on_pdf_viewer=app._open_pdf_viewer_empty,
            on_chatgpt=app.open_chatgpt_window,
            on_sites=app.show_sites_screen,
            on_notifications_clicked=app._on_notifications_clicked,
            on_mark_all_read=app._mark_all_notifications_read,
            on_delete_notification_for_me=app._delete_notification_for_me,
            on_delete_all_notifications_for_me=app._delete_all_notifications_for_me,
        )
        topbar.pack(side="top", fill="x")

        # 3. Separador pós-topbar
        refs.sep_toolbar_main.pack(side="top", fill="x", pady=0)
        try:
            refs.sep_toolbar_main.pack_propagate(False)
        except (AttributeError, Exception):
            pass

        # 4. AppMenuBar
        menu = AppMenuBar(
            app,
            on_home=app.show_hub_screen,
            on_refresh=app.refresh_current_view,
            on_quit=app._on_menu_logout,
            on_toggle_theme=app._handle_toggle_theme,
        )
        menu.attach()

        # 5. NavigationController
        nav = NavigationController(refs.content_container, frame_factory=app._frame_factory)

        # 6. StatusFooter
        footer = StatusFooter(app, show_trash=False)
        footer.pack(side="bottom", fill="x")
        footer.set_count(0)
        footer.set_user(None)
        footer.set_cloud("UNKNOWN")

        # Atualizar refs (sobrescrever placeholders)
        refs.topbar = topbar
        refs.menu = menu
        refs.nav = nav
        refs.footer = footer

        log.debug("Layout deferred completo")


def _apply_window_icon(app: App, icon_path_relative: str) -> None:
    """Aplica ícone da aplicação (private helper)."""
    from src.modules.main_window.views.helpers import resource_path

    try:
        icon_path = resource_path(icon_path_relative)
        # Logar apenas basename para evitar expor paths completos
        icon_name = os.path.basename(icon_path)
        log.info("Aplicando ícone: %s", icon_name)
        if os.path.exists(icon_path):
            try:
                app.iconbitmap(icon_path)
                log.debug("Ícone principal aplicado: %s", icon_name)

                # Tentar definir como ícone default para novos Toplevels
                try:
                    app.iconbitmap(default=icon_path)
                    log.debug("Ícone default aplicado para novos diálogos")
                except Exception:
                    log.debug("Ícone default não suportado neste ambiente", exc_info=True)

            except Exception:
                log.warning("iconbitmap falhou, tentando iconphoto com PNG", exc_info=True)
                # Fallback: usar rc.png
                try:
                    png_path = resource_path("rc.png")
                    if os.path.exists(png_path):
                        img = tk.PhotoImage(file=png_path)
                        app.iconphoto(True, img)
                        log.info("iconphoto aplicado com sucesso usando rc.png")
                except Exception:
                    log.error("iconphoto com PNG também falhou", exc_info=True)
        else:
            log.warning("Ícone %s não encontrado em: %s", icon_path_relative, icon_path)
    except Exception:
        log.exception("Falha ao aplicar ícone da aplicação")
