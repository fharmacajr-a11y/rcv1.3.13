# -*- coding: utf-8 -*-
"""FASE 8: Smoke test — alterna tema Light↔Dark e confirma sem warnings/exception.

Garante que apply_treeview_theme + style.map funcionam sem erros
e que background, fieldbackground e selection estão configurados.
"""

from __future__ import annotations

import tkinter as tk
import warnings
from tkinter import ttk

import pytest


@pytest.mark.gui
class TestTtkThemeToggleSmoke:
    """Smoke: alterna tema e valida que style está correto sem warnings."""

    def test_toggle_theme_no_warnings(self) -> None:
        """Alterna Light → Dark → Light e confirma ausência de warnings/exceptions."""
        from src.ui.ttk_treeview_theme import apply_treeview_theme

        root = tk.Tk()
        root.withdraw()

        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")

                # Light → aplicar
                style_name_light, colors_light = apply_treeview_theme("Light", root)
                assert style_name_light.endswith(".Treeview")
                assert colors_light.bg == "#ffffff"
                assert colors_light.field_bg == "#ffffff"

                # Dark → aplicar
                style_name_dark, colors_dark = apply_treeview_theme("Dark", root)
                assert style_name_dark.endswith(".Treeview")
                assert colors_dark.bg == "#2b2b2b"
                assert colors_dark.field_bg == "#2b2b2b"

                # Volta para Light
                style_name_back, colors_back = apply_treeview_theme("Light", root)
                assert colors_back.bg == "#ffffff"

                root.update_idletasks()

            # Nenhum warning de Tk/ttk gerado
            tk_warnings = [w for w in caught if "tk" in str(w.category).lower() or "ttk" in str(w.message).lower()]
            assert not tk_warnings, f"Warnings de Tk/ttk detectados: {tk_warnings}"
        finally:
            root.destroy()

    def test_style_configure_and_map_present(self) -> None:
        """Verifica que style.configure e style.map definem background + fieldbackground."""
        from src.ui.ttk_treeview_theme import apply_treeview_theme

        root = tk.Tk()
        root.withdraw()

        try:
            apply_treeview_theme("Dark", root, style_name="SmokeTest")

            style = ttk.Style(root)

            # Verificar configure
            cfg = style.configure("SmokeTest.Treeview")
            assert cfg is not None, "style.configure retornou None"

            bg = style.lookup("SmokeTest.Treeview", "background")
            field_bg = style.lookup("SmokeTest.Treeview", "fieldbackground")
            assert bg, "background não definido no style"
            assert field_bg, "fieldbackground não definido no style"

            # Verificar map (selection)
            bg_map = style.map("SmokeTest.Treeview", "background")
            assert any("selected" in str(entry) for entry in bg_map), f"selection background não mapeado: {bg_map}"

            root.update_idletasks()
        finally:
            root.destroy()

    def test_treeview_renders_with_both_themes(self) -> None:
        """Cria Treeview real, aplica ambos os temas, verifica sem crash."""
        from src.ui.ttk_treeview_theme import apply_treeview_theme, apply_zebra

        root = tk.Tk()
        root.withdraw()

        try:
            for mode in ("Light", "Dark"):
                style_name, colors = apply_treeview_theme(mode, root)

                tree = ttk.Treeview(root, columns=("col1",), show="headings", style=style_name)
                tree.heading("col1", text="Teste")

                for i in range(5):
                    tree.insert("", "end", values=(f"Item {i}",))

                apply_zebra(tree, colors)

                tree.pack()
                root.update_idletasks()
                tree.destroy()
        finally:
            root.destroy()
