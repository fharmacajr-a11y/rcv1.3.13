# -*- coding: utf-8 -*-
"""
PDF Viewer Handlers - Event handlers extraídos.

Extrai callbacks complexos de main_window.py para:
- Reduzir LOC da view principal
- Melhorar manutenibilidade
- Facilitar testes de eventos
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from .main_window import PdfViewerWin

logger = logging.getLogger(__name__)

__all__ = [
    "handle_wheel_scroll",
    "handle_wheel_zoom",
    "handle_page_navigation",
    "handle_zoom_shortcuts",
    "handle_pan_events",
    "handle_ocr_actions",
]

TkBindReturn = Literal["break"] | None


# ═══════════════════════════════════════════════════════════════════════════
# SCROLL & ZOOM HANDLERS
# ═══════════════════════════════════════════════════════════════════════════


def handle_wheel_scroll(viewer: PdfViewerWin, event: Any) -> TkBindReturn:
    """Handler para scroll com mouse wheel (sem Ctrl).

    Args:
        viewer: Instância do PdfViewerWin
        event: Evento do Tkinter

    Returns:
        "break" para consumir evento
    """
    if not viewer.canvas.winfo_exists():
        return "break"

    try:
        from src.ui.wheel_windows import wheel_steps

        steps = wheel_steps(event)
    except Exception as exc:  # noqa: BLE001
        # Import pode falhar - degrada para 0 steps
        logger.debug("wheel_steps import/call falhou: %s", type(exc).__name__)
        steps = 0

    if steps and viewer._is_pdf:
        viewer.canvas.yview_scroll(-steps, "units")
        viewer._render_visible_pages()
    elif steps and viewer._img_pil is not None:
        # Scroll para imagem
        viewer.canvas.yview_scroll(-steps, "units")
        if viewer._img_pil is not None:
            viewer._render_image(viewer._img_pil)

    return "break"


def handle_wheel_zoom(viewer: PdfViewerWin, event: Any) -> TkBindReturn:
    """Handler para zoom com Ctrl+MouseWheel.

    Args:
        viewer: Instância do PdfViewerWin
        event: Evento do Tkinter

    Returns:
        "break" para consumir evento
    """
    if not viewer.canvas.winfo_exists():
        return "break"

    try:
        from src.ui.wheel_windows import wheel_steps

        steps = wheel_steps(event)
    except Exception as exc:  # noqa: BLE001
        # Import pode falhar - degrada para 0 steps
        logger.debug("wheel_steps import/call falhou: %s", type(exc).__name__)
        steps = 0

    if steps:
        if viewer._is_pdf:
            viewer._zoom_by(steps, event)
        else:
            viewer._zoom_image_by(steps)

    return "break"


# ═══════════════════════════════════════════════════════════════════════════
# PAGE NAVIGATION
# ═══════════════════════════════════════════════════════════════════════════


def handle_page_navigation(
    viewer: PdfViewerWin,
    action: Literal["up", "down", "home", "end"],
    event: Any | None = None,
) -> TkBindReturn:
    """Handler unificado para navegação de páginas.

    Args:
        viewer: Instância do PdfViewerWin
        action: Tipo de navegação (up/down/home/end)
        event: Evento do Tkinter (opcional)

    Returns:
        "break" para consumir evento
    """
    viewer.focus_canvas()

    if action == "up":
        viewer.canvas.yview_scroll(-1, "pages")
    elif action == "down":
        viewer.canvas.yview_scroll(1, "pages")
    elif action == "home":
        viewer.canvas.yview_moveto(0.0)
    elif action == "end":
        viewer.canvas.yview_moveto(1.0)

    viewer._render_visible_pages()
    return "break"


# ═══════════════════════════════════════════════════════════════════════════
# ZOOM SHORTCUTS
# ═══════════════════════════════════════════════════════════════════════════


def handle_zoom_shortcuts(
    viewer: PdfViewerWin,
    action: Literal["in", "out", "reset", "fit"],
    event: Any,
) -> TkBindReturn:
    """Handler unificado para atalhos de zoom.

    Args:
        viewer: Instância do PdfViewerWin
        action: Tipo de ação (in/out/reset/fit)
        event: Evento do Tkinter

    Returns:
        "break" ou None
    """
    # Ignora se Ctrl está pressionado (conflito com Ctrl+MouseWheel)
    if event.state & 0x0004:
        return None

    viewer.focus_canvas()

    if action in ("in", "out"):
        step = 1 if action == "in" else -1
        viewer._zoom_by(step)
    elif action == "reset":
        viewer._set_zoom_exact(1.0)
    elif action == "fit":
        viewer._set_zoom_fit_width()

    return "break"


# ═══════════════════════════════════════════════════════════════════════════
# PAN (SPACE + DRAG)
# ═══════════════════════════════════════════════════════════════════════════


def handle_pan_events(
    viewer: PdfViewerWin,
    event_type: Literal["press", "motion", "release", "space_down", "space_up"],
    event: Any,
) -> TkBindReturn:
    """Handler unificado para eventos de pan (arrastar com Space).

    Args:
        viewer: Instância do PdfViewerWin
        event_type: Tipo de evento
        event: Evento do Tkinter

    Returns:
        "break" ou None
    """
    if event_type == "space_down":
        if not viewer._pan_active:
            viewer._pan_active = True
            viewer.canvas.configure(cursor="hand2")
        viewer.focus_canvas()
        return "break"

    elif event_type == "space_up":
        if viewer._pan_active:
            viewer._pan_active = False
            viewer.canvas.configure(cursor="")
        return "break"

    elif event_type == "press":
        if not viewer._pan_active:
            return None
        viewer.focus_canvas()
        viewer.canvas.scan_mark(event.x, event.y)
        return "break"

    elif event_type == "motion":
        if not viewer._pan_active:
            return None
        viewer.canvas.scan_dragto(event.x, event.y, gain=1)
        viewer._render_visible_pages()
        return "break"

    elif event_type == "release":
        if not viewer._pan_active:
            return None
        return "break"

    return None


# ═══════════════════════════════════════════════════════════════════════════
# OCR ACTIONS
# ═══════════════════════════════════════════════════════════════════════════


def handle_ocr_actions(
    viewer: PdfViewerWin,
    action: Literal["copy", "select_all", "show_menu"],
    event: Any | None = None,
) -> TkBindReturn:
    """Handler para ações de OCR/texto.

    Args:
        viewer: Instância do PdfViewerWin
        action: Tipo de ação
        event: Evento do Tkinter (usado para menu)

    Returns:
        "break" ou None
    """
    if action == "copy":
        try:
            viewer.text_panel.text.event_generate("<<Copy>>")
        except Exception as exc:
            logger.debug("Falha ao copiar texto OCR: %s", exc)
        return "break"

    elif action == "select_all":
        try:
            viewer.text_panel.text.event_generate("<<SelectAll>>")
        except Exception as exc:
            logger.debug("Falha ao selecionar texto OCR: %s", exc)
        return "break"

    elif action == "show_menu":
        try:
            if event is not None:
                # _show_menu retorna str, mas precisamos de TkBindReturn
                viewer.text_panel._show_menu(event)
                return "break"
        except Exception as exc:  # noqa: BLE001
            # Menu pode falhar se widget destruído
            logger.debug("text_panel menu falhou: %s", type(exc).__name__)
        return "break"

    return None
