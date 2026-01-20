# -*- coding: utf-8 -*-
"""Runtime contract test para Pick Mode da ActionBar do módulo Clientes.

Este teste valida o CONTRATO de runtime do pick mode (Microfase 11):
- enter_pick_mode() desabilita botões e preserva estado original
- leave_pick_mode() restaura exatamente o estado anterior
- Botões expõem API esperada: configure, cget (se ctk) ou __getitem__ (se tk)

⚠️ IMPORTANTE: Estes testes são a "guarda de runtime" para complementar
   o _type_sanity.py (guarda de type checking). Se alguém quebrar a API
   dos widgets (remover cget/__getitem__), estes testes FALHAM antes de
   afetar produção.

Criado na Microfase 11 (2026-01-14).
"""

from __future__ import annotations

import pytest


def test_actionbar_pick_mode_roundtrip_restores_state(tk_root):
    """Valida que enter_pick_mode/leave_pick_mode preservam/restauram estados.
    
    Fluxo:
    1. Cria actionbar com callbacks no-op
    2. Captura estado inicial dos botões (btn_novo, btn_editar, btn_subpastas)
    3. Chama enter_pick_mode() → botões devem ficar "disabled"
    4. Chama leave_pick_mode() → botões devem voltar ao estado original
    
    Critério de aceite:
    - Estado após leave_pick_mode == estado antes de enter_pick_mode
    - Nenhuma exceção lançada durante o ciclo
    """
    pytest.importorskip("customtkinter")

    from src.modules.clientes.appearance import ClientesThemeManager, HAS_CUSTOMTKINTER
    from src.modules.clientes.views.actionbar_ctk import ClientesActionBarCtk

    assert HAS_CUSTOMTKINTER, "Este teste requer customtkinter"

    theme_manager = ClientesThemeManager()

    # Cria actionbar com callbacks no-op
    actionbar = ClientesActionBarCtk(
        tk_root,
        on_novo=lambda: None,
        on_editar=lambda: None,
        on_subpastas=lambda: None,
        on_excluir=lambda: None,
        theme_manager=theme_manager,
    )

    # Força update para garantir que widgets estão inicializados
    actionbar.update_idletasks()

    # Captura estado inicial dos botões
    initial_states = {}
    for btn_name in ["btn_novo", "btn_editar", "btn_subpastas"]:
        btn = getattr(actionbar, btn_name, None)
        if btn is not None:
            # Usa cget se disponível (customtkinter)
            if hasattr(btn, "cget"):
                initial_states[btn_name] = btn.cget("state")
            else:
                # Fallback para __getitem__ (tkinter padrão)
                initial_states[btn_name] = btn["state"]

    assert len(initial_states) > 0, "Nenhum botão encontrado na actionbar"

    # FASE 1: enter_pick_mode() deve desabilitar todos os botões
    actionbar.enter_pick_mode()
    actionbar.update_idletasks()

    for btn_name in initial_states:
        btn = getattr(actionbar, btn_name)
        if hasattr(btn, "cget"):
            current_state = btn.cget("state")
        else:
            current_state = btn["state"]
        
        assert current_state == "disabled", (
            f"Botão {btn_name} deveria estar 'disabled' após enter_pick_mode(), "
            f"mas está: {current_state}"
        )

    # FASE 2: leave_pick_mode() deve restaurar estado original
    actionbar.leave_pick_mode()
    actionbar.update_idletasks()

    for btn_name, expected_state in initial_states.items():
        btn = getattr(actionbar, btn_name)
        if hasattr(btn, "cget"):
            restored_state = btn.cget("state")
        else:
            restored_state = btn["state"]
        
        assert restored_state == expected_state, (
            f"Botão {btn_name} deveria ter estado '{expected_state}' após leave_pick_mode(), "
            f"mas tem: {restored_state}"
        )


def test_actionbar_pick_buttons_support_expected_api(tk_root):
    """Valida que botões do pick mode expõem API esperada (configure + cget/__getitem__).
    
    Fluxo:
    1. Cria actionbar
    2. Chama _iter_pick_buttons() para listar botões controlados
    3. Para cada botão:
       - Valida que tem configure()
       - Se HAS_CUSTOMTKINTER: valida cget()
       - Se não: valida __getitem__ (btn["state"])
    
    Critério de aceite:
    - Todos os botões suportam configure()
    - Todos os botões suportam cget() OU __getitem__["state"]
    - Nenhuma exceção ao chamar esses métodos
    
    ⚠️ Se este teste falhar, significa que:
       - Stubs foram quebrados (/typings/customtkinter ou tkinter)
       - Widget real não implementa a API esperada
       - Protocol SupportsCgetConfigure está divergente do real
    """
    pytest.importorskip("customtkinter")

    from src.modules.clientes.appearance import ClientesThemeManager, HAS_CUSTOMTKINTER
    from src.modules.clientes.views.actionbar_ctk import ClientesActionBarCtk

    assert HAS_CUSTOMTKINTER, "Este teste requer customtkinter"

    theme_manager = ClientesThemeManager()

    actionbar = ClientesActionBarCtk(
        tk_root,
        on_novo=lambda: None,
        on_editar=lambda: None,
        on_subpastas=lambda: None,
        theme_manager=theme_manager,
    )

    actionbar.update_idletasks()

    # Obtém lista de botões controlados em pick mode
    pick_buttons = actionbar._iter_pick_buttons()

    assert len(pick_buttons) > 0, "Nenhum botão retornado por _iter_pick_buttons()"

    # Valida API de cada botão
    for btn in pick_buttons:
        # CONTRATO 1: configure() deve existir
        assert hasattr(btn, "configure"), (
            f"Botão {btn} não tem método configure() — API quebrada!"
        )

        # Testa configure() em runtime (não deve lançar exceção)
        try:
            btn.configure(state="normal")
        except Exception as exc:
            pytest.fail(
                f"Botão {btn}.configure(state='normal') lançou exceção: {exc}"
            )

        # CONTRATO 2: cget() ou __getitem__ devem existir
        if HAS_CUSTOMTKINTER:
            # CustomTkinter: espera-se cget()
            assert hasattr(btn, "cget"), (
                f"Botão CustomTkinter {btn} não tem método cget() — stub quebrado!"
            )

            try:
                state = btn.cget("state")
                assert state is not None, f"cget('state') retornou None para {btn}"
            except Exception as exc:
                pytest.fail(
                    f"Botão {btn}.cget('state') lançou exceção: {exc}"
                )
        else:
            # tkinter padrão: espera-se __getitem__ (btn["state"])
            try:
                state = btn["state"]
                assert state is not None, f"btn['state'] retornou None para {btn}"
            except Exception as exc:
                pytest.fail(
                    f"Botão {btn}['state'] lançou exceção: {exc}"
                )


