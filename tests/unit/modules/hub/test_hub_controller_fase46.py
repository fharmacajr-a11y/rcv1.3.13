"""
TESTE_1 - hub/controller

Objetivo: aumentar a cobertura de src/modules/hub/controller.py na fase 46,
cobrindo polling, refresh de notas e tratamento de erros/estados da tabela rc_notes.
"""

from __future__ import annotations

import importlib
import sys
import types
from types import SimpleNamespace
from typing import Any, Callable, List, Tuple

import pytest


class DummyText:
    def __init__(self) -> None:
        self.configure_calls: List[dict] = []
        self.insert_calls: List[Tuple[Any, Any, Any]] = []
        self.see_calls = 0

    def configure(self, **kwargs) -> None:
        self.configure_calls.append(kwargs)

    def insert(self, index, text, tags=None) -> None:  # noqa: ANN001
        self.insert_calls.append((index, text, tags))

    def see(self, index) -> None:  # noqa: ANN001
        self.see_calls += 1


class ScreenStub:
    def __init__(self) -> None:
        self.after_calls: List[Tuple[int, Callable, tuple]] = []
        self.after_cancel_calls: List[Any] = []
        self._auto_run_zero_after = True
        self._notes_poll_ms = 100
        self._auth_ready_value = True
        self._org_id_value = "org-1"
        self.notes_history = DummyText()
        self.rendered_notes = None
        self.names_cache_refreshed = False
        self._names_cache_loaded = False
        self.state = SimpleNamespace(
            notes_last_snapshot=None,
            notes_last_data=[],
            polling_active=True,
            notes_retry_ms=60000,
            notes_table_missing=False,
            notes_table_missing_notified=False,
            names_cache_loaded=False,
            live_sync_on=True,
            live_org_id="org-1",
            live_channel=None,
            live_last_ts=None,
        )
        self._notes_after_handle = None

    def after(self, delay, func=None, *args):  # noqa: ANN001
        self.after_calls.append((delay, func, args))
        if func and delay == 0 and self._auto_run_zero_after:
            return func(*args)
        return f"job{len(self.after_calls)}"

    def after_cancel(self, handle):  # noqa: ANN001
        self.after_cancel_calls.append(handle)

    def _auth_ready(self) -> bool:
        return self._auth_ready_value

    def _get_org_id_safe(self):
        return self._org_id_value

    def render_notes(self, notes):  # noqa: ANN001
        self.rendered_notes = notes

    def _refresh_author_names_cache_async(self) -> None:
        self.names_cache_refreshed = True

    # MF-19: Métodos públicos para modificar estado (encapsulam StateManager)
    def update_notes_data(self, notes, update_snapshot=True):  # noqa: ANN001
        self.state.notes_last_data = notes
        if update_snapshot:
            self.state.notes_last_snapshot = [(n.get("id"), n.get("created_at")) for n in notes]

    def set_notes_table_missing(self, missing: bool) -> None:
        self.state.notes_table_missing = missing

    def set_notes_table_missing_notified(self, notified: bool) -> None:
        self.state.notes_table_missing_notified = notified

    def set_names_cache_loaded(self, loaded: bool) -> None:
        self.state.names_cache_loaded = loaded

    def update_live_last_ts(self, timestamp: str) -> None:
        """Atualiza live_last_ts se o novo timestamp for maior."""
        current = self.state.live_last_ts or ""
        if timestamp > current:
            self.state.live_last_ts = timestamp

    def set_live_last_ts(self, timestamp: str) -> None:
        self.state.live_last_ts = timestamp

    def clear_pending_name_fetch(self) -> None:
        if not hasattr(self.state, "pending_name_fetch"):
            self.state.pending_name_fetch = set()
        else:
            self.state.pending_name_fetch.clear()

    def add_pending_name_fetch(self, email: str) -> None:
        if not hasattr(self.state, "pending_name_fetch"):
            self.state.pending_name_fetch = set()
        self.state.pending_name_fetch.add(email)

    def remove_pending_name_fetch(self, email: str) -> None:
        if hasattr(self.state, "pending_name_fetch"):
            self.state.pending_name_fetch.discard(email)


