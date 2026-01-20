# -*- coding: utf-8 -*-
"""Smoke test para validar actionbar CustomTkinter no módulo Clientes.

Este teste valida:
1. Importação da ClientesActionBarCtk sem erro
2. Criação da actionbar com callbacks
3. update_state() não lança exceção
4. refresh_colors() não lança exceção
5. Botões mudam state conforme update_state()
6. Compatibilidade com enter_pick_mode/leave_pick_mode
"""

from __future__ import annotations

import pytest


def test_actionbar_imports_successfully():
    """Testa se ClientesActionBarCtk pode ser importada sem erro."""
    try:
        from src.modules.clientes.views.actionbar_ctk import ClientesActionBarCtk
        from src.modules.clientes.appearance import HAS_CUSTOMTKINTER

        assert ClientesActionBarCtk is not None
        assert isinstance(HAS_CUSTOMTKINTER, bool)
    except ImportError:
        pytest.skip("CustomTkinter não disponível")


def test_actionbar_creates_with_callbacks(tk_root):
    """Testa se actionbar é criada com callbacks simples."""
    pytest.importorskip("customtkinter")

    from src.modules.clientes.appearance import ClientesThemeManager
    from src.modules.clientes.views.actionbar_ctk import ClientesActionBarCtk

    theme_manager = ClientesThemeManager()

    actionbar = ClientesActionBarCtk(
        tk_root,
        on_novo=lambda: None,
        on_editar=lambda: None,
        on_subpastas=lambda: None,
        on_excluir=lambda: None,
        theme_manager=theme_manager,
    )

    # Valida que actionbar foi criada
    assert actionbar is not None
    assert actionbar.winfo_exists()

    # Valida que botões existem
    assert hasattr(actionbar, "btn_novo")
    assert hasattr(actionbar, "btn_editar")
    assert hasattr(actionbar, "btn_subpastas")
    assert hasattr(actionbar, "btn_excluir")


def test_actionbar_update_state_no_exception(tk_root):
    """Testa se update_state() não lança exceção."""
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

    # Não deve lançar exceção
    actionbar.update_state(has_selection=False)
    actionbar.update_state(has_selection=True)


def test_actionbar_refresh_colors_no_exception(tk_root):
    """Testa se refresh_colors() não lança exceção."""
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

    # Alterna tema e chama refresh
    theme_manager.toggle()
    actionbar.refresh_colors(theme_manager)

    # Não deve lançar exceção
    assert actionbar.winfo_exists()


def test_actionbar_buttons_change_state(tk_root):
    """Testa se botões mudam state conforme update_state()."""
    pytest.importorskip("customtkinter")

    from src.modules.clientes.appearance import ClientesThemeManager
    from src.modules.clientes.views.actionbar_ctk import ClientesActionBarCtk

    theme_manager = ClientesThemeManager()

    actionbar = ClientesActionBarCtk(
        tk_root,
        on_novo=lambda: None,
        on_editar=lambda: None,
        on_subpastas=lambda: None,
        on_excluir=lambda: None,
        theme_manager=theme_manager,
    )

    # Estado inicial: sem seleção
    actionbar.update_state(has_selection=False)
    
    # Novo sempre habilitado
    assert actionbar.btn_novo.cget("state") == "normal"  # type: ignore[union-attr]
    
    # Editar/Arquivos/Excluir desabilitados
    assert actionbar.btn_editar.cget("state") == "disabled"  # type: ignore[union-attr]
    assert actionbar.btn_subpastas.cget("state") == "disabled"  # type: ignore[union-attr]
    assert actionbar.btn_excluir.cget("state") == "disabled"  # type: ignore[union-attr]

    # Com seleção: habilita botões dependentes
    actionbar.update_state(has_selection=True)
    
    assert actionbar.btn_novo.cget("state") == "normal"  # type: ignore[union-attr]
    assert actionbar.btn_editar.cget("state") == "normal"  # type: ignore[union-attr]
    assert actionbar.btn_subpastas.cget("state") == "normal"  # type: ignore[union-attr]
    assert actionbar.btn_excluir.cget("state") == "normal"  # type: ignore[union-attr]


