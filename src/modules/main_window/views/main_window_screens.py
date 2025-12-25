"""Funções de navegação entre telas do MainWindow.

Extrai a lógica de show_* methods para reduzir complexidade do main_window.py.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.modules.main_window.views.main_window import MainWindow

log = logging.getLogger(__name__)


def show_hub_screen(app: "MainWindow") -> Any:
    """Mostra o hub inicial.

    Args:
        app: Instância do MainWindow

    Returns:
        Frame do hub
    """
    # Usar router para navegação
    frame = app._router.show("hub")

    # Side-effects: atualizar contador e topbar
    try:
        app.refresh_clients_count_async()
    except Exception as exc:  # noqa: BLE001
        log.debug("refresh_clients_count_async failed in hub: %s", exc)

    try:
        app._update_topbar_state(frame)
    except Exception as exc:  # noqa: BLE001
        log.debug("_update_topbar_state failed: %s", exc)

    # Atualizar nav._current para compatibilidade
    try:
        app.nav._current = frame
    except Exception as exc:  # noqa: BLE001
        log.debug("set app.nav._current failed: %s", exc)

    return frame


def show_main_screen(app: "MainWindow") -> Any:
    """Mostra a tela principal de clientes.

    Args:
        app: Instância do MainWindow

    Returns:
        Frame da tela principal
    """
    # Usar router para navegação
    frame = app._router.show("main")

    # Side-effects: marcar como loaded e atualizar topbar
    app._main_loaded = True

    try:
        app._update_topbar_state(frame)
    except Exception as exc:  # noqa: BLE001
        log.debug("_update_topbar_state failed: %s", exc)

    # Atualizar nav._current para compatibilidade
    try:
        app.nav._current = frame
    except Exception as exc:  # noqa: BLE001
        log.debug("set app.nav._current failed: %s", exc)

    return frame


def show_passwords_screen(app: "MainWindow") -> Any:
    """Mostra a tela de gerenciamento de senhas.

    Args:
        app: Instância do MainWindow

    Returns:
        Frame da tela de senhas
    """
    # Usar router para navegação
    frame = app._router.show("passwords")

    # Side-effects: atualizar topbar
    try:
        app._update_topbar_state(frame)
    except Exception as exc:  # noqa: BLE001
        log.debug("_update_topbar_state failed: %s", exc)

    # Atualizar nav._current para compatibilidade
    try:
        app.nav._current = frame
    except Exception as exc:  # noqa: BLE001
        log.debug("set app.nav._current failed: %s", exc)

    return frame


def show_cashflow_screen(app: "MainWindow") -> Any:
    """Mostra a tela de fluxo de caixa.

    Args:
        app: Instância do MainWindow

    Returns:
        Frame da tela de cashflow
    """
    # Usar router para navegação
    frame = app._router.show("cashflow")

    # Side-effects: atualizar topbar
    try:
        app._update_topbar_state(frame)
    except Exception as exc:  # noqa: BLE001
        log.debug("_update_topbar_state failed: %s", exc)

    # Atualizar nav._current para compatibilidade
    try:
        app.nav._current = frame
    except Exception as exc:  # noqa: BLE001
        log.debug("set app.nav._current failed: %s", exc)

    return frame


def show_sites_screen(app: "MainWindow") -> Any:
    """Mostra a tela de gerenciamento de sites.

    Args:
        app: Instância do MainWindow

    Returns:
        Frame da tela de sites
    """
    # Usar router para navegação
    frame = app._router.show("sites")

    # Side-effects: atualizar topbar
    try:
        app._update_topbar_state(frame)
    except Exception as exc:  # noqa: BLE001
        log.debug("_update_topbar_state failed: %s", exc)

    # Atualizar nav._current para compatibilidade
    try:
        app.nav._current = frame
    except Exception as exc:  # noqa: BLE001
        log.debug("set app.nav._current failed: %s", exc)

    return frame
