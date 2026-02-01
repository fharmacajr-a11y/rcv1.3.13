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


def test_topbar_home_button_state_on_screen_change(tk_root_session):
    """REGRESSION: Verifica que botão Início NUNCA fica desabilitado, independente da tela.

    Bug histórico: Após refatoração MainWindow, o botão Início ficava desabilitado (cinza)
    em várias telas (main, hub, auditoria, etc.), impedindo voltar para a tela inicial.

    FIX DEFINITIVO: btn_home SEMPRE habilitado (!disabled) em TODAS as telas.
    Se precisar indicar "tela ativa", usar apenas mudança de estilo/cor, NÃO disabled.

    Comportamento esperado:
    - Em QUALQUER tela → botão Início SEMPRE HABILITADO (para permitir navegação)
    """
    mock_on_home = Mock()

    topbar = TopBar(
        tk_root_session,
        on_home=mock_on_home,
    )
    topbar.pack()
    tk_root_session.update_idletasks()

    # Testar múltiplas telas - btn_home NUNCA deve estar disabled
    test_screens = ["main", "hub", "sites", "cashflow", "auditoria", "anvisa"]

    for screen_name in test_screens:
        topbar.set_active_screen(screen_name)
        tk_root_session.update_idletasks()

        # Verificar que btn_home NÃO está disabled
        is_disabled = topbar._nav.btn_home.instate(["disabled"])
        assert not is_disabled, f"Botão Início NUNCA deve estar disabled, mas está em '{screen_name}'"

    # Testar também com set_is_hub (método legado)
    topbar.set_is_hub(True)
    tk_root_session.update_idletasks()
    is_disabled_hub = topbar._nav.btn_home.instate(["disabled"])
    assert not is_disabled_hub, "Botão Início NUNCA deve estar disabled, mesmo com set_is_hub(True)"

    topbar.set_is_hub(False)
    tk_root_session.update_idletasks()
    is_disabled_not_hub = topbar._nav.btn_home.instate(["disabled"])
    assert not is_disabled_not_hub, "Botão Início NUNCA deve estar disabled com set_is_hub(False)"

    # Testar modo pick (caso especial onde outros botões são desabilitados)
    topbar.set_pick_mode_active(True)
    tk_root_session.update_idletasks()
    is_disabled_pick = topbar._nav.btn_home.instate(["disabled"])
    assert not is_disabled_pick, "Botão Início NUNCA deve estar disabled, mesmo no pick mode"

    try:
        topbar.destroy()
    except Exception:
        pass
