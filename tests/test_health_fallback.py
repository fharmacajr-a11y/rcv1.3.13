"""
Testes para o fallback de health check quando RPC ping retorna 404.
"""

from unittest.mock import MagicMock, patch


class MockResponse:
    """Mock de resposta HTTP para simular /auth/v1/health."""

    def __init__(self, status_code, json_data):
        self.status_code = status_code
        self._json_data = json_data

    def json(self):
        return self._json_data


def test_health_fallback_on_rpc_404():
    """
    Testa que quando RPC ping retorna 404, o sistema faz fallback para /auth/v1/health.
    """
    from infra.supabase.db_client import _health_check_once

    # Mock do cliente Supabase
    mock_client = MagicMock()

    # Mock de resposta do /auth/v1/health (sucesso)
    mock_health_response = MockResponse(status_code=200, json_data={"version": "2.x.x", "name": "GoTrue", "description": "GoTrue Auth"})

    # Simular RPC ping retornando 404 e /auth/v1/health retornando 200
    with patch("infra.supabase.db_client.exec_postgrest", side_effect=Exception("404 Not Found")):
        with patch("httpx.get", return_value=mock_health_response) as mock_httpx_get:
            with patch.dict("os.environ", {"SUPABASE_URL": "https://test.supabase.co"}):
                # Executar health check
                result = _health_check_once(mock_client)

    # Validações
    assert result is True, "Health check deveria retornar True com fallback bem-sucedido"

    # Verificar que httpx.get foi chamado com URL correta
    mock_httpx_get.assert_called_once_with("https://test.supabase.co/auth/v1/health", timeout=10.0)


def test_health_fallback_continues_on_auth_failure():
    """
    Testa que quando RPC ping retorna 404 e /auth/v1/health também falha,
    o health check prossegue para o próximo fallback (tabela).
    """
    from infra.supabase.db_client import _health_check_once

    mock_client = MagicMock()

    # Simular RPC ping 404 e /auth/v1/health falhando
    with patch("infra.supabase.db_client.exec_postgrest") as mock_exec:
        # Primeira chamada (RPC): 404
        # Segunda chamada (tabela fallback): sucesso
        mock_exec.side_effect = [
            Exception("404 Not Found"),
            MagicMock(),  # fallback de tabela bem-sucedido
        ]

        with patch("httpx.get", side_effect=Exception("Connection timeout")):
            with patch.dict("os.environ", {"SUPABASE_URL": "https://test.supabase.co"}):
                # Simular estrutura de tabela
                mock_table = MagicMock()
                mock_select = MagicMock()
                mock_limit = MagicMock()

                mock_client.table.return_value = mock_table
                mock_table.select.return_value = mock_select
                mock_select.limit.return_value = mock_limit

                _ = _health_check_once(mock_client)  # Test that it doesn't raise

    # Deve ter tentado o fallback de tabela após falha do /auth/v1/health
    assert mock_client.table.called


def test_health_rpc_non_404_error_skips_auth_fallback():
    """
    Testa que erros de RPC diferentes de 404 não acionam o fallback /auth/v1/health.
    """
    from infra.supabase.db_client import _health_check_once

    mock_client = MagicMock()

    # Simular erro de rede (não 404)
    with patch("infra.supabase.db_client.exec_postgrest") as mock_exec:
        mock_exec.side_effect = [
            Exception("Connection refused"),  # RPC falha com erro de rede
            MagicMock(),  # fallback de tabela bem-sucedido
        ]

        with patch("httpx.get") as mock_httpx_get:
            with patch.dict("os.environ", {"SUPABASE_URL": "https://test.supabase.co"}):
                # Simular estrutura de tabela
                mock_table = MagicMock()
                mock_select = MagicMock()
                mock_limit = MagicMock()

                mock_client.table.return_value = mock_table
                mock_table.select.return_value = mock_select
                mock_select.limit.return_value = mock_limit

                _ = _health_check_once(mock_client)  # Test that it doesn't raise

    # Verificar que httpx.get NÃO foi chamado (não entrou no fallback /auth/v1/health)
    mock_httpx_get.assert_not_called()


