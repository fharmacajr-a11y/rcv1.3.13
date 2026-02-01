# -*- coding: utf-8 -*-
"""Manager global para ttk.Treeview com tema centralizado.

Gerencia todos os Treeviews do app e aplica tema automaticamente quando muda Light/Dark.
"""

from __future__ import annotations

import logging
import weakref
from typing import Any, Optional

from src.ui.ttk_treeview_theme import apply_treeview_theme, apply_zebra, TreeColors

log = logging.getLogger(__name__)


class TtkTreeviewManager:
    """Manager singleton para gerenciar tema de todos os Treeviews."""

    _instance: Optional[TtkTreeviewManager] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._trees: list[dict[str, Any]] = []  # Lista de registros
        self._tracker_registered = False

        log.info("[TtkTreeManager] Manager inicializado")

    def register(
        self, tree: Any, master: Any, style_name: str = "RC.Treeview", zebra: bool = True, mode: Optional[str] = None
    ) -> tuple[str, TreeColors]:
        """Registra um Treeview para gerenciamento automático de tema.

        Args:
            tree: Instância do ttk.Treeview
            master: Widget master para ttk.Style
            style_name: Nome base do style
            zebra: Se True, aplica zebra striping
            mode: Modo inicial (None = detectar automaticamente)

        Returns:
            Tupla (nome_style_completo, TreeColors)
        """
        try:
            # Detectar modo atual se não especificado
            if mode is None:
                try:
                    from src.ui.ctk_config import ctk

                    mode = ctk.get_appearance_mode()
                except Exception:
                    mode = "Light"

            # Aplicar tema imediatamente
            full_style, colors = apply_treeview_theme(mode, master, style_name)
            tree.configure(style=full_style)

            if zebra:
                apply_zebra(tree, colors)

            # Registrar com weakref para não impedir garbage collection
            record = {
                "tree": weakref.ref(tree),
                "master": master,
                "style_name": style_name,
                "zebra": zebra,
            }
            self._trees.append(record)

            # Registrar callback do AppearanceModeTracker (apenas uma vez)
            if not self._tracker_registered:
                self._register_appearance_tracker()
                # Aplicar tema atual em todas as trees já registradas
                if len(self._trees) > 0:
                    self.apply_all(mode)

            log.debug(f"[TtkTreeManager] Treeview registrado: style={full_style}, zebra={zebra}")

            return full_style, colors

        except Exception as exc:
            log.exception(f"[TtkTreeManager] Erro ao registrar Treeview: {exc}")
            # Retornar valores padrão em caso de erro
            return style_name, TreeColors(
                bg="#ffffff",
                field_bg="#ffffff",
                fg="#000000",
                heading_bg="#e5e7eb",
                heading_fg="#000000",
                sel_bg="#3b82f6",
                sel_fg="#ffffff",
                even_bg="#ffffff",
                odd_bg="#e6eaf0",
                border="#d1d5db",
            )

    def apply_to(self, tree: Any, master: Any, style_name: str, mode: str, zebra: bool = False) -> TreeColors:
        """Aplica tema em um Treeview específico.

        Args:
            tree: Instância do ttk.Treeview
            master: Widget master
            style_name: Nome base do style
            mode: "Light" ou "Dark"
            zebra: Se True, aplica zebra após aplicar tema

        Returns:
            TreeColors aplicado
        """
        try:
            full_style, colors = apply_treeview_theme(mode, master, style_name)
            tree.configure(style=full_style)

            if zebra:
                apply_zebra(tree, colors)

            return colors

        except Exception as exc:
            log.exception(f"[TtkTreeManager] Erro ao aplicar tema: {exc}")
            return TreeColors(
                bg="#ffffff",
                field_bg="#ffffff",
                fg="#000000",
                heading_bg="#e5e7eb",
                heading_fg="#000000",
                sel_bg="#3b82f6",
                sel_fg="#ffffff",
                even_bg="#ffffff",
                odd_bg="#e6eaf0",
                border="#d1d5db",
            )

    def apply_all(self, mode: str) -> None:
        """Aplica tema em todos os Treeviews registrados.

        Args:
            mode: "Light" ou "Dark"
        """
        log.debug(f"[TtkTreeManager] apply_all chamado: mode={mode}, trees={len(self._trees)}")

        # Limpar referências mortas
        self._trees = [r for r in self._trees if r["tree"]() is not None]

        applied = 0
        for record in self._trees:
            tree = record["tree"]()
            if tree is None:
                continue

            try:
                master = record["master"]
                style_name = record["style_name"]
                zebra = record["zebra"]

                full_style, colors = apply_treeview_theme(mode, master, style_name)
                tree.configure(style=full_style)

                # Reaplicar zebra em TODOS os itens existentes
                if zebra:
                    apply_zebra(tree, colors)
                    # Forçar update visual
                    try:
                        tree.update_idletasks()
                    except Exception:
                        pass

                applied += 1
                log.debug(f"[TtkTreeManager] Tree atualizada: {style_name}, bg={colors.bg}")

            except Exception as exc:
                log.warning(f"[TtkTreeManager] Erro ao aplicar tema em Treeview: {exc}")

        log.debug(f"[TtkTreeManager] Tema {mode} aplicado em {applied} Treeviews")

    def _register_appearance_tracker(self) -> None:
        """Registra callback no AppearanceModeTracker do CustomTkinter."""
        try:
            from customtkinter import AppearanceModeTracker  # type: ignore[import-untyped, attr-defined]

            def _theme_callback(mode: Optional[str] = None) -> None:
                """Callback compatível com diferentes versões do CustomTkinter."""
                if mode is None:
                    try:
                        from src.ui.ctk_config import ctk

                        mode = ctk.get_appearance_mode()
                    except Exception:
                        mode = "Light"

                log.debug(f"[TtkTreeManager] Tema mudou para: {mode}")
                self.apply_all(mode)

            # Tentar registrar callback (assinatura pode variar)
            try:
                AppearanceModeTracker.add(_theme_callback)
            except TypeError:
                # Fallback: algumas versões podem requerer widget
                try:
                    AppearanceModeTracker.add(_theme_callback, None)
                except Exception:
                    log.warning("[TtkTreeManager] AppearanceModeTracker.add() com assinatura incompatível")

            self._tracker_registered = True
            log.debug("[TtkTreeManager] Integrado com AppearanceModeTracker")

        except Exception as exc:
            log.warning(f"[TtkTreeManager] Erro ao integrar com AppearanceModeTracker: {exc}")


# Singleton global
_manager: Optional[TtkTreeviewManager] = None


def get_treeview_manager() -> TtkTreeviewManager:
    """Retorna instância singleton do TtkTreeviewManager."""
    global _manager
    if _manager is None:
        _manager = TtkTreeviewManager()
    return _manager
