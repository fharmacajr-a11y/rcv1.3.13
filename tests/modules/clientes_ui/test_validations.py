# -*- coding: utf-8 -*-
"""Testes de validações para ClientesV2 - FASE 3.2.

Testa validações de duplicatas (CNPJ, Razão Social, Telefone) no formulário de cliente.
"""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock
from typing import Any


@pytest.fixture
def mock_client_data() -> dict[str, Any]:
    """Dados de exemplo de um cliente existente."""
    return {
        "id": 1,
        "razao_social": "Empresa ABC Ltda",
        "cnpj": "11.222.333/0001-44",
        "nome": "João Silva",
        "whatsapp": "11999999999",
        "observacoes": "[Ativo] Cliente VIP",
    }


@pytest.fixture
def mock_conflicting_client() -> dict[str, Any]:
    """Cliente com CNPJ/dados conflitantes."""
    return {
        "id": 2,
        "razao_social": "Empresa XYZ",
        "cnpj": "11.222.333/0001-44",  # CNPJ duplicado
        "nome": "Maria Santos",
        "whatsapp": "11888888888",
    }


def test_validation_rejects_duplicate_cnpj_new_client(tk_root, monkeypatch):
    """Test que bloqueia salvar novo cliente com CNPJ duplicado."""
    from src.modules.clientes.ui.views.client_editor_dialog import ClientEditorDialog

    # Mock do checar_duplicatas_para_form retornando conflito de CNPJ
    mock_check = MagicMock(
        return_value={
            "cnpj_conflict": {"id": 2, "razao_social": "Empresa XYZ"},
            "razao_conflicts": [],
            "numero_conflicts": [],
            "blocking_fields": {"cnpj": True, "razao": False},
            "conflict_ids": {"cnpj": [2], "razao": [], "numero": []},
        }
    )

    # Mock do messagebox.showerror
    mock_showerror = MagicMock()

    with (
        patch("src.modules.clientes.service.checar_duplicatas_para_form", mock_check),
        patch("tkinter.messagebox.showerror", mock_showerror),
    ):
        # Criar dialog para novo cliente
        dialog = ClientEditorDialog(tk_root, client_id=None)

        # Preencher campos
        dialog.razao_entry.insert(0, "Nova Empresa")
        dialog.cnpj_entry.insert(0, "11.222.333/0001-44")
        dialog.nome_entry.insert(0, "Contato")
        dialog.whatsapp_entry.insert(0, "11999999999")

        # Tentar salvar
        dialog._on_save_clicked()

        # Verificar que chamou checar_duplicatas_para_form
        assert mock_check.called, "Deve chamar checar_duplicatas_para_form"

        # Verificar que mostrou erro de CNPJ duplicado
        assert mock_showerror.called, "Deve mostrar erro de CNPJ duplicado"
        call_args = mock_showerror.call_args[0]
        assert "CNPJ" in call_args[1].upper(), "Mensagem deve mencionar CNPJ duplicado"

        # Dialog não deve ser destruído (salvar foi bloqueado)
        assert dialog.winfo_exists(), "Dialog deve permanecer aberto após erro"


