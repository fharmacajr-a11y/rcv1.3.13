from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
from unittest.mock import MagicMock, patch
from urllib.error import URLError

import pytest

from src.core import auth_bootstrap
from src.utils import prefs as prefs_module


@pytest.fixture
def temp_auth_prefs_dir_bootstrap(monkeypatch, tmp_path):
    prefs_dir = tmp_path / "auth_prefs_bootstrap"
    prefs_dir.mkdir()
    monkeypatch.setattr("src.utils.prefs._get_base_dir", lambda: str(prefs_dir))
    return prefs_dir


def test_is_persisted_auth_session_valid_with_recent_date():
    now = datetime(2025, 1, 8, tzinfo=timezone.utc)
    created_at = (now - timedelta(days=1)).isoformat()
    data = {
        "access_token": "at",
        "refresh_token": "rt",
        "created_at": created_at,
        "keep_logged": True,
    }
    assert auth_bootstrap.is_persisted_auth_session_valid(data, now=now, max_age_days=7) is True


def test_is_persisted_auth_session_valid_expired():
    now = datetime(2025, 1, 8, tzinfo=timezone.utc)
    created_at = (now - timedelta(days=8)).isoformat()
    data = {
        "access_token": "at",
        "refresh_token": "rt",
        "created_at": created_at,
        "keep_logged": True,
    }
    assert auth_bootstrap.is_persisted_auth_session_valid(data, now=now, max_age_days=7) is False


class DummyAuth:
    def __init__(self):
        self.last_session = None
        self.access_token = ""
        self.refresh_token = ""

    def set_session(self, access_token, refresh_token):
        self.last_session = (access_token, refresh_token)
        self.access_token = access_token
        self.refresh_token = refresh_token

        class DummyResponse:
            session = object()

        return DummyResponse()

    def get_session(self):
        class DummySession:
            def __init__(self, at, rt):
                self.access_token = at
                self.refresh_token = rt
                self.user = type("U", (), {"id": "uid-1", "email": "user@test.com"})

        return DummySession(self.access_token, self.refresh_token)


class DummyClient:
    def __init__(self):
        self.auth = DummyAuth()


def test_restore_persisted_auth_session_if_any_success(temp_auth_prefs_dir_bootstrap):
    prefs_module.save_auth_session("at", "rt", keep_logged=True)

    client = DummyClient()
    restored = auth_bootstrap.restore_persisted_auth_session_if_any(client)

    assert restored is True
    assert client.auth.last_session == ("at", "rt")


def test_restore_persisted_auth_session_if_any_expired(temp_auth_prefs_dir_bootstrap):
    old_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    path = prefs_module._auth_session_path()
    prefs_module.save_auth_session("at", "rt", keep_logged=True)
    data = {"access_token": "at", "refresh_token": "rt", "created_at": old_date, "keep_logged": True}
    Path(path).write_text(json.dumps(data), encoding="utf-8")

    client = DummyClient()
    restored = auth_bootstrap.restore_persisted_auth_session_if_any(client)

    assert restored is False
    assert client.auth.last_session is None


# ============================================================================
# OFFLINE-SUPABASE-UX-001 (Parte D): Novos testes para comportamento offline
# ============================================================================


class TestNetworkErrorDetection:
    """Testes de detecção de erros de rede."""

    def test_is_network_error_detects_oserror(self):
        """Verifica que OSError é detectado como erro de rede."""
        exc = OSError("[Errno 11001] getaddrinfo failed")
        assert auth_bootstrap._is_network_error(exc) is True

    def test_is_network_error_detects_connection_error(self):
        """Verifica que ConnectionError é detectado como erro de rede."""
        exc = ConnectionError("Connection refused")
        assert auth_bootstrap._is_network_error(exc) is True

    def test_is_network_error_detects_timeout_error(self):
        """Verifica que TimeoutError é detectado como erro de rede."""
        exc = TimeoutError("Request timed out")
        assert auth_bootstrap._is_network_error(exc) is True

    def test_is_network_error_detects_urlerror(self):
        """Verifica que URLError é detectado como erro de rede."""
        exc = URLError("Network unreachable")
        assert auth_bootstrap._is_network_error(exc) is True

    def test_is_network_error_detects_by_message(self):
        """Verifica detecção por palavras-chave na mensagem."""
        test_cases = [
            "getaddrinfo failed",
            "connection timeout",
            "network is unreachable",
            "connection refused",
            "connection reset",
            "nodename nor servname provided",
            "temporary failure in name resolution",
        ]

        for msg in test_cases:
            exc = Exception(msg)
            assert auth_bootstrap._is_network_error(exc) is True, f"Failed to detect: {msg}"

    def test_is_network_error_rejects_non_network_errors(self):
        """Verifica que erros não relacionados a rede são rejeitados."""
        test_cases = [
            ValueError("Invalid input"),
            KeyError("Missing key"),
            Exception("Invalid session"),
            RuntimeError("Generic error"),
        ]

        for exc in test_cases:
            assert auth_bootstrap._is_network_error(exc) is False


