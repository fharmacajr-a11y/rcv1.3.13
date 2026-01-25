# -*- coding: utf-8 -*-
"""Compatibilidade e tematização para widgets ttk (Treeview, Scrollbar, Progressbar).

Este módulo fornece helpers para aplicar temas theme-aware em widgets ttk que
não possuem equivalentes CustomTkinter (principalmente ttk.Treeview).

REGRAS BASELINE CODEC:
- SEMPRE usar ttk.Style(master=...) - NUNCA ttk.Style() sem master
- Aplicar cores consistentes com modo light/dark/system
- Suportar re-aplicação dinâmica ao alternar tema
- Cleanup automático de callbacks em <Destroy>

API:
    apply_treeview_theme(tree, mode, *, master=None) -> None
    bind_treeview_to_theme_changes(tree, theme_manager) -> None
    apply_scrollbar_theme(scrollbar, mode, *, master=None) -> None
    bind_scrollbar_to_theme_changes(scrollbar, theme_manager) -> None
    apply_progressbar_theme(progressbar, mode, *, master=None) -> None
    bind_progressbar_to_theme_changes(progressbar, theme_manager) -> None
"""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING, Any, Literal, Optional

if TYPE_CHECKING:
    from src.ui.theme_manager import GlobalThemeManager

log = logging.getLogger(__name__)

__all__ = [
    "apply_treeview_theme",
    "bind_treeview_to_theme_changes",
    "apply_scrollbar_theme",
    "bind_scrollbar_to_theme_changes",
    "apply_progressbar_theme",
    "bind_progressbar_to_theme_changes",
]


# ==================== CORES THEME-AWARE ====================


def _get_treeview_colors(mode: Literal["Light", "Dark"]) -> dict[str, str]:
    """Retorna palette de cores para Treeview baseada no modo.

    Args:
        mode: "Light" ou "Dark"

    Returns:
        Dict com keys: bg, fg, field_bg, select_bg, select_fg, heading_bg, heading_fg
    """
    if mode == "Dark":
        return {
            "bg": "#2b2b2b",
            "fg": "#ffffff",
            "field_bg": "#1e1e1e",  # fieldbackground = áreas vazias
            "select_bg": "#3b82f6",
            "select_fg": "#ffffff",
            "heading_bg": "#1a1a1a",
            "heading_fg": "#ffffff",
        }
    else:  # Light
        return {
            "bg": "#ffffff",
            "fg": "#000000",
            "field_bg": "#f0f0f0",
            "select_bg": "#3b82f6",
            "select_fg": "#ffffff",
            "heading_bg": "#e5e7eb",
            "heading_fg": "#000000",
        }


# ==================== API PÚBLICA ====================


def apply_treeview_theme(
    tree: ttk.Treeview,
    mode: Literal["Light", "Dark"],
    *,
    master: Optional[tk.Misc] = None,
    style_name: Optional[str] = None,
) -> None:
    """Aplica tema theme-aware em ttk.Treeview.

    CRITICAL: Sempre passa master= ao criar ttk.Style (baseline CODEC).

    Args:
        tree: Widget ttk.Treeview a ser tematizado
        mode: Modo de aparência ("Light" ou "Dark")
        master: Widget master para ttk.Style (default: usar o parent do tree)
        style_name: Nome do style customizado (default: "Themed.Treeview")

    Example:
        >>> tree = ttk.Treeview(parent, columns=("id", "nome"))
        >>> apply_treeview_theme(tree, "Dark", master=parent)
    """
    # Determinar master
    if master is None:
        master = tree.master if hasattr(tree, "master") else tree.winfo_toplevel()

    # Obter cores
    colors = _get_treeview_colors(mode)

    # Criar style com master explícito (BASELINE CODEC)
    try:
        style = ttk.Style(master=master)  # type: ignore[attr-defined]
    except Exception as exc:
        log.error(f"Falha ao criar ttk.Style: {exc}")
        return

    # Forçar tema clam (único que aceita customização no Windows)
    try:
        current_theme = style.theme_use()
        if current_theme != "clam":
            style.theme_use("clam")
            log.debug(f"ttk theme alterado: {current_theme} → clam")
    except Exception as exc:
        log.warning(f"Falha ao aplicar tema clam: {exc}")

    # Nome do style
    style_name = style_name or "Themed.Treeview"

    # Configurar style
    try:
        style.configure(
            style_name,
            background=colors["bg"],
            fieldbackground=colors["field_bg"],  # CRÍTICO: remove branco residual
            foreground=colors["fg"],
            insertcolor=colors["fg"],
            borderwidth=0,
            relief="flat",
            rowheight=24,
        )

        # Heading
        style.configure(
            f"{style_name}.Heading",
            background=colors["heading_bg"],
            foreground=colors["heading_fg"],
            relief="flat",
            borderwidth=0,
        )

        # Map de seleção
        style.map(
            style_name,
            background=[("selected", colors["select_bg"])],
            foreground=[("selected", colors["select_fg"])],
        )

        # Aplicar style no Treeview
        tree.configure(style=style_name)  # type: ignore[attr-defined]

        log.info(f"✅ Treeview tematizado: mode={mode}, style={style_name}")

    except Exception as exc:
        log.error(f"Falha ao configurar style {style_name}: {exc}")


