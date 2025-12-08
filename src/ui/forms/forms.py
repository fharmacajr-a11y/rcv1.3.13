"""DEPRECATED: Este módulo será removido em versão futura.

Use: from src.modules.clientes.forms import form_cliente

Nota: O DeprecationWarning é emitido via __getattr__ em __init__.py,
apenas quando form_cliente é realmente acessado.
"""

from __future__ import annotations

from typing import Any

__all__ = ["form_cliente"]


def form_cliente(*args: Any, **kwargs: Any):
    """Proxy para src.modules.clientes.forms.form_cliente."""
    from src.modules.clientes.forms import form_cliente as _form_cliente_impl

    return _form_cliente_impl(*args, **kwargs)
