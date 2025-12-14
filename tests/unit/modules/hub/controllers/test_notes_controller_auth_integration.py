# -*- coding: utf-8 -*-
"""Testes de integração para validar fluxo de autenticação do NotesController.

Este arquivo testa especificamente o cenário reportado no bug:
- Usuário autenticado no Supabase
- HubGatewayImpl retorna dados corretos
- NotesController não bloqueia com "Não autenticado"
- Nota é criada com sucesso
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.modules.hub.controllers.notes_controller import NotesController
from src.modules.hub.viewmodels import NotesViewModel


@pytest.fixture
def mock_gateway_authenticated():
    """Gateway simulando usuário autenticado com sessão válida."""
    gateway = MagicMock()
    gateway.is_authenticated.return_value = True
    gateway.is_online.return_value = True
    gateway.get_org_id.return_value = "org-test-123"
    gateway.get_user_email.return_value = "user@test.com"
    return gateway


@pytest.fixture
def mock_gateway_not_authenticated():
    """Gateway simulando usuário NÃO autenticado."""
    gateway = MagicMock()
    gateway.is_authenticated.return_value = False
    gateway.is_online.return_value = False
    gateway.get_org_id.return_value = None
    gateway.get_user_email.return_value = None
    return gateway


@pytest.fixture
def mock_notes_service():
    """Service de notas mockado que retorna sucesso."""
    service = MagicMock()
    service.create_note.return_value = {
        "id": "note-123",
        "body": "Texto da nota",
        "author_email": "user@test.com",
        "org_id": "org-test-123",
        "created_at": "2025-12-11T00:00:00Z",
    }
    return service


@pytest.fixture
def notes_vm():
    """NotesViewModel básico."""
    vm = NotesViewModel()
    vm.after_note_created = MagicMock()
    return vm


def test_add_note_with_authenticated_user_succeeds(
    mock_gateway_authenticated,
    mock_notes_service,
    notes_vm,
):
    """Teste: usuário autenticado consegue adicionar nota com sucesso.

    Cenário:
    - is_authenticated() retorna True
    - get_org_id() retorna org válido
    - get_user_email() retorna email válido
    - Nota é criada sem erros
    - Não mostra MessageBox "Não autenticado"
    """
    controller = NotesController(
        vm=notes_vm,
        gateway=mock_gateway_authenticated,
        notes_service=mock_notes_service,
    )

    # Chamar handle_add_note_click
    success, message = controller.handle_add_note_click("Texto da nota de teste")

    # Verificações
    assert success is True, "Deveria ter sucesso com usuário autenticado"
    assert message == "", f"Mensagem deveria estar vazia, mas contém: {message}"

    # Verificar que checagens foram chamadas
    mock_gateway_authenticated.is_authenticated.assert_called_once()
    mock_gateway_authenticated.is_online.assert_called_once()
    mock_gateway_authenticated.get_org_id.assert_called_once()
    mock_gateway_authenticated.get_user_email.assert_called_once()

    # Verificar que service foi chamado corretamente
    mock_notes_service.create_note.assert_called_once_with(
        org_id="org-test-123",
        author_email="user@test.com",
        body="Texto da nota de teste",
    )

    # Verificar que ViewModel foi atualizado
    notes_vm.after_note_created.assert_called_once()

    # Verificar que NÃO mostrou erro de autenticação
    mock_gateway_authenticated.show_error.assert_not_called()


def test_add_note_with_unauthenticated_user_blocks(
    mock_gateway_not_authenticated,
    mock_notes_service,
    notes_vm,
):
    """Teste: usuário NÃO autenticado é bloqueado corretamente.

    Cenário:
    - is_authenticated() retorna False
    - MessageBox "Não autenticado" é mostrado
    - Service NÃO é chamado
    """
    controller = NotesController(
        vm=notes_vm,
        gateway=mock_gateway_not_authenticated,
        notes_service=mock_notes_service,
    )

    # Chamar handle_add_note_click
    success, message = controller.handle_add_note_click("Texto da nota")

    # Verificações
    assert success is False, "Deveria falhar com usuário não autenticado"
    assert message == "Não autenticado"

    # Verificar que checagem foi chamada
    mock_gateway_not_authenticated.is_authenticated.assert_called_once()

    # Verificar que show_error foi chamado com mensagem correta
    mock_gateway_not_authenticated.show_error.assert_called_once_with(
        "Não autenticado",
        "Você precisa estar autenticado para adicionar uma anotação.",
    )

    # Verificar que service NÃO foi chamado
    mock_notes_service.create_note.assert_not_called()

    # Verificar que ViewModel NÃO foi atualizado
    notes_vm.after_note_created.assert_not_called()


def test_add_note_with_missing_org_id_fails(
    mock_gateway_authenticated,
    mock_notes_service,
    notes_vm,
):
    """Teste: falha quando org_id não está disponível.

    Cenário:
    - is_authenticated() retorna True
    - get_org_id() retorna None
    - MessageBox de erro de contexto é mostrado
    """
    mock_gateway_authenticated.get_org_id.return_value = None

    controller = NotesController(
        vm=notes_vm,
        gateway=mock_gateway_authenticated,
        notes_service=mock_notes_service,
    )

    success, message = controller.handle_add_note_click("Texto da nota")

    assert success is False
    assert message == "Contexto inválido"

    # Verificar erro mostrado
    mock_gateway_authenticated.show_error.assert_called_once()
    args = mock_gateway_authenticated.show_error.call_args[0]
    assert args[0] == "Erro"
    assert "organização ou usuário" in args[1]

    # Service não deve ser chamado
    mock_notes_service.create_note.assert_not_called()


def test_add_note_with_missing_email_fails(
    mock_gateway_authenticated,
    mock_notes_service,
    notes_vm,
):
    """Teste: falha quando user_email não está disponível."""
    mock_gateway_authenticated.get_user_email.return_value = None

    controller = NotesController(
        vm=notes_vm,
        gateway=mock_gateway_authenticated,
        notes_service=mock_notes_service,
    )

    success, message = controller.handle_add_note_click("Texto da nota")

    assert success is False
    assert message == "Contexto inválido"

    mock_notes_service.create_note.assert_not_called()


def test_add_note_with_empty_text_fails(
    mock_gateway_authenticated,
    mock_notes_service,
    notes_vm,
):
    """Teste: texto vazio não permite criar nota."""
    controller = NotesController(
        vm=notes_vm,
        gateway=mock_gateway_authenticated,
        notes_service=mock_notes_service,
    )

    success, message = controller.handle_add_note_click("   ")  # Apenas espaços

    assert success is False
    assert message == "Texto vazio"

    # Não deve chamar is_authenticated nem service
    mock_gateway_authenticated.is_authenticated.assert_not_called()
    mock_notes_service.create_note.assert_not_called()


def test_add_note_with_service_exception_handles_gracefully(
    mock_gateway_authenticated,
    mock_notes_service,
    notes_vm,
):
    """Teste: exceção no service é tratada graciosamente."""
    mock_notes_service.create_note.side_effect = RuntimeError("Erro no Supabase")

    controller = NotesController(
        vm=notes_vm,
        gateway=mock_gateway_authenticated,
        notes_service=mock_notes_service,
    )

    success, message = controller.handle_add_note_click("Texto da nota")

    assert success is False
    assert "Erro no Supabase" in message

    # Verificar que show_error foi chamado
    mock_gateway_authenticated.show_error.assert_called_once()
    args = mock_gateway_authenticated.show_error.call_args[0]
    assert args[0] == "Erro"
    assert "Erro no Supabase" in args[1]


@patch("infra.supabase_client.get_supabase")
@patch("src.core.session.get_current_user")
def test_integration_hub_gateway_with_real_session(
    mock_get_current_user,
    mock_get_supabase,
):
    """Teste de integração: HubGatewayImpl com sessão mockada realista.

    Simula exatamente o cenário do bug:
    - get_current_user() retorna None (cache vazio)
    - get_supabase().auth.get_session() retorna sessão válida
    - HubGatewayImpl deve buscar org_id diretamente do Supabase
    """
    from src.modules.hub.views.hub_gateway_impl import HubGatewayImpl

    # Mock: get_current_user retorna None (cache não inicializado)
    mock_get_current_user.return_value = None

    # Mock: Supabase com sessão válida
    mock_session = MagicMock()
    mock_session.user.id = "user-123"
    mock_session.user.email = "test@example.com"

    mock_client = MagicMock()
    mock_client.auth.get_session.return_value = mock_session

    # Mock: memberships table retorna org_id
    mock_resp = MagicMock()
    mock_resp.data = [{"org_id": "org-456", "role": "owner"}]

    mock_table = MagicMock()
    mock_table.select.return_value.eq.return_value = mock_resp
    mock_client.table.return_value = mock_table

    mock_get_supabase.return_value = mock_client

    # Criar gateway
    mock_parent = MagicMock()
    gateway = HubGatewayImpl(mock_parent)

    # Testar is_authenticated
    assert gateway.is_authenticated() is True, "Deveria estar autenticado"

    # Testar get_user_email
    email = gateway.get_user_email()
    assert email == "test@example.com"

    # Testar get_org_id (deve buscar do Supabase quando cache está vazio)
    with patch("infra.supabase_client.exec_postgrest") as mock_exec:
        mock_exec.return_value = mock_resp
        org_id = gateway.get_org_id()
        assert org_id == "org-456", f"Esperava org-456, obteve {org_id}"


def test_notes_controller_integration_full_flow(
    mock_gateway_authenticated,
    mock_notes_service,
    notes_vm,
):
    """Teste de integração completo: fluxo end-to-end de adicionar nota.

    Este teste replica exatamente o fluxo do usuário:
    1. Usuário digita texto
    2. Clica em "Adicionar"
    3. Controller verifica autenticação
    4. Controller obtém org_id e email
    5. Controller chama service
    6. ViewModel é atualizado
    7. Retorna sucesso
    """
    controller = NotesController(
        vm=notes_vm,
        gateway=mock_gateway_authenticated,
        notes_service=mock_notes_service,
    )

    # Simular entrada do usuário
    user_input = "Esta é uma nota de teste para validar o fluxo completo"

    # Executar ação
    success, message = controller.handle_add_note_click(user_input)

    # Validação final
    assert success is True, "Fluxo completo deveria ter sucesso"
    assert message == "", "Não deveria ter mensagem de erro"

    # Verificar sequência de chamadas
    assert mock_gateway_authenticated.is_authenticated.called
    assert mock_gateway_authenticated.is_online.called
    assert mock_gateway_authenticated.get_org_id.called
    assert mock_gateway_authenticated.get_user_email.called
    assert mock_notes_service.create_note.called
    assert notes_vm.after_note_created.called

    # Verificar que não houve erros
    assert not mock_gateway_authenticated.show_error.called, "Não deveria ter mostrado nenhum erro"
