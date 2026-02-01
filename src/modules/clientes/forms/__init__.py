"""
Formularios e dialogos especificos do dominio de clientes.

AVISO: form_cliente, ClientPicker e open_subpastas_dialog foram DESCONTINUADOS.
Arquivos legados movidos para docs/_archive/clientes_forms/ (fora do runtime).

Use os substitutos modernos CustomTkinter:
- form_cliente → ClientEditorDialog (src.modules.clientes.ui.views.client_editor_dialog)
- ClientPicker → (usar treeview direta em ClientesV2Frame)
- open_subpastas_dialog → SubpastaDialog (src.modules.clientes.forms.client_subfolder_prompt)
"""

import warnings
from typing import Any

from ._dupes import (
    ask_razao_confirm,
    build_cnpj_warning,
    build_razao_confirm,
    has_cnpj_conflict,
    has_razao_conflict,
    show_cnpj_warning_and_abort,
)


# Stubs deprecados (compatibilidade legada)
def form_cliente(*args: Any, **kwargs: Any) -> None:
    """DESCONTINUADO: Use ClientEditorDialog (CustomTkinter).

    Este formulário legado (Tkinter/ttkbootstrap) foi removido do runtime.
    Código arquivado em: docs/_archive/clientes_forms/

    Raises:
        DeprecationWarning: Sempre - função descontinuada
        NotImplementedError: Se realmente chamado
    """
    warnings.warn(
        "form_cliente está DESCONTINUADO. Use ClientEditorDialog (src.modules.clientes.ui.views.client_editor_dialog)",
        DeprecationWarning,
        stacklevel=2,
    )
    raise NotImplementedError(
        "form_cliente foi removido. Use ClientEditorDialog (CTk).\n"
        "Código legado arquivado em: docs/_archive/clientes_forms/"
    )


class ClientPicker:
    """DESCONTINUADO: Use treeview direta em ClientesV2Frame.

    Este picker legado (Tkinter) foi removido do runtime.
    Código arquivado em: docs/_archive/clientes_forms/
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        warnings.warn(
            "ClientPicker está DESCONTINUADO. Use treeview em ClientesV2Frame",
            DeprecationWarning,
            stacklevel=2,
        )
        raise NotImplementedError(
            "ClientPicker foi removido.\n" "Código legado arquivado em: docs/_archive/clientes_forms/"
        )


def open_subpastas_dialog(*args: Any, **kwargs: Any) -> None:
    """DESCONTINUADO: Use SubpastaDialog.

    Esta dialog legada foi substituída por SubpastaDialog (CustomTkinter).
    Código arquivado em: docs/_archive/clientes_forms/

    Raises:
        DeprecationWarning: Sempre - função descontinuada
        NotImplementedError: Se realmente chamado
    """
    warnings.warn(
        "open_subpastas_dialog está DESCONTINUADO. Use SubpastaDialog",
        DeprecationWarning,
        stacklevel=2,
    )
    raise NotImplementedError(
        "open_subpastas_dialog foi removido. Use SubpastaDialog.\n"
        "Código legado arquivado em: docs/_archive/clientes_forms/"
    )


from .client_subfolder_prompt import SubpastaDialog

__all__ = [
    # Descontinuados (stubs apenas)
    "form_cliente",
    "ClientPicker",
    "open_subpastas_dialog",
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
