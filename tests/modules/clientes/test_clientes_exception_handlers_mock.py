# -*- coding: utf-8 -*-
"""Teste de exception handlers do pick mode com mock (Microfase 13 - Opcional).

Este teste cobre gaps de baixa prioridade em exception handlers usando mock
para forçar exceções durante configure().

Gap coberto: actionbar_ctk.py linhas ~318-320, ~334-336 (except handlers)

Criado na Microfase 13 (2026-01-14).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def test_actionbar_enter_pick_mode_handles_configure_exception(tk_root):
    """Valida que enter_pick_mode captura exceção em configure().
    
    Gap coberto: actionbar_ctk.py linhas ~318-320
    
    Cenário:
    - Mock btn.configure() para lançar Exception
    - Chama enter_pick_mode()
    - Valida que exceção é capturada (não propaga)
    
    Critério de aceite:
    - Nenhuma exceção propagada (except captura)
    - Log de debug é chamado (opcional)
    """
    pytest.importorskip("customtkinter")

    from src.modules.clientes.appearance import ClientesThemeManager
    from src.modules.clientes.views.actionbar_ctk import ClientesActionBarCtk

    theme_manager = ClientesThemeManager()

    actionbar = ClientesActionBarCtk(
        tk_root,
        on_novo=lambda: None,
        on_editar=lambda: None,
        on_subpastas=lambda: None,
        theme_manager=theme_manager,
    )

    actionbar.update_idletasks()

    # Mock btn_novo.configure para lançar Exception
    original_configure = actionbar.btn_novo.configure

    def mock_configure_failing(**kwargs):
        if kwargs.get("state") == "disabled":
            raise RuntimeError("Mock: configure falhou propositalmente")
        return original_configure(**kwargs)

    actionbar.btn_novo.configure = mock_configure_failing

    # Tenta entrar em pick mode → NÃO deve explodir
    try:
        actionbar.enter_pick_mode()
        # Se chegou aqui, exception foi capturada corretamente
    except Exception as exc:
        pytest.fail(
            f"enter_pick_mode deveria capturar exceção em configure(), "
            f"mas propagou: {exc}"
        )

    # Restaura método original
    actionbar.btn_novo.configure = original_configure


def test_actionbar_leave_pick_mode_handles_configure_exception(tk_root):
    """Valida que leave_pick_mode captura exceção em configure().
    
    Gap coberto: actionbar_ctk.py linhas ~334-336
    
    Cenário:
    - Entra em pick mode normalmente
    - Mock btn.configure() para lançar Exception
    - Chama leave_pick_mode()
    - Valida que exceção é capturada (não propaga)
    
    Critério de aceite:
    - Nenhuma exceção propagada (except captura)
    """
    pytest.importorskip("customtkinter")

    from src.modules.clientes.appearance import ClientesThemeManager
    from src.modules.clientes.views.actionbar_ctk import ClientesActionBarCtk

    theme_manager = ClientesThemeManager()

    actionbar = ClientesActionBarCtk(
        tk_root,
        on_novo=lambda: None,
        on_editar=lambda: None,
        on_subpastas=lambda: None,
        theme_manager=theme_manager,
    )

    actionbar.update_idletasks()

    # Entra em pick mode normalmente
    actionbar.enter_pick_mode()

    # Mock btn_editar.configure para lançar Exception durante restauração
    original_configure = actionbar.btn_editar.configure

    def mock_configure_failing(**kwargs):
        raise RuntimeError("Mock: configure falhou propositalmente")

    actionbar.btn_editar.configure = mock_configure_failing

    # Tenta sair do pick mode → NÃO deve explodir
    try:
        actionbar.leave_pick_mode()
        # Se chegou aqui, exception foi capturada corretamente
    except Exception as exc:
        pytest.fail(
            f"leave_pick_mode deveria capturar exceção em configure(), "
            f"mas propagou: {exc}"
        )

    # Restaura método original
    actionbar.btn_editar.configure = original_configure


def test_footer_enter_pick_mode_handles_state_access_exception(tk_root):
    """Valida que footer captura exceção ao acessar btn['state'].
    
    Gap coberto: footer.py linhas ~84-89
    
    Cenário:
    - Mock btn.__getitem__ para lançar KeyError
    - Chama enter_pick_mode()
    - Valida que exceção é capturada
    
    Critério de aceite:
    - Nenhuma exceção propagada
    """
    from src.modules.clientes.views.footer import ClientesFooter

    footer = ClientesFooter(
        tk_root,
        on_novo=lambda: None,
        on_editar=lambda: None,
        on_subpastas=lambda: None,
        on_excluir=None,
        on_batch_delete=lambda: None,
        on_batch_restore=lambda: None,
        on_batch_export=lambda: None,
    )

    footer.update_idletasks()

    # Mock btn_novo.__getitem__ para lançar KeyError
    original_getitem = footer.btn_novo.__getitem__

    def mock_getitem_failing(key):
        if key == "state":
            raise KeyError("Mock: acesso ao state falhou")
        return original_getitem(key)

    footer.btn_novo.__getitem__ = mock_getitem_failing

    # Tenta entrar em pick mode → NÃO deve explodir
    try:
        footer.enter_pick_mode()
    except Exception as exc:
        pytest.fail(
            f"enter_pick_mode deveria capturar exceção ao acessar btn['state'], "
            f"mas propagou: {exc}"
        )

    # Restaura método original
    footer.btn_novo.__getitem__ = original_getitem


def test_footer_leave_pick_mode_handles_configure_exception(tk_root):
    """Valida que footer captura exceção em configure() durante restauração.
    
    Gap coberto: footer.py linhas ~102-107
    
    Cenário:
    - Entra em pick mode normalmente
    - Mock btn.configure para lançar Exception
    - Chama leave_pick_mode()
    - Valida que exceção é capturada
    
    Critério de aceite:
    - Nenhuma exceção propagada
    """
    from src.modules.clientes.views.footer import ClientesFooter

    footer = ClientesFooter(
        tk_root,
        on_novo=lambda: None,
        on_editar=lambda: None,
        on_subpastas=lambda: None,
        on_excluir=None,
        on_batch_delete=lambda: None,
        on_batch_restore=lambda: None,
        on_batch_export=lambda: None,
    )

    footer.update_idletasks()

    # Entra em pick mode normalmente
    footer.enter_pick_mode()

    # Mock btn_subpastas.configure para lançar Exception
    original_configure = footer.btn_subpastas.configure

    def mock_configure_failing(**kwargs):
        raise RuntimeError("Mock: configure falhou propositalmente")

    footer.btn_subpastas.configure = mock_configure_failing

    # Tenta sair do pick mode → NÃO deve explodir
    try:
        footer.leave_pick_mode()
    except Exception as exc:
        pytest.fail(
            f"leave_pick_mode deveria capturar exceção em configure(), "
            f"mas propagou: {exc}"
        )

    # Restaura método original
    footer.btn_subpastas.configure = original_configure
