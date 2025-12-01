"""Testes unitários para SessionCache (src/modules/main_window/session_service.py)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.modules.main_window.session_service import SessionCache


@pytest.fixture
def cache() -> SessionCache:
    """
    Cria uma instância limpa de SessionCache para cada teste.

    Garante que cada teste comece com cache vazio, evitando interferência
    de testes anteriores no run global.
    """
    instance = SessionCache()
    instance.clear()  # Garantir que cache está limpo
    return instance


class TestSessionCache:
    """Testes para a classe SessionCache."""

    def test_get_user_caches_result(self, cache: SessionCache):
        """Testa que get_user() cacheia o resultado após primeira consulta."""
        # Mock do supabase.auth.get_user()
        with patch("infra.supabase_client.supabase") as mock_supa:
            mock_user = MagicMock()
            mock_user.id = "user-uuid-123"
            mock_user.email = "test@example.com"
            mock_response = MagicMock(user=mock_user)
            mock_supa.auth.get_user.return_value = mock_response

            # Primeira chamada: deve consultar Supabase
            user1 = cache.get_user()
            assert user1 == {"id": "user-uuid-123", "email": "test@example.com"}
            assert mock_supa.auth.get_user.call_count == 1

            # Segunda chamada: deve retornar do cache (sem nova query)
            user2 = cache.get_user()
            assert user2 == user1
            assert mock_supa.auth.get_user.call_count == 1  # Não chamou novamente

    def test_get_user_returns_none_on_error(self, cache: SessionCache):
        """Testa que get_user() retorna None quando Supabase falha."""
        with patch("infra.supabase_client.supabase") as mock_supa:
            mock_supa.auth.get_user.side_effect = Exception("Supabase error")

            user = cache.get_user()
            assert user is None

    def test_get_role_uses_memberships_and_caches(self, cache: SessionCache):
        """Testa que get_role() consulta memberships e cacheia resultado."""
        with (
            patch("infra.supabase_client.exec_postgrest") as mock_exec,
            patch("infra.supabase_client.supabase") as mock_supa,
        ):
            # Mock de resposta do exec_postgrest
            mock_response = MagicMock()
            mock_response.data = [{"role": "ADMIN"}]
            mock_exec.return_value = mock_response

            # Mock do supabase.table() para garantir que não falha
            mock_supa.table.return_value.select.return_value.eq.return_value.limit.return_value = MagicMock()

            # Primeira chamada
            role1 = cache.get_role("user-uuid")
            assert role1 == "admin"  # Deve estar em lowercase
            assert mock_exec.call_count == 1

            # Segunda chamada: deve retornar do cache
            role2 = cache.get_role("user-uuid")
            assert role2 == "admin"
            assert mock_exec.call_count == 1  # Não chamou novamente

    def test_get_role_returns_user_when_no_data(self, cache: SessionCache):
        """Testa que get_role() retorna 'user' (fallback) quando não há dados."""
        with patch("infra.supabase_client.exec_postgrest") as mock_exec:
            # Mock de resposta vazia
            mock_response = MagicMock()
            mock_response.data = None
            mock_exec.return_value = mock_response

            role = cache.get_role("user-uuid")
            assert role == "user"

    def test_get_role_returns_user_on_error(self, cache: SessionCache):
        """Testa que get_role() retorna 'user' quando há erro na query."""
        with patch("infra.supabase_client.exec_postgrest") as mock_exec:
            mock_exec.side_effect = Exception("Database error")

            role = cache.get_role("user-uuid")
            assert role == "user"

    def test_get_org_id_uses_memberships_and_caches(self, cache: SessionCache):
        """Testa que get_org_id() consulta memberships e cacheia resultado."""
        with (
            patch("infra.supabase_client.exec_postgrest") as mock_exec,
            patch("infra.supabase_client.supabase") as mock_supa,
        ):
            # Mock de resposta com org_id
            mock_response = MagicMock()
            mock_response.data = [{"org_id": "org-uuid-456"}]
            mock_exec.return_value = mock_response

            # Mock do supabase.table() para garantir que não falha
            mock_supa.table.return_value.select.return_value.eq.return_value.limit.return_value = MagicMock()

            # Primeira chamada
            org_id1 = cache.get_org_id("user-uuid")
            assert org_id1 == "org-uuid-456"
            assert mock_exec.call_count == 1

            # Segunda chamada: deve retornar do cache
            org_id2 = cache.get_org_id("user-uuid")
            assert org_id2 == "org-uuid-456"
            assert mock_exec.call_count == 1  # Não chamou novamente

    def test_get_org_id_returns_none_when_no_data(self, cache: SessionCache):
        """Testa que get_org_id() retorna None quando não há org_id."""
        with patch("infra.supabase_client.exec_postgrest") as mock_exec:
            # Mock de resposta sem org_id
            mock_response = MagicMock()
            mock_response.data = [{"org_id": None}]
            mock_exec.return_value = mock_response

            org_id = cache.get_org_id("user-uuid")
            assert org_id is None

    def test_get_org_id_returns_none_on_error(self, cache: SessionCache):
        """Testa que get_org_id() retorna None quando há erro."""
        with patch("infra.supabase_client.exec_postgrest") as mock_exec:
            mock_exec.side_effect = Exception("Database error")

            org_id = cache.get_org_id("user-uuid")
            assert org_id is None

    def test_clear_resets_cached_values(self, cache: SessionCache):
        """Testa que clear() limpa todo o cache."""
        # Preenche cache manualmente
        cache._user_cache = {"id": "test", "email": "test@test.com"}
        cache._role_cache = "admin"
        cache._org_id_cache = "org-test"

        # Limpa cache
        cache.clear()

        # Verifica que tudo voltou para None
        assert cache._user_cache is None
        assert cache._role_cache is None
        assert cache._org_id_cache is None

    def test_get_user_with_org_combines_all_data(self, cache: SessionCache):
        """Testa que get_user_with_org() combina user + role + org_id."""
        with (
            patch("infra.supabase_client.supabase") as mock_supa,
            patch("infra.supabase_client.exec_postgrest") as mock_exec,
        ):
            # Mock de get_user()
            mock_user = MagicMock()
            mock_user.id = "user-uuid"
            mock_user.email = "test@example.com"
            mock_supa.auth.get_user.return_value = MagicMock(user=mock_user)

            # Mock de exec_postgrest para role e org_id
            def mock_exec_side_effect(query):
                # Detecta qual query está sendo chamada
                response = MagicMock()
                if hasattr(query, "_select_params"):
                    # Simples heurística: role ou org_id
                    response.data = [{"role": "ADMIN", "org_id": "org-uuid"}]
                else:
                    response.data = [{"role": "ADMIN", "org_id": "org-uuid"}]
                return response

            mock_exec.side_effect = mock_exec_side_effect

            user_data = cache.get_user_with_org()

            assert user_data is not None
            assert user_data["id"] == "user-uuid"
            assert user_data["email"] == "test@example.com"
            assert user_data["role"] == "admin"  # lowercase
            assert user_data["org_id"] == "org-uuid"

    def test_get_user_with_org_returns_none_when_no_user(self, cache: SessionCache):
        """Testa que get_user_with_org() retorna None quando não há usuário."""
        with patch("infra.supabase_client.supabase") as mock_supa:
            mock_supa.auth.get_user.side_effect = Exception("Auth error")

            user_data = cache.get_user_with_org()
            assert user_data is None

    def test_get_user_returns_none_when_no_uid(self, cache: SessionCache):
        """Testa que get_user() retorna None quando user.id é None."""
        with patch("infra.supabase_client.supabase") as mock_supa:
            # Mock de usuário sem ID
            mock_user = MagicMock()
            mock_user.id = None
            mock_user.email = "test@example.com"
            mock_response = MagicMock(user=mock_user)
            mock_supa.auth.get_user.return_value = mock_response

            user = cache.get_user()
            assert user is None

    def test_get_role_returns_user_when_role_is_none(self, cache: SessionCache):
        """Testa que get_role() retorna 'user' quando role é None."""
        with patch("infra.supabase_client.exec_postgrest") as mock_exec:
            # Mock de resposta com role=None
            mock_response = MagicMock()
            mock_response.data = [{"role": None}]
            mock_exec.return_value = mock_response

            role = cache.get_role("user-uuid")
            assert role == "user"

    def test_get_role_fallback_when_cache_is_none(self, cache: SessionCache):
        """Testa que get_role() retorna 'user' quando cache é None (fallback final)."""
        with patch("infra.supabase_client.exec_postgrest") as mock_exec:
            # Mock de resposta com data vazio
            mock_response = MagicMock()
            mock_response.data = []
            mock_exec.return_value = mock_response

            # Força _role_cache para None
            cache._role_cache = None

            role = cache.get_role("user-uuid")
            assert role == "user"

    def test_get_org_id_returns_none_when_data_is_empty(self, cache: SessionCache):
        """Testa que get_org_id() retorna None quando data está vazio."""
        with patch("infra.supabase_client.exec_postgrest") as mock_exec:
            # Mock de resposta sem dados
            mock_response = MagicMock()
            mock_response.data = []
            mock_exec.return_value = mock_response

            org_id = cache.get_org_id("user-uuid")
            assert org_id is None

    def test_get_user_returns_cached_value_immediately(self, cache: SessionCache):
        """Testa que get_user() retorna valor do cache na primeira verificação."""
        # Preenche cache diretamente
        cache._user_cache = {"id": "cached-id", "email": "cached@test.com"}

        with patch("infra.supabase_client.supabase") as mock_supa:
            # Não deve chamar Supabase
            user = cache.get_user()
            assert user == {"id": "cached-id", "email": "cached@test.com"}
            mock_supa.auth.get_user.assert_not_called()

    def test_get_role_returns_cached_value_immediately(self, cache: SessionCache):
        """Testa que get_role() retorna valor do cache na primeira verificação."""
        # Preenche cache diretamente
        cache._role_cache = "superadmin"

        with patch("infra.supabase_client.exec_postgrest") as mock_exec:
            # Não deve chamar exec_postgrest
            role = cache.get_role("user-uuid")
            assert role == "superadmin"
            mock_exec.assert_not_called()

    def test_get_org_id_returns_cached_value_immediately(self, cache: SessionCache):
        """Testa que get_org_id() retorna valor do cache na primeira verificação."""
        # Preenche cache diretamente
        cache._org_id_cache = "cached-org"

        with patch("infra.supabase_client.exec_postgrest") as mock_exec:
            # Não deve chamar exec_postgrest
            org_id = cache.get_org_id("user-uuid")
            assert org_id == "cached-org"
            mock_exec.assert_not_called()

    def test_get_user_with_email_fallback(self, cache: SessionCache):
        """Testa que get_user() usa fallback quando email é None."""
        with patch("infra.supabase_client.supabase") as mock_supa:
            # Mock de usuário com email None
            mock_user = MagicMock()
            mock_user.id = "user-123"
            mock_user.email = None
            mock_response = MagicMock(user=mock_user)
            mock_supa.auth.get_user.return_value = mock_response

            user = cache.get_user()
            assert user == {"id": "user-123", "email": ""}

    def test_get_user_handles_response_without_user_attribute(self, cache: SessionCache):
        """Testa que get_user() trata resposta sem atributo 'user'."""
        with patch("infra.supabase_client.supabase") as mock_supa:
            # Mock de resposta sem atributo 'user' (usa a própria resposta)
            mock_response = MagicMock()
            mock_response.user = None
            mock_response.id = "direct-user-id"
            mock_response.email = "direct@test.com"
            mock_supa.auth.get_user.return_value = mock_response

            user = cache.get_user()
            assert user == {"id": "direct-user-id", "email": "direct@test.com"}