@pytest.fixture
def hub_controller(monkeypatch):
    service_stub = types.SimpleNamespace(
        list_notes=lambda *a, **k: [],
        list_notes_since=lambda *a, **k: [],
        NotesTransientError=type("NotesTransientError", (Exception,), {}),
        NotesAuthError=type("NotesAuthError", (Exception,), {}),
        NotesTableMissingError=type("NotesTableMissingError", (Exception,), {}),
    )
    notas_pkg = types.SimpleNamespace(service=service_stub)
    monkeypatch.setitem(sys.modules, "src.modules.notas", notas_pkg)
    monkeypatch.setitem(sys.modules, "src.modules.notas.service", service_stub)
    sys.modules.pop("src.modules.hub.controller", None)
    module = importlib.import_module("src.modules.hub.controller")
    return module


@pytest.fixture
def messagebox_calls(monkeypatch, hub_controller):
    calls = []
    mb = types.SimpleNamespace(showwarning=lambda *args, **kwargs: calls.append((args, kwargs)))
    monkeypatch.setattr(hub_controller, "messagebox", mb)
    return calls


@pytest.fixture
def instant_thread(monkeypatch, hub_controller):
    threads = []

    class InstantThread:
        def __init__(self, target=None, daemon=None):  # noqa: ANN001
            self.target = target
            self.daemon = daemon
            self.started = False

        def start(self) -> None:
            self.started = True
            if self.target:
                self.target()

    def factory(*args, **kwargs):
        thread = InstantThread(*args, **kwargs)
        threads.append(thread)
        return thread

    monkeypatch.setattr(hub_controller.threading, "Thread", factory)
    return threads


def test_schedule_poll_ativa_flag_e_agenda_refresh(hub_controller):
    screen = ScreenStub()
    screen.state.live_sync_on = True

    hub_controller.schedule_poll(screen, ms=123)

    assert screen.after_calls and screen.after_calls[0][0] == 123
    assert screen._hub_state.poll_job == "job1"


def test_schedule_poll_nao_agenda_quando_sync_off(hub_controller):
    screen = ScreenStub()
    screen.state.live_sync_on = False

    hub_controller.schedule_poll(screen)

    assert screen.after_calls == []
    assert getattr(screen._hub_state, "poll_job", None) is None


def test_schedule_poll_cancela_job_anterior(hub_controller):
    screen = ScreenStub()
    screen.state.live_sync_on = True
    hub_state = hub_controller._ensure_poll_attrs(screen)
    hub_state.poll_job = "job-old"

    hub_controller.schedule_poll(screen, ms=50)

    assert screen.after_cancel_calls == ["job-old"]
    assert hub_state.poll_job == "job1"


def test_cancel_poll_desativa_job(hub_controller):
    screen = ScreenStub()
    hub_state = hub_controller._ensure_poll_attrs(screen)
    hub_state.poll_job = "job-x"

    hub_controller.cancel_poll(screen)

    assert screen.after_cancel_calls == ["job-x"]
    assert hub_state.poll_job is None


def test_poll_notes_if_needed_sem_live_sync_nao_faz_nada(monkeypatch, hub_controller):
    screen = ScreenStub()
    screen.state.live_sync_on = False
    monkeypatch.setattr(
        hub_controller.notes_service, "list_notes_since", lambda *a, **k: pytest.fail("nao deveria chamar")
    )

    hub_controller.poll_notes_if_needed(screen)

    assert screen.after_calls == []


def test_poll_notes_if_needed_sem_org_agenda_retry(monkeypatch, hub_controller):
    screen = ScreenStub()
    screen.state.live_sync_on = True
    screen.state.live_org_id = None
    called = []
    monkeypatch.setattr(
        hub_controller.notes_service, "list_notes_since", lambda *a, **k: pytest.fail("nao deveria chamar")
    )
    monkeypatch.setattr(hub_controller, "schedule_poll", lambda scr: called.append(scr))

    hub_controller.poll_notes_if_needed(screen)

    assert called == [screen]


def test_poll_notes_if_needed_com_novas_notas_atualiza_ts(monkeypatch, hub_controller):
    screen = ScreenStub()
    screen.state.live_sync_on = True
    screen.state.live_org_id = "org1"
    screen.state.live_last_ts = "2023-01-01T00:00:00Z"
    added = []
    monkeypatch.setattr(
        hub_controller.notes_service,
        "list_notes_since",
        lambda org, since: [{"id": 1, "created_at": "2024-01-01T00:00:01Z"}],
    )
    monkeypatch.setattr(hub_controller, "append_note_incremental", lambda scr, note: added.append((scr, note)))
    scheduled = []
    monkeypatch.setattr(hub_controller, "schedule_poll", lambda scr: scheduled.append(scr))

    hub_controller.poll_notes_if_needed(screen)

    assert added and added[0][1]["id"] == 1
    assert screen.state.live_last_ts == "2024-01-01T00:00:01Z"
    assert scheduled == [screen]


