"""
Shim para manter compatibilidade com o pipeline legado de uploads de clientes.
"""

from __future__ import annotations

from src.modules.clientes.forms.pipeline import (  # noqa: F401
    finalize_state,
    perform_uploads,
    prepare_payload,
    validate_inputs,
)

__all__ = ["validate_inputs", "prepare_payload", "perform_uploads", "finalize_state"]
