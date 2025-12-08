# -*- coding: utf-8 -*-
"""
Diálogo mínimo de subpastas para listar objetos do Storage.
Backup caso src.ui.subpastas.dialog não esteja disponível.
"""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Optional

from src.shared.subfolders import sanitize_subfolder_name
from src.ui.window_utils import show_centered

logger = logging.getLogger(__name__)


class SubpastaDialog(tk.Toplevel):
    """
    Diálogo mínimo que lista objetos de um prefixo do Storage usando Treeview.

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

        # Frame principal
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill="both", expand=True)

        # Label de instrução
        ttk.Label(
            main_frame,
            text="Digite o nome da subpasta ou selecione uma existente:",
        ).pack(anchor="w", pady=(0, 5))

        # Entry para nome da subpasta
        entry_frame = ttk.Frame(main_frame)
        entry_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(entry_frame, text="Subpasta:").pack(side="left", padx=(0, 5))
        self.var = tk.StringVar(value=default or "")
        self.entry = ttk.Entry(entry_frame, textvariable=self.var)
        self.entry.pack(side="left", fill="x", expand=True)

        # Frame para Treeview (lista de subpastas existentes)
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill="both", expand=True, pady=(0, 10))

        ttk.Label(tree_frame, text="Subpastas existentes (clique duplo para selecionar):").pack(anchor="w", pady=(0, 5))

        # Scrollbar e Treeview
        tree_scroll = ttk.Scrollbar(tree_frame)
        tree_scroll.pack(side="right", fill="y")

        self.tree = ttk.Treeview(
            tree_frame,
            columns=("nome",),
            show="tree",
            yscrollcommand=tree_scroll.set,
        )
        self.tree.pack(side="left", fill="both", expand=True)
        tree_scroll.config(command=self.tree.yview)

        self.tree.bind("<Double-Button-1>", self._on_tree_double_click)

        # Botões
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x")

        ttk.Button(btn_frame, text="OK", command=self._ok).pack(side="left", padx=(0, 5))
        ttk.Button(btn_frame, text="Cancelar", command=self._cancel).pack(side="left", padx=(0, 5))
        ttk.Button(btn_frame, text="Atualizar Lista", command=self._load_subpastas).pack(side="left")

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
            from adapters.storage.api import list_files, using_storage_backend
            from adapters.storage.supabase_storage import SupabaseStorageAdapter

            # Limpa tree
            for item in self.tree.get_children():
                self.tree.delete(item)

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

            # Adiciona ao tree
            for subpasta in sorted(subpastas):
                self.tree.insert("", "end", text=subpasta, values=(subpasta,))

            logger.info("Carregadas %d subpastas do prefixo %s", len(subpastas), self.prefix)

        except Exception as exc:
            logger.exception("Erro ao listar subpastas do Storage: %s", exc)
            messagebox.showerror(
                "Erro",
                f"Não foi possível listar subpastas:\n{exc}",
                parent=self,
            )

    def _on_tree_double_click(self, event):
        """Seleciona a subpasta clicada."""
        selection = self.tree.selection()
        if selection:
            item = selection[0]
            nome = self.tree.item(item, "text")
            self.var.set(nome)
            self._ok()

    def _ok(self):
        raw = (self.var.get() or "").strip()
        # Usa sanitização centralizada
        self.result = sanitize_subfolder_name(raw) if raw else ""
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()