def test_on_realtime_note_encaminha_para_append(monkeypatch, hub_controller):
    screen = ScreenStub()
    captured = []
    monkeypatch.setattr(hub_controller, "append_note_incremental", lambda scr, payload: captured.append(payload))

    hub_controller.on_realtime_note(screen, {"id": 9})

    assert captured == [{"id": 9}]
    assert screen.after_calls and screen.after_calls[0][0] == 0


def test_append_note_incremental_ignora_duplicata(monkeypatch, hub_controller):
    screen = ScreenStub()
    screen.state.notes_last_data = [{"id": "1", "created_at": "ts"}]
    screen.notes_history = DummyText()
    monkeypatch.setattr(hub_controller, "_ensure_author_tag", lambda *a, **k: "tag")

    hub_controller.append_note_incremental(screen, {"id": 1, "created_at": "ts"})

    assert screen.state.notes_last_data == [{"id": "1", "created_at": "ts"}]
    assert screen.notes_history.insert_calls == []


def test_append_note_incremental_insere_nota_e_atualiza_estado(monkeypatch, hub_controller):
    screen = ScreenStub()
    screen.notes_history = DummyText()
    screen.state.live_last_ts = "2024-01-01T00:00:00Z"
    monkeypatch.setattr(hub_controller, "_ensure_author_tag", lambda *a, **k: "tag-1")
    # LEGACY-02: Atualizado para usar get_author_display_name do serviço
    monkeypatch.setattr("src.modules.hub.services.authors_service.get_author_display_name", lambda _email: "Alias")

    hub_controller.append_note_incremental(
        screen,
        {"id": 99, "created_at": "2024-01-02T00:00:00Z", "author_email": "a@b.com", "author_name": "", "body": "texto"},
    )

    assert screen.state.notes_last_snapshot == [(99, "2024-01-02T00:00:00Z")]
    assert screen.state.notes_last_data and screen.state.notes_last_data[0]["id"] == 99
    assert screen.state.live_last_ts == "2024-01-02T00:00:00Z"
    assert screen.notes_history.configure_calls
    assert screen.notes_history.insert_calls
    assert screen.notes_history.see_calls == 1


def test_refresh_notes_async_nao_roda_sem_polling(monkeypatch, hub_controller):
    screen = ScreenStub()
    screen.state.polling_active = False
    monkeypatch.setattr(hub_controller.threading, "Thread", lambda *a, **k: pytest.fail("nao deve criar thread"))

    hub_controller.refresh_notes_async(screen)

    assert screen.after_calls == []


def test_refresh_notes_async_tabela_ausente_agenda_retry(monkeypatch, hub_controller):
    screen = ScreenStub()
    screen.state.polling_active = True
    screen.state.notes_table_missing = True
    screen.state.notes_retry_ms = 1234
    monkeypatch.setattr(hub_controller.threading, "Thread", lambda *a, **k: pytest.fail("nao deve criar thread"))

    hub_controller.refresh_notes_async(screen)

    assert screen.after_calls and screen.after_calls[0][0] == 1234
    assert screen._notes_after_handle == "job1"


def test_refresh_notes_async_auth_pendente_agenda_retry(monkeypatch, hub_controller):
    screen = ScreenStub()
    screen.state.polling_active = True
    screen.state.notes_table_missing = False
    screen._auth_ready_value = False
    screen.AUTH_RETRY_MS = 321
    monkeypatch.setattr(hub_controller.threading, "Thread", lambda *a, **k: pytest.fail("nao deve criar thread"))

    hub_controller.refresh_notes_async(screen)

    assert screen.after_calls and screen.after_calls[0][0] == 321
    assert screen._notes_after_handle == "job1"


def test_refresh_notes_async_sem_org_id_agenda_retry(monkeypatch, hub_controller):
    screen = ScreenStub()
    screen.state.polling_active = True
    screen.state.notes_table_missing = False
    screen._auth_ready_value = True
    screen._org_id_value = None
    screen.AUTH_RETRY_MS = 321
    monkeypatch.setattr(hub_controller.threading, "Thread", lambda *a, **k: pytest.fail("nao deve criar thread"))

    hub_controller.refresh_notes_async(screen)

    assert screen.after_calls and screen.after_calls[0][0] == 321
    assert screen._notes_after_handle == "job1"


