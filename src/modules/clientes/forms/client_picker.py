# -*- coding: utf-8 -*-
"""
Dialogos/pickers especificos de clientes.
"""

from __future__ import annotations

import logging
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Dict, Optional

import ttkbootstrap as tb

from src.data.domain_types import ClientRow
from src.ui.components.progress_dialog import BusyDialog
from src.ui.window_utils import show_centered


def _get_field(row: Any, key: str, default: str = "") -> str:
    """Le campo de dict ou objeto; retorna string sempre."""
    if isinstance(row, dict):
        return str(row.get(key, default) or "")
    return str(getattr(row, key, default) or "")


def _format_cnpj(value: str) -> str:
    """Formata CNPJ para 00.000.000/0000-00; se nao tiver 14 digitos, retorna o original.

    Wrapper para compatibilidade. Delega para src.helpers.formatters.format_cnpj.
    """
    from src.helpers.formatters import format_cnpj as _format_cnpj_canonical

    return _format_cnpj_canonical(value)


def _display_name(row: Any) -> str:
    """Nome do cliente para exibir: usa 'nome' ou 'nome_fantasia'."""
    try:
        for key in ("nome", "nome_fantasia"):
            value = (_get_field(row, key) or "").strip()
            if value:
                return value
    except Exception:
        return ""
    return ""


log = logging.getLogger(__name__)


