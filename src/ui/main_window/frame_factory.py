from __future__ import annotations

from typing import Any, Optional
import logging

log = logging.getLogger("app_gui")

__all__ = ["create_frame"]


def _forget_widget(widget: Optional[Any]) -> None:
    if widget is None:
        return
    try:
        widget.pack_forget()
    except Exception:
        try:
            widget.place_forget()
        except Exception:
            pass


def _lift_widget(widget: Any) -> None:
    try:
        widget.lift()
    except Exception:
        pass


def _place_or_pack(widget: Any) -> None:
    try:
        widget.place(relx=0, rely=0, relwidth=1, relheight=1)
    except Exception:
        try:
            widget.pack(fill="both", expand=True)
        except Exception:
            pass


def create_frame(app: Any, frame_cls: Any, options: Optional[dict]) -> Any:
    """Replica a antiga lgica de _frame_factory mantendo comportamento."""
    options = options or {}
    current = getattr(app.nav, "current", lambda: None)()

    from src.ui.hub_screen import HubScreen

    if frame_cls is HubScreen:
        if getattr(app, "_hub_screen_instance", None) is None:
            app._hub_screen_instance = HubScreen(app._content_container, **options)
            _place_or_pack(app._hub_screen_instance)

        frame = app._hub_screen_instance

        if current is not None and current is not frame:
            _forget_widget(current)

        _lift_widget(frame)

        try:
            frame.on_show()
        except Exception as exc:
            log.warning("Erro ao chamar on_show do Hub: %s", exc)

        return frame

    try:
        if callable(frame_cls) and not isinstance(frame_cls, type):
            frame = frame_cls(app._content_container)
        else:
            frame = frame_cls(app._content_container, **options)
    except Exception:
        return None

    if current is not None and current is not frame:
        _forget_widget(current)

    try:
        frame.pack(fill="both", expand=True)
    except Exception:
        pass

    return frame
