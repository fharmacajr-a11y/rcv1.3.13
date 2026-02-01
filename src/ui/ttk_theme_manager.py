# -*- coding: utf-8 -*-
"""Gerenciador centralizado de tema para ttk.Treeview.

Garante consistência de tema Light/Dark em todas as Treeviews do app.
"""

from __future__ import annotations

import logging
from tkinter import ttk
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from customtkinter import AppearanceModeTracker  # type: ignore[import-not-found]
else:
    try:
        from customtkinter import AppearanceModeTracker  # type: ignore[import-not-found]
    except ImportError:
        AppearanceModeTracker = None  # type: ignore[assignment,misc]


log = logging.getLogger(__name__)


class TreeviewThemeManager:
    """Gerenciador global de tema para ttk.Treeview."""

    def __init__(self):
        self._registered_trees: list[tuple[Any, bool]] = []  # (tree, zebra) - usar Any para evitar type errors
        self._style_cache: dict[Any, Any] = {}  # master -> Style
        self._initialized = False

    def initialize(self) -> None:
        """Inicializa integração com AppearanceModeTracker."""
        if self._initialized:
            return

        # Registrar callback global de mudança de tema
        AppearanceModeTracker.add(self._on_theme_change)
        self._initialized = True
        log.info("TreeviewThemeManager inicializado")

    def _on_theme_change(self, mode: Optional[str] = None) -> None:
        """Callback quando tema muda."""
        current_mode = mode or AppearanceModeTracker.get_mode()
        log.info(f"TreeviewThemeManager: tema mudou para {current_mode}")
        self.apply_all(current_mode)

    def register_treeview(self, tree: ttk.Treeview, zebra: bool = True) -> None:
        """Registra Treeview para gerenciamento automático de tema.

        Args:
            tree: ttk.Treeview a ser registrado
            zebra: Se True, aplica tags even/odd para zebra striping
        """
        # Evitar duplicatas
        for registered_tree, _ in self._registered_trees:
            if registered_tree is tree:
                return

        self._registered_trees.append((tree, zebra))
        log.debug(f"Treeview registrado (total: {len(self._registered_trees)})")

        # Aplicar tema imediatamente
        current_mode = AppearanceModeTracker.get_mode()
        self._apply_to_tree(tree, current_mode, zebra)

    def unregister_treeview(self, tree: ttk.Treeview) -> None:
        """Remove Treeview do gerenciamento."""
        self._registered_trees = [(t, z) for t, z in self._registered_trees if t is not tree]

    def apply_all(self, mode: str) -> None:
        """Aplica tema em todas as Treeviews registradas.

        Args:
            mode: "Light" ou "Dark"
        """
        for tree, zebra in self._registered_trees:
            try:
                if tree.winfo_exists():
                    self._apply_to_tree(tree, mode, zebra)
            except Exception as exc:
                log.warning(f"Erro ao aplicar tema em Treeview: {exc}")

    def _apply_to_tree(self, tree: ttk.Treeview, mode: str, zebra: bool) -> None:
        """Aplica tema em uma Treeview específica."""
        is_dark = mode == "Dark"

        # Cores para Dark e Light
        if is_dark:
            even_bg = "#2b2b2b"
            odd_bg = "#1e1e1e"
            fg = "#ffffff"
            heading_bg = "#1a1a1a"
            heading_fg = "#ffffff"
            sel_bg = "#3b82f6"
            sel_fg = "#ffffff"
        else:
            even_bg = "#ffffff"
            odd_bg = "#e2e6ea"
            fg = "#000000"
            heading_bg = "#e5e7eb"
            heading_fg = "#000000"
            sel_bg = "#3b82f6"
            sel_fg = "#ffffff"

        try:
            # Obter ou criar Style para o master da Treeview
            master = getattr(tree, "master", None)
            if master is None:
                log.warning("[TreeviewThemeManager] Treeview sem master, ignorando")
                return

            if master not in self._style_cache:
                self._style_cache[master] = ttk.Style(master)  # type: ignore[attr-defined]

            style = self._style_cache[master]

            # Forçar tema clam (único que aceita fieldbackground no Windows)
            try:
                current_theme = style.theme_use()
                if current_theme != "clam":
                    style.theme_use("clam")
            except Exception:
                pass

            # Configurar style customizado
            style_name = "RC.Treeview"
            style.configure(
                style_name,
                background=even_bg,
                fieldbackground=even_bg,  # CRÍTICO: remove branco residual
                foreground=fg,
                insertcolor=fg,
                borderwidth=0,
                relief="flat",
                rowheight=28,
            )

            style.configure(
                f"{style_name}.Heading",
                background=heading_bg,
                foreground=heading_fg,
                relief="flat",
                borderwidth=1,
            )

            style.map(style_name, background=[("selected", sel_bg)], foreground=[("selected", sel_fg)])

            # Fallback para "Treeview" padrão
            style.configure("Treeview", background=even_bg, fieldbackground=even_bg, foreground=fg)
            style.configure("Treeview.Heading", background=heading_bg, foreground=heading_fg)

            # Configurar tags zebra se solicitado
            if zebra:
                if hasattr(tree, "tag_configure"):
                    tree.tag_configure("even", background=even_bg)  # type: ignore[attr-defined]
                    tree.tag_configure("odd", background=odd_bg)  # type: ignore[attr-defined]

        except Exception as exc:
            log.error(f"Erro ao aplicar tema em Treeview: {exc}", exc_info=True)

    def apply_treeview_theme(
        self, mode: str, master: Any = None, style_name: str = "RC.Treeview"
    ) -> tuple[str, str, str, str, str]:
        """Aplica tema e retorna cores (compatibilidade com código existente).

        Args:
            mode: "Light" ou "Dark"
            master: Widget master para criar ttk.Style
            style_name: Nome do style customizado

        Returns:
            Tupla (even_bg, odd_bg, fg, heading_bg, heading_fg)
        """
        is_dark = mode == "Dark"

        if is_dark:
            even_bg = "#2b2b2b"
            odd_bg = "#1e1e1e"
            fg = "#ffffff"
            heading_bg = "#1a1a1a"
            heading_fg = "#ffffff"
            sel_bg = "#3b82f6"
            sel_fg = "#ffffff"
        else:
            even_bg = "#ffffff"
            odd_bg = "#e2e6ea"
            fg = "#000000"
            heading_bg = "#e5e7eb"
            heading_fg = "#000000"
            sel_bg = "#3b82f6"
            sel_fg = "#ffffff"

        try:
            style = ttk.Style(master) if master else ttk.Style()  # type: ignore[attr-defined]

            try:
                current_theme = style.theme_use()
                if current_theme != "clam":
                    style.theme_use("clam")
            except Exception:
                pass

            style.configure(
                style_name,
                background=even_bg,
                fieldbackground=even_bg,
                foreground=fg,
                insertcolor=fg,
                borderwidth=0,
                relief="flat",
                rowheight=28,
            )

            style.configure(
                f"{style_name}.Heading",
                background=heading_bg,
                foreground=heading_fg,
                relief="flat",
                borderwidth=1,
            )

            style.map(style_name, background=[("selected", sel_bg)], foreground=[("selected", sel_fg)])

            style.configure("Treeview", background=even_bg, fieldbackground=even_bg, foreground=fg)
            style.configure("Treeview.Heading", background=heading_bg, foreground=heading_fg)

        except Exception as exc:
            log.warning(f"Erro ao aplicar tema: {exc}")

        return even_bg, odd_bg, fg, heading_bg, heading_fg


# Singleton global
_theme_manager: Optional[TreeviewThemeManager] = None


def get_theme_manager() -> TreeviewThemeManager:
    """Obtém instância singleton do gerenciador de tema."""
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = TreeviewThemeManager()
        _theme_manager.initialize()
    return _theme_manager
