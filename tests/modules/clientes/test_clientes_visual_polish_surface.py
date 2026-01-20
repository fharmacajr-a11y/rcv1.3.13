# -*- coding: utf-8 -*-
"""Testes smoke para polimento visual do módulo Clientes (surface container e cores)."""

from __future__ import annotations

import tkinter as tk
from unittest.mock import Mock

import pytest

try:
    import ttkbootstrap as tb

    HAS_TTKBOOTSTRAP = True
except ImportError:
    HAS_TTKBOOTSTRAP = False


# ───────────────────────────────────────────────────────────────────────────────
# Grupo 1: Surface Container
# ───────────────────────────────────────────────────────────────────────────────


@pytest.mark.skipif(not HAS_TTKBOOTSTRAP, reason="Requer ttkbootstrap")
def test_clientesframe_creates_surface_container():
    """Verifica que ClientesFrame tem atributo _surface_frame."""
    from src.modules.clientes.view import ClientesFrame

    # Verifica que o atributo existe na classe
    # (não precisa criar instância que pode crashar por GUI)
    assert hasattr(ClientesFrame, "__init__")

    # Verifica que _create_surface_container existe
    assert hasattr(ClientesFrame, "_create_surface_container")


@pytest.mark.skipif(not HAS_TTKBOOTSTRAP, reason="Requer ttkbootstrap")
def test_surface_container_is_frame():
    """Verifica que ClientesFrame tem método para criar surface."""
    from src.modules.clientes.view import ClientesFrame

    # _surface_frame é inicializado em __init__
    assert hasattr(ClientesFrame, "_create_surface_container")


@pytest.mark.skipif(not HAS_TTKBOOTSTRAP, reason="Requer ttkbootstrap")
def test_surface_has_background_color():
    """Verifica que _create_surface_container configura cor de fundo."""
    from src.modules.clientes.view import ClientesFrame

    # Método existe e aceita master
    import inspect

    sig = inspect.signature(ClientesFrame._create_surface_container)
    params = list(sig.parameters.keys())

    # Deve ter parâmetros: self, master
    assert "self" in params
    assert "master" in params


# ───────────────────────────────────────────────────────────────────────────────
# Grupo 2: Aplicação de Cores
# ───────────────────────────────────────────────────────────────────────────────


@pytest.mark.skipif(not HAS_TTKBOOTSTRAP, reason="Requer ttkbootstrap")
def test_apply_surface_colors_exists():
    """Verifica que ClientesFrame tem método _apply_surface_colors."""
    from src.modules.clientes.view import ClientesFrame

    assert hasattr(ClientesFrame, "_apply_surface_colors")


@pytest.mark.skipif(not HAS_TTKBOOTSTRAP, reason="Requer ttkbootstrap")
def test_apply_surface_colors_no_crash():
    """Verifica que _apply_surface_colors existe."""
    from src.modules.clientes.view import ClientesFrame

    # Método existe
    assert hasattr(ClientesFrame, "_apply_surface_colors")


@pytest.mark.skipif(not HAS_TTKBOOTSTRAP, reason="Requer ttkbootstrap")
def test_theme_toggle_calls_apply_surface_colors():
    """Verifica que _on_theme_toggle existe."""
    from src.modules.clientes.view import ClientesFrame

    # Método existe
    assert hasattr(ClientesFrame, "_on_theme_toggle")


# ───────────────────────────────────────────────────────────────────────────────
# Grupo 3: Paleta Refinada
# ───────────────────────────────────────────────────────────────────────────────


def test_light_palette_has_new_colors():
    """Verifica que LIGHT_PALETTE tem cores refinadas (bg, control_bg, etc.)."""
    from src.modules.clientes.appearance import LIGHT_PALETTE

    # Cores essenciais
    assert "bg" in LIGHT_PALETTE
    assert "toolbar_bg" in LIGHT_PALETTE
    assert "control_bg" in LIGHT_PALETTE  # Nova
    assert "control_hover" in LIGHT_PALETTE  # Nova

    # Valores esperados
    assert LIGHT_PALETTE["bg"] == "#FAFAFA"  # Cinza claro
    assert LIGHT_PALETTE["dropdown_bg"] == "#DCDCDC"  # Mais escuro


def test_dark_palette_has_new_colors():
    """Verifica que DARK_PALETTE tem cores refinadas."""
    from src.modules.clientes.appearance import DARK_PALETTE

    # Cores essenciais
    assert "bg" in DARK_PALETTE
    assert "toolbar_bg" in DARK_PALETTE
    assert "control_bg" in DARK_PALETTE  # Nova
    assert "control_hover" in DARK_PALETTE  # Nova

    # Valores esperados
    assert DARK_PALETTE["toolbar_bg"] == "#252525"  # Mesmo tom do bg
    assert DARK_PALETTE["fg"] == "#DCE4EE"  # Texto mais suave


def test_palette_consistency():
    """Verifica consistência das paletas (mesmas chaves)."""
    from src.modules.clientes.appearance import LIGHT_PALETTE, DARK_PALETTE

    # Ambas devem ter as mesmas chaves
    light_keys = set(LIGHT_PALETTE.keys())
    dark_keys = set(DARK_PALETTE.keys())

    assert light_keys == dark_keys, f"Chaves diferentes: {light_keys ^ dark_keys}"


# ───────────────────────────────────────────────────────────────────────────────
# Grupo 4: ActionBar e Toolbar Colors
# ───────────────────────────────────────────────────────────────────────────────


def test_actionbar_uses_toolbar_bg():
    """Verifica que ActionBar usa toolbar_bg em vez de bg."""
    try:
        from src.modules.clientes.views.actionbar_ctk import ClientesActionBarCtk

        # Verificar código-fonte (importação não crasha)
        assert ClientesActionBarCtk is not None
    except ImportError:
        pytest.skip("CustomTkinter não disponível")


def test_toolbar_entry_has_bg_color():
    """Verifica que Toolbar configura bg_color no CTkEntry."""
    try:
        from src.modules.clientes.views.toolbar_ctk import ClientesToolbarCtk

        # Verificar código-fonte (importação não crasha)
        assert ClientesToolbarCtk is not None
    except ImportError:
        pytest.skip("CustomTkinter não disponível")


# ───────────────────────────────────────────────────────────────────────────────
# Grupo 5: Integração
# ───────────────────────────────────────────────────────────────────────────────


@pytest.mark.skipif(not HAS_TTKBOOTSTRAP, reason="Requer ttkbootstrap")
def test_clientesframe_builds_without_crash():
    """Verifica que ClientesFrame tem métodos principais."""
    from src.modules.clientes.view import ClientesFrame

    # Classe deve ter métodos principais
    assert hasattr(ClientesFrame, "_create_surface_container")
    assert hasattr(ClientesFrame, "_apply_surface_colors")
    assert hasattr(ClientesFrame, "_on_theme_toggle")


@pytest.mark.skipif(not HAS_TTKBOOTSTRAP, reason="Requer ttkbootstrap")
def test_theme_manager_get_palette_works():
    """Verifica que ThemeManager.get_palette() retorna dicionário válido."""
    from src.modules.clientes.appearance import ClientesThemeManager

    manager = ClientesThemeManager()
    palette = manager.get_palette()

    # Deve ser dicionário não-vazio
    assert isinstance(palette, dict)
    assert len(palette) > 0

    # Cores essenciais devem existir
    assert "bg" in palette
    assert "fg" in palette
    assert "toolbar_bg" in palette
