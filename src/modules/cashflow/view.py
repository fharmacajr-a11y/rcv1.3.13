"""View principal do módulo Fluxo de Caixa.

Expõe `CashflowFrame` baseado em Frame (sem Toplevel) e mantém um
shim `open_cashflow_window` para compatibilidade, redirecionando
para a tela integrada via NavigationController quando possível.
"""

from __future__ import annotations

import logging
from typing import Any

from src.modules.cashflow.views.fluxo_caixa_frame import CashflowFrame  # noqa: F401

logger = logging.getLogger(__name__)


def open_cashflow_window(master: Any) -> None:
    """Shim legado: delega para a navegação interna se disponível."""
    try:
        if hasattr(master, "show_cashflow_screen"):
            master.show_cashflow_screen()
        elif hasattr(master, "navigate_to"):
            master.navigate_to("cashflow")
    except Exception as exc:  # noqa: BLE001
        logger.debug("Falha ao delegar abertura do fluxo de caixa: %s", exc)
