"""View principal do módulo Forms/Cadastros.

Este módulo encapsula funcionalidades de formulários e
reexporta ações de storage (download_file, list_storage_objects).

Para formulários de clientes específicos, importe diretamente de:
- src.modules.clientes.forms.client_form (form_cliente)
- src.modules.clientes.forms.client_subfolder_prompt (SubpastaDialog)
"""

from __future__ import annotations

from typing import Any

from src.modules.forms.actions import download_file, list_storage_objects

__all__ = [
    "download_file",
    "list_storage_objects",
]


def __getattr__(name: str) -> Any:
    """Lazy import de SubpastaDialog para compatibilidade com código legado."""
    if name == "SubpastaDialog":
        from src.modules.clientes.forms.client_subfolder_prompt import SubpastaDialog as _SubpastaDialog

        return _SubpastaDialog
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
