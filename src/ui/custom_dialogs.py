"""Diálogos customizados legados.

NOTA: ``show_info`` e ``ask_ok_cancel`` agora delegam para
``src.ui.dialogs.rc_dialogs``, que é o padrão canônico do app.
Use ``rc_dialogs`` diretamente em código novo.

``_apply_icon`` permanece aqui como helper de ícone standalone.
"""

from __future__ import annotations

import logging
import os
import tkinter as tk
from typing import Any

from src.utils.resource_path import resource_path

logger = logging.getLogger(__name__)


def _apply_icon(window: tk.Toplevel) -> None:
    """Aplica o ícone rc.ico ao toplevel, se disponível."""
    try:
        icon_path = resource_path("rc.ico")
        if not os.path.exists(icon_path):
            return
        try:
            window.iconbitmap(icon_path)
            return
        except tk.TclError:
            # FIX: Fallback deve usar rc.png (PhotoImage não funciona com .ico no Windows)
            try:
                png_path = resource_path("rc.png")
                if os.path.exists(png_path):
                    img = tk.PhotoImage(file=png_path)
                    window.iconphoto(True, img)
            except tk.TclError as inner_exc:
                logger.debug("Falha ao aplicar iconphoto: %s", inner_exc)
    except (OSError, tk.TclError) as exc:
        logger.debug("Falha ao configurar icone do dialogo: %s", exc)


# ---------------------------------------------------------------------------
# Wrappers legados — delegam para rc_dialogs (padrão canônico)
# ---------------------------------------------------------------------------


def show_info(parent: Any, title: str, message: str) -> None:
    """Mostra diálogo de informação. Delega para ``rc_dialogs.show_info``."""
    from src.ui.dialogs.rc_dialogs import show_info as _rc_show_info

    _rc_show_info(parent, title, message)


def ask_ok_cancel(parent: Any, title: str, message: str) -> bool:
    """Mostra diálogo Sim/Não. Delega para ``rc_dialogs.ask_yes_no``."""
    from src.ui.dialogs.rc_dialogs import ask_yes_no as _rc_ask_yes_no

    return _rc_ask_yes_no(parent, title, message)