def test_validation_accepts_own_cnpj_when_editing(tk_root, monkeypatch):
    """Test que aceita CNPJ próprio ao editar mesmo cliente."""
    from src.modules.clientes.ui.views.client_editor_dialog import ClientEditorDialog

    # Mock do checar_duplicatas_para_form retornando sem conflitos
    # (CNPJ é do próprio cliente sendo editado, então foi filtrado)
    mock_check = MagicMock(
        return_value={
            "cnpj_conflict": None,  # Filtrado porque é o próprio cliente
            "razao_conflicts": [],
            "numero_conflicts": [],
            "blocking_fields": {"cnpj": False, "razao": False},
            "conflict_ids": {"cnpj": [], "razao": [], "numero": []},
        }
    )

    # Mock do salvar_cliente_a_partir_do_form
    mock_save = MagicMock(return_value=({"id": 1}, None))

    # Mock do fetch_cliente_by_id para carregar dados (chamado no __init__)
    mock_fetch_cliente = MagicMock(
        return_value={
            "id": 1,
            "razao_social": "Empresa ABC",
            "cnpj": "11.222.333/0001-44",
            "nome": "Contato",
            "numero": "11999999999",
            "observacoes": "[Ativo] Cliente VIP",
        }
    )

    with (
        patch("src.modules.clientes.service.checar_duplicatas_para_form", mock_check),
        patch("src.modules.clientes.service.salvar_cliente_a_partir_do_form", mock_save),
        patch("src.modules.clientes.service.fetch_cliente_by_id", mock_fetch_cliente),
    ):
        # Criar dialog para editar cliente ID=1
        dialog = ClientEditorDialog(tk_root, client_id=1)

        # Aguardar carregamento e processar eventos
        tk_root.update_idletasks()

        # Simular carregamento dos dados (já que o after(100) pode não executar)
        # Preencher campos manualmente
        dialog.razao_entry.delete(0, "end")
        dialog.razao_entry.insert(0, "Empresa ABC")
        dialog.cnpj_entry.delete(0, "end")
        dialog.cnpj_entry.insert(0, "11.222.333/0001-44")
        dialog.nome_entry.delete(0, "end")
        dialog.nome_entry.insert(0, "Contato")
        dialog.whatsapp_entry.delete(0, "end")
        dialog.whatsapp_entry.insert(0, "11999999999")

        # Tentar salvar (com mesmo CNPJ)
        dialog._on_save_clicked()

        # Verificar que chamou checar_duplicatas_para_form com row=(1,)
        assert mock_check.called, "Deve chamar checar_duplicatas_para_form"
        call_args = mock_check.call_args
        # Segundo argumento deve ser row=(1,)
        assert call_args[0][1] == (1,), "Deve passar row com client_id ao editar"

        # Verificar que chamou salvar (não bloqueou)
        assert mock_save.called, "Deve salvar cliente sem bloquear"


def test_validation_warns_similar_razao_user_cancels(tk_root, monkeypatch):
    """Test que avisa sobre Razão Social similar e respeita cancelamento do usuário."""
    from src.modules.clientes.ui.views.client_editor_dialog import ClientEditorDialog

    # Mock do checar_duplicatas_para_form retornando conflito de razão (não bloqueante)
    mock_check = MagicMock(
        return_value={
            "cnpj_conflict": None,
            "razao_conflicts": [{"id": 3, "razao_social": "Empresa Similar Ltda"}],
            "numero_conflicts": [],
            "blocking_fields": {"cnpj": False, "razao": True},  # razao é warning, não bloqueia hard
            "conflict_ids": {"cnpj": [], "razao": [3], "numero": []},
        }
    )

    # Mock do messagebox.askyesno retornando False (usuário cancelou)
    mock_askyesno = MagicMock(return_value=False)

    # Mock do salvar (não deve ser chamado)
    mock_save = MagicMock()

    with (
        patch("src.modules.clientes.service.checar_duplicatas_para_form", mock_check),
        patch("tkinter.messagebox.askyesno", mock_askyesno),
        patch("src.modules.clientes.service.salvar_cliente_a_partir_do_form", mock_save),
    ):
        # Criar dialog para novo cliente
        dialog = ClientEditorDialog(tk_root, client_id=None)

        # Preencher campos
        dialog.razao_entry.insert(0, "Empresa Similar")
        dialog.cnpj_entry.insert(0, "99.888.777/0001-66")
        dialog.nome_entry.insert(0, "Contato")
        dialog.whatsapp_entry.insert(0, "11999999999")

        # Tentar salvar
        dialog._on_save_clicked()

        # Verificar que mostrou aviso
        assert mock_askyesno.called, "Deve mostrar aviso de Razão Social similar"
        call_args = mock_askyesno.call_args[0]
        assert (
            "razão" in call_args[1].lower() or "similar" in call_args[1].lower()
        ), "Mensagem deve mencionar razão social similar"

        # Verificar que NÃO salvou (usuário cancelou)
        assert not mock_save.called, "Não deve salvar se usuário cancelou"

        # Dialog deve permanecer aberto
        assert dialog.winfo_exists(), "Dialog deve permanecer aberto após cancelamento"


