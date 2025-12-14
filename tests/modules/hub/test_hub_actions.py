# -*- coding: utf-8 -*-
"""
Testes para lifecycle_service (antigo src/modules/hub/actions.py) - FASE 2 TEST-001.

UPDATED: Migrado para testar lifecycle_service diretamente após remoção do shim.

Cobertura headless (sem Tk real):
- handle_screen_shown() - inicialização de live-sync
- Tratamento de erros (offline, auth, tabela ausente)
"""

from __future__ import annotations

import sys
import types
from typing import Any, Callable, List
from unittest.mock import MagicMock

import pytest


# ============================================================================
# FIXTURES E STUBS
# ============================================================================


class NotesHistoryStub:
    """Stub para widget de histórico de notas."""

    def __init__(self):
        self.content = ""
        self._index_value = "1.0"

    def index(self, idx: str) -> str:
        return self._index_value

    def get(self, start: str, end: str) -> str:
        return self.content

    def set_empty(self):
        self._index_value = "1.0"
        self.content = ""

    def set_content(self, content: str):
        self.content = content
        self._index_value = "5.0"


class NewNoteStub:
    """Stub para widget de nova nota."""

    def __init__(self):
        self._content = ""

    def get(self, start: str, end: str) -> str:
        return self._content

    def delete(self, start: str, end: str) -> None:
        self._content = ""

    def set_content(self, content: str):
        self._content = content


class ButtonStub:
    """Stub para botão."""

    def __init__(self):
        self.state = "normal"
        self.configure_calls: List[dict] = []

    def configure(self, **kwargs):
        self.configure_calls.append(kwargs)
        if "state" in kwargs:
            self.state = kwargs["state"]


class ScreenStub:
    """Stub completo para HubScreen (sem Tk)."""

    def __init__(self):
        self.notes_history = NotesHistoryStub()
        self.new_note = NewNoteStub()
        self.btn_add_note = ButtonStub()

        self.state = type(
            "obj",
            (object,),
            {
                "notes_last_data": [],
                "author_cache": {},
                "email_prefix_map": {},
                "names_cache_loaded": False,
            },
        )()
        self._last_org_for_names = None

        self._auth_ready_value = True
        self._online_value = True
        self._org_id_value = "org-123"
        self._email_value = "user@test.com"

        self.render_notes_calls: List[tuple] = []
        self.refresh_cache_calls: List[dict] = []
        self.live_sync_started = False

        self.after_calls: List[tuple] = []
        self._auto_run_after = True

    def _auth_ready(self) -> bool:
        return self._auth_ready_value

    def _get_app(self) -> Any:
        return self if self._online_value else None

    def _is_online(self, app: Any) -> bool:
        return self._online_value

    def _get_org_id_safe(self) -> str | None:
        return self._org_id_value

    def _get_email_safe(self) -> str | None:
        return self._email_value

    def render_notes(self, notes: list, force: bool = False) -> None:
        self.render_notes_calls.append((notes, force))

    def clear_author_cache(self) -> None:
        """Limpa cache de autores (MF-19: método público via StateManager)."""
        self.state.author_cache = {}
        self.state.email_prefix_map = {}
        self.state.names_cache_loaded = False

    def _refresh_author_names_cache_async(self, force: bool = False) -> None:
        self.refresh_cache_calls.append({"force": force})

    def _start_live_sync(self) -> None:
        self.live_sync_started = True

    def after(self, delay: int, func: Callable | None = None, *args) -> str:
        job_id = f"job-{len(self.after_calls)}"
        self.after_calls.append((delay, func, args))
        if func and delay == 0 and self._auto_run_after:
            func(*args)
        return job_id


@pytest.fixture
def notes_service_stub(monkeypatch):
    """Stub do serviço de notas."""
    service = types.SimpleNamespace(
        add_note=MagicMock(),
        list_notes=MagicMock(return_value=[]),
        NotesTransientError=type("NotesTransientError", (Exception,), {}),
        NotesAuthError=type("NotesAuthError", (Exception,), {}),
        NotesTableMissingError=type("NotesTableMissingError", (Exception,), {}),
    )

    # Injetar no sys.modules
    monkeypatch.setitem(sys.modules, "src.modules.notas.service", service)
    monkeypatch.setitem(sys.modules, "src.modules.notas", types.SimpleNamespace(service=service))

    return service


