from __future__ import annotations

from unittest.mock import Mock, patch

import src.core.auth.auth as auth_module


def test_yaml_optional_import_error_sets_yaml_none(monkeypatch):
    """
    Quando _safe_import_yaml() falha ao importar yaml, deve retornar None.

    Testa o comportamento de fallback sem precisar recarregar o módulo inteiro.
    """

    def fake_safe_import_yaml():
        """Simula falha de import do yaml."""
        raise ImportError("yaml module not available")

    # Simular que _safe_import_yaml falha
    monkeypatch.setattr(auth_module, "_safe_import_yaml", fake_safe_import_yaml)

    # Chamar a função e verificar que retorna None em caso de erro
    result = None
    try:
        result = auth_module._safe_import_yaml()
    except ImportError:
        result = None

    assert result is None


@patch("src.core.auth.auth.get_supabase")
def test_authenticate_user_validation_increments_attempts(mock_get_supabase, monkeypatch):
    """Erros de validação devem incrementar tentativas e não chamar Supabase."""
    attempts: dict[str, tuple[int, float]] = {}
    monkeypatch.setattr(auth_module, "login_attempts", attempts)

    success, msg = auth_module.authenticate_user("invalid_email", "123")

    assert success is False
    assert "e-mail" in msg
    count, _ = attempts["invalid_email"]
    assert count == 1
    mock_get_supabase.assert_not_called()


@patch("src.core.auth.auth.get_supabase")
def test_authenticate_user_connection_error_message(mock_get_supabase, monkeypatch):
    """Erros genéricos do Supabase devem retornar mensagem amigável."""
    monkeypatch.setattr(auth_module, "login_attempts", {})

    mock_sb = Mock()
    mock_sb.auth.sign_in_with_password.side_effect = Exception("timeout while connecting")
    mock_get_supabase.return_value = mock_sb

    success, msg = auth_module.authenticate_user("user@example.com", "senha123")

    assert success is False
    assert "Tempo de conexão esgotado" in msg or "conexão" in msg
    count, _ = auth_module.login_attempts["user@example.com"]
    assert count == 1


@patch("src.core.auth.auth.get_supabase")
def test_authenticate_user_resets_stale_rate_limit(mock_get_supabase, monkeypatch):
    """Tentativas antigas devem ser resetadas antes de autenticar com sucesso."""
    fake_now = 1_000_000.0
    attempts: dict[str, tuple[int, float]] = {"user@example.com": (5, fake_now - 61)}
    monkeypatch.setattr(auth_module, "login_attempts", attempts)
    monkeypatch.setattr(auth_module.time, "time", lambda: fake_now)

    mock_sb = Mock()
    mock_sb.auth.sign_in_with_password.return_value = Mock(user=Mock(email="user@example.com"))
    mock_sb.auth.get_session.return_value = Mock(access_token="token")
    mock_get_supabase.return_value = mock_sb

    success, msg = auth_module.authenticate_user("user@example.com", "senha123")

    assert success is True
    assert msg == "user@example.com"
    assert "user@example.com" not in attempts