def test_refresh_notes_async_caminho_feliz_renderiza_e_agenda_proximo(monkeypatch, instant_thread, hub_controller):
    screen = ScreenStub()
    screen.state.polling_active = True
    screen._auth_ready_value = True
    screen._org_id_value = "org1"
    screen._notes_poll_ms = 150
    monkeypatch.setattr(
        hub_controller.notes_service, "list_notes", lambda org_id, limit=500: [{"id": 5, "created_at": "ts"}]
    )
    monkeypatch.setattr(
        hub_controller,
        "_normalize_note",
        lambda note: {"id": note["id"], "created_at": note["created_at"], "body": "b"},
    )

    hub_controller.refresh_notes_async(screen)

    assert screen.rendered_notes == [{"id": 5, "created_at": "ts", "body": "b"}]
    assert screen.names_cache_refreshed is True
    assert screen.state.notes_last_snapshot == [(5, "ts")]
    assert screen.state.notes_last_data[0]["id"] == 5
    assert screen._notes_after_handle == "job3"
    assert any(call[0] == 150 for call in screen.after_calls)


def test_refresh_notes_async_transient_error_agenda_retry(monkeypatch, instant_thread, hub_controller):
    screen = ScreenStub()
    screen.state.polling_active = True
    screen._auth_ready_value = True
    screen._org_id_value = "org1"

    class Transient(hub_controller.notes_service.NotesTransientError):
        pass

    def fail_list(*args, **kwargs):  # noqa: ANN001
        raise Transient()

    monkeypatch.setattr(hub_controller.notes_service, "NotesTransientError", Transient)
    monkeypatch.setattr(hub_controller.notes_service, "list_notes", fail_list)

    hub_controller.refresh_notes_async(screen)

    assert screen._notes_after_handle == "job2"
    assert any(call[0] == 2000 for call in screen.after_calls)


def test_refresh_notes_async_tabela_ausente_marca_flags(monkeypatch, instant_thread, messagebox_calls, hub_controller):
    screen = ScreenStub()
    screen.state.polling_active = True
    screen._auth_ready_value = True
    screen._org_id_value = "org1"

    class Missing(hub_controller.notes_service.NotesTableMissingError):
        pass

    def fail_list(*args, **kwargs):  # noqa: ANN001
        raise Missing("missing")

    monkeypatch.setattr(hub_controller.notes_service, "NotesTableMissingError", Missing)
    monkeypatch.setattr(hub_controller.notes_service, "list_notes", fail_list)

    hub_controller.refresh_notes_async(screen)

    assert screen.state.notes_table_missing is True
    assert screen.state.notes_table_missing_notified is True
    assert messagebox_calls
    assert screen._notes_after_handle is None


def test_refresh_notes_async_auth_error_emite_aviso(monkeypatch, instant_thread, messagebox_calls, hub_controller):
    screen = ScreenStub()
    screen.state.polling_active = True
    screen._auth_ready_value = True
    screen._org_id_value = "org1"

    class AuthErr(hub_controller.notes_service.NotesAuthError):
        pass

    def fail_list(*args, **kwargs):  # noqa: ANN001
        raise AuthErr("no auth")

    monkeypatch.setattr(hub_controller.notes_service, "NotesAuthError", AuthErr)
    monkeypatch.setattr(hub_controller.notes_service, "list_notes", fail_list)

    hub_controller.refresh_notes_async(screen)

    assert messagebox_calls
    assert screen._notes_after_handle is None


def test_refresh_notes_async_exception_generica_ainda_agenda(monkeypatch, instant_thread, hub_controller):
    screen = ScreenStub()
    screen._polling_active = True
    screen._auth_ready_value = True
    screen._org_id_value = "org1"
    screen._names_cache_loaded = False

    def fail_list(*args, **kwargs):  # noqa: ANN001
        raise RuntimeError("boom")

    monkeypatch.setattr(hub_controller.notes_service, "list_notes", fail_list)

    hub_controller.refresh_notes_async(screen)

    assert screen.rendered_notes == []
    assert screen.names_cache_refreshed is True
    assert screen._notes_after_handle == "job3"
    assert screen.state.notes_last_snapshot == []
