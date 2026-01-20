# -*- coding: utf-8 -*-
"""Modal CustomTkinter para módulo Clientes.

Fornece dialogs modais consistentes com o tema Light/Dark do módulo Clientes,
substituindo tk.messagebox quando CustomTkinter está disponível.

Microfase: 6 (Subdialogs CustomTkinter)
"""

from __future__ import annotations

import logging
import tkinter as tk
from typing import TYPE_CHECKING, Literal

# CustomTkinter: fonte única centralizada (Microfase 23 - SSoT)
from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk

if TYPE_CHECKING:
    pass  # ctk já importado via src.ui.ctk_config

from src.modules.clientes.appearance import ClientesThemeManager, LIGHT_PALETTE, DARK_PALETTE

logger = logging.getLogger(__name__)


class ClientesModalCTK:
    """Modal CustomTkinter para dialogs do módulo Clientes.

    Fornece métodos estáticos para exibir modals com visual consistente:
    - confirm(): Dialog de confirmação (Sim/Não)
    - alert(): Dialog de alerta (OK)
    - error(): Dialog de erro (OK)
    - info(): Dialog de informação (OK)

    Se CustomTkinter não disponível, fallback para tk.messagebox.
    """

    @staticmethod
    def confirm(
        parent: tk.Misc,
        title: str,
        message: str,
        theme_manager: ClientesThemeManager | None = None,
    ) -> bool:
        """Exibe dialog de confirmação (Sim/Não).

        Args:
            parent: Widget pai para centralizar dialog.
            title: Título do dialog.
            message: Mensagem do dialog.
            theme_manager: Theme manager para cores (opcional, cria se ausente).

        Returns:
            True se confirmado, False caso contrário.
        """
        if not HAS_CUSTOMTKINTER or ctk is None:
            # Fallback para messagebox legado
            from tkinter import messagebox

            return messagebox.askyesno(title, message, parent=parent)

        return _create_ctk_modal(
            parent=parent,
            title=title,
            message=message,
            modal_type="confirm",
            theme_manager=theme_manager,
        )

    @staticmethod
    def alert(
        parent: tk.Misc,
        title: str,
        message: str,
        theme_manager: ClientesThemeManager | None = None,
    ) -> None:
        """Exibe dialog de alerta (OK).

        Args:
            parent: Widget pai para centralizar dialog.
            title: Título do dialog.
            message: Mensagem do dialog.
            theme_manager: Theme manager para cores (opcional, cria se ausente).
        """
        if not HAS_CUSTOMTKINTER or ctk is None:
            # Fallback para messagebox legado
            from tkinter import messagebox

            messagebox.showwarning(title, message, parent=parent)
            return

        _create_ctk_modal(
            parent=parent,
            title=title,
            message=message,
            modal_type="alert",
            theme_manager=theme_manager,
        )

    @staticmethod
    def error(
        parent: tk.Misc,
        title: str,
        message: str,
        theme_manager: ClientesThemeManager | None = None,
    ) -> None:
        """Exibe dialog de erro (OK).

        Args:
            parent: Widget pai para centralizar dialog.
            title: Título do dialog.
            message: Mensagem do dialog.
            theme_manager: Theme manager para cores (opcional, cria se ausente).
        """
        if not HAS_CUSTOMTKINTER or ctk is None:
            # Fallback para messagebox legado
            from tkinter import messagebox

            messagebox.showerror(title, message, parent=parent)
            return

        _create_ctk_modal(
            parent=parent,
            title=title,
            message=message,
            modal_type="error",
            theme_manager=theme_manager,
        )

    @staticmethod
    def info(
        parent: tk.Misc,
        title: str,
        message: str,
        theme_manager: ClientesThemeManager | None = None,
    ) -> None:
        """Exibe dialog de informação (OK).

        Args:
            parent: Widget pai para centralizar dialog.
            title: Título do dialog.
            message: Mensagem do dialog.
            theme_manager: Theme manager para cores (opcional, cria se ausente).
        """
        if not HAS_CUSTOMTKINTER or ctk is None:
            # Fallback para messagebox legado
            from tkinter import messagebox

            messagebox.showinfo(title, message, parent=parent)
            return

        _create_ctk_modal(
            parent=parent,
            title=title,
            message=message,
            modal_type="info",
            theme_manager=theme_manager,
        )


