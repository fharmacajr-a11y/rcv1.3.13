# -*- coding: utf-8 -*-
# pyright: strict, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportPrivateUsage=false

"""Builders da tela principal de clientes (toolbar, lista, footer e banner)."""

from __future__ import annotations

import _tkinter
import logging
import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING, Any

try:
    import ttkbootstrap as tb
except Exception:
    tb = ttk  # fallback

if TYPE_CHECKING:
    from src.modules.clientes.views.main_screen import MainScreenFrame

from src.modules.clientes.components.helpers import STATUS_CHOICES
from src.modules.clientes.views.footer import ClientesFooter

# CustomTkinter ActionBar (Microfase 3)
# Evita redefinição de constantes (Microfase 7): variáveis internas em lowercase
_use_ctk_actionbar = False
ClientesActionBarCtk = None  # type: ignore[assignment,misc]

try:
    from src.modules.clientes.views.actionbar_ctk import ClientesActionBarCtk, HAS_CUSTOMTKINTER

    _use_ctk_actionbar = HAS_CUSTOMTKINTER
except ImportError:
    pass

USE_CTK_ACTIONBAR: bool = _use_ctk_actionbar

# CustomTkinter Scrollbar (Microfase 4)
# Evita redefinição de constantes (Microfase 7): variáveis internas em lowercase
_use_ctk_scrollbar = False
CTkScrollbar = None  # type: ignore[assignment,misc]

try:
    if USE_CTK_ACTIONBAR:  # Reutiliza HAS_CUSTOMTKINTER via USE_CTK_ACTIONBAR
        from src.ui.ctk_config import ctk

        CTkScrollbar = ctk.CTkScrollbar  # type: ignore[union-attr]

        _use_ctk_scrollbar = True
except (ImportError, NameError, AttributeError):
    pass

USE_CTK_SCROLLBAR: bool = _use_ctk_scrollbar

from src.modules.clientes.views.main_screen_constants import (  # noqa: E402
    COLUMN_CHECKBOX_WIDTH,
    COLUMN_CONTROL_PADDING,
    COLUMN_CONTROL_Y_OFFSET,
    COLUMN_MAX_WIDTH,
    COLUMN_MIN_WIDTH,
    COLUMN_PADDING,
    DEFAULT_COLUMN_ORDER,
    HEADER_CTRL_H,
    PICK_MODE_BANNER_FONT,
    PICK_MODE_BANNER_TEXT,
    PICK_MODE_CANCEL_TEXT,
    PICK_MODE_SELECT_TEXT,
    SEPARATOR_PADX,
    SEPARATOR_PADY_BOTTOM,
    SEPARATOR_PADY_TOP,
    TOOLBAR_PADX,
    TOOLBAR_PADY,
)
from src.modules.clientes.views.main_screen_helpers import normalize_order_label  # noqa: E402

# Tenta importar toolbar CustomTkinter, senão usa legada
# Evita redefinição de constantes (Microfase 7): variáveis internas em lowercase
_use_ctk_toolbar = False
ClientesToolbarCtk = None  # type: ignore[misc,assignment]

try:
    from src.modules.clientes.views.toolbar_ctk import ClientesToolbarCtk

    _use_ctk_toolbar = _use_ctk_actionbar  # Reutiliza o status do actionbar (ambos dependem de customtkinter)
except ImportError:
    pass

USE_CTK_TOOLBAR: bool = _use_ctk_toolbar

from src.modules.clientes.views.toolbar import ClientesToolbar  # noqa: E402
from src.ui.components import create_clients_treeview  # noqa: E402
from src.utils.prefs import load_columns_visibility, save_columns_visibility  # noqa: E402

log = logging.getLogger("app_gui")

# Constantes para switchbar de controle de colunas
SWITCHBAR_HEIGHT = 30
SWITCHCELL_HEIGHT = 30


