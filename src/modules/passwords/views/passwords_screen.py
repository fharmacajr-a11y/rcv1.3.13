# -*- coding: utf-8 -*-
"""Tela de gerenciamento de senhas com filtros, tabela e diálogo modal."""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable, Optional

import ttkbootstrap as tb

from data.domain_types import ClientRow, PasswordRow
from src.modules.passwords.controller import PasswordsController

log = logging.getLogger(__name__)


class PasswordDialog(tb.Toplevel):
    """Diálogo modal para criação/edição de senha."""

    def __init__(
        self,
        parent: tb.Widget,
        org_id: str,
        user_id: str,
        clients: list[ClientRow],
        on_save: Callable[[], None],
        password_data: Optional[PasswordRow] = None,
        controller: Optional[PasswordsController] = None,
    ) -> None:
        super().__init__(parent)
        self.title("Nova Senha" if password_data is None else "Editar Senha")
        self.geometry("500x400")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.org_id = org_id
        self.user_id = user_id
        self.clients = clients
        self.on_save = on_save
        self.password_data = password_data
        self.is_editing = password_data is not None
        self.controller = controller or PasswordsController()

        # Cliente selecionado
        self.selected_client_id: Optional[str] = None
        self.selected_client_display: str = ""

        self._build_ui()
        if self.is_editing:
            self._load_data()

        self._center_on_parent()

    def _center_on_parent(self) -> None:
        """Centraliza o diálogo na janela principal."""
        self.update_idletasks()
        if self.master is None:
            return
        parent_x = self.master.winfo_rootx()
        parent_y = self.master.winfo_rooty()
        parent_width = self.master.winfo_width()
        parent_height = self.master.winfo_height()

        width = self.winfo_width()
        height = self.winfo_height()

        x = parent_x + (parent_width - width) // 2
        y = parent_y + (parent_height - height) // 2

        self.geometry(f"{width}x{height}+{x}+{y}")

    def _build_ui(self) -> None:
        """Constrói a interface do diálogo."""
        container = tb.Frame(self, padding=20)
        container.pack(fill="both", expand=True)

        # Cliente
        tb.Label(container, text="Cliente:").grid(row=0, column=0, sticky="w", pady=5)
        client_frame = tb.Frame(container)
        client_frame.grid(row=0, column=1, sticky="ew", pady=5, padx=(10, 0))

        self.client_display_var = tk.StringVar()
        self.client_display_entry = tb.Entry(
            client_frame,
            textvariable=self.client_display_var,
            state="readonly",
            width=40,
        )
        self.client_display_entry.pack(side="left", fill="x", expand=True)

        self.select_client_button = tb.Button(
            client_frame,
            text="Selecionar...",
            bootstyle="secondary",
            command=self._on_select_client_clicked,
        )
        self.select_client_button.pack(side="right", padx=(5, 0))

        # Serviço
        tb.Label(container, text="Serviço:").grid(row=1, column=0, sticky="w", pady=5)
        self.service_var = tk.StringVar()
        self.service_combo = tb.Combobox(
            container,
            textvariable=self.service_var,
            values=["SIFAP", "CRF", "GOV.BR", "E-mail", "Banco", "Outro"],
        )
        self.service_combo.grid(row=1, column=1, sticky="ew", pady=5, padx=(10, 0))

        # Usuário/Login
        tb.Label(container, text="Usuário / Login:").grid(row=2, column=0, sticky="w", pady=5)
        self.username_var = tk.StringVar()
        self.username_entry = tb.Entry(container, textvariable=self.username_var)
        self.username_entry.grid(row=2, column=1, sticky="ew", pady=5, padx=(10, 0))

        # Senha
        tb.Label(container, text="Senha:").grid(row=3, column=0, sticky="w", pady=5)
        self.password_var = tk.StringVar()
        self.password_entry = tb.Entry(container, textvariable=self.password_var, show="*")
        self.password_entry.grid(row=3, column=1, sticky="ew", pady=5, padx=(10, 0))

        # Anotações
        tb.Label(container, text="Anotações:").grid(row=4, column=0, sticky="w", pady=5)
        self.notes_var = tk.StringVar()
        self.notes_entry = tb.Entry(container, textvariable=self.notes_var)
        self.notes_entry.grid(row=4, column=1, sticky="ew", pady=5, padx=(10, 0))

        # Botões
        btn_frame = tb.Frame(container)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=20)

        tb.Button(btn_frame, text="Salvar", bootstyle="success", command=self._save).pack(side="left", padx=5)
        tb.Button(btn_frame, text="Cancelar", bootstyle="secondary", command=self.destroy).pack(side="left", padx=5)

        container.columnconfigure(1, weight=1)

    def _on_select_client_clicked(self) -> None:
        """Abre o ClientPicker para selecionar cliente."""
        from src.modules.clientes.forms import ClientPicker

        picker = ClientPicker(self, org_id=self.org_id)
        selected_client = picker.show_modal()

        if selected_client:
            self.selected_client_id = str(selected_client["id"])
            self.selected_client_display = (
                selected_client.get("nome") or selected_client.get("nome_fantasia") or selected_client.get("razao_social") or ""
            ).strip()
            self.client_display_var.set(self.selected_client_display)

    def _load_data(self) -> None:
        """Carrega dados para edição."""
        if not self.password_data:
            return
        self.selected_client_display = self.password_data["client_name"]
        self.client_display_var.set(self.selected_client_display)
        self.service_var.set(self.password_data["service"])
        self.username_var.set(self.password_data["username"])
        # Senha não carrega por segurança
        self.notes_var.set(self.password_data["notes"])

    def _save(self) -> None:
        """Salva a senha."""
        client_name = self.selected_client_display.strip()
        service = self.service_var.get().strip()
        username = self.username_var.get().strip()
        password = self.password_var.get()
        notes = self.notes_var.get().strip()

        if not client_name or not service or not username or not password:
            messagebox.showerror("Erro", "Todos os campos são obrigatórios.")
            return

        try:
            if self.is_editing and self.password_data:
                self.controller.update_password(
                    self.password_data["id"],
                    client_name=client_name,
                    service=service,
                    username=username,
                    password_plain=password,
                    notes=notes,
                )
                messagebox.showinfo("Sucesso", "Senha atualizada com sucesso!")
            else:
                self.controller.create_password(
                    self.org_id,
                    client_name,
                    service,
                    username,
                    password,
                    notes,
                    self.user_id,
                )
                messagebox.showinfo("Sucesso", "Senha criada com sucesso!")

            self.on_save()
            self.destroy()
        except Exception as e:
            log.exception("Erro ao salvar senha")
            messagebox.showerror("Erro", f"Falha ao salvar: {e}")


