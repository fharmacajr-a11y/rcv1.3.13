"""Testes para o módulo de busca de clientes (search).

Cobertura de:
- Normalização de ordenação (_normalize_order)
- Conversão de rows para Cliente (_row_to_cliente)
- Criação de blob de busca (_cliente_search_blob)
- Filtragem local com normalização (_filter_rows_with_norm, _filter_clientes)
- Busca integrada (search_clientes) com mocks
"""

from unittest.mock import MagicMock, patch

import pytest

from src.core.models import Cliente
from src.core.search.search import (
    _cliente_search_blob,
    _filter_clientes,
    _filter_rows_with_norm,
    _normalize_order,
    _row_to_cliente,
    search_clientes,
)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def sample_row():
    """Row de cliente de exemplo para testes."""
    return {
        "id": 1,
        "numero": "123",
        "nome": "João Silva",
        "razao_social": "João Silva MEI",
        "cnpj": "12345678000190",
        "cnpj_norm": "12345678000190",
        "ultima_alteracao": "2024-01-15T10:30:00",
        "obs": "Cliente VIP",
        "ultima_por": "user@example.com",
        "created_at": "2024-01-01T00:00:00",
    }


@pytest.fixture
def sample_cliente():
    """Cliente de exemplo para testes."""
    return Cliente(
        id=2,
        numero="456",
        nome="Maria Santos",
        razao_social="Maria Santos LTDA",
        cnpj="98765432000100",
        cnpj_norm="98765432000100",
        ultima_alteracao="2024-02-20T15:45:00",
        obs="Cliente regular",
        ultima_por="admin@example.com",
        created_at="2024-02-01T00:00:00",
    )


# ============================================================================
# TESTES: _normalize_order
# ============================================================================


def test_normalize_order_none():
    """Testa normalização quando order_by é None."""
    col, desc = _normalize_order(None)
    assert col is None
    assert desc is False


def test_normalize_order_empty_string():
    """Testa normalização quando order_by é string vazia."""
    col, desc = _normalize_order("")
    assert col is None
    assert desc is False


def test_normalize_order_nome():
    """Testa normalização para ordenação por nome."""
    col, desc = _normalize_order("nome")
    assert col == "nome"
    assert desc is False


def test_normalize_order_razao_social():
    """Testa normalização para ordenação por razão social."""
    col, desc = _normalize_order("razao social")
    assert col == "razao_social"
    assert desc is False


def test_normalize_order_cnpj():
    """Testa normalização para ordenação por CNPJ."""
    col, desc = _normalize_order("cnpj")
    assert col == "cnpj"
    assert desc is False


def test_normalize_order_ultima_alteracao():
    """Testa normalização para ordenação por última alteração (descendente)."""
    col, desc = _normalize_order("ultima alteracao")
    assert col == "ultima_alteracao"
    assert desc is True


def test_normalize_order_invalid():
    """Testa normalização quando order_by é inválido."""
    col, desc = _normalize_order("campo_inexistente")
    assert col is None
    assert desc is False


# ============================================================================
# TESTES: _row_to_cliente
# ============================================================================


def test_row_to_cliente_complete(sample_row):
    """Testa conversão de row completo para Cliente."""
    cliente = _row_to_cliente(sample_row)

    assert isinstance(cliente, Cliente)
    assert cliente.id == 1
    assert cliente.numero == "123"
    assert cliente.nome == "João Silva"
    assert cliente.razao_social == "João Silva MEI"
    assert cliente.cnpj == "12345678000190"
    assert cliente.cnpj_norm == "12345678000190"
    assert cliente.ultima_alteracao == "2024-01-15T10:30:00"
    assert cliente.obs == "Cliente VIP"
    assert cliente.ultima_por == "user@example.com"
    assert cliente.created_at == "2024-01-01T00:00:00"


def test_row_to_cliente_partial():
    """Testa conversão de row com campos faltantes."""
    partial_row = {
        "id": 3,
        "nome": "Empresa XYZ",
        "cnpj": "11111111000100",
    }
    cliente = _row_to_cliente(partial_row)

    assert cliente.id == 3
    assert cliente.nome == "Empresa XYZ"
    assert cliente.cnpj == "11111111000100"
    assert cliente.razao_social is None
    assert cliente.obs is None


def test_row_to_cliente_empty():
    """Testa conversão de row vazio."""
    cliente = _row_to_cliente({})

    assert isinstance(cliente, Cliente)
    assert cliente.id is None
    assert cliente.nome is None


# ============================================================================
# TESTES: _cliente_search_blob
# ============================================================================


def test_cliente_search_blob_complete(sample_cliente):
    """Testa criação de blob de busca com cliente completo."""
    blob = _cliente_search_blob(sample_cliente)

    assert isinstance(blob, str)
    # Verifica que campos normalizados estão presentes (blob remove hífens/espaços)
    assert "2" in blob
    assert "maria" in blob.lower()
    assert "santos" in blob.lower()
    assert "98765432000100" in blob


def test_cliente_search_blob_partial():
    """Testa criação de blob com cliente parcial."""
    cliente = Cliente(
        id=4,
        nome="Teste Inc",
        numero=None,
        razao_social=None,
        cnpj=None,
        cnpj_norm=None,
        ultima_alteracao=None,
        obs=None,
        ultima_por=None,
    )
    blob = _cliente_search_blob(cliente)

    assert "4" in blob
    assert "teste" in blob.lower()


# ============================================================================
# TESTES: _filter_rows_with_norm
# ============================================================================


