# -*- coding: utf-8 -*-
"""Testes headless para NotesController.

Testa toda a lógica de ações de usuário sem dependências de Tkinter:
- handle_add_note_click (validação, criação)
- handle_edit_note_click (edição)
- handle_delete_note_click (confirmação, deleção)
- handle_toggle_pin / handle_toggle_done
- Interação com NotesGatewayProtocol
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.modules.hub.controllers.notes_controller import NotesController
from src.modules.hub.viewmodels.notes_vm import NotesViewModel, NotesViewState


class FakeNotesGateway:
    """Fake implementation of NotesGatewayProtocol for testing."""

    def __init__(self):
        self.shown_errors = []
        self.shown_infos = []
        self.shown_editors = []
        self.delete_confirmations = []
        self.org_id = "test_org"
        self.user_email = "test@example.com"
        self.is_auth = True
        self.is_conn = True

    def show_note_editor(self, note_data=None):
        """Mock show_note_editor."""
        self.shown_editors.append(note_data)
        # Return edited data (simulating user input)
        if note_data:
            return {**note_data, "body": "Edited body"}
        return {"body": "New note", "id": "new123"}

    def confirm_delete_note(self, note_data):
        """Mock confirm_delete_note."""
        self.delete_confirmations.append(note_data)
        return True  # Default: user confirms

    def show_error(self, title, message):
        """Mock show_error."""
        self.shown_errors.append({"title": title, "message": message})

    def show_info(self, title, message):
        """Mock show_info."""
        self.shown_infos.append({"title": title, "message": message})

    def get_org_id(self):
        """Mock get_org_id."""
        return self.org_id

    def get_user_email(self):
        """Mock get_user_email."""
        return self.user_email

    def is_authenticated(self):
        """Mock is_authenticated."""
        return self.is_auth

    def is_online(self):
        """Mock is_online."""
        return self.is_conn

    def reload_notes(self):
        """Mock reload_notes."""
        # Apenas registra que foi chamado, não faz nada nos testes
        pass

    def reload_dashboard(self):
        """Mock reload_dashboard."""
        # Apenas registra que foi chamado, não faz nada nos testes
        pass


class FakeNotificationsService:
    """Fake implementation of NotificationsService for testing."""

    def __init__(self):
        self.published_notifications = []
        # Mapa de nomes para teste (simular RC_INITIALS_MAP)
        self._names_map = {
            "test@example.com": "Testador",
            "farmacajr@gmail.com": "Junior",
        }

    def publish(self, module, event, message, **kwargs):
        """Mock publish method."""
        self.published_notifications.append({"module": module, "event": event, "message": message, **kwargs})
        return True

    def resolve_display_name(self, email):
        """Mock resolve_display_name method."""
        if not email:
            return "?"
        email_lower = email.lower()
        if email_lower in self._names_map:
            return self._names_map[email_lower]
        # Fallback: capitalizar prefixo do email
        return email.split("@")[0].capitalize()


@pytest.fixture
def fake_gateway():
    """Fake gateway for testing."""
    return FakeNotesGateway()


@pytest.fixture
def mock_notes_service():
    """Mock NotesService."""
    service = MagicMock()
    # Mock list_notes para retornar notas de exemplo
    service.list_notes.return_value = [
        {
            "id": "note1",
            "body": "First note",
            "created_at": "2024-01-01T10:00:00Z",
            "author_email": "test@example.com",  # Mesmo email do gateway
        },
        {
            "id": "note2",
            "body": "Second note",
            "created_at": "2024-01-02T11:00:00Z",
            "author_email": "test@example.com",  # Mesmo email do gateway
        },
    ]
    # Mock create_note para retornar nova nota
    service.create_note.return_value = {
        "id": "new_note_id",
        "body": "New note",
        "created_at": "2024-01-01T10:00:00Z",
        "author_email": "test@example.com",
    }
    # Mock update_note para retornar nota atualizada
    service.update_note.return_value = {
        "id": "note1",
        "body": "Updated body",
        "created_at": "2024-01-01T10:00:00Z",
        "author_email": "test@example.com",
    }
    return service


@pytest.fixture
def notes_vm_with_data(mock_notes_service):
    """NotesViewModel with sample data."""
    vm = NotesViewModel(service=mock_notes_service)
    # Carregar notas para popular o estado
    vm.load(org_id="test_org")
    return vm


@pytest.fixture
def controller(notes_vm_with_data, fake_gateway, mock_notes_service):
    """NotesController instance for testing."""
    return NotesController(
        vm=notes_vm_with_data,
        gateway=fake_gateway,
        notes_service=mock_notes_service,
    )


class TestNotesControllerAddNote:
    """Testes para handle_add_note_click."""

    def test_add_note_success(self, controller, fake_gateway, mock_notes_service):
        """Deve adicionar nota com sucesso."""
        success, message = controller.handle_add_note_click("Nova anotação")

        assert success is True
        assert message == ""
        mock_notes_service.create_note.assert_called_once_with(
            org_id="test_org",
            author_email="test@example.com",
            body="Nova anotação",
        )

    def test_add_note_with_notification(self, notes_vm_with_data, fake_gateway, mock_notes_service):
        """Deve adicionar nota e publicar notificação com nome resolvido e request_id."""
        # Criar fake notifications service
        fake_notifications = FakeNotificationsService()

        # Criar controller com notifications_service
        controller = NotesController(
            vm=notes_vm_with_data,
            gateway=fake_gateway,
            notes_service=mock_notes_service,
            notifications_service=fake_notifications,
        )

        # Adicionar nota
        success, message = controller.handle_add_note_click("Nova anotação compartilhada")

        # Validar criação da nota
        assert success is True
        assert message == ""

        # Validar notificação
        assert len(fake_notifications.published_notifications) == 1
        notification = fake_notifications.published_notifications[0]
        assert notification["module"] == "hub_notes"
        assert notification["event"] == "created"
        assert "Anotações" in notification["message"]
        # Deve usar nome resolvido ("Testador") e não email
        assert "Testador" in notification["message"]
        assert "test@example.com" not in notification["message"]
        assert "Nova anotação compartilhada" in notification["message"]

        # Validar request_id para dedupe
        assert "request_id" in notification
        assert notification["request_id"] == "hub_notes_created:new_note_id"

    def test_add_note_notification_failure_does_not_break_creation(
        self, notes_vm_with_data, fake_gateway, mock_notes_service
    ):
        """Deve criar nota mesmo se notificação falhar."""
        # Criar fake notifications service que falha
        fake_notifications = FakeNotificationsService()
        fake_notifications.publish = lambda *args, **kwargs: (_ for _ in ()).throw(Exception("Notification failed"))

        # Criar controller com notifications_service
        controller = NotesController(
            vm=notes_vm_with_data,
            gateway=fake_gateway,
            notes_service=mock_notes_service,
            notifications_service=fake_notifications,
        )

        # Adicionar nota (não deve falhar)
        success, message = controller.handle_add_note_click("Nota com notificação falhando")

        # Validar que nota foi criada com sucesso
        assert success is True
        assert message == ""
        mock_notes_service.create_note.assert_called_once()

    def test_add_note_long_text_preview(self, notes_vm_with_data, fake_gateway, mock_notes_service):
        """Deve truncar preview em notificação se texto for muito longo."""
        fake_notifications = FakeNotificationsService()

        controller = NotesController(
            vm=notes_vm_with_data,
            gateway=fake_gateway,
            notes_service=mock_notes_service,
            notifications_service=fake_notifications,
        )

        # Texto muito longo
        long_text = "A" * 150

        success, message = controller.handle_add_note_click(long_text)

        assert success is True
        notification = fake_notifications.published_notifications[0]
        # Mensagem deve conter preview truncado (117 chars + "...")
        preview_in_message = notification["message"].split(": ", 1)[1]
        assert len(preview_in_message) <= 120
        assert preview_in_message.endswith("...")

    def test_add_note_empty_text(self, controller, fake_gateway):
        """Deve rejeitar texto vazio."""
        success, message = controller.handle_add_note_click("   ")

        assert success is False
        assert message == "Texto vazio"

    def test_add_note_not_authenticated(self, controller, fake_gateway):
        """Deve rejeitar se não autenticado."""
        fake_gateway.is_auth = False

        success, message = controller.handle_add_note_click("Nota")

        assert success is False
        assert message == "Não autenticado"
        assert len(fake_gateway.shown_errors) == 1
        assert "autenticado" in fake_gateway.shown_errors[0]["message"].lower()

    def test_add_note_offline(self, controller, fake_gateway):
        """Deve rejeitar se offline."""
        fake_gateway.is_conn = False

        success, message = controller.handle_add_note_click("Nota")

        assert success is False
        assert message == "Sem conexão"
        assert len(fake_gateway.shown_errors) == 1

    def test_add_note_no_org_id(self, controller, fake_gateway):
        """Deve rejeitar se não há org_id."""
        fake_gateway.org_id = None

        success, message = controller.handle_add_note_click("Nota")

        assert success is False
        assert "Contexto inválido" in message

    def test_add_note_service_error(self, controller, mock_notes_service, fake_gateway):
        """Deve tratar erros do service."""
        mock_notes_service.create_note.side_effect = Exception("Database error")

        success, message = controller.handle_add_note_click("Nota")

        assert success is False
        assert "Database error" in message
        assert len(fake_gateway.shown_errors) == 1


class TestNotesControllerEditNote:
    """Testes para handle_edit_note_click."""

    def test_edit_note_success(self, controller, fake_gateway, mock_notes_service):
        """Deve editar nota com sucesso."""
        success, message = controller.handle_edit_note_click("note1")

        assert success is True
        assert message == ""
        # Verificar que show_note_editor foi chamado com nota correta
        assert len(fake_gateway.shown_editors) == 1
        assert fake_gateway.shown_editors[0]["id"] == "note1"
        # Verificar que service.update_note foi chamado
        mock_notes_service.update_note.assert_called_once()

    def test_edit_note_not_found(self, controller, fake_gateway):
        """Deve rejeitar se nota não encontrada."""
        success, message = controller.handle_edit_note_click("note_inexistente")

        assert success is False
        assert "Nota não encontrada" in message
        assert len(fake_gateway.shown_errors) == 1

    def test_edit_note_cancelled(self, controller, fake_gateway, mock_notes_service):
        """Deve tratar cancelamento do editor."""
        # Simular cancelamento (editor retorna None)
        fake_gateway.shown_editors = []

        def return_none(note_data=None):
            fake_gateway.shown_editors.append(note_data)
            return None

        fake_gateway.show_note_editor = return_none

        success, message = controller.handle_edit_note_click("note1")

        assert success is False
        assert message == "Cancelado"
        # Service não deve ser chamado
        mock_notes_service.update_note.assert_not_called()


class TestNotesControllerDeleteNote:
    """Testes para handle_delete_note_click."""

    def test_delete_note_success(self, controller, fake_gateway, mock_notes_service):
        """Deve fazer soft delete da nota (update body para __RC_DELETED__)."""
        success, message = controller.handle_delete_note_click("note1")

        assert success is True
        assert message == ""
        # Verificar que confirmação foi solicitada
        assert len(fake_gateway.delete_confirmations) == 1
        # Verificar que service.update_note foi chamado com body="__RC_DELETED__"
        mock_notes_service.update_note.assert_called_once_with(
            note_id="note1",
            body="__RC_DELETED__",
        )
        # Verificar que delete_note NÃO foi chamado
        mock_notes_service.delete_note.assert_not_called()

    def test_delete_note_not_found(self, controller, fake_gateway):
        """Deve rejeitar se nota não encontrada."""
        success, message = controller.handle_delete_note_click("note_inexistente")

        assert success is False
        assert "Nota não encontrada" in message

    def test_delete_note_cancelled(self, controller, fake_gateway, mock_notes_service):
        """Deve tratar cancelamento da confirmação."""
        # Simular cancelamento (confirmação retorna False)
        fake_gateway.delete_confirmations = []

        def return_false(note_data):
            fake_gateway.delete_confirmations.append(note_data)
            return False

        fake_gateway.confirm_delete_note = return_false

        success, message = controller.handle_delete_note_click("note1")

        assert success is False
        assert message == "Cancelado"
        # Service não deve ser chamado
        mock_notes_service.update_note.assert_not_called()
        mock_notes_service.delete_note.assert_not_called()


class TestNotesControllerToggleActions:
    """Testes para handle_toggle_pin e handle_toggle_done (MF-5)."""

    def test_toggle_pin_success_pin(self, controller, mock_notes_service):
        """Deve fixar nota com sucesso."""
        # Mock do update_note retornando nota com is_pinned=True
        mock_notes_service.update_note.return_value = {
            "id": "note1",
            "body": "First note",
            "created_at": "2024-01-01T10:00:00Z",
            "author_email": "user@example.com",
            "is_pinned": True,
            "is_done": False,
        }

        success, message = controller.handle_toggle_pin("note1")

        assert success is True
        assert message == ""
        # Service deve ter sido chamado com is_pinned=True (nota não estava fixada)
        mock_notes_service.update_note.assert_called_once()
        call_kwargs = mock_notes_service.update_note.call_args[1]
        assert call_kwargs["note_id"] == "note1"
        assert call_kwargs["is_pinned"] is True

    def test_toggle_pin_success_unpin(self, notes_vm_with_data, fake_gateway, mock_notes_service):
        """Deve desfixar nota fixada com sucesso."""
        # Adicionar nota fixada ao estado
        pinned_note = {
            "id": "note_pinned",
            "body": "Pinned note",
            "created_at": "2024-01-03T10:00:00Z",
            "author_email": "user@example.com",
            "is_pinned": True,
            "is_done": False,
        }
        notes_vm_with_data._state.notes.append(notes_vm_with_data._make_note_item(pinned_note))

        controller = NotesController(
            vm=notes_vm_with_data,
            gateway=fake_gateway,
            notes_service=mock_notes_service,
        )

        # Mock do update_note retornando nota com is_pinned=False
        mock_notes_service.update_note.return_value = {
            **pinned_note,
            "is_pinned": False,
        }

        success, message = controller.handle_toggle_pin("note_pinned")

        assert success is True
        assert message == ""
        # Service deve ter sido chamado com is_pinned=False
        call_kwargs = mock_notes_service.update_note.call_args[1]
        assert call_kwargs["is_pinned"] is False

    def test_toggle_pin_note_not_found(self, controller, fake_gateway):
        """Deve retornar erro se nota não encontrada."""
        success, message = controller.handle_toggle_pin("nonexistent_note")

        assert success is False
        assert "Nota não encontrada" in message
        assert len(fake_gateway.shown_errors) == 1

    def test_toggle_pin_service_error(self, controller, mock_notes_service, fake_gateway):
        """Deve tratar erros do service."""
        mock_notes_service.update_note.side_effect = Exception("Update error")

        success, message = controller.handle_toggle_pin("note1")

        assert success is False
        assert "Update error" in message
        assert len(fake_gateway.shown_errors) == 1

    def test_toggle_done_success_mark_done(self, controller, mock_notes_service):
        """Deve marcar nota como concluída com sucesso."""
        mock_notes_service.update_note.return_value = {
            "id": "note1",
            "body": "First note",
            "created_at": "2024-01-01T10:00:00Z",
            "author_email": "user@example.com",
            "is_pinned": False,
            "is_done": True,
        }

        success, message = controller.handle_toggle_done("note1")

        assert success is True
        assert message == ""
        call_kwargs = mock_notes_service.update_note.call_args[1]
        assert call_kwargs["is_done"] is True

    def test_toggle_done_success_mark_undone(self, notes_vm_with_data, fake_gateway, mock_notes_service):
        """Deve desmarcar nota concluída."""
        # Adicionar nota concluída ao estado
        done_note = {
            "id": "note_done",
            "body": "Done note",
            "created_at": "2024-01-03T10:00:00Z",
            "author_email": "user@example.com",
            "is_pinned": False,
            "is_done": True,
        }
        notes_vm_with_data._state.notes.append(notes_vm_with_data._make_note_item(done_note))

        controller = NotesController(
            vm=notes_vm_with_data,
            gateway=fake_gateway,
            notes_service=mock_notes_service,
        )

        mock_notes_service.update_note.return_value = {
            **done_note,
            "is_done": False,
        }

        success, message = controller.handle_toggle_done("note_done")

        assert success is True
        call_kwargs = mock_notes_service.update_note.call_args[1]
        assert call_kwargs["is_done"] is False

    def test_toggle_done_note_not_found(self, controller, fake_gateway):
        """Deve retornar erro se nota não encontrada."""
        success, message = controller.handle_toggle_done("nonexistent_note")

        assert success is False
        assert "Nota não encontrada" in message

    def test_toggle_done_service_error(self, controller, mock_notes_service, fake_gateway):
        """Deve tratar erros do service."""
        mock_notes_service.update_note.side_effect = Exception("Service error")

        success, message = controller.handle_toggle_done("note1")

        assert success is False
        assert "Service error" in message


class TestNotesControllerLoadNotes:
    """Testes para handle_load_notes."""

    def test_load_notes_success(self, controller, fake_gateway, mock_notes_service):
        """Deve carregar notas via controller."""
        sample_notes = [
            {
                "id": "note3",
                "body": "Third note",
                "created_at": "2024-01-03T12:00:00Z",
                "author_email": "user@example.com",
            }
        ]
        mock_notes_service.list_notes.return_value = sample_notes

        state = controller.handle_load_notes("test_org", author_names_cache={"user@example.com": "User"})

        assert isinstance(state, NotesViewState)
        assert len(state.notes) == 1
        assert state.notes[0].id == "note3"

    def test_load_notes_handles_error(self, controller, fake_gateway, mock_notes_service):
        """Deve tratar erros no load."""
        mock_notes_service.list_notes.side_effect = Exception("Load error")

        state = controller.handle_load_notes("test_org")

        # Deve retornar estado com error_message (ViewModel captura exceção)
        assert isinstance(state, NotesViewState)
        assert state.error_message is not None
        assert "Load error" in state.error_message
        assert not state.is_loading
