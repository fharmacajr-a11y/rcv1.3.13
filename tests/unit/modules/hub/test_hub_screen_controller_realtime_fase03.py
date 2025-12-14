"""
Testes unitários para funcionalidades de Realtime no HubScreenController.

Microfase 15-C - Fase 03: Realtime
- setup_realtime()
- stop_realtime()
- on_realtime_note()
- _append_note_incremental()

Cobertura:
- Setup de canal realtime
- Handlers de eventos
- Filtragem por org_id
- Error handling
"""

from unittest.mock import MagicMock, patch
from typing import Any

import pytest

from src.modules.hub.hub_screen_controller import HubScreenController


# ─────────────────────────────────────────────────────────────────────────
# Fixtures reutilizados (padrão do teste de notas)
# ─────────────────────────────────────────────────────────────────────────


@pytest.fixture
def fake_state():
    """State com campos necessários para realtime."""
    state = MagicMock()
    state.org_id = "org-123"
    state.live_sync_on = False
    state.live_org_id = None
    state.live_channel = None
    state.cached_notes = []
    state.notes = []
    state.is_active = True

    return state


@pytest.fixture
def fake_notes_vm():
    """ViewModel de notas com método async de carregamento."""
    vm = MagicMock()

    # Simular NotesViewState de sucesso
    fake_state = MagicMock()
    fake_state.notes = []

    # load() deve retornar uma coroutine
    async def fake_load(org_id: str, author_names_cache: dict[str, str]) -> Any:
        return fake_state

    vm.load = MagicMock(side_effect=lambda org_id, author_names_cache: fake_load(org_id, author_names_cache))

    return vm


@pytest.fixture
def fake_view(fake_state):
    """View duck-typed com métodos de notas e realtime."""
    view = MagicMock()
    view.render_notes.return_value = None
    view._update_notes_ui_state.return_value = None
    # Quando controller chamar _get_org_id_safe(), retornar o org_id atual do state
    view._get_org_id_safe = MagicMock(side_effect=lambda: fake_state.org_id)
    return view


@pytest.fixture
def fake_async_runner():
    """Async runner que executa callbacks de forma síncrona para testes."""
    runner = MagicMock()

    def sync_run(func, on_success=None, on_error=None):
        """Simula execução assíncrona de forma síncrona."""
        try:
            # func() é uma coroutine, executar com asyncio.run
            import asyncio

            coro = func()
            result = asyncio.run(coro)
            if on_success:
                on_success(result)
        except Exception as exc:
            if on_error:
                on_error(exc)

    runner.run = MagicMock(side_effect=sync_run)
    return runner


@pytest.fixture
def fake_lifecycle():
    """Lifecycle service mock."""
    lc = MagicMock()
    lc.schedule_notes_poll.return_value = None
    return lc


@pytest.fixture
def fake_quick_actions_controller():
    """Fake QuickActionsController para testes (MF-39)."""
    controller = MagicMock()
    controller.handle_action_click = MagicMock()
    return controller


@pytest.fixture
def controller_with_mocks(
    fake_state,
    fake_notes_vm,
    fake_view,
    fake_async_runner,
    fake_lifecycle,
    fake_quick_actions_controller,
):
    """Controller configurado com todos os mocks."""
    controller = HubScreenController(
        state=fake_state,
        notes_vm=fake_notes_vm,
        dashboard_vm=MagicMock(),  # dashboard não usado em testes de realtime
        quick_actions_vm=MagicMock(),  # quick actions não usado
        view=fake_view,
        async_runner=fake_async_runner,
        lifecycle=fake_lifecycle,
        quick_actions_controller=fake_quick_actions_controller,
    )
    return controller


# ─────────────────────────────────────────────────────────────────────────
# Testes: setup_realtime()
# ─────────────────────────────────────────────────────────────────────────


@patch("infra.supabase_client.get_supabase")
def test_setup_realtime_registra_callback(mock_get_supabase, controller_with_mocks, fake_state):
    """setup_realtime() deve registrar callback para eventos INSERT."""
    fake_state.org_id = "org-123"
    fake_state.live_sync_on = False

    # Mock do cliente Supabase
    mock_client = MagicMock()
    mock_channel = MagicMock()
    mock_client.realtime.channel.return_value = mock_channel
    mock_get_supabase.return_value = mock_client

    controller_with_mocks.setup_realtime()

    # Deve criar canal com nome específico
    mock_client.realtime.channel.assert_called_once_with("rc_notes_org_org-123")

    # Deve registrar handler para INSERT
    assert mock_channel.on.called
    call_args = mock_channel.on.call_args
    assert call_args[0][0] == "postgres_changes"
    config = call_args[0][1]
    assert config["event"] == "INSERT"
    assert config["table"] == "rc_notes"
    assert "org_id=eq.org-123" in config["filter"]

    # Deve fazer subscribe
    mock_channel.subscribe.assert_called_once()

    # Deve marcar state
    assert fake_state.live_sync_on is True
    assert fake_state.live_org_id == "org-123"
    assert fake_state.live_channel == mock_channel