def test_pick_mode_survives_multiple_cycles(tk_root):
    """Valida que pick mode pode ser chamado múltiplas vezes sem corromper estados.
    
    Fluxo:
    1. Cria actionbar
    2. Executa 3 ciclos de enter_pick_mode/leave_pick_mode
    3. Valida que estado final == estado inicial após cada ciclo
    
    Critério de aceite:
    - Estado restaurado corretamente em todos os ciclos
    - _pick_prev_states é limpo após cada leave_pick_mode()
    """
    pytest.importorskip("customtkinter")

    from src.modules.clientes.appearance import ClientesThemeManager, HAS_CUSTOMTKINTER
    from src.modules.clientes.views.actionbar_ctk import ClientesActionBarCtk

    assert HAS_CUSTOMTKINTER, "Este teste requer customtkinter"

    theme_manager = ClientesThemeManager()

    actionbar = ClientesActionBarCtk(
        tk_root,
        on_novo=lambda: None,
        on_editar=lambda: None,
        on_subpastas=lambda: None,
        theme_manager=theme_manager,
    )

    actionbar.update_idletasks()

    # Captura estado inicial
    initial_state = actionbar.btn_novo.cget("state") if hasattr(actionbar.btn_novo, "cget") else actionbar.btn_novo["state"]  # type: ignore[attr-defined]

    # Executa 3 ciclos
    for cycle in range(1, 4):
        # Enter pick mode
        actionbar.enter_pick_mode()
        actionbar.update_idletasks()

        # Valida que botão foi desabilitado
        current = actionbar.btn_novo.cget("state") if hasattr(actionbar.btn_novo, "cget") else actionbar.btn_novo["state"]  # type: ignore[attr-defined]
        assert current == "disabled", f"Ciclo {cycle}: botão não foi desabilitado"

        # Leave pick mode
        actionbar.leave_pick_mode()
        actionbar.update_idletasks()

        # Valida que estado foi restaurado
        restored = actionbar.btn_novo.cget("state") if hasattr(actionbar.btn_novo, "cget") else actionbar.btn_novo["state"]  # type: ignore[attr-defined]
        assert restored == initial_state, (
            f"Ciclo {cycle}: estado não foi restaurado (esperado={initial_state}, atual={restored})"
        )

        # Valida que cache interno foi limpo
        assert len(actionbar._pick_prev_states) == 0, (
            f"Ciclo {cycle}: _pick_prev_states não foi limpo após leave_pick_mode()"
        )


def test_pick_mode_handles_manual_state_change_during_pick(tk_root):
    """Valida comportamento se estado do botão mudar DURANTE pick mode.
    
    Cenário:
    1. Captura estado inicial (ex: "normal")
    2. enter_pick_mode() → botão vira "disabled"
    3. Alguém chama manualmente btn.configure(state="active") durante pick mode
    4. leave_pick_mode() → deve restaurar estado ORIGINAL ("normal"), não "active"
    
    Critério de aceite:
    - leave_pick_mode() restaura o estado de ANTES do enter_pick_mode()
    - Mudanças durante pick mode não afetam restauração
    """
    pytest.importorskip("customtkinter")

    from src.modules.clientes.appearance import ClientesThemeManager, HAS_CUSTOMTKINTER
    from src.modules.clientes.views.actionbar_ctk import ClientesActionBarCtk

    assert HAS_CUSTOMTKINTER, "Este teste requer customtkinter"

    theme_manager = ClientesThemeManager()

    actionbar = ClientesActionBarCtk(
        tk_root,
        on_novo=lambda: None,
        on_editar=lambda: None,
        on_subpastas=lambda: None,
        theme_manager=theme_manager,
    )

    actionbar.update_idletasks()

    # Captura estado inicial
    initial = actionbar.btn_novo.cget("state") if hasattr(actionbar.btn_novo, "cget") else actionbar.btn_novo["state"]  # type: ignore[attr-defined]

    # Enter pick mode
    actionbar.enter_pick_mode()

    # Simula mudança manual durante pick mode (ex: por outro componente)
    actionbar.btn_novo.configure(state="active")

    # Leave pick mode
    actionbar.leave_pick_mode()
    actionbar.update_idletasks()

    # Estado restaurado deve ser o ORIGINAL (antes do enter), não "active"
    restored = actionbar.btn_novo.cget("state") if hasattr(actionbar.btn_novo, "cget") else actionbar.btn_novo["state"]  # type: ignore[attr-defined]
    assert restored == initial, (
        f"Estado restaurado deveria ser '{initial}' (original), mas é '{restored}'"
    )
