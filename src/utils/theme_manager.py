# utils/theme_manager.py
"""DEPRECATED: ThemeManager legado (usa sistema de 14 temas ttkbootstrap).

⚠️ MICROFASE 26: ttkbootstrap REMOVIDO.
Este módulo é mantido apenas para compatibilidade com código legado.
Novo código deve usar src.ui.theme_manager.GlobalThemeManager (CustomTkinter).

IMPORTANTE:
- Não adicionar novas funcionalidades aqui
- Não usar em novos componentes
- Migrar gradualmente para src.ui.theme_manager.theme_manager
"""

from __future__ import annotations

import logging
from typing import Callable

log = logging.getLogger(__name__)


class ThemeManager:
    """Gerencia o tema ativo (DEPRECATED - ttkbootstrap removido)."""

    def __init__(self) -> None:
        self._windows: set[object] = set()
        self._listeners: list[Callable[[str], None]] = []
        self._theme: str = "light"

    # ---------------- estado ----------------
    @property
    def theme(self) -> str:
        """Retorna modo atual (light/dark)."""
        return self._theme

    # ---------------- registro ----------------
    def register_window(self, win: object) -> None:
        """Registra janela (no-op)."""
        self._windows.add(win)
        log.debug("ThemeManager legado: register_window (no-op)")

    def unregister_window(self, win: object) -> None:
        """Remove janela do registro."""
        self._windows.discard(win)

    def add_listener(self, fn: Callable[[str], None]) -> None:
        """Adiciona listener de mudanças de tema."""
        if fn not in self._listeners:
            self._listeners.append(fn)

    def remove_listener(self, fn: Callable[[str], None]) -> None:
        """Remove listener de mudanças de tema."""
        try:
            self._listeners.remove(fn)
        except ValueError:
            log.debug("ThemeManager: listener não registrado para remoção")

    # ---------------- ações ----------------
    def apply_all(self) -> None:
        """Notifica ouvintes (ttkbootstrap removido)."""
        for fn in list(self._listeners):
            try:
                fn(self._theme)
            except Exception:
                log.debug("ThemeManager: listener falhou")

    def set_theme(self, theme: str) -> None:
        """Define tema (deprecated - apenas notifica listeners)."""
        self._theme = theme
        self.apply_all()
        log.debug(f"ThemeManager legado: set_theme({theme}) - no-op")

    def toggle(self) -> str:
        """Alterna entre claro/escuro."""
        self._theme = "dark" if self._theme == "light" else "light"
        self.apply_all()
        return self._theme


# singleton prático
theme_manager = ThemeManager()
