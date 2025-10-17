# ui/utils.py
from __future__ import annotations


class OkCancelMixin:
    """Mixin for simple OK/Cancel dialogs."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)  # type: ignore[misc]
        self._cancel_result = None

    def _ok(self, value=True):
        """Close the dialog reporting success."""
        try:
            self._finalize_ok(value)  # type: ignore[attr-defined]
        except AttributeError:
            pass
        except Exception:
            pass
        try:
            self.result = value  # type: ignore[attr-defined]
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass

    def _cancel(self):
        """Close the dialog indicating cancellation."""
        self._cancel_result = False
        try:
            self.result = False  # type: ignore[attr-defined]
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass


def center_window(win, w: int = 1200, h: int = 500) -> None:
    """Center a window on the primary screen."""
    try:
        win.update_idletasks()
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        x = (sw // 2) - (w // 2)
        y = (sh // 2) - (h // 2)
        win.geometry(f"{w}x{h}+{x}+{y}")
    except Exception:
        try:
            win.geometry(f"{w}x{h}")
        except Exception:
            pass


def center_on_parent(win, parent=None, pad: int = 0):
    """Center ``win`` over ``parent`` (or over the screen as a fallback)."""
    try:
        win.update_idletasks()
        if parent is None:
            parent = getattr(win, "master", None) or win.winfo_toplevel()
        parent.update_idletasks()
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        ww, wh = win.winfo_width(), win.winfo_height()
        x = max(pad, px + (pw - ww) // 2)
        y = max(pad, py + (ph - wh) // 2)
        win.geometry(f"+{x}+{y}")
    except Exception:
        try:
            sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
            ww, wh = win.winfo_width(), win.winfo_height()
            x = max(pad, (sw - ww) // 2)
            y = max(pad, (sh - wh) // 2)
            win.geometry(f"+{x}+{y}")
        except Exception:
            pass
    return win


__all__ = ["OkCancelMixin", "center_window", "center_on_parent"]
