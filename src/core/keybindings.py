# application/keybindings.py
from __future__ import annotations
from typing import Callable, Optional, Dict, Any


def _wrap(fn: Optional[Callable[..., Any]]):
    def _h(_event=None):  # Renomeado para _event (prefixo _ indica não usado)
        if callable(fn):
            try:
                fn()
            except Exception:
                pass
        return "break"

    return _h


def bind_global_shortcuts(root, handlers: Dict[str, Callable[[], None]]) -> None:
    """
    handlers: mapeia nomes → callbacks já existentes no App.
      suportados por padrão:
        quit, refresh, new, edit, delete, upload, lixeira, subpastas, hub, find
    """
    b = root.bind_all
    b("<Control-q>", _wrap(handlers.get("quit")))
    b("<F5>", _wrap(handlers.get("refresh")))
    b("<Control-n>", _wrap(handlers.get("new")))
    b("<Control-e>", _wrap(handlers.get("edit")))
    b("<Delete>", _wrap(handlers.get("delete")))
    b("<Control-u>", _wrap(handlers.get("upload")))
    b("<Control-l>", _wrap(handlers.get("lixeira")))
    b("<Control-s>", _wrap(handlers.get("subpastas")))
    b("<Alt-Home>", _wrap(handlers.get("hub")))
    b("<Control-f>", _wrap(handlers.get("find")))
