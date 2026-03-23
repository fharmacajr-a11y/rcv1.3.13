# pyright: reportAttributeAccessIssue=false
# -*- coding: utf-8 -*-
"""
Testes de regressão — P2 fixes (FASE 3 estabilização clientes).

P2-3: _on_new_client respeita guard de reentrância (_opening_editor / _editor_dialog).
P2-4: refresh_theme reconfigura order_combo e status_combo (não só entry_search).

Nota: P2-1 e P2-2 foram removidos junto com os mixins do V1b
      (_files_download_mixin.py e _files_navigation_mixin.py — Fase 1 migração browser).
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_ROOT = Path(__file__).resolve().parent.parent
_VIEW_PY = _ROOT / "src" / "modules" / "clientes" / "ui" / "view.py"
_TOOLBAR_PY = _ROOT / "src" / "modules" / "clientes" / "ui" / "views" / "toolbar.py"


# ============================================================================
# P2-3: _on_new_client sem guard de reentrância
# ============================================================================


class TestP23NewClientReentrancy(unittest.TestCase):
    """P2-3: _on_new_client delega para _open_client_editor, que possui todos os guards de reentrância.

    Após refatoração (FASE 7B.5), _on_new_client é um wrapper de 1 linha que chama
    _open_client_editor(new_client=True). Os guards de reentrância vivem em
    _open_client_editor — verificamos o método correto.
    """

    def _get_method_source(self, method_name: str) -> str:
        """Extrai source do método especificado de view.py."""
        source = _VIEW_PY.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == method_name:
                return ast.get_source_segment(source, node) or ""
        return ""

    def test_on_new_client_delegates_to_open_editor(self) -> None:
        """_on_new_client delega para _open_client_editor com new_client=True."""
        src = self._get_method_source("_on_new_client")
        self.assertIn("_open_client_editor", src, "_on_new_client deve delegar para _open_client_editor")
        self.assertIn("new_client=True", src, "_on_new_client deve passar new_client=True")

    def test_checks_opening_editor_flag(self) -> None:
        """_open_client_editor (usado por _on_new_client) checa self._opening_editor."""
        src = self._get_method_source("_open_client_editor")
        self.assertIn("_opening_editor", src, "_open_client_editor não checa _opening_editor")

    def test_checks_editor_dialog_reference(self) -> None:
        """_open_client_editor (usado por _on_new_client) checa self._editor_dialog existente."""
        src = self._get_method_source("_open_client_editor")
        self.assertIn("_editor_dialog", src, "_open_client_editor não checa _editor_dialog")

    def test_sets_opening_editor_true_before_creation(self) -> None:
        """_open_client_editor (usado por _on_new_client) seta _opening_editor = True antes de criar diálogo."""
        src = self._get_method_source("_open_client_editor")
        self.assertIn("self._opening_editor = True", src, "_open_client_editor não seta _opening_editor = True")

    def test_resets_opening_editor_on_exception(self) -> None:
        """_open_client_editor (usado por _on_new_client) reseta _opening_editor no except."""
        src = self._get_method_source("_open_client_editor")
        self.assertIn("self._opening_editor = False", src, "_open_client_editor não reseta _opening_editor no except")
        self.assertIn("self._editor_dialog = None", src, "_open_client_editor não limpa _editor_dialog no except")

    def test_registers_on_closed_callback(self) -> None:
        """_open_client_editor (usado por _on_new_client) registra on_closed callback."""
        src = self._get_method_source("_open_client_editor")
        self.assertIn("on_close", src, "_open_client_editor não passa on_close callback")


# ============================================================================
# P2-4: refresh_theme incompleto na toolbar
# ============================================================================


class TestP24RefreshThemeCompleteness(unittest.TestCase):
    """P2-4: refresh_theme deve reconfigar combos, não só entry_search."""

    def _get_method_source(self) -> str:
        """Extrai source de refresh_theme da toolbar."""
        source = _TOOLBAR_PY.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "refresh_theme":
                return ast.get_source_segment(source, node) or ""
        return ""

    def test_reconfigures_entry_search(self) -> None:
        """refresh_theme deve configurar entry_search (baseline)."""
        src = self._get_method_source()
        self.assertIn("entry_search", src, "refresh_theme não configura entry_search")

    def test_reconfigures_order_combo(self) -> None:
        """refresh_theme deve configurar order_combo."""
        src = self._get_method_source()
        self.assertIn("order_combo", src, "refresh_theme não configura order_combo")

    def test_reconfigures_status_combo(self) -> None:
        """refresh_theme deve configurar status_combo."""
        src = self._get_method_source()
        self.assertIn("status_combo", src, "refresh_theme não configura status_combo")

    def test_order_combo_sets_text_color(self) -> None:
        """refresh_theme deve setar text_color no order_combo."""
        src = self._get_method_source()
        # Verificar que order_combo.configure inclui text_color
        idx_order = src.find("order_combo")
        remaining = src[idx_order:] if idx_order >= 0 else ""
        self.assertIn("text_color", remaining, "order_combo.configure não seta text_color")

    def test_status_combo_sets_dropdown_colors(self) -> None:
        """refresh_theme deve setar dropdown_fg_color no status_combo."""
        src = self._get_method_source()
        idx_status = src.find("status_combo")
        remaining = src[idx_status:] if idx_status >= 0 else ""
        self.assertIn("dropdown_fg_color", remaining, "status_combo.configure não seta dropdown_fg_color")


if __name__ == "__main__":
    unittest.main()