def build_toolbar(frame: MainScreenFrame) -> None:
    """Cria a toolbar com filtros, busca e botão de lixeira."""

    def _handle_open_trash():
        if frame._pick_mode_manager.get_snapshot().is_pick_mode_active:
            return
        result = frame._actions.handle_open_trash()
        frame._handle_action_result(result, "abrir lixeira")
        frame._update_main_buttons_state()

    # Usa toolbar CustomTkinter se disponível, senão fallback para legada
    theme_manager = getattr(frame, "_theme_manager", None)

    if USE_CTK_TOOLBAR and ClientesToolbarCtk is not None:
        log.info("Usando toolbar CustomTkinter")
        frame.toolbar = ClientesToolbarCtk(
            frame,
            order_choices=list(frame._order_choices.keys()),
            default_order=frame._default_order_label,
            status_choices=STATUS_CHOICES,
            on_search_changed=lambda text: frame._buscar(text),
            on_clear_search=frame._limpar_busca,
            on_order_changed=frame._on_order_changed,
            on_status_changed=lambda _value: frame.apply_filters(),
            on_open_trash=_handle_open_trash,
            theme_manager=theme_manager,
        )
    else:
        log.info("Usando toolbar legada (ttk/ttkbootstrap)")
        frame.toolbar = ClientesToolbar(
            frame,
            order_choices=list(frame._order_choices.keys()),
            default_order=frame._default_order_label,
            status_choices=STATUS_CHOICES,
            on_search_changed=lambda text: frame._buscar(text),
            on_clear_search=frame._limpar_busca,
            on_order_changed=frame._on_order_changed,
            on_status_changed=lambda _value: frame.apply_filters(),
            on_open_trash=_handle_open_trash,
        )

    frame.toolbar.pack(fill="x", padx=TOOLBAR_PADX, pady=TOOLBAR_PADY)

    frame.var_busca = frame.toolbar.var_busca
    frame.var_ordem = frame.toolbar.var_ordem

    normalized_order = normalize_order_label(frame.var_ordem.get())
    if normalized_order != frame.var_ordem.get():
        frame.var_ordem.set(normalized_order)
    frame._current_order_by = normalized_order

    frame.var_status = frame.toolbar.var_status
    frame.status_filter = frame.toolbar.status_combobox
    frame.entry_busca = frame.toolbar.entry_busca
    frame.btn_lixeira = frame.toolbar.lixeira_button

    frame.status_menu = None
    frame._status_menu_cliente = None
    frame._status_menu_row = None


