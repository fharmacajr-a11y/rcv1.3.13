# -*- coding: utf-8 -*-
"""Smoke test para verificar que o módulo Clientes com theme toggle não quebrou."""

from __future__ import annotations

import pytest

from tests.helpers.skip_conditions import SKIP_PY313_TKINTER


def test_clientes_theme_manager_import():
    """Verifica que o theme manager pode ser importado."""
    try:
        from src.modules.clientes.appearance import ClientesThemeManager, HAS_CUSTOMTKINTER

        assert ClientesThemeManager is not None
        # HAS_CUSTOMTKINTER pode ser False se não estiver instalado
        assert isinstance(HAS_CUSTOMTKINTER, bool)
    except ImportError as e:
        pytest.fail(f"Falha ao importar theme manager: {e}")


def test_clientes_frame_import():
    """Verifica que ClientesFrame pode ser importado."""
    try:
        from src.modules.clientes.view import ClientesFrame

        assert ClientesFrame is not None
    except ImportError as e:
        pytest.fail(f"Falha ao importar ClientesFrame: {e}")


def test_lists_new_functions_import():
    """Verifica que as novas funções de lists.py podem ser importadas."""
    try:
        from src.ui.components.lists import (
            reapply_clientes_treeview_style,
            reapply_clientes_treeview_tags,
        )

        assert callable(reapply_clientes_treeview_style)
        assert callable(reapply_clientes_treeview_tags)
    except ImportError as e:
        pytest.fail(f"Falha ao importar funções de lists: {e}")


def test_theme_manager_basic_operations():
    """Verifica operações básicas do theme manager."""
    from src.modules.clientes.appearance import ClientesThemeManager

    manager = ClientesThemeManager()

    # Verifica que tem um modo inicial
    assert manager.current_mode in ("light", "dark")

    # Verifica que get_palette retorna dict
    palette = manager.get_palette()
    assert isinstance(palette, dict)
    assert "bg" in palette
    assert "fg" in palette
    assert "tree_bg" in palette

    # Verifica que save/load funciona
    original_mode = manager.current_mode
    manager.save_mode("dark")
    loaded_mode = manager.load_mode()
    assert loaded_mode == "dark"

    # Restaura estado original
    manager.save_mode(original_mode)


@SKIP_PY313_TKINTER
def test_create_search_controls_with_palette():
    """Verifica que create_search_controls aceita theme_palette."""
    import tkinter as tk

    from src.ui.components.inputs import create_search_controls

    root = tk.Tk()  # type: ignore[attr-defined]
    try:
        # Cria com palette
        palette = {
            "entry_bg": "#FFFFFF",
            "entry_fg": "#000000",
            "entry_border": "#CCCCCC",
            "combo_bg": "#FFFFFF",
            "combo_fg": "#000000",
            "bg": "#F0F0F0",
        }

        controls = create_search_controls(
            root,
            order_choices=["Nome", "ID"],
            default_order="Nome",
            on_search=lambda e: None,
            on_clear=lambda: None,
            on_order_change=lambda: None,
            theme_palette=palette,
        )

        assert controls is not None
        assert controls.frame is not None
        
        # Fix Microfase 19.2: Garantir que widgets são processados antes de destruir
        root.update_idletasks()

    finally:
        try:
            root.destroy()
        except Exception:  # noqa: BLE001
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])  # type: ignore[misc]
