# -*- coding: utf-8 -*-
"""Utilitários de tipagem para UI - CTk/Tk compatibility protocols."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class TkInfoMixin(Protocol):
    """Protocol para widgets que possuem métodos winfo_* do Tkinter."""

    def winfo_rootx(self) -> int:
        """Coordenada X do widget relativa à tela."""
        ...

    def winfo_rooty(self) -> int:
        """Coordenada Y do widget relativa à tela."""
        ...

    def winfo_reqwidth(self) -> int:
        """Largura solicitada do widget."""
        ...

    def winfo_height(self) -> int:
        """Altura atual do widget."""
        ...

    def winfo_children(self) -> list[object]:
        """Lista de widgets filhos."""
        ...


@runtime_checkable
class TkToplevelMixin(Protocol):
    """Protocol para toplevels que possuem métodos de janela do Tkinter."""

    def withdraw(self) -> None:
        """Esconde a janela."""
        ...

    def deiconify(self) -> None:
        """Mostra a janela."""
        ...

    def overrideredirect(self, enable: bool) -> None:
        """Define se a janela deve ter decorações do WM."""
        ...

    def winfo_viewable(self) -> bool:
        """Retorna se a janela está visível."""
        ...

    def geometry(self, geometry: str) -> None:
        """Define geometria da janela."""
        ...
