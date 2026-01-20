# -*- coding: utf-8 -*-
"""Diálogo para criação/edição de senha."""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import messagebox
from typing import Any, Callable, Optional

from src.ui.ctk_config import ctk

from src.db.domain_types import ClientRow, PasswordRow
from src.core.app import apply_rc_icon
from src.modules.passwords.controller import PasswordsController
from src.modules.passwords.passwords_actions import PasswordDialogActions, PasswordFormData
from src.modules.passwords.utils import format_cnpj
from src.ui.window_utils import show_centered

log = logging.getLogger(__name__)


class PasswordDialog(ctk.CTkToplevel):
    """Diálogo modal para criação/edição de senha."""

    def __init__(
        self,
        parent,
        org_id: str,
        user_id: str,
        clients: list[ClientRow],
        on_save: Callable[[], None],
        password_data: Optional[PasswordRow] = None,
        controller: Optional[PasswordsController] = None,
        on_select_client: Optional[Callable[[], None]] = None,
        *,
        client_id: Optional[str] = None,
        client_display: Optional[str] = None,
    ) -> None:
        super().__init__(parent)

        # FIX-SENHAS-013: Esconder janela durante setup para evitar flash
        self.withdraw()

        # FIX-SENHAS-ÍCONES-LOCAL: Aplicar ícone da aplicação
        apply_rc_icon(self)

        self.title("Nova Senha" if password_data is None else "Editar Senha")
        self.minsize(500, 400)
        self.resizable(False, False)
        self.transient(parent)

        self.org_id = org_id
        self.user_id = user_id
        self.clients = clients
        self.on_save = on_save
        self.password_data = password_data
        self.is_editing = password_data is not None
        self.controller = controller or PasswordsController()
        self._on_select_client = on_select_client
        self.actions = PasswordDialogActions(controller=self.controller)

        # FIX-SENHAS-002: Cliente pré-selecionado (trava o botão Selecionar)
        self._client_locked = client_id is not None

        # Cliente selecionado
        self.selected_client_id: Optional[str] = client_id
        self.selected_client_display: str = client_display or ""

        self._build_ui()

        # FIX-SENHAS-002: Se cliente veio pré-definido, preencher e travar
        if self._client_locked and self.selected_client_id:
            self.client_display_var.set(self.selected_client_display)
            self.select_client_button.configure(state="disabled")

        if self.is_editing:
            self._load_data()

        self._center_on_parent()

        # Configurar handler de fechamento (FIX-CLIENTES-005: sem cancelamento de pick)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self) -> None:
        """Handler chamado quando a janela é fechada (X ou Escape)."""
        self.destroy()

    def _center_on_parent(self) -> None:
        """Centraliza o diálogo usando helper compartilhado."""
        try:
            self.update_idletasks()
            show_centered(self)
            self.grab_set()
            self.focus_force()
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao centralizar PasswordDialog: %s", exc)

    def _build_ui(self) -> None:
        """Constrói a interface do diálogo."""
        container = ctk.CTkFrame(self)
        container.pack(fill="both", expand=True, padx=20, pady=20)

        # Cliente
        ctk.CTkLabel(container, text="Cliente:").grid(row=0, column=0, sticky="w", pady=5)
        client_frame = ctk.CTkFrame(container)
        client_frame.grid(row=0, column=1, sticky="ew", pady=5, padx=(10, 0))

        self.client_display_var = tk.StringVar()
        self.client_display_entry = ctk.CTkEntry(
            client_frame,
            textvariable=self.client_display_var,
            state="readonly",
            width=300,
        )
        self.client_display_entry.pack(side="left", fill="x", expand=True)

        self.select_client_button = ctk.CTkButton(
            client_frame,
            text="Selecionar...",
            fg_color=("#757575", "#616161"),
            hover_color=("#616161", "#424242"),
            command=self._on_select_client_clicked,
            width=100,
        )
        self.select_client_button.pack(side="right", padx=(5, 0))

        # Serviço
        ctk.CTkLabel(container, text="Serviço:").grid(row=1, column=0, sticky="w", pady=5)
        self.service_var = tk.StringVar()
        self.service_combo = ctk.CTkComboBox(
            container,
            variable=self.service_var,
            values=["SIFAP", "CRF", "GOV.BR", "E-mail", "Banco", "Outro"],
        )
        self.service_combo.grid(row=1, column=1, sticky="ew", pady=5, padx=(10, 0))

        # Usuário/Login
        ctk.CTkLabel(container, text="Usuário / Login:").grid(row=2, column=0, sticky="w", pady=5)
        self.username_var = tk.StringVar()
        self.username_entry = ctk.CTkEntry(container, textvariable=self.username_var)
        self.username_entry.grid(row=2, column=1, sticky="ew", pady=5, padx=(10, 0))

        # Senha
        ctk.CTkLabel(container, text="Senha:").grid(row=3, column=0, sticky="w", pady=5)
        self.password_var = tk.StringVar()
        self.password_entry = ctk.CTkEntry(container, textvariable=self.password_var, show="*")
        self.password_entry.grid(row=3, column=1, sticky="ew", pady=5, padx=(10, 0))

        # Anotações
        ctk.CTkLabel(container, text="Anotações:").grid(row=4, column=0, sticky="w", pady=5)
        self.notes_var = tk.StringVar()
        self.notes_entry = ctk.CTkEntry(container, textvariable=self.notes_var)
        self.notes_entry.grid(row=4, column=1, sticky="ew", pady=5, padx=(10, 0))

        # Botões
        btn_frame = ctk.CTkFrame(container)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=20)

        ctk.CTkButton(btn_frame, text="Salvar", fg_color=("#2E7D32", "#1B5E20"), hover_color=("#1B5E20", "#0D4A11"), command=self._save).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Cancelar", fg_color=("#757575", "#616161"), hover_color=("#616161", "#424242"), command=self.destroy).pack(side="left", padx=5)

        container.columnconfigure(1, weight=1)

    def _on_select_client_clicked(self) -> None:
        """Chama o callback do PasswordsScreen para iniciar seleção."""
        if self._on_select_client:
            self._on_select_client()
        else:
            # Fallback para comportamento legado (não deve acontecer)
            messagebox.showerror("Erro", "Seleção de cliente não configurada.", parent=self)

    def set_client_from_data(self, client_data: dict) -> None:
        """Preenche o campo de cliente com os dados fornecidos.

        Args:
            client_data: Dicionário com 'id', 'razao_social' e opcionalmente 'cnpj'
        """
        try:
            self.selected_client_id = str(client_data["id"])
            razao = client_data.get("razao_social", "").strip()
            cnpj = client_data.get("cnpj", "").strip()

            # FIX-SENHAS-014: Formato padronizado "ID 256 – RAZAO SOCIAL – 05.788.603/0001-13"
            if razao and cnpj:
                formatted_cnpj = format_cnpj(cnpj)
                self.selected_client_display = f"ID {self.selected_client_id} – {razao} – {formatted_cnpj}"
            elif razao:
                self.selected_client_display = f"ID {self.selected_client_id} – {razao}"
            else:
                self.selected_client_display = f"ID {self.selected_client_id}"

            self.client_display_var.set(self.selected_client_display)

            # FEATURE-SENHAS-002: Desabilitar botão Selecionar quando cliente já foi escolhido via pick mode
            if hasattr(self, "select_client_button"):
                self.select_client_button.configure(state="disabled")

            log.info("Senhas: cliente ID %s selecionado", self.selected_client_id)
        except Exception as e:
            log.exception("Erro ao processar cliente selecionado")
            messagebox.showerror("Erro", f"Falha ao processar cliente: {e}", parent=self)

    def is_visible(self) -> bool:
        """Retorna True se a janela está visível."""
        try:
            return self.winfo_exists() and self.winfo_viewable()
        except Exception:
            return False

    def _handle_client_selected(self, client_data: dict) -> None:
        """Callback chamado quando cliente é selecionado no modo pick (DEPRECIADO - use set_client_from_data)."""
        self.set_client_from_data(client_data)

    def _get_main_app(self) -> Optional[Any]:
        """Obtém referência ao app principal navegando pela hierarquia."""
        widget = self.master
        while widget:
            if hasattr(widget, "show_frame") and hasattr(widget, "_main_frame_ref"):
                return widget
            widget = getattr(widget, "master", None)
        return None

    def _load_data(self) -> None:
        """Carrega dados para edição."""
        if not self.password_data:
            return
        # Carregar client_id se existir
        if "client_id" in self.password_data and self.password_data["client_id"]:
            self.selected_client_id = str(self.password_data["client_id"])

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

        form_data = PasswordFormData(
            client_id=self.selected_client_id or "",
            client_name=client_name,
            service=service,
            username=username,
            password=password,
            notes=notes,
            is_editing=self.is_editing,
            password_id=str(self.password_data["id"]) if self.password_data else None,
        )
        errors = self.actions.validate_form(form_data)
        if errors:
            messagebox.showerror("Erro", "\n".join(errors), parent=self)
            return

        if not self.org_id or not self.user_id:
            messagebox.showerror("Erro", "Usuário ou organização não identificados.", parent=self)
            return

        try:
            if not self.is_editing:
                duplicates = self.actions.find_duplicates(self.org_id, form_data.client_id, form_data.service)
                if duplicates:
                    decision = self._ask_duplicate_service_decision(duplicates)
                    if decision == "cancel":
                        return
                    if decision == "edit":
                        self._open_existing_password_for_edit(duplicates[0])
                        return

            if self.is_editing:
                self.actions.update_password(form_data)
                success_message = "Senha atualizada com sucesso!"
            else:
                self.actions.create_password(self.org_id, self.user_id, form_data)
                success_message = "Senha criada com sucesso!"

            messagebox.showinfo("Sucesso", success_message, parent=self)
            self.on_save()
            self.destroy()
        except Exception as e:
            log.exception("Erro ao salvar senha")
            messagebox.showerror("Erro", f"Falha ao salvar: {e}", parent=self)

    def _ask_duplicate_service_decision(
        self,
        duplicates: list[PasswordRow],
    ) -> str:
        """
        Mostra diálogo avisando que já existe senha para este
        Cliente + Serviço. Retorna:
        - "edit"   -> abrir edição da existente
        - "force"  -> criar mesmo assim
        - "cancel" -> não faz nada
        """
        msg = (
            "Já existe uma senha cadastrada para este Cliente + Serviço.\n\n"
            "Sim = criar outra mesmo assim.\n"
            "Não = ver/editar a senha já cadastrada.\n"
            "Cancelar = não fazer nada."
        )
        result = messagebox.askyesnocancel("Senha duplicada", msg, parent=self)
        if result is None:
            return "cancel"
        if result is True:
            return "force"
        return "edit"

    def _open_existing_password_for_edit(self, duplicate: PasswordRow) -> None:
        """Abre a senha existente para edição."""
        # Fecha o diálogo atual
        self.destroy()

        # Abre diálogo de edição com a senha existente
        # Obtém referência ao parent (PasswordsScreen) para abrir o novo diálogo
        parent = self.master
        if parent and hasattr(parent, "_open_edit_password_dialog"):
            parent._open_edit_password_dialog(duplicate)
        else:
            log.warning("Não foi possível abrir diálogo de edição para senha duplicada")
