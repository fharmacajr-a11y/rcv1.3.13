"""Helpers para navegação entre frames Tkinter/ttkbootstrap."""

from __future__ import annotations

import tkinter as tk
from typing import Any, Callable, Type, TypeVar

WidgetT = TypeVar("WidgetT", bound=tk.Widget)


def show_frame(
    container: tk.Misc,
    frame_cls: Type[WidgetT],
    *,
    pack_opts: dict[str, Any] | None = None,
    before_show: Callable[[WidgetT], None] | None = None,
    after_show: Callable[[WidgetT], None] | None = None,
    **frame_kwargs: Any,
) -> WidgetT:
    """Destroy frame atual do container, instancia o próximo e o exibe."""
    current = getattr(container, "_current_frame", None)
    if current is not None and hasattr(current, "winfo_exists") and current.winfo_exists():
        if getattr(current, "_keep_alive", False):
            try:
                current.pack_forget()
            except Exception:
                pass
        else:
            try:
                current.destroy()
            except Exception:
                pass

    frame = frame_cls(container, **frame_kwargs)

    if before_show:
        before_show(frame)

    pack_params = {"fill": "both", "expand": True}
    if pack_opts:
        pack_params.update(pack_opts)
    frame.pack(**pack_params)

    setattr(container, "_current_frame", frame)

    if after_show:
        after_show(frame)

    return frame
