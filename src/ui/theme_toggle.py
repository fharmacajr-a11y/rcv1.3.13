# -*- coding: utf-8 -*-
"""Theme Toggle - Wrapper fino do GlobalThemeManager.

MICROFASE 24+: Este módulo é um wrapper de compatibilidade para o
GlobalThemeManager (src.ui.theme_manager). Mantém interface antiga
para não quebrar código existente, mas delega tudo para o ThemeManager.

NÃO usar ttkbootstrap ou src.utils.themes aqui quando CTk está disponível.
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
    """Retorna lista de temas/modos disponíveis.

    Returns:
        Lista de modos quando CTk ativo, ou temas legados caso contrário
    """
    if HAS_CUSTOMTKINTER:
        return ["light", "dark"]
    else:
        # Lista completa de temas ttkbootstrap para compatibilidade
        return [
            "cosmo",
            "flatly",
            "journal",
            "litera",
            "lumen",
            "minty",
            "pulse",
            "sandstone",
            "united",
            "yeti",
            "morph",
            "simplex",
            "cerulean",
            "solar",
            "superhero",
            "darkly",
            "cyborg",
            "vapor",
        ]


def is_dark_theme(theme_name: str) -> bool:
    """Verifica se um tema/modo é escuro.

    Args:
        theme_name: Nome do tema ou modo

    Returns:
        True se o tema/modo for escuro
    """
    # Normalizar
    name = theme_name.lower().strip()

    # Modos CustomTkinter
    if name == "dark":
        return True
    elif name == "light":
        return False
    elif name == "system":  # Fallback legado
        return False

    # Temas ttkbootstrap legados
    darks = {"darkly", "cyborg", "superhero", "vapor", "solar"}
    return name in darks


__all__ = [
    "toggle_theme",
    "get_mode",
    "set_mode",
    "get_effective_mode",
    "is_dark_mode",
    "is_dark_theme",
    "get_available_themes",
]