class PasswordsScreen(tb.Frame):
    """Tela de gerenciamento de senhas com filtros e tabela."""

    def __init__(
        self,
        master,
        main_window: Optional[Any] = None,
        *,
        controller: Optional[PasswordsController] = None,
        **kwargs,
    ) -> None:
        super().__init__(master, padding=16, **kwargs)

        self.main_window = main_window
        self.controller = controller or PasswordsController()
        self.org_id: Optional[str] = None
        self.user_id: Optional[str] = None
        self.clients: list[ClientRow] = []
        self.passwords: list[PasswordRow] = []
        self._all_passwords: list[PasswordRow] = []
        self.password_cache: dict[str, str] = {}  # id -> decrypted password
        self._sort_column: Optional[str] = None
        self._sort_order: str = "asc"

        self._build_ui()

    def _refresh_data(self) -> None:
        """Recarrega dados do servidor e reaplica filtros."""
        self._load_all_passwords()
        self.reload_passwords()

    def _load_all_passwords(self) -> None:
        """Carrega todas as senhas do servidor."""
        if not self.org_id:
            return
        try:
            self._all_passwords = self.controller.load_all_passwords(self.org_id)
        except Exception as e:
            log.exception("Erro ao carregar senhas")
            messagebox.showerror("Erro", f"Falha ao carregar senhas: {e}")

    def _build_ui(self) -> None:
        """Constrói a interface principal."""
        # Filtros no topo
        filters_frame = tb.Frame(self)
        filters_frame.pack(fill="x", pady=(0, 10))

        # Busca
        tb.Label(filters_frame, text="Buscar:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_entry = tb.Entry(filters_frame, textvariable=self.search_var, width=40)
        self.search_entry.grid(row=0, column=1, sticky="w", padx=(0, 10))
        self.search_entry.bind("<KeyRelease>", lambda e: self.reload_passwords())

        # Serviço
        tb.Label(filters_frame, text="Serviço:").grid(row=0, column=2, sticky="w", padx=(0, 5))
        self.service_filter_var = tk.StringVar(value="Todos")
        self.service_filter_combo = tb.Combobox(
            filters_frame,
            textvariable=self.service_filter_var,
            values=["Todos", "SIFAP", "CRF", "GOV.BR", "E-mail", "Banco", "Outro"],
        )
        self.service_filter_combo.grid(row=0, column=3, sticky="ew", padx=(0, 10))
        self.service_filter_combo.bind("<<ComboboxSelected>>", lambda e: self.reload_passwords())

        filters_frame.columnconfigure(1, weight=0)
        filters_frame.columnconfigure(3, weight=1)

        # Tabela
        table_frame = tb.Frame(self)
        table_frame.pack(fill="both", expand=True)

        columns = ("cliente", "servico", "usuario", "senha", "anotacoes")
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
            height=15,
        )

        self.tree.heading("cliente", text="Cliente", command=lambda: self._sort_by_column("cliente"))
        self.tree.heading("servico", text="Serviço", command=lambda: self._sort_by_column("servico"))
        self.tree.heading("usuario", text="Usuário / Login", command=lambda: self._sort_by_column("usuario"))
        self.tree.heading("senha", text="Senha")
        self.tree.heading("anotacoes", text="Anotações", command=lambda: self._sort_by_column("anotacoes"))

        self.tree.column("cliente", width=220, minwidth=150)
        self.tree.column("servico", width=160, minwidth=120)
        self.tree.column("usuario", width=180, minwidth=140)
        self.tree.column("senha", width=80, minwidth=60)
        self.tree.column("anotacoes", width=260, minwidth=180)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.bind("<Double-1>", lambda e: self._edit_selected())

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Barra de ações
        actions_frame = tb.Frame(self)
        actions_frame.pack(fill="x", pady=(10, 0))

        tb.Button(
            actions_frame,
            text="Nova Senha",
            bootstyle="success",
            command=self._open_new_password_dialog,
            width=14,
        ).pack(side="left", padx=5)

        tb.Button(
            actions_frame,
            text="Editar",
            bootstyle="secondary",
            command=self._edit_selected,
            width=14,
        ).pack(side="left", padx=5)

        tb.Button(
            actions_frame,
            text="Excluir",
            bootstyle="danger",
            command=self._delete_selected,
            width=14,
        ).pack(side="left", padx=5)

        tb.Button(
            actions_frame,
            text="Copiar Senha",
            bootstyle="info",
            command=self._copy_password,
            width=14,
        ).pack(side="left", padx=5)

    def _open_new_password_dialog(self) -> None:
        """Abre diálogo para nova senha."""
        if not self.org_id or not self.user_id:
            messagebox.showerror("Erro", "Usuário não autenticado.")
            return
        assert self.org_id is not None
        assert self.user_id is not None
        PasswordDialog(
            self,
            self.org_id,
            self.user_id,
            self.clients,
            self._refresh_data,
            controller=self.controller,
        )

    def _edit_selected(self) -> None:
        """Edita a senha selecionada."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Atenção", "Selecione uma senha para editar.")
            return

        item_id = selection[0]
        password_id = self.tree.item(item_id, "tags")[0]
        password_data = next((p for p in self.passwords if str(p["id"]) == password_id), None)
        if not password_data:
            return

        if not self.org_id or not self.user_id:
            messagebox.showerror("Erro", "Usuário não autenticado.")
            return
        assert self.org_id is not None
        assert self.user_id is not None
        PasswordDialog(
            self,
            self.org_id,
            self.user_id,
            self.clients,
            self._refresh_data,
            password_data,
            controller=self.controller,
        )

    def _delete_selected(self) -> None:
        """Exclui a senha selecionada."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Atenção", "Selecione uma senha para excluir.")
            return

        if not messagebox.askyesno("Confirmação", "Tem certeza que deseja excluir esta senha?"):
            return

        item_id = selection[0]
        password_id = self.tree.item(item_id, "tags")[0]

        try:
            self.controller.delete_password(password_id)
            messagebox.showinfo("Sucesso", "Senha excluída com sucesso!")
            self._refresh_data()
        except Exception as e:
            log.exception("Erro ao excluir senha")
            messagebox.showerror("Erro", f"Falha ao excluir: {e}")

    def _copy_password(self) -> None:
        """Copia a senha selecionada para o clipboard."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Atenção", "Selecione uma senha para copiar.")
            return

        item_id = selection[0]
        password_id = self.tree.item(item_id, "tags")[0]
        password_data = next((p for p in self.passwords if str(p["id"]) == password_id), None)
        if not password_data:
            return

        try:
            plain_password = self.controller.decrypt_password(password_data["password_enc"])
            self.clipboard_clear()
            self.clipboard_append(plain_password)
            messagebox.showinfo("Sucesso", "Senha copiada para a área de transferência!")
        except Exception as e:
            log.exception("Erro ao copiar senha")
            messagebox.showerror("Erro", f"Falha ao copiar: {e}")

    def reload_passwords(self) -> None:
        """Recarrega as senhas com filtros aplicados (em memoria)."""
        if not self.org_id:
            return

        raw_search = self.search_var.get().strip()
        search_text = raw_search if raw_search else None
        service_filter = self.service_filter_var.get()

        try:
            self.passwords = self.controller.filter_passwords(search_text, service_filter)
            self._populate_table()
        except Exception as e:
            log.exception("Erro ao filtrar senhas")
            messagebox.showerror("Erro", f"Falha ao filtrar senhas: {e}")

    def _sort_by_column(self, column: str) -> None:
        """Ordena a tabela pela coluna especificada."""
        if self._sort_column == column:
            self._sort_order = "desc" if self._sort_order == "asc" else "asc"
        else:
            self._sort_column = column
            self._sort_order = "asc"

        reverse = self._sort_order == "desc"
        if column == "cliente":
            self.passwords.sort(key=lambda p: p["client_name"], reverse=reverse)
        elif column == "servico":
            self.passwords.sort(key=lambda p: p["service"], reverse=reverse)
        elif column == "usuario":
            self.passwords.sort(key=lambda p: p["username"], reverse=reverse)
        elif column == "anotacoes":
            self.passwords.sort(key=lambda p: p["notes"], reverse=reverse)

        self._populate_table()

    def _populate_table(self) -> None:
        """Preenche a tabela com os dados."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        for password in self.passwords:
            self.tree.insert(
                "",
                "end",
                values=(
                    password["client_name"],
                    password["service"],
                    password["username"],
                    "••••••",
                    password["notes"],
                ),
                tags=(str(password["id"]),),
            )

    def on_show(self) -> None:
        """Callback chamado ao exibir a tela."""
        try:
            # Obter org_id e user_id
            from infra.supabase_client import supabase

            user = supabase.auth.get_user()
            if user and hasattr(user, "user") and user.user:
                self.user_id = user.user.id

                app = self.winfo_toplevel()
                if hasattr(app, "_get_org_id_cached"):
                    self.org_id = app._get_org_id_cached(self.user_id)

            if not self.org_id:
                messagebox.showerror("Erro", "Organização não identificada.")
                return

            # Carregar clientes
            self.clients = self.controller.list_clients(self.org_id)

            # Carregar senhas
            self._load_all_passwords()
            self.reload_passwords()
        except Exception as e:
            log.exception("Erro ao inicializar tela de senhas")
            messagebox.showerror("Erro", f"Falha ao inicializar: {e}")
