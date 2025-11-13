# gui/widgets/client_picker.py
# -*- coding: utf-8 -*-
"""Modal para seleção de cliente."""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Dict, Optional

import ttkbootstrap as tb

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

        self.org_id = org_id
        self._result: Optional[Dict[str, Any]] = None
        self._clients_data = []  # Cache de dados completos

        # Configurar modal
        self.title("Selecionar Cliente")
        self.geometry("800x500")
        self.transient(master)
        self.grab_set()

        # Construir interface
        self._build_ui()

        # Centralizar na tela
        self.update_idletasks()
        self._center_window()

    def _build_ui(self) -> None:
        """Constrói interface do modal."""
        # Frame principal
        main = tb.Frame(self, padding=10)
        main.pack(fill="both", expand=True)

        # Frame de busca
        search_frame = tb.Frame(main)
        search_frame.pack(fill="x", pady=(0, 10))

        tb.Label(search_frame, text="Buscar:").pack(side="left", padx=(0, 5))

        self.entry_search = tb.Entry(search_frame, width=40)
        self.entry_search.pack(side="left", fill="x", expand=True, padx=5)
        self.entry_search.insert(0, "Digite nome, fantasia ou CNPJ...")
        self.entry_search.bind("<FocusIn>", self._clear_placeholder)
        self.entry_search.bind("<Return>", lambda e: self._do_search())
        self.entry_search.bind("<KeyRelease>", self._on_key_release)

        btn_search = tb.Button(search_frame, text="🔍 Buscar", command=self._do_search, bootstyle="primary")
        btn_search.pack(side="left", padx=5)

        # Treeview
        tree_frame = tb.Frame(main)
        tree_frame.pack(fill="both", expand=True, pady=(0, 10))

        columns = ("razao", "fantasia", "cnpj")
        self.tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
            height=15,
        )

        self.tree.heading("razao", text="Razão Social")
        self.tree.heading("fantasia", text="Nome Fantasia")
        self.tree.heading("cnpj", text="CNPJ")

        self.tree.column("razao", width=300)
        self.tree.column("fantasia", width=250)
        self.tree.column("cnpj", width=150)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Bind: duplo clique para selecionar
        self.tree.bind("<Double-Button-1>", lambda e: self._confirm())

        # Botões de ação
        btn_frame = tb.Frame(main)
        btn_frame.pack(fill="x")

        tb.Button(btn_frame, text="Selecionar", command=self._confirm, bootstyle="success").pack(side="right", padx=5)
        tb.Button(btn_frame, text="Cancelar", command=self._cancel, bootstyle="secondary").pack(side="right")

    def _center_window(self) -> None:
        """Centraliza janela na tela."""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _clear_placeholder(self, event) -> None:
        """Limpa placeholder ao focar."""
        if self.entry_search.get() == "Digite nome, fantasia ou CNPJ...":
            self.entry_search.delete(0, tk.END)

    def _on_key_release(self, event) -> None:
        """Atualiza busca ao digitar (busca instantânea)."""
        # Ignorar teclas especiais
        if event.keysym in (
            "Shift_L",
            "Shift_R",
            "Control_L",
            "Control_R",
            "Alt_L",
            "Alt_R",
            "Return",
        ):
            return
        self._do_search()

    def _load_initial(self) -> None:
        """Carrega lista inicial de clientes ao abrir modal."""
        try:
            from data.supabase_repo import list_clients_for_picker

            results = list_clients_for_picker(self.org_id, limit=500)
            self._fill_table(results)
            log.debug(f"ClientPicker: {len(results)} clientes carregados inicialmente")
        except Exception as e:
            log.warning(f"ClientPicker: erro ao carregar lista inicial: {e}")
            self._fill_table([])

    def _do_search(self) -> None:
        """Busca clientes baseado na query ou lista todos se query < 2."""
        query = self.entry_search.get().strip()

        # Ignorar placeholder
        if query == "Digite nome, fantasia ou CNPJ...":
            query = ""

        # Buscar clientes
        try:
            from data.supabase_repo import list_clients_for_picker, search_clients

            if len(query) < 2:
                # Lista todos os clientes
                results = list_clients_for_picker(self.org_id, limit=500)
            else:
                # Busca com filtro
                results = search_clients(self.org_id, query, limit=100)

            self._fill_table(results)

        except Exception as e:
            log.error(f"ClientPicker: erro ao buscar clientes: {e}")
            messagebox.showerror("Erro", f"Falha ao buscar clientes:\n{e}", parent=self)

    def _fill_table(self, results: list) -> None:
        """Preenche Treeview com resultados."""
        # Limpar árvore
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Armazenar dados completos
        self._clients_data = results

        # Preencher árvore
        if not results:
            return

        for client in results:
            razao = client.get("razao_social", "")
            fantasia = client.get("nome_fantasia", "")
            cnpj = client.get("cnpj", "")

            self.tree.insert(
                "",
                "end",
                values=(razao, fantasia, cnpj),
                tags=(str(client.get("id", "")),),
            )

    def _confirm(self) -> None:
        """Confirma seleção e fecha modal."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Atenção", "Selecione um cliente primeiro.", parent=self)
            return

        # Obter ID do cliente selecionado
        item = selection[0]
        tags = self.tree.item(item, "tags")
        if not tags:
            return

        try:
            client_id = int(tags[0])
        except (ValueError, IndexError):
            return

        # Buscar dados completos
        if hasattr(self, "_clients_data"):
            for client in self._clients_data:
                if client.get("id") == client_id:
                    self._result = client
                    break

        # Fechar modal
        self.destroy()

    def _cancel(self) -> None:
        """Cancela e fecha modal."""
        self._result = None
        self.destroy()

    def show_modal(self) -> Optional[Dict[str, Any]]:
        """Exibe modal, carrega lista inicial e retorna resultado (Dict ou None)."""
        # Carregar lista inicial após 50ms (permite UI renderizar)
        self.after(50, self._load_initial)
        self.wait_window(self)
        return self._result
