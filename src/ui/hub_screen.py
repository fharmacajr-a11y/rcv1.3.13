"""DEPRECATED: Este módulo será removido em versão futura.

Use: from src.modules.hub.views.hub_screen import HubScreen
"""

import warnings

warnings.warn(
    "src.ui.hub_screen está deprecated. Use src.modules.hub.views.hub_screen",
    DeprecationWarning,
    stacklevel=2,
)

from src.modules.hub.views.hub_screen import HubScreen

__all__ = ["HubScreen"]
