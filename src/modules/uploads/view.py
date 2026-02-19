"""Wrappers públicos para o navegador de arquivos modular."""

from __future__ import annotations

from typing import Any

from src.modules.uploads.views import browser as browser_view


class UploadsFrame:
    """Alias compatível para abrir o navegador de arquivos."""

    def __new__(cls, *args: Any, **kwargs: Any):
        return browser_view.open_files_browser(*args, **kwargs)


def open_files_browser(*args: Any, **kwargs: Any):
    """Reexporta o navegador modular, preservando assinatura compatível."""
    return browser_view.open_files_browser(*args, **kwargs)
