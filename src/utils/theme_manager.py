# utils/theme_manager.py
from __future__ import annotations
import logging
from typing import Callable, List, Set, Optional

from src.utils import themes

log = logging.getLogger(__name__)


class ThemeManager:
    """Gerencia o tema ativo, aplica em janelas e notifica ouvintes."""

    def __init__(self) -> None:
        self._windows: Set[object] = set()
        self._listeners: List[Callable[[str], None]] = []
        self._theme: Optional[str] = None

    # ---------------- estado ----------------
    @property
    def theme(self) -> str:
        if self._theme is None:
            self._theme = themes.load_theme()  # usa cache do themes.py
        return self._theme

    # ---------------- registro ----------------
    def register_window(self, win) -> None:
        self._windows.add(win)
        try:
            themes.apply_theme(win, theme=self.theme)
        except Exception:
            log.debug("ThemeManager: apply_theme silencioso")

    def unregister_window(self, win) -> None:
        self._windows.discard(win)

    def add_listener(self, fn: Callable[[str], None]) -> None:
        if fn not in self._listeners:
            self._listeners.append(fn)

    def remove_listener(self, fn: Callable[[str], None]) -> None:
        try:
            self._listeners.remove(fn)
        except ValueError:
            pass

    # ---------------- ações ----------------
    def apply_all(self) -> None:
        """Reaplica tema em todas as janelas registradas e notifica ouvintes."""
        t = self.theme
        for w in list(self._windows):
            try:
                if hasattr(w, "winfo_exists") and not w.winfo_exists():
                    self._windows.discard(w)
                    continue
                themes.apply_theme(w, theme=t)
            except Exception:
                log.debug("ThemeManager: apply_theme em janela falhou")
        for fn in list(self._listeners):
            try:
                fn(t)
            except Exception:
                log.debug("ThemeManager: listener falhou")

    def set_theme(self, theme: str) -> None:
        """Define e persiste o tema, aplicando nas janelas e notificando ouvintes."""
        try:
            themes.save_theme(theme)
            self._theme = theme
        except Exception:
            # ainda assim atualiza estado local
            self._theme = theme
        self.apply_all()

    def toggle(self) -> str:
        """Alterna entre claro/escuro reaproveitando toggle do themes.py."""
        t = themes.toggle_theme()  # já salva; usa cache
        self._theme = t
        self.apply_all()
        return t


# singleton prático
theme_manager = ThemeManager()
