# ui/dialogs/__init__.py
"""Diálogos da UI."""

from src.ui.dialogs.storage_uploader import (
    StorageDestinationDialog,
    enviar_para_supabase_avancado,
)

__all__ = [
    "StorageDestinationDialog",
    "enviar_para_supabase_avancado",
]
