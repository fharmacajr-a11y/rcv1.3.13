# -*- coding: utf-8 -*-
# gui/placeholders.py
from __future__ import annotations

from typing import Protocol, Type
import ttkbootstrap as tb
import tkinter.font as tkfont


class _BackCb(Protocol):
    def __call__(self) -> None: ...


class _BasePlaceholder(tb.Frame):
    title: str = "Em breve"

    def __init__(self, master, *, on_back: _BackCb | None = None, **_):
        super().__init__(master)

        header_font = tkfont.nametofont("TkDefaultFont").copy()
        header_font.configure(size=16, weight="bold")

        top = tb.Frame(self)
        top.pack(fill="x", padx=10, pady=(10, 0))

        center = tb.Frame(self)
        center.pack(expand=True, fill="both")

        header = tb.Label(center, text=self.title, font=header_font)
        header.pack(pady=(0, 6))

        desc = tb.Label(center, text="Funcionalidade em desenvolvimento.")
        desc.pack(pady=(0, 16))

        btn = tb.Button(center, text="Voltar", bootstyle="secondary")
        btn.pack()

        if callable(on_back):
            btn.configure(command=on_back)
            self.bind_all("<Escape>", lambda e: on_back(), add="+")

        try:
            self.master.pack_propagate(False)
        except Exception:
            pass


class AnvisaPlaceholder(_BasePlaceholder):
    title = "ANVISA - Em breve"


class AuditoriaPlaceholder(_BasePlaceholder):
    title = "AUDITORIA - Em breve"


class FarmaciaPopularPlaceholder(_BasePlaceholder):
    title = "FARMACIA POPULAR - Em breve"


class SnjpcPlaceholder(_BasePlaceholder):
    title = "SNJPC - Em breve"


class SenhasPlaceholder(_BasePlaceholder):
    title = "SENHAS - Em breve"


PlaceholderType = Type[_BasePlaceholder]


# --- compat: ComingSoonScreen esperado por app_gui.py ---
try:
    ComingSoonScreen  # type: ignore[name-defined]
except NameError:
    try:
        ComingSoonScreen = _BasePlaceholder  # type: ignore[name-defined]
    except Exception:

        class ComingSoonScreen(tb.Frame):
            def __init__(self, master=None, text: str = "Em breve...", **kwargs):
                super().__init__(master, **kwargs)
                container = tb.Frame(self)
                container.pack(fill="both", expand=True, padx=24, pady=24)
                title = tb.Label(container, text=text)
                title.pack(anchor="center", pady=8)


try:
    __all__.append("ComingSoonScreen")  # type: ignore[attr-defined]
except Exception:
    pass