def build_tree_and_column_controls(frame: MainScreenFrame) -> None:
    """Cria a Treeview de clientes e os controles de colunas."""

    frame._cols_separator = ttk.Separator(frame, orient="horizontal")  # type: ignore[attr-defined]
    frame._cols_separator.pack(
        side="top", fill="x", padx=SEPARATOR_PADX, pady=(SEPARATOR_PADY_TOP, SEPARATOR_PADY_BOTTOM)
    )

    frame.columns_align_bar = tk.Frame(frame, height=HEADER_CTRL_H)  # type: ignore[attr-defined]
    frame.columns_align_bar.pack(side="top", fill="x", padx=SEPARATOR_PADX)

    frame._col_order = DEFAULT_COLUMN_ORDER

    frame._user_key = (
        getattr(frame, "current_user_email", None) or getattr(frame, "status_user_email", None) or "default"
    )

    from src.modules.clientes.controllers.column_manager import ColumnManager

    frame._column_manager = ColumnManager(
        initial_order=frame._col_order,
        initial_visibility=None,
        mandatory_columns=None,
    )

    from src.modules.clientes.controllers.column_controls_layout import ColumnControlsLayout

    frame._column_controls_layout = ColumnControlsLayout()

    frame._column_manager.load_from_prefs(load_columns_visibility, frame._user_key)

    column_state = frame._column_manager.get_state()
    frame._col_content_visible = {
        c: tk.BooleanVar(value=column_state.visibility[c])  # type: ignore[attr-defined]
        for c in frame._col_order
    }

    def _persist_visibility():
        frame._column_manager.save_to_prefs(save_columns_visibility, frame._user_key)

    def _on_toggle(col: str):
        frame._column_manager.toggle(col)
        frame._column_manager.sync_to_ui_vars(frame._col_content_visible)
        frame._refresh_rows()
        _persist_visibility()

    frame.client_list_container = tk.Frame(frame)  # type: ignore[attr-defined]
    frame.client_list_container.pack(expand=True, fill="both", padx=10, pady=5)

    frame.client_list = create_clients_treeview(
        frame.client_list_container,
        on_double_click=frame._on_double_click,
        on_select=frame._update_main_buttons_state,
        on_delete=frame._on_tree_delete_key,
        on_click=frame._on_click,
    )

    # Scrollbar vertical (CustomTkinter se disponível, senão ttk)
    if USE_CTK_SCROLLBAR and CTkScrollbar:
        frame.clients_scrollbar = CTkScrollbar(
            frame.client_list_container,
            orientation="vertical",
            command=frame.client_list.yview,
        )
    else:
        frame.clients_scrollbar = tb.Scrollbar(
            frame.client_list_container,
            orient="vertical",
            command=frame.client_list.yview,
        )

    frame.client_list.configure(yscrollcommand=frame.clients_scrollbar.set)

    frame.client_list.grid(row=0, column=0, sticky="nsew")
    frame.clients_scrollbar.grid(row=0, column=1, sticky="ns")
    frame.client_list_container.rowconfigure(0, weight=1)
    frame.client_list_container.columnconfigure(0, weight=1)

    frame.tree = frame.client_list

    frame.client_list.bind("<Button-1>", frame._on_click, add="+")
    frame.client_list.bind("<Button-3>", frame._on_right_click, add="+")  # botão direito
    frame.client_list.bind("<Button-2>", frame._on_right_click, add="+")  # botão direito (mac)

    frame.client_list.configure(displaycolumns=frame._col_order)

    for col in frame._col_order:
        try:
            cur = frame.client_list.heading(col, option="text")
            if not cur:
                friendly = {
                    "Razao Social": "Razão Social",
                    "Observacoes": "Observações",
                    "Ultima Alteracao": "Última Alteração",
                }.get(col, col)
                # Todos os headings centralizados (incluindo WhatsApp)
                frame.client_list.heading(col, text=friendly, anchor="center")
            else:
                # Todos os headings centralizados (incluindo WhatsApp)
                frame.client_list.heading(col, text=cur, anchor="center")
        except Exception as e:
            log.debug("Erro ao configurar heading %s: %s", col, e)

    # Inicializar atributos para switches
    frame._switch_tree = frame.client_list  # type: ignore[attr-defined]
    frame._switch_cells = {}  # type: ignore[attr-defined]
    frame._switch_job = None  # type: ignore[attr-defined]
    frame._switchbar_bound = False  # type: ignore[attr-defined] # Flag anti-bind-duplicado
    frame._col_ctrls = {}

    # Configurar altura mínima da barra (evita cortar switches)
    frame.columns_align_bar.configure(height=SWITCHBAR_HEIGHT)
    try:
        frame.columns_align_bar.grid_propagate(False)
    except Exception:  # noqa: BLE001
        pass

    # Criar cell frames (um por coluna) para alinhamento perfeito
    for i, col in enumerate(frame._col_order):
        # Cell frame com altura fixa
        cell = tb.Frame(frame.columns_align_bar, height=SWITCHCELL_HEIGHT)
        cell.grid(row=0, column=i, sticky="nsew")
        cell.grid_propagate(False)  # Não deixar grid encolher e cortar o switch

        # Switch round-toggle SEM TEXTO
        # Fix Microfase 19.2: Fallback robusto se layout Round.Toggle não existir
        try:
            chk = tb.Checkbutton(
                cell,
                text="",  # SEM TEXTO - apenas o switch
                variable=frame._col_content_visible[col],
                command=lambda c=col: _on_toggle(c),  # type: ignore[misc]
                bootstyle="info-round-toggle",
                cursor="hand2",
                takefocus=False,
            )
        except _tkinter.TclError as exc:
            # Fallback: usar checkbutton simples se tema não suportar round-toggle
            log.debug("Round toggle não disponível, usando checkbutton padrão: %s", exc)
            chk = tb.Checkbutton(
                cell,
                text="",
                variable=frame._col_content_visible[col],
                command=lambda c=col: _on_toggle(c),  # type: ignore[misc]
                cursor="hand2",
                takefocus=False,
            )
        # Usar place para centralização matemática perfeita (elimina qualquer viés de padding/anchor)
        chk.place(relx=0.5, rely=0.5, anchor="center")

        frame._col_ctrls[col] = {"frame": cell, "check": chk}
        frame._switch_cells[col] = cell  # type: ignore[attr-defined]

    # Funções de sincronização
    def _schedule_sync_switchbar(*_: Any) -> None:
        """Agenda sincronização com debounce."""
        if frame._switch_job is not None:  # type: ignore[attr-defined]
            try:
                frame.client_list.after_cancel(frame._switch_job)  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001
                pass
        frame._switch_job = frame.client_list.after(60, _sync_switchbar_to_tree)  # type: ignore[attr-defined]

    def _sync_switchbar_to_tree() -> None:
        """Sincroniza largura dos cells com as colunas do Treeview."""
        frame._switch_job = None  # type: ignore[attr-defined]
        try:
            # Garante que widths já estejam assentados
            frame.client_list.update_idletasks()

            for col, cell in frame._switch_cells.items():  # type: ignore[attr-defined]
                try:
                    w = int(frame.client_list.column(col, "width"))
                    cell.configure(width=w)
                except Exception:  # noqa: BLE001
                    pass
        except Exception:  # noqa: BLE001
            pass

    # Sincronizar após criar (when Tk calculates sizes)
    # Fazemos 2 sincronizações: uma imediata e outra com delay
    # para garantir que os widths finais sejam aplicados
    frame.columns_align_bar.after_idle(_schedule_sync_switchbar)
    frame.columns_align_bar.after(120, _schedule_sync_switchbar)

    # Sincronizar quando Treeview redimensionar (com debounce) - apenas uma vez
    if not frame._switchbar_bound:  # type: ignore[attr-defined]
        frame.client_list.bind("<Configure>", _schedule_sync_switchbar, add="+")
        frame._switchbar_bound = True  # type: ignore[attr-defined]

    # Inicializa atributo para tracking do callback pendente (debounce)
    frame._col_controls_after_id: str | None = None  # type: ignore[attr-defined]
    frame._col_controls_bound = False  # type: ignore[attr-defined] # Flag anti-bind-duplicado

    def _sync_col_controls() -> None:
        """Executa o reposicionamento dos controles de coluna UMA vez (sem se reagendar)."""
        try:
            base_left = frame.client_list.winfo_rootx() - frame.columns_align_bar.winfo_rootx()

            items = frame.client_list.get_children()
            first_item = items[0] if items else None

            column_widths: dict[str, int] = {}
            cumulative_x = 0

            for col in frame._col_order:
                bx = None
                if first_item:
                    bx = frame.client_list.bbox(first_item, col)
                    if not bx:
                        col_w = int(frame.client_list.column(col, option="width"))  # pyright: ignore
                        bx = (cumulative_x, 0, col_w, 0)
                        cumulative_x += col_w
                else:
                    col_w = int(frame.client_list.column(col, option="width"))  # pyright: ignore
                    bx = (cumulative_x, 0, col_w, 0)
                    cumulative_x += col_w

                if bx:
                    _, _, col_w, _ = bx
                    column_widths[col] = col_w

            required_widths = {
                col: frame._col_ctrls[col]["label"].winfo_reqwidth() + COLUMN_CHECKBOX_WIDTH + COLUMN_CONTROL_PADDING
                for col in frame._col_order
            }

            geoms = frame._column_controls_layout.compute_column_geometries(
                frame._col_order,
                column_widths,
            )
            placements = frame._column_controls_layout.compute_control_placements(
                geoms,
                required_widths,
                min_width=COLUMN_MIN_WIDTH,
                max_width=COLUMN_MAX_WIDTH,
                padding=COLUMN_PADDING,
            )

            for col, placement in placements.items():
                control_frame = frame._col_ctrls[col]["frame"]
                x = base_left + placement.x
                control_frame.place_configure(
                    x=x,
                    y=COLUMN_CONTROL_Y_OFFSET,
                    width=placement.width,
                    height=HEADER_CTRL_H - COLUMN_CONTROL_PADDING,
                )

        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao posicionar controles de colunas: %s", exc)

    def _schedule_sync_col_controls(delay_ms: int = 60) -> None:
        """Agenda _sync_col_controls com debounce (cancela agendamento anterior)."""
        _cancel_scheduled_sync_col_controls()
        frame._col_controls_after_id = frame.after(delay_ms, _sync_col_controls)

    def _cancel_scheduled_sync_col_controls() -> None:
        """Cancela agendamento pendente de _sync_col_controls, se existir."""
        if frame._col_controls_after_id is not None:
            try:
                frame.after_cancel(frame._col_controls_after_id)
            except Exception:  # noqa: BLE001
                pass  # Tk pode lançar erro se já foi executado/cancelado
            frame._col_controls_after_id = None

    # Expõe a função de cancelamento no frame para uso no destroy()
    frame._cancel_scheduled_sync_col_controls = _cancel_scheduled_sync_col_controls  # type: ignore[attr-defined]
    # Expõe a função de agendamento para uso em _on_toggle_with_labels
    frame._schedule_sync_col_controls_fn = _schedule_sync_col_controls  # type: ignore[attr-defined]

    # Bind do Configure apenas uma vez para evitar acúmulo de callbacks
    if not frame._col_controls_bound:  # type: ignore[attr-defined]
        frame.client_list.bind("<Configure>", lambda e: _schedule_sync_col_controls())  # type: ignore[misc]
        frame._col_controls_bound = True  # type: ignore[attr-defined]

    try:
        old_cmd = frame.client_list.cget("xscrollcommand")

        def _xscroll_proxy(*args: Any) -> None:
            if old_cmd:
                try:
                    func = frame.nametowidget(old_cmd.split()[0])
                    func.set(*args)
                except Exception as inner_exc:  # noqa: BLE001
                    log.debug("Falha ao atualizar scrollbar horizontal: %s", inner_exc)
            _schedule_sync_col_controls()

        frame.client_list.configure(xscrollcommand=_xscroll_proxy)

    except Exception as exc:  # noqa: BLE001
        log.debug("Falha ao configurar proxy de scrollbar horizontal: %s", exc)

    # Inicialização: agenda após layout estabilizar (after_idle + schedule)
    frame.after_idle(lambda: _schedule_sync_col_controls(100))


