# application/navigation_controller.py
from __future__ import annotations
from typing import Any, Optional, Type, Callable


class NavigationController:
    """
    Controla transições entre frames Tkinter.
    Não conhece classes específicas; recebe a classe e kwargs.
    """

    def __init__(
        self,
        root: Any,
        *,
        frame_factory: Optional[Callable[[Type[Any], dict[str, Any]], Any]] = None,
    ) -> None:
        self._root = root
        self._current: Optional[Any] = None
        self._factory = frame_factory

    def show_frame(self, frame_cls: Type[Any], **kwargs: Any) -> Any:
        if self._factory is not None:
            frame = self._factory(frame_cls, kwargs)
            self._current = frame
            return frame

        try:
            if self._current is not None and hasattr(self._current, "destroy"):
                self._current.destroy()
        except Exception:
            pass

        frame = frame_cls(self._root, **kwargs)
        try:
            frame.pack(fill="both", expand=True)
        except Exception:
            pass
        self._current = frame
        return frame

    def current(self) -> Optional[Any]:
        return self._current
