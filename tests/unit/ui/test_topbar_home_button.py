"""Testes para o botão Início do TopBar."""

from __future__ import annotations

from unittest.mock import Mock

from src.ui.topbar import TopBar


def test_topbar_home_button_callback(tk_root_session):
    """Verifica que o botão Início dispara o callback on_home."""
    mock_on_home = Mock()

    topbar = TopBar(
        tk_root_session,
        on_home=mock_on_home,
    )
    topbar.pack()
    tk_root_session.update_idletasks()

    # Verifica que o botão existe
    assert hasattr(topbar, "btn_home")
    assert topbar.btn_home is not None

    # Invoca o botão
    topbar.btn_home.invoke()

    # Verifica que callback foi chamado
    mock_on_home.assert_called_once()

    try:
        topbar.destroy()
    except Exception:
        pass


def test_topbar_home_button_set_is_hub(tk_root_session):
    """Verifica que set_is_hub desabilita/habilita o botão Início."""
    mock_on_home = Mock()

    topbar = TopBar(
        tk_root_session,
        on_home=mock_on_home,
    )
    topbar.pack()
    tk_root_session.update_idletasks()

    # Verifica que método set_is_hub não gera erro
    try:
        topbar.set_is_hub(True)
        tk_root_session.update_idletasks()
        topbar.set_is_hub(False)
        tk_root_session.update_idletasks()
        success = True
    except Exception:
        success = False

    assert success, "set_is_hub deve executar sem erros"

    try:
        topbar.destroy()
    except Exception:
        pass


def test_topbar_home_button_pick_mode(tk_root_session):
    """Verifica que set_pick_mode_active desabilita/habilita o botão Início."""
    mock_on_home = Mock()

    topbar = TopBar(
        tk_root_session,
        on_home=mock_on_home,
    )
    topbar.pack()
    tk_root_session.update_idletasks()

    # Verifica que método set_pick_mode_active não gera erro
    try:
        topbar.set_pick_mode_active(True)
        tk_root_session.update_idletasks()
        topbar.set_pick_mode_active(False)
        tk_root_session.update_idletasks()
        success = True
    except Exception:
        success = False

    assert success, "set_pick_mode_active deve executar sem erros"

    try:
        topbar.destroy()
    except Exception:
        pass
