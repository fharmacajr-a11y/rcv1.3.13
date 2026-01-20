# -*- coding: utf-8 -*-
"""Smoke test: Import de ClientFormViewCTK.

Testa que a classe ClientFormViewCTK pode ser importada quando
CustomTkinter está disponível.

Microfase: 5 (Forms CustomTkinter)
"""

from __future__ import annotations

import pytest


def test_client_form_view_ctk_import():
    """Testa que ClientFormViewCTK pode ser importada."""
    pytest.importorskip("customtkinter")

    from src.modules.clientes.forms.client_form_view_ctk import ClientFormViewCTK

    assert ClientFormViewCTK is not None
    assert hasattr(ClientFormViewCTK, "__init__")
    assert hasattr(ClientFormViewCTK, "build_ui")
    assert hasattr(ClientFormViewCTK, "show")
    assert hasattr(ClientFormViewCTK, "close")


def test_client_form_ui_builders_ctk_import():
    """Testa que UI builders CTk podem ser importados."""
    pytest.importorskip("customtkinter")

    from src.modules.clientes.forms.client_form_ui_builders_ctk import (
        create_labeled_entry_ctk,
        create_labeled_textbox_ctk,
        create_status_dropdown_ctk,
        create_button_ctk,
        create_separator_ctk,
        bind_dirty_tracking_ctk,
        HAS_CUSTOMTKINTER,
    )

    assert HAS_CUSTOMTKINTER is True
    assert create_labeled_entry_ctk is not None
    assert create_labeled_textbox_ctk is not None
    assert create_status_dropdown_ctk is not None
    assert create_button_ctk is not None
    assert create_separator_ctk is not None
    assert bind_dirty_tracking_ctk is not None


def test_client_form_facade_has_customtkinter_flag():
    """Testa que facade tem flag HAS_CUSTOMTKINTER."""
    from src.modules.clientes.forms.client_form import HAS_CUSTOMTKINTER

    # Flag deve existir (True ou False dependendo de customtkinter estar instalado)
    assert isinstance(HAS_CUSTOMTKINTER, bool)


def test_client_form_facade_can_import_view_ctk_if_available():
    """Testa que facade pode importar ClientFormViewCTK se customtkinter disponível."""
    from src.modules.clientes.forms.client_form import HAS_CUSTOMTKINTER, ClientFormViewCTK

    if HAS_CUSTOMTKINTER:
        assert ClientFormViewCTK is not None
        assert hasattr(ClientFormViewCTK, "__init__")
    else:
        # Se CustomTkinter não disponível, ClientFormViewCTK deve ser None
        assert ClientFormViewCTK is None