def test_actionbar_enter_leave_pick_mode(tk_root):
    """Testa se enter_pick_mode/leave_pick_mode funcionam sem exceção."""
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

    # Habilita botões primeiro
    actionbar.update_state(has_selection=True)

    # Enter pick mode - deve desabilitar
    actionbar.enter_pick_mode()
    
    # Não deve lançar exceção
    assert actionbar.winfo_exists()

    # Leave pick mode - deve restaurar
    actionbar.leave_pick_mode()
    
    # Não deve lançar exceção
    assert actionbar.winfo_exists()


@pytest.mark.skip(
    reason=(
        "CustomTkinter é dependência obrigatória do projeto (requirements.txt). "
        "Teste de fallback quando CTK indisponível não é mais aplicável. "
        "Mock complexo causava 'halted; None in sys.modules'. "
        "Mantido como referência histórica (código comentado abaixo)."
    )
)
def test_actionbar_fallback_when_ctk_unavailable(tk_root, monkeypatch):
    """[OBSOLETO] Testa fallback quando CustomTkinter não disponível.
    
    HISTÓRICO:
    Este teste era relevante quando CustomTkinter era opcional.
    Desde a Microfase 3, CustomTkinter tornou-se dependência obrigatória.
    
    PROBLEMA:
    Mock de sys.modules["customtkinter"] = None causava erro:
    "ModuleNotFoundError: __import__ halted; None in sys.modules"
    
    DECISÃO:
    Marcado como skip permanente (Microfase 19.4).
    Código preservado abaixo como referência histórica.
    """
    pass  # Skip - código comentado abaixo para referência
    
    # Código original comentado (causa "halted; None in sys.modules"):
    # import sys
    # ctk_module = sys.modules.get("customtkinter")
    # if ctk_module:
    #     monkeypatch.setitem(sys.modules, "customtkinter", None)
    # 
    # import importlib
    # import src.modules.clientes.views.actionbar_ctk as actionbar_module
    # importlib.reload(actionbar_module)
    #
    # from src.modules.clientes.views.actionbar_ctk import ClientesActionBarCtk
    #
    # actionbar = ClientesActionBarCtk(
    #     tk_root,
    #     on_novo=lambda: None,
    #     on_editar=lambda: None,
    #     on_subpastas=lambda: None,
    # )
    #
    # assert actionbar is not None
    # assert actionbar.winfo_exists()
    # assert hasattr(actionbar, "btn_novo")


def test_actionbar_without_excluir_button(tk_root):
    """Testa se actionbar funciona sem botão Excluir (opcional)."""
    pytest.importorskip("customtkinter")

    from src.modules.clientes.appearance import ClientesThemeManager
    from src.modules.clientes.views.actionbar_ctk import ClientesActionBarCtk

    theme_manager = ClientesThemeManager()

    actionbar = ClientesActionBarCtk(
        tk_root,
        on_novo=lambda: None,
        on_editar=lambda: None,
        on_subpastas=lambda: None,
        on_excluir=None,  # Sem botão Excluir
        theme_manager=theme_manager,
    )

    assert actionbar is not None
    assert actionbar.btn_excluir is None


def test_actionbar_palette_colors_applied(tk_root):
    """Testa se cores da paleta são aplicadas nos botões."""
    pytest.importorskip("customtkinter")

    from src.modules.clientes.appearance import ClientesThemeManager
    from src.modules.clientes.views.actionbar_ctk import ClientesActionBarCtk

    theme_manager = ClientesThemeManager()
    palette = theme_manager.get_palette()

    actionbar = ClientesActionBarCtk(
        tk_root,
        on_novo=lambda: None,
        on_editar=lambda: None,
        on_subpastas=lambda: None,
        on_excluir=lambda: None,
        theme_manager=theme_manager,
    )

    # Valida que palette possui cores necessárias
    assert "accent" in palette
    assert "neutral_btn" in palette
    assert "danger" in palette

    # Valida que botões foram criados (cores aplicadas internamente)
    assert actionbar.btn_novo is not None
    assert actionbar.btn_editar is not None
    assert actionbar.btn_subpastas is not None
    assert actionbar.btn_excluir is not None