def build_footer(frame: MainScreenFrame) -> None:
    """Cria o footer com ações CRUD e batch operations."""

    def _handle_new():
        if frame._pick_mode_manager.get_snapshot().is_pick_mode_active:
            return
        result = frame._actions.handle_new()
        frame._handle_action_result(result, "criar novo cliente")
        frame._update_main_buttons_state()

    def _handle_edit():
        if frame._pick_mode_manager.get_snapshot().is_pick_mode_active:
            return
        result = frame._actions.handle_edit()
        frame._handle_action_result(result, "editar cliente")
        frame._update_main_buttons_state()

    def _handle_subpastas():
        if frame._pick_mode_manager.get_snapshot().is_pick_mode_active:
            return
        result = frame._actions.handle_open_subfolders()
        frame._handle_action_result(result, "abrir subpastas")
        frame._update_main_buttons_state()

    # Usa actionbar CustomTkinter se disponível, senão fallback para legada
    theme_manager = getattr(frame, "_theme_manager", None)

    if USE_CTK_ACTIONBAR and ClientesActionBarCtk is not None:
        log.info("Usando actionbar CustomTkinter")
        frame.footer = ClientesActionBarCtk(
            frame,
            on_novo=_handle_new,
            on_editar=_handle_edit,
            on_subpastas=_handle_subpastas,
            on_excluir=frame.on_delete_selected_clients,
            theme_manager=theme_manager,
        )
    else:
        log.info("Usando actionbar legada (ttk/ttkbootstrap)")
        frame.footer = ClientesFooter(
            frame,
            on_novo=_handle_new,
            on_editar=_handle_edit,
            on_subpastas=_handle_subpastas,
            on_excluir=frame.on_delete_selected_clients,
            on_batch_delete=frame._on_batch_delete_clicked,
            on_batch_restore=frame._on_batch_restore_clicked,
            on_batch_export=frame._on_batch_export_clicked,
        )

    frame.footer.pack(fill="x", padx=10, pady=10)

    frame.btn_novo = frame.footer.btn_novo
    frame.btn_editar = frame.footer.btn_editar
    frame.btn_subpastas = frame.footer.btn_subpastas
    frame.btn_excluir = frame.footer.btn_excluir

    frame.btn_batch_delete = frame.footer.btn_batch_delete
    frame.btn_batch_restore = frame.footer.btn_batch_restore
    frame.btn_batch_export = frame.footer.btn_batch_export

    frame._uploading_busy = False
    frame._last_cloud_state = None  # type: ignore[assignment]


