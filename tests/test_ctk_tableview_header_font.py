# pyright: reportAttributeAccessIssue=false
# -*- coding: utf-8 -*-
"""
Testes unitários para o hotfix de header_font no CTkTableView (Fase 9).

Verifica que:
  a) header_font NÃO é passado no construtor de CTkTable
  b) edit_row(0, font=header_font) é chamado quando headers estão presentes
  c) quando não há headers, edit_row não é chamado
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from typing import Any, cast
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Stubs mínimos para importar ctk_tableview sem UI real
# ---------------------------------------------------------------------------


def _build_fake_ctk():
    """Cria um módulo ctk fake suficiente para importar CTkTableView."""
    fake = types.ModuleType("customtkinter")

    class FakeCTkFrame:
        def __init__(self, master=None, **kw):
            self.master = master

        def pack(self, **kw):
            pass

        def destroy(self):
            pass

        def winfo_exists(self):
            return True

    fake.CTkFrame = FakeCTkFrame
    fake.CTkLabel = MagicMock()
    fake.get_appearance_mode = MagicMock(return_value="Light")
    return fake


def _install_stubs():
    """Instala stubs nos módulos necessários antes de importar o alvo."""
    fake_ctk = _build_fake_ctk()
    sys.modules.setdefault("customtkinter", fake_ctk)

    # src.ui.ctk_config expõe `ctk`
    ctk_config = types.ModuleType("src.ui.ctk_config")
    ctk_config.ctk = fake_ctk
    sys.modules["src.ui.ctk_config"] = ctk_config

    # TABLE_UI_SPEC e get_ctk_font_string
    table_ui = types.ModuleType("src.ui.table_ui_spec")

    class _Spec:
        font_family = "Arial"
        font_size = 12
        heading_font_size = 13
        heading_font_weight = "bold"
        hover_enabled = False

    table_ui.TABLE_UI_SPEC = _Spec()
    table_ui.get_ctk_font_string = MagicMock(return_value=("Arial", 12))
    sys.modules["src.ui.table_ui_spec"] = table_ui

    # ttk_treeview_theme
    treeview_theme = types.ModuleType("src.ui.ttk_treeview_theme")

    class _Colors:
        even_bg = "#ffffff"
        odd_bg = "#f0f0f0"

    treeview_theme.get_tree_colors = MagicMock(return_value=_Colors())
    sys.modules["src.ui.ttk_treeview_theme"] = treeview_theme

    # CTkTable fake — registra kwargs e calls a edit_row
    ctktable_mod = types.ModuleType("CTkTable")

    class FakeCTkTable:
        _instances: list = []

        def __init__(self, **kwargs):
            self._init_kwargs = dict(kwargs)
            FakeCTkTable._instances.append(self)
            self.edit_row_calls: list = []

        def pack(self, **kw):
            pass

        def destroy(self):
            pass

        def edit_row(self, row, **kwargs):
            self.edit_row_calls.append((row, kwargs))

    ctktable_mod.CTkTable = FakeCTkTable
    sys.modules["CTkTable"] = ctktable_mod

    return FakeCTkTable


# ---------------------------------------------------------------------------
# Fixture para obter a instância da FakeCTkTable criada durante os testes
# ---------------------------------------------------------------------------


class TestCTkTableViewHeaderFont(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Salva estado anterior — restaurado em tearDownClass
        _stub_keys = [
            "customtkinter",
            "src.ui.ctk_config",
            "src.ui.table_ui_spec",
            "src.ui.ttk_treeview_theme",
            "CTkTable",
            "src.ui.widgets.ctk_tableview",
        ]
        cls._saved_mods: dict = {k: sys.modules.get(k) for k in _stub_keys}

        cls.FakeCTkTable = _install_stubs()
        # Carrega o módulo diretamente (bypassa __init__.py que puxa ctk_treeview)
        spec = importlib.util.spec_from_file_location(
            "src.ui.widgets.ctk_tableview",
            str(Path(__file__).resolve().parent.parent / "src" / "ui" / "widgets" / "ctk_tableview.py"),
        )
        cls.mod = importlib.util.module_from_spec(spec)
        sys.modules["src.ui.widgets.ctk_tableview"] = cls.mod
        spec.loader.exec_module(cls.mod)
        cls.mod = cast(Any, cls.mod)  # evita reportAttributeAccessIssue

    @classmethod
    def tearDownClass(cls):
        """Restaura sys.modules ao estado anterior aos stubs."""
        for k, v in cls._saved_mods.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
        cls._saved_mods = {}

    def setUp(self):
        # Limpar instâncias entre testes
        self.FakeCTkTable._instances.clear()

    def _make_view(self, headers=None, rows=None):
        """Cria um CTkTableView com dados mínimos."""
        view = object.__new__(self.mod.CTkTableView)
        # Inicialização manual (sem Tk real)
        view._columns = headers or []
        view._headers = headers or []
        view._rows = rows or []
        view._selected_row_idx = None
        view._row_select_callback = None
        view._double_click_callback = None
        view._table = None
        view._height = 10
        view._zebra = False
        view._zebra_colors = ("#ffffff", "#f0f0f0")
        view._iid_to_index = {}
        view._next_iid = 0
        view._last_click_t = 0.0
        view._last_click_row_idx = None
        # Rótulo de erro (não usado aqui)
        view._show_import_error = lambda: None
        # pack do frame externo
        view.pack = lambda **kw: None
        view._create_table()
        return view

    # -----------------------------------------------------------------------
    # (a) header_font NÃO deve aparecer nos kwargs do construtor de CTkTable
    # -----------------------------------------------------------------------

    def test_header_font_not_in_constructor_kwargs(self):
        """CTkTable não deve receber header_font no __init__."""
        self._make_view(headers=["Nome", "Valor"], rows=[["A", "1"]])
        self.assertTrue(
            len(self.FakeCTkTable._instances) >= 1,
            "FakeCTkTable deve ter sido instanciado",
        )
        for inst in self.FakeCTkTable._instances:
            self.assertNotIn(
                "header_font",
                inst._init_kwargs,
                "header_font não deve estar nos kwargs do construtor",
            )

    def test_font_is_passed_in_constructor(self):
        """'font' (para células) deve ser passado no construtor."""
        self._make_view(headers=["Col"], rows=[["val"]])
        inst = self.FakeCTkTable._instances[-1]
        self.assertIn("font", inst._init_kwargs)

    # -----------------------------------------------------------------------
    # (b) edit_row(0, font=...) é chamado quando há headers
    # -----------------------------------------------------------------------

    def test_edit_row_called_with_header_font_when_headers_present(self):
        """edit_row(0, font=header_font) deve ser chamado quando há headers."""
        self._make_view(headers=["Nome", "Valor"], rows=[["A", "1"]])
        inst = self.FakeCTkTable._instances[-1]
        self.assertTrue(
            len(inst.edit_row_calls) >= 1,
            "edit_row deve ter sido chamado pelo menos uma vez",
        )
        row_idx, kwargs = inst.edit_row_calls[0]
        self.assertEqual(row_idx, 0, "edit_row deve ser chamado para a linha 0 (header)")
        self.assertIn("font", kwargs, "edit_row deve receber font=header_font")

    def test_edit_row_font_matches_spec(self):
        """A font passada para edit_row deve usar os valores de TABLE_UI_SPEC."""
        from src.ui.table_ui_spec import TABLE_UI_SPEC

        self._make_view(headers=["X"], rows=[["y"]])
        inst = self.FakeCTkTable._instances[-1]
        _, kwargs = inst.edit_row_calls[0]
        font = kwargs["font"]
        # Deve ser uma tupla com family/size/weight do spec
        self.assertIsInstance(font, tuple)
        self.assertEqual(font[0], TABLE_UI_SPEC.font_family)
        self.assertEqual(font[1], TABLE_UI_SPEC.heading_font_size)

    # -----------------------------------------------------------------------
    # (c) quando não há headers, edit_row não é chamado
    # -----------------------------------------------------------------------

    def test_edit_row_not_called_when_no_headers(self):
        """Sem headers, edit_row(0) não deve ser chamado."""
        self._make_view(headers=[], rows=[])
        for inst in self.FakeCTkTable._instances:
            self.assertEqual(
                inst.edit_row_calls,
                [],
                "edit_row não deve ser chamado sem headers",
            )

    # -----------------------------------------------------------------------
    # Extras: robustez
    # -----------------------------------------------------------------------

    def test_table_is_created(self):
        """_table não deve ser None após _create_table com headers."""
        view = self._make_view(headers=["A", "B"], rows=[["1", "2"]])
        self.assertIsNotNone(view._table)

    def test_edit_row_exception_does_not_propagate(self):
        """Exceção em edit_row não deve vazar (é suprimida com log.debug)."""
        inst_holder = []
        mod_ref = self.mod  # módulo carregado via spec_from_file_location

        original_cls = self.FakeCTkTable

        class BrokenEditRow(original_cls):
            def edit_row(self, row, **kwargs):
                inst_holder.append(self)
                raise RuntimeError("edit_row quebrado")

        original = mod_ref.CTkTable
        mod_ref.CTkTable = BrokenEditRow
        try:
            view = self._make_view(headers=["X"], rows=[["y"]])
            # Não deve levantar exceção
            self.assertIsNotNone(view._table)
        finally:
            mod_ref.CTkTable = original


if __name__ == "__main__":
    unittest.main()
