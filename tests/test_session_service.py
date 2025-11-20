"""Testes unitários para SessionCache (src/modules/main_window/session_service.py)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


from src.modules.main_window.session_service import SessionCache


class TestSessionCache:
    """Testes para a classe SessionCache."""

    def test_get_user_caches_result(self):
        """Testa que get_user() cacheia o resultado após primeira consulta."""
        cache = SessionCache()

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

    def test_get_user_returns_none_on_error(self):
        """Testa que get_user() retorna None quando Supabase falha."""
        cache = SessionCache()

        with patch("infra.supabase_client.supabase") as mock_supa:
            mock_supa.auth.get_user.side_effect = Exception("Supabase error")

            user = cache.get_user()
            assert user is None

    def test_get_role_uses_memberships_and_caches(self):
        """Testa que get_role() consulta memberships e cacheia resultado."""
        cache = SessionCache()

        with patch("infra.supabase_client.exec_postgrest") as mock_exec:
            # Mock de resposta do exec_postgrest
            mock_response = MagicMock()
            mock_response.data = [{"role": "ADMIN"}]
            mock_exec.return_value = mock_response

            # Primeira chamada
            role1 = cache.get_role("user-uuid")
            assert role1 == "admin"  # Deve estar em lowercase
            assert mock_exec.call_count == 1

            # Segunda chamada: deve retornar do cache
            role2 = cache.get_role("user-uuid")
            assert role2 == "admin"
            assert mock_exec.call_count == 1  # Não chamou novamente

    def test_get_role_returns_user_when_no_data(self):
        """Testa que get_role() retorna 'user' (fallback) quando não há dados."""
        cache = SessionCache()

        with patch("infra.supabase_client.exec_postgrest") as mock_exec:
            # Mock de resposta vazia
            mock_response = MagicMock()
            mock_response.data = None
            mock_exec.return_value = mock_response

            role = cache.get_role("user-uuid")
            assert role == "user"

    def test_get_role_returns_user_on_error(self):
        """Testa que get_role() retorna 'user' quando há erro na query."""
        cache = SessionCache()

        with patch("infra.supabase_client.exec_postgrest") as mock_exec:
            mock_exec.side_effect = Exception("Database error")

            role = cache.get_role("user-uuid")
            assert role == "user"

    def test_get_org_id_uses_memberships_and_caches(self):
        """Testa que get_org_id() consulta memberships e cacheia resultado."""
        cache = SessionCache()

        with patch("infra.supabase_client.exec_postgrest") as mock_exec:
            # Mock de resposta com org_id
            mock_response = MagicMock()
            mock_response.data = [{"org_id": "org-uuid-456"}]
            mock_exec.return_value = mock_response

            # Primeira chamada
            org_id1 = cache.get_org_id("user-uuid")
            assert org_id1 == "org-uuid-456"
            assert mock_exec.call_count == 1

            # Segunda chamada: deve retornar do cache
            org_id2 = cache.get_org_id("user-uuid")
            assert org_id2 == "org-uuid-456"
            assert mock_exec.call_count == 1  # Não chamou novamente

    def test_get_org_id_returns_none_when_no_data(self):
        """Testa que get_org_id() retorna None quando não há org_id."""
        cache = SessionCache()

        with patch("infra.supabase_client.exec_postgrest") as mock_exec:
            # Mock de resposta sem org_id
            mock_response = MagicMock()
            mock_response.data = [{"org_id": None}]
            mock_exec.return_value = mock_response

            org_id = cache.get_org_id("user-uuid")
            assert org_id is None

    def test_get_org_id_returns_none_on_error(self):
        """Testa que get_org_id() retorna None quando há erro."""
        cache = SessionCache()

        with patch("infra.supabase_client.exec_postgrest") as mock_exec:
            mock_exec.side_effect = Exception("Database error")

            org_id = cache.get_org_id("user-uuid")
            assert org_id is None

    def test_clear_resets_cached_values(self):
        """Testa que clear() limpa todo o cache."""
        cache = SessionCache()

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

    def test_get_user_with_org_combines_all_data(self):
        """Testa que get_user_with_org() combina user + role + org_id."""
        cache = SessionCache()

        with patch("infra.supabase_client.supabase") as mock_supa, patch("infra.supabase_client.exec_postgrest") as mock_exec:
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

    def test_get_user_with_org_returns_none_when_no_user(self):
        """Testa que get_user_with_org() retorna None quando não há usuário."""
        cache = SessionCache()

        with patch("infra.supabase_client.supabase") as mock_supa:
            mock_supa.auth.get_user.side_effect = Exception("Auth error")

            user_data = cache.get_user_with_org()
            assert user_data is None
