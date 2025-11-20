"""View principal do módulo Forms/Cadastros.

Este módulo encapsula a UI legada de formulários (`src.ui.forms`)
e reexporta os principais entrypoints usados pelo restante da
aplicação.

A ideia é que, no futuro, qualquer ajuste visual dos cadastros
seja feito aqui, sem precisar mexer diretamente em `src/ui/forms/*`.
"""

from __future__ import annotations

from src.modules.clientes.forms import SubpastaDialog, form_cliente
from src.ui.forms.actions import download_file, list_storage_objects

__all__ = [
    "form_cliente",
    "SubpastaDialog",
    "download_file",
    "list_storage_objects",
]
