# -*- coding: utf-8 -*-
"""
Main Window Layout Builder.

Responsável por construir toda a estrutura visual do MainWindow (frames, separadores,
topbar, menu, footer) SEM lógica de negócio ou navegação.

Extraído de main_window.py como parte de P2-MF "MainWindow Layout Extraction"
para reduzir MainWindow a ~500 linhas (apenas orquestrador).
"""

from __future__ import annotations

import logging
import os
import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk
from typing import TYPE_CHECKING

import ttkbootstrap as tb

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
    sep_menu_toolbar: ttk.Separator
    sep_toolbar_main: ttk.Separator

    # Componentes principais
    topbar: TopBar
    menu: AppMenuBar
    content_container: tb.Frame
    nav: NavigationController
    footer: StatusFooter

    # Variáveis Tkinter
    clients_count_var: tk.StringVar
    status_var_dot: tk.StringVar
    status_var_text: tk.StringVar


def build_main_window_layout(
    app: App,
    *,
    theme_name: str,
    start_hidden: bool = False,
) -> MainWindowLayoutRefs:
    """Constrói toda a estrutura visual do MainWindow.

    Args:
        app: Instância de MainWindow (App)
        theme_name: Nome do tema ttkbootstrap a usar
        start_hidden: Se True, oculta janela após construção

    Returns:
        MainWindowLayoutRefs com todas as referências aos componentes criados

    Responsabilidades:
        - Criar separadores horizontais
        - Criar TopBar (com callbacks passados)
        - Aplicar ícone da aplicação
        - Criar AppMenuBar
        - Configurar protocol WM_DELETE_WINDOW
        - Criar container de conteúdo + NavigationController
        - Criar StatusFooter
        - Criar variáveis Tkinter (clients_count_var, status_var, etc)

    NÃO responsável por:
        - Registrar telas no router (feito por _register_screens)
        - Iniciar pollers/jobs (feito por MainWindowPollers)
        - Lógica de navegação (feito por ScreenRouter)
        - Bind de atalhos globais (feito por bind_global_shortcuts)
    """
    from src.modules.main_window.views.constants import APP_ICON_PATH, APP_TITLE, APP_VERSION
    from src.modules.main_window.views.state_helpers import (
        build_app_title,
        format_version_string,
    )
    from src.ui.window_policy import apply_fit_policy
    from src.utils.themes import apply_combobox_style
    from src import app_status

    # 1. Separadores horizontais
    sep_menu_toolbar = ttk.Separator(app, orient="horizontal")
    sep_menu_toolbar.pack(side="top", fill="x", pady=0)

    # 2. TopBar (precisa de callbacks do app)
    topbar = TopBar(
        app,
        on_home=app.show_hub_screen,
        on_pdf_converter=app.run_pdf_batch_converter,
        on_pdf_viewer=app._open_pdf_viewer_empty,
        on_chatgpt=app.open_chatgpt_window,
        on_sites=app.show_sites_screen,
        on_notifications_clicked=app._on_notifications_clicked,
        on_mark_all_read=app._mark_all_notifications_read,
    )
    topbar.pack(side="top", fill="x")

    # Separador após topbar
    sep_toolbar_main = ttk.Separator(app, orient="horizontal")
    sep_toolbar_main.pack(side="top", fill="x", pady=0)

    # 3. Ícone da aplicação
    _apply_window_icon(app, APP_ICON_PATH)

    # 4. Protocol WM_DELETE_WINDOW
    app.protocol("WM_DELETE_WINDOW", app._confirm_exit)

    # 5. AppMenuBar
    menu = AppMenuBar(
        app,
        on_home=app.show_hub_screen,
        on_refresh=app.refresh_current_view,
        on_quit=app._on_menu_logout,
        on_change_theme=app._handle_menu_theme_change,
    )
    menu.attach()
    try:
        menu.refresh_theme(theme_name)
    except Exception as exc:  # noqa: BLE001
        log.debug("Falha ao atualizar tema do menu: %s", exc)

    # 6. Aplicar theme e combobox style
    try:
        app_style = tb.Style()
        app_style.theme_use(theme_name)
        apply_combobox_style(app_style)
    except Exception as exc:  # noqa: BLE001
        log.debug("Falha ao aplicar tema via Style: %s", exc)

    # 7. Título da janela
    version_str = format_version_string(APP_VERSION)
    window_title = build_app_title(APP_TITLE, version_str)
    app.title(window_title)

    # 8. Aplicar política Fit-to-WorkArea
    # BUGFIX-UX-STARTUP-HUB-001 (A2): Instrumentação antes/depois
    if os.getenv("RC_DEBUG_STARTUP_UI") == "1":
        log.info(
            "[UI] ANTES apply_fit_policy: state=%s, viewable=%s, geometry=%s",
            app.state(),
            app.winfo_viewable(),
            app.geometry(),
        )

    apply_fit_policy(app)

    if os.getenv("RC_DEBUG_STARTUP_UI") == "1":
        log.info(
            "[UI] DEPOIS apply_fit_policy: state=%s, viewable=%s, geometry=%s",
            app.state(),
            app.winfo_viewable(),
            app.geometry(),
        )

    # 9. Ocultar janela se start_hidden
    if start_hidden:
        try:
            app.withdraw()
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao ocultar janela: %s", exc)

    # 10. Container de conteúdo + NavigationController
    content_container = tb.Frame(app)
    content_container.pack(fill="both", expand=True)

    nav = NavigationController(content_container, frame_factory=app._frame_factory)

    # 11. StatusFooter
    footer = StatusFooter(app, show_trash=False)
    footer.pack(side="bottom", fill="x")
    footer.set_count(0)
    footer.set_user(None)
    footer.set_cloud("UNKNOWN")

    # 12. Variáveis Tkinter
    clients_count_var = tk.StringVar(master=app, value="0 clientes")
    status_var_dot = tk.StringVar(master=app, value="")
    status_var_text = tk.StringVar(
        master=app,
        value=(getattr(app_status, "status_text", None) or "LOCAL"),
    )

    return MainWindowLayoutRefs(
        sep_menu_toolbar=sep_menu_toolbar,
        sep_toolbar_main=sep_toolbar_main,
        topbar=topbar,
        menu=menu,
        content_container=content_container,
        nav=nav,
        footer=footer,
        clients_count_var=clients_count_var,
        status_var_dot=status_var_dot,
        status_var_text=status_var_text,
    )


def _apply_window_icon(app: App, icon_path_relative: str) -> None:
    """Aplica ícone da aplicação (private helper)."""
    from src.modules.main_window.views.helpers import resource_path

    try:
        icon_path = resource_path(icon_path_relative)
        log.info("Tentando aplicar ícone da aplicação: %s", icon_path)
        if os.path.exists(icon_path):
            try:
                app.iconbitmap(icon_path)
                log.info("iconbitmap aplicado com sucesso: %s", icon_path)
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
