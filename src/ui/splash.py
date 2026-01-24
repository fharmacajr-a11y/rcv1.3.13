# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import os
import time
import tkinter as tk
from collections.abc import Callable
from typing import Optional
from PIL import Image

from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk
from src.utils.resource_path import resource_path
from src.version import get_version

_log = logging.getLogger(__name__)

# Constantes do splash
SPLASH_MIN_DURATION_MS = 5000
SPLASH_PROGRESS_MAX = 100
SPLASH_PROGRESS_STEPS = 100
APP_VERSION = get_version()

# Constantes CTk
SPLASH_W = 480
SPLASH_H = 320

CARD_GRAY = ("#e2e2e2", "#242424")
SEP_COLOR = ("#d0d0d0", "#4a4a4a")  # mais claro no light; no dark continua visível

CARD_RADIUS = 22
PADX = 28
PADY = 22

LOGO_MAX_W = 360
LOGO_MAX_H = 170

PROG_H = 14  # altura da barra de progresso (MICROFASE 35: aumentada de 12→14)

# Cor "chave" para transparência (Windows)
TRANSPARENT_KEY = "#ff00ff"


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


def show_splash(root: tk.Misc, min_ms: int = SPLASH_MIN_DURATION_MS) -> tk.Toplevel:
    # Criar invisível para evitar "piscada" no 0,0
    _perf_start = time.perf_counter()

    # Usar CTkToplevel se disponível, senão tk.Toplevel
    if HAS_CUSTOMTKINTER and ctk is not None:
        splash = ctk.CTkToplevel(root)  # type: ignore[assignment]
    else:
        splash = tk.Toplevel(root)

    splash.withdraw()
    splash.overrideredirect(True)
    splash.attributes("-topmost", True)
    splash._created_at = time.monotonic()  # type: ignore[attr-defined]
    splash._min_duration_ms = max(int(min_ms), SPLASH_MIN_DURATION_MS)  # type: ignore[attr-defined]
    splash._close_job = None  # type: ignore[attr-defined]
    splash._progress_job = None  # type: ignore[attr-defined]
    splash._on_closed: Optional[Callable[[], None]] = None  # type: ignore[attr-defined]

    # Geometria + "cantos transparentes" (para SUMIR o quadrado externo)
    if HAS_CUSTOMTKINTER and ctk is not None:
        splash.geometry(f"{SPLASH_W}x{SPLASH_H}")
        splash.resizable(False, False)

        # Tentar ativar transparência de cantos (Windows)
        try:
            splash.configure(fg_color=TRANSPARENT_KEY)
            splash.overrideredirect(True)
            splash.wm_attributes("-transparentcolor", TRANSPARENT_KEY)
            splash.wm_attributes("-topmost", True)
        except Exception:
            # fallback: janela normal (vai ter quadrado externo), mas mantém layout OK
            splash.configure(fg_color=CARD_GRAY)
            try:
                splash.overrideredirect(False)
            except Exception:
                pass
    else:
        # Para Tk padrão
        splash.overrideredirect(True)
        splash.attributes("-topmost", True)

    def _fit(w, h, max_w, max_h):
        """Helper para calcular tamanho proporcional mantendo aspect ratio"""
        s = min(max_w / w, max_h / h)
        return max(1, int(w * s)), max(1, int(h * s))

    # Card único (SEM "quadrado dentro")
    if HAS_CUSTOMTKINTER and ctk is not None:
        card = ctk.CTkFrame(
            splash,
            fg_color=CARD_GRAY,
            corner_radius=CARD_RADIUS,
            border_width=0,
        )
        card.pack(fill="both", expand=True, padx=0, pady=0)

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=PADX, pady=PADY)
    else:
        content = tk.Frame(splash)
        content.pack(fill="both", expand=True, padx=20, pady=20)

    # Logo RC (se existir PNG)
    logo_path = _find_logo_path()
    if logo_path:
        try:
            if HAS_CUSTOMTKINTER and ctk is not None:
                # Logo maior SEM distorcer (aspect fit)
                pil = Image.open(logo_path).convert("RGBA")
                rw, rh = _fit(pil.size[0], pil.size[1], LOGO_MAX_W, LOGO_MAX_H)
                logo_img = ctk.CTkImage(light_image=pil, dark_image=pil, size=(rw, rh))
                splash._logo_img = logo_img  # manter referência

                logo_label = ctk.CTkLabel(content, image=logo_img, text="")
                logo_label.pack(pady=(0, 10))
            else:
                # Para tk tradicional, usar PhotoImage
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

                logo_label = tk.Label(content, image=logo_image)
                # Manter referência pra não ser coletado
                splash._logo_image = logo_image  # type: ignore[attr-defined]
                logo_label.pack(pady=(0, 10))
        except Exception as exc:  # noqa: BLE001
            # Se falhar por qualquer motivo, apenas segue sem logo
            _log.debug("Falha ao carregar logo em splash: %s", exc)

    # Textos + separador (título maior + separador mais cinza)
    if HAS_CUSTOMTKINTER and ctk is not None:
        title = ctk.CTkLabel(content, text=f"Gestor de Clientes {APP_VERSION}", font=("Segoe UI", 14, "bold"))
        title.pack(pady=(0, 10))

        sep = ctk.CTkFrame(content, height=1, corner_radius=0, fg_color=("#e6e6e6", "#3a3a3a"))
        sep.pack(fill="x", padx=110, pady=(0, 12))

        msg = ctk.CTkLabel(content, text="Carregando, por favor aguarde...", font=("Segoe UI", 12))
        msg.pack(pady=(0, 14))
    else:
        title = tk.Label(
            content,
            text=f"Gestor de Clientes {APP_VERSION}",
            font=("", 11, "bold"),  # pyright: ignore[reportArgumentType]
        )
        title.pack(pady=(0, 10))

        sep = tk.Frame(content, height=2, bg="#cccccc")
        sep.pack(fill="x", pady=(0, 12))

        msg = tk.Label(
            content,
            text="Carregando, por favor aguarde...",
            anchor="center",
            justify="center",
        )
        msg.pack(pady=(0, 14))
    splash.separator = sep  # type: ignore[attr-defined]

    # Progressbar DETERMINATE (sempre visível e enchendo)
    if HAS_CUSTOMTKINTER and ctk is not None:
        bar = ctk.CTkProgressBar(content, mode="determinate", height=PROG_H, corner_radius=8)
        bar.set(0.0)
        bar.pack(fill="x", pady=(0, 0))

        # Atualização manual usando after (NÃO usar bar.start())
        splash._pb = 0.0  # type: ignore[attr-defined]
        delay_ms = 50
        min_ms = 5000
        step = delay_ms / float(min_ms)

        def tick() -> None:
            try:
                if not splash.winfo_exists():
                    return
            except Exception:
                return

            splash._pb = min(1.0, splash._pb + step)  # type: ignore[attr-defined]
            try:
                bar.set(splash._pb)  # type: ignore[attr-defined]
            except Exception:
                return

            if splash._pb < 1.0:  # type: ignore[attr-defined]
                splash.after(delay_ms, tick)

        tick()
    else:
        # Fallback Canvas para tk puro
        bar = tk.Canvas(content, width=240, height=20, bg="#e0e0e0", highlightthickness=0)
        bar._progress_value = 0.0  # type: ignore[attr-defined]
        bar.pack(fill="x", padx=20, pady=(0, 20))
    splash.progress = bar  # type: ignore[attr-defined]

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

    # Tamanho fixo (para ficar sempre no mesmo tamanho do splash antigo)
    if HAS_CUSTOMTKINTER and ctk is not None:
        w, h = SPLASH_W, SPLASH_H
    else:
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

        # Fechar splash - completar barra antes de destruir
        try:
            bar = getattr(splash, "progress", None)
            if bar and hasattr(bar, "set"):
                bar.set(1.0)
        except Exception:
            pass
            pass

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
