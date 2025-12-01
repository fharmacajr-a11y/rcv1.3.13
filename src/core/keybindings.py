# application/keybindings.py
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional

log = logging.getLogger(__name__)


def _wrap(fn: Optional[Callable[..., Any]]) -> Callable[[Any], str]:
    """Encapsula um handler de atalho, protegendo contra exceções e devolvendo 'break'."""

    def _h(_event: Any = None) -> str:  # Renomeado para _event para indicar parâmetro não usado
        if callable(fn):
            try:
                fn()
            except Exception as exc:
                log.warning("Atalho falhou", exc_info=exc)
        return "break"

    return _h


def bind_global_shortcuts(root: Any, handlers: Dict[str, Callable[[], None]]) -> None:
    """Registra os atalhos globais (quit, refresh, new, etc.) no root informado."""
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
