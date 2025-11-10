"""Global exception handling utilities.

Provides a global exception hook that logs errors and optionally shows user-friendly
GUI dialogs, with suppression support for testing/CI environments.
"""

from __future__ import annotations

import logging
import os
import sys
import traceback
from typing import Any, Callable, Final

logger = logging.getLogger(__name__)


def install_global_exception_hook() -> None:
    """Install a global exception hook for unhandled exceptions.

    Behavior:
    - Always logs the exception with full traceback
    - Shows GUI error dialog unless RC_NO_GUI_ERRORS=1 or running in test mode
    - Preserves original excepthook chain
    """
    original_hook = sys.excepthook

    def exception_hook(
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_traceback: Any,
    ) -> None:
        """Handle uncaught exceptions."""
        # Log the exception
        logger.critical(
            "Unhandled exception",
            exc_info=(exc_type, exc_value, exc_traceback),
        )

        # Check if we should suppress GUI errors
        no_gui = os.getenv("RC_NO_GUI_ERRORS") == "1"

        if not no_gui:
            try:
                # Only import tkinter if we need it (avoid import in tests)
                import tkinter as tk
                from tkinter import messagebox

                # Check if we can show GUI (main loop exists)
                try:
                    root = tk._default_root  # type: ignore[attr-defined]
                    can_show_gui = root is not None
                except Exception:
                    can_show_gui = False

                if can_show_gui:
                    error_msg = f"{exc_type.__name__}: {exc_value}"
                    messagebox.showerror(
                        "Erro Inesperado",
                        f"Ocorreu um erro inesperado:\n\n{error_msg}\n\n"
                        "Consulte os logs para mais detalhes.",
                    )
            except Exception as e:
                # If GUI fails, just log it
                logger.warning("Failed to show GUI error dialog: %s", e)

        # Call original hook
        original_hook(exc_type, exc_value, exc_traceback)

    sys.excepthook = exception_hook


def uninstall_global_exception_hook() -> None:
    """Restore the original exception hook.

    Useful for testing or cleanup.
    """
    sys.excepthook = sys.__excepthook__


__all__: Final = ["install_global_exception_hook", "uninstall_global_exception_hook"]
