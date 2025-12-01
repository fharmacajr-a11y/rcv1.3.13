"""
TEST-001 Fase 27 – Cobertura de src/helpers/auth_utils.py

Objetivo:
    Aumentar cobertura de auth_utils.py para ≥95%, testando:
    - current_user_id(): diversos formatos de resposta, exceções
    - resolve_org_id(): com/sem user, fallback env, erros

Escopo:
    - Não altera lógica de produção
    - Foca em branches não cobertos
    - Usa mocks para isolar dependências externas
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.helpers.auth_utils import current_user_id, resolve_org_id


# ============================================================================
# TEST GROUP: current_user_id()
# ============================================================================


class TestCurrentUserId:
    """Testes para current_user_id() - retorna ID do usuário ou None."""

    def test_current_user_id_valid_object_format(self):
        """Cenário: auth.get_user() retorna objeto com user.id válido."""
        mock_user = MagicMock()
        mock_user.id = "user-uuid-12345"

        mock_resp = MagicMock()
        mock_resp.user = mock_user

        with patch("src.helpers.auth_utils.supabase") as mock_sb:
            mock_sb.auth.get_user.return_value = mock_resp
            result = current_user_id()

        assert result == "user-uuid-12345"

    def test_current_user_id_no_user_attribute(self):
        """Cenário: resposta sem atributo user (None)."""
        mock_resp = MagicMock()
        mock_resp.user = None

        with patch("src.helpers.auth_utils.supabase") as mock_sb:
            mock_sb.auth.get_user.return_value = mock_resp
            result = current_user_id()

        assert result is None

    def test_current_user_id_user_without_id(self):
        """Cenário: user existe mas não tem atributo id."""
        mock_user = MagicMock()
        del mock_user.id  # Remove atributo id

        mock_resp = MagicMock()
        mock_resp.user = mock_user

        with patch("src.helpers.auth_utils.supabase") as mock_sb:
            mock_sb.auth.get_user.return_value = mock_resp
            # Simula getattr retornando None
            with patch("src.helpers.auth_utils.getattr", side_effect=lambda obj, attr, default=None: None):
                result = current_user_id()

        assert result is None

    def test_current_user_id_dict_format_user_key(self):
        """Cenário: resposta em formato dict com chave 'user'."""
        mock_resp = {"user": {"id": "dict-user-789"}}

        with patch("src.helpers.auth_utils.supabase") as mock_sb:
            mock_sb.auth.get_user.return_value = mock_resp
            result = current_user_id()

        assert result == "dict-user-789"

    def test_current_user_id_dict_format_data_user_key(self):
        """Cenário: resposta em formato dict com chave 'data' -> 'user'."""
        mock_resp = {"data": {"user": {"id": "nested-user-456"}}}

        with patch("src.helpers.auth_utils.supabase") as mock_sb:
            mock_sb.auth.get_user.return_value = mock_resp
            result = current_user_id()

        assert result == "nested-user-456"

    def test_current_user_id_dict_format_uid_key(self):
        """Cenário: resposta dict com chave 'uid' em vez de 'id'."""
        mock_resp = {"user": {"uid": "user-uid-999"}}

        with patch("src.helpers.auth_utils.supabase") as mock_sb:
            mock_sb.auth.get_user.return_value = mock_resp
            result = current_user_id()

        assert result == "user-uid-999"

    def test_current_user_id_exception_handling(self):
        """Cenário: exceção durante get_user() deve retornar None."""
        with patch("src.helpers.auth_utils.supabase") as mock_sb:
            mock_sb.auth.get_user.side_effect = Exception("Network error")
            result = current_user_id()

        assert result is None

    def test_current_user_id_empty_dict(self):
        """Cenário: resposta dict vazio."""
        mock_resp = {}

        with patch("src.helpers.auth_utils.supabase") as mock_sb:
            mock_sb.auth.get_user.return_value = mock_resp
            result = current_user_id()

        assert result is None


# ============================================================================
# TEST GROUP: resolve_org_id()
# ============================================================================


class TestResolveOrgId:
    """Testes para resolve_org_id() - resolve ID da organização."""

    def test_resolve_org_id_from_memberships_success(self):
        """Cenário: org_id resolvido via tabela memberships."""
        mock_data = [{"org_id": "org-abc-123"}]
        mock_result = MagicMock()
        mock_result.data = mock_data

        with patch("src.helpers.auth_utils.current_user_id", return_value="user-123"):
            with patch("src.helpers.auth_utils.exec_postgrest", return_value=mock_result):
                result = resolve_org_id()

        assert result == "org-abc-123"

    def test_resolve_org_id_memberships_empty_fallback_env(self, monkeypatch):
        """Cenário: memberships vazio, usa fallback de env var."""
        monkeypatch.setenv("SUPABASE_DEFAULT_ORG", "org-env-456")

        mock_result = MagicMock()
        mock_result.data = []

        with patch("src.helpers.auth_utils.current_user_id", return_value="user-123"):
            with patch("src.helpers.auth_utils.exec_postgrest", return_value=mock_result):
                result = resolve_org_id()

        assert result == "org-env-456"

    def test_resolve_org_id_no_user_with_env_fallback(self, monkeypatch):
        """Cenário: usuário não autenticado mas env var definida."""
        monkeypatch.setenv("SUPABASE_DEFAULT_ORG", "org-fallback-789")

        with patch("src.helpers.auth_utils.current_user_id", return_value=None):
            result = resolve_org_id()

        assert result == "org-fallback-789"

    def test_resolve_org_id_no_user_no_env_raises(self, monkeypatch):
        """Cenário: sem user e sem env var deve levantar RuntimeError."""
        monkeypatch.delenv("SUPABASE_DEFAULT_ORG", raising=False)

        with patch("src.helpers.auth_utils.current_user_id", return_value=None):
            with pytest.raises(RuntimeError, match="Usuário não autenticado"):
                resolve_org_id()

    def test_resolve_org_id_memberships_exception_fallback_env(self, monkeypatch):
        """Cenário: exceção ao consultar memberships, usa env fallback."""
        monkeypatch.setenv("SUPABASE_DEFAULT_ORG", "org-exception-rescue")

        with patch("src.helpers.auth_utils.current_user_id", return_value="user-123"):
            with patch("src.helpers.auth_utils.exec_postgrest", side_effect=Exception("DB error")):
                result = resolve_org_id()

        assert result == "org-exception-rescue"

    def test_resolve_org_id_memberships_exception_no_fallback_raises(self, monkeypatch):
        """Cenário: exceção em memberships e sem env fallback deve levantar RuntimeError."""
        monkeypatch.delenv("SUPABASE_DEFAULT_ORG", raising=False)

        with patch("src.helpers.auth_utils.current_user_id", return_value="user-123"):
            with patch("src.helpers.auth_utils.exec_postgrest", side_effect=Exception("DB error")):
                with pytest.raises(RuntimeError, match="Não foi possível resolver"):
                    resolve_org_id()

    def test_resolve_org_id_memberships_no_data_attribute(self, monkeypatch):
        """Cenário: resultado sem atributo 'data', usa fallback env."""
        monkeypatch.setenv("SUPABASE_DEFAULT_ORG", "org-no-data-attr")

        mock_result = MagicMock()
        del mock_result.data  # Remove atributo data

        with patch("src.helpers.auth_utils.current_user_id", return_value="user-123"):
            with patch("src.helpers.auth_utils.exec_postgrest", return_value=mock_result):
                with patch("src.helpers.auth_utils.getattr", return_value=None):
                    result = resolve_org_id()

        assert result == "org-no-data-attr"

    def test_resolve_org_id_env_with_whitespace(self, monkeypatch):
        """Cenário: env var com espaços deve ser tratada corretamente."""
        monkeypatch.setenv("SUPABASE_DEFAULT_ORG", "  org-trimmed-123  ")

        with patch("src.helpers.auth_utils.current_user_id", return_value=None):
            result = resolve_org_id()

        assert result == "org-trimmed-123"

    def test_resolve_org_id_empty_env_string_no_user_raises(self, monkeypatch):
        """Cenário: env var vazia (após strip) e sem user deve levantar erro."""
        monkeypatch.setenv("SUPABASE_DEFAULT_ORG", "   ")

        with patch("src.helpers.auth_utils.current_user_id", return_value=None):
            with pytest.raises(RuntimeError, match="Usuário não autenticado"):
                resolve_org_id()


# ============================================================================
# TEST GROUP: Integração Leve
# ============================================================================


class TestAuthUtilsIntegration:
    """Testes de integração leve entre as funções."""

    def test_resolve_org_id_calls_current_user_id(self, monkeypatch):
        """Verifica que resolve_org_id() usa current_user_id() internamente."""
        monkeypatch.setenv("SUPABASE_DEFAULT_ORG", "org-integration-test")

        with patch("src.helpers.auth_utils.current_user_id") as mock_current:
            mock_current.return_value = None
            result = resolve_org_id()

        mock_current.assert_called_once()
        assert result == "org-integration-test"

    def test_full_flow_authenticated_user_with_membership(self):
        """Fluxo completo: user autenticado → org via memberships."""
        mock_user = MagicMock()
        mock_user.id = "full-flow-user"

        mock_auth_resp = MagicMock()
        mock_auth_resp.user = mock_user

        mock_membership_data = [{"org_id": "full-flow-org"}]
        mock_membership_resp = MagicMock()
        mock_membership_resp.data = mock_membership_data

        with patch("src.helpers.auth_utils.supabase") as mock_sb:
            mock_sb.auth.get_user.return_value = mock_auth_resp
            with patch("src.helpers.auth_utils.exec_postgrest", return_value=mock_membership_resp):
                # Primeiro chama current_user_id indiretamente via resolve_org_id
                org_id = resolve_org_id()

        assert org_id == "full-flow-org"
