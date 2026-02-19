"""DEPRECATED: Este pacote será removido em versão futura.

Use: from src.modules.hub import ...
"""

import warnings

warnings.warn(
    "src.ui.hub está deprecated. Use src.modules.hub",
    DeprecationWarning,
    stacklevel=2,
)

from src.modules.hub import *  # noqa: E402,F401,F403
