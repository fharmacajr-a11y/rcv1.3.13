"""Authors wrapper for Hub UI.

UPDATED: Import directly from authors_service instead of legacy shim.
"""

from src.modules.hub.services.authors_service import (
    debug_resolve_author,
    get_author_display_name,
)

# Re-export for backward compatibility
__all__ = ["get_author_display_name", "debug_resolve_author"]
