# -*- coding: utf-8 -*-

"""Main screen frame extracted from app_gui (clients list)."""

from __future__ import annotations

import logging

import tkinter as tk

import urllib.parse

import webbrowser

from tkinter import messagebox, ttk

from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

try:
    import ttkbootstrap as tb

except Exception:
    tb = ttk  # fallback

from infra.supabase_client import get_supabase_state

from src.ui.components import create_clients_treeview

from src.modules.clientes.components.helpers import (
    _build_status_menu,
    STATUS_CHOICES,
)
from src.modules.clientes.views.main_screen_helpers import (
    DEFAULT_ORDER_LABEL,
    ORDER_CHOICES,
    ORDER_LABEL_CNPJ,
    ORDER_LABEL_ID_ASC,
    ORDER_LABEL_ID_DESC,
    ORDER_LABEL_NOME,
    ORDER_LABEL_RAZAO,
    ORDER_LABEL_UPDATED_OLD,
    ORDER_LABEL_UPDATED_RECENT,
    build_filter_choices_with_all_option,
    calculate_button_states,
    calculate_new_clients_stats,
    can_batch_delete,
    can_batch_export,
    can_batch_restore,
    get_selection_count,
    has_selection,
    normalize_order_choices,
    normalize_order_label,
    resolve_filter_choice_from_options,
)

# MS-2: Import do controller headless
from src.modules.clientes.views.main_screen_controller import (
    MainScreenComputed,
    MainScreenState,
    compute_main_screen_state,
)

from src.modules.clientes.service import (
    fetch_cliente_by_id,
    update_cliente_status_and_observacoes,
)

from src.modules.clientes.viewmodel import ClienteRow, ClientesViewModel, ClientesViewModelError

from src.modules.clientes.controllers.connectivity import ClientesConnectivityController

from src.modules.clientes.views.footer import ClientesFooter

from src.modules.clientes.views.pick_mode import PickModeController

from src.modules.clientes.views.toolbar import ClientesToolbar

from src.utils.phone_utils import normalize_br_whatsapp

from src.utils.prefs import load_columns_visibility, save_columns_visibility

log = logging.getLogger("app_gui")

# Constantes para o modo seleção (pick mode)
PICK_MODE_BANNER_TEXT = "🔍 Modo seleção: dê duplo clique em um cliente ou pressione Enter"
PICK_MODE_CANCEL_TEXT = "✖ Cancelar"
PICK_MODE_SELECT_TEXT = "✓ Selecionar"

__all__ = [
    "MainScreenFrame",
    "DEFAULT_ORDER_LABEL",
    "ORDER_CHOICES",
    "PICK_MODE_BANNER_TEXT",
    "PICK_MODE_CANCEL_TEXT",
    "PICK_MODE_SELECT_TEXT",
]


