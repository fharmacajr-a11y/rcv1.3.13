"""View principal do módulo Notas/Hub.

Este módulo encapsula a UI legada do Hub (notas, mural) exposta em
`src.ui.hub_screen`, permitindo que o restante da aplicação use
uma interface estável para acessar a tela de notas.
"""

from __future__ import annotations

from typing import Any

from src.ui.hub_screen import HubScreen

__all__ = ["HubFrame"]


class HubFrame(HubScreen):
    """Alias tipado para a tela principal do Hub/Notas."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
