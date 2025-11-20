"""Componente de diálogo de progresso reutilizável."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from src.ui.utils import center_on_parent
from src.utils.resource_path import resource_path


class BusyDialog(tk.Toplevel):
    """Progress dialog. Suporta modo indeterminado e determinado (com %)."""

    def __init__(self, parent: tk.Misc, text: str = "Processando…"):
        super().__init__(parent)
        self.withdraw()
        self.title("Aguarde…")
        self.resizable(False, False)
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", lambda: None)  # não fecha
        try:
            self.iconbitmap(resource_path("rc.ico"))
        except Exception:
            pass

        body = ttk.Frame(self, padding=12)
        body.pack(fill="both", expand=True)

        self._lbl = ttk.Label(body, text=text, anchor="center", justify="center")
        self._lbl.pack(pady=(0, 8), fill="x")

        self._pb = ttk.Progressbar(body, mode="indeterminate", length=280, maximum=100)
        self._pb.pack(fill="x")

        # centraliza sobre o parent
        try:
            self.update_idletasks()
            center_on_parent(self, parent)
        except Exception:
            pass

        self.deiconify()
        self._pb.start(12)
        self.lift()
        try:
            self.attributes("-topmost", True)
            self.after(50, lambda: self.attributes("-topmost", False))
        except Exception:
            pass
        self.update()

        # estado para modo determinado
        self._det_total = None
        self._det_value = 0

    def set_text(self, txt: str) -> None:
        try:
            self._lbl.configure(text=txt)
            self.update_idletasks()
        except Exception:
            pass

    def set_total(self, total: int) -> None:
        """Troca para modo determinado com 'total' passos."""
        try:
            self._det_total = max(int(total), 1)
            self._det_value = 0
            self._pb.stop()
            self._pb.configure(mode="determinate", maximum=self._det_total, value=0)
            self.update_idletasks()
        except Exception:
            pass

    def step(self, inc: int = 1) -> None:
        try:
            if self._det_total:
                self._det_value = min(self._det_total, self._det_value + inc)
                self._pb.configure(value=self._det_value)
            self.update_idletasks()
        except Exception:
            pass

    def close(self) -> None:
        try:
            self._pb.stop()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass
