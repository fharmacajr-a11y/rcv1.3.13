"""
Ações de formulários - entrypoint público (módulo oficial).

Este módulo é o ponto de entrada oficial para todas as ações de formulários.
Código novo deve importar daqui, não de src.ui.forms.actions (legado).

Símbolos disponíveis:
- preencher_via_pasta: Preenche campos do formulário a partir de Cartão CNPJ em pasta
- salvar_e_enviar_para_supabase: Salvar + enviar documentos para armazenamento externo
- list_storage_objects: Lista objetos do Storage
- download_file: Download de arquivo do Storage
- SubpastaDialog: Dialog de seleção de subpastas (lazy import)
- salvar_e_upload_docs: DEPRECATED, use UploadDialog

Exemplo:
    from src.modules.forms.actions import preencher_via_pasta, SubpastaDialog
"""

from .actions_impl import (
    download_file,
    list_storage_objects,
    preencher_via_pasta,
    salvar_e_enviar_para_supabase,
    salvar_e_upload_docs,
)

__all__ = [
    "preencher_via_pasta",
    "salvar_e_enviar_para_supabase",
    "list_storage_objects",
    "download_file",
    "salvar_e_upload_docs",
]


def __getattr__(name: str):
    """Lazy import de SubpastaDialog para evitar ciclos de import."""

    if name == "SubpastaDialog":
        from .actions_impl import SubpastaDialog

        return SubpastaDialog
    raise AttributeError(f"module {__name__} has no attribute {name!r}")
