# tests/unit/core/services/test_clientes_service_fase60.py
"""
Testes para clientes_service.py (módulo de negócios CRUD + validação + integração).

Escopo (sem network real):
1) count_clients: retry 10035, fallback last-known
2) _normalize_payload: extração e normalização de campos
3) checar_duplicatas_info: CNPJ duplicado, Razão Social normalizada, exclude_id
4) salvar_cliente: criação, update, conflict CNPJ, validação mínima, auditoria, pasta
5) _pasta_do_cliente: formação de path local

Cobertura: Mocks de db_manager + infra.supabase_client + session + audit log.
Isolamento: sem FS real (tmp_path ou monkeypatch), sem network real.
"""

from __future__ import annotations

import os
import threading
from typing import Any
from unittest.mock import MagicMock, Mock

import pytest

# Importações do módulo alvo
from src.core.services import clientes_service
from src.core.services.clientes_service import (
    _normalize_payload,
    _pasta_do_cliente,
    checar_duplicatas_info,
    count_clients,
    salvar_cliente,
)


# ==========================================
# Fixtures: mocking de dependências
# ==========================================
@pytest.fixture
def mock_db_manager(monkeypatch: pytest.MonkeyPatch) -> dict[str, Mock]:
    """Mock das funções de db_manager para simular CRUD sem PostgreSQL real."""
    mock_find = Mock(return_value=None)
    mock_insert = Mock(return_value=101)
    mock_update = Mock()
    mock_list = Mock(return_value=[])

    monkeypatch.setattr("src.core.services.clientes_service.find_cliente_by_cnpj_norm", mock_find)
    monkeypatch.setattr("src.core.services.clientes_service.insert_cliente", mock_insert)
    monkeypatch.setattr("src.core.services.clientes_service.update_cliente", mock_update)
    monkeypatch.setattr("src.core.services.clientes_service.list_clientes", mock_list)

    return {
        "find_cliente_by_cnpj_norm": mock_find,
        "insert_cliente": mock_insert,
        "update_cliente": mock_update,
        "list_clientes": mock_list,
    }


@pytest.fixture
def mock_supabase_exec(monkeypatch: pytest.MonkeyPatch) -> Mock:
    """Mock de exec_postgrest para simular contagem de clientes sem rede."""
    mock = Mock()
    monkeypatch.setattr("src.core.services.clientes_service.exec_postgrest", mock)
    return mock


@pytest.fixture
def mock_audit_log(monkeypatch: pytest.MonkeyPatch) -> Mock:
    """Mock de log_client_action para evitar side-effects de auditoria."""
    mock = Mock()
    monkeypatch.setattr("src.core.services.clientes_service.log_client_action", mock)
    return mock


@pytest.fixture
def mock_session_user(monkeypatch: pytest.MonkeyPatch) -> Mock:
    """Mock de get_current_user para retornar usuário fake."""
    mock = Mock(return_value="test_user")
    monkeypatch.setattr("src.core.services.clientes_service.get_current_user", mock)
    return mock


