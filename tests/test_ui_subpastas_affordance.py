# pyright: reportAttributeAccessIssue=false
# -*- coding: utf-8 -*-
"""
Testes de regressão — affordance real de "subpastas / Arquivos" na UI.

Prova:
1. A actionbar real (ClientesV2ActionBar) NÃO tem botão "Arquivos" nem "Subpastas".
2. O botão "Arquivos" existe dentro do editor de clientes (_editor_ui_mixin.py).
3. O atalho Ctrl+S está mapeado para open_client_storage_subfolders (via keybindings).
4. Dead code removido: create_footer_buttons, FooterButtons, abrir_pasta, abrir_pasta_cliente.
5. Os aliases ver_subpastas() em App e AppActions apontam para o fluxo correto (Supabase).
"""

from __future__ import annotations

import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_BUTTONS = _ROOT / "src" / "ui" / "components" / "buttons.py"
_COMPONENTS_INIT = _ROOT / "src" / "ui" / "components" / "__init__.py"
_ACTIONBAR = _ROOT / "src" / "modules" / "clientes" / "ui" / "views" / "actionbar.py"
_EDITOR_UI = _ROOT / "src" / "modules" / "clientes" / "ui" / "views" / "_editor_ui_mixin.py"
_EDITOR_ACTIONS = _ROOT / "src" / "modules" / "clientes" / "ui" / "views" / "_editor_actions_mixin.py"
_KEYBINDINGS = _ROOT / "src" / "core" / "keybindings.py"
_BOOTSTRAP = _ROOT / "src" / "modules" / "main_window" / "views" / "main_window_bootstrap.py"
_APP_CORE = _ROOT / "src" / "core" / "app_core.py"
_APP_ACTIONS = _ROOT / "src" / "modules" / "main_window" / "app_actions.py"
_MAIN_WINDOW = _ROOT / "src" / "modules" / "main_window" / "views" / "main_window.py"


class TestActionBarNoArquivosButton(unittest.TestCase):
    """A ClientesV2ActionBar não deve ter botão 'Arquivos' ou 'Subpastas'."""

    def test_actionbar_no_arquivos_text(self) -> None:
        source = _ACTIONBAR.read_text(encoding="utf-8")
        # A actionbar cria Novo Cliente, Editar, Excluir, Restaurar.
        # NÃO deve ter "Arquivos" como texto de botão.
        self.assertNotIn(
            'text="Arquivos"',
            source,
            "ActionBar não deve ter botão 'Arquivos' (feature consolidada no editor)",
        )

    def test_actionbar_no_subpastas_text(self) -> None:
        source = _ACTIONBAR.read_text(encoding="utf-8")
        self.assertNotIn(
            'text="Subpastas"',
            source,
            "ActionBar não deve referir 'Subpastas' visualmente",
        )


class TestEditorHasArquivosButton(unittest.TestCase):
    """O editor de clientes DEVE ter o botão 'Arquivos' como ponto de entrada real."""

    def test_editor_ui_creates_arquivos_btn(self) -> None:
        source = _EDITOR_UI.read_text(encoding="utf-8")
        self.assertIn("arquivos_btn", source, "Editor deve criar arquivos_btn")
        self.assertIn('text="Arquivos"', source, "Editor deve rotular botão como 'Arquivos'")

    def test_editor_actions_has_on_arquivos(self) -> None:
        source = _EDITOR_ACTIONS.read_text(encoding="utf-8")
        self.assertIn("def _on_arquivos", source, "Editor deve ter handler _on_arquivos")
        self.assertIn("ClientFilesDialog", source, "Handler deve abrir ClientFilesDialog (Supabase)")


class TestCtrlSMapsToStorageBrowser(unittest.TestCase):
    """O atalho Ctrl+S deve mapear para open_client_storage_subfolders."""

    def test_keybindings_ctrl_s(self) -> None:
        source = _KEYBINDINGS.read_text(encoding="utf-8")
        self.assertIn("<Control-s>", source)
        self.assertIn("subpastas", source)

    def test_bootstrap_wires_subpastas_to_storage(self) -> None:
        source = _BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn(
            "open_client_storage_subfolders",
            source,
            "Bootstrap deve mapear 'subpastas' → open_client_storage_subfolders",
        )


class TestDeadCodeRemoved(unittest.TestCase):
    """Dead code removido: FooterButtons, create_footer_buttons, abrir_pasta, abrir_pasta_cliente."""

    def test_buttons_py_no_create_footer_buttons(self) -> None:
        source = _BUTTONS.read_text(encoding="utf-8")
        self.assertNotIn(
            "def create_footer_buttons",
            source,
            "create_footer_buttons deve ter sido removido (zero callers)",
        )

    def test_buttons_py_no_footer_buttons_class(self) -> None:
        source = _BUTTONS.read_text(encoding="utf-8")
        self.assertNotIn(
            "class FooterButtons",
            source,
            "FooterButtons deve ter sido removido (zero callers)",
        )

    def test_components_init_no_footer_buttons(self) -> None:
        source = _COMPONENTS_INIT.read_text(encoding="utf-8")
        self.assertNotIn("FooterButtons", source)
        self.assertNotIn("create_footer_buttons", source)
        self.assertNotIn("toolbar_button", source)

    def test_app_core_no_abrir_pasta(self) -> None:
        source = _APP_CORE.read_text(encoding="utf-8")
        self.assertNotIn(
            "def abrir_pasta(",
            source,
            "abrir_pasta() deve ter sido removida (dead code, zero callers, msg enganosa)",
        )

    def test_app_core_no_abrir_pasta_cliente(self) -> None:
        source = _APP_CORE.read_text(encoding="utf-8")
        self.assertNotIn(
            "def abrir_pasta_cliente(",
            source,
            "abrir_pasta_cliente() deve ter sido removida (dead code, zero callers)",
        )

    def test_app_core_all_clean(self) -> None:
        source = _APP_CORE.read_text(encoding="utf-8")
        self.assertNotIn('"abrir_pasta"', source, "abrir_pasta não deve estar em __all__")
        self.assertNotIn('"abrir_pasta_cliente"', source, "abrir_pasta_cliente não deve estar em __all__")


class TestVerSubpastasAliasesCorrect(unittest.TestCase):
    """ver_subpastas() em App e AppActions deve ser alias de open_client_storage_subfolders."""

    def test_app_ver_subpastas_delegates(self) -> None:
        source = _MAIN_WINDOW.read_text(encoding="utf-8")
        self.assertIn("def ver_subpastas", source)
        self.assertIn("self.open_client_storage_subfolders()", source)

    def test_app_actions_ver_subpastas_delegates(self) -> None:
        source = _APP_ACTIONS.read_text(encoding="utf-8")
        self.assertIn("def ver_subpastas", source)
        self.assertIn("self.open_client_storage_subfolders()", source)


if __name__ == "__main__":
    unittest.main()
