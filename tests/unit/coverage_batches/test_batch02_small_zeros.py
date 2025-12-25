"""
Batch 02: Import-smoke tests para módulos restantes com 0% de cobertura (<=15 statements).
"""

from __future__ import annotations

import importlib

import pytest

# Módulos restantes com 0% e <= 15 statements (após batch01)
BATCH_02_MODULES = [
    "src.ui.main_window",
    "src.utils.perf",
    "src.ui.login.login",
]


@pytest.mark.parametrize("module_name", BATCH_02_MODULES)
@pytest.mark.filterwarnings("ignore::DeprecationWarning")
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
