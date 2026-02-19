# -*- coding: utf-8 -*-
"""Diálogo para criação de nova tarefa - MIGRADO PARA CUSTOMTKINTER."""

from __future__ import annotations

import logging
import tkinter as tk
from datetime import date
from tkinter import messagebox
from tkinter.constants import W
from typing import Callable, Optional

from src.ui.ctk_config import ctk  # SSoT: import via ctk_config
from src.ui.widgets.button_factory import make_btn
from src.db.domain_types import ClientRow
from src.core.app import apply_rc_icon
from src.features.tasks.service import create_task
from src.ui.window_utils import show_centered

logger = logging.getLogger(__name__)


# Mapeamento de labels para valores de prioridade
PRIORITY_OPTIONS = {
    "Baixa": "low",
    "Normal": "normal",
    "Alta": "high",
    "Urgente": "urgent",
}


class NovaTarefaDialog(ctk.CTkToplevel):
    """Diálogo modal para criação de nova tarefa - CustomTkinter."""

    def __init__(
        self,
        parent: tk.Widget,
        org_id: str,
        user_id: str,
        on_success: Callable[[], None],
        clients: Optional[list[ClientRow]] = None,
    ) -> None:
        """Inicializa o diálogo de nova tarefa.

        Args:
            parent: Widget pai
            org_id: UUID da organização
            user_id: UUID do usuário criador
            on_success: Callback chamado após criação bem-sucedida
            clients: Lista opcional de clientes para o combobox
        """
        super().__init__(parent)

        # Esconder janela durante setup
        self.withdraw()

        # Aplicar ícone da aplicação
        apply_rc_icon(self)

        self.title("Nova Tarefa")
        self.minsize(550, 450)
        self.resizable(False, False)
        self.transient(parent)

        self.org_id = org_id
        self.user_id = user_id
        self.on_success = on_success
        self.clients = clients or []

        self._build_ui()
        self._center_on_parent()

        # Configurar handler de fechamento
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
            logger.debug("Falha ao centralizar NovaTarefaDialog: %s", exc)

    def _build_ui(self) -> None:
        """Constrói a interface do diálogo."""
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=20)

        # Configurar grid para expansão
        container.columnconfigure(1, weight=1)

        # Cliente (opcional)
        ctk.CTkLabel(container, text="Cliente (opcional):").grid(row=0, column=0, sticky=W, pady=5)
        self.client_var = tk.StringVar()

        # Preparar lista de clientes para o combobox
        client_values = ["(Nenhum)"]
        self._client_map: dict[str, str] = {}  # display -> client_id

        if self.clients:
            for client in self.clients:
                # Formatar display: "Razão Social - CNPJ"
                razao = client.get("razao_social", "")
                cnpj = client.get("cnpj", "")
                display = f"{razao} - {cnpj}" if cnpj else razao
                client_values.append(display)
                self._client_map[display] = client.get("id", "")

        self.client_combo = ctk.CTkComboBox(
            container,
            variable=self.client_var,
            values=client_values,
            state="readonly",
        )
        self.client_combo.set("(Nenhum)")  # Default
        self.client_combo.grid(row=0, column=1, sticky="ew", pady=5, padx=(10, 0))

        # Título (obrigatório)
        ctk.CTkLabel(container, text="Título*:").grid(row=1, column=0, sticky=W, pady=5)
        self.title_var = tk.StringVar()
        self.title_entry = ctk.CTkEntry(container, textvariable=self.title_var)
        self.title_entry.grid(row=1, column=1, sticky="ew", pady=5, padx=(10, 0))

        # Descrição (opcional)
        ctk.CTkLabel(container, text="Descrição:").grid(row=2, column=0, sticky=W + "n", pady=5)
        self.description_text = ctk.CTkTextbox(
            container,
            height=100,
            width=400,
            wrap="word",
        )
        self.description_text.grid(row=2, column=1, sticky="ew", pady=5, padx=(10, 0))

        # Prioridade
        ctk.CTkLabel(container, text="Prioridade:").grid(row=3, column=0, sticky=W, pady=5)
        self.priority_var = tk.StringVar()
        self.priority_combo = ctk.CTkComboBox(
            container,
            variable=self.priority_var,
            values=list(PRIORITY_OPTIONS.keys()),
            state="readonly",
        )
        self.priority_combo.set("Normal")  # Default
        self.priority_combo.grid(row=3, column=1, sticky="ew", pady=5, padx=(10, 0))

        # Data de vencimento
        ctk.CTkLabel(container, text="Vencimento:").grid(row=4, column=0, sticky=W, pady=5)

        # Frame para data
        date_frame = ctk.CTkFrame(container, fg_color="transparent")
        date_frame.grid(row=4, column=1, sticky="ew", pady=5, padx=(10, 0))

        # Entry simples para data (DateEntry não é compatível com CTk)
        self.date_var = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
        self.date_entry = ctk.CTkEntry(date_frame, textvariable=self.date_var, width=150)
        self.date_entry.pack(side="left")
        ctk.CTkLabel(
            date_frame,
            text="(formato: AAAA-MM-DD)",
            text_color="gray",
        ).pack(side="left", padx=(5, 0))

        # Hint para campos obrigatórios
        hint_label = ctk.CTkLabel(
            container,
            text="* Campos obrigatórios",
            text_color="gray",
        )
        hint_label.grid(row=5, column=0, columnspan=2, sticky=W, pady=(10, 5))

        # Botões
        button_frame = ctk.CTkFrame(container, fg_color="transparent")
        button_frame.grid(row=6, column=0, columnspan=2, pady=(15, 0))

        self.ok_button = make_btn(
            button_frame,
            text="Criar Tarefa",
            command=self._on_ok,
            fg_color="green",
            hover_color="darkgreen",
        )
        self.ok_button.pack(side="left", padx=5)

        self.cancel_button = make_btn(
            button_frame,
            text="Cancelar",
            command=self._on_close,
            fg_color="gray",
            hover_color="darkgray",
        )
        self.cancel_button.pack(side="left", padx=5)

        # Bind Enter/Escape
        self.bind("<Return>", lambda e: self._on_ok())
        self.bind("<Escape>", lambda e: self._on_close())

        # Foco inicial no título
        self.title_entry.focus_force()

    def _on_ok(self) -> None:
        """Handler do botão OK - valida e cria a tarefa."""
        # Validar título
        title = self.title_var.get().strip()
        if not title:
            messagebox.showerror(
                "Campo obrigatório",
                "Por favor, preencha o título da tarefa.",
                parent=self,
            )
            self.title_entry.focus_force()
            return

        # Pegar outros valores
        description = self.description_text.get("1.0", "end-1c").strip() or None

        priority_label = self.priority_var.get()
        priority = PRIORITY_OPTIONS.get(priority_label, "normal")

        # Parsear data
        date_str = self.date_var.get().strip()
        try:
            due_date = date.fromisoformat(date_str)
        except ValueError:
            messagebox.showerror(
                "Data inválida",
                f"Data inválida: '{date_str}'. Use o formato AAAA-MM-DD.",
                parent=self,
            )
            self.date_entry.focus_force()
            return

        # Determinar client_id
        client_display = self.client_var.get()
        client_id: int | None = None
        if client_display and client_display != "(Nenhum)":
            client_id_str = self._client_map.get(client_display)
            if client_id_str:
                try:
                    # Converter UUID para int se necessário, ou manter como string
                    # Baseado no schema, client_id é int
                    client_id = int(client_id_str) if client_id_str.isdigit() else None
                except (ValueError, AttributeError):
                    logger.warning("client_id inválido: %s", client_id_str)

        # Criar tarefa
        try:
            created_task = create_task(
                org_id=self.org_id,
                created_by=self.user_id,
                title=title,
                description=description,
                priority=priority,
                due_date=due_date,
                client_id=client_id,
            )

            logger.info("Tarefa criada: %s", created_task.get("id"))

            # Chamar callback de sucesso
            self.on_success()

            # Fechar diálogo
            self.destroy()

        except Exception as exc:
            logger.exception("Erro ao criar tarefa")
            messagebox.showerror(
                "Erro",
                f"Erro ao criar tarefa: {exc}",
                parent=self,
            )
