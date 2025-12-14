# -*- coding: utf-8 -*-
"""Testes unitários para HubNotesFacade (MF-31).

Foco:
- Testar que a facade delega corretamente para controllers e serviços
- Verificar operações CRUD de notas (add, edit, delete, toggle)
- Validar operações de rendering e polling
- Testar eventos realtime
"""

import pytest
from unittest.mock import MagicMock

from src.modules.hub.views.hub_notes_facade import HubNotesFacade


class TestHubNotesFacade:
    """Testes para HubNotesFacade (MF-23, MF-31)."""

    @pytest.fixture
    def mock_parent(self):
        """Mock do widget pai (HubScreen)."""
        parent = MagicMock()
        parent.notes_history = []
        return parent

    @pytest.fixture
    def mock_notes_controller(self):
        """Mock do NotesController."""
        controller = MagicMock()
        controller.handle_add_note_click = MagicMock(return_value=(True, ""))
        controller.handle_edit_note_click = MagicMock(return_value=(True, None))
        controller.handle_delete_note_click = MagicMock(return_value=(True, None))
        controller.handle_toggle_pin = MagicMock(return_value=(True, None))
        controller.handle_toggle_done = MagicMock(return_value=(True, None))
        return controller

    @pytest.fixture
    def mock_hub_controller(self):
        """Mock do HubScreenController."""
        return MagicMock()

    @pytest.fixture
    def mock_notes_renderer(self):
        """Mock do HubNotesRenderer."""
        renderer = MagicMock()
        renderer.render_notes = MagicMock()
        return renderer

    @pytest.fixture
    def mock_polling_service(self):
        """Mock do HubPollingService."""
        return MagicMock()

    @pytest.fixture
    def mock_state_manager(self):
        """Mock do HubStateManager."""
        return MagicMock()

    @pytest.fixture
    def mock_callbacks(self):
        """Mock de callbacks necessários."""
        return {
            "get_org_id": MagicMock(return_value="test-org-123"),
            "get_email": MagicMock(return_value="test@example.com"),
        }

    @pytest.fixture
    def facade(
        self,
        mock_parent,
        mock_notes_controller,
        mock_hub_controller,
        mock_notes_renderer,
        mock_polling_service,
        mock_state_manager,
        mock_callbacks,
    ):
        """Facade sem debug logger."""
        return HubNotesFacade(
            parent=mock_parent,
            notes_controller=mock_notes_controller,
            hub_controller=mock_hub_controller,
            notes_renderer=mock_notes_renderer,
            polling_service=mock_polling_service,
            state_manager=mock_state_manager,
            get_org_id=mock_callbacks["get_org_id"],
            get_email=mock_callbacks["get_email"],
            debug_logger=None,
        )

    # ==========================================================================
    # TESTES DE OPERAÇÕES DE NOTAS (CRUD)
    # ==========================================================================

    def test_on_add_note_delega_para_controller(self, facade, mock_notes_controller):
        """Testa que on_add_note delega para NotesController."""
        success, message = facade.on_add_note("Texto da nota teste")

        mock_notes_controller.handle_add_note_click.assert_called_once_with("Texto da nota teste")
        assert success is True
        assert message == ""

    def test_on_add_note_retorna_falha_quando_controller_falha(self, facade, mock_notes_controller):
        """Testa que on_add_note retorna falha quando controller falha."""
        mock_notes_controller.handle_add_note_click.return_value = (False, "Erro teste")

        success, message = facade.on_add_note("Texto teste")

        assert success is False
        assert message == "Erro teste"

    def test_on_add_note_trata_excecao(self, facade, mock_notes_controller):
        """Testa que exceções em on_add_note são tratadas."""
        mock_notes_controller.handle_add_note_click.side_effect = Exception("Erro de teste")

        success, message = facade.on_add_note("Texto teste")

        assert success is False
        assert "Erro de teste" in message

    def test_on_edit_note_delega_para_controller(self, facade, mock_notes_controller):
        """Testa que on_edit_note delega para NotesController."""
        facade.on_edit_note("note-123")

        mock_notes_controller.handle_edit_note_click.assert_called_once_with("note-123")

    def test_on_delete_note_delega_para_controller(self, facade, mock_notes_controller):
        """Testa que on_delete_note delega para NotesController."""
        facade.on_delete_note("note-123")

        mock_notes_controller.handle_delete_note_click.assert_called_once_with("note-123")

    def test_on_toggle_pin_delega_para_controller(self, facade, mock_notes_controller):
        """Testa que on_toggle_pin delega para NotesController."""
        facade.on_toggle_pin("note-123")

        mock_notes_controller.handle_toggle_pin.assert_called_once_with("note-123")

    def test_on_toggle_done_delega_para_controller(self, facade, mock_notes_controller):
        """Testa que on_toggle_done delega para NotesController."""
        facade.on_toggle_done("note-123")

        mock_notes_controller.handle_toggle_done.assert_called_once_with("note-123")

    # ==========================================================================
    # TESTES DE RENDERIZAÇÃO
    # ==========================================================================

    def test_render_notes_delega_para_renderer(self, facade, mock_notes_renderer, mock_parent):
        """Testa que render_notes delega para HubNotesRenderer."""
        notes_list = [{"id": "1", "text": "Nota 1"}, {"id": "2", "text": "Nota 2"}]

        facade.render_notes(notes_list, force=False)

        mock_notes_renderer.render_notes.assert_called_once_with(notes=notes_list, force=False, hub_screen=mock_parent)

    def test_render_notes_com_force_true(self, facade, mock_notes_renderer, mock_parent):
        """Testa que render_notes passa force=True corretamente."""
        notes_list = [{"id": "1", "text": "Nota 1"}]

        facade.render_notes(notes_list, force=True)

        mock_notes_renderer.render_notes.assert_called_once_with(notes=notes_list, force=True, hub_screen=mock_parent)

    def test_update_notes_ui_state_delega_para_renderer(self, facade, mock_notes_renderer, mock_parent):
        """Testa que update_notes_ui_state delega para renderer."""
        # Mockar atributos necessários do parent
        mock_parent.btn_add_note = MagicMock()
        mock_parent.new_note = MagicMock()

        facade.update_notes_ui_state()

        mock_notes_renderer.update_notes_ui_state.assert_called_once()

    # ==========================================================================
    # TESTES DE POLLING
    # ==========================================================================

    def test_start_notes_polling_delega_para_polling_service(self, facade, mock_polling_service):
        """Testa que start_notes_polling delega para polling_service."""
        facade.start_notes_polling()

        mock_polling_service.start_notes_polling.assert_called_once_with()

    def test_poll_notes_if_needed_delega_para_hub_controller(self, facade, mock_hub_controller):
        """Testa que poll_notes_if_needed delega para hub_controller."""
        facade.poll_notes_if_needed()

        mock_hub_controller.refresh_notes.assert_called_once_with(force=False)

    def test_poll_notes_impl_sem_force_delega_para_polling_service(self, facade, mock_polling_service):
        """Testa que poll_notes_impl delega para polling_service."""
        facade.poll_notes_impl(force=False)

        mock_polling_service.poll_notes.assert_called_once_with(force=False)

    def test_poll_notes_impl_com_force_delega_para_polling_service(self, facade, mock_polling_service):
        """Testa que poll_notes_impl com force=True delega corretamente."""
        facade.poll_notes_impl(force=True)

        mock_polling_service.poll_notes.assert_called_once_with(force=True)

    def test_refresh_notes_async_delega_para_hub_controller(self, facade, mock_hub_controller):
        """Testa que refresh_notes_async delega para hub_controller."""
        facade.refresh_notes_async(force=False)

        mock_hub_controller.refresh_notes.assert_called_once_with(force=False)

    # ==========================================================================
    # TESTES DE REALTIME
    # ==========================================================================

    def test_on_realtime_note_delega_para_hub_controller(self, facade, mock_hub_controller):
        """Testa que on_realtime_note delega para hub_controller."""
        row_data = {"id": "note-123", "text": "Nova nota", "type": "INSERT"}

        facade.on_realtime_note(row_data)

        mock_hub_controller.on_realtime_note.assert_called_once_with(row_data)

    def test_append_note_incremental_delega_para_hub_controller(self, facade, mock_hub_controller):
        """Testa que append_note_incremental delega para hub_controller."""
        row_data = {"id": "note-123", "text": "Nova nota"}

        facade.append_note_incremental(row_data)

        mock_hub_controller._append_note_incremental.assert_called_once_with(row_data)

    # ==========================================================================
    # TESTES DE DEBUG
    # ==========================================================================

    def test_collect_notes_debug_retorna_dict(self, facade):
        """Testa que collect_notes_debug retorna um dict com informações."""
        debug_info = facade.collect_notes_debug()

        assert isinstance(debug_info, dict)
        # Verifica que contém as chaves esperadas (vindas de collect_full_notes_debug)
        assert "org_id" in debug_info

    def test_operacoes_com_debug_logger(
        self,
        mock_parent,
        mock_notes_controller,
        mock_hub_controller,
        mock_notes_renderer,
        mock_polling_service,
        mock_state_manager,
        mock_callbacks,
    ):
        """Testa que operações fazem log quando debug está habilitado."""
        mock_debug_logger = MagicMock()
        facade_with_debug = HubNotesFacade(
            parent=mock_parent,
            notes_controller=mock_notes_controller,
            hub_controller=mock_hub_controller,
            notes_renderer=mock_notes_renderer,
            polling_service=mock_polling_service,
            state_manager=mock_state_manager,
            get_org_id=mock_callbacks["get_org_id"],
            get_email=mock_callbacks["get_email"],
            debug_logger=mock_debug_logger,
        )

        facade_with_debug.on_add_note("Texto teste")

        # Verifica que logger foi chamado
        mock_debug_logger.assert_called_once()
        call_msg = mock_debug_logger.call_args[0][0]
        assert "on_add_note" in call_msg

    # ==========================================================================
    # TESTES DE RETRY APÓS ERRO
    # ==========================================================================

    def test_retry_after_table_missing_delega_para_hub_controller(self, facade, mock_hub_controller):
        """Testa que retry_after_table_missing delega para hub_controller."""
        facade.retry_after_table_missing()

        mock_hub_controller.refresh_notes.assert_called_once_with(force=True)

    # ==========================================================================
    # TESTES DE INTEGRAÇÃO ENTRE OPERAÇÕES
    # ==========================================================================

    def test_fluxo_completo_add_note_com_sucesso(self, facade, mock_notes_controller, mock_notes_renderer):
        """Testa fluxo completo de adicionar nota com sucesso."""
        mock_notes_controller.handle_add_note_click.return_value = (True, "")

        success, message = facade.on_add_note("Nova nota importante")

        assert success is True
        assert message == ""
        mock_notes_controller.handle_add_note_click.assert_called_once()

    def test_fluxo_render_atualiza_ui(self, facade, mock_notes_renderer, mock_parent):
        """Testa fluxo de render seguido de update de UI."""
        notes = [{"id": "1", "text": "Nota"}]
        # Mockar atributos necessários do parent
        mock_parent.btn_add_note = MagicMock()
        mock_parent.new_note = MagicMock()

        facade.render_notes(notes)
        facade.update_notes_ui_state()

        mock_notes_renderer.render_notes.assert_called_once_with(notes=notes, force=False, hub_screen=mock_parent)
        mock_notes_renderer.update_notes_ui_state.assert_called_once()
