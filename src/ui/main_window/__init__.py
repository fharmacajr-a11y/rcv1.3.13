"""DEPRECATED: Este pacote será removido em versão futura.

Use:
    from src.modules.main_window.views.main_window import App
    from src.modules.main_window.controller import create_frame, navigate_to, tk_report
"""

import warnings

warnings.warn(
    "src.ui.main_window está deprecated. Use src.modules.main_window",
    DeprecationWarning,
    stacklevel=2,
)

from .app import App  # noqa: E402
from .frame_factory import create_frame as create_frame  # noqa: E402
from .router import navigate_to as navigate_to  # noqa: E402
from .tk_report import tk_report as tk_report  # noqa: E402

__all__ = ["App", "create_frame", "navigate_to", "tk_report"]
