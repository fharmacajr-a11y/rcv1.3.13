# ui/utils.py
from __future__ import annotations

def center_window(win, w: int = 1200, h: int = 500) -> None:
    """Centraliza uma janela Tk/Toplevel no centro da tela principal."""
    try:
        win.update_idletasks()
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        x = (sw // 2) - (w // 2)
        y = (sh // 2) - (h // 2)
        win.geometry(f"{w}x{h}+{x}+{y}")
    except Exception:
        # fallback: não quebra a UI
        try:
            win.geometry(f"{w}x{h}")
        except Exception:
            pass


def center_on_parent(parent, win, w: int, h: int) -> None:
    """Centraliza `win` em relação à janela `parent` (útil para modais)."""
    try:
        parent.update_idletasks()
        win.update_idletasks()
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        x = int(px + (pw - w) / 2)
        y = int(py + (ph - h) / 2)
        win.geometry(f"{w}x{h}+{x}+{y}")
    except Exception:
        # se falhar (parent destruído, etc.), cai no center_window
        center_window(win, w, h)


__all__ = ["center_window", "center_on_parent"]
