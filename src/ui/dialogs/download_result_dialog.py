# -*- coding: utf-8 -*-
"""Diálogo de resultado de download.

Popup CTk para exibir resultado de download de arquivo único ou ZIP.
Movido de _files_download_mixin.py (Fase 1 — remoção do legado V1b).
"""

from __future__ import annotations

from typing import Any

from src.ui.ctk_config import ctk
from src.ui.dark_window_helper import set_win_dark_titlebar
from src.ui.ui_tokens import (
    BORDER,
    BUTTON_RADIUS,
    DIALOG_BTN_H,
    DIALOG_BTN_W,
    PRIMARY_BLUE,
    PRIMARY_BLUE_HOVER,
    SURFACE_2,
    TEXT_MUTED,
    TEXT_PRIMARY,
)
from src.ui.window_utils import apply_window_icon


class DownloadResultDialog(ctk.CTkToplevel):
    """Popup CTk para exibir resultado de download.

    Substitui tkinter.messagebox.showinfo para manter ícone RC e visual CTk.
    Segue o padrão anti-flash: prepare_hidden_window → build → show_centered_no_flash.
    """

    def __init__(
        self,
        parent: Any,
        title: str,
        file_name: str,
        save_path: str,
        extra_info: str = "",
        **kwargs: Any,
    ):
        super().__init__(parent, **kwargs)

        # Anti-flash: ocultar imediatamente antes de qualquer build
        from src.ui.window_utils import prepare_hidden_window, show_centered_no_flash as _show_centered

        prepare_hidden_window(self)

        self.title(title)
        self.configure(fg_color=SURFACE_2)
        self.resizable(False, False)

        # Ícone RC (antes de deiconify para evitar flash)
        try:
            apply_window_icon(self)
        except Exception:
            pass

        # Modal (transient antes de exibir)
        self.transient(parent)

        # Titlebar escura no Windows
        try:
            set_win_dark_titlebar(self)
        except Exception:
            pass

        self._build(title, file_name, save_path, extra_info)

        # Exibir centralizado sem flash; height=None → mede winfo_reqheight automaticamente
        _show_centered(self, parent, width=500, height=None)
        self.minsize(480, 235)  # pyright: ignore[reportAttributeAccessIssue]

        # grab_set após deiconify
        self.after(50, self.grab_set)

        # Fechar com Escape/Enter
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Return>", lambda e: self.destroy())

    def _build(self, title: str, file_name: str, save_path: str, extra_info: str) -> None:
        """Constrói o conteúdo visual do popup."""
        from src.ui.dialog_icons import make_icon_label

        # corner_radius=0 + padx/pady=0: card preenche a janela sem expor
        # fundo do pai → elimina "halo" branco ao redor das bordas arredondadas.
        card = ctk.CTkFrame(
            self,
            corner_radius=0,
            fg_color=SURFACE_2,
            border_width=1,
            border_color=BORDER,
        )
        card.pack(fill="both", expand=True, padx=0, pady=0)
        card.grid_columnconfigure(0, weight=1)  # pyright: ignore[reportAttributeAccessIssue]

        # Ícone gráfico de sucesso (PIL desenhado, sem emoji)
        make_icon_label(card, "success", size=44).grid(row=0, column=0, pady=(20, 2))

        # Título
        ctk.CTkLabel(
            card,
            text=title,
            font=("Segoe UI", 13, "bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=1, column=0, pady=(0, 2))

        # Informação extra (ex: quantidade de arquivos no ZIP)
        if extra_info:
            ctk.CTkLabel(
                card,
                text=extra_info,
                font=("Segoe UI", 10),
                text_color=TEXT_MUTED,
            ).grid(row=2, column=0, pady=(0, 4))

        # Rótulo "Arquivo salvo em:"
        ctk.CTkLabel(
            card,
            text="Arquivo salvo em:",
            font=("Segoe UI", 10),
            text_color=TEXT_MUTED,
            anchor="w",
        ).grid(row=3, column=0, sticky="w", padx=20, pady=(6, 0))

        # Caixa de caminho (CTkTextbox somente leitura)
        path_box = ctk.CTkTextbox(
            card,
            height=46,
            corner_radius=8,
            font=("Segoe UI", 9),
            activate_scrollbars=False,
            wrap="word",
        )
        path_box.grid(row=4, column=0, sticky="ew", padx=20, pady=(2, 10))
        path_box.insert("1.0", save_path)
        path_box.configure(state="disabled")

        # Botões
        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.grid(row=5, column=0, pady=(0, 20))

        ctk.CTkButton(
            btn_frame,
            text="Copiar caminho",
            width=DIALOG_BTN_W,
            height=DIALOG_BTN_H,
            corner_radius=BUTTON_RADIUS,
            fg_color=("#6b7280", "#4b5563"),
            hover_color=("#4b5563", "#374151"),
            command=lambda p=save_path: self._copy_path(p),
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="OK",
            width=DIALOG_BTN_W,
            height=DIALOG_BTN_H,
            corner_radius=BUTTON_RADIUS,
            fg_color=PRIMARY_BLUE,
            hover_color=PRIMARY_BLUE_HOVER,
            command=self.destroy,
        ).pack(side="left", padx=5)

    def _copy_path(self, path: str) -> None:
        """Copia o caminho para a área de transferência."""
        try:
            self.clipboard_clear()  # pyright: ignore[reportAttributeAccessIssue]
            self.clipboard_append(path)  # pyright: ignore[reportAttributeAccessIssue]
        except Exception:
            pass
