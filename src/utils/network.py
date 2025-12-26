"""Utilidades de conectividade para modo cloud-only, com checagem e alerta GUI."""

from __future__ import annotations

import logging
import os
import socket
import urllib.request
from typing import Final
from urllib.error import HTTPError, URLError

logger = logging.getLogger(__name__)


SOCKET_TEST_HOST = ("8.8.8.8", 53)

# Flag global para log único de WinError 10013
_winerror_10013_logged = False


def _socket_check(timeout: float) -> bool:
    """Tenta abrir socket TCP para o host de teste; retorna True em sucesso, False em erro."""
    try:
        with socket.create_connection(SOCKET_TEST_HOST, timeout=timeout):
            return True
    except OSError as exc:
        global _winerror_10013_logged
        # Se for WinError 10013, é típico de firewall/VPN bloqueando esse tipo de socket.
        if getattr(exc, "winerror", None) == 10013:
            if not _winerror_10013_logged:
                logger.debug(
                    "Internet connectivity check blocked by local policy (WinError 10013). Will try HTTP fallback."
                )
                _winerror_10013_logged = True
        else:
            logger.warning("Internet connectivity check failed (socket): %s", exc)
        return False


def _http_check(timeout: float) -> bool:
    """Realiza HEAD em URLs whitelisted para confirmar conectividade HTTP (fallback)."""
    # Lista simples de URLs genericas para teste de conectividade HTTP.
    # Usar apenas sites publicos amplamente alcancaveis; todos via HTTPS.
    test_urls = [
        "https://clients3.google.com/generate_204",
        "https://www.google.com",
        "https://www.cloudflare.com",
    ]

    for url in test_urls:
        try:
            req = urllib.request.Request(url, method="HEAD")
            # URLs são constantes/whitelist, sem entrada do usuário (safe)
            with urllib.request.urlopen(req, timeout=timeout):  # nosec B310
                # Se conseguimos obter qualquer resposta HTTP, consideramos que há internet.
                return True
        except (URLError, HTTPError, OSError) as exc:
            logger.debug("HTTP connectivity check to %s failed: %s", url, exc)

    return False


def check_internet_connectivity(timeout: float = 1.0) -> bool:
    """Verifica conectividade tentando socket e fallback HTTP, respeitando RC_NO_NET_CHECK."""
    # Skip check if RC_NO_NET_CHECK=1 (for testing)
    if os.getenv("RC_NO_NET_CHECK") == "1":
        logger.debug("Network check bypassed (RC_NO_NET_CHECK=1)")
        return True

    # 1) Tentativa via socket (comportamento antigo)
    if _socket_check(timeout=timeout):
        logger.info("Internet connectivity confirmed (cloud-only mode)")
        return True

    # 2) Fallback HTTP
    # Timeout agressivo para não atrasar startup (PERF-001)
    http_timeout = max(timeout, 2.0)
    if _http_check(timeout=http_timeout):
        logger.info("Internet connectivity confirmed via HTTP fallback (cloud-only mode)")
        return True

    # 3) Se ambos falharem, mantém o comportamento anterior (sem internet)
    logger.error("Internet unavailable in cloud-only mode")
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
        return True

    # No internet in cloud-only mode - show alert
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
                (
                    "Este aplicativo requer conexão com a internet para funcionar.\n\n"
                    "Verifique sua conexão e tente novamente."
                ),
                icon="warning",
            )

            root.destroy()

            # If user clicked Cancel, return False
            return result if result else False

        except Exception as e:
            logger.warning("Failed to show internet alert dialog: %s", e)

    return False


__all__: Final = ["check_internet_connectivity", "require_internet_or_alert"]
