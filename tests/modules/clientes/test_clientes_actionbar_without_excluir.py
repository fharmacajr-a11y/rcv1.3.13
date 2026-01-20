# -*- coding: utf-8 -*-
"""Teste de gap crítico: actionbar sem callback on_excluir (Microfase 13).

Este teste cobre o gap identificado na linha ~159-177 de actionbar_ctk.py onde:
- Botão excluir é criado condicionalmente (if on_excluir)
- Se não fornecido, btn_excluir = None

Gap crítico encontrado no trace coverage (Microfase 12):
- actionbar_ctk.py:159-177 (criação condicional de btn_excluir)

Criado na Microfase 13 (2026-01-14).
"""

from __future__ import annotations

import pytest


def test_actionbar_without_excluir_callback(tk_root):
    """Valida que actionbar funciona corretamente SEM callback on_excluir.
    
    Gap coberto: actionbar_ctk.py linhas ~159-177
    
    Fluxo:
    1. Cria actionbar COM callbacks no-op, mas SEM on_excluir (None/omitido)
    2. Valida que btn_excluir não é criado (ou é None)
    3. Valida que outros botões funcionam normalmente
    
    Critério de aceite:
    - btn_excluir é None quando on_excluir não é fornecido
    - Outros botões (novo, editar, subpastas) existem normalmente
    """
    pytest.importorskip("customtkinter")

    from src.modules.clientes.appearance import ClientesThemeManager
    from src.modules.clientes.views.actionbar_ctk import ClientesActionBarCtk

    theme_manager = ClientesThemeManager()

    # Cria actionbar SEM on_excluir (comportamento do gap)
    actionbar = ClientesActionBarCtk(
        tk_root,
        on_novo=lambda: None,
        on_editar=lambda: None,
        on_subpastas=lambda: None,
        # on_excluir NÃO é passado (None implícito)
        theme_manager=theme_manager,
    )

    actionbar.update_idletasks()

    # CRÍTICO: btn_excluir deve ser None (não foi criado)
    assert actionbar.btn_excluir is None, (
        "btn_excluir deveria ser None quando on_excluir não é fornecido"
    )

    # Outros botões devem existir normalmente
    assert actionbar.btn_novo is not None, "btn_novo deveria existir"
    assert actionbar.btn_editar is not None, "btn_editar deveria existir"
    assert actionbar.btn_subpastas is not None, "btn_subpastas deveria existir"

    # Valida que botões existentes funcionam (não explodem ao configurar)
    actionbar.btn_novo.configure(state="normal")
    actionbar.btn_editar.configure(state="disabled")
    actionbar.btn_subpastas.configure(state="normal")


def test_actionbar_with_excluir_callback_creates_button(tk_root):
    """Valida que actionbar CRIA btn_excluir quando on_excluir é fornecido.
    
    Gap coberto: actionbar_ctk.py linhas ~159-177 (branch if)
    
    Fluxo:
    1. Cria actionbar COM on_excluir
    2. Valida que btn_excluir foi criado
    3. Valida que botão funciona (configurável)
    
    Critério de aceite:
    - btn_excluir existe e não é None
    - Botão é configurável (state, etc)
    """
    pytest.importorskip("customtkinter")

    from src.modules.clientes.appearance import ClientesThemeManager
    from src.modules.clientes.views.actionbar_ctk import ClientesActionBarCtk

    theme_manager = ClientesThemeManager()

    # Cria actionbar COM on_excluir
    actionbar = ClientesActionBarCtk(
        tk_root,
        on_novo=lambda: None,
        on_editar=lambda: None,
        on_subpastas=lambda: None,
        on_excluir=lambda: None,  # ← Fornecido (branch if)
        theme_manager=theme_manager,
    )

    actionbar.update_idletasks()

    # btn_excluir deve existir
    assert actionbar.btn_excluir is not None, (
        "btn_excluir deveria existir quando on_excluir é fornecido"
    )

    # Valida que botão é funcional
    actionbar.btn_excluir.configure(state="disabled")
    assert actionbar.btn_excluir.cget("state") == "disabled"  # type: ignore[union-attr]

    actionbar.btn_excluir.configure(state="normal")
    assert actionbar.btn_excluir.cget("state") == "normal"  # type: ignore[union-attr]