@pytest.fixture
def lifecycle_service(monkeypatch, notes_service_stub):
    """Importa lifecycle_service após configurar stubs."""
    # Limpar cache de import
    sys.modules.pop("src.modules.hub.services.lifecycle_service", None)

    # Mock de custom_dialogs
    custom_dialogs = types.SimpleNamespace(show_info=MagicMock())
    monkeypatch.setitem(sys.modules, "src.ui.custom_dialogs", custom_dialogs)

    from src.modules.hub.services import lifecycle_service

    return lifecycle_service


@pytest.fixture
def messagebox_mock(monkeypatch, lifecycle_service):
    """Mock do messagebox."""
    mock = MagicMock()
    return mock


@pytest.fixture
def threading_mock(monkeypatch, lifecycle_service):
    """Mock do threading para execução síncrona."""
    threads = []

    class InstantThread:
        def __init__(self, target=None, daemon=None):
            self.target = target
            self.daemon = daemon

        def start(self):
            if self.target:
                self.target()

    def factory(*args, **kwargs):
        thread = InstantThread(*args, **kwargs)
        threads.append(thread)
        return thread

    import threading as threading_module

    monkeypatch.setattr(threading_module, "Thread", factory)
    return threads


# ============================================================================
# TESTES: on_show()
# ============================================================================


class TestOnShow:
    """Testes para on_show()."""

    def test_starts_live_sync(self, lifecycle_service):
        """on_show() inicia live-sync."""
        screen = ScreenStub()

        lifecycle_service.handle_screen_shown(screen)

        assert screen.live_sync_started is True

    def test_renders_cached_notes_when_empty(self, lifecycle_service):
        """on_show() renderiza notas do cache quando widget vazio."""
        screen = ScreenStub()
        screen.notes_history.set_empty()
        screen.state.notes_last_data = [{"id": 1, "body": "cached"}]

        lifecycle_service.handle_screen_shown(screen)

        assert len(screen.render_notes_calls) == 1
        assert screen.render_notes_calls[0][0] == [{"id": 1, "body": "cached"}]
        assert screen.render_notes_calls[0][1] is True  # force=True

    def test_skips_render_when_widget_has_content(self, lifecycle_service):
        """on_show() não renderiza se widget já tem conteúdo."""
        screen = ScreenStub()
        screen.notes_history.set_content("existing content")

        lifecycle_service.handle_screen_shown(screen)

        assert len(screen.render_notes_calls) == 0

    def test_refreshes_names_cache(self, lifecycle_service):
        """on_show() atualiza cache de nomes."""
        screen = ScreenStub()

        lifecycle_service.handle_screen_shown(screen)

        assert len(screen.refresh_cache_calls) > 0
        assert screen.refresh_cache_calls[-1]["force"] is True

    def test_clears_names_cache(self, lifecycle_service):
        """on_show() limpa cache de nomes antes de refresh."""
        screen = ScreenStub()
        screen.state.author_cache = {"old": "data"}
        screen.state.email_prefix_map = {"old": "data"}
        screen.state.names_cache_loaded = True
        screen._last_org_for_names = "old-org"

        lifecycle_service.handle_screen_shown(screen)

        assert screen.state.author_cache == {}
        assert screen.state.email_prefix_map == {}
        assert screen.state.names_cache_loaded is False
        assert screen._last_org_for_names is None

    def test_handles_live_sync_error(self, lifecycle_service):
        """on_show() trata erro no live-sync graciosamente."""
        screen = ScreenStub()

        def fail_sync():
            raise RuntimeError("sync failed")

        screen._start_live_sync = fail_sync

        # Não deve levantar exceção
        lifecycle_service.handle_screen_shown(screen)

        # Cache deve ser atualizado mesmo assim
        assert len(screen.refresh_cache_calls) > 0


# ============================================================================
# TESTES: on_add_note_clicked()
# ============================================================================