def test_validation_warns_similar_razao_user_confirms(tk_root, monkeypatch):
    """Test que avisa sobre Razão Social similar e prossegue se usuário confirmar."""
    from src.modules.clientes.ui.views.client_editor_dialog import ClientEditorDialog

    # Mock do checar_duplicatas_para_form retornando conflito de razão
    mock_check = MagicMock(
        return_value={
            "cnpj_conflict": None,
            "razao_conflicts": [{"id": 3, "razao_social": "Empresa Similar Ltda"}],
            "numero_conflicts": [],
            "blocking_fields": {"cnpj": False, "razao": True},
            "conflict_ids": {"cnpj": [], "razao": [3], "numero": []},
        }
    )

    # Mock do messagebox.askyesno retornando True (usuário confirmou)
    mock_askyesno = MagicMock(return_value=True)

    # Mock do salvar
    mock_save = MagicMock(return_value=({"id": 10}, None))

    with (
        patch("src.modules.clientes.service.checar_duplicatas_para_form", mock_check),
        patch("tkinter.messagebox.askyesno", mock_askyesno),
        patch("src.modules.clientes.service.salvar_cliente_a_partir_do_form", mock_save),
    ):
        # Criar dialog para novo cliente
        dialog = ClientEditorDialog(tk_root, client_id=None)

        # Preencher campos
        dialog.razao_entry.insert(0, "Empresa Similar")
        dialog.cnpj_entry.insert(0, "99.888.777/0001-66")
        dialog.nome_entry.insert(0, "Contato")
        dialog.whatsapp_entry.insert(0, "11999999999")

        # Tentar salvar
        dialog._on_save_clicked()

        # Verificar que mostrou aviso
        assert mock_askyesno.called, "Deve mostrar aviso de Razão Social similar"

        # Verificar que salvou (usuário confirmou)
        assert mock_save.called, "Deve salvar se usuário confirmou"


def test_validation_warns_similar_telefone_user_cancels(tk_root, monkeypatch):
    """Test que avisa sobre telefone similar e respeita cancelamento."""
    from src.modules.clientes.ui.views.client_editor_dialog import ClientEditorDialog

    # Mock do checar_duplicatas_para_form retornando conflito de telefone
    mock_check = MagicMock(
        return_value={
            "cnpj_conflict": None,
            "razao_conflicts": [],
            "numero_conflicts": [{"id": 4, "razao_social": "Outra Empresa", "numero": "11999999999"}],
            "blocking_fields": {"cnpj": False, "razao": False},
            "conflict_ids": {"cnpj": [], "razao": [], "numero": [4]},
        }
    )

    # Mock do messagebox.askyesno retornando False (usuário cancelou)
    mock_askyesno = MagicMock(return_value=False)

    # Mock do salvar (não deve ser chamado)
    mock_save = MagicMock()

    with (
        patch("src.modules.clientes.service.checar_duplicatas_para_form", mock_check),
        patch("tkinter.messagebox.askyesno", mock_askyesno),
        patch("src.modules.clientes.service.salvar_cliente_a_partir_do_form", mock_save),
    ):
        # Criar dialog para novo cliente
        dialog = ClientEditorDialog(tk_root, client_id=None)

        # Preencher campos
        dialog.razao_entry.insert(0, "Nova Empresa")
        dialog.cnpj_entry.insert(0, "99.888.777/0001-66")
        dialog.nome_entry.insert(0, "Contato")
        dialog.whatsapp_entry.insert(0, "11999999999")  # Telefone duplicado

        # Tentar salvar
        dialog._on_save_clicked()

        # Verificar que mostrou aviso
        assert mock_askyesno.called, "Deve mostrar aviso de telefone similar"

        # Verificar que NÃO salvou
        assert not mock_save.called, "Não deve salvar se usuário cancelou"


