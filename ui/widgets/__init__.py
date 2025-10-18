# ui/widgets/__init__.py
from __future__ import annotations

__all__ = ["BusyOverlay"]

try:
    from ui.widgets.busy import BusyOverlay
except ImportError:
    pass