class ClientPicker(tk.Toplevel):
    """
    Toplevel modal para selecionar cliente.

    Uso:
        picker = ClientPicker(parent, org_id="org_123")
        result = picker.show_modal()  # retorna Dict ou None
    """

    def __init__(self, master, org_id: str = "", **kwargs):
        super().__init__(master, **kwargs)
        self.withdraw()

        self.org_id = org_id
        self._result: Optional[Dict[str, Any]] = None
        self._clients_data: list[Any] = []  # Cache de dados completos
        self._search_placeholder = "Digite nome, CNPJ, telefone..."
        self._busy_dialog: Optional[BusyDialog] = None
        self._search_pending = False  # Evita múltiplas buscas simultâneas
        self._destroyed = False  # Flag para evitar atualização de widgets destruídos

        # Configurar modal
        self.title("Selecionar Cliente")
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w = max(980, min(int(sw * 0.60), 1400))
        h = max(520, min(int(sh * 0.60), 900))
        self.minsize(w, h)
        self.transient(master)

        # Construir interface
        self._build_ui()

        # Centralizar na tela
        self.update_idletasks()
        show_centered(self)
        self.grab_set()

    def _build_ui(self) -> None:
        """Constroi interface do modal."""
        # Frame principal
        main = tb.Frame(self, padding=10)
        main.pack(fill="both", expand=True)

        # Frame de busca
        search_frame = tb.Frame(main)
        search_frame.pack(fill="x", pady=(0, 10))

        tb.Label(search_frame, text="Buscar:").pack(side="left", padx=(0, 5))

        self.entry_search = tb.Entry(search_frame, width=40)
        self.entry_search.pack(side="left", fill="x", expand=True, padx=5)
        self.entry_search.insert(0, self._search_placeholder)
        self.entry_search.bind("<FocusIn>", self._clear_placeholder)
        self.entry_search.bind("<Return>", lambda e: self._do_search())
        self.entry_search.bind("<KeyRelease>", self._on_key_release)

        self.search_button = tb.Button(search_frame, text="Buscar", command=self._do_search, bootstyle="primary")
        self.search_button.pack(side="left", padx=5)

        # Treeview
        tree_frame = tb.Frame(main)
        tree_frame.pack(fill="both", expand=True, pady=(0, 10), padx=(10, 10))

        self.tree = ttk.Treeview(
            tree_frame,
            columns=("id", "razao_social", "cnpj", "nome"),
            show="headings",
            selectmode="browse",
            height=15,
        )

        # Ordem fixa pedida: ID | Razao Social | CNPJ | Nome
        self.tree["columns"] = ("id", "razao_social", "cnpj", "nome")
        self.tree["displaycolumns"] = ("id", "razao_social", "cnpj", "nome")
        self.tree["show"] = "headings"

        # Cabecalhos (texto centralizado)
        self.tree.heading("id", text="ID", anchor="center")
        self.tree.heading("razao_social", text="Razao Social", anchor="center")
        self.tree.heading("cnpj", text="CNPJ", anchor="center")
        self.tree.heading("nome", text="Nome", anchor="center")

        # Celulas (conteudo): ID/CNPJ fixos; Razao/Nome expansivos
        self.tree.column("id", width=80, anchor="center", stretch=False)
        self.tree.column("razao_social", width=280, anchor="w")
        self.tree.column("cnpj", width=160, anchor="w", stretch=False)
        self.tree.column("nome", width=260, anchor="w")

        self.tree.pack(fill="both", expand=True)

        # Scroller
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Rodape com botoes
        footer = tb.Frame(main)
        footer.pack(fill="x", pady=(10, 0))

        tb.Button(footer, text="Selecionar", command=self._confirm, bootstyle="success").pack(side="right", padx=5)
        tb.Button(footer, text="Cancelar", command=self._cancel, bootstyle="secondary").pack(side="right")

    def _clear_placeholder(self, event) -> None:
        """Limpa placeholder ao focar entry."""
        if self.entry_search.get() == self._search_placeholder:
            self.entry_search.delete(0, "end")

    def _on_key_release(self, event) -> None:
        """Atualiza busca ao digitar (busca instantanea)."""
        if event.keysym in ("Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R", "Return"):
            return
        self._do_search()

    def _safe_after(self, delay: int, callback) -> None:
        """Agenda callback apenas se widget ainda existir."""
        if self._destroyed:
            return
        try:
            self.after(delay, callback)
        except tk.TclError:
            pass

    def _close_busy(self) -> None:
        """Fecha diálogo de progresso se existir."""
        if self._busy_dialog is not None:
            try:
                self._busy_dialog.close()
            except Exception:  # noqa: BLE001
                log.exception("Falha ao fechar BusyDialog do ClientPicker")
            self._busy_dialog = None

    def _set_search_enabled(self, enabled: bool) -> None:
        """Habilita/desabilita controles de busca."""
        state = "normal" if enabled else "disabled"
        try:
            self.search_button.configure(state=state)
            self.entry_search.configure(state=state)
        except tk.TclError:
            pass

    def _load_initial(self) -> None:
        """Carrega lista inicial de clientes ao abrir modal (async)."""
        if self._search_pending:
            return

        self._search_pending = True
        self._set_search_enabled(False)

        # Mostrar busy dialog
        try:
            self._busy_dialog = BusyDialog(self, text="Carregando clientes...")
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao criar BusyDialog: %s", exc)
            self._busy_dialog = None

        result: dict[str, Any] = {"data": [], "error": None}

        def _worker() -> None:
            try:
                from src.data.supabase_repo import list_clients_for_picker

                t0 = time.perf_counter()
                results: list[ClientRow] = list_clients_for_picker(self.org_id, limit=500)
                t1 = time.perf_counter()
                result["data"] = results
                log.info("Senhas: consulta clientes inicial (%s linhas) em %.3fs", len(results), t1 - t0)
            except Exception as e:
                result["error"] = e
                log.warning("ClientPicker: erro ao carregar lista inicial: %s", e)
            finally:
                self._safe_after(0, _on_done)

        def _on_done() -> None:
            self._search_pending = False
            self._close_busy()
            self._set_search_enabled(True)

            if self._destroyed:
                return

            if result["error"] is not None:
                self._fill_table([])
            else:
                self._fill_table(result["data"])
                log.debug("ClientPicker: %s clientes carregados inicialmente", len(result["data"]))

        threading.Thread(target=_worker, daemon=True).start()

    def _do_search(self) -> None:
        """Busca clientes baseado na query ou lista todos se query < 2 (async)."""
        # Se já há busca em andamento, ignorar
        if self._search_pending:
            return

        query = self.entry_search.get().strip()

        if query == self._search_placeholder:
            query = ""

        self._search_pending = True
        self._set_search_enabled(False)

        # Para buscas por digitação, não mostrar busy dialog (seria intrusivo)
        # Apenas para buscas mais longas (lista completa) ou Enter
        show_busy = len(query) < 2
        if show_busy:
            try:
                self._busy_dialog = BusyDialog(self, text="Buscando clientes...")
            except Exception as exc:  # noqa: BLE001
                log.debug("Falha ao criar BusyDialog para busca: %s", exc)
                self._busy_dialog = None

        result: dict[str, Any] = {"data": [], "error": None, "query": query}

        def _worker() -> None:
            try:
                from src.data.supabase_repo import list_clients_for_picker, search_clients

                t0 = time.perf_counter()
                results: list[ClientRow]
                if len(query) < 2:
                    results = list_clients_for_picker(self.org_id, limit=500)
                else:
                    results = search_clients(self.org_id, query, limit=100)

                t1 = time.perf_counter()
                result["data"] = results
                log.info(
                    "Senhas: consulta clientes (%s linhas, query='%s') em %.3fs",
                    len(results),
                    query or "<vazio>",
                    t1 - t0,
                )
            except Exception as e:
                result["error"] = e
                log.error("ClientPicker: erro ao buscar clientes: %s", e)
            finally:
                self._safe_after(0, _on_done)

        def _on_done() -> None:
            self._search_pending = False
            self._close_busy()
            self._set_search_enabled(True)

            if self._destroyed:
                return

            if result["error"] is not None:
                messagebox.showerror("Erro", f"Falha ao buscar clientes:\n{result['error']}", parent=self)
            else:
                self._fill_table(result["data"])

        threading.Thread(target=_worker, daemon=True).start()

    def _fill_table(self, results: list[ClientRow]) -> None:
        """Preenche Treeview com resultados."""
        t0 = time.perf_counter()
        children = self.tree.get_children()
        if children:
            self.tree.delete(*children)

        rows: list[Any] = list(results or [])
        self._clients_data = rows

        if not rows:
            log.info("Senhas: treeview clientes populada em %.3fs (0 linhas)", time.perf_counter() - t0)
            return

        def sort_key(row: Any) -> tuple[int, str]:
            razao = _get_field(row, "razao_social").strip()
            cnpj = _get_field(row, "cnpj").strip()
            incompleto = 1 if not razao or not cnpj else 0
            return incompleto, (razao or "").upper()

        sorted_rows = sorted(rows, key=sort_key)

        for row in sorted_rows:
            rid = _get_field(row, "id")
            razao = _get_field(row, "razao_social")
            cnpj_raw = _get_field(row, "cnpj_norm") or _get_field(row, "cnpj")
            cnpj_fmt = _format_cnpj(cnpj_raw)
            nome = _display_name(row)

            self.tree.insert(
                "",
                "end",
                iid=str(rid) if rid else "",
                values=(rid, razao, cnpj_fmt, nome),
            )
        log.info("Senhas: treeview clientes populada em %.3fs (%s linhas)", time.perf_counter() - t0, len(sorted_rows))

    def _confirm(self) -> None:
        """Confirma selecao e fecha modal."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Atencao", "Selecione um cliente primeiro.", parent=self)
            return

        item = selection[0]
        try:
            client_id = int(item)
        except (ValueError, TypeError):
            return

        if hasattr(self, "_clients_data"):
            for client in self._clients_data:
                stored_id_text = _get_field(client, "id")
                try:
                    stored_id = int(stored_id_text)
                except ValueError:
                    stored_id = None

                if (stored_id is not None and stored_id == client_id) or stored_id_text == str(client_id):
                    self._result = client
                    break

        self.destroy()

    def _cancel(self) -> None:
        """Cancela e fecha modal."""
        self._result = None
        self.destroy()

    def destroy(self) -> None:
        """Override para marcar janela como destruída e limpar recursos."""
        self._destroyed = True
        self._close_busy()
        try:
            super().destroy()
        except tk.TclError:
            pass

    def show_modal(self) -> Optional[Dict[str, Any]]:
        """Exibe modal, carrega lista inicial e retorna resultado (Dict ou None)."""
        self.after(50, self._load_initial)
        self.wait_window(self)
        return self._result
