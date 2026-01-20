# -*- coding: utf-8 -*-
"""Testes smoke para Microfase 4: padronização visual da Treeview com CustomTkinter."""

from __future__ import annotations

import tkinter as tk
from unittest.mock import MagicMock, Mock

import pytest

try:
    import ttkbootstrap as tb

    HAS_TTKBOOTSTRAP = True
except ImportError:
    HAS_TTKBOOTSTRAP = False


# ───────────────────────────────────────────────────────────────────────────────
# Grupo 1: reapply_clientes_treeview_style
# ───────────────────────────────────────────────────────────────────────────────


@pytest.mark.skipif(not HAS_TTKBOOTSTRAP, reason="Requer ttkbootstrap")
def test_reapply_style_accepts_palette_dict():
    """Verifica que reapply_clientes_treeview_style aceita dicionário de palette."""
    from src.ui.components.lists import reapply_clientes_treeview_style

    mock_style = Mock()
    mock_style.configure = Mock()
    mock_style.map = Mock()
    palette = {
        "tree_bg": "#FFFFFF",
        "tree_fg": "#000000",
        "tree_field_bg": "#FFFFFF",
        "tree_heading_bg": "#E0E0E0",
        "tree_heading_fg": "#000000",
        "tree_heading_bg_active": "#C8C8C8",
        "tree_selected_bg": "#0078D7",
        "tree_selected_fg": "#FFFFFF",
        "tree_even_row": "#FFFFFF",
        "tree_odd_row": "#E8E8E8",
    }

    # Deve retornar tupla (even_bg, odd_bg)
    result = reapply_clientes_treeview_style(
        mock_style,
        base_bg=palette["tree_bg"],
        base_fg=palette["tree_fg"],
        field_bg=palette["tree_field_bg"],
        heading_bg=palette["tree_heading_bg"],
        heading_fg=palette["tree_heading_fg"],
        heading_bg_active=palette["tree_heading_bg_active"],
        selected_bg=palette["tree_selected_bg"],
        selected_fg=palette["tree_selected_fg"],
    )

    assert isinstance(result, tuple)
    assert len(result) == 2


@pytest.mark.skipif(not HAS_TTKBOOTSTRAP, reason="Requer ttkbootstrap")
def test_reapply_style_calls_configure_and_map():
    """Verifica que reapply_clientes_treeview_style chama style.configure e style.map."""
    from src.ui.components.lists import reapply_clientes_treeview_style

    mock_style = Mock()
    mock_style.configure = Mock()
    mock_style.map = Mock()

    reapply_clientes_treeview_style(
        mock_style,
        base_bg="#FFFFFF",
        base_fg="#000000",
        field_bg="#FFFFFF",
        heading_bg="#E0E0E0",
        heading_fg="#000000",
        heading_bg_active="#C8C8C8",
        selected_bg="#0078D7",
        selected_fg="#FFFFFF",
    )

    # Deve ter chamado configure 2 vezes (Treeview + Heading)
    assert mock_style.configure.call_count >= 2
    # Deve ter chamado map 1 vez
    assert mock_style.map.call_count >= 1


# ───────────────────────────────────────────────────────────────────────────────
# Grupo 2: reapply_clientes_treeview_tags
# ───────────────────────────────────────────────────────────────────────────────


@pytest.mark.skipif(not HAS_TTKBOOTSTRAP, reason="Requer ttkbootstrap")
def test_reapply_tags_accepts_treeview_and_colors():
    """Verifica que reapply_clientes_treeview_tags aceita Treeview e cores."""
    from src.ui.components.lists import reapply_clientes_treeview_tags

    mock_tree = Mock()
    mock_tree.tag_configure = Mock()

    reapply_clientes_treeview_tags(
        mock_tree,
        even_bg="#FFFFFF",
        odd_bg="#E8E8E8",
        fg="#000000",
    )

    # Deve ter chamado tag_configure 2 vezes (even, odd)
    assert mock_tree.tag_configure.call_count >= 2


