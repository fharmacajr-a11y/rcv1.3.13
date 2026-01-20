# -*- coding: utf-8 -*-
"""Teste de gap crítico: estado desabilitado do Footer (Microfase 13).

Este teste cobre o gap identificado na linha ~65-90 de footer.py onde:
- Botões entram em estado disabled durante pick mode
- Estado original é preservado e restaurado corretamente

Gap crítico encontrado no trace coverage (Microfase 12):
- footer.py:74-90 (enter_pick_mode e exception handlers)

Criado na Microfase 13 (2026-01-14).
"""

from __future__ import annotations

import tkinter as tk
from typing import Any

import pytest


def test_footer_disabled_state_preserved_during_pick_mode(tk_root: Any) -> None:
    """Valida que footer preserva/restaura estado disabled corretamente em pick mode.
    
    Gap coberto: footer.py linhas ~74-90
    
    Fluxo:
    1. Cria footer com callbacks no-op
    2. Força um botão para estado "disabled" ANTES do pick mode
    3. Entra em pick mode → todos ficam disabled
    4. Sai do pick mode → botão volta para "disabled" (preservado)
    
    Critério de aceite:
    - Estado original (disabled) é preservado após leave_pick_mode
    - Nenhuma exceção durante ciclo
    """
    from src.modules.clientes.views.footer import ClientesFooter

    # Cria footer com callbacks no-op
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

    # SETUP: Força btn_novo para disabled ANTES do pick mode
    # (simula botão que já estava disabled por alguma razão de negócio)
    footer.btn_novo.configure(state="disabled")
    footer.btn_editar.configure(state="normal")
    footer.update_idletasks()

    # Captura estado inicial (btn_novo=disabled, btn_editar=normal)
    initial_novo_state = str(footer.btn_novo.cget("state"))  # type: ignore[attr-defined]
    initial_editar_state = str(footer.btn_editar.cget("state"))  # type: ignore[attr-defined]

    assert initial_novo_state == "disabled", "Setup: btn_novo deveria estar disabled"
    assert initial_editar_state == "normal", "Setup: btn_editar deveria estar normal"

    # FASE 1: enter_pick_mode() → todos disabled
    footer.enter_pick_mode()
    footer.update_idletasks()

    # Valida que TODOS ficaram disabled (incluindo o que já estava)
    assert str(footer.btn_novo.cget("state")) == "disabled"  # type: ignore[attr-defined]
    assert str(footer.btn_editar.cget("state")) == "disabled"  # type: ignore[attr-defined]
    assert str(footer.btn_subpastas.cget("state")) == "disabled"  # type: ignore[attr-defined]

    # FASE 2: leave_pick_mode() → restaura estados ORIGINAIS
    footer.leave_pick_mode()
    footer.update_idletasks()

    # CRÍTICO: btn_novo deve voltar para disabled (não para normal)
    restored_novo = str(footer.btn_novo.cget("state"))  # type: ignore[attr-defined]
    restored_editar = str(footer.btn_editar.cget("state"))  # type: ignore[attr-defined]

    assert restored_novo == "disabled", (
        f"btn_novo deveria ter voltado para 'disabled' (estado original), "
        f"mas voltou para: {restored_novo}"
    )

    assert restored_editar == "normal", (
        f"btn_editar deveria ter voltado para 'normal' (estado original), "
        f"mas voltou para: {restored_editar}"
    )


def test_footer_exception_handler_in_enter_pick_mode(tk_root: Any) -> None:
    """Valida que exception handler em enter_pick_mode não explode.
    
    Gap coberto: footer.py linhas ~84-89 (except handler)
    
    Cenário:
    - Força erro ao acessar btn["state"] removendo o botão do widget tree
    - Valida que enter_pick_mode não lança exceção (apenas loga)
    
    Critério de aceite:
    - Nenhuma exceção propagada (except captura corretamente)
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

    # HACK: Destroi btn_novo para forçar erro ao acessar state
    footer.btn_novo.destroy()  # type: ignore[attr-defined]

    # Tenta entrar em pick mode → NÃO deve explodir
    # (o except deve capturar TclError/KeyError/AttributeError)
    try:
        footer.enter_pick_mode()
        # Se chegou aqui, exception foi capturada corretamente
    except Exception as exc:
        pytest.fail(
            f"enter_pick_mode deveria capturar exceção internamente, "
            f"mas propagou: {exc}"
        )


def test_footer_exception_handler_in_leave_pick_mode(tk_root: Any) -> None:
    """Valida que exception handler em leave_pick_mode não explode.
    
    Gap coberto: footer.py linhas ~102-107 (except handler)
    
    Cenário:
    - Entra em pick mode normalmente
    - Destroi botão DURANTE pick mode
    - Sai do pick mode → não deve explodir
    
    Critério de aceite:
    - Nenhuma exceção propagada (except captura corretamente)
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

    # HACK: Destroi btn_editar DURANTE pick mode
    footer.btn_editar.destroy()  # type: ignore[attr-defined]

    # Tenta sair do pick mode → NÃO deve explodir
    try:
        footer.leave_pick_mode()
        # Se chegou aqui, exception foi capturada corretamente
    except Exception as exc:
        pytest.fail(
            f"leave_pick_mode deveria capturar exceção internamente, "
            f"mas propagou: {exc}"
        )


def test_footer_multiple_cycles_with_disabled_state(tk_root: Any) -> None:
    """Valida múltiplos ciclos de pick mode preservam estado disabled.
    
    Gap coberto: footer.py linhas ~74-109 (ciclo completo)
    
    Fluxo:
    1. Força btn_novo=disabled, btn_editar=normal
    2. Executa 3 ciclos de enter/leave pick mode
    3. Valida que estados são preservados em TODOS os ciclos
    
    Critério de aceite:
    - btn_novo permanece disabled após todos os ciclos
    - btn_editar permanece normal após todos os ciclos
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

    # Setup: estados mistos
    footer.btn_novo.configure(state="disabled")
    footer.btn_editar.configure(state="normal")
    footer.btn_subpastas.configure(state="normal")
    footer.update_idletasks()

    # Executa 3 ciclos
    for cycle in range(1, 4):
        # Enter pick mode
        footer.enter_pick_mode()
        footer.update_idletasks()

        # Valida que todos estão disabled
        assert str(footer.btn_novo.cget("state")) == "disabled"  # type: ignore[attr-defined]
        assert str(footer.btn_editar.cget("state")) == "disabled"  # type: ignore[attr-defined]
        assert str(footer.btn_subpastas.cget("state")) == "disabled"  # type: ignore[attr-defined]

        # Leave pick mode
        footer.leave_pick_mode()
        footer.update_idletasks()

        # Valida que estados originais foram restaurados
        assert str(footer.btn_novo.cget("state")) == "disabled", (  # type: ignore[attr-defined]
            f"Ciclo {cycle}: btn_novo deveria permanecer disabled"
        )
        assert str(footer.btn_editar.cget("state")) == "normal", (  # type: ignore[attr-defined]
            f"Ciclo {cycle}: btn_editar deveria permanecer normal"
        )
        assert str(footer.btn_subpastas.cget("state")) == "normal", (  # type: ignore[attr-defined]
            f"Ciclo {cycle}: btn_subpastas deveria permanecer normal"
        )
