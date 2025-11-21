# -*- coding: utf-8 -*-
"""
DEPRECATED: Este módulo é mantido apenas para retrocompatibilidade.
Use: from src.ui.files_browser import open_files_browser

Este arquivo será removido em versão futura.
Toda a lógica foi movida para o pacote src.ui.files_browser/
"""

# Mantém API pública para retrocompatibilidade
from src.ui.files_browser import open_files_browser

# Re-export para compatibilidade com imports antigos
# Nota: format_cnpj_for_display estava sendo importado erroneamente deste módulo
# mas na verdade vem de src.modules.uploads.components.helpers
from src.modules.uploads.components.helpers import format_cnpj_for_display

__all__ = ["open_files_browser", "format_cnpj_for_display"]
