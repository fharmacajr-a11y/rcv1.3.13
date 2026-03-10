"""
Formularios e dialogos especificos do dominio de clientes.

Contém utilitários de validação de duplicatas e o diálogo
moderno SubpastaDialog (CustomTkinter).
"""

from ._dupes import (
    ask_razao_confirm,
    build_cnpj_warning,
    build_razao_confirm,
    has_cnpj_conflict,
    has_razao_conflict,
    show_cnpj_warning_and_abort,
)

from .client_subfolder_prompt import SubpastaDialog

__all__ = [
    # Utilitários de validação (ativos)
    "build_cnpj_warning",
    "build_razao_confirm",
    "has_cnpj_conflict",
    "has_razao_conflict",
    "show_cnpj_warning_and_abort",
    "ask_razao_confirm",
    # Dialog moderno (ativo)
    "SubpastaDialog",
]