@pytest.mark.skip(reason="on_add_note_clicked foi removido em LEGACY-02")
class TestOnAddNoteClicked:
    """Testes para on_add_note_clicked()."""

    def test_ignores_empty_text(self, lifecycle_service, threading_mock):
        """Ignora texto vazio."""
        screen = ScreenStub()
        screen.new_note.set_content("")

        lifecycle_service.on_add_note_clicked(screen)

        assert len(threading_mock) == 0
        assert screen.btn_add_note.state == "normal"

    def test_ignores_whitespace_only(self, lifecycle_service, threading_mock):
        """Ignora texto apenas com espaços."""
        screen = ScreenStub()
        screen.new_note.set_content("   \n  \t  ")

        lifecycle_service.on_add_note_clicked(screen)

        assert len(threading_mock) == 0

    def test_requires_auth(self, lifecycle_service, messagebox_mock, threading_mock):
        """Exige autenticação."""
        screen = ScreenStub()
        screen.new_note.set_content("Test note")
        screen._auth_ready_value = False

        lifecycle_service.on_add_note_clicked(screen)

        messagebox_mock.showerror.assert_called_once()
        assert "autenticado" in str(messagebox_mock.showerror.call_args).lower()
        assert len(threading_mock) == 0

    def test_requires_online(self, lifecycle_service, messagebox_mock, threading_mock):
        """Exige conexão online."""
        screen = ScreenStub()
        screen.new_note.set_content("Test note")
        screen._auth_ready_value = True
        screen._online_value = False

        lifecycle_service.on_add_note_clicked(screen)

        messagebox_mock.showerror.assert_called_once()
        assert "conexão" in str(messagebox_mock.showerror.call_args).lower()
        assert len(threading_mock) == 0

    def test_requires_org_and_email(self, lifecycle_service, messagebox_mock, threading_mock):
        """Exige org_id e email."""
        screen = ScreenStub()
        screen.new_note.set_content("Test note")
        screen._org_id_value = None

        lifecycle_service.on_add_note_clicked(screen)

        messagebox_mock.showerror.assert_called_once()
        assert "sessão" in str(messagebox_mock.showerror.call_args).lower()

    def test_disables_button_during_submission(self, lifecycle_service, notes_service_stub, threading_mock):
        """Desabilita botão durante submissão."""
        screen = ScreenStub()
        screen._auto_run_after = False  # Não executar after(0) automaticamente
        screen.new_note.set_content("Test note")

        lifecycle_service.on_add_note_clicked(screen)

        # Botão deve ser desabilitado antes do thread
        assert any(c.get("state") == "disabled" for c in screen.btn_add_note.configure_calls)

    def test_calls_add_note_service(self, lifecycle_service, notes_service_stub, threading_mock):
        """Chama serviço de notas."""
        screen = ScreenStub()
        screen.new_note.set_content("Test note content")

        lifecycle_service.on_add_note_clicked(screen)

        notes_service_stub.add_note.assert_called_once_with(
            "org-123",
            "user@test.com",
            "Test note content",
        )

    def test_clears_field_on_success(self, lifecycle_service, notes_service_stub, threading_mock):
        """Limpa campo após sucesso."""
        screen = ScreenStub()
        screen.new_note.set_content("Test note")

        lifecycle_service.on_add_note_clicked(screen)

        # after(0) foi chamado e executou _ui()
        assert screen.new_note.get("1.0", "end") == ""

    def test_reenables_button_on_success(self, lifecycle_service, notes_service_stub, threading_mock):
        """Reabilita botão após sucesso."""
        screen = ScreenStub()
        screen.new_note.set_content("Test note")

        lifecycle_service.on_add_note_clicked(screen)

        # Último configure deve ser state="normal"
        assert screen.btn_add_note.configure_calls[-1].get("state") == "normal"


