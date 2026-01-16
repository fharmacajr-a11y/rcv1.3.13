# -*- coding: utf-8 -*-
"""Smoke test: Criação de ClientFormViewCTK sem crash.

Testa que ClientFormViewCTK pode ser instanciada e construída
sem causar erros (se GUI disponível).

Microfase: 5 (Forms CustomTkinter)
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest


@pytest.mark.skipif(
    not pytest.importorskip("customtkinter", reason="CustomTkinter não instalado"),
    reason="CustomTkinter não disponível",
)
def test_client_form_view_ctk_create_no_crash(tk_root):
    """Testa criação de ClientFormViewCTK sem crash.

    Requer:
        - CustomTkinter instalado
        - GUI disponível (tk_root fixture)
    """
    pytest.importorskip("customtkinter")

    from src.modules.clientes.forms.client_form_view_ctk import ClientFormViewCTK

    # Mock handlers
    handlers = Mock()
    handlers.on_save = Mock()
    handlers.on_save_and_upload = Mock()
    handlers.on_cartao_cnpj = Mock()
    handlers.on_cancel = Mock()
    handlers.on_senhas = Mock()
    handlers.on_dirty = Mock()

    # Tentar criar view
    try:
        view = ClientFormViewCTK(
            parent=tk_root,
            handlers=handlers,
            transient=False,  # Não transient para evitar problemas em CI
        )

        # Verificar que view foi criada
        assert view is not None
        assert view.window is not None
        assert view.ents == {}  # Vazio antes de build_ui

        # Construir UI
        view.build_ui()

        # Verificar que campos foram criados
        assert len(view.ents) > 0
        assert "Razão Social" in view.ents
        assert "CNPJ" in view.ents
        assert "Nome" in view.ents
        assert "WhatsApp" in view.ents
        assert "Observações" in view.ents
        assert "Status do Cliente" in view.ents

        # Verificar campos internos
        assert view.internal_vars is not None
        assert "endereco" in view.internal_vars
        assert "bairro" in view.internal_vars
        assert "cidade" in view.internal_vars
        assert "cep" in view.internal_vars

        # Verificar botões
        assert view.btn_upload is not None
        assert view.btn_cartao_cnpj is not None

        # Testar métodos públicos
        view.set_title("Teste")
        assert view.window.title() == "Teste"

        view.disable_upload_button()
        view.enable_upload_button()

        view.disable_cartao_cnpj_button()
        view.enable_cartao_cnpj_button()

        # Testar fill_fields e get_field_value
        view.fill_fields({"Razão Social": "Teste LTDA", "CNPJ": "12.345.678/0001-90"})
        razao = view.get_field_value("Razão Social")
        assert "Teste" in razao

        # Fechar view
        view.close()
        assert view.window is None

    except Exception as e:
        pytest.fail(f"ClientFormViewCTK criação causou erro: {e}")


@pytest.mark.skipif(
    not pytest.importorskip("customtkinter", reason="CustomTkinter não instalado"),
    reason="CustomTkinter não disponível",
)
def test_client_form_ui_builders_ctk_create_widgets(tk_root):
    """Testa que UI builders CTk criam widgets sem crash."""
    pytest.importorskip("customtkinter")

    from src.ui.ctk_config import ctk
    from src.modules.clientes.forms.client_form_ui_builders_ctk import (
        create_labeled_entry_ctk,
        create_labeled_textbox_ctk,
        create_status_dropdown_ctk,
        create_button_ctk,
        create_separator_ctk,
    )

    # Frame de teste
    frame = ctk.CTkFrame(tk_root)
    frame.pack()

    # Testar create_labeled_entry_ctk
    lbl, entry, next_row = create_labeled_entry_ctk(frame, "Teste Entry:", 0)
    assert lbl is not None
    assert entry is not None
    assert next_row == 2

    # Testar create_labeled_textbox_ctk
    lbl2, textbox, text_row, next_row2 = create_labeled_textbox_ctk(frame, "Teste Textbox:", 2)
    assert lbl2 is not None
    assert textbox is not None
    assert text_row == 3
    assert next_row2 == 4

    # Testar create_status_dropdown_ctk
    lbl3, dropdown, next_row3 = create_status_dropdown_ctk(frame, "Status:", ["Ativo", "Inativo"], 4)
    assert lbl3 is not None
    assert dropdown is not None
    assert next_row3 == 6

    # Testar create_button_ctk
    btn = create_button_ctk(frame, "Teste Button", command=lambda: None)
    assert btn is not None

    # Testar create_separator_ctk
    sep, next_row4 = create_separator_ctk(frame, 6)
    assert sep is not None
    assert next_row4 == 7

    # Limpar
    frame.destroy()
