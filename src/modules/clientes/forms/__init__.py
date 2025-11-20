"""
Formularios e dialogos especificos do dominio de clientes.
"""

from ._dupes import (
    ask_razao_confirm,
    build_cnpj_warning,
    build_razao_confirm,
    has_cnpj_conflict,
    has_razao_conflict,
    show_cnpj_warning_and_abort,
)
from .client_form import form_cliente
from .client_picker import ClientPicker
from .client_subfolder_prompt import SubpastaDialog
from .client_subfolders_dialog import open_subpastas_dialog

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
