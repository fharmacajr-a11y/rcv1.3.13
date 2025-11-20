from __future__ import annotations

import tkinter as tk
from typing import Callable, Optional

try:
    import ttkbootstrap as tb
except Exception:
    from tkinter import ttk as tb  # fallback

from src.ui.components import create_footer_buttons


class ClientesFooter(tb.Frame):
    """Barra inferior com botões de ações da tela de Clientes."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        on_novo: Callable[[], None],
        on_editar: Callable[[], None],
        on_subpastas: Callable[[], None],
        on_enviar_supabase: Callable[[], None],
        on_enviar_pasta: Callable[[], None],
    ) -> None:
        super().__init__(master)

        buttons = create_footer_buttons(
            self,
            on_novo=on_novo,
            on_editar=on_editar,
            on_subpastas=on_subpastas,
            on_enviar=on_enviar_supabase,
            on_enviar_pasta=on_enviar_pasta,
        )
        buttons.frame.pack(fill="x", padx=0, pady=0)

        self.btn_novo = buttons.novo
        self.btn_editar = buttons.editar
        self.btn_subpastas = buttons.subpastas
        self.btn_enviar = buttons.enviar
        self.enviar_menu = buttons.enviar_menu

        self._uploading_busy = False
        self._send_button_prev_text: Optional[str] = None

        # Alias para compatibilidade
        self.frame = buttons.frame

    def set_uploading(self, uploading: bool) -> None:
        """Desabilita/ajusta textos durante upload em andamento."""
        uploading = bool(uploading)
        if uploading == self._uploading_busy:
            return

        self._uploading_busy = uploading

        if uploading:
            try:
                if self.btn_enviar:
                    self._send_button_prev_text = self.btn_enviar.cget("text")
                    self.btn_enviar.configure(text="Enviando…")
            except Exception:
                pass
        else:
            try:
                if self.btn_enviar and self._send_button_prev_text is not None:
                    self.btn_enviar.configure(text=self._send_button_prev_text)
            except Exception:
                pass
            self._send_button_prev_text = None


__all__ = ["ClientesFooter"]
