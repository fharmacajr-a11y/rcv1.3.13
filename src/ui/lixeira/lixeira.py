"""DEPRECATED: Este módulo será removido em versão futura.

Use: from src.modules.lixeira.views.lixeira import abrir_lixeira, refresh_if_open
"""

import warnings

warnings.warn(
    "src.ui.lixeira.lixeira está deprecated. Use src.modules.lixeira.views.lixeira",
    DeprecationWarning,
    stacklevel=2,
)

from src.modules.lixeira.views.lixeira import abrir_lixeira, refresh_if_open  # noqa: E402

__all__ = ["abrir_lixeira", "refresh_if_open"]
