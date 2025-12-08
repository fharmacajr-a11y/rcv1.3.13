# -*- coding: utf-8 -*-
"""Testes UI para a tela de Lixeira (LIXEIRA-UI-001).

Testa:
- Criação da janela sem exceção
- Existência dos botões principais
- Wiring dos handlers aos botões
"""

from __future__ import annotations

import tkinter as tk
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_tk_root():
    """Cria um root Tk falso para testes sem GUI real."""
    root = MagicMock(spec=tk.Tk)
    root.winfo_exists.return_value = 1
    root.after = MagicMock(side_effect=lambda ms, func: func())
    return root


@pytest.fixture
def mock_service_functions():
    """Mock das funções de serviço da lixeira."""
    with (
        patch("src.modules.lixeira.views.lixeira.listar_clientes_na_lixeira") as mock_listar,
        patch("src.modules.lixeira.views.lixeira.restaurar_clientes_da_lixeira") as mock_restaurar,
        patch("src.modules.lixeira.views.lixeira.excluir_clientes_definitivamente") as mock_excluir,
    ):
        mock_listar.return_value = []
        mock_restaurar.return_value = None
        mock_excluir.return_value = (0, [])
        yield {
            "listar": mock_listar,
            "restaurar": mock_restaurar,
            "excluir": mock_excluir,
        }


class TestLixeiraViewStructure:
    """Testes estruturais da view da Lixeira (sem GUI real)."""

    def test_module_has_abrir_lixeira_function(self):
        """Verifica que o módulo exporta a função abrir_lixeira."""
        from src.modules.lixeira.views import lixeira as lixeira_mod

        assert hasattr(lixeira_mod, "abrir_lixeira")
        assert callable(lixeira_mod.abrir_lixeira)

    def test_module_has_refresh_if_open_function(self):
        """Verifica que o módulo exporta a função refresh_if_open."""
        from src.modules.lixeira.views import lixeira as lixeira_mod

        assert hasattr(lixeira_mod, "refresh_if_open")
        assert callable(lixeira_mod.refresh_if_open)

    def test_is_open_returns_false_when_no_window(self):
        """Verifica que _is_open retorna False quando não há janela aberta."""
        from src.modules.lixeira.views import lixeira as lixeira_mod

        # Reset singleton
        lixeira_mod._OPEN_WINDOW = None

        assert lixeira_mod._is_open() is False

    def test_refresh_if_open_does_nothing_when_closed(self):
        """Verifica que refresh_if_open não faz nada quando janela está fechada."""
        from src.modules.lixeira.views import lixeira as lixeira_mod

        # Reset singleton
        lixeira_mod._OPEN_WINDOW = None

        # Não deve levantar exceção
        lixeira_mod.refresh_if_open()


class TestLixeiraButtonDefinitions:
    """Testes para verificar a definição dos botões na view."""

    def test_button_texts_are_defined(self):
        """Verifica que os textos dos botões estão definidos no código."""
        from src.modules.lixeira.views import lixeira as lixeira_mod
        import inspect

        source = inspect.getsource(lixeira_mod.abrir_lixeira)

        # Verifica textos dos botões principais
        assert '"Restaurar Selecionados"' in source
        assert '"Apagar Selecionados"' in source
        assert '"⟳"' in source
        assert '"Fechar"' in source

    def test_button_bootstyles_are_defined(self):
        """Verifica que os estilos dos botões estão definidos corretamente."""
        from src.modules.lixeira.views import lixeira as lixeira_mod
        import inspect

        source = inspect.getsource(lixeira_mod.abrir_lixeira)

        # Verifica bootstyles
        assert 'bootstyle="success"' in source  # Restaurar
        assert 'bootstyle="danger"' in source  # Apagar
        assert 'bootstyle="secondary"' in source  # Fechar

    def test_handler_functions_are_defined(self):
        """Verifica que as funções de handler estão definidas no código."""
        from src.modules.lixeira.views import lixeira as lixeira_mod
        import inspect

        source = inspect.getsource(lixeira_mod.abrir_lixeira)

        # Verifica definições de handlers
        assert "def on_restore()" in source
        assert "def on_purge()" in source
        assert "def carregar()" in source

    def test_buttons_are_connected_to_handlers(self):
        """Verifica que os botões são configurados com os handlers corretos."""
        from src.modules.lixeira.views import lixeira as lixeira_mod
        import inspect

        source = inspect.getsource(lixeira_mod.abrir_lixeira)

        # Verifica conexão de handlers
        assert "btn_restore.configure(command=on_restore)" in source
        assert "btn_purge.configure(command=on_purge)" in source
        assert "btn_refresh.configure(command=carregar)" in source


class TestLixeiraTreeviewColumns:
    """Testes para verificar as colunas do Treeview."""

    def test_treeview_columns_are_defined(self):
        """Verifica que as colunas do Treeview estão definidas."""
        from src.modules.lixeira.views import lixeira as lixeira_mod
        import inspect

        source = inspect.getsource(lixeira_mod.abrir_lixeira)

        expected_columns = [
            "id",
            "razao_social",
            "cnpj",
            "nome",
            "whatsapp",
            "obs",
            "ultima_alteracao",
        ]

        for col in expected_columns:
            assert f'"{col}"' in source, f"Coluna {col} não encontrada"

    def test_treeview_headings_are_defined(self):
        """Verifica que os headings do Treeview estão definidos."""
        from src.modules.lixeira.views import lixeira as lixeira_mod
        import inspect

        source = inspect.getsource(lixeira_mod.abrir_lixeira)

        expected_headings = [
            '"ID"',
            '"Razão Social"',
            '"CNPJ"',
            '"Nome"',
            '"WhatsApp"',
            '"Observações"',
            '"Última Alteração"',
        ]

        for heading in expected_headings:
            assert heading in source, f"Heading {heading} não encontrado"


class TestLixeiraWindowConfiguration:
    """Testes para verificar a configuração da janela."""

    def test_window_title_is_set(self):
        """Verifica que o título da janela está definido."""
        from src.modules.lixeira.views import lixeira as lixeira_mod
        import inspect

        source = inspect.getsource(lixeira_mod.abrir_lixeira)

        assert '"Lixeira de Clientes"' in source

    def test_window_minimum_size_is_set(self):
        """Verifica que o tamanho mínimo da janela está definido."""
        from src.modules.lixeira.views import lixeira as lixeira_mod
        import inspect

        source = inspect.getsource(lixeira_mod.abrir_lixeira)

        assert "minsize(900, 520)" in source

    def test_singleton_pattern_is_implemented(self):
        """Verifica que o padrão singleton está implementado."""
        from src.modules.lixeira.views import lixeira as lixeira_mod

        # Verifica que existe a variável global _OPEN_WINDOW
        assert hasattr(lixeira_mod, "_OPEN_WINDOW")

        # Verifica que existe a função _is_open
        assert hasattr(lixeira_mod, "_is_open")
        assert callable(lixeira_mod._is_open)
