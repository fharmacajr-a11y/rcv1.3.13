# -*- coding: utf-8 -*-
"""
⚠️ DEPRECATED: Este módulo é mantido apenas para retrocompatibilidade.

A funcionalidade de navegação de arquivos foi movida para:
    src.modules.uploads.views.browser.UploadsBrowserWindow

Use a API pública:
    from src.modules.uploads import open_files_browser

Este arquivo será removido em versão futura.
"""

# Mantém re-export direto para compatibilidade com imports antigos
from src.modules.uploads import open_files_browser
from src.modules.uploads.components.helpers import format_cnpj_for_display

__all__ = ["open_files_browser", "format_cnpj_for_display"]
