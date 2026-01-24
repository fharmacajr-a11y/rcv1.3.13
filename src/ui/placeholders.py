# -*- coding: utf-8 -*-
# gui/placeholders.py
from __future__ import annotations

import logging
import tkinter as tk
import tkinter.font as tkfont
from typing import Protocol, Type

from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk

__all__ = ["PlaceholderType"]

_log = logging.getLogger(__name__)


class _BackCb(Protocol):
    def __call__(self) -> None: ...


class _BasePlaceholder(tk.Frame if not (HAS_CUSTOMTKINTER and ctk) else ctk.CTkFrame):  # type: ignore[misc]
    title: str = "Em breve"

    def __init__(self, master, *, on_back: _BackCb | None = None, **_):
        super().__init__(master)

        # Configurar fonte para CTk e tk
        if HAS_CUSTOMTKINTER and ctk is not None:
            header_font = ("Arial", 16, "bold")  # CTk aceita tuplas
        else:
            header_font = tkfont.nametofont("TkDefaultFont").copy()
            header_font.configure(size=16, weight="bold")

        if HAS_CUSTOMTKINTER and ctk is not None:
            top = ctk.CTkFrame(self, fg_color="transparent")
            center = ctk.CTkFrame(self, fg_color="transparent")
        else:
            top = tk.Frame(self)
            center = tk.Frame(self)

        top.pack(fill="x", padx=10, pady=(10, 0))
        center.pack(expand=True, fill="both")

        if HAS_CUSTOMTKINTER and ctk is not None:
            header = ctk.CTkLabel(center, text=self.title, font=header_font)
            desc = ctk.CTkLabel(center, text="Funcionalidade em desenvolvimento.")
            btn = ctk.CTkButton(center, text="Voltar")
        else:
            header = tk.Label(center, text=self.title, font=header_font)
            desc = tk.Label(center, text="Funcionalidade em desenvolvimento.")
            btn = tk.Button(center, text="Voltar")

        header.pack(pady=(0, 6))
        desc.pack(pady=(0, 16))
        btn.pack()

        if callable(on_back):
            btn.configure(command=on_back)
            self.bind_all("<Escape>", lambda e: on_back(), add="+")

        try:
            self.master.pack_propagate(False)
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao desabilitar pack_propagate: %s", exc)


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

        class ComingSoonScreen(tk.Frame if not (HAS_CUSTOMTKINTER and ctk) else ctk.CTkFrame):  # type: ignore[misc]
            def __init__(self, master=None, text: str = "Em breve...", **kwargs):
                super().__init__(master, **kwargs)
                if HAS_CUSTOMTKINTER and ctk is not None:
                    container = ctk.CTkFrame(self)
                    container.pack(fill="both", expand=True, padx=24, pady=24)
                    title = ctk.CTkLabel(container, text=text)
                else:
                    container = tk.Frame(self)
                    container.pack(fill="both", expand=True, padx=24, pady=24)
                    title = tk.Label(container, text=text)
                title.pack(anchor="center", pady=8)


try:
    __all__.append("ComingSoonScreen")  # type: ignore[attr-defined]
except Exception as exc:  # noqa: BLE001
    _log.debug("Falha ao adicionar ComingSoonScreen a __all__: %s", exc)
