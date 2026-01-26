# -*- coding: utf-8 -*-
"""Global Tkinter Exception Handler - Captura exceções do callback Tkinter.

Hook para report_callback_exception que loga com stacktrace completo
e opcionalmente mostra messagebox em modo desenvolvimento.
"""

from __future__ import annotations

import logging
import os
import traceback
from tkinter import messagebox
from typing import Any

log = logging.getLogger(__name__)

# Modo dev: mostrar messagebox para exceções (além de log)
DEV_MODE = os.getenv("RC_DEBUG_TK_EXCEPTIONS", "0") == "1"


def install_global_exception_handler(tk_root: Any) -> None:
    """Instala handler global para exceções do Tkinter.

    Args:
        tk_root: Instância raiz do Tkinter (Tk ou CTk)

    Usage:
        app = ctk.CTk()
        install_global_exception_handler(app)
    """
    original_handler = getattr(tk_root, "report_callback_exception", None)

    def _handle_exception(exc_type: type, exc_value: BaseException, exc_tb: Any) -> None:
        """Handler customizado de exceções do Tkinter."""
        # Formatar stacktrace completo
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_tb)
        tb_text = "".join(tb_lines)

        # Log completo
        log.error(
            "[Tkinter Exception] %s: %s\n%s",
            exc_type.__name__,
            exc_value,
            tb_text,
        )

        # Em modo dev, mostrar messagebox
        if DEV_MODE:
            try:
                # Truncar stacktrace para não sobrecarregar messagebox
                short_tb = "".join(tb_lines[-10:])  # Últimas 10 linhas
                messagebox.showerror(
                    "Erro Interno (Dev Mode)",
                    f"{exc_type.__name__}: {exc_value}\n\n"
                    f"Últimas linhas do stacktrace:\n{short_tb}\n\n"
                    f"Veja o log completo no console.",
                    parent=tk_root,
                )
            except Exception:
                # Não falhar se messagebox der erro
                pass

        # Chamar handler original se existir
        if original_handler and callable(original_handler):
            try:
                original_handler(exc_type, exc_value, exc_tb)
            except Exception:
                pass

    # Instalar handler
    tk_root.report_callback_exception = _handle_exception
    log.info(
        "✅ [TkExceptionHandler] Instalado (dev_mode=%s, env RC_DEBUG_TK_EXCEPTIONS=%s)",
        DEV_MODE,
        os.getenv("RC_DEBUG_TK_EXCEPTIONS", "0"),
    )


__all__ = ["install_global_exception_handler", "DEV_MODE"]
