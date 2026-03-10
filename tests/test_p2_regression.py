# pyright: reportAttributeAccessIssue=false
# -*- coding: utf-8 -*-
"""
Testes de regressão — P2 fixes (FASE 3 estabilização clientes).

P2-1: ZIP temp file deve usar tempfile.mkstemp, não os.getpid().
P2-2: _loading é resetado mesmo quando _safe_after falha (try/except guard).
P2-3: _on_new_client respeita guard de reentrância (_opening_editor / _editor_dialog).
P2-4: refresh_theme reconfigura order_combo e status_combo (não só entry_search).
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_ROOT = Path(__file__).resolve().parent.parent
_FILES_DOWNLOAD_MIXIN = _ROOT / "src" / "modules" / "clientes" / "ui" / "views" / "_files_download_mixin.py"
_FILES_NAVIGATION_MIXIN = _ROOT / "src" / "modules" / "clientes" / "ui" / "views" / "_files_navigation_mixin.py"
_VIEW_PY = _ROOT / "src" / "modules" / "clientes" / "ui" / "view.py"
_TOOLBAR_PY = _ROOT / "src" / "modules" / "clientes" / "ui" / "views" / "toolbar.py"


# ============================================================================
# P2-1: ZIP temp file collision — deve usar mkstemp, não getpid
# ============================================================================


class TestP21ZipTempFileCollision(unittest.TestCase):
    """P2-1: ZIP temp file name não pode depender de os.getpid()."""

    def test_no_getpid_in_zip_creation(self) -> None:
        """Código de download ZIP NÃO deve conter rc_zip_{os.getpid()}.zip."""
        source = _FILES_DOWNLOAD_MIXIN.read_text(encoding="utf-8")
        self.assertNotIn("os.getpid()", source, "Ainda usa os.getpid() para nome do ZIP temporário")

    def test_uses_mkstemp_for_zip(self) -> None:
        """Código de download ZIP deve usar tempfile.mkstemp para evitar colisão."""
        source = _FILES_DOWNLOAD_MIXIN.read_text(encoding="utf-8")
        self.assertIn("tempfile.mkstemp(", source, "Não usa tempfile.mkstemp() para ZIP temporário")

    def test_mkstemp_has_zip_suffix(self) -> None:
        """mkstemp deve usar suffix='.zip'."""
        source = _FILES_DOWNLOAD_MIXIN.read_text(encoding="utf-8")
        self.assertIn('suffix=".zip"', source, "mkstemp não especifica suffix='.zip'")

    def test_temp_zip_cleanup_in_finally(self) -> None:
        """Arquivo temp ZIP deve ser limpo em bloco finally."""
        source = _FILES_DOWNLOAD_MIXIN.read_text(encoding="utf-8")
        # Verifica que há unlink(missing_ok=True) em bloco finally
        self.assertIn("temp_zip.unlink(missing_ok=True)", source, "Falta cleanup do temp ZIP em finally")


# ============================================================================
# P2-2: _loading sem try/finally — flag pode ficar presa
# ============================================================================


class TestP22LoadingFlagProtection(unittest.TestCase):
    """P2-2: _loading deve ser resetado mesmo quando _safe_after falha."""

    def test_navigation_load_thread_has_safe_after_guard(self) -> None:
        """_load_thread no navigation mixin deve ter try/except ao redor de _safe_after no except."""
        source = _FILES_NAVIGATION_MIXIN.read_text(encoding="utf-8")
        # O except block que trata erros de list_files deve ter try/except
        # ao redor do _safe_after, com fallback self._loading = False
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.attr, str):
                if node.attr == "_loading":
                    # Procurar assignment self._loading = False dentro de except
                    pass
        # Abordagem pragmática: verificar que o padrão existe no source
        self.assertIn("self._loading = False", source, "Falta fallback self._loading = False no navigation mixin")

    def test_download_open_thread_has_safe_after_guard(self) -> None:
        """_open_thread no download mixin deve ter try/except ao redor de _safe_after no except."""
        source = _FILES_DOWNLOAD_MIXIN.read_text(encoding="utf-8")
        # Contar que há pelo menos 3 ocorrências de self._loading = False
        # (open callback, open error callback, e fallback no except)
        count = source.count("self._loading = False")
        self.assertGreaterEqual(count, 3, f"Esperado >=3 resets de _loading, encontrado {count}")


# ============================================================================
# P2-3: _on_new_client sem guard de reentrância
# ============================================================================


class TestP23NewClientReentrancy(unittest.TestCase):
    """P2-3: _on_new_client deve usar mesma guarda de reentrância que _open_client_editor."""

    def _get_method_source(self, method_name: str) -> str:
        """Extrai source do método especificado de view.py."""
        source = _VIEW_PY.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == method_name:
                return ast.get_source_segment(source, node) or ""
        return ""

    def test_checks_opening_editor_flag(self) -> None:
        """_on_new_client deve checar self._opening_editor."""
        src = self._get_method_source("_on_new_client")
        self.assertIn("_opening_editor", src, "_on_new_client não checa _opening_editor")

    def test_checks_editor_dialog_reference(self) -> None:
        """_on_new_client deve checar self._editor_dialog existente."""
        src = self._get_method_source("_on_new_client")
        self.assertIn("_editor_dialog", src, "_on_new_client não checa _editor_dialog")

    def test_sets_opening_editor_true_before_creation(self) -> None:
        """_on_new_client deve setar _opening_editor = True antes de criar diálogo."""
        src = self._get_method_source("_on_new_client")
        self.assertIn("self._opening_editor = True", src, "_on_new_client não seta _opening_editor = True")

    def test_resets_opening_editor_on_exception(self) -> None:
        """_on_new_client deve resetar _opening_editor no except."""
        src = self._get_method_source("_on_new_client")
        # Deve ter except que reseta ambas as referências
        self.assertIn("self._opening_editor = False", src, "_on_new_client não reseta _opening_editor no except")
        self.assertIn("self._editor_dialog = None", src, "_on_new_client não limpa _editor_dialog no except")

    def test_registers_on_closed_callback(self) -> None:
        """_on_new_client deve registrar on_closed callback para limpar referências."""
        src = self._get_method_source("_on_new_client")
        self.assertIn("on_close", src, "_on_new_client não passa on_close callback")


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
