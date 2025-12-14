"""DEPRECATED: src.ui.forms está deprecated. Use src.modules.clientes.forms.

Este pacote mantém compatibilidade retroativa mas emitirá DeprecationWarning
quando form_cliente for acessado.
"""

from __future__ import annotations

import warnings
from typing import Any

# __all__ removido - form_cliente é carregado via __getattr__ lazy import


def __getattr__(name: str) -> Any:
    """Lazy import com deprecation warning apenas quando atributo é acessado."""
    if name == "form_cliente":
        warnings.warn(
            "src.ui.forms.form_cliente está deprecated. Use src.modules.clientes.forms.form_cliente",
            DeprecationWarning,
            stacklevel=2,
        )
        from .forms import form_cliente

        return form_cliente

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
