# -*- coding: utf-8 -*-
"""Diálogo para gerenciar senhas de um cliente específico."""

from __future__ import annotations

import logging
from tkinter import messagebox
from typing import Callable, Optional

from src.ui.ctk_config import ctk
from src.ui.widgets import CTkTableView

from src.db.domain_types import ClientRow, PasswordRow
from src.core.app import apply_rc_icon
from src.modules.passwords.controller import ClientPasswordsSummary, PasswordsController
from src.modules.passwords.utils import format_cnpj
from src.ui.window_utils import show_centered

log = logging.getLogger(__name__)
logger = log


class ClientPasswordsDialog(ctk.CTkToplevel):
    """Diálogo para gerenciar todas as senhas de um cliente específico (FIX-SENHAS-002).

    Permite visualizar, adicionar, editar, excluir e copiar senhas de um único cliente.
    """

    def __init__(
        self,
        parent,
        controller: PasswordsController,
        client_summary: ClientPasswordsSummary,
        org_id: str,
        user_id: str,
        clients: list[ClientRow],
        *,
        on_close_refresh: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(parent)

        # FIX-SENHAS-013: Esconder janela durante setup para evitar flash
        self.withdraw()

        # FIX-SENHAS-ÍCONES-LOCAL: Aplicar ícone da aplicação
        apply_rc_icon(self)

        self.title(f"Senhas – {client_summary.display_name}")
        self.minsize(800, 500)
        self.resizable(True, True)
        self.transient(parent)

        self.controller = controller
        self.client_summary = client_summary
        self.org_id = org_id
        self.user_id = user_id
        self.clients = clients
        self._on_close_refresh = on_close_refresh

        # Lista de senhas do cliente
        self.passwords: list[PasswordRow] = []
        self._sort_column: Optional[str] = None
        self._sort_order: str = "asc"

        self._build_ui()
        self._load_passwords()
        self._center_on_parent()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self) -> None:
        """Handler chamado quando a janela é fechada."""
        if self._on_close_refresh:
            self._on_close_refresh()
        self.destroy()

    def _center_on_parent(self) -> None:
        """Centraliza o diálogo usando helper compartilhado."""
        try:
            self.update_idletasks()
            show_centered(self)
            self.grab_set()
            self.focus_force()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao centralizar ClientPasswordsDialog: %s", exc)

    def _build_ui(self) -> None:
        """Constrói a interface do diálogo."""
        container = ctk.CTkFrame(self)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        # Cabeçalho com informações do cliente
        header_frame = ctk.CTkFrame(container)
        header_frame.pack(fill="x", pady=(0, 10))

        # FIX-SENHAS-011: Label único com CNPJ formatado
        formatted_cnpj = format_cnpj(self.client_summary.cnpj) if self.client_summary.cnpj else ""
        client_label = (
            f"Cliente: {self.client_summary.display_name} – {formatted_cnpj}"
            if formatted_cnpj
            else f"Cliente: {self.client_summary.display_name}"
        )

        ctk.CTkLabel(
            header_frame,
            text=client_label,
            font=("Arial", 11, "bold"),
        ).pack(side="left")

        # Tabela de senhas
        table_frame = ctk.CTkFrame(container)
        table_frame.pack(fill="both", expand=True)

        columns = ("servico", "usuario", "senha", "anotacoes")
        self.tree = CTkTableView(
            table_frame,
            columns=columns,
            show="headings",
            height=12,
            zebra=True,
        )  # TODO: selectmode="browse" -> handle in CTk way

        self.tree.heading("servico", text="Serviço", anchor="center", command=lambda: self._sort_by_column("servico"))
        self.tree.heading(
            "usuario", text="Usuário / Login", anchor="center", command=lambda: self._sort_by_column("usuario")
        )
        self.tree.heading("senha", text="Senha", anchor="center")
        self.tree.heading(
            "anotacoes", text="Anotações", anchor="center", command=lambda: self._sort_by_column("anotacoes")
        )

        # Centraliza também os dados das colunas
        self.tree.column("servico", width=160, anchor="center", stretch=False)
        self.tree.column("usuario", width=200, anchor="center", stretch=False)
        self.tree.column("senha", width=120, anchor="center", stretch=False)
        self.tree.column("anotacoes", width=260, anchor="center", stretch=True)

        self.tree.bind("<Double-1>", lambda e: self._on_edit_clicked())

        self.tree.pack(side="left", fill="both", expand=True)

        # Barra de ações
        actions_frame = ctk.CTkFrame(container)
        actions_frame.pack(fill="x", pady=(10, 0))

        ctk.CTkButton(
            actions_frame,
            text="Nova Senha",
            fg_color=("#2E7D32", "#1B5E20"),
            hover_color=("#1B5E20", "#0D4A11"),
            command=self._on_new_password_clicked,
            width=140,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            actions_frame,
            text="Editar",
            fg_color=("#757575", "#616161"),
            hover_color=("#616161", "#424242"),
            command=self._on_edit_clicked,
            width=140,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            actions_frame,
            text="Excluir",
            fg_color=("#D32F2F", "#B71C1C"),
            hover_color=("#B71C1C", "#8B0000"),
            command=self._on_delete_clicked,
            width=140,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            actions_frame,
            text="Copiar Senha",
            fg_color=("#0288D1", "#01579B"),
            hover_color=("#01579B", "#004C8C"),
            command=self._on_copy_password_clicked,
            width=140,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            actions_frame,
            text="Fechar",
            fg_color="transparent",
            border_width=2,
            border_color=("#757575", "#616161"),
            text_color=("#757575", "#FFFFFF"),
            hover_color=("#F5F5F5", "#424242"),
            command=self._on_close,
            width=100,
        ).pack(side="right", padx=5)

    def _load_passwords(self) -> None:
        """Carrega as senhas do cliente."""
        self.passwords = self.controller.get_passwords_for_client(self.client_summary.client_id)
        self._populate_table()

    def _populate_table(self) -> None:
        """Preenche a tabela com as senhas."""
        # Limpa a tabela
        self.tree.clear()

        for password in self.passwords:
            self.tree.insert(
                "",
                "end",
                values=[
                    password["service"],
                    password["username"],
                    "••••••",
                    password["notes"],
                ],
                tags=(str(password["id"]),),
            )

    def _sort_by_column(self, column: str) -> None:
        """Ordena a tabela pela coluna especificada."""
        if self._sort_column == column:
            self._sort_order = "desc" if self._sort_order == "asc" else "asc"
        else:
            self._sort_column = column
            self._sort_order = "asc"

        reverse = self._sort_order == "desc"
        if column == "servico":
            self.passwords.sort(key=lambda p: p["service"], reverse=reverse)
        elif column == "usuario":
            self.passwords.sort(key=lambda p: p["username"], reverse=reverse)
        elif column == "anotacoes":
            self.passwords.sort(key=lambda p: p["notes"], reverse=reverse)

        self._populate_table()

    def _get_selected_password(self) -> Optional[PasswordRow]:
        """Retorna a senha selecionada na tabela."""
        item_id = self.tree.get_selected_iid()
        if not item_id:
            return None

        password_id = self.tree.item(item_id, "tags")[0]
        return next((p for p in self.passwords if str(p["id"]) == password_id), None)

    def _on_new_password_clicked(self) -> None:
        """Handler do botão Nova Senha."""
        from src.modules.passwords.views.password_dialog import PasswordDialog

        PasswordDialog(
            self,
            self.org_id,
            self.user_id,
            self.clients,
            self._on_password_saved,
            controller=self.controller,
            client_id=self.client_summary.client_id,
            client_display=f"{self.client_summary.display_name} ({self.client_summary.cnpj})"
            if self.client_summary.cnpj
            else self.client_summary.display_name,
        )

    def _on_edit_clicked(self) -> None:
        """Handler do botão Editar."""
        from src.modules.passwords.views.password_dialog import PasswordDialog

        password = self._get_selected_password()
        if not password:
            messagebox.showwarning("Atenção", "Selecione uma senha para editar.", parent=self)
            return

        PasswordDialog(
            self,
            self.org_id,
            self.user_id,
            self.clients,
            self._on_password_saved,
            password,
            controller=self.controller,
            client_id=self.client_summary.client_id,
            client_display=f"{self.client_summary.display_name} ({self.client_summary.cnpj})"
            if self.client_summary.cnpj
            else self.client_summary.display_name,
        )

    def _on_delete_clicked(self) -> None:
        """Handler do botão Excluir."""
        password = self._get_selected_password()
        if not password:
            messagebox.showwarning("Atenção", "Selecione uma senha para excluir.", parent=self)
            return

        if not messagebox.askyesno(
            "Confirmação",
            f"Tem certeza que deseja excluir a senha do serviço '{password['service']}'?",
            parent=self,
        ):
            return

        try:
            self.controller.delete_password(password["id"])
            messagebox.showinfo("Sucesso", "Senha excluída com sucesso!", parent=self)
            self._load_passwords()
        except Exception as e:
            log.exception("Erro ao excluir senha")
            messagebox.showerror("Erro", f"Falha ao excluir: {e}", parent=self)

    def _on_copy_password_clicked(self) -> None:
        """Handler do botão Copiar Senha."""
        password = self._get_selected_password()
        if not password:
            messagebox.showwarning("Atenção", "Selecione uma senha para copiar.", parent=self)
            return

        try:
            plain_password = self.controller.decrypt_password(password["password_enc"])
            self.clipboard_clear()
            self.clipboard_append(plain_password)
            messagebox.showinfo("Sucesso", "Senha copiada para a área de transferência!", parent=self)
        except Exception as e:
            log.exception("Erro ao copiar senha")
            messagebox.showerror("Erro", f"Falha ao copiar: {e}", parent=self)

    def _on_password_saved(self) -> None:
        """Callback chamado quando uma senha é salva."""
        # Recarrega a lista de senhas
        self._load_passwords()

        # Atualiza o summary com as novas contagens
        self.client_summary = ClientPasswordsSummary(
            client_id=self.client_summary.client_id,
            client_external_id=self.client_summary.client_external_id,
            razao_social=self.client_summary.razao_social,
            cnpj=self.client_summary.cnpj,
            contato_nome=self.client_summary.contato_nome,
            whatsapp=self.client_summary.whatsapp,
            services=sorted(set(p["service"] for p in self.passwords)),
            passwords_count=len(self.passwords),
        )
