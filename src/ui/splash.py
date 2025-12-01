# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import os
import time
import tkinter as tk
from collections.abc import Callable
from typing import Optional

import ttkbootstrap as tb
from ttkbootstrap.constants import INFO

from src.utils.resource_path import resource_path
from src.version import get_version

_log = logging.getLogger(__name__)

SPLASH_MIN_DURATION_MS = 5000
SPLASH_PROGRESS_MAX = 100
SPLASH_PROGRESS_STEPS = 100
APP_VERSION = get_version()


def get_splash_progressbar_bootstyle() -> str:
    """Retorna o bootstyle configurado para a progressbar do splash."""
    return str(INFO)


def _find_logo_path() -> str | None:
    """
    Retorna o caminho do logo PNG, se existir, ou None se não encontrar.
    Procura por nomes comuns na raiz do app (rc_logo.png, rc.png).
    """

    def _safe_resource_path(name: str) -> str | None:
        try:
            return resource_path(name)
        except (OSError, ValueError) as exc:
            _log.debug("Falha ao resolver resource_path(%s): %s", name, exc)
            return None

    for name in ("rc_logo.png", "rc.png", "RC.png"):
        path = _safe_resource_path(name)
        if path and os.path.exists(path):
            return path

    return None


def _center_coords(screen_w: int, screen_h: int, w: int, h: int) -> tuple[int, int]:
    x = max((screen_w - w) // 2, 0)
    y = max((screen_h - h) // 2, 0)
    return x, y


def _compute_remaining_ms(created_at: float, now: float, min_duration_ms: int) -> int:
    """Calcula quanto tempo resta para cumprir o tempo minimo do splash."""
    try:
        elapsed_ms = int((now - created_at) * 1000)
    except Exception:
        elapsed_ms = 0
    if elapsed_ms < 0:
        elapsed_ms = 0
    return max(0, int(min_duration_ms) - elapsed_ms)


def show_splash(root: tk.Misc, min_ms: int = SPLASH_MIN_DURATION_MS) -> tb.Toplevel:
    # Criar invisível para evitar "piscada" no 0,0
    _perf_start = time.perf_counter()
    splash = tb.Toplevel(root)
    splash.withdraw()
    splash.overrideredirect(True)
    splash.attributes("-topmost", True)
    splash._created_at = time.monotonic()  # type: ignore[attr-defined]
    splash._min_duration_ms = max(int(min_ms), SPLASH_MIN_DURATION_MS)  # type: ignore[attr-defined]
    splash._close_job = None  # type: ignore[attr-defined]
    splash._progress_job = None  # type: ignore[attr-defined]
    splash._on_closed: Optional[Callable[[], None]] = None  # type: ignore[attr-defined]

    # Container principal com padding
    container = tb.Frame(splash, padding=20)
    container.pack(fill="both", expand=True)

    row = 0

    # Logo RC (se existir PNG)
    logo_path = _find_logo_path()
    if logo_path:
        try:
            logo_image = tk.PhotoImage(file=logo_path)
            # Reduzir se estiver muito grande (p.ex. 512x512)
            max_size = 128
            width, height = logo_image.width(), logo_image.height()
            scale = max(width / max_size, height / max_size, 1)
            if scale > 1:
                # subsample aceita apenas inteiro; arredonda pra cima/fator mínimo 1
                factor = int(scale)
                if factor < 1:
                    factor = 1
                logo_image = logo_image.subsample(factor, factor)

            logo_label = tb.Label(container, image=logo_image)
            logo_label.pack(pady=(0, 10))
            # Manter referência pra não ser coletado
            splash._logo_image = logo_image  # type: ignore[attr-defined]
            row += 1
        except Exception as exc:  # noqa: BLE001
            # Se falhar por qualquer motivo, apenas segue sem logo
            _log.debug("Falha ao carregar logo em splash: %s", exc)

    # Cabeçalho com nome do app
    header_label = tb.Label(
        container,
        text=f"Gestor de Clientes {APP_VERSION}",
        font=("", 11, "bold"),  # pyright: ignore[reportArgumentType]
        anchor="center",
    )
    header_label.pack(pady=(0, 8))

    # Separador horizontal
    separator = tb.Separator(container, orient="horizontal")
    separator.pack(fill="x", padx=20, pady=(4, 8))
    splash.separator = separator  # type: ignore[attr-defined]

    # Mensagem de carregamento
    message_label = tb.Label(
        container,
        text="Carregando, por favor aguarde...",
        anchor="center",
        justify="center",
    )
    message_label.pack(pady=(0, 12))

    # Progressbar deterministica
    bar = tb.Progressbar(
        container,
        mode="determinate",
        length=240,
        bootstyle=INFO,
        maximum=SPLASH_PROGRESS_MAX,
    )
    bar["value"] = 0
    bar.pack(fill="x")
    splash.progress = bar  # type: ignore[attr-defined]

    step_delay = splash._min_duration_ms // SPLASH_PROGRESS_STEPS  # type: ignore[attr-defined]
    splash._progress_step_delay = max(10, int(step_delay))  # type: ignore[attr-defined]
    splash._progress_step_value = SPLASH_PROGRESS_MAX / float(SPLASH_PROGRESS_STEPS)  # type: ignore[attr-defined]
    try:
        _log.info(
            "Splash: progresso configurado delay=%dms step=%.3f min_ms=%s",
            splash._progress_step_delay,  # type: ignore[attr-defined]
            splash._progress_step_value,  # type: ignore[attr-defined]
            splash._min_duration_ms,  # type: ignore[attr-defined]
        )
    except Exception:
        _log.debug("Falha ao registrar log de progresso do splash", exc_info=True)

    def _cancel_job(attr: str) -> None:
        job_id = getattr(splash, attr, None)  # type: ignore[attr-defined]
        if job_id is not None:
            try:
                splash.after_cancel(job_id)
            except Exception:
                _log.debug("Falha ao cancelar job do splash", exc_info=True)
            setattr(splash, attr, None)  # type: ignore[attr-defined]

    def _run_on_closed(callback: Optional[Callable[[], None]]) -> None:
        if callback is None:
            return
        try:
            splash.after_idle(callback)
        except Exception:
            try:
                callback()
            except Exception:
                _log.debug("Falha ao executar callback on_closed do splash", exc_info=True)

    def _schedule_progress() -> None:
        """Avança a barra de progresso até o máximo dentro do tempo mínimo."""
        try:
            exists = splash.winfo_exists()
        except Exception:
            exists = False
        if not exists:
            splash._progress_job = None  # type: ignore[attr-defined]
            return
        try:
            current = float(bar["value"])
            maximum = float(bar["maximum"])
        except Exception:
            splash._progress_job = None  # type: ignore[attr-defined]
            return

        if current >= maximum:
            bar["value"] = maximum
            splash._progress_job = None  # type: ignore[attr-defined]
            return

        bar.step(splash._progress_step_value)  # type: ignore[attr-defined]
        try:
            splash._progress_job = splash.after(splash._progress_step_delay, _schedule_progress)  # type: ignore[attr-defined]
        except Exception:
            splash._progress_job = None  # type: ignore[attr-defined]

    _schedule_progress()

    # Aplicar ícone rc.ico se disponível
    try:
        icon_path = resource_path("rc.ico")
        if os.path.exists(icon_path):
            splash.iconbitmap(icon_path)
    except Exception as exc:  # noqa: BLE001
        _log.debug("Falha ao definir ícone em splash: %s", exc)

    # Medir e centralizar antes de exibir
    splash.update_idletasks()
    try:
        sw, sh = splash.winfo_screenwidth(), splash.winfo_screenheight()
    except Exception:
        sw, sh = 1366, 768

    # Tamanho ajustado para o novo layout
    w = splash.winfo_reqwidth() or 360
    h = splash.winfo_reqheight() or 200
    x, y = _center_coords(sw, sh, w, h)
    splash.geometry(f"{w}x{h}+{x}+{y}")

    # Mostrar já centralizado (sem flash)
    splash.deiconify()
    splash.lift()
    splash.update()

    def _do_close() -> None:
        """Fecha o splash e executa callback (se definido)."""
        try:
            exists = splash.winfo_exists()
        except Exception:
            exists = False
        if not exists:
            callback = getattr(splash, "_on_closed", None)  # type: ignore[attr-defined]
            splash._on_closed = None  # type: ignore[attr-defined]
            _run_on_closed(callback)
            return

        callback = getattr(splash, "_on_closed", None)  # type: ignore[attr-defined]
        splash._on_closed = None  # type: ignore[attr-defined]

        try:
            splash.attributes("-topmost", False)
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao remover topmost em splash: %s", exc)
        _cancel_job("_progress_job")
        _cancel_job("_close_job")
        splash.destroy()

        _run_on_closed(callback)
        try:
            _log.info(
                "Splash: fechado apos %.3fs (min_ms=%s)",
                time.perf_counter() - _perf_start,
                getattr(splash, "_min_duration_ms", SPLASH_MIN_DURATION_MS),
            )
        except Exception:
            _log.debug("Falha ao registrar log de fechamento do splash", exc_info=True)

    def _close_after_min_duration() -> None:
        """Fecha o splash respeitando o tempo mínimo em tela."""
        try:
            exists = splash.winfo_exists()
        except Exception:
            exists = False
        if not exists:
            callback = getattr(splash, "_on_closed", None)  # type: ignore[attr-defined]
            splash._on_closed = None  # type: ignore[attr-defined]
            _run_on_closed(callback)
            return
        created_at = getattr(splash, "_created_at", time.monotonic())  # type: ignore[attr-defined]
        min_duration_ms = getattr(splash, "_min_duration_ms", SPLASH_MIN_DURATION_MS)  # type: ignore[attr-defined]
        remaining_ms = _compute_remaining_ms(created_at, time.monotonic(), min_duration_ms)

        if remaining_ms <= 0:
            _do_close()
            return

        # Cancela agendamento anterior (se houver) e agenda com o restante
        _cancel_job("_close_job")
        splash._close_job = splash.after(remaining_ms, _do_close)  # type: ignore[attr-defined]

    def _public_close(on_closed: Optional[Callable[[], None]] = None) -> None:
        """API pública para fechamento seguro."""
        splash._on_closed = on_closed  # type: ignore[attr-defined]
        _close_after_min_duration()

    splash.close = _public_close  # type: ignore[attr-defined]
    _close_after_min_duration()
    return splash