def bind_treeview_to_theme_changes(
    tree: ttk.Treeview,
    theme_manager: GlobalThemeManager,
    *,
    style_name: Optional[str] = None,
) -> None:
    """Vincula Treeview ao theme_manager com cleanup em <Destroy>.

    Registra callback no theme_manager para atualizar o Treeview automaticamente
    quando o usuário alterna entre Light/Dark. Ao destruir o widget, o callback
    é automaticamente desregistrado para evitar memory leaks.

    Args:
        tree: Widget ttk.Treeview
        theme_manager: Instância de GlobalThemeManager
        style_name: Nome do style customizado (passado para apply_treeview_theme)

    Example:
        >>> from src.ui.theme_manager import theme_manager
        >>> tree = ttk.Treeview(parent)
        >>> bind_treeview_to_theme_changes(tree, theme_manager)
    """
    # Aplicar tema inicial
    try:
        from src.ui.ctk_config import ctk

        mode = ctk.get_appearance_mode() if ctk is not None else "Light"
    except Exception:
        mode = "Light"

    apply_treeview_theme(tree, mode, style_name=style_name)

    # Registrar callback para re-aplicar ao alternar tema
    def on_theme_change(new_mode: Literal["Light", "Dark"]) -> None:
        """Callback chamado ao alternar tema."""
        try:
            apply_treeview_theme(tree, new_mode, style_name=style_name)
            log.info(f"🎨 Treeview re-tematizado: {new_mode}")
        except Exception:
            log.exception("Falha ao re-aplicar tema no Treeview")

    theme_manager.register_callback(on_theme_change)
    log.debug("Treeview vinculado ao theme_manager com callback")

    # Cleanup automático ao destruir widget
    def on_destroy(event: Any) -> None:
        """Desregistra callback ao destruir widget."""
        if event.widget is tree:
            try:
                theme_manager.unregister_callback(on_theme_change)
                log.debug("Callback de Treeview desregistrado no <Destroy>")
            except Exception:
                pass

    tree.bind("<Destroy>", on_destroy, add="+")


# ==================== SCROLLBAR ====================


def _get_scrollbar_colors(mode: Literal["Light", "Dark"]) -> dict[str, str]:
    """Retorna palette de cores para Scrollbar baseada no modo."""
    if mode == "Dark":
        return {"bg": "#2b2b2b", "troughcolor": "#1e1e1e", "arrowcolor": "#ffffff"}
    else:  # Light
        return {"bg": "#e5e7eb", "troughcolor": "#f0f0f0", "arrowcolor": "#000000"}


def apply_scrollbar_theme(
    scrollbar: ttk.Scrollbar,
    mode: Literal["Light", "Dark"],
    *,
    master: Optional[tk.Misc] = None,
    style_name: Optional[str] = None,
) -> None:
    """Aplica tema theme-aware em ttk.Scrollbar."""
    if master is None:
        master = scrollbar.master if hasattr(scrollbar, "master") else scrollbar.winfo_toplevel()

    colors = _get_scrollbar_colors(mode)

    try:
        style = ttk.Style(master=master)  # type: ignore[attr-defined]
    except Exception as exc:
        log.error(f"Falha ao criar ttk.Style: {exc}")
        return

    try:
        current_theme = style.theme_use()
        if current_theme != "clam":
            style.theme_use("clam")
    except Exception as exc:
        log.warning(f"Falha ao aplicar tema clam: {exc}")

    orient = str(scrollbar.cget("orient")).lower()
    if style_name is None:
        style_name = f"Themed.{'Vertical' if orient == 'vertical' else 'Horizontal'}.TScrollbar"

    try:
        style.configure(
            style_name,
            background=colors["bg"],
            troughcolor=colors["troughcolor"],
            arrowcolor=colors["arrowcolor"],
            borderwidth=0,
            relief="flat",
        )
        scrollbar.configure(style=style_name)  # type: ignore[attr-defined]
        log.debug(f"✅ Scrollbar tematizado: mode={mode}, style={style_name}")
    except Exception as exc:
        log.error(f"Falha ao configurar style {style_name}: {exc}")


