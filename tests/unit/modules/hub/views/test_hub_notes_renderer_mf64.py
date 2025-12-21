# -*- coding: utf-8 -*-
"""MF-64: Testes headless para hub_notes_renderer.py.

Testa HubNotesRenderer com mocks, sem dependências reais.
Meta: 100% coverage (statements + branches).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


# =============================================================================
# FAKES HEADLESS
# =============================================================================


class FakeButton:
    """Botão fake para testes headless."""

    def __init__(self) -> None:
        self.configure_calls: list[dict[str, Any]] = []

    def configure(self, **kwargs: Any) -> None:
        """Registra chamada de configure."""
        self.configure_calls.append(kwargs)


class FakeText:
    """Campo de texto fake para testes headless."""

    def __init__(self) -> None:
        self.configure_calls: list[dict[str, Any]] = []
        self.delete_calls: list[tuple[str, str]] = []
        self.insert_calls: list[tuple[str, str]] = []
        self.content: str = ""

    def configure(self, **kwargs: Any) -> None:
        """Registra chamada de configure."""
        self.configure_calls.append(kwargs)

    def delete(self, start: str, end: str) -> None:
        """Registra chamada de delete."""
        self.delete_calls.append((start, end))
        self.content = ""

    def insert(self, position: str, text: str) -> None:
        """Registra chamada de insert."""
        self.insert_calls.append((position, text))
        self.content = text


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_notes_view() -> MagicMock:
    """Mock do HubNotesView."""
    return MagicMock()


@pytest.fixture
def mock_state() -> SimpleNamespace:
    """Estado mock com campos necessários."""
    return SimpleNamespace(
        author_tags={"user@example.com": "tag-1"},
        author_cache={"user@example.com": "John Doe"},
    )


@pytest.fixture
def mock_callbacks(mock_notes_view: MagicMock, mock_state: SimpleNamespace) -> MagicMock:
    """Callbacks mock."""
    callbacks = MagicMock()
    callbacks.get_notes_view.return_value = mock_notes_view
    callbacks.get_state.return_value = mock_state
    callbacks.get_debug_logger.return_value = None
    return callbacks


@pytest.fixture
def renderer(mock_callbacks: MagicMock) -> Any:
    """Renderer com callbacks mock."""
    from src.modules.hub.views.hub_notes_renderer import HubNotesRenderer

    return HubNotesRenderer(callbacks=mock_callbacks)


# =============================================================================
# TEST: __init__
# =============================================================================


class TestInit:
    """Testes de inicialização."""

    def test_init_stores_callbacks(self, mock_callbacks: MagicMock) -> None:
        """__init__ armazena callbacks corretamente."""
        from src.modules.hub.views.hub_notes_renderer import HubNotesRenderer

        renderer = HubNotesRenderer(callbacks=mock_callbacks)

        assert renderer._callbacks is mock_callbacks
        assert renderer._logger is not None

    def test_repr(self, renderer: Any) -> None:
        """__repr__ retorna string esperada."""
        assert repr(renderer) == "<HubNotesRenderer>"


# =============================================================================
# TEST: render_notes (happy path)
# =============================================================================


class TestRenderNotesHappyPath:
    """Testes de render_notes - happy path."""

    def test_render_notes_calls_notes_view(
        self,
        renderer: Any,
        mock_notes_view: MagicMock,
        mock_state: SimpleNamespace,
    ) -> None:
        """render_notes() delega para notes_view.render_notes()."""
        notes = [{"id": 1, "text": "Test note"}]

        renderer.render_notes(notes)

        mock_notes_view.render_notes.assert_called_once()
        call_args = mock_notes_view.render_notes.call_args
        assert call_args[0][0] == notes  # Primeiro argumento posicional
        assert call_args[1]["force"] is False
        assert call_args[1]["author_tags"] == mock_state.author_tags
        assert call_args[1]["author_names_cache"] == mock_state.author_cache

    def test_render_notes_with_force_true(
        self,
        renderer: Any,
        mock_notes_view: MagicMock,
    ) -> None:
        """render_notes(force=True) passa force=True para notes_view."""
        notes = [{"id": 1, "text": "Test note"}]

        renderer.render_notes(notes, force=True)

        call_args = mock_notes_view.render_notes.call_args
        assert call_args[1]["force"] is True

    def test_render_notes_with_hub_screen(
        self,
        renderer: Any,
        mock_notes_view: MagicMock,
    ) -> None:
        """render_notes() passa hub_screen para notes_view."""
        notes = [{"id": 1, "text": "Test note"}]
        hub_screen_mock = MagicMock()

        renderer.render_notes(notes, hub_screen=hub_screen_mock)

        call_args = mock_notes_view.render_notes.call_args
        assert call_args[1]["hub_screen"] is hub_screen_mock

    def test_render_notes_with_debug_logger(
        self,
        renderer: Any,
        mock_notes_view: MagicMock,
        mock_callbacks: MagicMock,
    ) -> None:
        """render_notes() passa debug_logger quando disponível."""
        debug_logger = MagicMock()
        mock_callbacks.get_debug_logger.return_value = debug_logger
        notes = [{"id": 1, "text": "Test note"}]

        renderer.render_notes(notes)

        call_args = mock_notes_view.render_notes.call_args
        assert call_args[1]["debug_logger"] is debug_logger

    def test_render_notes_with_empty_list(
        self,
        renderer: Any,
        mock_notes_view: MagicMock,
    ) -> None:
        """render_notes([]) chama notes_view com lista vazia."""
        renderer.render_notes([])

        call_args = mock_notes_view.render_notes.call_args
        assert call_args[0][0] == []

    def test_render_notes_with_none_list(
        self,
        renderer: Any,
        mock_notes_view: MagicMock,
    ) -> None:
        """render_notes(None) converte para lista vazia."""
        renderer.render_notes(None)

        call_args = mock_notes_view.render_notes.call_args
        assert call_args[0][0] == []

    def test_render_notes_creates_author_tags_if_none(
        self,
        renderer: Any,
        mock_state: SimpleNamespace,
        mock_notes_view: MagicMock,
    ) -> None:
        """render_notes() cria author_tags={} se None."""
        mock_state.author_tags = None
        notes = [{"id": 1, "text": "Test note"}]

        renderer.render_notes(notes)

        # Verifica que author_tags foi criado como dict vazio
        assert mock_state.author_tags == {}
        # Verifica que foi passado para notes_view
        call_args = mock_notes_view.render_notes.call_args
        assert call_args[1]["author_tags"] == {}

    def test_render_notes_handles_none_author_cache(
        self,
        renderer: Any,
        mock_state: SimpleNamespace,
        mock_notes_view: MagicMock,
    ) -> None:
        """render_notes() converte author_cache None para {}."""
        mock_state.author_cache = None
        notes = [{"id": 1, "text": "Test note"}]

        renderer.render_notes(notes)

        call_args = mock_notes_view.render_notes.call_args
        assert call_args[1]["author_names_cache"] == {}


# =============================================================================
# TEST: render_notes (notes_view None)
# =============================================================================


class TestRenderNotesViewNone:
    """Testes de render_notes quando notes_view é None."""

    def test_render_notes_with_none_view_logs_warning(
        self,
        renderer: Any,
        mock_callbacks: MagicMock,
    ) -> None:
        """render_notes() loga warning quando notes_view é None."""
        mock_callbacks.get_notes_view.return_value = None
        notes = [{"id": 1, "text": "Test note"}]

        with patch.object(renderer, "_logger") as mock_logger:
            renderer.render_notes(notes)

            mock_logger.warning.assert_called_once()
            call_args = str(mock_logger.warning.call_args)
            assert "notes_view" in call_args.lower() or "ausente" in call_args.lower()

    def test_render_notes_with_none_view_does_not_crash(
        self,
        renderer: Any,
        mock_callbacks: MagicMock,
    ) -> None:
        """render_notes() não explode quando notes_view é None."""
        mock_callbacks.get_notes_view.return_value = None
        notes = [{"id": 1, "text": "Test note"}]

        # Não deve lançar exceção
        renderer.render_notes(notes)


# =============================================================================
# TEST: render_notes (exceptions)
# =============================================================================


class TestRenderNotesExceptions:
    """Testes de render_notes com exceções."""

    def test_render_notes_catches_callback_exception(
        self,
        renderer: Any,
        mock_callbacks: MagicMock,
    ) -> None:
        """render_notes() captura exceção de get_state() e loga."""
        mock_callbacks.get_state.side_effect = RuntimeError("State error")
        notes = [{"id": 1, "text": "Test note"}]

        with patch.object(renderer, "_logger") as mock_logger:
            renderer.render_notes(notes)

            mock_logger.warning.assert_called_once()
            call_args = str(mock_logger.warning.call_args)
            assert "erro" in call_args.lower() or "callbacks" in call_args.lower()

    def test_render_notes_catches_get_notes_view_exception(
        self,
        renderer: Any,
        mock_callbacks: MagicMock,
    ) -> None:
        """render_notes() captura exceção de get_notes_view() e loga."""
        mock_callbacks.get_notes_view.side_effect = RuntimeError("View error")
        notes = [{"id": 1, "text": "Test note"}]

        with patch.object(renderer, "_logger") as mock_logger:
            renderer.render_notes(notes)

            mock_logger.warning.assert_called_once()

    def test_render_notes_catches_render_exception(
        self,
        renderer: Any,
        mock_notes_view: MagicMock,
    ) -> None:
        """render_notes() captura exceção de notes_view.render_notes()."""
        mock_notes_view.render_notes.side_effect = RuntimeError("Render error")
        notes = [{"id": 1, "text": "Test note"}]

        with patch.object(renderer, "_logger") as mock_logger:
            renderer.render_notes(notes)

            mock_logger.exception.assert_called_once()
            call_args = str(mock_logger.exception.call_args)
            assert "erro" in call_args.lower() or "renderizar" in call_args.lower()


# =============================================================================
# TEST: render_loading
# =============================================================================


class TestRenderLoading:
    """Testes de render_loading."""

    def test_render_loading_logs_debug(self, renderer: Any) -> None:
        """render_loading() loga debug."""
        with patch.object(renderer, "_logger") as mock_logger:
            renderer.render_loading()

            mock_logger.debug.assert_called_once()
            call_args = str(mock_logger.debug.call_args)
            assert "loading" in call_args.lower() or "placeholder" in call_args.lower()

    def test_render_loading_does_not_crash(self, renderer: Any) -> None:
        """render_loading() não explode."""
        # Não deve lançar exceção
        renderer.render_loading()


# =============================================================================
# TEST: render_error
# =============================================================================


class TestRenderError:
    """Testes de render_error."""

    def test_render_error_logs_warning(self, renderer: Any) -> None:
        """render_error() loga warning com mensagem."""
        with patch.object(renderer, "_logger") as mock_logger:
            renderer.render_error("Test error message")

            mock_logger.warning.assert_called_once()
            call_args = str(mock_logger.warning.call_args)
            assert "test error message" in call_args.lower()

    def test_render_error_does_not_crash(self, renderer: Any) -> None:
        """render_error() não explode."""
        # Não deve lançar exceção
        renderer.render_error("Some error")


# =============================================================================
# TEST: render_empty
# =============================================================================


class TestRenderEmpty:
    """Testes de render_empty."""

    def test_render_empty_logs_debug(self, renderer: Any) -> None:
        """render_empty() loga debug."""
        with patch.object(renderer, "_logger") as mock_logger:
            renderer.render_empty()

            mock_logger.debug.assert_called_once()
            call_args = str(mock_logger.debug.call_args)
            assert "empty" in call_args.lower() or "vazia" in call_args.lower()

    def test_render_empty_does_not_crash(self, renderer: Any) -> None:
        """render_empty() não explode."""
        # Não deve lançar exceção
        renderer.render_empty()


# =============================================================================
# TEST: update_notes_ui_state
# =============================================================================


class TestUpdateNotesUiState:
    """Testes de update_notes_ui_state."""

    def test_update_ui_state_with_org_id_enables_button(self, renderer: Any) -> None:
        """update_notes_ui_state(has_org_id=True) habilita botão."""
        fake_btn = FakeButton()

        with patch("src.modules.hub.views.hub_screen_helpers.calculate_notes_ui_state") as mock_calc:
            mock_calc.return_value = {
                "button_enabled": True,
                "text_field_enabled": True,
                "placeholder_message": "",
            }

            renderer.update_notes_ui_state(
                has_org_id=True,
                btn_add_note=fake_btn,
                new_note_field=None,
            )

            # Verifica que botão foi configurado como "normal"
            assert len(fake_btn.configure_calls) == 1
            assert fake_btn.configure_calls[0]["state"] == "normal"

    def test_update_ui_state_without_org_id_disables_button(self, renderer: Any) -> None:
        """update_notes_ui_state(has_org_id=False) desabilita botão."""
        fake_btn = FakeButton()

        with patch("src.modules.hub.views.hub_screen_helpers.calculate_notes_ui_state") as mock_calc:
            mock_calc.return_value = {
                "button_enabled": False,
                "text_field_enabled": False,
                "placeholder_message": "Sem organização",
            }

            renderer.update_notes_ui_state(
                has_org_id=False,
                btn_add_note=fake_btn,
                new_note_field=None,
            )

            # Verifica que botão foi configurado como "disabled"
            assert len(fake_btn.configure_calls) == 1
            assert fake_btn.configure_calls[0]["state"] == "disabled"

    def test_update_ui_state_updates_text_field(self, renderer: Any) -> None:
        """update_notes_ui_state() atualiza campo de texto com placeholder."""
        fake_text = FakeText()

        with patch("src.modules.hub.views.hub_screen_helpers.calculate_notes_ui_state") as mock_calc:
            mock_calc.return_value = {
                "button_enabled": False,
                "text_field_enabled": False,
                "placeholder_message": "Selecione uma organização",
            }

            renderer.update_notes_ui_state(
                has_org_id=False,
                btn_add_note=None,
                new_note_field=fake_text,
            )

            # Verifica que campo foi manipulado corretamente
            # 1. configure(state="normal") para permitir edição
            # 2. delete("1.0", "end") para limpar
            # 3. insert("1.0", placeholder)
            # 4. configure(state="disabled")
            assert len(fake_text.configure_calls) == 2
            assert fake_text.configure_calls[0]["state"] == "normal"
            assert fake_text.configure_calls[1]["state"] == "disabled"

            assert len(fake_text.delete_calls) == 1
            assert fake_text.delete_calls[0] == ("1.0", "end")

            assert len(fake_text.insert_calls) == 1
            assert fake_text.insert_calls[0] == ("1.0", "Selecione uma organização")

    def test_update_ui_state_with_none_widgets(self, renderer: Any) -> None:
        """update_notes_ui_state() não explode com widgets None."""
        with patch("src.modules.hub.views.hub_screen_helpers.calculate_notes_ui_state") as mock_calc:
            mock_calc.return_value = {
                "button_enabled": True,
                "text_field_enabled": True,
                "placeholder_message": "",
            }

            # Não deve lançar exceção
            renderer.update_notes_ui_state(
                has_org_id=True,
                btn_add_note=None,
                new_note_field=None,
            )

    def test_update_ui_state_catches_button_configure_exception(self, renderer: Any) -> None:
        """update_notes_ui_state() captura exceção de btn.configure()."""
        fake_btn = FakeButton()
        # Força exceção em configure
        fake_btn.configure = MagicMock(side_effect=RuntimeError("Configure error"))

        with patch("src.modules.hub.views.hub_screen_helpers.calculate_notes_ui_state") as mock_calc:
            mock_calc.return_value = {
                "button_enabled": True,
                "text_field_enabled": True,
                "placeholder_message": "",
            }

            with patch.object(renderer, "_logger") as mock_logger:
                renderer.update_notes_ui_state(
                    has_org_id=True,
                    btn_add_note=fake_btn,
                    new_note_field=None,
                )

                # Verifica que logger.debug foi chamado com erro
                mock_logger.debug.assert_called_once()
                call_args = str(mock_logger.debug.call_args)
                assert "erro" in call_args.lower() or "botão" in call_args.lower()

    def test_update_ui_state_catches_text_field_exception(self, renderer: Any) -> None:
        """update_notes_ui_state() captura exceção de text.insert()."""
        fake_text = FakeText()
        # Força exceção em insert
        fake_text.insert = MagicMock(side_effect=RuntimeError("Insert error"))

        with patch("src.modules.hub.views.hub_screen_helpers.calculate_notes_ui_state") as mock_calc:
            mock_calc.return_value = {
                "button_enabled": True,
                "text_field_enabled": True,
                "placeholder_message": "Test placeholder",
            }

            with patch.object(renderer, "_logger") as mock_logger:
                renderer.update_notes_ui_state(
                    has_org_id=True,
                    btn_add_note=None,
                    new_note_field=fake_text,
                )

                # Verifica que logger.debug foi chamado com erro
                mock_logger.debug.assert_called_once()
                call_args = str(mock_logger.debug.call_args)
                assert "erro" in call_args.lower()

    def test_update_ui_state_without_placeholder_message(self, renderer: Any) -> None:
        """update_notes_ui_state() não insere quando placeholder_message é empty/None."""
        fake_text = FakeText()

        with patch("src.modules.hub.views.hub_screen_helpers.calculate_notes_ui_state") as mock_calc:
            mock_calc.return_value = {
                "button_enabled": True,
                "text_field_enabled": True,
                "placeholder_message": "",
            }

            renderer.update_notes_ui_state(
                has_org_id=True,
                btn_add_note=None,
                new_note_field=fake_text,
            )

            # Verifica que insert não foi chamado (placeholder vazio)
            assert len(fake_text.insert_calls) == 0


# =============================================================================
# TEST: Logger fallback
# =============================================================================


class TestLoggerFallback:
    """Testes do fallback de logger."""

    def test_get_logger_fallback_when_import_fails(self) -> None:
        """get_logger retorna logger padrão quando import falha."""
        import builtins
        import sys

        # Salvar módulo original
        original_module = sys.modules.get("src.modules.hub.views.hub_notes_renderer")

        try:
            # Remove módulo se já importado
            if "src.modules.hub.views.hub_notes_renderer" in sys.modules:
                del sys.modules["src.modules.hub.views.hub_notes_renderer"]

            original_import = builtins.__import__

            def mock_import(name, *args, **kwargs):
                if name == "src.core.logger":
                    raise ImportError("Mocked import failure")
                return original_import(name, *args, **kwargs)

            # Patch __import__ e reload
            with patch("builtins.__import__", side_effect=mock_import):
                import src.modules.hub.views.hub_notes_renderer as reloaded_module

                # Verifica que get_logger existe e retorna logger com nome correto
                logger = reloaded_module.get_logger("test_logger")
                assert logger.name == "test_logger"

        finally:
            # Restaurar módulo original
            if original_module is not None:
                sys.modules["src.modules.hub.views.hub_notes_renderer"] = original_module
            elif "src.modules.hub.views.hub_notes_renderer" in sys.modules:
                del sys.modules["src.modules.hub.views.hub_notes_renderer"]
