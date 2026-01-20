# -*- coding: utf-8 -*-
"""Testes de smoke para imports do modal CustomTkinter de Clientes.

Microfase: 6 (Subdialogs CustomTkinter)
"""

import pytest

pytest.importorskip("customtkinter")


def test_clientes_modal_ctk_import() -> None:
    """Testa se ClientesModalCTK pode ser importado."""
    from src.modules.clientes.ui import ClientesModalCTK

    assert ClientesModalCTK is not None


def test_clientes_modal_ctk_has_required_methods() -> None:
    """Testa se ClientesModalCTK tem os métodos necessários."""
    from src.modules.clientes.ui import ClientesModalCTK

    assert hasattr(ClientesModalCTK, "confirm")
    assert hasattr(ClientesModalCTK, "alert")
    assert hasattr(ClientesModalCTK, "error")
    assert hasattr(ClientesModalCTK, "info")


def test_clientes_ui_has_customtkinter_flag() -> None:
    """Testa se módulo ui tem flag HAS_CUSTOMTKINTER."""
    from src.modules.clientes.ui import HAS_CUSTOMTKINTER

    assert HAS_CUSTOMTKINTER is True


def test_tk_message_adapter_has_modal_support() -> None:
    """Testa se TkMessageAdapter tem suporte a modal CTk."""
    from src.modules.clientes.forms.client_form_adapters import TkMessageAdapter

    # Verifica que o adaptador pode ser criado com theme_manager
    adapter = TkMessageAdapter(parent=None, theme_manager=None)
    assert adapter is not None
    assert hasattr(adapter, "warn")
    assert hasattr(adapter, "ask_yes_no")
    assert hasattr(adapter, "show_error")
    assert hasattr(adapter, "show_info")