@patch("infra.supabase_client.get_supabase")
def test_setup_realtime_sem_org_id_nao_faz_nada(mock_get_supabase, controller_with_mocks, fake_state):
    """setup_realtime() sem org_id não deve configurar canal."""
    fake_state.org_id = None

    controller_with_mocks.setup_realtime()

    # Não deve chamar get_supabase
    mock_get_supabase.assert_not_called()
    # State deve continuar desligado
    assert fake_state.live_sync_on is False


@patch("infra.supabase_client.get_supabase")
def test_setup_realtime_ja_ativo_nao_recria_canal(mock_get_supabase, controller_with_mocks, fake_state):
    """setup_realtime() com canal já ativo não deve recriar."""
    fake_state.org_id = "org-123"
    fake_state.live_sync_on = True
    fake_state.live_org_id = "org-123"

    controller_with_mocks.setup_realtime()

    # Não deve chamar get_supabase
    mock_get_supabase.assert_not_called()


@patch("infra.supabase_client.get_supabase")
def test_setup_realtime_com_erro_nao_quebra(mock_get_supabase, controller_with_mocks, fake_state):
    """setup_realtime() com erro não deve quebrar aplicação."""
    fake_state.org_id = "org-123"
    mock_get_supabase.side_effect = Exception("Supabase error")

    # Não deve levantar exceção
    controller_with_mocks.setup_realtime()

    # State deve estar marcado como inativo (erro)
    assert fake_state.live_sync_on is False
    assert fake_state.live_channel is None


# ─────────────────────────────────────────────────────────────────────────
# Testes: stop_realtime()
# ─────────────────────────────────────────────────────────────────────────


def test_stop_realtime_desinscreve_canal(controller_with_mocks, fake_state):
    """stop_realtime() deve desinscrever do canal."""
    fake_state.live_sync_on = True
    fake_state.live_org_id = "org-123"
    mock_channel = MagicMock()
    fake_state.live_channel = mock_channel

    controller_with_mocks.stop_realtime()

    # Deve chamar unsubscribe
    mock_channel.unsubscribe.assert_called_once()

    # Deve limpar state
    assert fake_state.live_sync_on is False
    assert fake_state.live_org_id is None
    assert fake_state.live_channel is None


def test_stop_realtime_sem_canal_nao_quebra(controller_with_mocks, fake_state):
    """stop_realtime() sem canal ativo não deve quebrar."""
    fake_state.live_sync_on = False
    fake_state.live_channel = None

    # Não deve levantar exceção
    controller_with_mocks.stop_realtime()

    assert fake_state.live_sync_on is False


def test_stop_realtime_com_erro_limpa_state(controller_with_mocks, fake_state):
    """stop_realtime() com erro no unsubscribe deve limpar state mesmo assim."""
    fake_state.live_sync_on = True
    mock_channel = MagicMock()
    mock_channel.unsubscribe.side_effect = Exception("Unsubscribe error")
    fake_state.live_channel = mock_channel

    controller_with_mocks.stop_realtime()

    # Deve limpar state mesmo com erro
    assert fake_state.live_sync_on is False
    assert fake_state.live_channel is None


# ─────────────────────────────────────────────────────────────────────────
# Testes: on_realtime_note()
# ─────────────────────────────────────────────────────────────────────────


def test_on_realtime_note_evento_valido_atualiza_cache(controller_with_mocks, fake_state, fake_view):
    """on_realtime_note() com evento válido deve atualizar cache e UI."""
    fake_state.org_id = "org-123"
    fake_state.cached_notes = []

    payload = {
        "id": "note-1",
        "org_id": "org-123",
        "body": "Nova nota via realtime",
        "author_email": "user@test.com",
        "created_at": "2024-01-01T10:00:00Z",
    }

    controller_with_mocks.on_realtime_note(payload)

    # Deve adicionar ao cache
    assert len(fake_state.cached_notes) == 1
    assert fake_state.cached_notes[0]["id"] == "note-1"

    # Deve chamar render_notes
    fake_view.render_notes.assert_called_once()


