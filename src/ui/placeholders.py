# -*- coding: utf-8 -*-
# gui/placeholders.py
from __future__ import annotations

import logging
import tkinter as tk
from typing import Protocol, Type

from src.ui.ctk_config import ctk
from src.ui.utils.binding_tracker import BindingTracker
from src.ui.widgets.button_factory import make_btn

__all__ = ["PlaceholderType"]

_log = logging.getLogger(__name__)


class _BackCb(Protocol):
    def __call__(self) -> None: ...


class _BasePlaceholder(ctk.CTkFrame):  # type: ignore[misc]
    title: str = "Em breve"

    def __init__(self, master, *, on_back: _BackCb | None = None, **_):
        super().__init__(master)
        self._binding_tracker = BindingTracker()

        # Configurar fonte para CTk
        header_font = ("Arial", 16, "bold")  # CTk aceita tuplas

        top = ctk.CTkFrame(self, fg_color="transparent")
        center = ctk.CTkFrame(self, fg_color="transparent")

        top.pack(fill="x", padx=10, pady=(10, 0))
        center.pack(expand=True, fill="both")

        header = ctk.CTkLabel(center, text=self.title, font=header_font)
        desc = ctk.CTkLabel(center, text="Funcionalidade em desenvolvimento.")
        btn = make_btn(center, text="Voltar")

        header.pack(pady=(0, 6))
        desc.pack(pady=(0, 16))
        btn.pack()

        if callable(on_back):
            btn.configure(command=on_back)
            self._binding_tracker.bind_all(self, "<Escape>", lambda e: on_back())

        # Cleanup: remover bind_all global quando este frame for destruído (Fase 13)
        self.bind("<Destroy>", self._on_placeholder_destroy)

        try:
            self.master.pack_propagate(False)  # pyright: ignore[reportAttributeAccessIssue]
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao desabilitar pack_propagate: %s", exc)

    def _on_placeholder_destroy(self, event: tk.Event) -> None:  # type: ignore[override]
        """Remove bind_all global ao destruir (Fase 13)."""
        if event.widget is not self:
            return
        self._binding_tracker.unbind_all()


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

        class ComingSoonScreen(ctk.CTkFrame):  # type: ignore[misc]
            def __init__(self, master=None, text: str = "Em breve...", **kwargs):
                super().__init__(master, **kwargs)
                container = ctk.CTkFrame(self)
                container.pack(fill="both", expand=True, padx=24, pady=24)
                title = ctk.CTkLabel(container, text=text)
                title.pack(anchor="center", pady=8)


try:
    __all__.append("ComingSoonScreen")  # type: ignore[attr-defined]
except Exception as exc:  # noqa: BLE001
    _log.debug("Falha ao adicionar ComingSoonScreen a __all__: %s", exc)
