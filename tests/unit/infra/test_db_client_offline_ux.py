"""
Testes unitários para OFFLINE-SUPABASE-UX-002.

Valida que o health checker não é iniciado quando em modo cloud-only sem internet,
evitando spam de warnings no console.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import src.infra.supabase.db_client as db_client


@pytest.fixture(autouse=True)
def reset_health_checker_state():
    """Reset do estado global do health checker antes de cada teste."""
    original_value = db_client._HEALTH_CHECKER_STARTED
    db_client._HEALTH_CHECKER_STARTED = False
    yield
    db_client._HEALTH_CHECKER_STARTED = original_value


class TestHealthCheckerOfflineCloudOnly:
    """OFFLINE-SUPABASE-UX-002: Testes de health checker em cloud-only offline."""

    def test_health_checker_not_started_when_cloud_only_offline(self, monkeypatch):
        """Health checker NÃO deve iniciar em cloud-only sem internet."""
        # Configura ambiente cloud-only
        monkeypatch.setenv("RC_NO_LOCAL_FS", "1")
        monkeypatch.delenv("RC_TESTING", raising=False)
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

        # Mock de check_internet_connectivity retornando False (offline)
        with patch("src.utils.network.check_internet_connectivity") as mock_check:
            mock_check.return_value = False

            # Mock de threading.Thread para capturar se foi iniciado
            with patch("src.infra.supabase.db_client.threading.Thread") as mock_thread:
                mock_thread_instance = MagicMock()
                mock_thread.return_value = mock_thread_instance

                # Mock de supa_types para evitar erro se HEALTHCHECK_DISABLED não existir
                with patch("src.infra.supabase.db_client.supa_types") as mock_supa_types:
                    mock_supa_types.HEALTHCHECK_DISABLED = False
                    mock_supa_types.HEALTHCHECK_INTERVAL_SECONDS = 30.0
                    mock_supa_types.HEALTHCHECK_UNSTABLE_THRESHOLD = 60.0
                    mock_supa_types.HEALTHCHECK_RPC_NAME = "ping"

                    # Executa
                    db_client._start_health_checker()

                    # Validações
                    mock_check.assert_called_once_with(timeout=1.0)
                    # Thread NÃO deve ter sido criada
                    mock_thread.assert_not_called()
                    # Flag global NÃO deve ter sido setada (early return)
                    assert db_client._HEALTH_CHECKER_STARTED is False

    def test_health_checker_starts_when_cloud_only_online(self, monkeypatch):
        """Health checker DEVE iniciar em cloud-only COM internet."""
        # Configura ambiente cloud-only
        monkeypatch.setenv("RC_NO_LOCAL_FS", "1")
        monkeypatch.delenv("RC_TESTING", raising=False)
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

        # Mock de check_internet_connectivity retornando True (online)
        with patch("src.utils.network.check_internet_connectivity") as mock_check:
            mock_check.return_value = True

            # Mock de threading.Thread
            with patch("src.infra.supabase.db_client.threading.Thread") as mock_thread:
                mock_thread_instance = MagicMock()
                mock_thread.return_value = mock_thread_instance

                # Executa
                db_client._start_health_checker()

                # Validações
                mock_check.assert_called_once_with(timeout=1.0)
                # Thread DEVE ter sido criada e iniciada
                mock_thread.assert_called_once()
                mock_thread_instance.start.assert_called_once()
                # Flag global DEVE ter sido setada
                assert db_client._HEALTH_CHECKER_STARTED is True

    def test_health_checker_starts_when_not_cloud_only(self, monkeypatch):
        """Health checker DEVE iniciar no modo híbrido (não cloud-only)."""
        # Configura ambiente híbrido (RC_NO_LOCAL_FS != "1")
        monkeypatch.setenv("RC_NO_LOCAL_FS", "0")
        monkeypatch.delenv("RC_TESTING", raising=False)
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

        # Mock de check_internet_connectivity (não deve ser chamado)
        with patch("src.utils.network.check_internet_connectivity") as mock_check:
            mock_check.return_value = False  # Simula offline, mas não deve importar

            # Mock de threading.Thread
            with patch("src.infra.supabase.db_client.threading.Thread") as mock_thread:
                mock_thread_instance = MagicMock()
                mock_thread.return_value = mock_thread_instance

                # Executa
                db_client._start_health_checker()

                # Validações
                # check_internet_connectivity NÃO deve ter sido chamado
                mock_check.assert_not_called()
                # Thread DEVE ter sido criada (modo híbrido sempre inicia checker)
                mock_thread.assert_called_once()
                mock_thread_instance.start.assert_called_once()
                # Flag global DEVE ter sido setada
                assert db_client._HEALTH_CHECKER_STARTED is True

    def test_health_checker_starts_when_rc_testing(self, monkeypatch):
        """Health checker DEVE iniciar em cloud-only offline quando RC_TESTING=1."""
        # Configura ambiente cloud-only + RC_TESTING
        monkeypatch.setenv("RC_NO_LOCAL_FS", "1")
        monkeypatch.setenv("RC_TESTING", "1")

        # Mock de check_internet_connectivity (não deve ser chamado devido ao RC_TESTING)
        with patch("src.utils.network.check_internet_connectivity") as mock_check:
            mock_check.return_value = False

            # Mock de threading.Thread
            with patch("src.infra.supabase.db_client.threading.Thread") as mock_thread:
                mock_thread_instance = MagicMock()
                mock_thread.return_value = mock_thread_instance

                # Executa
                db_client._start_health_checker()

                # Validações
                # check_internet_connectivity NÃO deve ter sido chamado (skip por RC_TESTING)
                mock_check.assert_not_called()
                # Thread DEVE ter sido criada (testes sempre iniciam checker)
                mock_thread.assert_called_once()
                mock_thread_instance.start.assert_called_once()
                # Flag global DEVE ter sido setada
                assert db_client._HEALTH_CHECKER_STARTED is True

    def test_health_checker_idempotent(self, monkeypatch):
        """Segunda chamada a _start_health_checker deve ser idempotente."""
        monkeypatch.setenv("RC_NO_LOCAL_FS", "0")

        with patch("src.infra.supabase.db_client.threading.Thread") as mock_thread:
            mock_thread_instance = MagicMock()
            mock_thread.return_value = mock_thread_instance

            # Primeira chamada
            db_client._start_health_checker()
            assert mock_thread.call_count == 1

            # Segunda chamada (deve fazer early return)
            db_client._start_health_checker()
            # Não deve ter criado nova thread
            assert mock_thread.call_count == 1

    def test_health_checker_handles_check_internet_error(self, monkeypatch):
        """Health checker deve iniciar normalmente se check_internet_connectivity falhar."""
        # Configura ambiente cloud-only
        monkeypatch.setenv("RC_NO_LOCAL_FS", "1")
        monkeypatch.delenv("RC_TESTING", raising=False)
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

        # Mock de check_internet_connectivity lançando exceção
        with patch("src.utils.network.check_internet_connectivity") as mock_check:
            mock_check.side_effect = Exception("Network error")

            # Mock de threading.Thread
            with patch("src.infra.supabase.db_client.threading.Thread") as mock_thread:
                mock_thread_instance = MagicMock()
                mock_thread.return_value = mock_thread_instance

                # Executa (não deve lançar exceção)
                db_client._start_health_checker()

                # Validações
                mock_check.assert_called_once_with(timeout=1.0)
                # Thread DEVE ter sido criada (fallback em caso de erro)
                mock_thread.assert_called_once()
                mock_thread_instance.start.assert_called_once()
                # Flag global DEVE ter sido setada
                assert db_client._HEALTH_CHECKER_STARTED is True