@pytest.fixture
def mock_pasta_helpers(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> dict[str, Any]:
    """Mock de funções de pasta para evitar FS real."""
    mock_ensure = Mock()
    mock_write = Mock()
    monkeypatch.setattr("src.core.services.clientes_service.ensure_subpastas", mock_ensure)
    monkeypatch.setattr("src.core.services.clientes_service.write_marker", mock_write)
    # Força DOCS_DIR para tmp_path
    monkeypatch.setattr("src.core.services.clientes_service.DOCS_DIR", tmp_path)
    return {"ensure_subpastas": mock_ensure, "write_marker": mock_write, "tmp_path": tmp_path}


@pytest.fixture
def reset_last_clients_count(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reseta o contador global antes de cada teste."""
    # BUG-002: Usar _clients_cache ao invés de _LAST_CLIENTS_COUNT
    import src.core.services.clientes_service as svc

    with svc._clients_cache.lock:
        svc._clients_cache.count = 0


@pytest.fixture(autouse=True)
def _force_cloud_only_false(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    TESTFIX-DUPLICATAS-001: Force CLOUD_ONLY=False para unit tests.

    Unit tests devem ser determinísticos e offline (sem network real).
    PERF-001 introduziu branch CLOUD_ONLY que chama Supabase diretamente,
    mas esses testes mockam list_clientes/find_cliente_by_cnpj_norm.
    """
    monkeypatch.setattr("src.core.services.clientes_service.CLOUD_ONLY", False, raising=False)


# ==========================================
# Testes: count_clients
# ==========================================
def test_count_clients_success(mock_supabase_exec: Mock, reset_last_clients_count: None) -> None:
    """count_clients retorna contagem do Supabase quando sem erros."""
    mock_response = Mock()
    mock_response.count = 42
    mock_supabase_exec.return_value = mock_response

    result = count_clients()
    assert result == 42
    # BUG-002: Verifica que o cache foi atualizado
    with clientes_service._clients_cache.lock:
        assert clientes_service._clients_cache.count == 42


def test_count_clients_none_count(mock_supabase_exec: Mock, reset_last_clients_count: None) -> None:
    """count_clients retorna 0 se resp.count for None."""
    mock_response = Mock()
    mock_response.count = None
    mock_supabase_exec.return_value = mock_response

    result = count_clients()
    assert result == 0
    # BUG-002: Verifica cache
    with clientes_service._clients_cache.lock:
        assert clientes_service._clients_cache.count == 0


def test_count_clients_winerror_10035_retry(
    mock_supabase_exec: Mock,
    reset_last_clients_count: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """count_clients faz retry em WinError 10035 e eventualmente sucede."""
    # Simular 2 falhas seguidas de sucesso
    side_effects = []
    err = OSError("WSAEWOULDBLOCK")
    err.winerror = 10035  # type: ignore[attr-defined]
    side_effects.append(err)
    side_effects.append(err)
    mock_response = Mock()
    mock_response.count = 99
    side_effects.append(mock_response)

    mock_supabase_exec.side_effect = side_effects
    # Acelerar o teste: reduzir o delay para 0s
    monkeypatch.setattr("src.core.services.clientes_service.time.sleep", lambda x: None)

    result = count_clients(max_retries=2, base_delay=0.0)
    assert result == 99
    # BUG-002: Verificar cache atualizado
    with clientes_service._clients_cache.lock:
        assert clientes_service._clients_cache.count == 99
    # Verifica que tentou 3 vezes
    assert mock_supabase_exec.call_count == 3


def test_count_clients_winerror_10035_fallback(
    mock_supabase_exec: Mock,
    reset_last_clients_count: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """count_clients usa last-known se esgotar retries em 10035."""
    # BUG-002: Popular o cache com valor 123
    with clientes_service._clients_cache.lock:
        clientes_service._clients_cache.count = 123

    # Agora sempre falha com 10035
    err = OSError("WSAEWOULDBLOCK")
    err.winerror = 10035  # type: ignore[attr-defined]
    mock_supabase_exec.side_effect = err

    monkeypatch.setattr("src.core.services.clientes_service.time.sleep", lambda x: None)

    result = count_clients(max_retries=2, base_delay=0.0)
    assert result == 123  # Deve usar last-known
    # BUG-002: cache não mudou
    with clientes_service._clients_cache.lock:
        assert clientes_service._clients_cache.count == 123


def test_count_clients_other_oserror_fallback(
    mock_supabase_exec: Mock,
    reset_last_clients_count: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """count_clients usa last-known se houver OSError não-10035."""
    # BUG-002: Popular cache
    with clientes_service._clients_cache.lock:
        clientes_service._clients_cache.count = 50
    mock_supabase_exec.side_effect = OSError("Connection refused")

    result = count_clients()
    assert result == 50


def test_count_clients_generic_exception_fallback(
    mock_supabase_exec: Mock,
    reset_last_clients_count: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """count_clients usa last-known se houver Exception genérica."""
    # BUG-002: Popular cache
    with clientes_service._clients_cache.lock:
        clientes_service._clients_cache.count = 10
    mock_supabase_exec.side_effect = ValueError("Unexpected error")

    result = count_clients()
    assert result == 10


def test_count_clients_thread_safety(mock_supabase_exec: Mock, reset_last_clients_count: None) -> None:
    """count_clients mantém cache consistente em multi-threading (basic check)."""
    mock_response = Mock()
    mock_response.count = 77
    mock_supabase_exec.return_value = mock_response

    results: list[int] = []

    def worker() -> None:
        results.append(count_clients())

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Todos devem ter retornado 77
    assert all(r == 77 for r in results)
    # BUG-002: Verificar cache
    with clientes_service._clients_cache.lock:
        assert clientes_service._clients_cache.count == 77


# ==========================================
# Testes: _normalize_payload
# ==========================================
def test_normalize_payload_all_fields() -> None:
    """_normalize_payload extrai e normaliza todos os campos corretamente."""
    valores = {
        "Razão Social": " Empresa ABC ",
        "CNPJ": " 12.345.678/0001-10 ",
        "Nome": " João ",
        "WhatsApp": " 11987654321 ",
        "Observações": " Cliente VIP ",
    }
    razao, cnpj, cnpj_norm, nome, numero, obs = _normalize_payload(valores)
    assert razao == "Empresa ABC"
    assert cnpj == "12.345.678/0001-10"
    assert cnpj_norm == "12345678000110"
    assert nome == "João"
    assert numero == "11987654321"
    assert obs == "Cliente VIP"


def test_normalize_payload_fallback_keys() -> None:
    """_normalize_payload usa keys alternativas (razao_social, telefone, etc)."""
    valores = {
        "razao_social": "Empresa XYZ",
        "cnpj": "11.222.333/0001-65",
        "nome": "Maria",
        "Telefone": "21999887766",
        "Obs": "Observação curta",
    }
    razao, cnpj, cnpj_norm, nome, numero, obs = _normalize_payload(valores)
    assert razao == "Empresa XYZ"
    assert cnpj == "11.222.333/0001-65"
    assert cnpj_norm == "11222333000165"
    assert nome == "Maria"
    assert numero == "21999887766"
    assert obs == "Observação curta"


def test_normalize_payload_empty_strings() -> None:
    """_normalize_payload retorna strings vazias para valores ausentes."""
    valores: dict[str, Any] = {}
    razao, cnpj, cnpj_norm, nome, numero, obs = _normalize_payload(valores)
    assert razao == ""
    assert cnpj == ""
    assert cnpj_norm == ""
    assert nome == ""
    assert numero == ""
    assert obs == ""


def test_normalize_payload_whitespace_only() -> None:
    """_normalize_payload trata campos com apenas espaços como vazios."""
    valores = {
        "Razão Social": "   ",
        "CNPJ": "\t\n",
        "Nome": " ",
        "WhatsApp": "  ",
    }
    razao, cnpj, cnpj_norm, nome, numero, obs = _normalize_payload(valores)
    assert razao == ""
    assert cnpj == ""
    assert cnpj_norm == ""
    assert nome == ""
    assert numero == ""


def test_normalize_payload_multiple_keys_priority() -> None:
    """_normalize_payload usa o primeiro valor não-vazio entre keys alternativas."""
    # Fornece "Razão Social" e "razao_social" - deve pegar "Razão Social"
    valores = {
        "Razão Social": "Empresa A",
        "razao_social": "Empresa B",
        "CNPJ": "",
        "cnpj": "12.345.678/0001-10",
    }
    razao, cnpj, cnpj_norm, nome, numero, obs = _normalize_payload(valores)
    assert razao == "Empresa A"
    assert cnpj == "12.345.678/0001-10"


# ==========================================
# Testes: checar_duplicatas_info
# ==========================================
def test_checar_duplicatas_no_conflicts(mock_db_manager: dict[str, Mock]) -> None:
    """checar_duplicatas_info retorna vazios quando não há conflitos."""
    mock_db_manager["find_cliente_by_cnpj_norm"].return_value = None
    mock_db_manager["list_clientes"].return_value = []

    result = checar_duplicatas_info(
        numero="11987654321",
        cnpj="12.345.678/0001-10",
        nome="João",
        razao="Empresa ABC",
    )

    assert result["cnpj_conflict"] is None
    assert result["razao_conflicts"] == []
    assert result["cnpj_norm"] == "12345678000110"
    assert result["razao_norm"] == "Empresa ABC"  # normalize_text apenas faz strip(), não lowercase


def test_checar_duplicatas_cnpj_conflict(mock_db_manager: dict[str, Mock]) -> None:
    """checar_duplicatas_info retorna cnpj_conflict quando CNPJ duplicado."""
    fake_cliente = MagicMock()
    fake_cliente.id = 50
    fake_cliente.razao_social = "Empresa Existente"
    fake_cliente.cnpj = "12.345.678/0001-10"
    mock_db_manager["find_cliente_by_cnpj_norm"].return_value = fake_cliente
    mock_db_manager["list_clientes"].return_value = []

    result = checar_duplicatas_info(
        numero="11999888777",
        cnpj="12.345.678/0001-10",
        nome="Pedro",
        razao="Empresa Nova",
    )

    assert result["cnpj_conflict"] == fake_cliente
    assert result["razao_conflicts"] == []


def test_checar_duplicatas_razao_conflict(mock_db_manager: dict[str, Mock]) -> None:
    """checar_duplicatas_info retorna razao_conflicts quando Razão Social normalizada coincide."""
    mock_db_manager["find_cliente_by_cnpj_norm"].return_value = None

    # Cliente existente: mesma razão normalizada (após strip), CNPJ diferente
    fake_cliente = MagicMock()
    fake_cliente.id = 60
    fake_cliente.razao_social = "  Empresa ABC  "  # Após strip: "Empresa ABC"
    fake_cliente.cnpj = "11.222.333/0001-65"
    fake_cliente.cnpj_norm = "11222333000165"

    mock_db_manager["list_clientes"].return_value = [fake_cliente]

    result = checar_duplicatas_info(
        numero="11987654321",
        cnpj="12.345.678/0001-10",
        nome="João",
        razao="Empresa ABC",  # Após strip: "Empresa ABC" - match!
    )

    assert result["cnpj_conflict"] is None
    razao_conflicts = result["razao_conflicts"]
    assert isinstance(razao_conflicts, list)
    assert len(razao_conflicts) == 1
    assert razao_conflicts[0].id == 60


def test_checar_duplicatas_exclude_id(mock_db_manager: dict[str, Mock]) -> None:
    """checar_duplicatas_info ignora conflitos com exclude_id."""
    # Cliente existente que seria conflito, mas é exclude_id
    fake_cliente = MagicMock()
    fake_cliente.id = 70
    fake_cliente.razao_social = "Empresa ABC"
    fake_cliente.cnpj = "12.345.678/0001-10"
    fake_cliente.cnpj_norm = "12345678000110"

    mock_db_manager["find_cliente_by_cnpj_norm"].return_value = None  # já passa exclude_id internamente
    mock_db_manager["list_clientes"].return_value = [fake_cliente]

    result = checar_duplicatas_info(
        numero="11987654321",
        cnpj="12.345.678/0001-10",
        nome="João",
        razao="Empresa ABC",
        exclude_id=70,
    )

    # CNPJ conflict: None porque find_cliente_by_cnpj_norm já filtra exclude_id
    # razao_conflict: [] porque o único cliente tem id 70
    assert result["cnpj_conflict"] is None
    assert result["razao_conflicts"] == []


def test_checar_duplicatas_empty_cnpj_razao(mock_db_manager: dict[str, Mock]) -> None:
    """checar_duplicatas_info com CNPJ/razão vazios retorna None/[]."""
    mock_db_manager["find_cliente_by_cnpj_norm"].return_value = None
    mock_db_manager["list_clientes"].return_value = []

    result = checar_duplicatas_info(
        numero="11987654321",
        cnpj="",
        nome="João",
        razao="",
    )

    assert result["cnpj_conflict"] is None
    assert result["razao_conflicts"] == []
    assert result["cnpj_norm"] == ""
    assert result["razao_norm"] == ""


def test_checar_duplicatas_razao_same_cnpj_norm(mock_db_manager: dict[str, Mock]) -> None:
    """checar_duplicatas_info não retorna razao_conflict se cliente tem mesmo CNPJ."""
    mock_db_manager["find_cliente_by_cnpj_norm"].return_value = None

    fake_cliente = MagicMock()
    fake_cliente.id = 80
    fake_cliente.razao_social = "Empresa ABC"
    fake_cliente.cnpj = "12.345.678/0001-10"
    fake_cliente.cnpj_norm = "12345678000110"

    mock_db_manager["list_clientes"].return_value = [fake_cliente]

    result = checar_duplicatas_info(
        numero="11987654321",
        cnpj="12.345.678/0001-10",
        nome="João",
        razao="Empresa ABC",
    )

    # Mesmo CNPJ normalizado -> não é razao_conflict
    assert result["razao_conflicts"] == []


# ==========================================
# Testes: salvar_cliente (criação)
# ==========================================
def test_salvar_cliente_create_success(
    mock_db_manager: dict[str, Mock],
    mock_audit_log: Mock,
    mock_session_user: Mock,
    mock_pasta_helpers: dict[str, Any],
) -> None:
    """salvar_cliente cria novo cliente quando row=None e retorna ID + pasta."""
    # Configurar mock_db_manager
    mock_db_manager["find_cliente_by_cnpj_norm"].return_value = None
    mock_db_manager["insert_cliente"].return_value = 101

    valores = {
        "Razão Social": "Empresa ABC",
        "CNPJ": "12.345.678/0001-10",
        "Nome": "João",
        "WhatsApp": "11987654321",
        "Observações": "Cliente VIP",
    }

    pk, pasta = salvar_cliente(row=None, valores=valores)

    # Verifica retorno
    assert pk == 101
    assert "12345678000110" in pasta or "Empresa" in pasta or "101" in pasta

    # Verifica chamada a insert_cliente
    mock_db_manager["insert_cliente"].assert_called_once()
    call_kwargs = mock_db_manager["insert_cliente"].call_args[1]
    assert call_kwargs["numero"] == "11987654321"
    assert call_kwargs["nome"] == "João"
    assert call_kwargs["razao_social"] == "Empresa ABC"
    assert call_kwargs["cnpj"] == "12.345.678/0001-10"
    assert call_kwargs["cnpj_norm"] == "12345678000110"
    assert call_kwargs["obs"] == "Cliente VIP"

    # Verifica auditoria
    mock_audit_log.assert_called_once_with("test_user", 101, "criacao")


def test_salvar_cliente_create_minimal_data(
    mock_db_manager: dict[str, Mock],
    mock_audit_log: Mock,
    mock_session_user: Mock,
    mock_pasta_helpers: dict[str, Any],
) -> None:
    """salvar_cliente aceita criação com apenas Razão Social preenchida."""
    mock_db_manager["find_cliente_by_cnpj_norm"].return_value = None
    mock_db_manager["insert_cliente"].return_value = 102

    valores = {"Razão Social": "Empresa Mínima"}

    pk, pasta = salvar_cliente(row=None, valores=valores)
    assert pk == 102
    mock_db_manager["insert_cliente"].assert_called_once()


def test_salvar_cliente_create_no_data_raises(
    mock_db_manager: dict[str, Mock],
) -> None:
    """salvar_cliente levanta ValueError se não houver dados mínimos."""
    valores: dict[str, Any] = {}
    with pytest.raises(ValueError, match="Preencha pelo menos"):
        salvar_cliente(row=None, valores=valores)

    mock_db_manager["insert_cliente"].assert_not_called()


def test_salvar_cliente_create_cnpj_conflict_raises(
    mock_db_manager: dict[str, Mock],
) -> None:
    """salvar_cliente levanta ValueError se CNPJ já cadastrado."""
    fake_cliente = MagicMock()
    fake_cliente.id = 50
    fake_cliente.razao_social = "Empresa Existente"
    fake_cliente.cnpj = "12.345.678/0001-10"
    mock_db_manager["find_cliente_by_cnpj_norm"].return_value = fake_cliente

    valores = {
        "Razão Social": "Empresa Nova",
        "CNPJ": "12.345.678/0001-10",
    }

    with pytest.raises(ValueError, match="CNPJ já cadastrado"):
        salvar_cliente(row=None, valores=valores)

    mock_db_manager["insert_cliente"].assert_not_called()


# ==========================================
# Testes: salvar_cliente (update)
# ==========================================
def test_salvar_cliente_update_success(
    mock_db_manager: dict[str, Mock],
    mock_audit_log: Mock,
    mock_session_user: Mock,
    mock_pasta_helpers: dict[str, Any],
) -> None:
    """salvar_cliente atualiza cliente existente quando row != None."""
    mock_db_manager["find_cliente_by_cnpj_norm"].return_value = None
    mock_db_manager["update_cliente"].return_value = None

    row = (99, "11987654321", "João Antigo", "Empresa ABC", "12.345.678/0001-10", "Obs antiga")
    valores = {
        "Razão Social": "Empresa ABC Atualizada",
        "CNPJ": "12.345.678/0001-10",
        "Nome": "João Silva",
        "WhatsApp": "11999888777",
        "Observações": "Obs nova",
    }

    pk, pasta = salvar_cliente(row=row, valores=valores)

    assert pk == 99
    # Verifica chamada a update_cliente
    mock_db_manager["update_cliente"].assert_called_once_with(
        99,
        numero="11999888777",
        nome="João Silva",
        razao_social="Empresa ABC Atualizada",
        cnpj="12.345.678/0001-10",
        obs="Obs nova",
        cnpj_norm="12345678000110",
    )

    # Verifica auditoria com "edicao"
    mock_audit_log.assert_called_once_with("test_user", 99, "edicao")


def test_salvar_cliente_update_cnpj_conflict_exclude_self(
    mock_db_manager: dict[str, Mock],
    mock_audit_log: Mock,
    mock_session_user: Mock,
    mock_pasta_helpers: dict[str, Any],
) -> None:
    """salvar_cliente permite update se CNPJ conflitante é o próprio cliente."""
    # Cliente 99 já tem CNPJ 12.345.678/0001-10
    # find_cliente_by_cnpj_norm retorna None porque exclude_id=99
    mock_db_manager["find_cliente_by_cnpj_norm"].return_value = None

    row = (99, "11987654321", "João", "Empresa ABC", "12.345.678/0001-10", "")
    valores = {
        "Razão Social": "Empresa ABC",
        "CNPJ": "12.345.678/0001-10",  # Mesmo CNPJ
    }

    pk, pasta = salvar_cliente(row=row, valores=valores)
    assert pk == 99
    # Verifica que find_cliente_by_cnpj_norm foi chamado com exclude_id=99
    mock_db_manager["find_cliente_by_cnpj_norm"].assert_called_once_with("12345678000110", exclude_id=99)


def test_salvar_cliente_update_cnpj_conflict_other_raises(
    mock_db_manager: dict[str, Mock],
) -> None:
    """salvar_cliente levanta ValueError se update tentar usar CNPJ de outro cliente."""
    fake_cliente = MagicMock()
    fake_cliente.id = 50
    fake_cliente.razao_social = "Empresa Existente"
    fake_cliente.cnpj = "11.222.333/0001-65"
    mock_db_manager["find_cliente_by_cnpj_norm"].return_value = fake_cliente

    row = (99, "11987654321", "João", "Empresa ABC", "12.345.678/0001-10", "")
    valores = {
        "Razão Social": "Empresa ABC",
        "CNPJ": "11.222.333/0001-65",  # CNPJ do cliente 50
    }

    with pytest.raises(ValueError, match="CNPJ já cadastrado"):
        salvar_cliente(row=row, valores=valores)

    mock_db_manager["update_cliente"].assert_not_called()


# ==========================================
# Testes: _pasta_do_cliente
# ==========================================
def test_pasta_do_cliente_cloud_only(
    monkeypatch: pytest.MonkeyPatch,
    mock_pasta_helpers: dict[str, Any],
) -> None:
    """_pasta_do_cliente retorna path sem criar pasta se CLOUD_ONLY=True."""
    monkeypatch.setattr("src.core.services.clientes_service.CLOUD_ONLY", True)

    pasta = _pasta_do_cliente(pk=101, cnpj="12.345.678/0001-10", numero="11987654321", razao="Empresa ABC")

    assert os.path.isabs(pasta)
    # Não deve chamar ensure_subpastas nem write_marker
    mock_pasta_helpers["ensure_subpastas"].assert_not_called()
    mock_pasta_helpers["write_marker"].assert_not_called()


def test_pasta_do_cliente_local_fs(
    monkeypatch: pytest.MonkeyPatch,
    mock_pasta_helpers: dict[str, Any],
) -> None:
    """_pasta_do_cliente cria pasta e marker se CLOUD_ONLY=False."""
    monkeypatch.setattr("src.core.services.clientes_service.CLOUD_ONLY", False)

    pasta = _pasta_do_cliente(pk=102, cnpj="11.222.333/0001-65", numero="21999887766", razao="Empresa XYZ")

    assert os.path.isabs(pasta)
    # Deve chamar ensure_subpastas e write_marker
    mock_pasta_helpers["ensure_subpastas"].assert_called_once_with(pasta)
    mock_pasta_helpers["write_marker"].assert_called_once_with(pasta, 102)


def test_pasta_do_cliente_safe_base_integration(
    monkeypatch: pytest.MonkeyPatch,
    mock_pasta_helpers: dict[str, Any],
) -> None:
    """_pasta_do_cliente usa safe_base_from_fields corretamente."""
    monkeypatch.setattr("src.core.services.clientes_service.CLOUD_ONLY", True)
    tmp = mock_pasta_helpers["tmp_path"]

    pasta = _pasta_do_cliente(pk=103, cnpj="12.345.678/0001-10", numero="", razao="")

    # Deve conter o ID 103 e estar dentro do tmp_path
    assert str(tmp) in pasta
    assert "103" in pasta or "12345678000110" in pasta


# ==========================================
# Testes: auditoria e edge cases
# ==========================================
def test_salvar_cliente_auditoria_failure_does_not_raise(
    mock_db_manager: dict[str, Mock],
    mock_audit_log: Mock,
    mock_session_user: Mock,
    mock_pasta_helpers: dict[str, Any],
) -> None:
    """salvar_cliente não levanta exceção se auditoria falhar."""
    mock_db_manager["find_cliente_by_cnpj_norm"].return_value = None
    mock_db_manager["insert_cliente"].return_value = 104
    # Simular falha na auditoria
    mock_audit_log.side_effect = RuntimeError("Audit log failure")

    valores = {"Razão Social": "Empresa Test"}

    # Não deve levantar exceção
    pk, pasta = salvar_cliente(row=None, valores=valores)
    assert pk == 104


def test_salvar_cliente_current_user_none(
    mock_db_manager: dict[str, Mock],
    mock_audit_log: Mock,
    monkeypatch: pytest.MonkeyPatch,
    mock_pasta_helpers: dict[str, Any],
) -> None:
    """salvar_cliente lida com get_current_user retornando None."""
    mock_db_manager["find_cliente_by_cnpj_norm"].return_value = None
    mock_db_manager["insert_cliente"].return_value = 105
    monkeypatch.setattr("src.core.services.clientes_service.get_current_user", lambda: None)

    valores = {"Razão Social": "Empresa Test"}

    pk, pasta = salvar_cliente(row=None, valores=valores)
    assert pk == 105
    # Auditoria deve ser chamada com user=""
    mock_audit_log.assert_called_once_with("", 105, "criacao")
