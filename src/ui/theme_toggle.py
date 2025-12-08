# ui/theme_toggle.py
from __future__ import annotations

from typing import Any


def toggle_theme(style_or_app: Any = None) -> str:
    """
    Alterna entre tema claro e escuro usando utils.themes como fonte da verdade.

    Args:
        style_or_app: Objeto Style do ttkbootstrap ou app principal (opcional)

    Returns:
        Nome do novo tema aplicado
    """
    from src.utils import themes

    # Delega para utils.themes que gerencia persistência e aplicação
    new_theme = themes.toggle_theme(app=style_or_app)
    return new_theme


def get_available_themes() -> list[str]:
    """
    Retorna lista de temas disponíveis no ttkbootstrap.

    Returns:
        Lista de nomes de temas
    """
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
    """
    Verifica se um tema é escuro.

    Args:
        theme_name: Nome do tema

    Returns:
        True se o tema for escuro
    """
    darks = {"darkly", "cyborg", "superhero", "vapor", "solar"}
    return theme_name.lower() in darks
