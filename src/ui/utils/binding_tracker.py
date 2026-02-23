"""BindingTracker — helper para rastrear e limpar bindings Tkinter.

Fase 13: Evitar callbacks globais pendurados após destroy de widgets/dialogs.

Uso básico::

    class MyFrame(tk.Frame):
        def __init__(self, master):
            super().__init__(master)
            self._bt = BindingTracker()
            self._bt.bind(self, "<KeyPress>", self._on_key)
            self._bt.bind_all(self, "<MouseWheel>", self._on_wheel)
            self.bind("<Destroy>", self._on_destroy)

        def _on_destroy(self, event):
            if event.widget is not self:
                return
            self._bt.unbind_all()
"""

from __future__ import annotations

import logging
import tkinter as tk
from typing import Any

_log = logging.getLogger(__name__)


class BindingTracker:
    """Rastreia bind/bind_all/bind_class e os desfaz em unbind_all().

    Todos os métodos são idempotentes: chamar unbind_all() mais de uma vez
    não causa erros.
    """

    def __init__(self) -> None:
        self._entries: list[tuple[Any, ...]] = []

    # ------------------------------------------------------------------
    # Registro
    # ------------------------------------------------------------------

    def bind(self, widget: Any, sequence: str, func: Any, add: str = "+") -> str:
        """Equivalente a ``widget.bind(sequence, func, add)``; armazena funcid."""
        funcid: str = widget.bind(sequence, func, add)
        self._entries.append(("widget", widget, sequence, funcid))
        return funcid

    def bind_all(self, widget: Any, sequence: str, func: Any, add: str = "+") -> str:
        """Equivalente a ``widget.bind_all(sequence, func, add)``; armazena para cleanup.

        Nota: ``unbind_all()`` chamará ``widget.unbind_all(sequence)`` que remove
        *todos* os handlers globais daquele sequence.  Só usado quando não há
        múltiplos consumidores simultâneos do mesmo sequence global.
        """
        funcid: str = widget.bind_all(sequence, func, add)
        self._entries.append(("all", widget, sequence))
        return funcid

    def bind_class(
        self,
        widget: Any,
        classname: str,
        sequence: str,
        func: Any,
        add: str = "+",
    ) -> str:
        """Equivalente a ``widget.bind_class(classname, sequence, func, add)``."""
        funcid: str = widget.bind_class(classname, sequence, func, add)
        self._entries.append(("class", widget, classname, sequence))
        return funcid

    # ------------------------------------------------------------------
    # Limpeza
    # ------------------------------------------------------------------

    def unbind_all(self) -> None:
        """Remove todos os bindings registrados (idempotente, silencia TclError)."""
        for entry in reversed(self._entries):
            kind = entry[0]
            try:
                if kind == "widget":
                    _, widget, sequence, funcid = entry
                    widget.unbind(sequence, funcid)
                elif kind == "all":
                    _, widget, sequence = entry
                    widget.unbind_all(sequence)
                elif kind == "class":
                    _, widget, classname, sequence = entry
                    widget.unbind_class(classname, sequence)
            except tk.TclError:
                pass
            except Exception:  # noqa: BLE001
                _log.debug(
                    "BindingTracker: erro ao desfazer binding %s",
                    entry,
                    exc_info=True,
                )
        self._entries.clear()

    def __len__(self) -> int:
        return len(self._entries)


__all__ = ["BindingTracker"]
