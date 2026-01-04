"""Testes para erros de repositório no módulo de Senhas.

FASE 6 - Cobertura de falhas de repositório e tratamento de exceções.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import types

import pytest

from src.db.domain_types import PasswordRow
from tests.unit.modules.passwords.conftest import make_password_row

from src.modules.passwords import service as passwords_service


# ========================================
# Fixtures
# ========================================


@pytest.fixture
def mock_supabase_user(monkeypatch):
    """Mock do cliente Supabase com usuário válido."""
    import src.infra.supabase_client as supabase_client

    fake_user = types.SimpleNamespace(user=types.SimpleNamespace(id="user-123"))
    fake_supabase = types.SimpleNamespace(auth=types.SimpleNamespace(get_user=lambda: fake_user))
    monkeypatch.setattr(supabase_client, "supabase", fake_supabase)
    return fake_user


# ========================================
# Testes de filter_passwords - casos de borda
# ========================================


class TestFilterPasswordsEdgeCases:
    """Testes de casos de borda para filter_passwords."""

    def test_filter_passwords_empty_list(self) -> None:
        """Deve retornar lista vazia para entrada vazia."""
        empty_passwords: list[PasswordRow] = []
        result = passwords_service.filter_passwords(empty_passwords, "busca", "servico")
        assert result == []

    def test_filter_passwords_none_values_in_data(self) -> None:
        """Deve lidar com valores None nos dados."""
        passwords: list[PasswordRow] = [
            make_password_row(client_name=None, service="SIFAP", username="user1"),
            make_password_row(client_name="Alpha", service=None, username="user2"),
            make_password_row(client_name="Beta", service="GOV.BR", username=None),
        ]

        # Não deve lançar exceção
        result = passwords_service.filter_passwords(passwords, "alpha", None)
        assert len(result) == 1
        assert result[0]["client_name"] == "Alpha"

    def test_filter_passwords_whitespace_search(self) -> None:
        """Busca só com espaços deve ser tratada como vazia."""
        passwords: list[PasswordRow] = [
            make_password_row(client_name="Alpha", service="SIFAP", username="user1"),
        ]

        result = passwords_service.filter_passwords(passwords, "   ", None)
        assert len(result) == 1  # Retorna todos (busca vazia)

    def test_filter_passwords_todos_service_filter(self) -> None:
        """Filtro de serviço "Todos" deve retornar todos."""
        passwords: list[PasswordRow] = [
            make_password_row(client_name="Alpha", service="SIFAP", username="user1"),
            make_password_row(client_name="Beta", service="GOV.BR", username="user2"),
        ]

        result = passwords_service.filter_passwords(passwords, None, "Todos")
        assert len(result) == 2


# ========================================
# Testes de group_passwords_by_client - casos de borda
# ========================================


class TestGroupPasswordsEdgeCases:
    """Testes de casos de borda para group_passwords_by_client."""

    def test_group_passwords_empty_list(self) -> None:
        """Deve retornar lista vazia para entrada vazia."""
        passwords: list[PasswordRow] = []
        result = passwords_service.group_passwords_by_client(passwords)
        assert result == []

    def test_group_passwords_skips_empty_client_id(self) -> None:
        """Deve ignorar senhas sem client_id."""
        passwords: list[PasswordRow] = [
            make_password_row(client_id="", razao_social="Ignorado", service="Test"),
            make_password_row(client_id=None, razao_social="Também ignorado", service="Test"),
            make_password_row(client_id="1", razao_social="Válido", service="SIFAP"),
        ]

        result = passwords_service.group_passwords_by_client(passwords)
        assert len(result) == 1
        assert result[0].client_id == "1"

    def test_group_passwords_coerces_client_external_id(self) -> None:
        """Deve converter client_external_id para int."""
        passwords: list[PasswordRow] = [
            make_password_row(
                client_id="1",
                client_external_id="123",
                razao_social="Alpha",
                cnpj="",
                nome="",
                whatsapp="",
                service="Test",
            ),
        ]

        result = passwords_service.group_passwords_by_client(passwords)
        assert result[0].client_external_id == 123

    def test_group_passwords_handles_invalid_external_id(self) -> None:
        """Deve usar fallback para external_id inválido."""
        passwords: list[PasswordRow] = [
            make_password_row(
                client_id="42",
                client_external_id="nao_numerico",
                razao_social="Alpha",
                cnpj="",
                nome="",
                whatsapp="",
                service="Test",
            ),
        ]

        result = passwords_service.group_passwords_by_client(passwords)
        # Fallback para client_id convertido
        assert result[0].client_external_id == 42

    def test_group_passwords_fallback_to_zero(self) -> None:
        """Deve retornar 0 se nem external_id nem client_id são numéricos."""
        passwords: list[PasswordRow] = [
            make_password_row(
                client_id="uuid-abc",
                client_external_id="invalid",
                razao_social="Alpha",
                cnpj="",
                nome="",
                whatsapp="",
                service="Test",
            ),
        ]

        result = passwords_service.group_passwords_by_client(passwords)
        assert result[0].client_external_id == 0


# ========================================
# Testes de resolve_user_context - erros
# ========================================


class TestResolveUserContextErrors:
    """Testes de erros em resolve_user_context."""

    def test_resolve_context_supabase_import_error(self, monkeypatch) -> None:
        """Deve lançar RuntimeError se import do Supabase falhar."""
        # Simular falha no import
        original_import = __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__

        def failing_import(name, *args, **kwargs):
            if "supabase_client" in name:
                raise ImportError("Supabase not available")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=failing_import):
            # Precisa limpar cache de módulos para forçar reimport
            with pytest.raises(RuntimeError, match="Supabase indisponível|Usuário"):
                passwords_service.resolve_user_context(MagicMock())

    def test_resolve_context_no_org_found(self, mock_supabase_user, monkeypatch) -> None:
        """Deve lançar RuntimeError se org_id não for encontrado."""

        class FakeWindowNoOrg:
            def _get_org_id_cached(self, user_id):
                return None

        # Mock fallback também falha
        monkeypatch.setattr(
            "src.modules.clientes.service._resolve_current_org_id",
            lambda: None,
            raising=False,
        )

        with pytest.raises(RuntimeError, match="organização"):
            passwords_service.resolve_user_context(FakeWindowNoOrg())

    def test_resolve_context_dict_user_object(self, monkeypatch) -> None:
        """Deve extrair user_id de objeto dict."""
        import src.infra.supabase_client as supabase_client

        # User como dict
        fake_user = {"id": "user-dict-123", "email": "test@test.com"}
        fake_response = types.SimpleNamespace(user=fake_user)
        fake_supabase = types.SimpleNamespace(auth=types.SimpleNamespace(get_user=lambda: fake_response))
        monkeypatch.setattr(supabase_client, "supabase", fake_supabase)

        class FakeWindow:
            def _get_org_id_cached(self, user_id):
                return "org-123"

        ctx = passwords_service.resolve_user_context(FakeWindow())
        assert ctx.user_id == "user-dict-123"

    def test_resolve_context_user_with_uid_fallback(self, monkeypatch) -> None:
        """Deve usar 'uid' se 'id' não existir no dict."""
        import src.infra.supabase_client as supabase_client

        # User como dict com uid ao invés de id
        fake_user = {"uid": "user-uid-456"}
        fake_response = types.SimpleNamespace(user=fake_user)
        fake_supabase = types.SimpleNamespace(auth=types.SimpleNamespace(get_user=lambda: fake_response))
        monkeypatch.setattr(supabase_client, "supabase", fake_supabase)

        class FakeWindow:
            def _get_org_id_cached(self, user_id):
                return "org-123"

        ctx = passwords_service.resolve_user_context(FakeWindow())
        assert ctx.user_id == "user-uid-456"


# ========================================
# Testes de ClientPasswordsSummary
# ========================================


class TestClientPasswordsSummary:
    """Testes para ClientPasswordsSummary dataclass."""

    def test_display_name_with_id_and_razao(self) -> None:
        """display_name deve mostrar ID e razão social."""
        summary = passwords_service.ClientPasswordsSummary(
            client_id="1",
            client_external_id=100,
            razao_social="Alpha Corp",
            cnpj="11.111.111/0001-11",
            contato_nome="João",
            whatsapp="11999998888",
            passwords_count=3,
            services=["SIFAP", "GOV.BR"],
        )

        assert "ID 100" in summary.display_name
        assert "Alpha Corp" in summary.display_name

    def test_display_name_only_id(self) -> None:
        """display_name só com ID se razão social vazia."""
        summary = passwords_service.ClientPasswordsSummary(
            client_id="1",
            client_external_id=100,
            razao_social="",
            cnpj="",
            contato_nome="",
            whatsapp="",
            passwords_count=1,
            services=[],
        )

        assert summary.display_name == "ID 100"

    def test_display_name_only_razao(self) -> None:
        """display_name só com razão se external_id é 0."""
        summary = passwords_service.ClientPasswordsSummary(
            client_id="uuid-abc",
            client_external_id=0,
            razao_social="Beta Corp",
            cnpj="",
            contato_nome="",
            whatsapp="",
            passwords_count=1,
            services=[],
        )

        assert summary.display_name == "Beta Corp"

    def test_display_name_fallback_to_client_id(self) -> None:
        """display_name deve usar client_id se nada mais disponível."""
        summary = passwords_service.ClientPasswordsSummary(
            client_id="fallback-id",
            client_external_id=0,
            razao_social="",
            cnpj="",
            contato_nome="",
            whatsapp="",
            passwords_count=1,
            services=[],
        )

        assert summary.display_name == "fallback-id"


# ========================================
# Testes de reexports do repositório
# ========================================


class TestServiceReexports:
    """Testes para garantir que reexports funcionam."""

    def test_get_passwords_is_exported(self) -> None:
        """get_passwords deve estar disponível no service."""
        assert hasattr(passwords_service, "get_passwords")
        assert callable(passwords_service.get_passwords)

    def test_create_password_is_exported(self) -> None:
        """create_password deve estar disponível no service."""
        assert hasattr(passwords_service, "create_password")
        assert callable(passwords_service.create_password)

    def test_update_password_is_exported(self) -> None:
        """update_password_by_id deve estar disponível no service."""
        assert hasattr(passwords_service, "update_password_by_id")
        assert callable(passwords_service.update_password_by_id)

    def test_delete_password_is_exported(self) -> None:
        """delete_password_by_id deve estar disponível no service."""
        assert hasattr(passwords_service, "delete_password_by_id")
        assert callable(passwords_service.delete_password_by_id)

    def test_delete_all_for_client_is_exported(self) -> None:
        """delete_all_passwords_for_client deve estar disponível no service."""
        assert hasattr(passwords_service, "delete_all_passwords_for_client")
        assert callable(passwords_service.delete_all_passwords_for_client)

    def test_find_duplicate_is_exported(self) -> None:
        """find_duplicate_password_by_service deve estar disponível no service."""
        assert hasattr(passwords_service, "find_duplicate_password_by_service")
        assert callable(passwords_service.find_duplicate_password_by_service)