def bind_scrollbar_to_theme_changes(
    scrollbar: ttk.Scrollbar,
    theme_manager: GlobalThemeManager,
    *,
    style_name: Optional[str] = None,
) -> None:
    """Vincula Scrollbar ao theme_manager com cleanup em <Destroy>."""
    try:
        from src.ui.ctk_config import ctk

        mode = ctk.get_appearance_mode() if ctk is not None else "Light"
    except Exception:
        mode = "Light"

    apply_scrollbar_theme(scrollbar, mode, style_name=style_name)

    def on_theme_change(new_mode: Literal["Light", "Dark"]) -> None:
        try:
            if scrollbar.winfo_exists():
                apply_scrollbar_theme(scrollbar, new_mode, style_name=style_name)
                log.debug(f"🎨 Scrollbar re-tematizado: {new_mode}")
        except Exception:
            log.exception("Falha ao re-aplicar tema no Scrollbar")

    theme_manager.register_callback(on_theme_change)

    def on_destroy(event: Any = None) -> None:
        if event and event.widget is scrollbar:
            try:
                theme_manager.unregister_callback(on_theme_change)
                log.debug("Scrollbar callback removido")
            except Exception:
                pass

    scrollbar.bind("<Destroy>", on_destroy, add="+")
    log.debug("Scrollbar vinculado ao theme_manager")


# ==================== PROGRESSBAR ====================


def _get_progressbar_colors(mode: Literal["Light", "Dark"]) -> dict[str, str]:
    """Retorna palette de cores para Progressbar baseada no modo."""
    if mode == "Dark":
        return {"bg": "#2b2b2b", "troughcolor": "#1e1e1e", "pbarcolor": "#3b82f6"}
    else:  # Light
        return {"bg": "#ffffff", "troughcolor": "#e5e7eb", "pbarcolor": "#3b82f6"}


def apply_progressbar_theme(
    progressbar: ttk.Progressbar,
    mode: Literal["Light", "Dark"],
    *,
    master: Optional[tk.Misc] = None,
    style_name: Optional[str] = None,
) -> None:
    """Aplica tema theme-aware em ttk.Progressbar."""
    if master is None:
        master = progressbar.master if hasattr(progressbar, "master") else progressbar.winfo_toplevel()

    colors = _get_progressbar_colors(mode)

    try:
        style = ttk.Style(master=master)  # type: ignore[attr-defined]
    except Exception as exc:
        log.error(f"Falha ao criar ttk.Style: {exc}")
        return

    try:
        current_theme = style.theme_use()
        if current_theme != "clam":
            style.theme_use("clam")
    except Exception as exc:
        log.warning(f"Falha ao aplicar tema clam: {exc}")

    orient = str(progressbar.cget("orient")).lower()
    if style_name is None:
        style_name = f"Themed.{'Horizontal' if orient == 'horizontal' else 'Vertical'}.TProgressbar"

    try:
        style.configure(
            style_name,
            background=colors["pbarcolor"],
            troughcolor=colors["troughcolor"],
            borderwidth=0,
            relief="flat",
        )
        progressbar.configure(style=style_name)  # type: ignore[attr-defined]
        log.debug(f"✅ Progressbar tematizado: mode={mode}, style={style_name}")
    except Exception as exc:
        log.error(f"Falha ao configurar style {style_name}: {exc}")


def bind_progressbar_to_theme_changes(
    progressbar: ttk.Progressbar,
    theme_manager: GlobalThemeManager,
    *,
    style_name: Optional[str] = None,
) -> None:
    """Vincula Progressbar ao theme_manager com cleanup em <Destroy>."""
    try:
        from src.ui.ctk_config import ctk

        mode = ctk.get_appearance_mode() if ctk is not None else "Light"
    except Exception:
        mode = "Light"

    apply_progressbar_theme(progressbar, mode, style_name=style_name)

    def on_theme_change(new_mode: Literal["Light", "Dark"]) -> None:
        try:
            if progressbar.winfo_exists():
                apply_progressbar_theme(progressbar, new_mode, style_name=style_name)
                log.debug(f"🎨 Progressbar re-tematizado: {new_mode}")
        except Exception:
            log.exception("Falha ao re-aplicar tema no Progressbar")

    theme_manager.register_callback(on_theme_change)

    def on_destroy(event: Any = None) -> None:
        if event and event.widget is progressbar:
            try:
                theme_manager.unregister_callback(on_theme_change)
                log.debug("Progressbar callback removido")
            except Exception:
                pass

    progressbar.bind("<Destroy>", on_destroy, add="+")
    log.debug("Progressbar vinculado ao theme_manager")
