# -*- coding: utf-8 -*-
"""Testes de integração do botão Obrigações na tela de clientes.

LEGACY - v1.3.61: Funcionalidade movida para o Hub
====================================================
Este arquivo contém testes antigos para o botão "Obrigações" que existia
no módulo Clientes (toolbar e footer).

A partir da v1.3.61, a funcionalidade foi reestruturada:
- Removido: Botão "Obrigações" do módulo Clientes
- Adicionado: Botão "+ Nova Obrigação" no Hub (dashboard_center.py)
- Fluxo novo: Hub → Modo Seleção de Clientes → Janela de Obrigações

Este arquivo foi renomeado para LEGACY_ e não é mais executado nos testes.
Os novos testes estão em:
- tests/unit/modules/hub/views/test_dashboard_center.py (botões de ação)
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_app_instance():
    """Cria um mock do app com os métodos necessários."""
    app = MagicMock()
    app.abrir_obrigacoes_cliente = MagicMock()
    return app


def test_main_screen_accepts_on_obrigacoes_callback(tk_root_session, mock_app_instance):
    """Testa que MainScreenFrame aceita o callback on_obrigacoes."""
    from src.modules.clientes.views.main_screen import MainScreenFrame

    callback = MagicMock()

    frame = MainScreenFrame(
        tk_root_session,
        app=mock_app_instance,
        on_obrigacoes=callback,
    )

    assert frame.on_obrigacoes is callback


def test_toolbar_has_obrigacoes_button(tk_root_session):
    """Testa que a toolbar tem o botão de obrigações quando callback é fornecido."""
    from src.modules.clientes.views.toolbar import ClientesToolbar

    callback = MagicMock()

    toolbar = ClientesToolbar(
        tk_root_session,
        order_choices=["Nome A-Z", "Data Criação"],
        default_order="Nome A-Z",
        status_choices=["Todos", "Ativo", "Inativo"],
        on_search_changed=MagicMock(),
        on_clear_search=MagicMock(),
        on_order_changed=MagicMock(),
        on_status_changed=MagicMock(),
        on_obrigacoes=callback,
    )

    assert toolbar.obrigacoes_button is not None
    assert toolbar.obrigacoes_button.cget("text") == "Obrigações"


def test_footer_obrigacoes_button_always_none(tk_root_session):
    """Testa que o botão de obrigações no footer sempre é None (funcionalidade movida para toolbar)."""
    from src.modules.clientes.views.footer import ClientesFooter

    # Mesmo passando callback, footer não deve criar botão
    footer = ClientesFooter(
        tk_root_session,
        on_novo=MagicMock(),
        on_editar=MagicMock(),
        on_subpastas=MagicMock(),
        on_enviar_supabase=MagicMock(),
        on_enviar_pasta=MagicMock(),
        on_obrigacoes=MagicMock(),  # callback fornecido, mas botão não deve existir
        on_batch_delete=MagicMock(),
        on_batch_restore=MagicMock(),
        on_batch_export=MagicMock(),
    )

    # Botão sempre None no footer - funcionalidade está na toolbar superior
    assert footer.btn_obrigacoes is None


def test_app_actions_has_abrir_obrigacoes_cliente():
    """Testa que AppActions tem o método abrir_obrigacoes_cliente."""
    from src.modules.main_window.app_actions import AppActions

    mock_app_instance = MagicMock()
    actions = AppActions(mock_app_instance)

    assert hasattr(actions, "abrir_obrigacoes_cliente")
    assert callable(actions.abrir_obrigacoes_cliente)


def test_main_window_has_abrir_obrigacoes_cliente_method():
    """Testa que a janela principal tem o método abrir_obrigacoes_cliente."""
    from src.modules.main_window.views.main_window import App

    assert hasattr(App, "abrir_obrigacoes_cliente")
