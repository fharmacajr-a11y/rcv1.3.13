# -*- coding: utf-8 -*-
"""
Diálogo mínimo de subpastas para listar objetos do Storage.
Backup caso src.ui.subpastas.dialog não esteja disponível.
"""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import messagebox
from typing import Optional

from src.ui.ctk_config import ctk
from src.utils.subfolders import sanitize_subfolder_name
from src.ui.window_utils import show_centered

logger = logging.getLogger(__name__)


class SubpastaDialog(ctk.CTkToplevel):
    """
    Diálogo mínimo que lista objetos de um prefixo do Storage.

    Permite ao usuário escolher uma subpasta ou criar uma nova.
    """

    def __init__(
        self,
        parent: tk.Misc,
        default: str = "",
        prefix: str = "",
        bucket: str = "rc-docs",
    ):
        super().__init__(parent)
        self.withdraw()
        self.title("Escolher Subpasta")
        self.transient(parent)
        self.resizable(True, True)
        self.minsize(600, 400)

        self.result: Optional[str] = None
        self.prefix = prefix
        self.bucket = bucket
        self._buttons: dict[str, ctk.CTkButton] = {}

        # Frame principal
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Label de instrução
        ctk.CTkLabel(
            main_frame,
            text="Digite o nome da subpasta ou selecione uma existente:",
        ).pack(anchor="w", pady=(0, 5))

        # Entry para nome da subpasta
        entry_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        entry_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(entry_frame, text="Subpasta:").pack(side="left", padx=(0, 5))
        self.var = tk.StringVar(value=default or "")
        self.entry = ctk.CTkEntry(entry_frame, textvariable=self.var)
        self.entry.pack(side="left", fill="x", expand=True)

        # Frame para lista de subpastas existentes
        list_frame = ctk.CTkFrame(main_frame)
        list_frame.pack(fill="both", expand=True, pady=(0, 10))

        ctk.CTkLabel(list_frame, text="Subpastas existentes (clique para selecionar):").pack(anchor="w", pady=(0, 5))

        # ScrollableFrame para lista de botões
        self.scroll_frame = ctk.CTkScrollableFrame(list_frame, height=200)
        self.scroll_frame.pack(fill="both", expand=True)

        # Botões
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(fill="x")

        ctk.CTkButton(btn_frame, text="OK", command=self._ok, width=80).pack(side="left", padx=(0, 5))
        ctk.CTkButton(btn_frame, text="Cancelar", command=self._cancel, width=100).pack(side="left", padx=(0, 5))
        ctk.CTkButton(btn_frame, text="Atualizar Lista", command=self._load_subpastas, width=120).pack(side="left")

        # Bindings
        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self._cancel())

        self.update_idletasks()
        show_centered(self)

        # Carrega subpastas se prefix foi fornecido
        if prefix:
            self._load_subpastas()

        self.grab_set()
        self.entry.focus_force()

    def _load_subpastas(self):
        """Carrega subpastas do Storage via adapter."""
        if not self.prefix:
            return

        try:
            from src.adapters.storage.api import list_files, using_storage_backend
            from src.adapters.storage.supabase_storage import SupabaseStorageAdapter

            adapter = SupabaseStorageAdapter(bucket=self.bucket)

            with using_storage_backend(adapter):
                objects = list(list_files(self.prefix))

            # Extrai nomes únicos de subpastas
            subpastas = set()
            for obj in objects:
                if isinstance(obj, dict):
                    full_path = obj.get("full_path", "")
                    # Remove o prefixo e pega o primeiro segmento
                    rel = full_path.replace(self.prefix, "").strip("/")
                    if "/" in rel:
                        subpasta = rel.split("/")[0]
                        subpastas.add(subpasta)

            # Limpa botões antigos
            for btn in self._buttons.values():
                btn.destroy()
            self._buttons.clear()

            # Adiciona botões para cada subpasta
            for subpasta in sorted(subpastas):
                btn = ctk.CTkButton(
                    self.scroll_frame,
                    text=subpasta,
                    command=lambda s=subpasta: self._select_subpasta(s),
                    anchor="w",
                )
                btn.pack(fill="x", padx=5, pady=2)
                self._buttons[subpasta] = btn

            logger.info("Carregadas %d subpastas do prefixo %s", len(subpastas), self.prefix)

        except Exception as exc:
            logger.exception("Erro ao listar subpastas do Storage: %s", exc)
            messagebox.showerror(
                "Erro",
                f"Não foi possível listar subpastas:\n{exc}",
                parent=self,
            )

    def _select_subpasta(self, subpasta: str):
        """Seleciona subpasta ao clicar no botão."""
        if subpasta:
            self.var.set(subpasta)
            self.entry.focus_set()

    def _ok(self):
        raw = (self.var.get() or "").strip()
        # Usa sanitização centralizada
        self.result = sanitize_subfolder_name(raw) if raw else ""
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()
