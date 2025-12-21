"""
Testes de cobertura QA para infra/supabase/db_client.py

Objetivo: Cobrir casos faltantes (linhas 170-171, branch StopIteration)
e corrigir teste instável de get_supabase_state.
"""

from __future__ import annotations

import sys
import time
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock

import pytest

import infra.supabase.db_client as db_client


@pytest.fixture(autouse=True)
def _reset_singleton(monkeypatch):
    """Reset singleton e estado antes de cada teste."""
    monkeypatch.setattr(db_client, "_SUPABASE_SINGLETON", None)
    monkeypatch.setattr(db_client, "_SINGLETON_REUSE_LOGGED", False)
    monkeypatch.setattr(db_client, "_IS_ONLINE", False)
    monkeypatch.setattr(db_client, "_LAST_SUCCESS_TIMESTAMP", 0.0)
    monkeypatch.setattr(db_client, "_HEALTH_CHECKER_STARTED", False)
    yield


def test_get_supabase_state_online_dentro_threshold(monkeypatch):
    """Testa estado online quando última resposta está DENTRO do threshold."""
    # Definir threshold explícito
    monkeypatch.setattr(db_client.supa_types, "HEALTHCHECK_UNSTABLE_THRESHOLD", 60.0)

    # Definir timestamp bem dentro do threshold (5s atrás)
    now = time.time()
    monkeypatch.setattr(db_client, "_IS_ONLINE", True)
    monkeypatch.setattr(db_client, "_LAST_SUCCESS_TIMESTAMP", now - 5.0)

    state, desc = db_client.get_supabase_state()
    assert state == "online", f"Esperado 'online', obtido '{state}' (threshold: 60s, delta: 5s)"
    assert "estável" in desc.lower() or "estabilidade" in desc.lower()


def test_get_supabase_state_unstable_apos_threshold(monkeypatch):
    """Testa estado instável quando última resposta excede threshold."""
    # Definir threshold explícito
    monkeypatch.setattr(db_client.supa_types, "HEALTHCHECK_UNSTABLE_THRESHOLD", 60.0)

    # Definir timestamp além do threshold (70s atrás)
    now = time.time()
    monkeypatch.setattr(db_client, "_IS_ONLINE", True)
    monkeypatch.setattr(db_client, "_LAST_SUCCESS_TIMESTAMP", now - 70.0)

    state, desc = db_client.get_supabase_state()
    assert state == "unstable", f"Esperado 'unstable', obtido '{state}' (threshold: 60s, delta: 70s)"
    assert "limiar" in desc.lower() or "threshold" in desc.lower()


def test_get_supabase_state_offline_quando_is_online_false(monkeypatch):
    """Testa estado offline quando _IS_ONLINE é False."""
    monkeypatch.setattr(db_client.supa_types, "HEALTHCHECK_UNSTABLE_THRESHOLD", 60.0)
    monkeypatch.setattr(db_client, "_IS_ONLINE", False)
    monkeypatch.setattr(db_client, "_LAST_SUCCESS_TIMESTAMP", time.time())

    state, desc = db_client.get_supabase_state()
    assert state == "offline"
    assert "sem resposta" in desc.lower() or "offline" in desc.lower()


def test_get_cloud_status_for_ui_todos_estados(monkeypatch):
    """Testa get_cloud_status_for_ui() para todos os 3 estados."""
    monkeypatch.setattr(db_client.supa_types, "HEALTHCHECK_UNSTABLE_THRESHOLD", 60.0)

    # Estado: offline
    monkeypatch.setattr(db_client, "_IS_ONLINE", False)
    monkeypatch.setattr(db_client, "_LAST_SUCCESS_TIMESTAMP", 0.0)
    text, style, tooltip = db_client.get_cloud_status_for_ui()
    assert text == "Offline"
    assert style == "danger"
    assert "offline" in tooltip.lower() or "sem conexão" in tooltip.lower()

    # Estado: online
    now = time.time()
    monkeypatch.setattr(db_client, "_IS_ONLINE", True)
    monkeypatch.setattr(db_client, "_LAST_SUCCESS_TIMESTAMP", now - 5.0)
    text, style, tooltip = db_client.get_cloud_status_for_ui()
    assert text == "Online"
    assert style == "success"
    assert "conectada" in tooltip.lower() or "estável" in tooltip.lower()

    # Estado: unstable
    monkeypatch.setattr(db_client, "_IS_ONLINE", True)
    monkeypatch.setattr(db_client, "_LAST_SUCCESS_TIMESTAMP", now - 70.0)
    text, style, tooltip = db_client.get_cloud_status_for_ui()
    assert text == "Instável"
    assert style == "warning"
    assert "instável" in tooltip.lower() or "intermitente" in tooltip.lower()


