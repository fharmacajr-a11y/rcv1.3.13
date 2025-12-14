"""
Testes de Integração do Módulo Auditoria (Microfase 10).

Foco: Validar fluxos completos atravessando as camadas:
Controller → Service → Repository → Storage

Estratégia:
- Usar implementações reais de Service, Repository, Storage
- Mockar apenas dependências externas (Supabase client, file system)
- 10-15 testes cirúrgicos cobrindo fluxos principais + erros de infraestrutura

Arquitetura testada:
┌──────────────┐
│   Service    │  ← Entry point dos fluxos
└──────┬───────┘
       │
       ├─→ Repository (acesso a dados)
       │
       └─→ Storage (arquivos)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.modules.auditoria import service
from src.modules.auditoria.service import (
    AuditoriaOfflineError,
    AuditoriaServiceError,
)


# --- Fixtures ---


@pytest.fixture
def mock_supabase():
    """Cria um cliente Supabase fake para testes de integração."""
    mock_sb = MagicMock()

    # Mock de autenticação
    mock_auth = MagicMock()
    mock_user_response = MagicMock()
    mock_user_obj = MagicMock()
    mock_user_obj.id = "test-user-123"
    mock_user_response.user = mock_user_obj
    mock_auth.get_user.return_value = mock_user_response
    mock_sb.auth = mock_auth

    # Mock de storage
    mock_storage = MagicMock()
    mock_sb.storage = mock_storage

    return mock_sb


@pytest.fixture
def mock_table_clients(mock_supabase):
    """Configura mock de tabela clients."""

    def configure_clients_data(clients_data):
        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_order = MagicMock()
        mock_execute = MagicMock()

        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.order.return_value = mock_order
        mock_execute.data = clients_data
        mock_order.execute.return_value = mock_execute

    return configure_clients_data


@pytest.fixture
def mock_table_auditorias(mock_supabase):
    """Configura mock de tabela auditorias."""

    def configure_auditorias_data(auditorias_data):
        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_order = MagicMock()
        mock_execute = MagicMock()

        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.order.return_value = mock_order
        mock_execute.data = auditorias_data
        mock_order.execute.return_value = mock_execute

    return configure_auditorias_data


@pytest.fixture
def mock_table_memberships(mock_supabase):
    """Configura mock de tabela memberships."""

    def configure_membership_data(org_id):
        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_eq = MagicMock()
        mock_limit = MagicMock()
        mock_execute = MagicMock()

        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq
        mock_eq.limit.return_value = mock_limit
        mock_execute.data = [{"org_id": org_id}]
        mock_limit.execute.return_value = mock_execute

    return configure_membership_data


@pytest.fixture(autouse=True)
def reset_service_cache():
    """Reseta cache de org_id antes de cada teste."""
    service.reset_org_cache()
    yield
    service.reset_org_cache()


# --- Testes de Fluxo: Clientes ---


def test_listar_clientes_fluxo_completo(mock_supabase, mock_table_clients):
    """Testa fluxo completo de listagem de clientes (Service → Repository)."""
    # Arrange
    mock_table_clients(
        [
            {"id": 1, "razao_social": "Empresa A", "cnpj": "12345678000190"},
            {"id": 2, "razao_social": "Empresa B", "cnpj": "98765432000100"},
        ]
    )

    with patch("src.modules.auditoria.service.get_supabase", return_value=mock_supabase):
        # Act
        clientes = service.fetch_clients()

        # Assert
        assert len(clientes) == 2
        assert clientes[0]["razao_social"] == "Empresa A"
        assert clientes[1]["id"] == 2
        mock_supabase.table.assert_called_with("clients")


def test_listar_clientes_quando_supabase_offline_lanca_erro():
    """Testa que offline lança AuditoriaOfflineError."""
    # Arrange
    with patch("src.modules.auditoria.service.get_supabase", return_value=None):
        # Act & Assert
        with pytest.raises(AuditoriaOfflineError, match="Supabase client is not available"):
            service.fetch_clients()


# --- Testes de Fluxo: Auditorias (CRUD Completo) ---


def test_listar_auditorias_fluxo_completo(mock_supabase, mock_table_auditorias):
    """Testa fluxo completo de listagem de auditorias (Service → Repository)."""
    # Arrange
    mock_table_auditorias(
        [
            {
                "id": 1,
                "status": "em_andamento",
                "cliente_id": 10,
                "created_at": "2024-01-01",
                "updated_at": "2024-01-02",
            },
            {
                "id": 2,
                "status": "pendente",
                "cliente_id": 20,
                "created_at": "2024-01-03",
                "updated_at": "2024-01-04",
            },
        ]
    )

    with patch("src.modules.auditoria.service.get_supabase", return_value=mock_supabase):
        # Act
        auditorias = service.list_auditorias()

        # Assert
        assert len(auditorias) == 2
        assert auditorias[0]["status"] == "em_andamento"
        assert auditorias[1]["cliente_id"] == 20


def test_criar_auditoria_simples_fluxo_completo(mock_supabase):
    """Testa criação de auditoria (Service → Repository → DB mock)."""
    # Arrange
    mock_table = MagicMock()
    mock_insert = MagicMock()
    mock_execute = MagicMock()

    mock_supabase.table.return_value = mock_table
    mock_table.insert.return_value = mock_insert
    mock_execute.data = [{"id": 999, "status": "em_andamento", "cliente_id": 100}]
    mock_insert.execute.return_value = mock_execute

    with patch("src.modules.auditoria.service.get_supabase", return_value=mock_supabase):
        # Act
        auditoria = service.start_auditoria(cliente_id=100)

        # Assert
        assert auditoria["id"] == 999
        assert auditoria["status"] == "em_andamento"
        assert auditoria["cliente_id"] == 100
        mock_table.insert.assert_called_once_with({"cliente_id": 100, "status": "em_andamento"})


def test_criar_auditoria_com_status_customizado(mock_supabase):
    """Testa criação de auditoria com status customizado."""
    # Arrange
    mock_table = MagicMock()
    mock_insert = MagicMock()
    mock_execute = MagicMock()

    mock_supabase.table.return_value = mock_table
    mock_table.insert.return_value = mock_insert
    mock_execute.data = [{"id": 888, "status": "pendente", "cliente_id": 50}]
    mock_insert.execute.return_value = mock_execute

    with patch("src.modules.auditoria.service.get_supabase", return_value=mock_supabase):
        # Act
        auditoria = service.start_auditoria(cliente_id=50, status="pendente")

        # Assert
        assert auditoria["status"] == "pendente"
        mock_table.insert.assert_called_once_with({"cliente_id": 50, "status": "pendente"})


def test_atualizar_status_auditoria_fluxo_completo(mock_supabase):
    """Testa atualização de status (Service → Repository)."""
    # Arrange
    mock_table = MagicMock()
    mock_update = MagicMock()
    mock_eq = MagicMock()
    mock_select = MagicMock()
    mock_execute = MagicMock()

    mock_supabase.table.return_value = mock_table
    mock_table.update.return_value = mock_update
    mock_update.eq.return_value = mock_eq
    mock_eq.select.return_value = mock_select
    mock_execute.data = [{"status": "finalizado", "updated_at": "2024-01-10T12:00:00"}]
    mock_select.execute.return_value = mock_execute

    with patch("src.modules.auditoria.service.get_supabase", return_value=mock_supabase):
        # Act
        result = service.update_auditoria_status(auditoria_id="123", status="finalizado")

        # Assert
        assert result["status"] == "finalizado"
        mock_table.update.assert_called_once_with({"status": "finalizado"})
        mock_update.eq.assert_called_once_with("id", "123")


def test_atualizar_status_auditoria_inexistente_lanca_erro(mock_supabase):
    """Testa que atualizar auditoria inexistente lança erro."""
    # Arrange
    mock_table = MagicMock()
    mock_update = MagicMock()
    mock_eq = MagicMock()
    mock_select = MagicMock()
    mock_execute = MagicMock()

    mock_supabase.table.return_value = mock_table
    mock_table.update.return_value = mock_update
    mock_update.eq.return_value = mock_eq
    mock_eq.select.return_value = mock_select
    mock_execute.data = []  # Sem dados = não encontrado
    mock_select.execute.return_value = mock_execute

    with patch("src.modules.auditoria.service.get_supabase", return_value=mock_supabase):
        # Act & Assert
        with pytest.raises(AuditoriaServiceError, match="Auditoria nao encontrada para atualizacao"):
            service.update_auditoria_status(auditoria_id="999", status="finalizado")


def test_excluir_auditorias_em_batch_fluxo_completo(mock_supabase):
    """Testa exclusão de múltiplas auditorias (Service → Repository)."""
    # Arrange
    mock_table = MagicMock()
    mock_delete = MagicMock()
    mock_in = MagicMock()
    mock_execute = MagicMock()

    mock_supabase.table.return_value = mock_table
    mock_table.delete.return_value = mock_delete
    mock_delete.in_.return_value = mock_in
    mock_in.execute.return_value = mock_execute

    with patch("src.modules.auditoria.service.get_supabase", return_value=mock_supabase):
        # Act
        service.delete_auditorias(["1", "2", "3"])

        # Assert
        mock_table.delete.assert_called_once()
        mock_delete.in_.assert_called_once_with("id", ["1", "2", "3"])


def test_excluir_auditorias_ignora_ids_invalidos(mock_supabase):
    """Testa que delete_auditorias filtra IDs None/vazios."""
    # Arrange
    mock_table = MagicMock()
    mock_delete = MagicMock()
    mock_in = MagicMock()
    mock_execute = MagicMock()

    mock_supabase.table.return_value = mock_table
    mock_table.delete.return_value = mock_delete
    mock_delete.in_.return_value = mock_in
    mock_in.execute.return_value = mock_execute

    with patch("src.modules.auditoria.service.get_supabase", return_value=mock_supabase):
        # Act
        service.delete_auditorias([None, "", "1", "  ", "2", None])

        # Assert
        # Apenas "1" e "2" devem ser passados
        mock_delete.in_.assert_called_once_with("id", ["1", "2"])


def test_excluir_auditorias_lista_vazia_nao_chama_repository(mock_supabase):
    """Testa que lista vazia não chama repository."""
    with patch("src.modules.auditoria.service.get_supabase", return_value=mock_supabase):
        # Act
        service.delete_auditorias([])

        # Assert
        mock_supabase.table.assert_not_called()


# --- Testes de Fluxo: Storage e Organização ---


def test_obter_org_id_fluxo_completo(mock_supabase, mock_table_memberships):
    """Testa fluxo completo de obtenção de org_id (Service → Repository)."""
    # Arrange
    mock_table_memberships("org-xyz-789")

    with patch("src.modules.auditoria.service.get_supabase", return_value=mock_supabase):
        # Act
        org_id = service.get_current_org_id()

        # Assert
        assert org_id == "org-xyz-789"
        mock_supabase.auth.get_user.assert_called_once()


def test_obter_org_id_usa_cache_na_segunda_chamada(mock_supabase, mock_table_memberships):
    """Testa que org_id usa cache em memória."""
    # Arrange
    mock_table_memberships("org-cached-123")

    with patch("src.modules.auditoria.service.get_supabase", return_value=mock_supabase):
        # Act
        org_id_1 = service.get_current_org_id()
        org_id_2 = service.get_current_org_id()  # Segunda chamada

        # Assert
        assert org_id_1 == org_id_2 == "org-cached-123"
        # Auth deve ser chamado apenas uma vez (cache)
        assert mock_supabase.auth.get_user.call_count == 1


def test_obter_org_id_force_refresh_ignora_cache(mock_supabase, mock_table_memberships):
    """Testa que force_refresh=True ignora cache."""
    # Arrange
    mock_table_memberships("org-refreshed-456")

    with patch("src.modules.auditoria.service.get_supabase", return_value=mock_supabase):
        # Act
        org_id_1 = service.get_current_org_id()
        org_id_2 = service.get_current_org_id(force_refresh=True)

        # Assert
        assert org_id_1 == org_id_2 == "org-refreshed-456"
        # Auth deve ser chamado duas vezes (refresh)
        assert mock_supabase.auth.get_user.call_count == 2


def test_criar_contexto_storage_fluxo_completo(mock_supabase, mock_table_memberships):
    """Testa criação de contexto de storage (Service → Storage)."""
    # Arrange
    mock_table_memberships("org-storage-999")

    with patch("src.modules.auditoria.service.get_supabase", return_value=mock_supabase):
        # Act
        context = service.get_storage_context(client_id=100)

        # Assert
        assert context.org_id == "org-storage-999"
        assert "GERAL/Auditoria" in context.auditoria_prefix
        assert context.bucket  # Bucket configurado


# --- Testes de Erro de Infraestrutura ---


def test_erro_repository_propagado_como_service_error(mock_supabase):
    """Testa que erro no repository é encapsulado em AuditoriaServiceError."""
    # Arrange
    mock_table = MagicMock()
    mock_select = MagicMock()

    mock_supabase.table.return_value = mock_table
    mock_table.select.return_value = mock_select
    mock_select.order.side_effect = RuntimeError("DB connection failed")

    with patch("src.modules.auditoria.service.get_supabase", return_value=mock_supabase):
        # Act & Assert
        with pytest.raises(AuditoriaServiceError, match="Falha ao carregar clientes"):
            service.fetch_clients()


def test_erro_insert_auditoria_propagado_como_service_error(mock_supabase):
    """Testa que erro no insert é encapsulado."""
    # Arrange
    mock_table = MagicMock()
    mock_insert = MagicMock()

    mock_supabase.table.return_value = mock_table
    mock_table.insert.return_value = mock_insert
    mock_insert.execute.side_effect = Exception("Constraint violation")

    with patch("src.modules.auditoria.service.get_supabase", return_value=mock_supabase):
        # Act & Assert
        with pytest.raises(AuditoriaServiceError, match="Nao foi possivel iniciar auditoria"):
            service.start_auditoria(cliente_id=100)


def test_erro_autenticacao_propagado_como_service_error(mock_supabase):
    """Testa que erro de autenticação é encapsulado."""
    # Arrange
    mock_auth = MagicMock()
    mock_supabase.auth = mock_auth
    mock_auth.get_user.side_effect = Exception("Auth service down")

    with patch("src.modules.auditoria.service.get_supabase", return_value=mock_supabase):
        # Act & Assert
        with pytest.raises(AuditoriaServiceError, match="Nao foi possivel determinar o org_id"):
            service.get_current_org_id()
