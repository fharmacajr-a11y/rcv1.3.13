"""View principal do modulo Lixeira.

Encapsula a UI da Lixeira em utilitarios compatíveis com o app,
expondo wrappers finos para abertura e refresh.
"""

from __future__ import annotations

from typing import Any

from src.modules.lixeira.views.lixeira import abrir_lixeira as _abrir_lixeira
from src.modules.lixeira.views.lixeira import refresh_if_open as _refresh_if_open


class LixeiraFrame:
    """Alias tipado/compatível para abertura da janela da Lixeira."""

    def __new__(cls, *args: Any, **kwargs: Any):
        return _abrir_lixeira(*args, **kwargs)


def abrir_lixeira(*args: Any, **kwargs: Any):
    """Wrapper fino para a função legada `abrir_lixeira`."""
    return _abrir_lixeira(*args, **kwargs)


def refresh_if_open() -> None:
    """Wrapper fino para `refresh_if_open` da UI legada."""
    _refresh_if_open()
