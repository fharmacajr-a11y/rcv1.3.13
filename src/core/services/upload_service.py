"""Shim de compatibilidade para servicos de upload legado."""

from __future__ import annotations

from src.modules.uploads.service import upload_folder_to_supabase

__all__ = ["upload_folder_to_supabase"]
