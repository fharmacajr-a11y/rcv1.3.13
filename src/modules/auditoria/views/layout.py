from __future__ import annotations

from src.ui.ctk_config import ctk

"""Helpers for building the Auditoria UI layout."""

import logging
import tkinter as tk
from typing import TYPE_CHECKING, Optional

from .components import AuditoriaListPanel, AuditoriaToolbar

logger = logging.getLogger(__name__)

if TYPE_CHECKING:  # pragma: no cover
    from .main_frame import AuditoriaFrame


def build_auditoria_ui(frame: "AuditoriaFrame") -> None:
    """Create the full Auditoria UI inside the provided frame."""
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(2, weight=1)

    ui_gap = getattr(frame, "UI_GAP", 6)
    ui_padx = getattr(frame, "UI_PADX", 8)
    ui_pady = getattr(frame, "UI_PADY", 6)

    toolbar = AuditoriaToolbar(
        frame,
        ui_gap=ui_gap,
        ui_padx=ui_padx,
        ui_pady=ui_pady,
        search_var=getattr(frame, "search_var", getattr(frame, "_search_var", None)),
        cliente_var=getattr(frame, "cliente_var", getattr(frame, "_cliente_var", None)),
        on_search_change=lambda text: frame._filtra_clientes(text),
        on_clear_filter=getattr(frame, "on_limpar_busca", frame._clear_search),
        on_cliente_selected=lambda: frame._on_cliente_selected(),
    )
    toolbar.grid(row=0, column=0, sticky="ew", padx=ui_padx, pady=(ui_pady, 0))
    frame.toolbar = toolbar
    frame.search_var = toolbar.search_var
    frame._search_var = toolbar.search_var
    frame.entry_busca = toolbar.entry_busca
    frame.ent_busca = toolbar.entry_busca
    frame.btn_limpar = toolbar.btn_limpar
    frame.cliente_var = toolbar.cliente_var
    frame._cliente_var = toolbar.cliente_var
    frame.combo_cliente = toolbar.combo_cliente
    frame.cmb_cliente = toolbar.combo_cliente

    frame.sep_top = ctk.CTkFrame(frame, height=2)  # Separador horizontal
    frame.sep_top.grid(row=1, column=0, sticky="ew", padx=ui_padx, pady=(0, ui_gap))

    list_panel = AuditoriaListPanel(
        frame,
        ui_gap=ui_gap,
        ui_padx=ui_padx,
        ui_pady=ui_pady,
        on_tree_select=frame._on_auditoria_select,
        on_open_status_menu=frame._open_status_menu,
        on_start_auditoria=getattr(frame, "on_iniciar_auditoria", frame._on_iniciar),
        on_view_subpastas=getattr(frame, "on_ver_subpastas", frame._open_subpastas),
        on_upload_files=getattr(frame, "on_enviar_arquivos", frame._upload_archive_to_auditoria),
        on_delete=getattr(frame, "on_excluir", frame._delete_auditorias),
    )
    list_panel.grid(row=2, column=0, sticky="nsew", padx=ui_padx, pady=(0, ui_pady))
    frame.list_panel = list_panel
    frame.list_frame = list_panel
    frame.tree_container = list_panel.tree_container
    frame.tree = list_panel.tree
    frame.lbl_notfound = list_panel.lbl_notfound
    frame.lf_actions = list_panel.actions_frame
    frame.btn_iniciar = list_panel.btn_iniciar
    frame.btn_subpastas = list_panel.btn_subpastas
    frame.btn_enviar = list_panel.btn_enviar
    frame.btn_excluir = list_panel.btn_excluir
    frame._btn_h_ver = frame.btn_subpastas
    frame._btn_h_enviar_zip = frame.btn_enviar
    frame._btn_h_delete = frame.btn_excluir

    try:
        frame.bind_all("<F5>", lambda event: frame._load_auditorias())
    except Exception as exc:  # noqa: BLE001
        logger.debug("Falha ao registrar atalho F5 na Auditoria: %s", exc)
    add_refresh_menu_entry(frame)


def add_refresh_menu_entry(frame: "AuditoriaFrame") -> None:
    """Ensure the refresh action exists in the top menu."""
    if getattr(frame, "_menu_refresh_added", False):
        return

    try:
        root = frame.winfo_toplevel()
    except Exception as exc:  # noqa: BLE001
        logger.debug("Falha ao obter toplevel para Auditoria: %s", exc)
        return
    if not root or not root.winfo_exists():
        return

    menu_name: Optional[str]
    try:
        menu_name = root["menu"]
    except Exception as exc:  # noqa: BLE001
        logger.debug("Janela sem menu configurado: %s", exc)
        menu_name = None
    if not menu_name:
        return

    try:
        top_widget = root.nametowidget(menu_name)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Falha ao localizar widget de menu principal: %s", exc)
        return
    if not isinstance(top_widget, tk.Menu):
        return
    top_menu: tk.Menu = top_widget

    exibir_menu: Optional[tk.Menu] = None
    try:
        top_end = top_menu.index("end")
    except Exception as exc:  # noqa: BLE001
        logger.debug("Menu principal sem entradas: %s", exc)
        top_end = None
    if top_end is not None:
        for idx in range(top_end + 1):
            try:
                if top_menu.type(idx) == "cascade" and top_menu.entrycget(idx, "label") == "Exibir":
                    submenu_name = top_menu.entrycget(idx, "menu")
                    candidate = top_menu.nametowidget(submenu_name)
                    if isinstance(candidate, tk.Menu):
                        exibir_menu = candidate
                        break
            except Exception as exc:  # noqa: BLE001
                logger.debug("Falha ao inspecionar item de menu Exibir: %s", exc)
                continue

    if exibir_menu is None:
        exibir_menu = tk.Menu(top_menu, tearoff=False)
        top_menu.add_cascade(label="Exibir", menu=exibir_menu)

    if not isinstance(exibir_menu, tk.Menu):
        return
    menu_exibir: tk.Menu = exibir_menu

    try:
        end_index = menu_exibir.index("end")
    except Exception as exc:  # noqa: BLE001
        logger.debug("Menu 'Exibir' sem entradas: %s", exc)
        end_index = None
    if end_index is not None:
        for idx in range(end_index + 1):
            try:
                if menu_exibir.entrycget(idx, "label") == "Recarregar lista":
                    frame._menu_refresh_added = True
                    return
            except Exception as exc:  # noqa: BLE001
                logger.debug("Falha ao inspecionar entradas do menu 'Exibir': %s", exc)
                continue

    try:
        menu_exibir.add_command(label="Recarregar lista", accelerator="F5", command=frame._do_refresh)
        frame._menu_refresh_added = True
    except Exception as exc:  # noqa: BLE001
        logger.debug("Falha ao adicionar comando 'Recarregar lista': %s", exc)
