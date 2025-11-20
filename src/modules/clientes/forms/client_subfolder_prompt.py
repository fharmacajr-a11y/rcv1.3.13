# -*- coding: utf-8 -*-
"""
Dialogo simples para definir subpastas de clientes.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional

from src.ui.utils import center_on_parent
from src.utils.resource_path import resource_path

try:
    from src.utils.validators import sanitize_key_component as _sanitize_key_component
except Exception:  # pragma: no cover

    def _sanitize_key_component(s: str | None) -> str:
        import re

        return re.sub(r"[^\w\-]+", "", str(s or "").strip())


DEFAULT_IMPORT_SUBFOLDER = "GERAL"


class SubpastaDialog(tk.Toplevel):
    """Dialogo que coleta o nome da subpasta (ex.: usada em uploads de clientes)."""

    def __init__(self, parent: tk.Misc, default: str = ""):
        super().__init__(parent)
        self.withdraw()
        self.title("Subpasta em GERAL")
        self.transient(parent)
        self.resizable(False, False)
        try:
            self.iconbitmap(resource_path("rc.ico"))
        except Exception:
            pass

        frm = ttk.Frame(self, padding=12)
        frm.pack(fill="both", expand=True)

        ttk.Label(
            frm,
            text=f"Digite o nome da subpasta (ou deixe vazio para usar só '{DEFAULT_IMPORT_SUBFOLDER}/').",
        ).pack(anchor="w", pady=(0, 8))
        ttk.Label(
            frm,
            text="Ex.: SIFAP, VISA, Farmacia_Popular, Auditoria",
            foreground="#6c757d",
        ).pack(anchor="w")

        self.var = tk.StringVar(value=default or "")
        ent = ttk.Entry(frm, textvariable=self.var, width=40)
        ent.pack(fill="x", pady=(8, 10))
        btns = ttk.Frame(frm)
        btns.pack(fill="x")
        ttk.Button(btns, text="OK", command=self._ok).pack(side="left", padx=4)
        ttk.Button(btns, text="Cancelar", command=self._cancel).pack(side="left", padx=4)

        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self._cancel())
        _attach_close_handler(self)

        try:
            self.update_idletasks()
            center_on_parent(self, parent)
        except Exception:
            pass

        self.deiconify()
        self.grab_set()
        ent.focus_force()

        self.result: Optional[str] = None
        self.cancelled: bool = False

    def _ok(self):
        raw = (self.var.get() or "").strip()
        self.result = _sanitize_key_component(raw) if raw else ""
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
        except Exception:
            return None


def _attach_close_handler(dlg: SubpastaDialog) -> None:
    try:
        dlg.protocol("WM_DELETE_WINDOW", dlg._on_close)
    except Exception:
        try:
            dlg.protocol("WM_DELETE_WINDOW", lambda: dlg._on_close())
        except Exception:
            pass


def _ask_subpasta_nome(parent: tk.Misc, default: str = "") -> Optional[str]:
    dlg = SubpastaDialog(parent, default=default)
    parent.wait_window(dlg)
    return dlg.result
