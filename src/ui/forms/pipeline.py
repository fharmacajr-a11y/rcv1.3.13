"""DEPRECATED: Este módulo será removido em versão futura.

Use: from src.modules.clientes.forms.pipeline import validate_inputs, prepare_payload, perform_uploads, finalize_state
"""

from __future__ import annotations

import warnings

warnings.warn(
    "src.ui.forms.pipeline está deprecated. Use src.modules.clientes.forms.pipeline",
    DeprecationWarning,
    stacklevel=2,
)

from src.modules.clientes.forms.pipeline import (  # noqa: F401
    finalize_state,
    perform_uploads,
    prepare_payload,
    validate_inputs,
)

__all__ = ["validate_inputs", "prepare_payload", "perform_uploads", "finalize_state"]
