"""CTkSplitPane - Split container com sash arrastável para CustomTkinter.

MICROFASE 30: Substitui PanedWindow legado por widget CTk nativo.
"""

from __future__ import annotations

import tkinter as tk
from typing import Any, Literal, cast

from src.ui.ctk_config import ctk


class CTkSplitPane(ctk.CTkFrame):
    """Container com 2 panes e sash arrastável (substitui PanedWindow legado)."""

    def __init__(
        self,
        master: Any,
        orient: Literal["horizontal", "vertical"] = "horizontal",
        sash_width: int = 5,
        sash_color: str | None = None,
        sash_hover_color: str | None = None,
        **kwargs: Any,
    ):
        super().__init__(master, **kwargs)

        self._orient = orient
        self._sash_width = sash_width

        # Acesso seguro às cores do tema via cast (CTk possui ThemeManager em runtime)
        ctk_any = cast(Any, ctk)
        theme_manager = getattr(ctk_any, "ThemeManager", None)
        theme_colors = getattr(theme_manager, "theme", {}) if theme_manager else {}
        frame_colors = theme_colors.get("CTkFrame", {}).get("border_color", ("#3B3B3B", "#404040"))
        button_colors = theme_colors.get("CTkButton", {}).get("fg_color", ("#1f538d", "#14375e"))

        # Aplicação de appearance mode via cast (método interno do CTk)
        apply_mode_fn = getattr(self, "_apply_appearance_mode", lambda x: x[0] if isinstance(x, (list, tuple)) else x)

        self._sash_color = sash_color or apply_mode_fn(frame_colors)
        self._sash_hover_color = sash_hover_color or apply_mode_fn(button_colors)

        self._pane1: tk.Widget | None = None
        self._pane2: tk.Widget | None = None
        self._sash: ctk.CTkFrame | None = None

        self._dragging = False
        self._drag_start_pos = 0
        self._ratio = 0.5  # Proporção inicial 50/50
        self._minsize1 = 50
        self._minsize2 = 50

        # Configure grid
        if orient == "horizontal":
            self.columnconfigure(0, weight=1, minsize=self._minsize1)
            self.columnconfigure(1, weight=0)
            self.columnconfigure(2, weight=1, minsize=self._minsize2)
            self.rowconfigure(0, weight=1)
        else:  # vertical
            self.rowconfigure(0, weight=1, minsize=self._minsize1)
            self.rowconfigure(1, weight=0)
            self.rowconfigure(2, weight=1, minsize=self._minsize2)
            self.columnconfigure(0, weight=1)

        # Create sash
        self._create_sash()

    def _create_sash(self) -> None:
        """Cria o sash arrastável."""
        if self._orient == "horizontal":
            self._sash = ctk.CTkFrame(
                self, width=self._sash_width, fg_color=self._sash_color, cursor="sb_h_double_arrow"
            )
            self._sash.grid(row=0, column=1, sticky="ns")
        else:
            self._sash = ctk.CTkFrame(
                self, height=self._sash_width, fg_color=self._sash_color, cursor="sb_v_double_arrow"
            )
            self._sash.grid(row=1, column=0, sticky="ew")

        # Bind drag events
        self._sash.bind("<ButtonPress-1>", self._on_sash_press)
        self._sash.bind("<B1-Motion>", self._on_sash_drag)
        self._sash.bind("<ButtonRelease-1>", self._on_sash_release)
        self._sash.bind("<Enter>", self._on_sash_enter)
        self._sash.bind("<Leave>", self._on_sash_leave)

    def add(self, widget: tk.Widget, **kwargs: Any) -> None:
        """Adiciona um pane ao container.

        Args:
            widget: Widget a ser adicionado (pane1 ou pane2)
            **kwargs: Opções adicionais (weight, minsize, etc.)
        """
        if self._pane1 is None:
            self._pane1 = widget
            if self._orient == "horizontal":
                widget.grid(row=0, column=0, sticky="nsew")
            else:
                widget.grid(row=0, column=0, sticky="nsew")

            # Aplicar minsize se fornecido
            if "minsize" in kwargs:
                self._minsize1 = kwargs["minsize"]
        elif self._pane2 is None:
            self._pane2 = widget
            if self._orient == "horizontal":
                widget.grid(row=0, column=2, sticky="nsew")
            else:
                widget.grid(row=2, column=0, sticky="nsew")

            # Aplicar minsize se fornecido
            if "minsize" in kwargs:
                self._minsize2 = kwargs["minsize"]
        else:
            raise ValueError("CTkSplitPane suporta apenas 2 panes")

    def forget(self, widget: tk.Widget) -> None:
        """Remove um pane do container."""
        if widget == self._pane1:
            cast(Any, widget).grid_forget()  # Grid forget disponível em runtime
            self._pane1 = None
        elif widget == self._pane2:
            cast(Any, widget).grid_forget()  # Grid forget disponível em runtime
            self._pane2 = None

    def set_ratio(self, ratio: float) -> None:
        """Define a proporção do split (0.0 a 1.0)."""
        self._ratio = max(0.1, min(0.9, ratio))
        self._update_layout()

    def get_ratio(self) -> float:
        """Retorna a proporção atual do split."""
        return self._ratio

    def _update_layout(self) -> None:
        """Atualiza o layout baseado na proporção."""
        if self._orient == "horizontal":
            # Calcular weights baseados na proporção
            weight1 = int(self._ratio * 100)
            weight2 = int((1 - self._ratio) * 100)
            self.columnconfigure(0, weight=weight1)
            self.columnconfigure(2, weight=weight2)
        else:
            weight1 = int(self._ratio * 100)
            weight2 = int((1 - self._ratio) * 100)
            self.rowconfigure(0, weight=weight1)
            self.rowconfigure(2, weight=weight2)

    def _on_sash_press(self, event: Any) -> None:  # event: tkinter Event em runtime
        """Handler para início do drag."""
        self._dragging = True
        if self._orient == "horizontal":
            self._drag_start_pos = event.x_root
        else:
            self._drag_start_pos = event.y_root

    def _on_sash_drag(self, event: Any) -> None:  # event: tkinter Event em runtime
        """Handler para drag do sash."""
        if not self._dragging:
            return

        if self._orient == "horizontal":
            # Calcular nova proporção baseada na posição horizontal
            container_width = self.winfo_width()
            if container_width > 0:
                sash_x = cast(Any, self._sash).winfo_x() + (event.x_root - self._drag_start_pos)
                new_ratio = sash_x / container_width
                self.set_ratio(new_ratio)
                self._drag_start_pos = event.x_root
        else:
            # Calcular nova proporção baseada na posição vertical
            container_height = self.winfo_height()
            if container_height > 0:
                sash_y = cast(Any, self._sash).winfo_y() + (event.y_root - self._drag_start_pos)
                new_ratio = sash_y / container_height
                self.set_ratio(new_ratio)
                self._drag_start_pos = event.y_root

    def _on_sash_release(self, event: Any) -> None:  # event: tkinter Event em runtime
        """Handler para fim do drag."""
        self._dragging = False

    def _on_sash_enter(self, event: Any) -> None:  # event: tkinter Event em runtime
        """Handler para mouse enter no sash."""
        if self._sash:
            self._sash.configure(fg_color=self._sash_hover_color)

    def _on_sash_leave(self, event: Any) -> None:  # event: tkinter Event em runtime
        """Handler para mouse leave no sash."""
        if self._sash and not self._dragging:
            self._sash.configure(fg_color=self._sash_color)


__all__ = ["CTkSplitPane"]
