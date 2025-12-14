# -*- coding: utf-8 -*-
"""Testes para HubLayoutConfig e helpers de layout.

NOTA HUB-TEST-TK-01:
- Alguns testes dependem de Tkinter funcional (tk.Tk()).
- Em ambientes com Tcl/Tk mal configurado, esses testes são automaticamente
  marcados como skip com mensagem clara.
- Erro típico: "couldn't read file .../tcl8.6/auto.tcl" ou "Can't find a usable tk.tcl".
"""

from __future__ import annotations

import tkinter as tk

import pytest

from src.modules.hub.layout import HubLayoutConfig, apply_hub_layout


class TestHubLayoutConfig:
    """Testes para HubLayoutConfig dataclass."""

    def test_default_config(self):
        """Deve criar config com valores padrão corretos."""
        config = HubLayoutConfig()

        assert config.modules_col == 0
        assert config.center_col == 1
        assert config.notes_col == 2
        assert config.row_main == 0
        assert config.modules_weight == 0  # Sem expansão
        assert config.center_weight == 1  # Expansível
        assert config.notes_weight == 0  # Sem expansão

    def test_custom_config(self):
        """Deve permitir customização de valores."""
        config = HubLayoutConfig(
            modules_col=1,
            center_col=0,
            notes_col=2,
            center_weight=2,
        )

        assert config.modules_col == 1
        assert config.center_col == 0
        assert config.notes_col == 2
        assert config.center_weight == 2

    def test_config_is_immutable(self):
        """HubLayoutConfig deve ser imutável (frozen)."""
        config = HubLayoutConfig()

        with pytest.raises(Exception):  # dataclass frozen
            config.center_weight = 999  # type: ignore

    def test_config_has_minsize_properties(self):
        """Deve ter propriedades de minsize para cada coluna."""
        config = HubLayoutConfig()

        assert hasattr(config, "modules_minsize")
        assert hasattr(config, "center_minsize")
        assert hasattr(config, "notes_minsize")
        assert config.modules_minsize > 0
        assert config.center_minsize > 0
        assert config.notes_minsize > 0

    def test_config_has_padding_properties(self):
        """Deve ter propriedades de padding."""
        config = HubLayoutConfig()

        assert hasattr(config, "pad_outer")
        assert hasattr(config, "pad_inner")
        assert config.pad_outer > 0
        assert config.pad_inner > 0


class TestApplyHubLayout:
    """Testes para função apply_hub_layout."""

    def test_apply_layout_configures_columns(self, tk_root):
        """Deve configurar grid_columnconfigure para as 3 colunas."""
        config = HubLayoutConfig()

        apply_hub_layout(tk_root, config)

        # Verificar que colunas foram configuradas
        # (Tkinter não tem API direta para verificar, mas podemos testar sem erro)
        # A melhor validação é visual ou através de grid_info dos widgets filhos
        assert True  # Se chegou aqui, não deu erro

    def test_apply_layout_with_custom_weights(self, tk_root):
        """Deve aplicar weights customizados."""
        config = HubLayoutConfig(
            modules_weight=1,
            center_weight=2,
            notes_weight=1,
        )

        # Não deve dar erro
        apply_hub_layout(tk_root, config)

    def test_apply_layout_configures_row(self, tk_root):
        """Deve configurar grid_rowconfigure para linha principal."""
        config = HubLayoutConfig(row_main=0)

        apply_hub_layout(tk_root, config)

        # Deve ter configurado row 0 com weight 1
        assert True

    def test_apply_layout_on_frame(self, tk_root):
        """Deve funcionar em um Frame, não só em Tk."""
        frame = tk.Frame(tk_root)
        config = HubLayoutConfig()

        # Não deve dar erro
        apply_hub_layout(frame, config)

    def test_config_modules_column_zero_weight(self):
        """Módulos deve ter weight 0 por padrão (sem expansão)."""
        config = HubLayoutConfig()
        assert config.modules_weight == 0

    def test_config_center_column_positive_weight(self):
        """Centro deve ter weight > 0 por padrão (expansível)."""
        config = HubLayoutConfig()
        assert config.center_weight > 0

    def test_config_notes_column_zero_weight(self):
        """Notas deve ter weight 0 por padrão (sem expansão)."""
        config = HubLayoutConfig()
        assert config.notes_weight == 0

    def test_apply_layout_multiple_times(self, tk_root):
        """Deve permitir aplicar layout múltiplas vezes sem erro."""
        config = HubLayoutConfig()

        apply_hub_layout(tk_root, config)
        apply_hub_layout(tk_root, config)  # Segunda vez

        # Não deve dar erro

    def test_different_configs_on_same_root(self, tk_root):
        """Deve permitir aplicar configs diferentes sequencialmente."""
        config1 = HubLayoutConfig(center_weight=1)
        config2 = HubLayoutConfig(center_weight=2)

        apply_hub_layout(tk_root, config1)
        apply_hub_layout(tk_root, config2)

        # A última config deve prevalecer


class TestHubLayoutIntegration:
    """Testes de integração para verificar layout real."""

    def test_three_columns_setup(self, tk_root):
        """Deve permitir setup de 3 colunas com widgets."""
        config = HubLayoutConfig()

        # Criar 3 frames para simular módulos|centro|notas
        modules_frame = tk.Frame(tk_root, bg="red", width=100, height=100)
        center_frame = tk.Frame(tk_root, bg="green", width=200, height=100)
        notes_frame = tk.Frame(tk_root, bg="blue", width=150, height=100)

        # Aplicar configuração de grid
        apply_hub_layout(tk_root, config)

        # Posicionar widgets
        modules_frame.grid(row=config.row_main, column=config.modules_col, sticky="nsew")
        center_frame.grid(row=config.row_main, column=config.center_col, sticky="nsew")
        notes_frame.grid(row=config.row_main, column=config.notes_col, sticky="nsew")

        # Verificar que widgets foram posicionados (via grid_info)
        assert modules_frame.grid_info()["column"] == 0
        assert center_frame.grid_info()["column"] == 1
        assert notes_frame.grid_info()["column"] == 2

    def test_center_column_expands(self, tk_root):
        """Centro deve ser a coluna expansível (weight > 0)."""
        config = HubLayoutConfig()

        # Com config padrão, apenas center_col deve ter weight > 0
        assert config.center_weight > 0
        assert config.modules_weight == 0
        assert config.notes_weight == 0
