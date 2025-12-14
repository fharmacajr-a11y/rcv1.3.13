"""
DEPRECATED: Este módulo é legado e será removido em versão futura.

Use: src.modules.forms.actions

Motivo: Migração de src.ui.* para src.modules.* (LEGADO-MIGRATE-01)
Este arquivo agora é apenas um shim de compatibilidade que reexporta
os símbolos do módulo oficial.

Código novo deve importar de src.modules.forms.actions diretamente.
"""

from src.modules.forms.actions import (
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
        from src.modules.forms.actions import SubpastaDialog

        return SubpastaDialog
    raise AttributeError(f"module {__name__} has no attribute {name!r}")