class TestSessionPersistenceOnNetworkError:
    """Testes de preservação de sessão em erros de rede."""

    def test_restore_session_preserves_on_network_error(self, temp_auth_prefs_dir_bootstrap):
        """Verifica que sessão não é apagada em erro de rede."""
        prefs_module.save_auth_session("at", "rt", keep_logged=True)

        # Cliente que falha com erro de rede
        client = DummyClient()

        def fail_with_network_error(*args):
            raise OSError("[Errno 11001] getaddrinfo failed")

        client.auth.set_session = fail_with_network_error

        # Verifica que auth_session.json existe antes
        session_path = Path(prefs_module._auth_session_path())
        assert session_path.exists()

        restored = auth_bootstrap.restore_persisted_auth_session_if_any(client)

        # Deve retornar False (falha ao restaurar)
        assert restored is False

        # MAS sessão deve ter sido preservada (arquivo ainda existe)
        assert session_path.exists()
        data = json.loads(session_path.read_text(encoding="utf-8"))
        assert data["access_token"] == "at"
        assert data["refresh_token"] == "rt"

    def test_restore_session_clears_on_auth_error(self, temp_auth_prefs_dir_bootstrap):
        """Verifica que sessão É apagada em erro de autenticação (não rede)."""
        prefs_module.save_auth_session("at", "rt", keep_logged=True)

        # Cliente que falha com erro de autenticação
        client = DummyClient()

        def fail_with_auth_error(*args):
            raise Exception("Invalid session")

        client.auth.set_session = fail_with_auth_error

        # Verifica que auth_session.json existe antes
        session_path = Path(prefs_module._auth_session_path())
        assert session_path.exists()

        restored = auth_bootstrap.restore_persisted_auth_session_if_any(client)

        # Deve retornar False (falha ao restaurar)
        assert restored is False

        # Sessão deve ter sido limpa (arquivo não existe mais)
        assert not session_path.exists()


class TestFriendlyErrorMessages:
    """Testes de mensagens amigáveis em authenticate_user."""

    @pytest.mark.parametrize(
        "exception_msg,expected_msg",
        [
            (
                "[Errno 11001] getaddrinfo failed",
                "Sem conexão com a internet. Verifique sua rede e tente novamente.",
            ),
            (
                "nodename nor servname provided",
                "Sem conexão com a internet. Verifique sua rede e tente novamente.",
            ),
            (
                "Temporary failure in name resolution",
                "Sem conexão com a internet. Verifique sua rede e tente novamente.",
            ),
            (
                "Request timeout",
                "Tempo de conexão esgotado. Verifique sua internet e tente novamente.",
            ),
            (
                "Connection timed out",
                "Tempo de conexão esgotado. Verifique sua internet e tente novamente.",
            ),
            (
                "Connection refused",
                "Não foi possível conectar ao servidor. Tente novamente mais tarde.",
            ),
            (
                "Connection reset by peer",
                "Não foi possível conectar ao servidor. Tente novamente mais tarde.",
            ),
        ],
    )
    def test_authenticate_user_friendly_network_errors(self, exception_msg: str, expected_msg: str):
        """Verifica que erros de rede têm mensagens amigáveis."""
        from src.core.auth.auth import authenticate_user

        with patch("src.core.auth.auth.get_supabase") as mock_sb:
            mock_client = MagicMock()
            mock_client.auth.sign_in_with_password.side_effect = Exception(exception_msg)
            mock_sb.return_value = mock_client

            ok, msg = authenticate_user("test@example.com", "password123")

            assert ok is False
            assert msg == expected_msg

    def test_authenticate_user_invalid_credentials(self):
        """Verifica mensagem amigável para credenciais inválidas."""
        from src.core.auth.auth import authenticate_user

        with patch("src.core.auth.auth.get_supabase") as mock_sb:
            mock_client = MagicMock()
            mock_client.auth.sign_in_with_password.side_effect = Exception("Invalid credentials")
            mock_sb.return_value = mock_client

            ok, msg = authenticate_user("test@example.com", "wrongpass")

            assert ok is False
            assert msg == "E-mail ou senha incorretos."
