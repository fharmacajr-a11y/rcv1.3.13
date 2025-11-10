"""Network connectivity utilities for cloud-only mode.

Provides internet connectivity checking with GUI alerts when running in cloud-only mode.
"""

from __future__ import annotations

import logging
import os
import socket
from typing import Final

logger = logging.getLogger(__name__)


def check_internet_connectivity(timeout: float = 2.0) -> bool:
    """Check if internet is available by attempting a socket connection.

    Uses DNS (8.8.8.8:53) as a lightweight check without sending HTTP traffic.

    Args:
        timeout: Connection timeout in seconds

    Returns:
        True if internet is available, False otherwise
    """
    # Skip check if RC_NO_NET_CHECK=1 (for testing)
    if os.getenv("RC_NO_NET_CHECK") == "1":
        logger.debug("Network check bypassed (RC_NO_NET_CHECK=1)")
        return True

    try:
        # Attempt connection to Google DNS
        sock = socket.create_connection(("8.8.8.8", 53), timeout=timeout)
        sock.close()
        return True
    except OSError as e:
        logger.warning("Internet connectivity check failed: %s", e)
        return False


def require_internet_or_alert() -> bool:
    """Check internet connectivity and show alert if unavailable in cloud-only mode.

    Only performs check if RC_NO_LOCAL_FS=1 (cloud-only mode).
    Shows a GUI alert if internet is unavailable.

    Returns:
        True if internet is available or not required, False if unavailable
    """
    # Only check in cloud-only mode
    is_cloud_only = os.getenv("RC_NO_LOCAL_FS") == "1"
    if not is_cloud_only:
        logger.debug("Not in cloud-only mode, skipping internet check")
        return True

    # Check connectivity
    if check_internet_connectivity():
        logger.info("Internet connectivity confirmed (cloud-only mode)")
        return True

    # No internet in cloud-only mode - show alert
    logger.error("Internet unavailable in cloud-only mode")

    # Show GUI alert unless RC_NO_GUI_ERRORS=1
    if os.getenv("RC_NO_GUI_ERRORS") != "1":
        try:
            import tkinter as tk
            from tkinter import messagebox

            # Create minimal root if needed
            root = tk.Tk()
            root.withdraw()

            result = messagebox.askokcancel(
                "Internet Necessária",
                "Este aplicativo requer conexão com a internet para funcionar.\n\n"
                "Verifique sua conexão e tente novamente.",
                icon="warning",
            )

            root.destroy()

            # If user clicked Cancel, return False
            return result if result else False

        except Exception as e:
            logger.warning("Failed to show internet alert dialog: %s", e)

    return False


__all__: Final = ["check_internet_connectivity", "require_internet_or_alert"]