def test_validation_warns_combined_conflicts(tk_root, monkeypatch):
    """Test que avisa sobre múltiplos conflitos (razão + telefone)."""
    from src.modules.clientes.ui.views.client_editor_dialog import ClientEditorDialog

    # Mock com conflitos múltiplos
    mock_check = MagicMock(
        return_value={
            "cnpj_conflict": None,
            "razao_conflicts": [{"id": 3, "razao_social": "Empresa Similar"}],
            "numero_conflicts": [{"id": 4, "razao_social": "Outra Empresa", "numero": "11999999999"}],
            "blocking_fields": {"cnpj": False, "razao": True},
            "conflict_ids": {"cnpj": [], "razao": [3], "numero": [4]},
        }
    )

    # Mock do messagebox.askyesno retornando False
    mock_askyesno = MagicMock(return_value=False)

    # Mock do salvar
    mock_save = MagicMock()

    with (
        patch("src.modules.clientes.service.checar_duplicatas_para_form", mock_check),
        patch("tkinter.messagebox.askyesno", mock_askyesno),
        patch("src.modules.clientes.service.salvar_cliente_a_partir_do_form", mock_save),
    ):
        # Criar dialog
        dialog = ClientEditorDialog(tk_root, client_id=None)

        # Preencher campos
        dialog.razao_entry.insert(0, "Empresa Similar")
        dialog.cnpj_entry.insert(0, "99.888.777/0001-66")
        dialog.nome_entry.insert(0, "Contato")
        dialog.whatsapp_entry.insert(0, "11999999999")

        # Tentar salvar
        dialog._on_save_clicked()

        # Verificar que mostrou aviso (deve mencionar múltiplos conflitos)
        assert mock_askyesno.called, "Deve mostrar aviso de conflitos"
        call_args = mock_askyesno.call_args[0]
        message = call_args[1].lower()
        # Deve mencionar razão ou telefone ou "clientes similares"
        assert (
            "razão" in message or "telefone" in message or "similar" in message
        ), "Mensagem deve mencionar conflitos encontrados"


def test_validation_no_conflicts_saves_directly(tk_root, monkeypatch):
    """Test que salva diretamente quando não há conflitos."""
    from src.modules.clientes.ui.views.client_editor_dialog import ClientEditorDialog

    # Mock sem conflitos
    mock_check = MagicMock(
        return_value={
            "cnpj_conflict": None,
            "razao_conflicts": [],
            "numero_conflicts": [],
            "blocking_fields": {"cnpj": False, "razao": False},
            "conflict_ids": {"cnpj": [], "razao": [], "numero": []},
        }
    )

    # Mock do salvar
    mock_save = MagicMock(return_value=({"id": 10}, None))

    # Mock do messagebox (não deve ser chamado)
    mock_askyesno = MagicMock()
    mock_showerror = MagicMock()

    with (
        patch("src.modules.clientes.service.checar_duplicatas_para_form", mock_check),
        patch("src.modules.clientes.service.salvar_cliente_a_partir_do_form", mock_save),
        patch("tkinter.messagebox.askyesno", mock_askyesno),
        patch("tkinter.messagebox.showerror", mock_showerror),
    ):
        # Criar dialog
        dialog = ClientEditorDialog(tk_root, client_id=None)

        # Preencher campos
        dialog.razao_entry.insert(0, "Empresa Nova Única")
        dialog.cnpj_entry.insert(0, "12.345.678/0001-90")
        dialog.nome_entry.insert(0, "Contato Único")
        dialog.whatsapp_entry.insert(0, "11987654321")

        # Tentar salvar
        dialog._on_save_clicked()

        # Verificar que salvou diretamente
        assert mock_save.called, "Deve salvar quando não há conflitos"

        # Não deve mostrar avisos
        assert not mock_askyesno.called, "Não deve mostrar aviso quando não há conflitos"
        assert not mock_showerror.called, "Não deve mostrar erro quando não há conflitos"


def test_validation_handles_service_error(tk_root, monkeypatch):
    """Test que trata erro ao chamar serviço de validação."""
    from src.modules.clientes.ui.views.client_editor_dialog import ClientEditorDialog

    # Mock que lança exceção
    mock_check = MagicMock(side_effect=Exception("Erro de conexão"))

    # Mock do messagebox.showerror
    mock_showerror = MagicMock()

    with (
        patch("src.modules.clientes.service.checar_duplicatas_para_form", mock_check),
        patch("tkinter.messagebox.showerror", mock_showerror),
    ):
        # Criar dialog
        dialog = ClientEditorDialog(tk_root, client_id=None)

        # Preencher campos
        dialog.razao_entry.insert(0, "Empresa")
        dialog.cnpj_entry.insert(0, "12.345.678/0001-90")
        dialog.nome_entry.insert(0, "Contato")
        dialog.whatsapp_entry.insert(0, "11987654321")

        # Tentar salvar
        dialog._on_save_clicked()

        # Verificar que mostrou erro
        assert mock_showerror.called, "Deve mostrar erro ao falhar validação"

        # Dialog deve permanecer aberto
        assert dialog.winfo_exists(), "Dialog deve permanecer aberto após erro"