@pytest.mark.skip(reason="on_add_note_clicked foi removido em LEGACY-02")
class TestOnAddNoteErrors:
    """Testes de tratamento de erros em on_add_note_clicked()."""

    def test_handles_transient_error(self, lifecycle_service, notes_service_stub, messagebox_mock, threading_mock):
        """Trata erro transitório."""
        screen = ScreenStub()
        screen.new_note.set_content("Test")

        notes_service_stub.add_note.side_effect = notes_service_stub.NotesTransientError()

        lifecycle_service.on_add_note_clicked(screen)

        messagebox_mock.showwarning.assert_called_once()
        assert "instável" in str(messagebox_mock.showwarning.call_args).lower()

    def test_handles_table_missing_error(self, lifecycle_service, notes_service_stub, messagebox_mock, threading_mock):
        """Trata erro de tabela ausente."""
        screen = ScreenStub()
        screen.new_note.set_content("Test")

        notes_service_stub.add_note.side_effect = notes_service_stub.NotesTableMissingError("Table not found")

        lifecycle_service.on_add_note_clicked(screen)

        messagebox_mock.showerror.assert_called_once()
        assert "rc_notes" in str(messagebox_mock.showerror.call_args)

    def test_handles_auth_error(self, lifecycle_service, notes_service_stub, messagebox_mock, threading_mock):
        """Trata erro de autenticação."""
        screen = ScreenStub()
        screen.new_note.set_content("Test")

        notes_service_stub.add_note.side_effect = notes_service_stub.NotesAuthError("Not authorized")

        lifecycle_service.on_add_note_clicked(screen)

        messagebox_mock.showerror.assert_called_once()
        assert "permissão" in str(messagebox_mock.showerror.call_args).lower()

    def test_handles_generic_error(self, lifecycle_service, notes_service_stub, messagebox_mock, threading_mock):
        """Trata erro genérico."""
        screen = ScreenStub()
        screen.new_note.set_content("Test")

        notes_service_stub.add_note.side_effect = RuntimeError("Unknown error")

        lifecycle_service.on_add_note_clicked(screen)

        messagebox_mock.showerror.assert_called_once()
        assert "falha" in str(messagebox_mock.showerror.call_args).lower()

    def test_reenables_button_on_error(self, lifecycle_service, notes_service_stub, threading_mock):
        """Reabilita botão mesmo após erro."""
        screen = ScreenStub()
        screen.new_note.set_content("Test")

        notes_service_stub.add_note.side_effect = RuntimeError("Error")

        lifecycle_service.on_add_note_clicked(screen)

        assert screen.btn_add_note.configure_calls[-1].get("state") == "normal"

    def test_marks_table_missing_flag(self, lifecycle_service, notes_service_stub, messagebox_mock, threading_mock):
        """Marca flag de tabela ausente."""
        screen = ScreenStub()
        screen.new_note.set_content("Test")
        screen._notes_table_missing = False
        screen._notes_table_missing_notified = False

        notes_service_stub.add_note.side_effect = notes_service_stub.NotesTableMissingError("Missing")

        lifecycle_service.on_add_note_clicked(screen)

        # Flags devem ser marcadas
        # (verificamos nos after_calls que _mark_table_missing foi agendado)
        assert any("_mark_table_missing" in str(call) or len(screen.after_calls) > 0 for call in [1])


@pytest.mark.skip(reason="on_add_note_clicked foi removido em LEGACY-02")
class TestOnAddNoteEdgeCases:
    """Testes de casos de borda."""

    def test_trims_whitespace(self, lifecycle_service, notes_service_stub, threading_mock):
        """Remove espaços das pontas do texto."""
        screen = ScreenStub()
        screen.new_note.set_content("  Test note  \n")

        lifecycle_service.on_add_note_clicked(screen)

        notes_service_stub.add_note.assert_called_once()
        call_args = notes_service_stub.add_note.call_args[0]
        assert call_args[2] == "Test note"

    def test_handles_missing_app(self, lifecycle_service, messagebox_mock, threading_mock):
        """Trata ausência de app."""
        screen = ScreenStub()
        screen.new_note.set_content("Test")
        screen._get_app = lambda: None

        lifecycle_service.on_add_note_clicked(screen)

        messagebox_mock.showerror.assert_called_once()

    def test_handles_missing_email(self, lifecycle_service, messagebox_mock, threading_mock):
        """Trata ausência de email."""
        screen = ScreenStub()
        screen.new_note.set_content("Test")
        screen._email_value = None

        lifecycle_service.on_add_note_clicked(screen)

        messagebox_mock.showerror.assert_called_once()
        assert "sessão" in str(messagebox_mock.showerror.call_args).lower()
