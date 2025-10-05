# app_status.py
from __future__ import annotations

import os
import time
import yaml
import threading
import logging
from typing import Tuple

from infra.net_status import probe, Status

log = logging.getLogger(__name__)

DEFAULT_INTERVAL_MS = 30000  # 30s
DEFAULT_TIMEOUT = 2.0
CONFIG_PATH = "config.yml"

# ------------------------- helpers de UI -------------------------
def _set_env(app, text: str):
    """Define o ambiente no rodapé preservando o usuário, se disponível."""
    try:
        if hasattr(app, "_merge_status_text"):
            app._merge_status_text(text)
        else:
            app.status_var_text.set(text)
    except Exception:
        try:
            app.status_var_text.set(text)
        except Exception:
            pass

def _apply_status(app, st: Status):
    if not getattr(app, "winfo_exists", None):
        return
    try:
        if not app.winfo_exists():
            return
    except Exception:
        return

    try:
        # mantém o ponto sempre visível; estilo muda pela rede
        try:
            app.status_var_dot.set("●")
        except Exception:
            pass

        if st == Status.ONLINE:
            _set_env(app, "ONLINE")
            app.status_dot.configure(bootstyle="success")
        elif st == Status.OFFLINE:
            _set_env(app, "OFFLINE")
            app.status_dot.configure(bootstyle="danger")
        else:
            _set_env(app, "LOCAL")
            app.status_dot.configure(bootstyle="warning")
    except Exception:
        pass

# ------------------------- cache de config.yml -------------------------
_cfg_cache: Tuple[str, float, Tuple[str, float, int]] | None = None
# formato: (path, mtime, (url, timeout, interval_ms))

def _read_cfg_from_disk() -> Tuple[str, float, int]:
    """Lê config.yml (ou defaults) sem cache."""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        sp = cfg.get("status_probe") or {}
        url = str(sp.get("url", "") or "")
        timeout = float(sp.get("timeout_seconds", DEFAULT_TIMEOUT))
        interval_ms = int(sp.get("interval_ms", DEFAULT_INTERVAL_MS))
        return url, timeout, interval_ms
    except Exception:
        return "", DEFAULT_TIMEOUT, DEFAULT_INTERVAL_MS

def _get_cfg() -> Tuple[str, float, int]:
    """Retorna (url, timeout, interval_ms) com cache por mtime."""
    global _cfg_cache
    try:
        mtime = os.path.getmtime(CONFIG_PATH) if os.path.exists(CONFIG_PATH) else -1.0
    except Exception:
        mtime = -1.0

    if _cfg_cache and _cfg_cache[0] == CONFIG_PATH and _cfg_cache[1] == mtime:
        return _cfg_cache[2]

    vals = _read_cfg_from_disk()
    _cfg_cache = (CONFIG_PATH, mtime, vals)
    return vals

# ------------------------- worker único + throttle -------------------------
def update_net_status(app, interval_ms: int | None = None):
    """
    Inicia (uma vez) um worker de status de rede e agenda updates na UI.
    - Evita spawn de threads por intervalo (apenas 1 daemon).
    - Throttle de updates na UI (~3/s) e evita updates redundantes quando o status não muda.
    - Respeita config.yml com cache por mtime; permite override via `interval_ms`.
    """
    # já rodando?
    if getattr(app, "_net_worker_started", False):
        return

    app._net_worker_started = True
    app._net_last_ui = 0.0
    app._net_last_status = None  # type: ignore[assignment]

    def _safe_after_apply(status: Status):
        try:
            if app.winfo_exists():
                app.after(0, lambda s=status: _apply_status(app, s))
        except Exception:
            pass

    def worker():
        log.info("NetStatusWorker: iniciado (daemon)")
        while True:
            # carrega config (com cache)
            url, timeout, cfg_interval_ms = _get_cfg()
            eff_interval_ms = int(interval_ms or cfg_interval_ms or DEFAULT_INTERVAL_MS)
            eff_interval_s = max(1.0, eff_interval_ms / 1000.0)

            # mede status
            st = Status.LOCAL
            try:
                st = probe(url, timeout)
            except Exception:
                # probe falhou -> considera LOCAL (degradação suave)
                st = Status.LOCAL

            # throttle de UI e evita updates redundantes
            now = time.time()
            do_throttle = (now - getattr(app, "_net_last_ui", 0.0)) >= 0.33
            last_st = getattr(app, "_net_last_status", None)

            if do_throttle or st != last_st:
                try:
                    if app.winfo_exists():
                        app._net_last_ui = now
                        app._net_last_status = st
                        app.after(0, lambda s=st: _apply_status(app, s))
                except Exception:
                    # janela pode ter sido fechada — como daemon, terminamos quando o processo sair
                    pass

            time.sleep(eff_interval_s)

    t = threading.Thread(target=worker, daemon=True, name="NetStatusWorker")
    t.start()
    app._net_worker_thread = t
