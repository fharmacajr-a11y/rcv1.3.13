# -*- coding: utf-8 -*-
"""Helper para suprimir flicker de titlebar durante toggle de tema.

FASE 2: Mitigação app-side do flash causado pelo ciclo
withdraw/deiconify que o CustomTkinter faz internamente ao mudar
a cor da titlebar no Windows via DwmSetWindowAttribute.

Estratégia:
  1. Antes de ctk.set_appearance_mode(), substituímos temporariamente
     _windows_set_titlebar_color() nas janelas CTk/CTkToplevel abertas
     por uma versão que NÃO faz withdraw/deiconify.
  2. Após o toggle, aplicamos DwmSetWindowAttribute diretamente e
     forçamos repaint do non-client area via SetWindowPos(SWP_FRAMECHANGED).
  3. Restauramos os métodos originais.

Tudo isso é Windows-only, isolado neste módulo, e fácil de remover.
"""

from __future__ import annotations

import contextlib
import logging
import sys
from typing import Any, Optional

log = logging.getLogger(__name__)


def _apply_titlebar_color_no_flash(window: Any, color_mode: str) -> None:
    """Aplica DwmSetWindowAttribute SEM withdraw/deiconify.

    Usa SetWindowPos(SWP_FRAMECHANGED) para forçar o Windows a
    repintar a barra de título sem esconder/reexibir a janela inteira.

    Args:
        window: Janela Tk/CTk com winfo_id()
        color_mode: "Dark" ou "Light"
    """
    if sys.platform != "win32":
        return

    try:
        import ctypes

        value = 1 if color_mode.lower() == "dark" else 0
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())

        DWMWA_USE_IMMERSIVE_DARK_MODE = 20  # noqa: N806
        DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1 = 19  # noqa: N806

        if (
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_USE_IMMERSIVE_DARK_MODE,
                ctypes.byref(ctypes.c_int(value)),
                ctypes.sizeof(ctypes.c_int(value)),
            )
            != 0
        ):
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1,
                ctypes.byref(ctypes.c_int(value)),
                ctypes.sizeof(ctypes.c_int(value)),
            )

        # Forçar repaint do non-client area (titlebar) sem withdraw/deiconify
        SWP_NOMOVE = 0x0002  # noqa: N806
        SWP_NOSIZE = 0x0001  # noqa: N806
        SWP_NOZORDER = 0x0004  # noqa: N806
        SWP_FRAMECHANGED = 0x0020  # noqa: N806
        ctypes.windll.user32.SetWindowPos(
            hwnd,
            0,
            0,
            0,
            0,
            0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED,
        )

        log.debug(f"[theme_toggle_helper] DWM titlebar aplicado: {color_mode}")

    except Exception as exc:
        log.debug(f"[theme_toggle_helper] Falha ao aplicar DWM: {exc}")


def _find_all_ctk_windows(root: Any) -> list[Any]:
    """Retorna a janela root + qualquer CTkToplevel aberto.

    Percorre winfo_children do root procurando Toplevels que tenham
    o método _windows_set_titlebar_color (sinal de janela CTk).
    """
    windows: list[Any] = []
    if root is not None and hasattr(root, "_windows_set_titlebar_color"):
        windows.append(root)

    if root is not None:
        try:
            for child in root.winfo_children():
                if hasattr(child, "_windows_set_titlebar_color"):
                    windows.append(child)
        except Exception:
            pass

    return windows


@contextlib.contextmanager
def suppress_titlebar_flash(master_ref: Optional[Any], color_mode: str):
    """Context manager que suprime o flash de titlebar durante o toggle.

    Uso em theme_manager.py:
        with suppress_titlebar_flash(self._master_ref, "Dark"):
            ctk.set_appearance_mode("Dark")

    Se master_ref for None ou não estiver em Windows, é um no-op seguro.

    Args:
        master_ref: Referência à janela principal (CTk)
        color_mode: "Dark" ou "Light" — modo ALVO do toggle
    """
    # No-op em plataformas não-Windows ou se não temos janela
    if sys.platform != "win32" or master_ref is None:
        yield
        return

    windows = _find_all_ctk_windows(master_ref)

    if not windows:
        yield
        return

    # Salvar métodos originais e substituir por no-op
    originals: list[tuple[Any, Any]] = []
    for win in windows:
        try:
            orig = win._windows_set_titlebar_color
            originals.append((win, orig))
            # Substituir por no-op (não faz withdraw/deiconify)
            win._windows_set_titlebar_color = lambda mode, _w=win: None  # noqa: ARG005
        except Exception:
            pass

    try:
        yield
    finally:
        # Restaurar métodos originais
        for win, orig in originals:
            try:
                win._windows_set_titlebar_color = orig
            except Exception:
                pass

        # Aplicar DWM diretamente em cada janela, sem withdraw/deiconify
        for win in windows:
            try:
                if win.winfo_exists():
                    _apply_titlebar_color_no_flash(win, color_mode)
            except Exception:
                pass


__all__ = ["suppress_titlebar_flash"]
