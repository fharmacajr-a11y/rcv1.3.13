# -*- coding: utf-8 -*-
"""
Dialogo CTkToplevel para definir subpastas de clientes.
"""

from __future__ import annotations

import logging
import tkinter as tk
from typing import Optional

from src.ui.ctk_config import ctk
from src.ui.ui_tokens import (
    APP_BG,
    BTN_SECONDARY,
    BTN_SECONDARY_HOVER,
    DIALOG_BTN_H,
    DIALOG_BTN_W,
    BUTTON_RADIUS,
    SURFACE,
    PRIMARY_BLUE,
    PRIMARY_BLUE_HOVER,
    TEXT_MUTED,
    DIALOG_RADIUS,
    INPUT_RADIUS,
    FONT_SECTION,
    FONT_BODY_SM,
)
from src.utils.subfolders import sanitize_subfolder_name
from src.ui.window_utils import apply_window_icon

logger = logging.getLogger(__name__)


DEFAULT_IMPORT_SUBFOLDER = "GERAL"


class SubpastaDialog(ctk.CTkToplevel):
    """Dialogo CTkToplevel que coleta o nome da subpasta (ex.: usada em uploads de clientes)."""

    DIALOG_MIN_WIDTH = 500
    WRAP_LEN = 440

    def __init__(self, parent: tk.Misc, default: str = ""):
        super().__init__(parent)
        self.withdraw()
        self.title("Subpasta em GERAL")
        self.transient(parent)
        self.resizable(False, False)
        self.configure(fg_color=APP_BG)
        apply_window_icon(self)

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        # Card central arredondado
        card = ctk.CTkFrame(
            self,
            corner_radius=DIALOG_RADIUS,
            fg_color=SURFACE,
            bg_color=APP_BG,
        )
        card.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        card.columnconfigure(0, weight=1)

        # Label título
        ctk.CTkLabel(
            card,
            text=f"Digite o nome da subpasta (ou deixe vazio para usar só '{DEFAULT_IMPORT_SUBFOLDER}/').",
            font=FONT_SECTION,
            wraplength=self.WRAP_LEN,
            justify="left",
            fg_color="transparent",
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(20, 4))

        # Label descrição
        ctk.CTkLabel(
            card,
            text="Ex.: SIFAP, VISA, Farmacia_Popular, Auditoria",
            font=FONT_BODY_SM,
            text_color=TEXT_MUTED,
            wraplength=self.WRAP_LEN,
            justify="left",
            fg_color="transparent",
        ).grid(row=1, column=0, sticky="w", padx=20, pady=(0, 10))

        # Entry arredondada
        self.var = tk.StringVar(value=default or "")
        ent = ctk.CTkEntry(
            card,
            textvariable=self.var,
            corner_radius=INPUT_RADIUS,
            placeholder_text="Ex.: SIFAP, VISA, Farmacia_Popular, Auditoria",
        )
        ent.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 16))

        # Botões alinhados à direita (tamanho padrão de diálogo)
        btns_frame = ctk.CTkFrame(card, fg_color="transparent")
        btns_frame.grid(row=3, column=0, sticky="e", padx=20, pady=(0, 20))
        ctk.CTkButton(
            btns_frame,
            text="Cancelar",
            command=self._cancel,
            width=DIALOG_BTN_W,
            height=DIALOG_BTN_H,
            corner_radius=BUTTON_RADIUS,
            fg_color=BTN_SECONDARY,
            hover_color=BTN_SECONDARY_HOVER,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            btns_frame,
            text="OK",
            command=self._ok,
            width=DIALOG_BTN_W,
            height=DIALOG_BTN_H,
            corner_radius=BUTTON_RADIUS,
            fg_color=PRIMARY_BLUE,
            hover_color=PRIMARY_BLUE_HOVER,
        ).pack(side="left")

        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self._cancel())
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Centralizar sobre o parent e exibir com anti-flash
        try:
            self.update_idletasks()
            req_w = max(self.DIALOG_MIN_WIDTH, self.winfo_reqwidth())
            req_h = self.winfo_reqheight() + 10
            self.minsize(req_w, req_h)
            # Centralizar sobre o parent
            try:
                px = parent.winfo_rootx()
                py = parent.winfo_rooty()
                pw = parent.winfo_width()
                ph = parent.winfo_height()
                x = max(0, px + (pw - req_w) // 2)
                y = max(0, py + (ph - req_h) // 2)
                self.geometry(f"{req_w}x{req_h}+{x}+{y}")
            except Exception:
                self.geometry(f"{req_w}x{req_h}")
            # Anti-flash: alpha 0 → deiconify → reveal após 220ms
            try:
                self.attributes("-alpha", 0.0)
            except Exception:
                pass
            self.deiconify()
            self.lift()
            self.grab_set()
            self.focus_force()

            def _reveal() -> None:
                if not self.winfo_exists():
                    return
                apply_window_icon(self)
                try:
                    self.attributes("-alpha", 1.0)
                except Exception:
                    pass
                self.lift()

            self.after(220, _reveal)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao centralizar SubpastaDialog: %s", exc)
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
