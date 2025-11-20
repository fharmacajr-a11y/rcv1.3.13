"""
Shims para manter compatibilidade de import com os formularios legados.
"""

from __future__ import annotations

from typing import Any

__all__ = ["form_cliente"]


def form_cliente(*args: Any, **kwargs: Any):
    from src.modules.clientes.forms import form_cliente as _form_cliente_impl

    return _form_cliente_impl(*args, **kwargs)
