# -*- coding: utf-8 -*-
"""Testes para tooltips no painel de módulos do Hub.

Verifica que tooltips são criados corretamente quando action.description
está disponível.

Relacionado: P4 do TECH_DEBT_REGISTER (modules_panel.py:114)
"""

from __future__ import annotations

import tkinter as tk
from unittest.mock import Mock, patch

import pytest
from tests import ui_compat as tb

from src.modules.hub.views.modules_panel import build_modules_panel
from src.modules.hub.viewmodels.quick_actions_vm import QuickActionItemView, QuickActionsViewState


@pytest.fixture
def mock_root():
    """Cria root Tk para testes de UI."""
    root = tk.Tk()
    yield root
    try:
        root.destroy()
    except tk.TclError:
        pass


@pytest.fixture
def state_with_descriptions():
    """Cria estado com ações que têm descriptions."""
    state = QuickActionsViewState(
        actions=[
            QuickActionItemView(
                id="clientes",
                label="Clientes",
                description="Gerenciar cadastro de clientes",
                category="cadastros",
                bootstyle="info",
            ),
            QuickActionItemView(
                id="senhas",
                label="Senhas",
                description="Gerenciar senhas de acesso",
                category="cadastros",
                bootstyle="warning",
            ),
            QuickActionItemView(
                id="anvisa",
                label="Anvisa",
                description="Regulatório Anvisa",
                category="regulatorio",
                bootstyle="secondary",
            ),
        ]
    )
    return state


@pytest.fixture
def state_without_descriptions():
    """Cria estado com ações sem descriptions."""
    state = QuickActionsViewState(
        actions=[
            QuickActionItemView(
                id="test1",
                label="Test 1",
                description=None,  # Sem description
                category="test",
                bootstyle="info",
            ),
            QuickActionItemView(
                id="test2",
                label="Test 2",
                description="",  # Description vazia
                category="test",
                bootstyle="info",
            ),
        ]
    )
    return state


@pytest.mark.skip(reason="ToolTip removed with ttkbootstrap migration - tooltips not critical for core functionality")
def test_tooltips_created_when_description_available(mock_root, state_with_descriptions):
    """Testa que tooltips são criados quando action.description existe."""
    # Callback mock
    on_action_click = Mock()

    # Construir painel
    with patch("src.modules.hub.views.modules_panel.ToolTip") as mock_tooltip:
        _ = build_modules_panel(mock_root, state_with_descriptions, on_action_click)

        # Verificar que ToolTip foi chamado para cada ação com description
        assert mock_tooltip.call_count == 3  # 3 ações com description

        # Verificar que text foi passado corretamente
        calls = mock_tooltip.call_args_list
        descriptions = [call.kwargs["text"] for call in calls]

        assert "Gerenciar cadastro de clientes" in descriptions
        assert "Gerenciar senhas de acesso" in descriptions
        assert "Regulatório Anvisa" in descriptions

        # Verificar que wraplength foi usado
        for call in calls:
            assert call.kwargs.get("wraplength") == 260


@pytest.mark.skip(reason="ToolTip removed with ttkbootstrap migration")
def test_tooltips_not_created_when_description_missing(mock_root, state_without_descriptions):
    """Testa que tooltips NÃO são criados quando description está ausente."""
    on_action_click = Mock()

    # Construir painel
    with patch("src.modules.hub.views.modules_panel.ToolTip") as mock_tooltip:
        _ = build_modules_panel(mock_root, state_without_descriptions, on_action_click)

        # Verificar que ToolTip NÃO foi chamado (descriptions vazias/None)
        assert mock_tooltip.call_count == 0


@pytest.mark.skip(reason="ToolTip removed with ttkbootstrap migration")
def test_tooltip_import_fallback():
    """Testa que import de ToolTip funciona (com fallback)."""
    # Verificar que o import funciona
    from src.modules.hub.views.modules_panel import ToolTip

    # ToolTip deve ser uma classe/callable
    assert callable(ToolTip)


@pytest.mark.skip(reason="ToolTip removed with ttkbootstrap migration")
def test_build_modules_panel_creates_buttons_with_tooltips(mock_root, state_with_descriptions):
    """Teste de integração: verifica que painel é criado com botões e tooltips."""
    on_action_click = Mock()

    # Construir painel (sem mock para ver integração real)
    panel = build_modules_panel(mock_root, state_with_descriptions, on_action_click)

    # Verificar que painel foi criado
    assert panel is not None
    assert isinstance(panel, tb.Labelframe)

    # Verificar que painel tem children (frames de categoria)
    children = list(panel.winfo_children())
    assert len(children) > 0

    # Botões existem (dentro dos frames de categoria)
    # Nota: Não verificamos tooltips diretamente pois são objetos internos do ttkbootstrap
    # Mas o fato de não haver exceção já valida que ToolTip funcionou


@pytest.mark.skip(reason="ToolTip removed with ttkbootstrap migration")
def test_tooltip_wraplength_parameter():
    """Testa que wraplength é usado para evitar tooltips muito largos."""
    # Este é um teste de contrato: garantir que wraplength=260 foi escolhido
    # (valor razoável para tooltips de 1-2 linhas em telas 1920x1080)
    expected_wraplength = 260

    mock_root = tk.Tk()
    state = QuickActionsViewState(
        actions=[
            QuickActionItemView(
                id="test",
                label="Test",
                description="Descrição de teste para tooltip",
                category="test",
                bootstyle="info",
            ),
        ]
    )

    with patch("src.modules.hub.views.modules_panel.ToolTip") as mock_tooltip:
        build_modules_panel(mock_root, state, Mock())

        # Verificar que wraplength foi passado
        assert mock_tooltip.call_args.kwargs["wraplength"] == expected_wraplength

    mock_root.destroy()
