from __future__ import annotations

from src.ui.ctk_config import ctk

# -*- coding: utf-8 -*-
"""ScrollableFrame widget para conteúdo rolável usando Canvas.

Fornece um frame com barra de rolagem vertical automática,
ideal para conteúdo que pode exceder a altura da janela.
"""

import tkinter as tk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tkinter import Event


class ScrollableFrame(tk.Frame):
    """Frame com barra de rolagem vertical automática.

    Usa Canvas + Frame interno para permitir conteúdo rolável.
    A barra de rolagem aparece automaticamente quando necessário.

    Attributes:
        canvas: Canvas interno que contém o frame de conteúdo.
        vscrollbar: Barra de rolagem vertical.
        content: Frame interno onde o conteúdo deve ser adicionado.

    Example:
        >>> scroll = ScrollableFrame(parent)
        >>> scroll.pack(fill="both", expand=True)
        >>>
        >>> # Adicionar widgets ao frame interno
        >>> label = tk.Label(scroll.content, text="Conteúdo")
        >>> label.pack()
    """

    def __init__(self, parent: tk.Widget, *args, **kwargs) -> None:
        """Inicializa o ScrollableFrame.

        Args:
            parent: Widget pai.
            *args: Argumentos posicionais para tk.Frame.
            **kwargs: Argumentos nomeados para tk.Frame.
        """
        super().__init__(parent, *args, **kwargs)

        # Obter cor de fundo do frame
        try:
            bg_color = self.cget("background")
        except Exception:
            bg_color = "white"

        # Canvas sem borda para conter o frame de conteúdo
        self.canvas = tk.Canvas(
            self,
            borderwidth=0,
            highlightthickness=0,
            bg=bg_color,
        )

        # Barra de rolagem vertical
        self.vscrollbar = ctk.CTkScrollbar(
            self,
            command=self.canvas.yview,
        )
        self.canvas.configure(yscrollcommand=self.vscrollbar.set)

        # Frame interno onde o conteúdo será adicionado
        self.content = tk.Frame(self.canvas)

        # Criar janela no canvas para o frame de conteúdo
        self._canvas_window = self.canvas.create_window(
            (0, 0),
            window=self.content,
            anchor="nw",
        )

        # Layout: canvas à esquerda, scrollbar à direita
        self.canvas.pack(side="left", fill="both", expand=True)
        self.vscrollbar.pack(side="right", fill="y")

        # Atualizar scrollregion quando o conteúdo muda de tamanho
        self.content.bind("<Configure>", self._on_content_configure)

        # Atualizar largura do canvas quando o ScrollableFrame é redimensionado
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Bind de mousewheel para scroll
        self._bind_mousewheel()

    def _on_content_configure(self, event: Event | None = None) -> None:
        """Atualiza a scrollregion quando o conteúdo muda de tamanho.

        Args:
            event: Evento de configuração (ignorado).
        """
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event: Event | None = None) -> None:
        """Ajusta a largura do frame interno quando o canvas é redimensionado.

        Args:
            event: Evento de configuração do canvas.
        """
        if event:
            # Fazer o frame interno ocupar toda a largura do canvas
            canvas_width = event.width
            self.canvas.itemconfig(self._canvas_window, width=canvas_width)

    def _bind_mousewheel(self) -> None:
        """Adiciona suporte a mousewheel para scroll."""
        # Bind quando o mouse entra no widget
        self.canvas.bind("<Enter>", self._on_enter)
        self.canvas.bind("<Leave>", self._on_leave)

    def _on_enter(self, event: Event | None = None) -> None:
        """Ativa scroll com mousewheel quando o mouse entra no canvas.

        Args:
            event: Evento de entrada do mouse.
        """
        # Windows e MacOS
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        # Linux
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _on_leave(self, event: Event | None = None) -> None:
        """Desativa scroll com mousewheel quando o mouse sai do canvas.

        Args:
            event: Evento de saída do mouse.
        """
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event: Event) -> None:
        """Processa evento de mousewheel para scroll.

        Args:
            event: Evento de mousewheel.
        """
        # Windows e MacOS
        if event.num == 4 or event.delta > 0:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5 or event.delta < 0:
            self.canvas.yview_scroll(1, "units")

    def scroll_to_top(self) -> None:
        """Rola o conteúdo para o topo."""
        self.canvas.yview_moveto(0)

    def scroll_to_bottom(self) -> None:
        """Rola o conteúdo para o final."""
        self.canvas.yview_moveto(1)