def _create_ctk_modal(
    parent: tk.Misc,
    title: str,
    message: str,
    modal_type: Literal["confirm", "alert", "error", "info"],
    theme_manager: ClientesThemeManager | None = None,
) -> bool:
    """Cria e exibe um modal CustomTkinter.

    Args:
        parent: Widget pai.
        title: Título do modal.
        message: Mensagem do modal.
        modal_type: Tipo de modal (confirm, alert, error, info).
        theme_manager: Theme manager para cores.

    Returns:
        True se confirmado (para confirm), False caso contrário.
        Para outros tipos, retorna False.
    """
    if not HAS_CUSTOMTKINTER or ctk is None:
        return False

    # Theme manager
    if theme_manager is None:
        theme_manager = ClientesThemeManager()

    current_mode = theme_manager.load_mode()
    # NÃO usar ctk.set_appearance_mode direto (viola SSoT)
    # O GlobalThemeManager já definiu o modo global

    # Paletas
    palette = DARK_PALETTE if current_mode == "dark" else LIGHT_PALETTE

    # Criar janela modal
    try:
        parent_window = parent.winfo_toplevel()  # type: ignore[union-attr]
    except Exception:
        parent_window = parent

    modal = ctk.CTkToplevel(parent_window)  # type: ignore[arg-type]
    modal.title(title)
    modal.resizable(False, False)
    modal.transient(parent_window)

    # Cores
    bg_color = palette["bg"]
    fg_color = palette["fg"]
    accent_color = (palette["accent"], DARK_PALETTE["accent"])
    danger_color = (palette["danger"], DARK_PALETTE["danger"])
    neutral_color = (palette["neutral_btn"], DARK_PALETTE["neutral_btn"])

    modal.configure(fg_color=bg_color)

    # Frame principal
    frame = ctk.CTkFrame(modal, fg_color="transparent")
    frame.pack(fill="both", expand=True, padx=20, pady=20)

    # Ícone baseado no tipo
    icon_map = {
        "confirm": "❓",
        "alert": "⚠️",
        "error": "❌",
        "info": "ℹ️",
    }
    icon = icon_map.get(modal_type, "ℹ️")

    # Label com ícone e mensagem
    message_text = f"{icon}  {message}"
    label = ctk.CTkLabel(
        frame,
        text=message_text,
        wraplength=400,
        justify="left",
        text_color=(fg_color, DARK_PALETTE["fg"]),
        font=("Segoe UI", 11),
    )
    label.pack(pady=(0, 20))

    # Resultado (para confirm)
    result = [False]

    def on_yes():
        result[0] = True
        modal.destroy()

    def on_no():
        result[0] = False
        modal.destroy()

    def on_ok():
        modal.destroy()

    # Botões
    button_frame = ctk.CTkFrame(frame, fg_color="transparent")
    button_frame.pack()

    if modal_type == "confirm":
        # Botões Sim/Não
        btn_yes = ctk.CTkButton(
            button_frame,
            text="✓ Sim",
            command=on_yes,
            fg_color=accent_color,
            hover_color=(palette["accent_hover"], DARK_PALETTE["accent_hover"]),
            width=100,
        )
        btn_yes.pack(side="left", padx=5)

        btn_no = ctk.CTkButton(
            button_frame,
            text="✗ Não",
            command=on_no,
            fg_color=neutral_color,
            hover_color=(palette["neutral_hover"], DARK_PALETTE["neutral_hover"]),
            text_color=(fg_color, DARK_PALETTE["fg"]),
            width=100,
        )
        btn_no.pack(side="left", padx=5)

        # Enter = Sim, Escape = Não
        modal.bind("<Return>", lambda e: on_yes())
        modal.bind("<Escape>", lambda e: on_no())
        btn_yes.focus_set()

    else:
        # Botão OK
        btn_color = danger_color if modal_type == "error" else accent_color
        btn_ok = ctk.CTkButton(
            button_frame,
            text="OK",
            command=on_ok,
            fg_color=btn_color,
            hover_color=(
                palette["danger_hover"] if modal_type == "error" else palette["accent_hover"],
                DARK_PALETTE["danger_hover"] if modal_type == "error" else DARK_PALETTE["accent_hover"],
            ),
            width=100,
        )
        btn_ok.pack()

        # Enter/Escape = OK
        modal.bind("<Return>", lambda e: on_ok())
        modal.bind("<Escape>", lambda e: on_ok())
        btn_ok.focus_set()

    # Centralizar
    modal.update_idletasks()
    modal_width = modal.winfo_reqwidth()
    modal_height = modal.winfo_reqheight()

    try:
        parent_x = parent_window.winfo_x()
        parent_y = parent_window.winfo_y()
        parent_width = parent_window.winfo_width()
        parent_height = parent_window.winfo_height()

        x = parent_x + (parent_width - modal_width) // 2
        y = parent_y + (parent_height - modal_height) // 2
    except Exception:
        # Fallback: centro da tela
        screen_width = modal.winfo_screenwidth()
        screen_height = modal.winfo_screenheight()
        x = (screen_width - modal_width) // 2
        y = (screen_height - modal_height) // 2

    modal.geometry(f"{modal_width}x{modal_height}+{x}+{y}")

    # Modal
    modal.grab_set()
    modal.focus_set()
    modal.wait_window()

    return result[0]
