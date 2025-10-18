# -*- coding: utf-8 -*-
"""Status monitor controller used by the Tkinter App."""

from __future__ import annotations

import threading
from typing import Any, Callable, Optional

try:  # pragma: no cover - import optional worker
    from infra.net_status import NetStatusWorker  # type: ignore
except Exception:  # pragma: no cover
    NetStatusWorker = None  # type: ignore[misc]

try:
    from infra.net_status import Status, probe
except Exception:  # pragma: no cover
    from app_status import Status, probe  # type: ignore

from shared.config.environment import cloud_only_default


class _FallbackNetStatusWorker:
    """Minimal worker that polls net status and notifies a callback."""

    def __init__(
        self,
        callback: Callable[[bool], None],
        *,
        interval_ms: int = 30_000,
    ) -> None:
        self._callback = callback
        self._interval = max(1.0, (interval_ms or 30_000) / 1000.0)
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="StatusMonitorWorker"
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                status = probe()
                is_online = status == Status.ONLINE
            except Exception:
                is_online = False
            try:
                self._callback(is_online)
            except Exception:
                pass
            if self._stop_event.wait(self._interval):
                break


if NetStatusWorker is None:
    NetStatusWorker = _FallbackNetStatusWorker  # type: ignore[assignment]


class StatusMonitor:
    """Orquestra texto da barra de status (ambiente + online/offline)."""

    def __init__(
        self,
        set_text: Callable[..., None],
        *,
        app_after: Callable[[int, Callable[[], None]], Any],
        interval_ms: int = 30_000,
    ) -> None:
        self._set_text = set_text
        self._after = app_after
        self._is_cloud = cloud_only_default()
        self._online: Optional[bool] = None
        self._interval_ms = interval_ms
        self._net: Optional[NetStatusWorker] = None

    # ---------- API pública ----------
    def start(self) -> None:
        if self._net is None:
            try:
                self._net = NetStatusWorker(callback=self._on_net_change, interval_ms=self._interval_ms)  # type: ignore[arg-type]
            except TypeError:  # pragma: no cover - accommodate different signatures
                self._net = NetStatusWorker(self._on_net_change)  # type: ignore[call-arg]
        if self._net:
            try:
                self._net.start()
            except Exception:
                pass
        self._post_update()

    def stop(self) -> None:
        try:
            if self._net:
                self._net.stop()  # type: ignore[call-arg]
        except Exception:
            pass
        finally:
            self._net = None

    def set_cloud_only(self, is_cloud: bool) -> None:
        self._is_cloud = bool(is_cloud)
        self._post_update()

    # ---------- Callbacks internos ----------
    def _on_net_change(self, is_online: bool) -> None:
        self._online = bool(is_online)
        self._post_update()

    def _post_update(self) -> None:
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
    def env_text(is_cloud: Optional[bool]) -> str:
        return "Nuvem" if is_cloud else "Local"

    @staticmethod
    def merge_status_text(env_label: str, is_online: Optional[bool]) -> str:
        if is_online is None:
            status_label = "verificando rede…"
        else:
            status_label = "online" if is_online else "offline"
        return f"{env_label} • {status_label}"
