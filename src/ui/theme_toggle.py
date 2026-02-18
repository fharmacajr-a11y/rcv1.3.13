# -*- coding: utf-8 -*-
"""Theme Toggle - Wrapper fino do GlobalThemeManager.

Delega tudo para src.ui.theme_manager.GlobalThemeManager (CustomTkinter).
"""

from __future__ import annotations

from typing import Literal

from src.ui.ctk_config import HAS_CUSTOMTKINTER


def toggle_theme(style_or_app: object = None) -> str:
    """Alterna entre tema claro, escuro e system em ciclo.

    Args:
        style_or_app: IGNORADO (mantido para compatibilidade)

    Returns:
        Nome do novo modo aplicado ("light" ou "dark")
    """
    if HAS_CUSTOMTKINTER:
        from src.ui.theme_manager import theme_manager

        new_mode = theme_manager.toggle_mode()
        return new_mode
    # CustomTkinter é obrigatório - sem fallback
    return "light"


def get_mode() -> str:
    """Retorna o modo de aparência atual (light/dark).

    Returns:
        Modo atual: "light" ou "dark"
    """
    if HAS_CUSTOMTKINTER:
        from src.ui.theme_manager import theme_manager

        return theme_manager.get_current_mode()
    # CustomTkinter é obrigatório - sem fallback
    return "light"


def set_mode(mode: Literal["light", "dark"]) -> None:
    """Define o modo de aparência.

    Args:
        mode: Modo desejado ("light" ou "dark")
    """
    # Fallback para "light" se modo inválido (ex: "system" legado)
    valid_mode: Literal["light", "dark"] = "light" if mode not in ["light", "dark"] else mode

    if HAS_CUSTOMTKINTER:
        from src.ui.theme_manager import theme_manager

        theme_manager.set_mode(valid_mode)  # type: ignore[arg-type]
    # CustomTkinter é obrigatório - sem fallback


def get_effective_mode() -> Literal["light", "dark"]:
    """Retorna o modo efetivo (sempre 'light' ou 'dark').

    Returns:
        Modo efetivo resolvido
    """
    if HAS_CUSTOMTKINTER:
        from src.ui.theme_manager import theme_manager

        return theme_manager.get_effective_mode()
    else:
        mode = get_mode()
        return "dark" if mode == "dark" else "light"


def is_dark_mode() -> bool:
    """Verifica se o modo atual é dark.

    Returns:
        True se o modo atual for dark
    """
    return get_effective_mode() == "dark"


def get_available_themes() -> list[str]:
    """Retorna lista de modos disponíveis (light/dark).

    Returns:
        Lista de modos
    """
    return ["light", "dark"]


def is_dark_theme(theme_name: str) -> bool:
    """Verifica se um modo é escuro.

    Args:
        theme_name: Nome do modo ("light" ou "dark")

    Returns:
        True se o modo for escuro
    """
    return theme_name.lower().strip() == "dark"


__all__ = [
    "toggle_theme",
    "get_mode",
    "set_mode",
    "get_effective_mode",
    "is_dark_mode",
    "is_dark_theme",
    "get_available_themes",
]
