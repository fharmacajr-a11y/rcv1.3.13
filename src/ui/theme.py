# ui/theme.py
from __future__ import annotations
import tkinter as tk
from tkinter import font as tkfont
from ttkbootstrap import Style

DEFAULT_THEME = "flatly"  # pode trocar para "darkly" se preferir escuro
DEFAULT_SCALING = 1.25  # escala para monitores 125%; ajuste se necessário


def init_theme(
    root: tk.Tk, theme: str = DEFAULT_THEME, scaling: float = DEFAULT_SCALING
) -> Style:
    """
    Inicializa o tema do ttkbootstrap e ajusta a escala do Tk.

    Args:
        root: Janela principal Tk
        theme: Nome do tema ttkbootstrap (ex: "flatly", "darkly", "cosmo")
        scaling: Fator de escala para DPI (1.0 = 100%, 1.25 = 125%, 1.5 = 150%)

    Returns:
        Style: Objeto de estilo do ttkbootstrap
    """
    # Ajuste de escala do Tk (pontos -> pixels); ajuda em 125/150% sem distorcer fontes
    try:
        root.tk.call("tk", "scaling", scaling)
    except Exception:
        pass

    style = Style(theme=theme)  # tema ttkbootstrap

    # Configurar fontes via fontes nomeadas (evita parsing ambíguo de "Segoe UI 10")
    # Usar nametofont é seguro para nomes de fonte com espaços (ex: "Segoe UI", "Courier New")
    try:
        base = 10
        size = int(round(base * scaling))
        for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
            f = tkfont.nametofont(name)
            f.configure(family="Segoe UI", size=size)
    except Exception:
        pass

    return style
