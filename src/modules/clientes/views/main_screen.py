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

ORDER_LABEL_RAZAO = "Razão Social (A→Z)"

ORDER_LABEL_CNPJ = "CNPJ (A→Z)"

ORDER_LABEL_NOME = "Nome (A→Z)"

ORDER_LABEL_ID_ASC = "ID (1→9)"

ORDER_LABEL_ID_DESC = "ID (9→1)"

ORDER_LABEL_UPDATED_RECENT = "Última Alteração (mais recente)"

ORDER_LABEL_UPDATED_OLD = "Última Alteração (mais antiga)"

ORDER_LABEL_ALIASES = {
    "Razao Social (A->Z)": ORDER_LABEL_RAZAO,
    "CNPJ (A->Z)": ORDER_LABEL_CNPJ,
    "Nome (A->Z)": ORDER_LABEL_NOME,
    "Ultima Alteracao (mais recente)": ORDER_LABEL_UPDATED_RECENT,
    "Ultima Alteracao (mais antiga)": ORDER_LABEL_UPDATED_OLD,
    "ID (1→9)": ORDER_LABEL_ID_ASC,
    "ID (1->9)": ORDER_LABEL_ID_ASC,
    "ID (9→1)": ORDER_LABEL_ID_DESC,
    "ID (9->1)": ORDER_LABEL_ID_DESC,
}

DEFAULT_ORDER_LABEL = ORDER_LABEL_RAZAO

ORDER_CHOICES: Dict[str, Tuple[Optional[str], bool]] = {
    ORDER_LABEL_RAZAO: ("razao_social", False),
    ORDER_LABEL_CNPJ: ("cnpj", False),
    ORDER_LABEL_NOME: ("nome", False),
    ORDER_LABEL_ID_ASC: ("id", False),
    ORDER_LABEL_ID_DESC: ("id", True),
    ORDER_LABEL_UPDATED_RECENT: ("ultima_alteracao", False),
    ORDER_LABEL_UPDATED_OLD: ("ultima_alteracao", True),
}

__all__ = ["MainScreenFrame", "DEFAULT_ORDER_LABEL", "ORDER_CHOICES"]


