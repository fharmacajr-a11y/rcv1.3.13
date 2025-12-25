"""Network status helpers for the Tkinter desktop application."""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Any

import yaml

from infra.net_status import Status, probe

log = logging.getLogger(__name__)

# Public attribute consumed by the UI during bootstrap.
status_text: str = "LOCAL"

DEFAULT_INTERVAL_MS = 30_000  # 30 seconds
DEFAULT_TIMEOUT = 2.0
CONFIG_PATH = Path("config.yml")
_STATUS_DOT = "\u25cf"  # Unicode bullet rendered by ttkbootstrap

# Cache structure: (path, mtime, (url, timeout, interval_ms))
ConfigValues = tuple[str, float, int]
ConfigCache = tuple[Path, float, ConfigValues] | None

_cfg_cache: ConfigCache = None


def _set_env_text(app: Any, text: str) -> None:
    """Update the environment text label while preserving existing user details."""
    try:
        if hasattr(app, "_merge_status_text"):
            app._merge_status_text(text)
        elif hasattr(app, "status_var_text"):
            app.status_var_text.set(text)
    except Exception as exc:
        log.warning("Falha ao propagar texto de ambiente: %s", exc, exc_info=True)


def _apply_status(app: Any, status: Status) -> None:
    """Apply the probe result to the UI (dot style, text and callbacks)."""
    try:
        if hasattr(app, "winfo_exists") and not app.winfo_exists():
            return
    except Exception as exc:
        log.warning("Erro ao verificar existência da janela: %s", exc)
        return

    # Always show the status dot
    try:
        if hasattr(app, "status_var_dot"):
            app.status_var_dot.set(_STATUS_DOT)
        if hasattr(app, "status_dot"):
            style = "warning"
            env_text = "LOCAL"
            if status == Status.ONLINE:
                style = "success"
                env_text = "ONLINE"
            elif status == Status.OFFLINE:
                style = "danger"
                env_text = "OFFLINE"
            app.status_dot.configure(bootstyle=style)
            _set_env_text(app, env_text)
        else:
            _set_env_text(app, "ONLINE" if status == Status.ONLINE else "OFFLINE")
    except Exception as exc:
        log.warning("Falha ao atualizar widgets de status: %s", exc, exc_info=True)

    try:
        callback = getattr(app, "on_net_status_change", None)
        if callable(callback):
            callback(status)
    except Exception as exc:
        log.warning("Hook on_net_status_change falhou: %s", exc, exc_info=True)


def _read_cfg_from_disk() -> ConfigValues:
    """Read config.yml (if available) returning (url, timeout, interval_ms)."""
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as file:
            cfg = yaml.safe_load(file) or {}
        probe_opts = cfg.get("status_probe") or {}
        url = str(probe_opts.get("url") or "")
        timeout = float(probe_opts.get("timeout_seconds", DEFAULT_TIMEOUT))
        interval_ms = int(probe_opts.get("interval_ms", DEFAULT_INTERVAL_MS))
        return url, timeout, interval_ms
    except Exception as exc:
        log.warning("Falha ao ler configuração do disco: %s", exc)
        return "", DEFAULT_TIMEOUT, DEFAULT_INTERVAL_MS


def _get_cfg() -> ConfigValues:
    """Return cached probe configuration using file mtime as invalidation token."""
    global _cfg_cache
    try:
        mtime = CONFIG_PATH.stat().st_mtime
    except Exception as exc:
        log.debug("Config file não encontrado ou inacessível: %s", exc)
        mtime = -1.0

    if _cfg_cache and _cfg_cache[0] == CONFIG_PATH and _cfg_cache[1] == mtime:
        return _cfg_cache[2]

    values = _read_cfg_from_disk()
    _cfg_cache = (CONFIG_PATH, mtime, values)
    return values


def update_net_status(app: Any, interval_ms: int | None = None) -> None:
    """
    Start a background worker that probes network connectivity and updates the UI.

    The first probe is executed synchronously so the status indicator is updated as soon
    as the window is shown. Subsequent probes run in a daemon thread with throttled UI
    updates to avoid overwhelming Tkinter.
    """
    if getattr(app, "_net_worker_started", False):
        return

    app._net_worker_started = True
    app._net_last_ui = 0.0
    app._net_last_status = None  # type: ignore[assignment]

    url, timeout, cfg_interval_ms = _get_cfg()
    try:
        first_status = probe(url, timeout)
    except Exception as exc:
        log.warning("Primeira tentativa de probe falhou: %s", exc)
        first_status = Status.LOCAL

    try:
        app.after(0, lambda s=first_status: _apply_status(app, s))
    except Exception as exc:
        log.warning("Falha ao agendar atualização inicial de status: %s", exc, exc_info=True)

    def worker() -> None:
        log.info("NetStatusWorker started")
        while True:
            url_, timeout_, cfg_interval_ms_ = _get_cfg()
            eff_interval_ms = int(interval_ms or cfg_interval_ms_ or DEFAULT_INTERVAL_MS)
            eff_interval_s = max(1.0, eff_interval_ms / 1000.0)

            try:
                current_status = probe(url_, timeout_)
            except Exception as exc:
                log.debug("Probe de rede falhou: %s", exc)
                current_status = Status.LOCAL

            now = time.time()
            last_ui = getattr(app, "_net_last_ui", 0.0)
            previous_status = getattr(app, "_net_last_status", None)
            throttle = (now - last_ui) >= 0.33

            if throttle or current_status != previous_status:
                try:
                    if hasattr(app, "winfo_exists") and app.winfo_exists():
                        app._net_last_ui = now
                        app._net_last_status = current_status
                        app.after(0, lambda s=current_status: _apply_status(app, s))
                except Exception as exc:
                    log.warning("Falha ao despachar atualização de status: %s", exc, exc_info=True)

            time.sleep(eff_interval_s)

    thread = threading.Thread(target=worker, daemon=True, name="NetStatusWorker")
    thread.start()
    app._net_worker_thread = thread


__all__ = ["status_text", "update_net_status"]
