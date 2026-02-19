from __future__ import annotations

from typing import Any

from src.core.api import api_clients, api_files, api_notes

__all__ = ["register_endpoints"]


def register_endpoints(app: Any) -> Any:
    """Return the unchanged app instance while ensuring API modules stay imported."""
    _ = (api_clients, api_files, api_notes)  # referenced to appease linters
    return app
