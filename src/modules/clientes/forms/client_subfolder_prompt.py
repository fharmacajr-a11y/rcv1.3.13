# -*- coding: utf-8 -*-
"""
Dialogo simples para definir subpastas de clientes.
"""

from __future__ import annotations

import logging
import tkinter as tk
from typing import Optional

from src.ui.ctk_config import ctk

from src.utils.subfolders import sanitize_subfolder_name
from src.ui.window_utils import show_centered
from src.utils.resource_path import resource_path

logger = logging.getLogger(__name__)


DEFAULT_IMPORT_SUBFOLDER = "GERAL"


class SubpastaDialog(tk.Toplevel):
    """Dialogo que coleta o nome da subpasta (ex.: usada em uploads de clientes)."""

    DIALOG_MIN_WIDTH = 520
    WRAP_LEN = 520

    def __init__(self, parent: tk.Misc, default: str = ""):
        super().__init__(parent)
        self.withdraw()
        self.title("Subpasta em GERAL")
        self.transient(parent)
        self.resizable(False, False)
        try:
            self.iconbitmap(resource_path("rc.ico"))
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao aplicar iconbitmap no SubpastaDialog: %s", exc)

        # Grid layout compacto
        self.rowconfigure(0, weight=0)
        self.columnconfigure(0, weight=1)

        frm = tk.Frame(self)
        frm.grid(row=0, column=0, sticky="nsew", padx=16, pady=(12, 10))
        frm.columnconfigure(0, weight=1)

        # Labels com wraplength para evitar texto feio
        ctk.CTkLabel(
            frm,
            text=f"Digite o nome da subpasta (ou deixe vazio para usar só '{DEFAULT_IMPORT_SUBFOLDER}/').",
            wraplength=520,
            justify="left",
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        ctk.CTkLabel(
            frm,
            text="Ex.: SIFAP, VISA, Farmacia_Popular, Auditoria",
            foreground="#6c757d",
            wraplength=520,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(0, 6))

        self.var = tk.StringVar(value=default or "")
        ent = ctk.CTkEntry(frm, textvariable=self.var, width=40)
        ent.grid(row=2, column=0, sticky="ew", pady=(6, 8))

        # Botões no canto direito com padding mínimo
        btns = tk.Frame(frm)
        btns.grid(row=3, column=0, sticky="e", pady=(0, 0))
        tk.Button(btns, text="OK", command=self._ok).pack(side="left", padx=4)
        tk.Button(btns, text="Cancelar", command=self._cancel).pack(side="left", padx=4)

        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self._cancel())
        _attach_close_handler(self)

        # Forçar largura mínima e centralizar
        try:
            self.update_idletasks()
            req_h = self.winfo_reqheight()
            self.minsize(self.DIALOG_MIN_WIDTH, req_h)
            show_centered(self)

            # Reaplicar geometry mantendo posição para garantir largura
            self.update_idletasks()
            x, y = self.winfo_x(), self.winfo_y()
            w = max(self.DIALOG_MIN_WIDTH, self.winfo_reqwidth())
            h = self.winfo_reqheight()
            self.geometry(f"{w}x{h}+{x}+{y}")
            self.minsize(w, h)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao centralizar SubpastaDialog: %s", exc)
        self.grab_set()
        ent.focus_force()

        self.result: Optional[str] = None
        self.cancelled: bool = False

    def _ok(self):
        raw = (self.var.get() or "").strip()
        self.result = sanitize_subfolder_name(raw) if raw else ""
        self.cancelled = False
        self.destroy()

    def _cancel(self):
        self.result = None
        self.cancelled = True
        self.destroy()

    def _on_close(self):
        self.result = None
        self.cancelled = True
        self.destroy()

    def protocol(self, name=None, func=None):
        try:
            return super().protocol(name, func)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao registrar protocolo no SubpastaDialog: %s", exc)
            return None


def _attach_close_handler(dlg: SubpastaDialog) -> None:
    try:
        dlg.protocol("WM_DELETE_WINDOW", dlg._on_close)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Falha ao atribuir handler direto de fechamento: %s", exc)
        try:
            dlg.protocol("WM_DELETE_WINDOW", lambda: dlg._on_close())
        except Exception as inner_exc:  # noqa: BLE001
            logger.debug("Falha ao atribuir handler alternativo de fechamento: %s", inner_exc)


def _ask_subpasta_nome(parent: tk.Misc, default: str = "") -> Optional[str]:
    dlg = SubpastaDialog(parent, default=default)
    parent.wait_window(dlg)
    return dlg.result
