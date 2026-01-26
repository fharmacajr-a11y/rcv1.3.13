"""
Formularios e dialogos especificos do dominio de clientes.

NOTA: Módulos legados foram movidos para _archived/.
Este __init__.py mantém compatibilidade importando de lá.
"""

from ._dupes import (
    ask_razao_confirm,
    build_cnpj_warning,
    build_razao_confirm,
    has_cnpj_conflict,
    has_razao_conflict,
    show_cnpj_warning_and_abort,
)

# Imports de módulos arquivados (compatibilidade legada)
try:
    from ._archived.client_form import form_cliente
except (ImportError, ModuleNotFoundError):
    # Fallback: se client_form não existir, definir stub
    def form_cliente(*args, **kwargs):  # type: ignore[misc]
        raise NotImplementedError("form_cliente foi movido/removido. Use ClientEditorDialog (CTk).")


try:
    from ._archived.client_picker import ClientPicker
except (ImportError, ModuleNotFoundError):
    # Fallback: se client_picker não existir, definir stub
    class ClientPicker:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):  # type: ignore[misc]
            raise NotImplementedError("ClientPicker foi movido/removido.")


from .client_subfolder_prompt import SubpastaDialog

try:
    from ._archived.client_subfolders_dialog import open_subpastas_dialog
except (ImportError, ModuleNotFoundError):
    # Fallback: se não existir, definir stub
    def open_subpastas_dialog(*args, **kwargs):  # type: ignore[misc]
        raise NotImplementedError("open_subpastas_dialog foi movido/removido.")


__all__ = [
    "form_cliente",
    "ClientPicker",
    "SubpastaDialog",
    "open_subpastas_dialog",
]

__all__ += [
    "build_cnpj_warning",
    "build_razao_confirm",
    "has_cnpj_conflict",
    "has_razao_conflict",
    "show_cnpj_warning_and_abort",
    "ask_razao_confirm",
]
