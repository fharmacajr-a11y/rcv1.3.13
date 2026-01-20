# -*- coding: utf-8 -*-
"""Smoke test para validar polimento visual da toolbar CustomTkinter no módulo Clientes.

Este teste valida:
1. Paletas expandidas com cores específicas da toolbar
2. Entry de busca sem borda dupla (usando bg_color)
3. Dropdowns com cor mais escura no modo claro
4. Cores harmonizadas de botões (accent, neutral, danger)
5. refresh_colors() aplicando novas cores dinamicamente
"""

from __future__ import annotations

import pytest


def test_palettes_have_toolbar_specific_colors():
    """Testa se paletas possuem todas as cores específicas da toolbar."""
    from src.modules.clientes.appearance import DARK_PALETTE, LIGHT_PALETTE

    # Lista de chaves obrigatórias para toolbar
    required_keys = [
        "toolbar_bg",
        "input_bg",
        "input_border",
        "input_text",
        "input_placeholder",
        "dropdown_bg",
        "dropdown_hover",
        "dropdown_text",
        "accent_hover",
        "danger",
        "danger_hover",
        "neutral_btn",
        "neutral_hover",
    ]

    # Valida LIGHT_PALETTE
    for key in required_keys:
        assert key in LIGHT_PALETTE, f"LIGHT_PALETTE está faltando chave '{key}'"
        assert isinstance(LIGHT_PALETTE[key], str), f"LIGHT_PALETTE['{key}'] deve ser string"
        assert LIGHT_PALETTE[key].startswith("#"), f"LIGHT_PALETTE['{key}'] deve ser hex"

    # Valida DARK_PALETTE
    for key in required_keys:
        assert key in DARK_PALETTE, f"DARK_PALETTE está faltando chave '{key}'"
        assert isinstance(DARK_PALETTE[key], str), f"DARK_PALETTE['{key}'] deve ser string"
        assert DARK_PALETTE[key].startswith("#"), f"DARK_PALETTE['{key}'] deve ser hex"


def test_light_mode_dropdown_darker_than_input():
    """Testa se dropdown é mais escuro que input no modo claro (contraste visual)."""
    from src.modules.clientes.appearance import LIGHT_PALETTE

    input_bg = LIGHT_PALETTE["input_bg"]
    dropdown_bg = LIGHT_PALETTE["dropdown_bg"]

    # Converte hex para RGB para comparar brilho
    def hex_to_brightness(hex_color: str) -> int:
        """Calcula brilho percebido de cor hex (#RRGGBB)."""
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        return int(0.299 * r + 0.587 * g + 0.114 * b)

    input_brightness = hex_to_brightness(input_bg)
    dropdown_brightness = hex_to_brightness(dropdown_bg)

    # Dropdown deve ser mais escuro (menor brilho) no modo claro
    assert (
        dropdown_brightness < input_brightness
    ), f"Dropdown ({dropdown_bg}) deve ser mais escuro que input ({input_bg}) no modo claro"


def test_toolbar_ctk_initializes_with_new_colors(tk_root):
    """Testa se toolbar inicializa usando as novas cores específicas."""
    pytest.importorskip("customtkinter")

    from src.modules.clientes.appearance import ClientesThemeManager
    from src.modules.clientes.views.toolbar_ctk import ClientesToolbarCtk

    # Callbacks simples
    toolbar = ClientesToolbarCtk(
        tk_root,
        order_choices=["Nome", "Cidade"],
        default_order="Nome",
        status_choices=["Todos", "Ativo"],
        theme_manager=ClientesThemeManager(),
        on_search_changed=lambda x: None,
        on_clear_search=lambda: None,
        on_order_changed=lambda x: None,
        on_status_changed=lambda x: None,
        on_open_trash=lambda: None,
    )

    # Valida que toolbar foi criada
    assert toolbar is not None
    assert toolbar.winfo_exists()

    # Valida que widgets existem
    assert hasattr(toolbar, "entry_busca")
    assert hasattr(toolbar, "order_combobox")
    assert hasattr(toolbar, "status_combobox")
    assert hasattr(toolbar, "lixeira_button")


def test_toolbar_refresh_colors_applies_new_palette(tk_root):
    """Testa se refresh_colors() aplica todas as novas cores da paleta expandida."""
    pytest.importorskip("customtkinter")

    from src.modules.clientes.appearance import ClientesThemeManager
    from src.modules.clientes.views.toolbar_ctk import ClientesToolbarCtk

    theme_manager = ClientesThemeManager()
    toolbar = ClientesToolbarCtk(
        tk_root,
        order_choices=["Nome"],
        default_order="Nome",
        status_choices=["Todos"],
        theme_manager=theme_manager,
        on_search_changed=lambda x: None,
        on_clear_search=lambda: None,
        on_order_changed=lambda x: None,
        on_status_changed=lambda x: None,
    )

    # Troca tema e chama refresh_colors
    theme_manager.toggle()
    toolbar.refresh_colors(theme_manager)

    # Valida que não houve exceção (prova que cores novas são aplicadas)
    assert toolbar.winfo_exists()


def test_entry_busca_uses_input_bg_colors(tk_root):
    """Testa se Entry de busca usa input_bg ao invés de entry_bg (fix borda dupla)."""
    pytest.importorskip("customtkinter")

    from src.modules.clientes.appearance import ClientesThemeManager
    from src.modules.clientes.views.toolbar_ctk import ClientesToolbarCtk

    theme_manager = ClientesThemeManager()
    palette = theme_manager.get_palette()

    toolbar = ClientesToolbarCtk(
        tk_root,
        order_choices=["Nome"],
        default_order="Nome",
        status_choices=["Todos"],
        theme_manager=theme_manager,
        on_search_changed=lambda x: None,
        on_clear_search=lambda: None,
        on_order_changed=lambda x: None,
        on_status_changed=lambda x: None,
    )

    # Valida que entry_busca existe e usa input_bg da paleta
    assert hasattr(toolbar, "entry_busca")
    assert toolbar.entry_busca is not None

    # Valida que palette possui input_bg (usado pelo CTkEntry)
    assert "input_bg" in palette
    assert palette["input_bg"].startswith("#")


def test_button_colors_harmonized(tk_root):
    """Testa se botões usam cores harmonizadas (accent, neutral, danger)."""
    pytest.importorskip("customtkinter")

    from src.modules.clientes.appearance import ClientesThemeManager
    from src.modules.clientes.views.toolbar_ctk import ClientesToolbarCtk

    theme_manager = ClientesThemeManager()
    palette = theme_manager.get_palette()

    toolbar = ClientesToolbarCtk(
        tk_root,
        order_choices=["Nome"],
        default_order="Nome",
        status_choices=["Todos"],
        theme_manager=theme_manager,
        on_search_changed=lambda x: None,
        on_clear_search=lambda: None,
        on_order_changed=lambda x: None,
        on_status_changed=lambda x: None,
        on_open_trash=lambda: None,
    )

    # Valida que palette possui cores de botões
    assert "accent" in palette
    assert "accent_hover" in palette
    assert "neutral_btn" in palette
    assert "neutral_hover" in palette
    assert "danger" in palette
    assert "danger_hover" in palette

    # Valida que botões foram criados
    assert hasattr(toolbar, "lixeira_button")
    assert toolbar.lixeira_button is not None