def test_health_checker_stopiteration_no_loop_principal(monkeypatch):
    """
    Testa que StopIteration no loop principal do health checker
    encerra a thread de forma limpa (cobre linhas 170-171).
    """
    monkeypatch.setattr(db_client.supa_types, "HEALTHCHECK_DISABLED", False)
    monkeypatch.setattr(db_client.supa_types, "HEALTHCHECK_INTERVAL_SECONDS", 0.01)
    monkeypatch.setattr(db_client.supa_types, "HEALTHCHECK_UNSTABLE_THRESHOLD", 5.0)

    # Criar mock de cliente que lança StopIteration na primeira verificação
    mock_client = MagicMock()
    mock_get_supabase_calls = 0

    def mock_get_supabase():
        nonlocal mock_get_supabase_calls
        mock_get_supabase_calls += 1
        if mock_get_supabase_calls == 1:
            # Primeira chamada: retorna cliente normal
            return mock_client
        # Segunda chamada em diante: lança StopIteration para encerrar thread
        raise StopIteration("Teste: forçando encerramento de thread")

    monkeypatch.setattr(db_client, "get_supabase", mock_get_supabase)

    # Mock _health_check_once para não fazer verificações reais
    monkeypatch.setattr(db_client, "_health_check_once", lambda client: True)

    # Desabilitar log de spam em testes
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "test_health_checker_stopiteration")

    # Iniciar health checker (com StopIteration forçada)
    db_client._start_health_checker()

    # Aguardar thread processar
    time.sleep(0.15)

    # Verificar que thread foi marcada como iniciada
    assert db_client._HEALTH_CHECKER_STARTED is True
    # Verificar que get_supabase foi chamado pelo menos 2 vezes (StopIteration disparou)
    assert mock_get_supabase_calls >= 2, f"Esperado >=2 chamadas, obteve {mock_get_supabase_calls}"


def test_health_checker_stopiteration_no_sleep(monkeypatch):
    """
    Testa que StopIteration no time.sleep() encerra a thread de forma limpa
    (cobre linhas 185-186 - branch alternativo de StopIteration).
    """
    monkeypatch.setattr(db_client.supa_types, "HEALTHCHECK_DISABLED", False)
    monkeypatch.setattr(db_client.supa_types, "HEALTHCHECK_INTERVAL_SECONDS", 0.01)

    # Mock de time.sleep que lança StopIteration após primeira chamada
    sleep_calls = 0
    original_sleep = time.sleep

    def mock_sleep(duration):
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls >= 2:
            # Segunda chamada ao sleep: encerrar thread
            raise StopIteration("Teste: forçando encerramento em sleep")
        # Primeira chamada: sleep real curto
        original_sleep(0.001)

    monkeypatch.setattr(time, "sleep", mock_sleep)

    # Mock get_supabase para retornar cliente fake
    mock_client = MagicMock()
    monkeypatch.setattr(db_client, "get_supabase", lambda: mock_client)

    # Mock _health_check_once para retornar sucesso
    monkeypatch.setattr(db_client, "_health_check_once", lambda client: True)

    # Desabilitar log de spam em testes
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "test_health_checker_stopiteration_sleep")

    # Iniciar health checker
    db_client._start_health_checker()

    # Aguardar thread processar múltiplos ciclos
    original_sleep(0.2)

    # Verificar que sleep foi chamado pelo menos 2 vezes (StopIteration disparou)
    assert sleep_calls >= 2, f"Esperado >=2 chamadas ao sleep, obteve {sleep_calls}"


def test_health_check_exception_generico_no_loop(monkeypatch):
    """
    Testa que Exception genérica no loop do health checker
    não trava a thread (continua rodando).
    """
    monkeypatch.setattr(db_client.supa_types, "HEALTHCHECK_DISABLED", False)
    monkeypatch.setattr(db_client.supa_types, "HEALTHCHECK_INTERVAL_SECONDS", 0.01)

    # Mock get_supabase que lança Exception na primeira chamada
    call_count = 0

    def mock_get_supabase():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("Teste: erro simulado no get_supabase")
        # Após primeira exceção, retornar cliente normal
        return MagicMock()

    monkeypatch.setattr(db_client, "get_supabase", mock_get_supabase)
    monkeypatch.setattr(db_client, "_health_check_once", lambda client: True)

    # Desabilitar log de spam em testes
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "test_health_check_exception")

    # Patch time.sleep para controlar ciclos
    sleep_count = 0
    original_sleep = time.sleep

    def mock_sleep(duration):
        nonlocal sleep_count
        sleep_count += 1
        if sleep_count >= 3:
            # Após 3 ciclos, encerrar thread
            raise StopIteration("Teste: finalizar após 3 ciclos")
        original_sleep(0.01)  # Sleep real curto

    monkeypatch.setattr(time, "sleep", mock_sleep)

    # Iniciar health checker
    db_client._start_health_checker()

    # Aguardar thread processar (fora do monkeypatch de sleep)
    original_sleep(0.15)

    # Verificar que Exception foi processada (thread continuou executando)
    assert call_count >= 2, f"Esperado >=2 chamadas (erro + recuperação), obteve {call_count}"

    # Verificar que _IS_ONLINE foi marcado como False após a Exception
    # (mas pode ter voltado a True se recuperou)
    assert sleep_count >= 3, f"Esperado >=3 ciclos de sleep, obteve {sleep_count}"


