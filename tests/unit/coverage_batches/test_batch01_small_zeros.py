"""
Batch 01: Import-smoke tests para módulos com 0% de cobertura (poucos statements).
Objetivo: aumentar cobertura rapidamente sem depender de GUI funcional.
"""

from __future__ import annotations

import importlib

import pytest

# Lista de módulos com 0% e <= 15 statements (gerada via reports/coverage.json)
BATCH_01_MODULES = [
    "src.ui.hub.colors",
    "src.ui.hub.constants",
    "src.ui.hub.controller",
    "src.ui.hub.format",
    "src.ui.hub.layout",
    "src.ui.hub.panels",
    "src.ui.hub.state",
    "src.ui.hub.utils",
    "src.utils.file_utils.zip_utils",
    "src.ui.hub.actions",
    "src.ui.hub.authors",
    "src.ui.login.__init__",
    "src.ui.main_window.app",
    "src.ui.main_window.frame_factory",
    "src.ui.main_window.router",
    "src.ui.main_window.tk_report",
    "src.ui.hub.__init__",
    "src.ui.hub_screen",
    "src.ui.lixeira.__init__",
    "src.ui.lixeira.lixeira",
    # "src.ui.passwords_screen",  # Removido na migração
    # "src.modules.clientes.forms.pipeline",  # Removido na migração
    # "src.ui.main_screen",  # Deprecated, MainScreenFrame não exportado mais
    "src.ui.widgets.client_picker",
    "src.modules.forms.actions",
]


@pytest.mark.parametrize("module_name", BATCH_01_MODULES)
def test_import_smoke(module_name: str) -> None:
    """
    Import-smoke test: tenta importar o módulo.
    Se falhar por TclError (Tk não disponível), skip.
    Qualquer outro erro: FAIL.
    """
    try:
        importlib.import_module(module_name)
    except Exception as exc:
        # Check se é erro relacionado a Tcl/Tk
        exc_str = str(exc).lower()
        exc_type = type(exc).__name__

        if exc_type == "TclError" or "tk.tcl" in exc_str or "init.tcl" in exc_str or "_tkinter" in exc_str:
            pytest.skip(f"Ambiente sem Tcl/Tk funcional: {exc_type}: {exc}")

        # Qualquer outro erro: FAIL
        raise