@pytest.mark.skipif(not HAS_TTKBOOTSTRAP, reason="Requer ttkbootstrap")
def test_reapply_tags_with_missing_fg():
    """Verifica que reapply_clientes_treeview_tags funciona sem fg."""
    from src.ui.components.lists import reapply_clientes_treeview_tags

    mock_tree = Mock()
    mock_tree.tag_configure = Mock()

    # fg é opcional (default="")
    reapply_clientes_treeview_tags(
        mock_tree,
        even_bg="#FFFFFF",
        odd_bg="#E8E8E8",
    )

    assert mock_tree.tag_configure.call_count >= 2


# ───────────────────────────────────────────────────────────────────────────────
# Grupo 3: Integração CTkScrollbar
# ───────────────────────────────────────────────────────────────────────────────


def test_main_screen_builder_has_use_ctk_scrollbar_flag():
    """Verifica que main_screen_ui_builder tem flag USE_CTK_SCROLLBAR."""
    from src.modules.clientes.views import main_screen_ui_builder

    assert hasattr(main_screen_ui_builder, "USE_CTK_SCROLLBAR")
    assert isinstance(main_screen_ui_builder.USE_CTK_SCROLLBAR, bool)


def test_main_screen_builder_has_ctk_scrollbar_import():
    """Verifica que main_screen_ui_builder importa CTkScrollbar."""
    from src.modules.clientes.views import main_screen_ui_builder

    # Verifica se as flags e variáveis estão presentes
    assert hasattr(main_screen_ui_builder, "USE_CTK_SCROLLBAR")
    assert hasattr(main_screen_ui_builder, "CTkScrollbar")
    assert isinstance(main_screen_ui_builder.USE_CTK_SCROLLBAR, bool)


# ───────────────────────────────────────────────────────────────────────────────
# Grupo 4: Integração com theme toggle
# ───────────────────────────────────────────────────────────────────────────────


@pytest.mark.skipif(not HAS_TTKBOOTSTRAP, reason="Requer ttkbootstrap")
def test_view_reapply_treeview_colors_exists():
    """Verifica que ClientesFrame tem método _reapply_treeview_colors."""
    from src.modules.clientes.view import ClientesFrame

    assert hasattr(ClientesFrame, "_reapply_treeview_colors")


@pytest.mark.skipif(not HAS_TTKBOOTSTRAP, reason="Requer ttkbootstrap")
def test_view_reapply_calls_new_functions(monkeypatch):
    """Verifica que _reapply_treeview_colors chama as novas funções."""
    mock_style_fn = Mock(return_value=("#FFFFFF", "#E8E8E8"))
    mock_tags_fn = Mock()

    # Mock das funções em src.ui.components.lists
    monkeypatch.setattr(
        "src.ui.components.lists.reapply_clientes_treeview_style",
        mock_style_fn,
    )
    monkeypatch.setattr(
        "src.ui.components.lists.reapply_clientes_treeview_tags",
        mock_tags_fn,
    )

    # Mock do tb.Style
    mock_style_class = Mock()
    monkeypatch.setattr("ttkbootstrap.Style", mock_style_class)

    # Criar instância simulada do método
    from src.modules.clientes.view import ClientesFrame

    # Criar frame mock sem inicializar UI
    mock_frame = Mock(spec=ClientesFrame)
    mock_frame._theme_manager = Mock()
    mock_frame._theme_manager.get_palette = Mock(
        return_value={
            "tree_bg": "#FFFFFF",
            "tree_fg": "#000000",
            "tree_field_bg": "#FFFFFF",
            "tree_heading_bg": "#E0E0E0",
            "tree_heading_fg": "#000000",
            "tree_selected_bg": "#0078D7",
            "tree_selected_fg": "#FFFFFF",
        }
    )
    mock_frame.client_list = Mock()

    # Chamar método diretamente (bound method)
    ClientesFrame._reapply_treeview_colors(mock_frame)

    # Deve ter chamado as funções
    assert mock_style_fn.called
    assert mock_tags_fn.called
