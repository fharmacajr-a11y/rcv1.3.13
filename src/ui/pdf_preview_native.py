from __future__ import annotations

import tkinter as tk

from src.modules.pdf_preview.views.main_window import PdfViewerWin


def _center_modal(window: tk.Toplevel, parent: tk.Misc | None) -> None:
    """Centraliza janela relativa ao pai ou à tela."""
    try:
        window.update_idletasks()
        # Se não há parent, tente centralização nativa do Tk (uma única vez)
        try:
            if not parent or not parent.winfo_exists():
                window.tk.call("tk::PlaceWindow", str(window), "center")
                return
        except Exception:
            # se não estiver disponível, seguimos com o cálculo manual abaixo
            pass
        width = window.winfo_width() or window.winfo_reqwidth()
        height = window.winfo_height() or window.winfo_reqheight()

        if parent and parent.winfo_exists():
            try:
                parent.update_idletasks()
                px, py = parent.winfo_rootx(), parent.winfo_rooty()
                pw, ph = parent.winfo_width(), parent.winfo_height()
                if pw > 0 and ph > 0:
                    x = px + (pw - width) // 2
                    y = py + (ph - height) // 2
                else:
                    raise ValueError
            except Exception:
                parent = None
        if not parent or not parent.winfo_exists():
            screen_w = window.winfo_screenwidth()
            screen_h = window.winfo_screenheight()
            x = max(0, (screen_w - width) // 2)
            y = max(0, (screen_h - height) // 2)
        window.geometry(f"{width}x{height}+{x}+{y}")
    except Exception:
        pass


def open_pdf_viewer(
    master,
    pdf_path: str | None = None,
    display_name: str | None = None,
    data_bytes: bytes | None = None,
):
    """
    Abre visualizador unificado de PDF/imagem.

    Args:
        master: widget pai
        pdf_path: caminho do arquivo (se disponível)
        display_name: nome para exibição
        data_bytes: bytes do arquivo (alternativa a pdf_path)
    """
    win = PdfViewerWin(
        master,
        pdf_path=pdf_path,
        display_name=display_name,
        data_bytes=data_bytes,
    )
    parent = None
    try:
        parent = master.winfo_toplevel() if master else None
    except Exception:
        parent = None
    if parent:
        try:
            win.transient(parent)
        except Exception:
            pass
    _center_modal(win, parent)
    try:
        win.grab_set()
    except Exception:
        pass
    win.focus_canvas()
    return win
