from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger("app_gui")

__all__ = ["tk_report"]


def tk_report(exc: Any, val: Any, tb_: Any) -> None:
    log.exception("Excecao no Tkinter callback", exc_info=(exc, val, tb_))

