# -*- coding: utf-8 -*-
"""Diálogo de gerenciamento de arquivos do cliente - ClientesV2.

FASE 4: Placeholder CTk para arquivos, sem UI legacy.
"""

from __future__ import annotations

import logging
from typing import Any

from src.ui.ctk_config import ctk
from src.ui.ui_tokens import SURFACE, SURFACE_DARK, TEXT_PRIMARY, TEXT_MUTED, APP_BG

log = logging.getLogger(__name__)


class ClientFilesDialog(ctk.CTkToplevel):
    """Diálogo para gerenciar arquivos de um cliente.

    100% CustomTkinter (CTkToplevel).
    """

    def __init__(self, parent: Any, client_id: int, client_name: str = "Cliente", **kwargs: Any):
        """Inicializa o diálogo.

        Args:
            parent: Widget pai
            client_id: ID do cliente
            client_name: Nome do cliente para exibição
        """
        super().__init__(parent, **kwargs)

        self.client_id = client_id
        self.client_name = client_name

        # Configurar janela
        self.title(f"Arquivos - {client_name}")
        self.geometry("900x600")
        self.resizable(True, True)

        # Centralizar
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (900 // 2)
        y = (self.winfo_screenheight() // 2) - (600 // 2)
        self.geometry(f"+{x}+{y}")

        # Tornar modal
        self.transient(parent)
        self.grab_set()

        # Usar cores do Hub
        self.configure(fg_color=APP_BG)

        self._build_ui()

        log.info(f"[ClientFiles] Diálogo aberto para cliente ID={client_id}")

    def _build_ui(self) -> None:
        """Constrói a interface do diálogo."""
        # Container principal
        container = ctk.CTkFrame(self, fg_color=SURFACE_DARK, corner_radius=12)
        container.pack(fill="both", expand=True, padx=20, pady=20)

        # Cabeçalho
        header = ctk.CTkFrame(container, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkLabel(
            header, text=f"📁 Arquivos - {self.client_name}", font=("Segoe UI", 18, "bold"), text_color=TEXT_PRIMARY
        ).pack(side="left")

        ctk.CTkButton(
            header, text="✖ Fechar", command=self.destroy, width=100, fg_color="gray", hover_color="darkgray"
        ).pack(side="right")

        # Área central - Placeholder
        content = ctk.CTkFrame(container, fg_color=SURFACE, corner_radius=8)
        content.pack(fill="both", expand=True, padx=20, pady=10)

        # Mensagem de desenvolvimento
        ctk.CTkLabel(
            content,
            text="🚧 Gerenciador de Arquivos em Desenvolvimento",
            font=("Segoe UI", 16, "bold"),
            text_color=TEXT_PRIMARY,
        ).pack(pady=(40, 20))

        ctk.CTkLabel(
            content,
            text="Em breve você poderá:\n\n"
            "• Upload de arquivos para o cliente\n"
            "• Organização em subpastas\n"
            "• Visualização e download\n"
            "• Exclusão de arquivos\n\n"
            "Temporariamente, use o módulo Clientes legacy.",
            font=("Segoe UI", 12),
            text_color=TEXT_MUTED,
            justify="center",
        ).pack(pady=20)

        # Botão de ação alternativa
        ctk.CTkButton(
            content,
            text="🔙 Voltar",
            command=self.destroy,
            width=200,
            height=40,
            fg_color=("#2563eb", "#3b82f6"),
            hover_color=("#1d4ed8", "#2563eb"),
        ).pack(pady=(40, 20))

        # Bind Escape para fechar
        self.bind("<Escape>", lambda e: self.destroy())
