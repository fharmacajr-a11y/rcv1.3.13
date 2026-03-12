# pyright: reportAttributeAccessIssue=false
# -*- coding: utf-8 -*-
"""
Testes de regressão — remoção final dos caminhos mortos antigos.

Prova que:
1. app_core.py não contém open_client_local_subfolders nem ver_subpastas.
2. forms/__init__.py não contém open_subpastas_dialog / form_cliente / ClientPicker.
3. O fluxo legado externo (subpastas → browser.py) foi removido do bootstrap.
4. Nenhum stub NotImplementedError resta no forms/__init__.py.
"""

from __future__ import annotations

import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_APP_CORE = _ROOT / "src" / "core" / "app_core.py"
_FORMS_INIT = _ROOT / "src" / "modules" / "clientes" / "forms" / "__init__.py"
_BOOTSTRAP = _ROOT / "src" / "modules" / "main_window" / "views" / "main_window_bootstrap.py"


class TestDeadPathRemoved(unittest.TestCase):
    """Validação de que caminhos mortos foram removidos."""

    def test_app_core_no_open_client_local_subfolders(self) -> None:
        source = _APP_CORE.read_text(encoding="utf-8")
        self.assertNotIn(
            "def open_client_local_subfolders",
            source,
            "open_client_local_subfolders deveria ter sido removida (dead code)",
        )

    def test_app_core_no_ver_subpastas(self) -> None:
        source = _APP_CORE.read_text(encoding="utf-8")
        self.assertNotIn(
            "def ver_subpastas",
            source,
            "ver_subpastas deveria ter sido removida de app_core (dead code)",
        )

    def test_forms_no_open_subpastas_dialog(self) -> None:
        source = _FORMS_INIT.read_text(encoding="utf-8")
        self.assertNotIn(
            "def open_subpastas_dialog",
            source,
            "open_subpastas_dialog stub deveria ter sido removido (zero callers)",
        )

    def test_forms_no_form_cliente(self) -> None:
        source = _FORMS_INIT.read_text(encoding="utf-8")
        self.assertNotIn(
            "def form_cliente",
            source,
            "form_cliente stub deveria ter sido removido (zero callers desde P0)",
        )

    def test_forms_no_client_picker(self) -> None:
        source = _FORMS_INIT.read_text(encoding="utf-8")
        self.assertNotIn(
            "class ClientPicker",
            source,
            "ClientPicker stub deveria ter sido removido (zero callers)",
        )

    def test_forms_no_not_implemented_error(self) -> None:
        source = _FORMS_INIT.read_text(encoding="utf-8")
        self.assertNotIn(
            "NotImplementedError",
            source,
            "Nenhum NotImplementedError deve restar em forms/__init__.py",
        )

    def test_bootstrap_no_legacy_subpastas(self) -> None:
        source = _BOOTSTRAP.read_text(encoding="utf-8")
        self.assertNotIn(
            "open_client_storage_subfolders",
            source,
            "Bootstrap não deve mais referenciar open_client_storage_subfolders (fluxo externo removido)",
        )
        self.assertNotIn(
            '"subpastas"',
            source,
            "Bootstrap não deve mais mapear handler 'subpastas' (fluxo externo removido)",
        )

    def test_forms_exports_only_active_code(self) -> None:
        """__all__ não deve exportar nenhum stub deprecated."""
        source = _FORMS_INIT.read_text(encoding="utf-8")
        for name in ("form_cliente", "ClientPicker", "open_subpastas_dialog"):
            self.assertNotIn(
                f'"{name}"',
                source,
                f"{name} não deveria estar em __all__ (foi removido)",
            )


if __name__ == "__main__":
    unittest.main()
