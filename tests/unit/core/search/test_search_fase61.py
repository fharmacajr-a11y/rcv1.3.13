# tests/unit/core/search/test_search_fase61.py
"""
Testes para search.py (busca de clientes com Supabase + fallback local).

Escopo (sem network real):
1) search_clientes: online vs offline, ordenação, filtros, org_id
2) _normalize_order: mapeamento de apelidos para colunas
3) _row_to_cliente: conversão de row dict para Cliente
4) _cliente_search_blob: concatenação normalizada
5) _filter_rows_with_norm: filtro local com cache
6) _filter_clientes: filtro em lista de Cliente

Cobertura: Mocks de infra.supabase_client + db_manager + session.
Isolamento: sem network, sem SQLite real (mocks completos).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock

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


# ==========================================
# Fixtures: mocking de dependências
# ==========================================
@pytest.fixture
def mock_supabase_online(monkeypatch: pytest.MonkeyPatch) -> Mock:
    """Mock is_supabase_online() para simular estado de conectividade."""
    mock = Mock(return_value=True)
    monkeypatch.setattr("src.core.search.search.is_supabase_online", mock)
    return mock


@pytest.fixture
def mock_supabase_client(monkeypatch: pytest.MonkeyPatch) -> dict[str, Mock]:
    """Mock completo do Supabase client com QueryBuilder encadeado."""
    mock_response = Mock()
    mock_response.data = []

    mock_qb = Mock()
    mock_qb.select.return_value = mock_qb
    mock_qb.is_.return_value = mock_qb
    mock_qb.eq.return_value = mock_qb
    mock_qb.or_.return_value = mock_qb
    mock_qb.order.return_value = mock_qb

    mock_table = Mock(return_value=mock_qb)
    mock_supabase = Mock()
    mock_supabase.table = mock_table

    mock_exec = Mock(return_value=mock_response)

    monkeypatch.setattr("src.core.search.search.supabase", mock_supabase)
    monkeypatch.setattr("src.core.search.search.exec_postgrest", mock_exec)

    return {
        "supabase": mock_supabase,
        "exec_postgrest": mock_exec,
        "response": mock_response,
        "qb": mock_qb,
    }


@pytest.fixture
def mock_db_manager(monkeypatch: pytest.MonkeyPatch) -> Mock:
    """Mock list_clientes_by_org para fallback local."""
    mock = Mock(return_value=[])
    # list_clientes_by_org é importado dinamicamente dentro da função
    monkeypatch.setattr("src.core.db_manager.db_manager.list_clientes_by_org", mock)
    return mock


@pytest.fixture
def mock_current_user(monkeypatch: pytest.MonkeyPatch) -> Mock:
    """Mock get_current_user() para auto-resolver org_id."""
    mock_user = Mock()
    mock_user.org_id = "org-123"
    mock = Mock(return_value=mock_user)
    monkeypatch.setattr("src.core.search.search.get_current_user", mock)
    return mock


# ==========================================
# Testes: _normalize_order
# ==========================================
def test_normalize_order_nome() -> None:
    """_normalize_order mapeia 'nome' para coluna 'nome', ascending."""
    col, desc = _normalize_order("nome")
    assert col == "nome"
    assert desc is False


def test_normalize_order_razao_social_variations() -> None:
    """_normalize_order aceita 'razao social' e 'razao_social'."""
    col1, desc1 = _normalize_order("razao social")
    col2, desc2 = _normalize_order("razao_social")
    assert col1 == "razao_social"
    assert desc1 is False
    assert col2 == "razao_social"
    assert desc2 is False


def test_normalize_order_ultima_alteracao_descending() -> None:
    """_normalize_order mapeia 'ultima alteracao' para 'ultima_alteracao', descending=True."""
    col, desc = _normalize_order("ultima alteracao")
    assert col == "ultima_alteracao"
    assert desc is True


def test_normalize_order_case_insensitive() -> None:
    """_normalize_order é case-insensitive."""
    col1, desc1 = _normalize_order("NOME")
    col2, desc2 = _normalize_order("Razao Social")
    assert col1 == "nome"
    assert col2 == "razao_social"


def test_normalize_order_invalid() -> None:
    """_normalize_order retorna (None, False) para apelido inválido."""
    col, desc = _normalize_order("campo_invalido")
    assert col is None
    assert desc is False


def test_normalize_order_none() -> None:
    """_normalize_order retorna (None, False) para None."""
    col, desc = _normalize_order(None)
    assert col is None
    assert desc is False


# ==========================================
# Testes: _row_to_cliente
# ==========================================
def test_row_to_cliente_all_fields() -> None:
    """_row_to_cliente converte row completa em Cliente."""
    row = {
        "id": 101,
        "numero": "11987654321",
        "nome": "João Silva",
        "razao_social": "Empresa ABC",
        "cnpj": "12.345.678/0001-10",
        "cnpj_norm": "12345678000110",
        "ultima_alteracao": "2025-12-20T10:00:00Z",
        "obs": "Cliente VIP",
        "ultima_por": "user@example.com",
        "created_at": "2025-01-01T00:00:00Z",
    }
    cliente = _row_to_cliente(row)
    assert cliente.id == 101
    assert cliente.numero == "11987654321"
    assert cliente.nome == "João Silva"
    assert cliente.razao_social == "Empresa ABC"
    assert cliente.cnpj == "12.345.678/0001-10"
    assert cliente.cnpj_norm == "12345678000110"
    assert cliente.ultima_alteracao == "2025-12-20T10:00:00Z"
    assert cliente.obs == "Cliente VIP"
    assert cliente.ultima_por == "user@example.com"
    assert cliente.created_at == "2025-01-01T00:00:00Z"


def test_row_to_cliente_missing_fields() -> None:
    """_row_to_cliente lida com campos ausentes (None)."""
    row = {"id": 102, "nome": "Maria"}
    cliente = _row_to_cliente(row)
    assert cliente.id == 102
    assert cliente.nome == "Maria"
    assert cliente.numero is None
    assert cliente.razao_social is None
    assert cliente.cnpj is None


def test_row_to_cliente_empty_row() -> None:
    """_row_to_cliente lida com row vazia."""
    row: dict[str, Any] = {}
    cliente = _row_to_cliente(row)
    assert cliente.id is None
    assert cliente.nome is None


# ==========================================
# Testes: _cliente_search_blob
# ==========================================
def test_cliente_search_blob_all_fields() -> None:
    """_cliente_search_blob concatena todos os campos relevantes."""
    cliente = Cliente(
        id=101,
        numero="11987654321",
        nome="João Silva",
        razao_social="Empresa ABC",
        cnpj="12.345.678/0001-10",
        cnpj_norm="12345678000110",
        ultima_alteracao="2025-12-20T10:00:00Z",
        obs="Cliente VIP",
        ultima_por="user@example.com",
    )
    blob = _cliente_search_blob(cliente)
    # join_and_normalize deve juntar id, nome, razao_social, cnpj, numero, obs
    assert "101" in blob or "joao" in blob.lower()
    assert "11987654321" in blob or "1198765" in blob


def test_cliente_search_blob_partial_fields() -> None:
    """_cliente_search_blob lida com campos parciais."""
    cliente = Cliente(
        id=102,
        nome="Maria",
        cnpj=None,
        numero=None,
        razao_social=None,
        cnpj_norm=None,
        ultima_alteracao=None,
        obs=None,
        ultima_por=None,
    )
    blob = _cliente_search_blob(cliente)
    assert "102" in blob or "maria" in blob.lower()


# ==========================================
# Testes: _filter_rows_with_norm
# ==========================================
def test_filter_rows_with_norm_match() -> None:
    """_filter_rows_with_norm retorna rows que contêm o termo normalizado."""
    rows = [
        {"id": 1, "razao_social": "Empresa ABC", "cnpj": "12.345.678/0001-10"},
        {"id": 2, "razao_social": "Empresa XYZ", "cnpj": "11.222.333/0001-65"},
    ]
    result = _filter_rows_with_norm(rows, "ABC")
    assert len(result) == 1
    assert result[0]["id"] == 1


def test_filter_rows_with_norm_empty_term() -> None:
    """_filter_rows_with_norm retorna todas as rows se termo vazio."""
    rows = [
        {"id": 1, "razao_social": "Empresa ABC"},
        {"id": 2, "razao_social": "Empresa XYZ"},
    ]
    result = _filter_rows_with_norm(rows, "")
    assert len(result) == 2


def test_filter_rows_with_norm_caching() -> None:
    """_filter_rows_with_norm cacheia _search_norm nas rows."""
    rows = [{"id": 1, "razao_social": "Empresa ABC", "cnpj": "12.345.678/0001-10"}]
    result = _filter_rows_with_norm(rows, "ABC")
    # Verifica que _search_norm foi adicionado
    assert "_search_norm" in result[0]


def test_filter_rows_with_norm_no_match() -> None:
    """_filter_rows_with_norm retorna vazio se nenhuma row match."""
    rows = [{"id": 1, "razao_social": "Empresa ABC"}]
    result = _filter_rows_with_norm(rows, "XYZ")
    assert len(result) == 0


# ==========================================
# Testes: _filter_clientes
# ==========================================
def test_filter_clientes_match() -> None:
    """_filter_clientes retorna clientes que contêm o termo."""
    clientes = [
        Cliente(
            id=1,
            nome="João Silva",
            numero="11987654321",
            razao_social="Empresa ABC",
            cnpj="12.345.678/0001-10",
            cnpj_norm="12345678000110",
            ultima_alteracao=None,
            obs=None,
            ultima_por=None,
        ),
        Cliente(
            id=2,
            nome="Maria Santos",
            numero="21999888777",
            razao_social="Empresa XYZ",
            cnpj="11.222.333/0001-65",
            cnpj_norm="11222333000165",
            ultima_alteracao=None,
            obs=None,
            ultima_por=None,
        ),
    ]
    result = _filter_clientes(clientes, "João")
    assert len(result) == 1
    assert result[0].id == 1


def test_filter_clientes_empty_term() -> None:
    """_filter_clientes retorna todos os clientes se termo vazio."""
    clientes = [
        Cliente(
            id=1,
            nome="João",
            numero=None,
            razao_social=None,
            cnpj=None,
            cnpj_norm=None,
            ultima_alteracao=None,
            obs=None,
            ultima_por=None,
        ),
        Cliente(
            id=2,
            nome="Maria",
            numero=None,
            razao_social=None,
            cnpj=None,
            cnpj_norm=None,
            ultima_alteracao=None,
            obs=None,
            ultima_por=None,
        ),
    ]
    result = _filter_clientes(clientes, "")
    assert len(result) == 2


def test_filter_clientes_no_match() -> None:
    """_filter_clientes retorna vazio se nenhum cliente match."""
    clientes = [
        Cliente(
            id=1,
            nome="João",
            numero=None,
            razao_social=None,
            cnpj=None,
            cnpj_norm=None,
            ultima_alteracao=None,
            obs=None,
            ultima_por=None,
        )
    ]
    result = _filter_clientes(clientes, "Maria")
    assert len(result) == 0


# ==========================================
# Testes: search_clientes (online)
# ==========================================
def test_search_clientes_online_basic(
    mock_supabase_online: Mock,
    mock_supabase_client: dict[str, Mock],
) -> None:
    """search_clientes retorna clientes quando online e com resultados."""
    mock_supabase_client["response"].data = [
        {"id": 1, "nome": "João", "razao_social": "Empresa ABC", "cnpj": "12.345.678/0001-10"},
    ]

    result = search_clientes(term="João", org_id="org-123")

    assert len(result) == 1
    assert result[0].id == 1
    assert result[0].nome == "João"
    # Verifica que chamou Supabase
    mock_supabase_client["exec_postgrest"].assert_called()


def test_search_clientes_online_empty_term(
    mock_supabase_online: Mock,
    mock_supabase_client: dict[str, Mock],
) -> None:
    """search_clientes com termo vazio retorna todos os clientes da org."""
    mock_supabase_client["response"].data = [
        {"id": 1, "nome": "João"},
        {"id": 2, "nome": "Maria"},
    ]

    result = search_clientes(term="", org_id="org-123")

    assert len(result) == 2
    # Não deve chamar or_() se termo vazio
    mock_supabase_client["qb"].or_.assert_not_called()


def test_search_clientes_online_with_order(
    mock_supabase_online: Mock,
    mock_supabase_client: dict[str, Mock],
) -> None:
    """search_clientes aplica ordenação corretamente."""
    mock_supabase_client["response"].data = [{"id": 1, "nome": "João"}]

    search_clientes(term="", order_by="nome", org_id="org-123")

    # Verifica que chamou order() com coluna correta
    mock_supabase_client["qb"].order.assert_called_with("nome", desc=False)


def test_search_clientes_online_no_org_id_raises(
    mock_supabase_online: Mock,
    mock_supabase_client: dict[str, Mock],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """search_clientes levanta ValueError se online e org_id=None."""
    # Garante que get_current_user retorna None
    monkeypatch.setattr("src.core.search.search.get_current_user", lambda: None)

    with pytest.raises(ValueError, match="org_id obrigatorio"):
        search_clientes(term="João", org_id=None)


def test_search_clientes_online_auto_resolve_org_id(
    mock_supabase_online: Mock,
    mock_supabase_client: dict[str, Mock],
    mock_current_user: Mock,
) -> None:
    """search_clientes auto-resolve org_id de get_current_user()."""
    mock_supabase_client["response"].data = [{"id": 1, "nome": "João"}]

    result = search_clientes(term="João", org_id=None)

    assert len(result) == 1
    # Verifica que chamou eq() com org_id do usuário
    mock_supabase_client["qb"].eq.assert_called_with("org_id", "org-123")


def test_search_clientes_online_double_filter(
    mock_supabase_online: Mock,
    mock_supabase_client: dict[str, Mock],
) -> None:
    """search_clientes faz 2 queries se primeira query com termo não retornar nada."""
    # Primeira query retorna vazio, segunda query retorna item
    mock_supabase_client["exec_postgrest"].side_effect = [
        Mock(data=[]),  # 1ª query com ilike
        Mock(data=[{"id": 1, "nome": "João Silva", "razao_social": "Empresa ABC"}]),  # 2ª query sem filtro
    ]

    result = search_clientes(term="João", org_id="org-123")

    # Deve ter chamado exec_postgrest 2 vezes
    assert mock_supabase_client["exec_postgrest"].call_count == 2
    # Resultado pode estar vazio se filtro local também não achar
    assert isinstance(result, list)


# ==========================================
# Testes: search_clientes (offline/fallback)
# ==========================================
def test_search_clientes_offline(
    mock_supabase_online: Mock,
    mock_db_manager: Mock,
) -> None:
    """search_clientes usa fallback local quando offline."""
    mock_supabase_online.return_value = False
    mock_db_manager.return_value = [
        Cliente(
            id=1,
            nome="João",
            numero=None,
            razao_social="Empresa ABC",
            cnpj=None,
            cnpj_norm=None,
            ultima_alteracao=None,
            obs=None,
            ultima_por=None,
        ),
    ]

    result = search_clientes(term="João", org_id="org-123")

    assert len(result) == 1
    assert result[0].id == 1
    # Verifica que chamou list_clientes_by_org
    mock_db_manager.assert_called_once()


def test_search_clientes_offline_no_org_id_raises(
    mock_supabase_online: Mock,
    mock_db_manager: Mock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """search_clientes levanta ValueError se offline e org_id=None."""
    mock_supabase_online.return_value = False
    monkeypatch.setattr("src.core.search.search.get_current_user", lambda: None)

    with pytest.raises(ValueError, match="org_id obrigatorio"):
        search_clientes(term="João", org_id=None)


def test_search_clientes_supabase_exception_fallback(
    mock_supabase_online: Mock,
    mock_supabase_client: dict[str, Mock],
    mock_db_manager: Mock,
) -> None:
    """search_clientes faz fallback local se Supabase levantar exceção."""
    mock_supabase_client["exec_postgrest"].side_effect = RuntimeError("Network error")
    mock_db_manager.return_value = [
        Cliente(
            id=1,
            nome="João",
            numero=None,
            razao_social=None,
            cnpj=None,
            cnpj_norm=None,
            ultima_alteracao=None,
            obs=None,
            ultima_por=None,
        )
    ]

    result = search_clientes(term="João", org_id="org-123")

    assert len(result) == 1
    # Verifica que chamou fallback
    mock_db_manager.assert_called_once()


def test_search_clientes_supabase_exception_no_org_id_raises(
    mock_supabase_online: Mock,
    mock_supabase_client: dict[str, Mock],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """search_clientes levanta ValueError se falha Supabase e org_id=None."""
    mock_supabase_client["exec_postgrest"].side_effect = RuntimeError("Network error")
    monkeypatch.setattr("src.core.search.search.get_current_user", lambda: None)

    with pytest.raises(ValueError, match="org_id obrigatorio"):
        search_clientes(term="João", org_id=None)


def test_search_clientes_offline_with_order(
    mock_supabase_online: Mock,
    mock_db_manager: Mock,
) -> None:
    """search_clientes passa ordenação para list_clientes_by_org no fallback."""
    mock_supabase_online.return_value = False
    mock_db_manager.return_value = []

    search_clientes(term="", order_by="nome", org_id="org-123")

    # Verifica que chamou com order_by e descending corretos (nome = False)
    mock_db_manager.assert_called_once_with("org-123", order_by="nome", descending=False)


def test_search_clientes_offline_empty_term(
    mock_supabase_online: Mock,
    mock_db_manager: Mock,
) -> None:
    """search_clientes offline com termo vazio retorna todos."""
    mock_supabase_online.return_value = False
    mock_db_manager.return_value = [
        Cliente(
            id=1,
            nome="João",
            numero=None,
            razao_social=None,
            cnpj=None,
            cnpj_norm=None,
            ultima_alteracao=None,
            obs=None,
            ultima_por=None,
        ),
        Cliente(
            id=2,
            nome="Maria",
            numero=None,
            razao_social=None,
            cnpj=None,
            cnpj_norm=None,
            ultima_alteracao=None,
            obs=None,
            ultima_por=None,
        ),
    ]

    result = search_clientes(term="", org_id="org-123")

    assert len(result) == 2


def test_search_clientes_offline_filter_local(
    mock_supabase_online: Mock,
    mock_db_manager: Mock,
) -> None:
    """search_clientes offline aplica filtro local quando termo fornecido."""
    mock_supabase_online.return_value = False
    mock_db_manager.return_value = [
        Cliente(
            id=1,
            nome="João Silva",
            numero=None,
            razao_social="Empresa ABC",
            cnpj=None,
            cnpj_norm=None,
            ultima_alteracao=None,
            obs=None,
            ultima_por=None,
        ),
        Cliente(
            id=2,
            nome="Maria Santos",
            numero=None,
            razao_social="Empresa XYZ",
            cnpj=None,
            cnpj_norm=None,
            ultima_alteracao=None,
            obs=None,
            ultima_por=None,
        ),
    ]

    result = search_clientes(term="João", org_id="org-123")

    # Deve filtrar localmente
    assert len(result) == 1
    assert result[0].id == 1


# ==========================================
# Testes: edge cases
# ==========================================
def test_search_clientes_term_whitespace_only(
    mock_supabase_online: Mock,
    mock_supabase_client: dict[str, Mock],
) -> None:
    """search_clientes com termo apenas espaços trata como vazio."""
    mock_supabase_client["response"].data = [{"id": 1, "nome": "João"}]

    result = search_clientes(term="   ", org_id="org-123")

    # Termo normalizado vazio -> não chama or_()
    mock_supabase_client["qb"].or_.assert_not_called()
    assert len(result) == 1


def test_search_clientes_order_by_invalid(
    mock_supabase_online: Mock,
    mock_supabase_client: dict[str, Mock],
) -> None:
    """search_clientes com order_by inválido não chama order()."""
    mock_supabase_client["response"].data = [{"id": 1, "nome": "João"}]

    search_clientes(term="", order_by="campo_invalido", org_id="org-123")

    # Não deve chamar order() se col=None
    mock_supabase_client["qb"].order.assert_not_called()


def test_search_clientes_empty_response(
    mock_supabase_online: Mock,
    mock_supabase_client: dict[str, Mock],
) -> None:
    """search_clientes lida com response.data=None."""
    mock_supabase_client["response"].data = None

    result = search_clientes(term="João", org_id="org-123")

    # Deve retornar lista vazia sem erro
    assert result == []


def test_search_clientes_current_user_no_org_id(
    mock_supabase_online: Mock,
    mock_supabase_client: dict[str, Mock],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """search_clientes levanta ValueError se current_user não tem org_id."""
    mock_user = Mock()
    mock_user.org_id = None
    monkeypatch.setattr("src.core.search.search.get_current_user", lambda: mock_user)

    with pytest.raises(ValueError, match="org_id obrigatorio"):
        search_clientes(term="João", org_id=None)