class MainScreenFrame(tb.Frame):  # pyright: ignore[reportGeneralTypeIssues]
    """

    Frame da tela principal (lista de clientes + aÃ§Ãµes).

    Recebe callbacks do App para operaÃ§Ãµes de negÃ³cio.

    """

    def __init__(
        self,
        master: tk.Misc,
        *,
        on_new: Optional[Callable[[], None]] = None,
        on_edit: Optional[Callable[[], None]] = None,
        on_delete: Optional[Callable[[], None]] = None,
        on_upload: Optional[Callable[[], None]] = None,
        on_open_subpastas: Optional[Callable[[], None]] = None,
        on_open_lixeira: Optional[Callable[[], None]] = None,
        app: Optional[Any] = None,
        order_choices: Optional[Dict[str, Tuple[Optional[str], bool]]] = None,
        default_order_label: str = DEFAULT_ORDER_LABEL,
        on_upload_folder: Optional[Callable[[], None]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, **kwargs)

        self.app: Optional[Any] = app

        self.on_new: Optional[Callable[[], None]] = on_new

        self.on_edit: Optional[Callable[[], None]] = on_edit

        self.on_delete: Optional[Callable[[], None]] = on_delete

        self.on_upload: Optional[Callable[[], None]] = on_upload

        self.on_upload_folder: Optional[Callable[[], None]] = on_upload_folder

        self.on_open_subpastas: Optional[Callable[[], None]] = on_open_subpastas

        self.on_open_lixeira: Optional[Callable[[], None]] = on_open_lixeira

        self._order_choices: Dict[str, Tuple[Optional[str], bool]] = normalize_order_choices(
            order_choices or ORDER_CHOICES
        )

        self._default_order_label: str = normalize_order_label(default_order_label) or DEFAULT_ORDER_LABEL
        if self._default_order_label not in self._order_choices:
            self._default_order_label = DEFAULT_ORDER_LABEL

        self._buscar_after: Optional[str] = None

        self._vm: ClientesViewModel = ClientesViewModel(
            order_choices=self._order_choices,
            default_order_label=self._default_order_label,
            author_resolver=self._resolve_author_initial,
        )

        self._pick_controller: PickModeController = PickModeController(self)

        self._connectivity: ClientesConnectivityController = ClientesConnectivityController(self)

        # Modo de seleção (para integração com Senhas)

        self._pick_mode: bool = False

        self._on_pick: Optional[Callable[[dict], None]] = None  # callable(dict_cliente)

        self._return_to: Optional[Callable[[], None]] = None  # callable() que volta pra tela anterior

        self._saved_toolbar_state: Dict[tk.Misc, dict[str, Any] | None] = {}  # Armazena estado dos botões CRUD

        self._trash_button_state_before_pick: str | None = (
            None  # FIX-CLIENTES-007: Estado da Lixeira antes do pick mode
        )

        self._current_rows: List[ClienteRow] = []

        self.toolbar = ClientesToolbar(
            self,
            order_choices=list(self._order_choices.keys()),
            default_order=self._default_order_label,
            status_choices=STATUS_CHOICES,
            on_search_changed=lambda text: self._buscar(text),
            on_clear_search=self._limpar_busca,
            on_order_changed=self._on_order_changed,
            on_status_changed=lambda _value: self.apply_filters(),
            on_open_trash=lambda: self._invoke_safe(self.on_open_lixeira),
        )

        self.toolbar.pack(fill="x", padx=10, pady=10)

        self.var_busca: tk.StringVar = self.toolbar.var_busca

        self.var_ordem: tk.StringVar = self.toolbar.var_ordem

        normalized_order = normalize_order_label(self.var_ordem.get())
        if normalized_order != self.var_ordem.get():
            self.var_ordem.set(normalized_order)
        self._current_order_by = normalized_order

        self.var_status: tk.StringVar = self.toolbar.var_status

        self.status_filter: ttk.Combobox = self.toolbar.status_combobox

        self.entry_busca: ttk.Entry = self.toolbar.entry_busca

        self.status_menu: Optional[tk.Menu] = None

        self._status_menu_cliente: Optional[int] = None

        self._status_menu_row: Optional[str] = None

        self.btn_lixeira: ttk.Button = self.toolbar.lixeira_button

        # --- DivisÃ³ria entre filtros e a faixa de controles de colunas

        self._cols_separator = ttk.Separator(self, orient="horizontal")

        self._cols_separator.pack(side="top", fill="x", padx=10, pady=(6, 4))

        # --- Faixa alinhada Ã s colunas (fora do Treeview, mas sincronizada)

        HEADER_CTRL_H = 26  # altura da faixa dos controles

        self.columns_align_bar = tk.Frame(self, height=HEADER_CTRL_H)

        self.columns_align_bar.pack(side="top", fill="x", padx=10)

        # IDs/ordem exatos das colunas

        self._col_order: Tuple[str, ...] = (
            "ID",
            "Razao Social",
            "CNPJ",
            "Nome",
            "WhatsApp",
            "Observacoes",
            "Status",
            "Ultima Alteracao",
        )

        # Estado por usuÃ¡rio (mantemos persistÃªncia)

        def _user_key():
            return getattr(self, "current_user_email", None) or getattr(self, "status_user_email", None) or "default"

        self._user_key: str = _user_key()

        _saved = load_columns_visibility(self._user_key)

        self._col_content_visible: Dict[str, tk.BooleanVar] = {
            c: tk.BooleanVar(value=_saved.get(c, True)) for c in self._col_order
        }

        # FunÃ§Ãµes auxiliares (nested functions)

        def _persist_visibility():
            save_columns_visibility(
                self._user_key,
                {k: v.get() for k, v in self._col_content_visible.items()},
            )

        def _on_toggle(col: str):
            # Garante pelo menos uma visÃ­vel

            if not any(v.get() for v in self._col_content_visible.values()):
                self._col_content_visible[col].set(True)

            self._refresh_rows()

            _persist_visibility()

        # Container para Treeview e Scrollbar

        self.client_list_container = tk.Frame(self)

        self.client_list_container.pack(expand=True, fill="both", padx=10, pady=5)

        self.client_list: ttk.Treeview = create_clients_treeview(
            self.client_list_container,
            on_double_click=lambda _event: self._invoke_safe(self.on_edit),
            on_select=self._update_main_buttons_state,
            on_delete=self._on_tree_delete_key,
            on_click=self._on_click,
        )

        # Scrollbar vertical

        self.clients_scrollbar: ttk.Scrollbar = tb.Scrollbar(
            self.client_list_container,
            orient="vertical",
            command=self.client_list.yview,
        )

        self.client_list.configure(yscrollcommand=self.clients_scrollbar.set)

        # Layout com grid

        self.client_list.grid(row=0, column=0, sticky="nsew")

        self.clients_scrollbar.grid(row=0, column=1, sticky="ns")

        self.client_list_container.rowconfigure(0, weight=1)

        self.client_list_container.columnconfigure(0, weight=1)

        self.tree: ttk.Treeview = self.client_list

        # Removido bind <Button-3> para menu de status

        # self.client_list.bind("<Button-3>", self._on_status_menu, add="+")

        # Bind para menu de status apenas na coluna Status com clique esquerdo

        self.client_list.bind("<Button-1>", self._on_click, add="+")

        # Configura headings sem sobrescrever os textos vindos do componente

        self.client_list.configure(displaycolumns=self._col_order)

        for col in self._col_order:
            try:
                # mantÃ©m o texto atual (com acento) se jÃ¡ veio do componente

                cur = self.client_list.heading(col, option="text")

                if not cur:
                    # fallback para IDs internos sem acento

                    friendly = {
                        "Razao Social": "RazÃ£o Social",
                        "Observacoes": "ObservaÃ§Ãµes",
                        "Ultima Alteracao": "Ãšltima AlteraÃ§Ã£o",
                    }.get(col, col)

                    self.client_list.heading(col, text=friendly, anchor="center")

                else:
                    self.client_list.heading(col, text=cur, anchor="center")

            except Exception as e:
                log.debug("Erro ao configurar heading %s: %s", col, e)

        # Larguras originais (para nÃ£o mexer quando ocultar)

        self._col_widths: Dict[str, int] = {}

        for c in self._col_order:
            try:
                self._col_widths[c] = self.client_list.column(c, option="width")

            except Exception:
                self._col_widths[c] = 120

        # FunÃ§Ã£o auxiliar para texto dinÃ¢mico do rÃ³tulo

        def _label_for(col: str) -> str:
            return "Ocultar" if self._col_content_visible[col].get() else "Mostrar"

        # FunÃ§Ã£o para atualizar textos dos rÃ³tulos

        def _update_toggle_labels():
            for col, parts in self._col_ctrls.items():
                parts["label"].config(text=_label_for(col))

        # Atualiza _on_toggle para incluir atualizaÃ§Ã£o de labels

        _original_on_toggle = _on_toggle

        def _on_toggle_with_labels(col: str):
            _original_on_toggle(col)

            _update_toggle_labels()

        # Cria os controles alinhados (um grupo por coluna)

        self._col_ctrls: Dict[str, Dict[str, tk.Widget]] = {}  # col -> {"frame":..., "label":..., "check":...}

        for col in self._col_order:
            grp = tk.Frame(self.columns_align_bar, bd=0, highlightthickness=0)

            chk = tk.Checkbutton(
                grp,
                variable=self._col_content_visible[col],
                command=lambda c=col: _on_toggle_with_labels(c),
                bd=0,
                highlightthickness=0,
                padx=0,
                pady=0,  # <- sem padding
                cursor="hand2",
                anchor="w",
            )

            chk.pack(side="left")

            lbl = ttk.Label(grp, text=_label_for(col))

            lbl.pack(side="left", padx=(0, 0))  # <- sem padding, totalmente colado

            grp.place(x=0, y=2, width=120, height=HEADER_CTRL_H - 4)

            self._col_ctrls[col] = {"frame": grp, "label": lbl, "check": chk}

        # Inicializa textos dos rÃ³tulos

        _update_toggle_labels()

        # FunÃ§Ã£o de sincronizaÃ§Ã£o: alinha grupos com as colunas (usa bbox para precisÃ£o)

        def _sync_col_controls():
            try:
                self.columns_align_bar.update_idletasks()

                self.client_list.update_idletasks()

                # base X do Treeview em relaÃ§Ã£o Ã  barra (corrige deslocamento de janela)

                base_left = self.client_list.winfo_rootx() - self.columns_align_bar.winfo_rootx()

                # pegue o primeiro item visÃ­vel para medir as colunas com bbox

                items = self.client_list.get_children()

                first_item = items[0] if items else None

                # Se nÃ£o houver items, calcula posiÃ§Ã£o acumulada manualmente

                cumulative_x = 0

                for col in self._col_order:
                    # largura e posiÃ§Ã£o reais da coluna via bbox

                    bx = None  # inicializa explicitamente

                    if first_item:
                        bx = self.client_list.bbox(first_item, col)

                        if not bx:
                            # se bbox vier vazio, usa fallback acumulado

                            col_w = int(self.client_list.column(col, option="width"))  # pyright: ignore[reportArgumentType]

                            bx = (cumulative_x, 0, col_w, 0)

                            cumulative_x += col_w

                    else:
                        # fallback: calcula posiÃ§Ã£o acumulada das colunas

                        col_w = int(self.client_list.column(col, option="width"))  # pyright: ignore[reportArgumentType]

                        bx = (cumulative_x, 0, col_w, 0)

                        cumulative_x += col_w

                    if not bx:
                        # se ainda assim vier vazio, pula

                        continue

                    col_x_rel, _, col_w, _ = bx

                    col_left = base_left + col_x_rel

                    col_right = col_left + col_w

                    # largura necessÃ¡ria do bloquinho = label + check + margens

                    parts = self._col_ctrls[col]

                    req_w = parts["label"].winfo_reqwidth() + 12 + 4  # label + checkbox (~12px) + margem (4px)

                    # limite por coluna

                    min_w, max_w = 70, 160

                    gw = max(min_w, min(max_w, min(req_w, col_w - 8)))

                    # centraliza dentro da coluna

                    gx = col_left + (col_w - gw) // 2

                    # nÃ£o deixa vazar a borda

                    if gx < col_left + 2:
                        gx = col_left + 2

                    if gx + gw > col_right - 2:
                        gx = max(col_left + 2, col_right - gw - 2)

                    parts["frame"].place_configure(x=gx, y=2, width=gw, height=HEADER_CTRL_H - 4)

            except Exception as exc:  # noqa: BLE001
                log.debug("Falha ao posicionar controles de colunas: %s", exc)

            # mantÃ©m alinhado mesmo com resize/scroll

            self.after(120, _sync_col_controls)

        # Eventos que disparam a sync

        self.client_list.bind("<Configure>", lambda e: _sync_col_controls())

        # Se houver scrollbar horizontal dedicado, sincronize

        try:
            old_cmd = self.client_list.cget("xscrollcommand")

            def _xscroll_proxy(*args):
                if old_cmd:
                    try:
                        func = self.nametowidget(old_cmd.split()[0])

                        func.set(*args)

                    except Exception as inner_exc:  # noqa: BLE001
                        log.debug("Falha ao atualizar scrollbar horizontal: %s", inner_exc)

                _sync_col_controls()

            self.client_list.configure(xscrollcommand=_xscroll_proxy)

        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao configurar proxy de scrollbar horizontal: %s", exc)

        # primeira sincronizaÃ§Ã£o

        _sync_col_controls()

        self.footer = ClientesFooter(
            self,
            on_novo=lambda: self._invoke_safe(self.on_new),
            on_editar=lambda: self._invoke_safe(self.on_edit),
            on_subpastas=lambda: self._invoke_safe(self.on_open_subpastas),
            on_enviar_supabase=lambda: self._invoke_safe(self.on_upload),
            on_enviar_pasta=lambda: self._invoke_safe(self.on_upload_folder),
            on_excluir=self.on_delete_selected_clients,
            on_batch_delete=self._on_batch_delete_clicked,
            on_batch_restore=self._on_batch_restore_clicked,
            on_batch_export=self._on_batch_export_clicked,
        )

        self.footer.pack(fill="x", padx=10, pady=10)

        self.btn_novo: ttk.Button = self.footer.btn_novo

        self.btn_editar: ttk.Button = self.footer.btn_editar

        self.btn_subpastas: ttk.Button = self.footer.btn_subpastas

        self.btn_enviar: ttk.Menubutton = self.footer.btn_enviar

        self.btn_excluir: Optional[ttk.Button] = self.footer.btn_excluir

        self.menu_enviar: tk.Menu = self.footer.enviar_menu

        # Botões batch (Fase 06)
        self.btn_batch_delete: ttk.Button = self.footer.btn_batch_delete
        self.btn_batch_restore: ttk.Button = self.footer.btn_batch_restore
        self.btn_batch_export: ttk.Button = self.footer.btn_batch_export

        self._uploading_busy: bool = False

        self._send_button_prev_text: Optional[str] = None

        self._last_cloud_state: Optional[str] = None

        self.btn_enviar.state(["disabled"])

        try:
            last_index = self.menu_enviar.index("end")

            if last_index is not None:
                for idx in range(last_index + 1):
                    self.menu_enviar.entryconfigure(idx, state="disabled")

        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao desabilitar menu de envio inicial: %s", exc)

        def _refresh_send_state() -> None:
            has_sel = bool(self.tree.selection())

            if has_sel:
                self.btn_enviar.state(["!disabled"])

                self.menu_enviar.entryconfig(0, state="normal")

                self.menu_enviar.entryconfig(1, state="normal")

            else:
                self.btn_enviar.state(["disabled"])

                self.menu_enviar.entryconfig(0, state="disabled")

                self.menu_enviar.entryconfig(1, state="disabled")

            self._update_main_buttons_state()

        _refresh_send_state()

        self.tree.bind("<<TreeviewSelect>>", lambda _event: _refresh_send_state(), add="+")

        # UI do modo de seleção (oculto inicialmente)

        self._pick_banner_frame: ttk.Frame = tb.Frame(self, bootstyle="info")

        self._pick_label: ttk.Label = tb.Label(
            self._pick_banner_frame,
            text=PICK_MODE_BANNER_TEXT,
            font=("", 10, "bold"),  # pyright: ignore[reportArgumentType]
            bootstyle="info-inverse",
        )

        self._pick_label.pack(side="left", padx=10, pady=5)

        self._pick_cancel_button = tb.Button(
            self._pick_banner_frame,
            text=PICK_MODE_CANCEL_TEXT,
            bootstyle="danger-outline",
            command=self._pick_controller.cancel_pick,
        )

        self._pick_cancel_button.pack(side="right", padx=10, pady=5)

        self.btn_select: ttk.Button = tb.Button(
            self._pick_banner_frame,
            text=PICK_MODE_SELECT_TEXT,
            command=self._pick_controller.confirm_pick,
            state="disabled",
            bootstyle="success",
        )

        self.btn_select.pack(side="right", padx=10, pady=5)

        # StatusBar removido - agora é global no main_window

        # Usar referências da App

        if self.app is not None:
            self.clients_count_var = getattr(self.app, "clients_count_var", None)

            self.status_var_dot = getattr(self.app, "status_var_dot", None)

            self.status_var_text = getattr(self.app, "status_var_text", None)

            self.status_dot = getattr(self.app, "status_dot", None)

            self.status_lbl = getattr(self.app, "status_lbl", None)

            setattr(self.app, "_main_frame_ref", self)

        self._update_main_buttons_state()

        # Inicia verificação periódica de conectividade

        self._connectivity.start()

    def destroy(self) -> None:
        """
        Cleanup ao destruir o frame.

        FIX-CLIENTES-007: Garante que o botão Conversor PDF seja reabilitado
        caso o usuário saia do modo seleção navegando para outro módulo
        (em vez de clicar em Cancelar).
        """
        # Se estava em modo pick, garante que o Conversor PDF seja reabilitado
        if getattr(self, "_pick_mode", False) and self.app and hasattr(self.app, "topbar"):
            try:
                self.app.topbar.set_pick_mode_active(False)
            except Exception as exc:  # noqa: BLE001
                log.debug("Erro ao reabilitar Conversor PDF no destroy: %s", exc)

        # Chama o destroy original do ttk.Frame
        super().destroy()

    def set_uploading(self, busy: bool) -> None:
        """Disable upload actions while an upload job is running."""

        busy = bool(busy)

        if busy == self._uploading_busy:
            return

        self._uploading_busy = busy

        try:
            if hasattr(self, "footer"):
                self.footer.set_uploading(busy)
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao atualizar footer em estado de upload: %s", exc)

        self._update_main_buttons_state()

    def _enter_pick_mode_ui(self) -> None:
        """Configura a tela para o modo seleção de clientes (FIX-CLIENTES-005 + FIX-CLIENTES-007)."""
        log.debug("FIX-007: entrando em pick mode na tela de clientes")

        # FIX-CLIENTES-007: Desabilitar botões do footer usando método específico
        if hasattr(self, "footer") and hasattr(self.footer, "enter_pick_mode"):
            try:
                self.footer.enter_pick_mode()
            except Exception as exc:  # noqa: BLE001
                log.debug("Falha ao entrar em pick mode no footer: %s", exc)

        # FIX-CLIENTES-007: Lixeira fica VISÍVEL mas DESABILITADA (cinza)
        trash_button = getattr(self, "btn_lixeira", None)
        if trash_button is not None:
            try:
                # Guarda o estado atual (normalmente "normal")
                current_state = str(trash_button["state"])
                self._trash_button_state_before_pick = current_state
                # Desabilita visualmente (fica cinza)
                trash_button.configure(state="disabled")
            except Exception as exc:  # noqa: BLE001
                log.debug("Falha ao desabilitar botão lixeira: %s", exc)

        # Desabilitar menus superiores (Conversor PDF)
        if self.app is not None and hasattr(self.app, "topbar"):
            try:
                self.app.topbar.set_pick_mode_active(True)
            except Exception as exc:  # noqa: BLE001
                log.debug("Falha ao desabilitar menus no pick mode: %s", exc)

    def _leave_pick_mode_ui(self) -> None:
        """Restaura a tela para o modo normal (não seleção) (FIX-CLIENTES-005 + FIX-CLIENTES-007)."""
        # Restaurar estados dos botões via atualização central
        try:
            self._update_main_buttons_state()
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao restaurar estados dos botões: %s", exc)

        # FIX-CLIENTES-007: Restaurar estado da Lixeira DEPOIS do _update_main_buttons_state
        # para garantir que nosso estado salvo prevaleça sobre a lógica de conectividade
        trash_button = getattr(self, "btn_lixeira", None)
        if trash_button is not None:
            try:
                previous_state = self._trash_button_state_before_pick or "normal"
                trash_button.configure(state=previous_state)
            except Exception as exc:  # noqa: BLE001
                log.debug("Falha ao restaurar botão lixeira: %s", exc)

        # FIX-CLIENTES-007: Restaurar botões do rodapé usando método específico
        if hasattr(self, "footer") and hasattr(self.footer, "leave_pick_mode"):
            try:
                self.footer.leave_pick_mode()
            except Exception as exc:  # noqa: BLE001
                log.debug("Falha ao sair de pick mode no footer: %s", exc)

        # Reabilitar menus superiores (Conversor PDF)
        if self.app is not None and hasattr(self.app, "topbar"):
            try:
                self.app.topbar.set_pick_mode_active(False)
            except Exception as exc:  # noqa: BLE001
                log.debug("Falha ao reabilitar menus após pick mode: %s", exc)

    def _start_connectivity_monitor(self) -> None:
        self._connectivity.start()

    def carregar(self) -> None:
        """Preenche a tabela de clientes.

        MS-2: Agora delega filtros/ordenação ao controller headless.
        """
        # TODO MS-2: Integrado com main_screen_controller.compute_main_screen_state

        order_label_raw = self.var_ordem.get()
        order_label = normalize_order_label(order_label_raw)
        if order_label != order_label_raw:
            self.var_ordem.set(order_label)

        search_term = self.var_busca.get().strip()

        log.info("Atualizando lista (busca='%s', ordem='%s')", search_term, order_label)

        # MS-3: ViewModel apenas carrega dados brutos do backend.
        # Controller (compute_main_screen_state) aplica filtros/ordenação.
        try:
            self._vm.refresh_from_service()

        except ClientesViewModelError as exc:
            log.warning("Falha ao carregar lista: %s", exc)

            messagebox.showerror("Erro", f"Falha ao carregar lista: {exc}", parent=self)

            return

        # Atualizar opções de filtro de status (dinâmico baseado nos dados)
        self._populate_status_filter_options()

        # MS-2: Usar controller para aplicar filtros/ordenação
        self._refresh_with_controller()

    def _sort_by(self, column: str) -> None:
        current = normalize_order_label(self.var_ordem.get())

        if column == "updated_at":
            new_value = ORDER_LABEL_UPDATED_OLD if current == ORDER_LABEL_UPDATED_RECENT else ORDER_LABEL_UPDATED_RECENT
            self.var_ordem.set(new_value)
        elif column in ("razao_social", "cnpj", "nome"):
            mapping = {
                "razao_social": ORDER_LABEL_RAZAO,
                "cnpj": ORDER_LABEL_CNPJ,
                "nome": ORDER_LABEL_NOME,
            }
            self.var_ordem.set(mapping[column])
        elif column == "id":
            new_value = ORDER_LABEL_ID_DESC if current == ORDER_LABEL_ID_ASC else ORDER_LABEL_ID_ASC
            self.var_ordem.set(new_value)
        else:
            return

        self.carregar()

    def _get_selected_values(self) -> Optional[Sequence[Any]]:
        try:
            selection = self.client_list.selection()

        except Exception:
            return None

        if not selection:
            return None

        item_id = selection[0]

        try:
            return self.client_list.item(item_id, "values")

        except Exception:
            return None

    def _buscar(self, _event: Any | None = None) -> None:
        try:
            if self._buscar_after:
                self.after_cancel(self._buscar_after)
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao cancelar debounce de busca: %s", exc)

        self._buscar_after = self.after(200, self.carregar)

    def _limpar_busca(self) -> None:
        self.var_busca.set("")

        self.var_status.set("Todos")

        self.carregar()

    def apply_filters(self, *_: Any) -> None:
        """Aplica filtros de status e texto de busca.

        MS-2: Agora usa o controller headless para computar a lista filtrada.
        """
        # TODO MS-2: Integrado com main_screen_controller.compute_main_screen_state
        self._refresh_with_controller()

    def _populate_status_filter_options(self) -> None:
        statuses = self._vm.get_status_choices()

        choices = build_filter_choices_with_all_option(statuses)

        try:
            self.status_filter.configure(values=choices)

        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao atualizar filtro de status: %s", exc)

        current = (self.var_status.get() or "").strip()

        resolved = resolve_filter_choice_from_options(current, choices)

        if resolved != current:
            self.var_status.set(resolved)

    # MS-3: Método _refresh_list_from_vm() removido - não é mais usado.
    # MainScreen usa exclusivamente _refresh_with_controller() para atualizar lista.

    def _row_values_masked(self, row: ClienteRow) -> tuple[Any, ...]:
        mapping = {
            "ID": row.id,
            "Razao Social": row.razao_social,
            "CNPJ": row.cnpj,
            "Nome": row.nome,
            "WhatsApp": row.whatsapp,
            "Observacoes": row.observacoes,
            "Status": row.status,
            "Ultima Alteracao": row.ultima_alteracao,
        }

        values: list[str] = []

        for col in self._col_order:
            value = mapping.get(col, "")

            if not self._col_content_visible[col].get():
                value = ""

            values.append(value)

        return tuple(values)

    def _refresh_rows(self) -> None:
        rows = self._current_rows

        items = self.client_list.get_children()

        if len(items) != len(rows):
            self.client_list.delete(*items)

            for row in rows:
                self.client_list.insert("", "end", values=self._row_values_masked(row))

            return

        for item_id, row in zip(items, rows):
            self.client_list.item(item_id, values=self._row_values_masked(row))

    def _render_clientes(self, rows: Sequence[ClienteRow]) -> None:
        try:
            self.client_list.delete(*self.client_list.get_children())

        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao limpar treeview de clientes: %s", exc)

        for row in rows:
            tags = ("has_obs",) if row.observacoes.strip() else ()

            self.client_list.insert("", "end", values=self._row_values_masked(row), tags=tags)

        raw_clientes = [
            row.raw.get("cliente") for row in rows if isinstance(row.raw, dict) and row.raw.get("cliente") is not None
        ]

        count = len(rows) if isinstance(rows, (list, tuple)) else len(self.client_list.get_children())

        self._set_count_text(count, raw_clientes)

        self._update_main_buttons_state()

        try:
            self.after(50, lambda: None)

        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao agendar refresh ass�ncrono: %s", exc)

    def _apply_connectivity_state(self, state: str, description: str, text: str, _style: str, _tooltip: str) -> None:
        """

        Aplica efeitos de conectividade (enable/disable, textos, status bar).

        """

        try:
            if self.app is not None:
                setattr(self.app, "_net_is_online", state == "online")

                setattr(self.app, "_net_state", state)

                setattr(self.app, "_net_description", description)

        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao atualizar atributos globais de conectividade: %s", exc)

        # Atualiza estado dos botões e textos

        try:
            self._update_main_buttons_state()

            if hasattr(self, "btn_enviar") and not self._uploading_busy:
                if state == "online":
                    self.btn_enviar.configure(text="Enviar Para SupaBase")

                elif state == "unstable":
                    self.btn_enviar.configure(text="Envio suspenso - Conexao instavel")

                else:
                    self.btn_enviar.configure(text="Envio suspenso - Offline")

        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao atualizar UI de conectividade: %s", exc)

        # Atualiza indicador visual na UI (status bar global)

        status_var = getattr(self.app, "status_var_text", None) if self.app is not None else None

        if status_var is not None:
            try:
                current_text = status_var.get()

                if "Nuvem:" in current_text:
                    parts = current_text.split("|")

                    parts[0] = f"Nuvem: {text}"

                    status_var.set(" | ".join(parts))

                else:
                    status_var.set(f"Nuvem: {text}")

            except Exception as exc:  # noqa: BLE001
                log.debug("Falha ao atualizar texto de status global: %s", exc)

        if not hasattr(self, "_last_cloud_state") or self._last_cloud_state != state:
            log.info(
                "Status da nuvem mudou: %s – %s (%s)",
                getattr(self, "_last_cloud_state", "unknown"),
                state.upper(),
                description,
            )

            self._last_cloud_state = state

    def _ensure_status_menu(self) -> tk.Menu:
        menu = self.status_menu

        if menu is None:
            menu = tk.Menu(self, tearoff=0)

            self.status_menu = menu

        menu.configure(postcommand=lambda: _build_status_menu(menu, self._on_status_pick))

        return menu

    def _show_status_menu(self, row_id: str, cliente_id: int, event: Any) -> None:
        menu = self._ensure_status_menu()

        self.client_list.selection_set(row_id)

        self.client_list.focus(row_id)

        self._status_menu_row = row_id

        self._status_menu_cliente = cliente_id

        try:
            menu.tk_popup(event.x_root, event.y_root)

        finally:
            menu.grab_release()

            if self._status_menu_row == row_id:
                self._status_menu_row = None

            if self._status_menu_cliente == cliente_id:
                self._status_menu_cliente = None

    def _on_status_menu(self, event: Any) -> None:
        tv = getattr(self, "tree", self.client_list)

        row_id = tv.identify_row(event.y)

        if not row_id:
            return

        tv.selection_set(row_id)

        tv.focus(row_id)

        try:
            values = tv.item(row_id, "values")

            idx = self._col_order.index("ID") if "ID" in self._col_order else 0

            cliente_id = int(values[idx])

        except Exception:
            return

        self._show_status_menu(row_id, cliente_id, event)

    def _on_status_pick(self, label: str) -> None:
        self._set_status(label)

    def _set_status(self, label: str) -> None:
        target_id = self._status_menu_cliente

        if target_id is None:
            try:
                selection = self.client_list.selection()

                if not selection:
                    self._status_menu_cliente = None

                    self._status_menu_row = None

                    return

                values = self.client_list.item(selection[0], "values")

                idx = self._col_order.index("ID") if "ID" in self._col_order else 0

                target_id = int(values[idx])

            except Exception:
                self._status_menu_cliente = None

                self._status_menu_row = None

                return

        try:
            self._apply_status_for(int(target_id), label)

        finally:
            self._status_menu_cliente = None

            self._status_menu_row = None

    def _on_click(self, event: Any) -> None:
        """Abre WhatsApp na col #5 e menu de Status na col #7."""

        item = self.client_list.identify_row(event.y)

        col = self.client_list.identify_column(event.x)

        if not item:
            return

        # Menu de Status ao clicar na coluna #7

        if col == "#7":
            try:
                vals = self.client_list.item(item, "values")

                id_index = self._col_order.index("ID") if "ID" in self._col_order else 0

                cliente_id = int(vals[id_index])

            except Exception:
                return

            self._show_status_menu(item, cliente_id, event)

            return

        # WhatsApp permanece na coluna #5

        if col != "#5":
            return

        try:
            cell = self.client_list.item(item, "values")[4] or ""  # Ã­ndice 4 = 5Âª coluna (WhatsApp)

        except Exception:
            cell = ""

        # Usa normalize_br_whatsapp para obter formato e164

        wa = normalize_br_whatsapp(str(cell))

        if not wa["e164"]:
            return

        msg = "OlÃ¡, tudo bem?"

        webbrowser.open_new_tab(f"https://wa.me/{wa['e164']}?text={urllib.parse.quote(msg)}")

    def _resolve_author_initial(self, email: str) -> str:
        """Resolve inicial do autor reutilizando os helpers do hub."""

        raw = email or ""

        try:
            from src.ui.hub.authors import _author_display_name as _author_name

            display = _author_name(self, raw)

            return display or raw

        except Exception:
            return raw

    # ========================================================================
    # MS-2: Helpers para integração com main_screen_controller
    # ========================================================================

    def _get_clients_for_controller(self) -> Sequence[ClienteRow]:
        """Obtém lista de clientes para passar ao controller.

        Retorna a lista completa de clientes (antes de filtros/ordenação),
        pois o controller é responsável por aplicar filtros e ordenação.

        Nota MS-2: O ViewModel atual já filtra internamente, então pegamos
        _clientes_raw e convertemos manualmente para ClienteRow.
        """
        # Precisamos reconstruir as rows a partir dos dados brutos
        # sem aplicar filtros, para que o controller faça isso
        raw_clientes = self._vm._clientes_raw  # pyright: ignore[reportPrivateUsage]

        # Converter cada cliente raw para ClienteRow usando o método do VM
        rows: list[ClienteRow] = []
        for cliente in raw_clientes:
            row = self._vm._build_row_from_cliente(cliente)  # pyright: ignore[reportPrivateUsage]
            rows.append(row)

        return rows

    def _build_main_screen_state(self) -> MainScreenState:
        """Constrói o estado atual da tela para o controller.

        Coleta todos os dados de estado da UI e monta o MainScreenState.
        """
        # Clientes (lista completa, antes de filtros)
        clients = self._get_clients_for_controller()

        # Ordenação atual
        order_label = normalize_order_label(self.var_ordem.get())

        # Filtro de status atual
        filter_label = (self.var_status.get() or "").strip()

        # Texto de busca atual
        search_text = self.var_busca.get().strip()

        # IDs selecionados
        selected_ids = list(self._get_selected_ids())

        # Status online/offline
        try:
            state, _ = get_supabase_state()  # pyright: ignore[reportAssignmentType]
            is_online = state == "online"
        except Exception:
            is_online = False

        # Modo lixeira (MainScreenFrame é sempre lista principal)
        is_trash_screen = False

        return MainScreenState(
            clients=clients,
            order_label=order_label,
            filter_label=filter_label,
            search_text=search_text,
            selected_ids=selected_ids,
            is_online=is_online,
            is_trash_screen=is_trash_screen,
        )

    def _update_ui_from_computed(self, computed: MainScreenComputed) -> None:
        """Atualiza a UI usando os dados computados pelo controller.

        Esta é a função central que aplica os resultados do controller
        na interface Tkinter.
        """
        # 1. Atualizar lista visível na Treeview
        self._current_rows = list(computed.visible_clients)
        self._render_clientes(self._current_rows)

        # 2. Atualizar botões de batch operations
        self._update_batch_buttons_from_computed(computed)

        # 3. Atualizar botões principais (já existe, mantém compatibilidade)
        self._update_main_buttons_state()

    def _update_batch_buttons_from_computed(self, computed: MainScreenComputed) -> None:
        """Atualiza botões de batch operations usando dados do controller.

        Substitui a lógica antiga que calculava estados localmente.
        """
        try:
            if getattr(self, "btn_batch_delete", None) is not None:
                self.btn_batch_delete.configure(state="normal" if computed.can_batch_delete else "disabled")

            if getattr(self, "btn_batch_restore", None) is not None:
                self.btn_batch_restore.configure(state="normal" if computed.can_batch_restore else "disabled")

            if getattr(self, "btn_batch_export", None) is not None:
                self.btn_batch_export.configure(state="normal" if computed.can_batch_export else "disabled")
        except Exception as e:
            log.debug("Erro ao atualizar botões de batch: %s", e)

    def _refresh_with_controller(self) -> None:
        """Função central que usa o controller para recomputar o estado.

        TODO MS-2: Este é o ponto de integração principal com o controller.
        Substitui a lógica antiga de filtros/ordenação dispersa.
        """
        # 1. Construir estado atual da tela
        state = self._build_main_screen_state()

        # 2. Computar estado usando controller headless
        computed = compute_main_screen_state(state)

        # 3. Atualizar UI com resultado
        self._update_ui_from_computed(computed)

    def _update_batch_buttons_on_selection_change(self) -> None:
        """Atualiza apenas botões de batch quando seleção muda (sem recarregar lista).

        MS-2: Usa controller para calcular estados, mas sem reprocessar toda a lista.
        """
        # Construir estado atual (com lista já carregada em _current_rows)
        state = MainScreenState(
            clients=self._current_rows,  # Usa lista já em memória
            order_label=normalize_order_label(self.var_ordem.get()),
            filter_label=(self.var_status.get() or "").strip(),
            search_text=self.var_busca.get().strip(),
            selected_ids=list(self._get_selected_ids()),
            is_online=get_supabase_state()[0] == "online",  # pyright: ignore[reportGeneralTypeIssues]
            is_trash_screen=False,
        )

        # Computar apenas para obter flags de batch
        computed = compute_main_screen_state(state)

        # Atualizar apenas botões de batch
        self._update_batch_buttons_from_computed(computed)

    # ========================================================================
    # Fim dos helpers MS-2
    # ========================================================================

    def _apply_status_for(self, cliente_id: int, chosen: str) -> None:
        """Atualiza o [STATUS] no campo Observações e recarrega a grade."""

        try:
            cli = fetch_cliente_by_id(cliente_id)

            if not cli:
                return

            old_obs = (getattr(cli, "obs", None) or getattr(cli, "observacoes", None) or "").strip()

            _, body = self._vm.extract_status_and_observacoes(old_obs)

            update_cliente_status_and_observacoes(cliente=cliente_id, novo_status=chosen)

            self.carregar()

        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao atualizar status: {e}", parent=self)

    # === FASE 07: Callbacks de Batch Operations (Implementação Real) ===

    def _on_batch_delete_clicked(self) -> None:
        """Callback do botão 'Excluir em Lote'.

        FASE 07: Implementação real da exclusão em massa.
        Exclui definitivamente os clientes selecionados após confirmação.
        """
        # Obter IDs selecionados
        selected_ids = self._get_selected_ids()
        if not selected_ids:
            return

        # Validar pré-condições com helper
        supabase_state = get_supabase_state()
        is_online = supabase_state[0] == "online"

        if not can_batch_delete(selected_ids, is_trash_screen=False, is_online=is_online):
            messagebox.showwarning(
                "Operação não permitida",
                "A exclusão em lote não está disponível no momento.\n"
                "Verifique sua conexão ou se há clientes selecionados.",
                parent=self,
            )
            return

        # Diálogo de confirmação
        count = get_selection_count(selected_ids)
        message = (
            f"Você deseja excluir definitivamente {count} cliente(s) selecionado(s)?\n\n"
            f"⚠️ Esta operação NÃO pode ser desfeita!\n"
            f"Os dados e arquivos associados serão removidos permanentemente."
        )
        confirmed = messagebox.askyesno(
            "Excluir em Lote",
            message,
            parent=self,
        )
        if not confirmed:
            return

        # Executar exclusão
        def _delete_batch() -> None:
            try:
                ok, errors = self._vm.delete_clientes_batch(selected_ids)

                # Recarregar lista
                self.carregar()

                # Feedback ao usuário
                if errors:
                    error_msg = "\n".join([f"ID {cid}: {msg}" for cid, msg in errors[:5]])
                    if len(errors) > 5:
                        error_msg += f"\n... e mais {len(errors) - 5} erro(s)"

                    messagebox.showwarning(
                        "Exclusão Parcial",
                        f"Excluídos: {ok}/{count}\n\nErros:\n{error_msg}",
                        parent=self,
                    )
                else:
                    messagebox.showinfo(
                        "Sucesso",
                        f"{ok} cliente(s) excluído(s) com sucesso!",
                        parent=self,
                    )
            except Exception as e:
                log.exception("Erro ao excluir clientes em lote")
                messagebox.showerror(
                    "Erro",
                    f"Falha ao excluir clientes em lote: {e}",
                    parent=self,
                )

        # Usar padrão de invocação segura
        self._invoke_safe(_delete_batch)

    def _on_batch_restore_clicked(self) -> None:
        """Callback do botão 'Restaurar em Lote'.

        FASE 07: Implementação real da restauração em massa.
        Restaura os clientes selecionados da lixeira.
        """
        # Obter IDs selecionados
        selected_ids = self._get_selected_ids()
        if not selected_ids:
            return

        # Validar pré-condições com helper
        supabase_state = get_supabase_state()
        is_online = supabase_state[0] == "online"

        # Restore em lote só faz sentido na lixeira (is_trash_screen=True)
        # MainScreenFrame é lista principal, então is_trash_screen=False
        if not can_batch_restore(selected_ids, is_trash_screen=False, is_online=is_online):
            messagebox.showwarning(
                "Operação não permitida",
                "A restauração em lote não está disponível nesta tela.\n"
                "Use a tela de Lixeira para restaurar clientes.",
                parent=self,
            )
            return

        # Diálogo de confirmação
        count = get_selection_count(selected_ids)
        message = f"Você deseja restaurar {count} cliente(s) selecionado(s) da lixeira?"
        confirmed = messagebox.askyesno(
            "Restaurar em Lote",
            message,
            parent=self,
        )
        if not confirmed:
            return

        # Executar restauração
        def _restore_batch() -> None:
            try:
                self._vm.restore_clientes_batch(selected_ids)

                # Recarregar lista
                self.carregar()

                # Feedback ao usuário
                messagebox.showinfo(
                    "Sucesso",
                    f"{count} cliente(s) restaurado(s) com sucesso!",
                    parent=self,
                )
            except Exception as e:
                log.exception("Erro ao restaurar clientes em lote")
                messagebox.showerror(
                    "Erro",
                    f"Falha ao restaurar clientes em lote: {e}",
                    parent=self,
                )

        # Usar padrão de invocação segura
        self._invoke_safe(_restore_batch)

    def _on_batch_export_clicked(self) -> None:
        """Callback do botão 'Exportar em Lote'.

        FASE 07: Implementação real da exportação em massa.
        Exporta dados dos clientes selecionados.
        """
        # Obter IDs selecionados
        selected_ids = self._get_selected_ids()
        if not has_selection(selected_ids):
            return

        # Validar pré-condições com helper (export não depende de is_online)
        if not can_batch_export(selected_ids):
            messagebox.showwarning(
                "Operação não permitida",
                "A exportação em lote não está disponível no momento.\n" "Verifique se há clientes selecionados.",
                parent=self,
            )
            return

        # Executar exportação (sem confirmação - operação não destrutiva)
        def _export_batch() -> None:
            try:
                self._vm.export_clientes_batch(selected_ids)

                # Feedback ao usuário
                count = get_selection_count(selected_ids)
                messagebox.showinfo(
                    "Exportação",
                    f"Exportação de {count} cliente(s) iniciada.\n\n"
                    f"Nota: Funcionalidade em desenvolvimento.\n"
                    f"Os dados foram logados para processamento futuro.",
                    parent=self,
                )
            except Exception as e:
                log.exception("Erro ao exportar clientes em lote")
                messagebox.showerror(
                    "Erro",
                    f"Falha ao exportar clientes em lote: {e}",
                    parent=self,
                )

        # Usar padrão de invocação segura
        self._invoke_safe(_export_batch)

    def _get_selected_ids(self) -> set[str]:
        """Retorna o conjunto de IDs de clientes atualmente selecionados na árvore.

        Returns:
            Set de IDs (strings) dos itens selecionados. Set vazio se nenhuma seleção.
        """
        try:
            # Usa self.client_list que é o mesmo que self.tree
            selection_tuple = self.client_list.selection()
            return set(selection_tuple) if selection_tuple else set()
        except Exception:
            return set()

    def _update_batch_buttons_state(self) -> None:
        """Atualiza o estado (normal/disabled) dos botões de operações em massa.

        Usa helpers puros de batch operations (Fase 04) para determinar estados.
        """
        # Obtém seleção atual via método centralizado
        selected_ids = self._get_selected_ids()

        # Obtém estado online da mesma forma que _update_main_buttons_state
        try:
            state, _ = get_supabase_state()  # pyright: ignore[reportAssignmentType]
            is_online = state == "online"
        except Exception:
            is_online = False

        # MainScreenFrame é sempre lista principal (não lixeira)
        # Tela de lixeira é separada (trash screen)
        is_trash_screen = False

        # Calcula estados usando helpers da Fase 04
        can_delete = can_batch_delete(
            selected_ids,
            is_trash_screen=is_trash_screen,
            is_online=is_online,
            max_items=None,  # Sem limite por enquanto
        )

        can_restore = can_batch_restore(
            selected_ids,
            is_trash_screen=is_trash_screen,
            is_online=is_online,
        )

        can_export = can_batch_export(
            selected_ids,
            max_items=None,  # Sem limite por enquanto
        )

        # Atualiza botões de batch (se existirem)
        # Nota: Os botões de batch podem não estar presentes na UI principal
        try:
            if getattr(self, "btn_batch_delete", None) is not None:
                self.btn_batch_delete.configure(state="normal" if can_delete else "disabled")

            if getattr(self, "btn_batch_restore", None) is not None:
                self.btn_batch_restore.configure(state="normal" if can_restore else "disabled")

            if getattr(self, "btn_batch_export", None) is not None:
                self.btn_batch_export.configure(state="normal" if can_export else "disabled")
        except Exception as e:
            log.debug("Erro ao atualizar botões de batch: %s", e)

    def _update_main_buttons_state(self, *_: Any) -> None:
        """

        Atualiza o estado dos botÃµes principais baseado em:

        - SeleÃ§Ã£o de cliente

        - Status de conectividade com Supabase (Online/InstÃ¡vel/Offline)

        Comportamento:

        - ONLINE: Todos os botÃµes funcionam normalmente

        - INSTÃVEL ou OFFLINE: BotÃµes de envio ficam desabilitados

        - OperaÃ§Ãµes locais (visualizar, buscar) continuam disponÃ­veis

        """

        try:
            has_sel = bool(self.client_list.selection())

        except Exception:
            has_sel = False

        # ObtÃ©m estado detalhado da nuvem

        state, _ = get_supabase_state()  # pyright: ignore[reportAssignmentType]

        online = state == "online"  # Somente "online" permite envio

        # Usa helper para calcular estados
        states = calculate_button_states(
            has_selection=has_sel,
            is_online=online,
            is_uploading=self._uploading_busy,
            is_pick_mode=self._pick_mode,
        )

        try:
            # BotÃµes que dependem de conexÃ£o E seleÃ§Ã£o

            self.btn_editar.configure(state=("normal" if states["editar"] else "disabled"))

            self.btn_subpastas.configure(state=("normal" if states["subpastas"] else "disabled"))

            if states["enviar"]:
                self.btn_enviar.state(["!disabled"])

            else:
                self.btn_enviar.state(["disabled"])

            if hasattr(self, "menu_enviar") and self.menu_enviar is not None:
                try:
                    last_index = self.menu_enviar.index("end")

                    if last_index is not None:
                        entry_state = "normal" if states["enviar"] else "disabled"

                        for idx in range(last_index + 1):
                            self.menu_enviar.entryconfigure(idx, state=entry_state)

                except Exception as exc:  # noqa: BLE001
                    log.debug("Falha ao atualizar menu de envio: %s", exc)

            # BotÃµes que dependem apenas de conexÃ£o

            self.btn_novo.configure(state=("normal" if states["novo"] else "disabled"))

            # FIX-CLIENTES-007: Não mexer no estado da Lixeira quando estamos saindo do pick mode
            # O _leave_pick_mode_ui() restaurará o estado salvo
            if not getattr(self, "_pick_mode", False):
                self.btn_lixeira.configure(state=("normal" if states["lixeira"] else "disabled"))

            # BotÃ£o de seleÃ§Ã£o (modo pick) - nÃ£o depende de conexÃ£o

            if self._pick_mode and hasattr(self, "btn_select"):
                self.btn_select.configure(state=("normal" if states["select"] else "disabled"))
            if getattr(self, "btn_excluir", None) is not None:
                self.btn_excluir.configure(state=("normal" if states["editar"] else "disabled"))

        except Exception as e:
            log.debug("Erro ao atualizar estado dos botÃµes: %s", e)

        # MS-2: Botões de batch agora atualizados via controller
        self._update_batch_buttons_on_selection_change()

    def _on_order_changed(self, _value: Any | None = None) -> None:
        """Dispara recarga apenas quando a ordenação efetivamente muda."""
        new_value = normalize_order_label(self.var_ordem.get())
        if new_value == getattr(self, "_current_order_by", None):
            return
        self._current_order_by = new_value
        self.var_ordem.set(new_value)
        self.carregar()

    def on_delete_selected_clients(self) -> None:
        """Aciona a exclus?o (envio para lixeira) dos clientes selecionados."""
        if self.on_delete:
            self._invoke_safe(self.on_delete)

    def _on_tree_delete_key(self, _event: Any = None) -> None:
        """Handler da tecla Delete na lista principal."""
        self.on_delete_selected_clients()

    def _resolve_order_preferences(self) -> Tuple[Optional[str], bool]:
        label = normalize_order_label(self.var_ordem.get())
        return self._order_choices.get(label, (None, False))

    def _set_count_text(self, count: int, clientes: Sequence[Any] | None = None) -> None:
        try:
            from datetime import date

            total_clients = count

            new_today = 0

            new_month = 0

            if clientes:
                today = date.today()
                # Usa helper para calcular estatísticas
                new_today, new_month = calculate_new_clients_stats(clientes, today)

            # Atualiza o StatusFooter global

            if self.app and self.app.status_footer:
                self.app.status_footer.set_clients_summary(total_clients, new_today, new_month)

        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao atualizar resumo de clientes: %s", exc)

    # =========================================================================

    # Modo de seleÃ§Ã£o para integraÃ§Ã£o com Senhas

    # =========================================================================

    # Modo de seleção para integração com Senhas

    # =========================================================================

    def start_pick(self, on_pick: Callable[[dict], None], return_to: Optional[Callable[[], None]] = None) -> None:
        """API pública usada pelo router para modo pick (Senhas)."""

        self._pick_controller.start_pick(on_pick=on_pick, return_to=return_to)

    def _on_pick_cancel(self, *_: object) -> None:
        self._pick_controller.cancel_pick()

    def _on_pick_confirm(self, *_: object) -> None:
        self._pick_controller.confirm_pick()

    @staticmethod
    def _invoke(callback: Optional[Callable[[], None]]) -> None:
        if callable(callback):
            callback()

    def _invoke_safe(self, callback: Optional[Callable[[], None]]) -> None:
        """Invoca callback apenas se NÃO estiver em modo seleção."""

        if getattr(self, "_pick_mode", False):
            return

        if callable(callback):
            callback()
