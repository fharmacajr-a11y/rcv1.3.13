from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Optional, TYPE_CHECKING

from infra.supabase_client import get_cloud_status_for_ui, get_supabase_state

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..views.main_screen import MainScreenFrame


@dataclass
class ClientesConnectivityController:
    """
    Controla o monitoramento de conectividade Supabase/Cloud para a tela de Clientes.

    Agenda checagens via Tk.after, consulta estado da nuvem e aplica efeitos na UI
    através do frame.
    """

    frame: "MainScreenFrame"
    _job_id: Optional[str] = None
    _running: bool = False
    _interval_ms: int = 5000

    def start(self) -> None:
        """Inicia o monitor se ainda não estiver rodando."""
        if self._running:
            return
        self._running = True
        try:
            self._job_id = self.frame.after(2000, self._tick)
        except Exception as exc:  # noqa: BLE001
            self._running = False
            logger.warning("Falha ao consultar estado da nuvem: %s", exc)
            logger.debug("Falha ao agendar monitor de conectividade: %s", exc)

    def stop(self) -> None:
        """Cancela o monitor agendado, se houver."""
        if not self._running:
            return
        self._running = False
        if self._job_id is not None:
            try:
                self.frame.after_cancel(self._job_id)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Falha ao cancelar monitor de conectividade: %s", exc)
            self._job_id = None

    def _schedule_next(self) -> None:
        if not self._running:
            return
        try:
            self._job_id = self.frame.after(self._interval_ms, self._tick)
        except Exception as exc:  # noqa: BLE001
            self._job_id = None
            logger.debug("Falha ao reagendar verificação de conectividade: %s", exc)

    def _tick(self) -> None:
        """Executa uma checagem de conectividade e agenda a próxima."""
        if not self._running:
            return
        try:
            state, description = get_supabase_state()
            text, style, tooltip = get_cloud_status_for_ui()
            self.frame._apply_connectivity_state(state, description, text, style, tooltip)
        except Exception as exc:  # noqa: BLE001
            # Em caso de falha, mantem proximo tick agendado
            logger.warning("Falha ao consultar estado da nuvem: %s", exc)
        finally:
            self._schedule_next()
