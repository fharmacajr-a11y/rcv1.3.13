"""Actions wrapper for Hub UI.

UPDATED: Import directly from lifecycle_service instead of legacy shim.
"""

from src.modules.hub.services.lifecycle_service import handle_screen_shown

# Re-export for backward compatibility
__all__ = ["handle_screen_shown"]