def build_pick_mode_banner(frame: MainScreenFrame) -> None:
    """Cria o banner do modo seleção (pick mode)."""

    frame._pick_banner_frame = tb.Frame(frame, bootstyle="info")

    frame._pick_label = tb.Label(
        frame._pick_banner_frame,
        text=PICK_MODE_BANNER_TEXT,
        font=PICK_MODE_BANNER_FONT,  # pyright: ignore
        bootstyle="info-inverse",
    )
    frame._pick_banner_default_text = PICK_MODE_BANNER_TEXT
    frame._pick_label.pack(side="left", padx=10, pady=5)

    frame._pick_cancel_button = tb.Button(
        frame._pick_banner_frame,
        text=PICK_MODE_CANCEL_TEXT,
        bootstyle="danger-outline",
        command=frame._pick_controller.cancel_pick,
    )
    frame._pick_cancel_button.pack(side="right", padx=10, pady=5)

    frame.btn_select = tb.Button(
        frame._pick_banner_frame,
        text=PICK_MODE_SELECT_TEXT,
        command=frame._pick_controller.confirm_pick,
        state="disabled",
        bootstyle="success",
    )
    frame.btn_select.pack(side="right", padx=10, pady=5)


def bind_main_events(frame: MainScreenFrame) -> None:
    """Configura bindings de eventos principais."""
    # Atualizar estado dos botões na seleção
    frame.tree.bind("<<TreeviewSelect>>", lambda _event: frame._update_main_buttons_state(), add="+")  # type: ignore[misc]


def setup_app_references(frame: MainScreenFrame) -> None:
    """Conecta referências compartilhadas com a aplicação principal."""

    if frame.app is not None:
        frame.clients_count_var = getattr(frame.app, "clients_count_var", None)
        frame.status_var_dot = getattr(frame.app, "status_var_dot", None)
        frame.status_var_text = getattr(frame.app, "status_var_text", None)
        frame.status_dot = getattr(frame.app, "status_dot", None)
        frame.status_lbl = getattr(frame.app, "status_lbl", None)
        setattr(frame.app, "_main_frame_ref", frame)