class MainScreenFrame(tb.Frame):  # pyright: ignore[reportGeneralTypeIssues]
    """

    Frame da tela principal (lista de clientes + aÃ§Ãµes).

    Recebe callbacks do App para operaÃ§Ãµes de negÃ³cio.

    """

    @staticmethod
    def _normalize_order_label(label: Optional[str]) -> str:
        normalized = (label or "").strip()
        return ORDER_LABEL_ALIASES.get(normalized, normalized)

    @classmethod
    def _normalize_order_choices(cls, order_choices: Dict[str, Tuple[Optional[str], bool]]) -> Dict[str, Tuple[Optional[str], bool]]:
        normalized: Dict[str, Tuple[Optional[str], bool]] = {}
        for key, value in order_choices.items():
            normalized_label = cls._normalize_order_label(key)
            normalized[normalized_label] = value
        return normalized

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

        self.app = app

        self.on_new = on_new

        self.on_edit = on_edit

        self.on_delete = on_delete

        self.on_upload = on_upload

        self.on_upload_folder = on_upload_folder

        self.on_open_subpastas = on_open_subpastas

        self.on_open_lixeira = on_open_lixeira

        self._order_choices = self._normalize_order_choices(order_choices or ORDER_CHOICES)

        self._default_order_label = self._normalize_order_label(default_order_label) or DEFAULT_ORDER_LABEL
        if self._default_order_label not in self._order_choices:
            self._default_order_label = DEFAULT_ORDER_LABEL

        self._buscar_after: Optional[str] = None

        self._vm = ClientesViewModel(
            order_choices=self._order_choices,
            default_order_label=self._default_order_label,
            author_resolver=self._resolve_author_initial,
        )

        self._pick_controller = PickModeController(self)

        self._connectivity = ClientesConnectivityController(self)

        # Modo de seleção (para integração com Senhas)

        self._pick_mode: bool = False

        self._on_pick = None  # callable(dict_cliente)

        self._return_to = None  # callable() que volta pra tela anterior

        self._saved_toolbar_state = {}  # Armazena estado dos botões CRUD

        self._current_rows: List[ClienteRow] = []

        self.toolbar = ClientesToolbar(
            self,
            order_choices=list(self._order_choices.keys()),
            default_order=self._default_order_label,
            status_choices=STATUS_CHOICES,
            on_search_changed=lambda text: self._buscar(text),
            on_clear_search=self._limpar_busca,
            on_order_changed=lambda _value: self.carregar(),
            on_status_changed=lambda _value: self.apply_filters(),
            on_open_trash=lambda: self._invoke_safe(self.on_open_lixeira),
        )

        self.toolbar.pack(fill="x", padx=10, pady=10)

        self.var_busca = self.toolbar.var_busca

        self.var_ordem = self.toolbar.var_ordem

        normalized_order = self._normalize_order_label(self.var_ordem.get())
        if normalized_order != self.var_ordem.get():
            self.var_ordem.set(normalized_order)

        self.var_status = self.toolbar.var_status

        self.status_filter = self.toolbar.status_combobox

        self.entry_busca = self.toolbar.entry_busca

        self.status_menu: Optional[tk.Menu] = None

        self._status_menu_cliente: Optional[int] = None

        self._status_menu_row: Optional[str] = None

        self.btn_lixeira = self.toolbar.lixeira_button

        # --- DivisÃ³ria entre filtros e a faixa de controles de colunas

        self._cols_separator = ttk.Separator(self, orient="horizontal")

        self._cols_separator.pack(side="top", fill="x", padx=10, pady=(6, 4))

        # --- Faixa alinhada Ã s colunas (fora do Treeview, mas sincronizada)

        HEADER_CTRL_H = 26  # altura da faixa dos controles

        self.columns_align_bar = tk.Frame(self, height=HEADER_CTRL_H)

        self.columns_align_bar.pack(side="top", fill="x", padx=10)

        # IDs/ordem exatos das colunas

        self._col_order = (
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

        self._user_key = _user_key()

        _saved = load_columns_visibility(self._user_key)

        self._col_content_visible = {c: tk.BooleanVar(value=_saved.get(c, True)) for c in self._col_order}

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

        self.client_list = create_clients_treeview(
            self.client_list_container,
            on_double_click=lambda _event: self._invoke_safe(self.on_edit),
            on_select=self._update_main_buttons_state,
            on_delete=lambda _event: self._invoke_safe(self.on_delete),
            on_click=self._on_click,
        )

        # Scrollbar vertical

        self.clients_scrollbar = tb.Scrollbar(
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

        self.tree = self.client_list

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

        self._col_widths = {}

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

        self._col_ctrls = {}  # col -> {"frame":..., "label":..., "check":...}

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

            except Exception:
                pass

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

                    except Exception:
                        pass

                _sync_col_controls()

            self.client_list.configure(xscrollcommand=_xscroll_proxy)

        except Exception:
            pass

        # primeira sincronizaÃ§Ã£o

        _sync_col_controls()

        self.footer = ClientesFooter(
            self,
            on_novo=lambda: self._invoke_safe(self.on_new),
            on_editar=lambda: self._invoke_safe(self.on_edit),
            on_subpastas=lambda: self._invoke_safe(self.on_open_subpastas),
            on_enviar_supabase=lambda: self._invoke_safe(self.on_upload),
            on_enviar_pasta=lambda: self._invoke_safe(self.on_upload_folder),
        )

        self.footer.pack(fill="x", padx=10, pady=10)

        self.btn_novo = self.footer.btn_novo

        self.btn_editar = self.footer.btn_editar

        self.btn_subpastas = self.footer.btn_subpastas

        self.btn_enviar = self.footer.btn_enviar

        self.menu_enviar = self.footer.enviar_menu

        self._uploading_busy = False

        self._send_button_prev_text: Optional[str] = None

        self.btn_enviar.state(["disabled"])

        try:
            last_index = self.menu_enviar.index("end")

            if last_index is not None:
                for idx in range(last_index + 1):
                    self.menu_enviar.entryconfigure(idx, state="disabled")

        except Exception:
            pass

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

        # UI do modo de seleÃ§Ã£o (oculto inicialmente)

        self._pick_banner_frame = tb.Frame(self, bootstyle="info")

        self._pick_label = tb.Label(
            self._pick_banner_frame,
            text="ðŸ” Modo seleÃ§Ã£o: dÃª duplo clique em um cliente ou pressione Enter",
            font=("", 10, "bold"),  # pyright: ignore[reportArgumentType]
            bootstyle="info-inverse",
        )

        self._pick_label.pack(side="left", padx=10, pady=5)

        btn_cancel_pick = tb.Button(
            self._pick_banner_frame,
            text="âœ• Cancelar",
            bootstyle="danger-outline",
            command=self._pick_controller.cancel_pick,
        )

        btn_cancel_pick.pack(side="right", padx=10, pady=5)

        self.btn_select = tb.Button(
            self._pick_banner_frame,
            text="âœ“ Selecionar",
            command=self._pick_controller.confirm_pick,
            state="disabled",
            bootstyle="success",
        )

        self.btn_select.pack(side="right", padx=10, pady=5)

        # StatusBar removido - agora Ã© global no main_window

        # Usar referÃªncias da App

        if self.app is not None:
            self.clients_count_var = getattr(self.app, "clients_count_var", None)

            self.status_var_dot = getattr(self.app, "status_var_dot", None)

            self.status_var_text = getattr(self.app, "status_var_text", None)

            self.status_dot = getattr(self.app, "status_dot", None)

            self.status_lbl = getattr(self.app, "status_lbl", None)

            setattr(self.app, "_main_frame_ref", self)

        self._update_main_buttons_state()

        # Inicia verificaÃ§Ã£o periÃ³dica de conectividade

        self._connectivity.start()

    def set_uploading(self, busy: bool) -> None:
        """Disable upload actions while an upload job is running."""

        busy = bool(busy)

        if busy == self._uploading_busy:
            return

        self._uploading_busy = busy

        try:
            if hasattr(self, "footer"):
                self.footer.set_uploading(busy)

        except Exception:
            pass

        self._update_main_buttons_state()

    def _start_connectivity_monitor(self) -> None:
        self._connectivity.start()

    def carregar(self) -> None:
        """Preenche a tabela de clientes."""

        order_label_raw = self.var_ordem.get()
        order_label = self._normalize_order_label(order_label_raw)
        if order_label != order_label_raw:
            self.var_ordem.set(order_label)

        search_term = self.var_busca.get().strip()

        log.info("Atualizando lista (busca='%s', ordem='%s')", search_term, order_label)

        self._vm.set_order_label(order_label, rebuild=False)

        self._vm.set_search_text(search_term, rebuild=False)

        try:
            self._vm.refresh_from_service()

        except ClientesViewModelError as exc:
            log.warning("Falha ao carregar lista: %s", exc)

            messagebox.showerror("Erro", f"Falha ao carregar lista: {exc}", parent=self)

            return

        self._populate_status_filter_options()

        self._refresh_list_from_vm()

    def _sort_by(self, column: str) -> None:
        current = self._normalize_order_label(self.var_ordem.get())

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

        except Exception:
            pass

        self._buscar_after = self.after(200, self.carregar)

    def _limpar_busca(self) -> None:
        self.var_busca.set("")

        self.var_status.set("Todos")

        self.carregar()

    def apply_filters(self, *_: Any) -> None:
        search_term = self.var_busca.get().strip()

        status_value = (self.var_status.get() or "").strip()

        status_filter = None if not status_value or status_value.lower() == "todos" else status_value

        self._vm.set_search_text(search_term, rebuild=False)

        self._vm.set_status_filter(status_filter, rebuild=True)

        self._refresh_list_from_vm()

    def _populate_status_filter_options(self) -> None:
        statuses = self._vm.get_status_choices()

        choices = ["Todos"] + statuses if statuses else ["Todos"]

        try:
            self.status_filter.configure(values=choices)

        except Exception:
            pass

        current = (self.var_status.get() or "").strip()

        normalized_current = current.lower()

        available_map = {choice.lower(): choice for choice in choices}

        if normalized_current in available_map:
            resolved = available_map[normalized_current]

            if resolved != current:
                self.var_status.set(resolved)

        else:
            self.var_status.set("Todos")

    def _refresh_list_from_vm(self) -> None:
        self._current_rows = self._vm.get_rows()

        self._render_clientes(self._current_rows)

    def _row_values_masked(self, row: ClienteRow) -> tuple:
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

        except Exception:
            pass

        for row in rows:
            tags = ("has_obs",) if row.observacoes.strip() else ()

            self.client_list.insert("", "end", values=self._row_values_masked(row), tags=tags)

        raw_clientes = [row.raw.get("cliente") for row in rows if isinstance(row.raw, dict) and row.raw.get("cliente") is not None]

        count = len(rows) if isinstance(rows, (list, tuple)) else len(self.client_list.get_children())

        self._set_count_text(count, raw_clientes)

        self._update_main_buttons_state()

        try:
            self.after(50, lambda: None)

        except Exception:
            pass

    def _apply_connectivity_state(self, state: str, description: str, text: str, _style: str, _tooltip: str) -> None:
        """

        Aplica efeitos de conectividade (enable/disable, textos, status bar).

        """

        try:
            if self.app is not None:
                setattr(self.app, "_net_is_online", state == "online")

                setattr(self.app, "_net_state", state)

                setattr(self.app, "_net_description", description)

        except Exception:
            pass

        # Atualiza estado dos botões e textos

        try:
            self._update_main_buttons_state()

            if hasattr(self, "btn_enviar") and not self._uploading_busy:
                if state == "online":
                    self.btn_enviar.configure(text="Enviar Para SupaBase")

                elif state == "unstable":
                    self.btn_enviar.configure(text="Envio suspenso – Conexão instável")

                else:
                    self.btn_enviar.configure(text="Envio suspenso – Offline")

        except Exception:
            pass

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

            except Exception:
                pass

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

    def _apply_status_for(self, cliente_id: int, chosen: str) -> None:
        """Atualiza o [STATUS] no campo Observações e recarrega a grade."""

        try:
            cli = fetch_cliente_by_id(cliente_id)

            if not cli:
                return

            old_obs = (getattr(cli, "obs", None) or getattr(cli, "observacoes", None) or "").strip()

            _, body = self._vm.extract_status_and_observacoes(old_obs)

            update_cliente_status_and_observacoes(cliente_id=cliente_id, novo_status=chosen, texto_observacoes=body)

            self.carregar()

        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao atualizar status: {e}", parent=self)

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

        allow_send = has_sel and online and not self._uploading_busy

        try:
            # BotÃµes que dependem de conexÃ£o E seleÃ§Ã£o

            self.btn_editar.configure(state=("normal" if (has_sel and online) else "disabled"))

            self.btn_subpastas.configure(state=("normal" if (has_sel and online) else "disabled"))

            if allow_send:
                self.btn_enviar.state(["!disabled"])

            else:
                self.btn_enviar.state(["disabled"])

            if hasattr(self, "menu_enviar") and self.menu_enviar is not None:
                try:
                    last_index = self.menu_enviar.index("end")

                    if last_index is not None:
                        entry_state = "normal" if allow_send else "disabled"

                        for idx in range(last_index + 1):
                            self.menu_enviar.entryconfigure(idx, state=entry_state)

                except Exception:
                    pass

            # BotÃµes que dependem apenas de conexÃ£o

            self.btn_novo.configure(state=("normal" if online else "disabled"))

            self.btn_lixeira.configure(state=("normal" if online else "disabled"))

            # BotÃ£o de seleÃ§Ã£o (modo pick) - nÃ£o depende de conexÃ£o

            if self._pick_mode and hasattr(self, "btn_select"):
                self.btn_select.configure(state=("normal" if has_sel else "disabled"))

        except Exception as e:
            log.debug("Erro ao atualizar estado dos botÃµes: %s", e)

    def _resolve_order_preferences(self) -> Tuple[Optional[str], bool]:
        label = self._normalize_order_label(self.var_ordem.get())
        return self._order_choices.get(label, (None, False))

    def _set_count_text(self, count: int, clientes: Sequence[Any] | None = None) -> None:
        try:
            from datetime import datetime, date

            total_clients = count

            new_today = 0

            new_month = 0

            if clientes:
                today = date.today()

                first_of_month = today.replace(day=1)

                def parse_created_at(c):
                    created_str = getattr(c, "created_at", None) or c.get("created_at") if hasattr(c, "get") else None

                    if not created_str:
                        return None

                    try:
                        return datetime.fromisoformat(created_str)

                    except Exception:
                        return None

                created_dates = [parse_created_at(c) for c in clientes]

                new_today = sum(1 for d in created_dates if d and d.date() == today)

                new_month = sum(1 for d in created_dates if d and d.date() >= first_of_month)

            # Atualiza o StatusFooter global

            if self.app and self.app.status_footer:
                self.app.status_footer.set_clients_summary(total_clients, new_today, new_month)

        except Exception:
            pass

    # =========================================================================

    # Modo de seleÃ§Ã£o para integraÃ§Ã£o com Senhas

    # =========================================================================

    # Modo de seleção para integração com Senhas

    # =========================================================================

    def start_pick(self, on_pick, return_to=None):
        """API pública usada pelo router para modo pick (Senhas)."""

        self._pick_controller.start_pick(on_pick=on_pick, return_to=return_to)

    def _on_pick_cancel(self, *_):
        self._pick_controller.cancel_pick()

    def _on_pick_confirm(self, *_):
        self._pick_controller.confirm_pick()

    @staticmethod
    def _invoke(callback: Optional[Callable[[], None]]) -> None:
        if callable(callback):
            callback()

    def _invoke_safe(self, callback: Optional[Callable[[], None]]) -> None:
        """Invoca callback apenas se NÃƒO estiver em modo seleÃ§Ã£o."""

        if getattr(self, "_pick_mode", False):
            return

        if callable(callback):
            callback()
