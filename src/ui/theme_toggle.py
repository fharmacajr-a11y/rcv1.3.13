# ui/theme_toggle.py
from __future__ import annotations

from ttkbootstrap import Style


def toggle_theme(style: Style):
    """
    Alterna entre tema claro e escuro sem reiniciar o app.

    Args:
        style: Objeto Style do ttkbootstrap
    """
    darks = {"darkly", "cyborg", "superhero", "vapor"}
    now = style.theme.name
    # escolhe um "par" simples
    newt = "flatly" if now in darks else "darkly"
    style.theme_use(newt)


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
