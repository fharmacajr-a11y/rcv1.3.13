from __future__ import annotations

from typing import Any

from application.api import api_clients, api_files, api_notes

__all__ = ["register_endpoints"]


def register_endpoints(app: Any):
    """Keep compatibility with existing endpoint registration."""
    _ = (api_clients, api_files, api_notes)  # referenced to appease linters
    return app