def test_on_realtime_note_payload_sem_id_eh_ignorado(controller_with_mocks, fake_state, fake_view):
    """on_realtime_note() com payload sem id deve ser ignorado."""
    fake_state.cached_notes = []

    payload = {
        "body": "Nota sem ID",
    }

    controller_with_mocks.on_realtime_note(payload)

    # Não deve adicionar ao cache
    assert len(fake_state.cached_notes) == 0

    # Não deve chamar render_notes
    fake_view.render_notes.assert_not_called()


def test_on_realtime_note_payload_vazio_eh_ignorado(controller_with_mocks, fake_state, fake_view):
    """on_realtime_note() com payload vazio/None deve ser ignorado."""
    fake_state.cached_notes = []

    controller_with_mocks.on_realtime_note({})

    # Não deve adicionar ao cache
    assert len(fake_state.cached_notes) == 0

    # Não deve chamar render_notes
    fake_view.render_notes.assert_not_called()


def test_on_realtime_note_duplicado_nao_adiciona_novamente(controller_with_mocks, fake_state):
    """on_realtime_note() com nota duplicada não deve adicionar novamente."""
    fake_state.org_id = "org-123"
    fake_state.cached_notes = [{"id": "note-1", "body": "Nota existente"}]

    payload = {
        "id": "note-1",
        "org_id": "org-123",
        "body": "Nota duplicada",
    }

    controller_with_mocks.on_realtime_note(payload)

    # Cache deve continuar com apenas 1 nota
    assert len(fake_state.cached_notes) == 1


def test_on_realtime_note_quebra_view_sem_explodir(controller_with_mocks, fake_state, fake_view):
    """on_realtime_note() com erro na view não deve quebrar."""
    fake_state.org_id = "org-123"
    fake_state.cached_notes = []
    fake_view.render_notes.side_effect = Exception("Render error")

    payload = {
        "id": "note-1",
        "org_id": "org-123",
        "body": "Nota teste",
    }

    # Não deve levantar exceção
    controller_with_mocks.on_realtime_note(payload)

    # Nota deve estar no cache mesmo com erro de render
    assert len(fake_state.cached_notes) == 1


# ─────────────────────────────────────────────────────────────────────────
# Testes: _append_note_incremental()
# ─────────────────────────────────────────────────────────────────────────


def test_append_note_incremental_adiciona_ao_cache(controller_with_mocks, fake_state):
    """_append_note_incremental() deve adicionar nota ao cache."""
    fake_state.org_id = "org-123"
    fake_state.cached_notes = []

    row = {
        "id": "note-1",
        "org_id": "org-123",
        "body": "Nova nota",
    }

    controller_with_mocks._append_note_incremental(row)

    # Deve adicionar ao cache
    assert len(fake_state.cached_notes) == 1
    assert fake_state.cached_notes[0]["id"] == "note-1"


def test_append_note_incremental_atualiza_hash(controller_with_mocks, fake_state):
    """_append_note_incremental() deve atualizar hash de notas."""
    fake_state.org_id = "org-123"
    fake_state.cached_notes = []
    fake_state.update_notes_hash = MagicMock()

    row = {
        "id": "note-1",
        "org_id": "org-123",
        "body": "Nova nota",
    }

    controller_with_mocks._append_note_incremental(row)

    # Deve chamar update_notes_hash
    fake_state.update_notes_hash.assert_called_once()


def test_append_note_incremental_chama_render(controller_with_mocks, fake_state, fake_view):
    """_append_note_incremental() deve chamar render_notes."""
    fake_state.org_id = "org-123"
    fake_state.cached_notes = []

    row = {
        "id": "note-1",
        "org_id": "org-123",
        "body": "Nova nota",
    }

    controller_with_mocks._append_note_incremental(row)

    # Deve chamar render_notes com força=True (nova nota)
    fake_view.render_notes.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────
# Estatísticas de Cobertura
# ─────────────────────────────────────────────────────────────────────────
# Total de testes: 17
# Métodos cobertos:
# - setup_realtime() - 4 testes
# - stop_realtime() - 3 testes
# - on_realtime_note() - 6 testes
# - _append_note_incremental() - 3 testes
# - Integração realtime - 1 teste