def test_filter_rows_with_norm_match():
    """Testa filtragem de rows com termo que faz match."""
    rows = [
        {"id": "1", "nome": "João Silva", "cnpj": "12345678000190"},
        {"id": "2", "nome": "Maria Santos", "cnpj": "98765432000100"},
    ]

    filtered = _filter_rows_with_norm(rows, "joão")
    assert len(filtered) == 1
    assert filtered[0]["id"] == "1"


def test_filter_rows_with_norm_no_match():
    """Testa filtragem quando nenhum row faz match."""
    rows = [
        {"id": "1", "nome": "João Silva"},
        {"id": "2", "nome": "Maria Santos"},
    ]

    filtered = _filter_rows_with_norm(rows, "pedro")
    assert len(filtered) == 0


def test_filter_rows_with_norm_empty_term():
    """Testa filtragem com termo vazio retorna todos os rows."""
    rows = [
        {"id": "1", "nome": "João Silva"},
        {"id": "2", "nome": "Maria Santos"},
    ]

    filtered = _filter_rows_with_norm(rows, "")
    assert len(filtered) == 2


def test_filter_rows_with_norm_cnpj():
    """Testa filtragem por CNPJ."""
    rows = [
        {"id": "1", "nome": "Empresa A", "cnpj": "12345678000190"},
        {"id": "2", "nome": "Empresa B", "cnpj": "98765432000100"},
    ]

    filtered = _filter_rows_with_norm(rows, "12345678")
    assert len(filtered) == 1
    assert filtered[0]["id"] == "1"


# ============================================================================
# TESTES: _filter_clientes
# ============================================================================


def test_filter_clientes_match(sample_cliente):
    """Testa filtragem de clientes com termo que faz match."""
    clientes = [
        sample_cliente,
        Cliente(
            id=3,
            nome="Pedro Alves",
            numero="789",
            razao_social="Pedro Alves MEI",
            cnpj="11111111000100",
            cnpj_norm="11111111000100",
            ultima_alteracao=None,
            obs=None,
            ultima_por=None,
        ),
    ]

    filtered = _filter_clientes(clientes, "maria")
    assert len(filtered) == 1
    assert filtered[0].id == 2


def test_filter_clientes_no_match():
    """Testa filtragem quando nenhum cliente faz match."""
    clientes = [
        Cliente(id=1, nome="João Silva", numero=None, razao_social=None, cnpj=None, cnpj_norm=None, ultima_alteracao=None, obs=None, ultima_por=None),
        Cliente(id=2, nome="Maria Santos", numero=None, razao_social=None, cnpj=None, cnpj_norm=None, ultima_alteracao=None, obs=None, ultima_por=None),
    ]

    filtered = _filter_clientes(clientes, "inexistente")
    assert len(filtered) == 0


def test_filter_clientes_empty_term():
    """Testa filtragem com termo vazio retorna todos os clientes."""
    clientes = [
        Cliente(id=1, nome="João Silva", numero=None, razao_social=None, cnpj=None, cnpj_norm=None, ultima_alteracao=None, obs=None, ultima_por=None),
        Cliente(id=2, nome="Maria Santos", numero=None, razao_social=None, cnpj=None, cnpj_norm=None, ultima_alteracao=None, obs=None, ultima_por=None),
    ]

    filtered = _filter_clientes(clientes, "")
    assert len(filtered) == 2


# ============================================================================
# TESTES: search_clientes (integração com mocks)
# ============================================================================


@patch("src.core.search.search.is_supabase_online")
@patch("src.core.search.search.get_current_user")
def test_search_clientes_offline_fallback(mock_get_user, mock_is_online):
    """Testa fallback para busca local quando Supabase está offline."""
    # Arrange
    mock_is_online.return_value = False
    mock_user = MagicMock()
    mock_user.org_id = "org-123"
    mock_get_user.return_value = mock_user

    with patch("src.core.db_manager.db_manager.list_clientes_by_org") as mock_list:
        mock_list.return_value = [
            Cliente(
                id=1,
                nome="João Silva",
                numero="123",
                razao_social="João Silva MEI",
                cnpj="12345678000190",
                cnpj_norm="12345678000190",
                ultima_alteracao=None,
                obs=None,
                ultima_por=None,
            ),
        ]

        # Act
        result = search_clientes("joão", org_id="org-123")

        # Assert
        assert len(result) == 1
        assert result[0].id == 1
        mock_list.assert_called_once()


@patch("src.core.search.search.is_supabase_online")
@patch("src.core.search.search.get_current_user")
def test_search_clientes_no_org_id_raises(mock_get_user, mock_is_online):
    """Testa que busca sem org_id levanta ValueError em fallback."""
    # Arrange
    mock_is_online.return_value = False
    mock_get_user.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match="org_id obrigatorio"):
        search_clientes("teste", org_id=None)


@patch("src.core.search.search.is_supabase_online")
@patch("src.core.search.search.get_current_user")
def test_search_clientes_empty_term_offline(mock_get_user, mock_is_online):
    """Testa busca sem termo (listar todos) em modo offline."""
    # Arrange
    mock_is_online.return_value = False
    mock_user = MagicMock()
    mock_user.org_id = "org-456"
    mock_get_user.return_value = mock_user

    with patch("src.core.db_manager.db_manager.list_clientes_by_org") as mock_list:
        mock_list.return_value = [
            Cliente(id=1, nome="Cliente A", numero=None, razao_social=None, cnpj=None, cnpj_norm=None, ultima_alteracao=None, obs=None, ultima_por=None),
            Cliente(id=2, nome="Cliente B", numero=None, razao_social=None, cnpj=None, cnpj_norm=None, ultima_alteracao=None, obs=None, ultima_por=None),
        ]

        # Act
        result = search_clientes("", org_id="org-456")

        # Assert
        assert len(result) == 2
        mock_list.assert_called_once()