def test_actionbar_pick_mode_skips_none_excluir_button(tk_root):
    """Valida que pick mode funciona mesmo quando btn_excluir é None.
    
    Gap coberto: actionbar_ctk.py linhas ~294-303 (_iter_pick_buttons)
    
    Fluxo:
    1. Cria actionbar sem on_excluir (btn_excluir=None)
    2. Chama enter_pick_mode/leave_pick_mode
    3. Valida que não explode (não tenta acessar btn_excluir)
    
    Critério de aceite:
    - pick mode funciona normalmente sem btn_excluir
    - Nenhuma exceção lançada
    """
    pytest.importorskip("customtkinter")

    from src.modules.clientes.appearance import ClientesThemeManager
    from src.modules.clientes.views.actionbar_ctk import ClientesActionBarCtk

    theme_manager = ClientesThemeManager()

    # Cria actionbar SEM on_excluir
    actionbar = ClientesActionBarCtk(
        tk_root,
        on_novo=lambda: None,
        on_editar=lambda: None,
        on_subpastas=lambda: None,
        # on_excluir omitido
        theme_manager=theme_manager,
    )

    actionbar.update_idletasks()

    # Captura estado inicial dos botões existentes
    initial_novo = actionbar.btn_novo.cget("state")  # type: ignore[union-attr]
    initial_editar = actionbar.btn_editar.cget("state")  # type: ignore[union-attr]
    initial_subpastas = actionbar.btn_subpastas.cget("state")  # type: ignore[union-attr]

    # Enter pick mode → NÃO deve explodir mesmo sem btn_excluir
    try:
        actionbar.enter_pick_mode()
        actionbar.update_idletasks()
    except Exception as exc:
        pytest.fail(
            f"enter_pick_mode não deveria falhar sem btn_excluir, mas lançou: {exc}"
        )

    # Valida que botões existentes foram desabilitados
    assert actionbar.btn_novo.cget("state") == "disabled"  # type: ignore[union-attr]
    assert actionbar.btn_editar.cget("state") == "disabled"  # type: ignore[union-attr]
    assert actionbar.btn_subpastas.cget("state") == "disabled"  # type: ignore[union-attr]

    # Leave pick mode → restaura estados
    try:
        actionbar.leave_pick_mode()
        actionbar.update_idletasks()
    except Exception as exc:
        pytest.fail(
            f"leave_pick_mode não deveria falhar sem btn_excluir, mas lançou: {exc}"
        )

    # Valida que estados foram restaurados
    assert actionbar.btn_novo.cget("state") == initial_novo  # type: ignore[union-attr]
    assert actionbar.btn_editar.cget("state") == initial_editar  # type: ignore[union-attr]
    assert actionbar.btn_subpastas.cget("state") == initial_subpastas  # type: ignore[union-attr]


def test_actionbar_update_state_without_excluir_button(tk_root):
    """Valida que update_state funciona sem btn_excluir.
    
    Gap coberto: actionbar_ctk.py linhas ~195-228 (update_state)
    
    Fluxo:
    1. Cria actionbar sem on_excluir
    2. Chama update_state(has_selection=True/False)
    3. Valida que não explode ao tentar atualizar btn_excluir
    
    Critério de aceite:
    - update_state não lança exceção quando btn_excluir é None
    - Outros botões são atualizados normalmente
    """
    pytest.importorskip("customtkinter")

    from src.modules.clientes.appearance import ClientesThemeManager
    from src.modules.clientes.views.actionbar_ctk import ClientesActionBarCtk

    theme_manager = ClientesThemeManager()

    # Cria actionbar SEM on_excluir
    actionbar = ClientesActionBarCtk(
        tk_root,
        on_novo=lambda: None,
        on_editar=lambda: None,
        on_subpastas=lambda: None,
        # on_excluir omitido
        theme_manager=theme_manager,
    )

    actionbar.update_idletasks()

    # Testa update_state com has_selection=False
    try:
        actionbar.update_state(has_selection=False)
        actionbar.update_idletasks()
    except Exception as exc:
        pytest.fail(
            f"update_state(has_selection=False) não deveria falhar sem btn_excluir, "
            f"mas lançou: {exc}"
        )

    # btn_editar e btn_subpastas devem estar disabled
    assert actionbar.btn_editar.cget("state") == "disabled"  # type: ignore[union-attr]
    assert actionbar.btn_subpastas.cget("state") == "disabled"  # type: ignore[union-attr]

    # Testa update_state com has_selection=True
    try:
        actionbar.update_state(has_selection=True)
        actionbar.update_idletasks()
    except Exception as exc:
        pytest.fail(
            f"update_state(has_selection=True) não deveria falhar sem btn_excluir, "
            f"mas lançou: {exc}"
        )

    # btn_editar e btn_subpastas devem estar normal
    assert actionbar.btn_editar.cget("state") == "normal"  # type: ignore[union-attr]
    assert actionbar.btn_subpastas.cget("state") == "normal"  # type: ignore[union-attr]