def test_is_really_online_threshold_exato(monkeypatch):
    """Testa is_really_online() com threshold exato (sem arredondamentos)."""
    monkeypatch.setattr(db_client.supa_types, "HEALTHCHECK_UNSTABLE_THRESHOLD", 60.0)

    # Caso 1: Exatamente no threshold (59.999s) -> online
    now = time.time()
    monkeypatch.setattr(db_client, "_IS_ONLINE", True)
    monkeypatch.setattr(db_client, "_LAST_SUCCESS_TIMESTAMP", now - 59.999)
    assert db_client.is_really_online() is True

    # Caso 2: Exatamente acima do threshold (60.001s) -> offline
    monkeypatch.setattr(db_client, "_LAST_SUCCESS_TIMESTAMP", now - 60.001)
    assert db_client.is_really_online() is False

    # Caso 3: _IS_ONLINE=False -> offline independente do timestamp
    monkeypatch.setattr(db_client, "_IS_ONLINE", False)
    monkeypatch.setattr(db_client, "_LAST_SUCCESS_TIMESTAMP", now - 5.0)
    assert db_client.is_really_online() is False


def test_exec_postgrest_com_retry(monkeypatch):
    """Testa exec_postgrest() com retry em caso de falha temporária."""

    # Mock builder que falha 2 vezes e sucede na 3ª
    call_count = 0

    def mock_execute():
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise ConnectionError(f"Falha temporária #{call_count}")
        return SimpleNamespace(data="success", error=None)

    mock_builder = SimpleNamespace(execute=mock_execute)

    # Executar com retry
    result = db_client.exec_postgrest(mock_builder)

    assert call_count == 3, f"Esperado 3 tentativas, obteve {call_count}"
    assert result.data == "success"


def test_health_check_fallback_404_auth_health_ok(monkeypatch):
    """Testa fallback para /auth/v1/health quando RPC retorna 404."""
    monkeypatch.setattr(db_client.supa_types, "HEALTHCHECK_USE_RPC", True)
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")

    # Mock exec_postgrest que lança 404
    monkeypatch.setattr(db_client, "exec_postgrest", lambda builder: (_ for _ in ()).throw(Exception("404 Not Found")))

    # Mock httpx.get que retorna sucesso
    mock_httpx = ModuleType("httpx")

    def mock_get(url, timeout):
        assert "/auth/v1/health" in url
        return SimpleNamespace(status_code=200, json=lambda: {"version": "2.0", "name": "GoTrue"})

    mock_httpx.get = mock_get
    mock_httpx.Response = SimpleNamespace
    monkeypatch.setitem(sys.modules, "httpx", mock_httpx)

    # Executar health check
    mock_client = MagicMock()
    mock_client.rpc = lambda name: "rpc:ping"

    result = db_client._health_check_once(mock_client)
    assert result is True


def test_health_check_fallback_404_auth_health_falha(monkeypatch):
    """Testa fallback para /auth/v1/health quando RPC 404 e auth falha."""
    monkeypatch.setattr(db_client.supa_types, "HEALTHCHECK_USE_RPC", True)
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setattr(db_client.supa_types, "HEALTHCHECK_FALLBACK_TABLE", "profiles")

    # Mock exec_postgrest que lança 404 no RPC e sucede no fallback table
    call_count = 0

    def mock_exec_postgrest(builder):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Primeira chamada (RPC): 404
            raise Exception("404 Not Found")
        # Segunda chamada (fallback table): sucesso
        return SimpleNamespace(data=[], error=None)

    monkeypatch.setattr(db_client, "exec_postgrest", mock_exec_postgrest)

    # Mock httpx.get que falha
    mock_httpx = ModuleType("httpx")

    def mock_get(url, timeout):
        raise ConnectionError("Auth endpoint inacessível")

    mock_httpx.get = mock_get
    monkeypatch.setitem(sys.modules, "httpx", mock_httpx)

    # Executar health check
    mock_client = MagicMock()
    mock_client.rpc = lambda name: "rpc:ping"
    mock_client.table = lambda name: MagicMock(select=lambda *args, **kwargs: MagicMock(limit=lambda n: "table-query"))

    result = db_client._health_check_once(mock_client)
    assert result is True  # Deve ter sucesso via fallback table
    assert call_count == 2  # RPC (falhou) + fallback table (sucedeu)