def test_health_auth_fallback_requires_valid_response():
    """
    Testa que /auth/v1/health com resposta inválida não considera online via esse caminho.
    """
    from infra.supabase.db_client import _health_check_once

    mock_client = MagicMock()

    # Mock de resposta inválida (sem version ou name)
    mock_invalid_response = MockResponse(
        status_code=200,
        json_data={"status": "unknown"},  # sem 'version' ou 'name': 'GoTrue'
    )

    with patch("infra.supabase.db_client.exec_postgrest") as mock_exec:
        # RPC 404, depois tabela bem-sucedida
        mock_exec.side_effect = [Exception("404 Not Found"), MagicMock()]

        with patch("httpx.get", return_value=mock_invalid_response):
            with patch.dict("os.environ", {"SUPABASE_URL": "https://test.supabase.co"}):
                # Simular estrutura de tabela
                mock_table = MagicMock()
                mock_select = MagicMock()
                mock_limit = MagicMock()

                mock_client.table.return_value = mock_table
                mock_table.select.return_value = mock_select
                mock_select.limit.return_value = mock_limit

                _ = _health_check_once(mock_client)  # Test that it doesn't raise

    # Deve ter prosseguido para fallback de tabela
    assert mock_client.table.called


def test_health_auth_fallback_on_401_unauthorized():
    """
    Testa que HTTP 401 (Unauthorized) no /auth/v1/health prossegue para fallback de tabela.
    """
    from infra.supabase.db_client import _health_check_once

    mock_client = MagicMock()

    # Mock de resposta 401 Unauthorized
    mock_unauthorized_response = MockResponse(status_code=401, json_data={"error": "Unauthorized"})

    with patch("infra.supabase.db_client.exec_postgrest") as mock_exec:
        # RPC 404, depois tabela bem-sucedida
        mock_exec.side_effect = [Exception("404 Not Found"), MagicMock()]

        with patch("httpx.get", return_value=mock_unauthorized_response):
            with patch.dict("os.environ", {"SUPABASE_URL": "https://test.supabase.co"}):
                # Simular estrutura de tabela
                mock_table = MagicMock()
                mock_select = MagicMock()
                mock_limit = MagicMock()

                mock_client.table.return_value = mock_table
                mock_table.select.return_value = mock_select
                mock_select.limit.return_value = mock_limit

                _ = _health_check_once(mock_client)  # Test that it doesn't raise

    # Deve ter prosseguido para fallback de tabela após 401
    assert mock_client.table.called


def test_health_auth_fallback_on_403_forbidden():
    """
    Testa que HTTP 403 (Forbidden) no /auth/v1/health prossegue para fallback de tabela.
    """
    from infra.supabase.db_client import _health_check_once

    mock_client = MagicMock()

    # Mock de resposta 403 Forbidden
    mock_forbidden_response = MockResponse(status_code=403, json_data={"error": "Forbidden"})

    with patch("infra.supabase.db_client.exec_postgrest") as mock_exec:
        # RPC 404, depois tabela bem-sucedida
        mock_exec.side_effect = [Exception("404 Not Found"), MagicMock()]

        with patch("httpx.get", return_value=mock_forbidden_response):
            with patch.dict("os.environ", {"SUPABASE_URL": "https://test.supabase.co"}):
                # Simular estrutura de tabela
                mock_table = MagicMock()
                mock_select = MagicMock()
                mock_limit = MagicMock()

                mock_client.table.return_value = mock_table
                mock_table.select.return_value = mock_select
                mock_select.limit.return_value = mock_limit

                _ = _health_check_once(mock_client)  # Test that it doesn't raise

    # Deve ter prosseguido para fallback de tabela após 403
    assert mock_client.table.called


def test_health_auth_fallback_on_timeout():
    """
    Testa que timeout no /auth/v1/health prossegue para fallback de tabela.
    """
    from infra.supabase.db_client import _health_check_once
    import httpx

    mock_client = MagicMock()

    with patch("infra.supabase.db_client.exec_postgrest") as mock_exec:
        # RPC 404, depois tabela bem-sucedida
        mock_exec.side_effect = [Exception("404 Not Found"), MagicMock()]

        # Simular timeout do httpx.get
        with patch("httpx.get", side_effect=httpx.TimeoutException("Request timed out")):
            with patch.dict("os.environ", {"SUPABASE_URL": "https://test.supabase.co"}):
                # Simular estrutura de tabela
                mock_table = MagicMock()
                mock_select = MagicMock()
                mock_limit = MagicMock()

                mock_client.table.return_value = mock_table
                mock_table.select.return_value = mock_select
                mock_select.limit.return_value = mock_limit

                _ = _health_check_once(mock_client)  # Test that it doesn't raise

    # Deve ter prosseguido para fallback de tabela após timeout
    assert mock_client.table.called
