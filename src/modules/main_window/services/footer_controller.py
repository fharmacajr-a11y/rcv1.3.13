# -*- coding: utf-8 -*-
"""
FooterController - Gerenciador de estado do rodapé (StatusFooter).

Solução para o problema de timing no layout em fases:
- Estado persiste antes do widget existir (skeleton phase)
- Aplicação acontece via root.after(0) quando widget é bindado (deferred phase)
- Thread-safe: todas as atualizações vão pela main thread

FASE 5A FIX: Garantir que user/cloud nunca se percam mesmo com deferred layout.
"""

from __future__ import annotations

import logging
import tkinter as tk
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from src.ui.status_footer import StatusFooter

log = logging.getLogger("app_gui.footer_controller")


class FooterController:
    """Controlador de estado do StatusFooter com apply assíncrono via after(0)."""

    def __init__(self, root: tk.Tk | tk.Misc):
        """
        Inicializa o controller com referência ao root (para after).

        Args:
            root: Instância do Tk/CTk root para agendar updates via after(0)
        """
        self._root = root
        self._footer_widget: Optional[StatusFooter] = None

        # Estado atual (fonte da verdade)
        self._user_email: str = "-"
        self._cloud_status: str = "UNKNOWN"

        log.info("FooterController criado (estado inicial: user=-, cloud=UNKNOWN)")

    def bind_footer(self, footer_widget: StatusFooter) -> None:
        """
        Vincula o widget StatusFooter e aplica estado atual.

        Chamado pelo layout deferred após criar o footer widget.

        Args:
            footer_widget: Instância de StatusFooter a ser controlada
        """
        self._footer_widget = footer_widget
        log.info("FooterController: footer widget bindado, aplicando estado...")
        # Aplicar estado imediatamente (já estamos no deferred = main thread)
        self._apply_now()

    def set_user(self, email: str | None) -> None:
        """
        Atualiza o email do usuário e agenda apply no footer.

        Args:
            email: Email do usuário ou None para "-"
        """
        self._user_email = email or "-"
        log.debug(f"FooterController.set_user: {self._user_email}")
        self._apply_async()

    def set_cloud(self, status: str) -> None:
        """
        Atualiza o status da nuvem e agenda apply no footer.

        Args:
            status: Status da nuvem ("ONLINE", "OFFLINE", "UNKNOWN", etc)
        """
        self._cloud_status = (status or "UNKNOWN").upper()
        log.debug(f"FooterController.set_cloud: {self._cloud_status}")
        self._apply_async()

    def _apply_async(self) -> None:
        """Agenda aplicação do estado via root.after(0) (thread-safe)."""
        try:
            self._root.after(0, self._apply_now)
        except Exception as exc:  # noqa: BLE001
            log.debug(f"FooterController: falha ao agendar apply: {exc}")

    def _apply_now(self) -> None:
        """Aplica estado atual no widget (chamado via after ou diretamente no bind)."""
        if self._footer_widget is None:
            log.debug("FooterController: widget ainda não bindado, estado guardado")
            return

        try:
            self._footer_widget.set_user(self._user_email)
            self._footer_widget.set_cloud(self._cloud_status)
            log.debug(f"FooterController: estado aplicado (user={self._user_email}, cloud={self._cloud_status})")
        except Exception as exc:  # noqa: BLE001
            log.debug(f"FooterController: falha ao aplicar estado: {exc}")
