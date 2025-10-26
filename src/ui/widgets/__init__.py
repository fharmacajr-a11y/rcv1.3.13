# ui/widgets/__init__.py
from __future__ import annotations

__all__ = ["BusyOverlay"]

try:
    from src.ui.widgets.busy import BusyOverlay
except ImportError:
    pass
