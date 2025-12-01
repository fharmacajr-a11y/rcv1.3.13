# -*- coding: utf-8 -*-
# application/navigation_controller.py
from __future__ import annotations

import logging
from typing import Any, Callable, Optional, Type

log = logging.getLogger(__name__)


class NavigationController:
    """Controla transições entre frames Tkinter, sem acoplamento a classes específicas."""

    def __init__(
        self,
        root: Any,
        *,
        frame_factory: Optional[Callable[[Type[Any], dict[str, Any]], Any]] = None,
    ) -> None:
        """Inicializa o controlador com o root Tk e uma factory opcional de frames."""
        self._root = root
        self._current: Optional[Any] = None
        self._factory = frame_factory

    def show_frame(self, frame_cls: Type[Any], **kwargs: Any) -> Any:
        """Mostra (ou reutiliza) o frame indicado e devolve o frame ativo."""
        # Quando a factory devolver um frame existente (reuso),
        # não destruir o atual; apenas levantar (lift) o destino e atualizar _current.
        if self._factory is not None:
            frame = self._factory(frame_cls, kwargs)
            if frame is None:
                return self._show_frame_default(frame_cls, **kwargs)

            # Mesmo frame: apenas lift
            if frame is self._current:
                try:
                    frame.lift()
                except Exception as exc:
                    log.debug("Falha ao dar lift no frame atual", exc_info=exc)
                return frame

            # Frame reutilizado: NÃO destruir o anterior aqui.
            try:
                if hasattr(frame, "pack_info"):
                    frame.pack(fill="both", expand=True)
                else:
                    frame.place(relx=0, rely=0, relwidth=1, relheight=1)
                frame.lift()
            except Exception as exc:
                log.debug("Falha ao posicionar frame reutilizado", exc_info=exc)

            self._current = frame
            return frame

        # Sem factory -> caminho padrão (pode destruir)
        return self._show_frame_default(frame_cls, **kwargs)

    def _show_frame_default(self, frame_cls: Type[Any], **kwargs: Any) -> Any:
        """Cria um frame novo, destrói o anterior (se houver) e posiciona o atual."""
        try:
            if self._current is not None and hasattr(self._current, "destroy"):
                self._current.destroy()
        except Exception as exc:
            log.debug("Falha ao destruir frame anterior", exc_info=exc)
        frame = frame_cls(self._root, **kwargs)
        try:
            frame.pack(fill="both", expand=True)
        except Exception as exc:
            log.debug("Falha ao posicionar frame padrão", exc_info=exc)
        self._current = frame
        return frame

    def current(self) -> Optional[Any]:
        """Retorna o frame atualmente ativo (ou None)."""
        return self._current


__all__ = ["NavigationController"]
