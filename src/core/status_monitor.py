# -*- coding: utf-8 -*-
"""Status monitor controller used by the Tkinter App."""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable

try:
    from src.infra.net_status import Status, probe
except Exception:  # pragma: no cover
    from src.core.status import Status, probe  # type: ignore

from src.config.environment import cloud_only_default

log = logging.getLogger(__name__)


class _NetStatusWorker:
    """
    Worker que consulta status de rede periodicamente e notifica callback.

    Callback recebe bool: is_online.
    """

    def __init__(
        self,
        callback: Callable[[bool], None],
        interval_ms: int = 30_000,
    ) -> None:
        self._callback: Callable[[bool], None] = callback
        self._interval_sec: float = max(1.0, float(interval_ms) / 1000.0)
        self._stop_event: threading.Event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="NetStatusWorker")
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)
        self._thread = None

    def _run(self) -> None:
        """Loop de sondagem que aplica callback enquanto não recebe sinal de parada."""
        while not self._stop_event.is_set():
            try:
                status = probe()
                is_online = status == Status.ONLINE
            except Exception as exc:
                log.debug("StatusMonitor: falha ao sondar rede", exc_info=exc)
                is_online = False
            try:
                self._callback(is_online)
            except Exception as exc:
                log.debug("StatusMonitor: callback de rede falhou", exc_info=exc)
            if self._stop_event.wait(self._interval_sec):
                break


class StatusMonitor:
    """
    Orquestra texto da barra de status (ambiente + online/offline).

    Args:
        set_text: Função que atualiza o texto de status na UI.
                  Pode aceitar (str) ou (str, bool).
        app_after: Agendador da UI thread (ex: Tk.after).
        interval_ms: Intervalo de verificação de rede em ms.
    """

    def __init__(
        self,
        set_text: Callable[..., None],
        *,
        app_after: Callable[[int, Callable[[], None]], Any],
        interval_ms: int = 30_000,
    ) -> None:
        self._set_text: Callable[..., None] = set_text
        self._after: Callable[[int, Callable[[], None]], Any] = app_after
        self._is_cloud: bool = cloud_only_default()
        self._online: bool | None = None
        self._interval_ms: int = interval_ms
        self._net: _NetStatusWorker | None = None

    # ---------- API pública ----------
    def start(self) -> None:
        """Inicia monitoramento de status de rede."""
        if self._net is None:
            self._net = _NetStatusWorker(callback=self._on_net_change, interval_ms=self._interval_ms)
        try:
            self._net.start()
        except Exception as exc:
            log.debug("StatusMonitor: falha ao iniciar worker de rede", exc_info=exc)
        self._post_update()

    def stop(self) -> None:
        """Para monitoramento de status de rede."""
        try:
            if self._net:
                self._net.stop()
        except Exception as exc:
            log.debug("StatusMonitor: falha ao parar worker de rede", exc_info=exc)
        finally:
            self._net = None

    def set_cloud_only(self, is_cloud: bool) -> None:
        """Define se está em modo cloud-only."""
        self._is_cloud = bool(is_cloud)
        self._post_update()

    def set_cloud_status(self, is_online: bool) -> None:
        """Define status da nuvem (online/offline) manualmente."""
        self._online = bool(is_online)
        self._post_update()

    # ---------- Callbacks internos ----------
    def _on_net_change(self, is_online: bool) -> None:
        """Callback do worker de rede."""
        self._online = bool(is_online)
        # Agendar atualização na UI thread
        try:
            self._after(0, self._post_update)
        except Exception:
            self._post_update()

    def _post_update(self) -> None:
        """Agenda (ou executa) a atualização do texto na UI thread."""
        text = self.merge_status_text(self.env_text(self._is_cloud), self._online)

        def _apply() -> None:
            try:
                self._set_text(text, self._online)
            except TypeError:
                self._set_text(text)  # type: ignore[misc]

        try:
            self._after(0, _apply)
        except Exception:
            _apply()

    # ---------- Helpers ----------
    @staticmethod
    def env_text(is_cloud: bool | None) -> str:
        return "Nuvem" if is_cloud else "Local"

    @staticmethod
    def merge_status_text(env_label: str, is_online: bool | None) -> str:
        """Gera texto de status sem incluir e-mail (apenas ambiente + online/offline)."""
        if is_online is None:
            status_label = "verificando rede…"
        else:
            status_label = "online" if is_online else "offline"
        return f"{env_label} • {status_label}"
