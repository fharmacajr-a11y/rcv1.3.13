# tests/test_infra_healthcheck_fase37.py
"""
Testes para o módulo infra/healthcheck.py (COV-INFRA-003).
Objetivo: Aumentar cobertura para 100%.

Funções testadas:
- db_check(): INSERT + DELETE em test_health
- storage_check(): Verifica bucket storage
- healthcheck(): Função principal que orquestra todos os checks
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


# ========================================
# Testes de db_check
# ========================================


def test_db_check_success():
    """Testa db_check quando INSERT e DELETE funcionam corretamente."""
    from src.infra.healthcheck import db_check

    # Mock do Supabase client
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_insert = MagicMock()
    mock_delete = MagicMock()
    mock_execute = MagicMock()

    # Configurar cadeia de mocks
    mock_sb.table.return_value = mock_table
    mock_table.insert.return_value = mock_insert
    mock_insert.execute.return_value = mock_execute
    mock_table.delete.return_value = mock_delete
    mock_delete.eq.return_value = mock_delete
    mock_delete.execute.return_value = mock_execute

    with patch("src.infra.healthcheck.get_supabase", return_value=mock_sb):
        ok, msg = db_check()

    assert ok is True
    assert msg == "insert/delete OK"
    assert mock_sb.table.call_count == 2  # insert e delete
    mock_sb.table.assert_any_call("test_health")


def test_db_check_insert_failure():
    """Testa db_check quando INSERT falha."""
    from src.infra.healthcheck import db_check

    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_insert = MagicMock()

    mock_sb.table.return_value = mock_table
    mock_table.insert.return_value = mock_insert
    mock_insert.execute.side_effect = Exception("Permission denied on table test_health")

    with patch("src.infra.healthcheck.get_supabase", return_value=mock_sb):
        ok, msg = db_check()

    assert ok is False
    assert "DB health falhou" in msg
    assert "Permission denied" in msg


def test_db_check_delete_failure():
    """Testa db_check quando DELETE falha."""
    from src.infra.healthcheck import db_check

    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_insert = MagicMock()
    mock_delete = MagicMock()
    mock_execute_success = MagicMock()

    # INSERT funciona
    mock_sb.table.return_value = mock_table
    mock_table.insert.return_value = mock_insert
    mock_insert.execute.return_value = mock_execute_success

    # DELETE falha
    mock_table.delete.return_value = mock_delete
    mock_delete.eq.return_value = mock_delete
    mock_delete.execute.side_effect = Exception("Network timeout on delete")

    with patch("src.infra.healthcheck.get_supabase", return_value=mock_sb):
        ok, msg = db_check()

    assert ok is False
    assert "DB health falhou" in msg
    assert "Network timeout" in msg


# ========================================
# Testes de storage_check
# ========================================


def test_storage_check_success():
    """Testa storage_check quando bucket é acessível e retorna lista."""
    from src.infra.healthcheck import storage_check

    mock_sb = MagicMock()
    mock_storage = MagicMock()
    mock_from = MagicMock()

    # Simular retorno de lista com 3 arquivos
    mock_from.list.return_value = ["file1.txt", "file2.pdf", "file3.zip"]

    mock_sb.storage.from_.return_value = mock_from
    mock_storage.from_.return_value = mock_from

    with patch("src.infra.healthcheck.get_supabase", return_value=mock_sb):
        ok, info = storage_check("rc-docs")

    assert ok is True
    assert info["count"] == 3
    mock_sb.storage.from_.assert_called_once_with("rc-docs")


def test_storage_check_empty_bucket():
    """Testa storage_check quando bucket está vazio."""
    from src.infra.healthcheck import storage_check

    mock_sb = MagicMock()
    mock_from = MagicMock()
    mock_from.list.return_value = []

    mock_sb.storage.from_.return_value = mock_from

    with patch("src.infra.healthcheck.get_supabase", return_value=mock_sb):
        ok, info = storage_check("empty-bucket")

    assert ok is True
    assert info["count"] == 0


def test_storage_check_non_list_response():
    """Testa storage_check quando resposta não é lista (caso inesperado)."""
    from src.infra.healthcheck import storage_check

    mock_sb = MagicMock()
    mock_from = MagicMock()
    mock_from.list.return_value = {"data": []}  # Dict ao invés de lista

    mock_sb.storage.from_.return_value = mock_from

    with patch("src.infra.healthcheck.get_supabase", return_value=mock_sb):
        ok, info = storage_check("weird-bucket")

    assert ok is True
    assert info["count"] is None  # Quando não é lista


def test_storage_check_failure():
    """Testa storage_check quando acesso ao bucket falha."""
    from src.infra.healthcheck import storage_check

    mock_sb = MagicMock()
    mock_from = MagicMock()
    mock_from.list.side_effect = Exception("Bucket not found: rc-docs")

    mock_sb.storage.from_.return_value = mock_from

    with patch("src.infra.healthcheck.get_supabase", return_value=mock_sb):
        ok, info = storage_check("rc-docs")

    assert ok is False
    assert "error" in info
    assert "Bucket not found" in info["error"]


# ========================================
# Testes de healthcheck (função principal)
# ========================================


def test_healthcheck_all_success():
    """Testa healthcheck quando todos os checks passam."""
    from src.infra.healthcheck import healthcheck

    # Mock SessionGuard
    with patch("src.infra.healthcheck.SessionGuard.ensure_alive", return_value=True):
        # Mock storage_check
        with patch("src.infra.healthcheck.storage_check", return_value=(True, {"count": 5})):
            # Mock db_check
            with patch("src.infra.healthcheck.db_check", return_value=(True, "insert/delete OK")):
                result = healthcheck(bucket="test-bucket")

    assert result["ok"] is True
    assert result["bucket"] == "test-bucket"
    assert result["items"]["session"]["ok"] is True
    assert result["items"]["storage"]["ok"] is True
    assert result["items"]["storage"]["count"] == 5
    assert result["items"]["db"]["ok"] is True
    assert result["items"]["db"]["msg"] == "insert/delete OK"


def test_healthcheck_session_failure():
    """Testa healthcheck quando sessão falha."""
    from src.infra.healthcheck import healthcheck

    with patch("src.infra.healthcheck.SessionGuard.ensure_alive", return_value=False):
        with patch("src.infra.healthcheck.storage_check", return_value=(True, {"count": 5})):
            with patch("src.infra.healthcheck.db_check", return_value=(True, "insert/delete OK")):
                result = healthcheck()

    assert result["ok"] is False  # Falha geral
    assert result["items"]["session"]["ok"] is False
    assert result["items"]["storage"]["ok"] is True  # Outros passam
    assert result["items"]["db"]["ok"] is True


def test_healthcheck_storage_failure():
    """Testa healthcheck quando storage falha."""
    from src.infra.healthcheck import healthcheck

    with patch("src.infra.healthcheck.SessionGuard.ensure_alive", return_value=True):
        with patch("src.infra.healthcheck.storage_check", return_value=(False, {"error": "Connection timeout"})):
            with patch("src.infra.healthcheck.db_check", return_value=(True, "insert/delete OK")):
                result = healthcheck()

    assert result["ok"] is False
    assert result["items"]["session"]["ok"] is True
    assert result["items"]["storage"]["ok"] is False
    assert result["items"]["storage"]["error"] == "Connection timeout"
    assert result["items"]["db"]["ok"] is True


def test_healthcheck_db_failure():
    """Testa healthcheck quando DB check falha."""
    from src.infra.healthcheck import healthcheck

    with patch("src.infra.healthcheck.SessionGuard.ensure_alive", return_value=True):
        with patch("src.infra.healthcheck.storage_check", return_value=(True, {"count": 2})):
            with patch(
                "src.infra.healthcheck.db_check", return_value=(False, "DB health falhou: RLS policy violation")
            ):
                result = healthcheck()

    assert result["ok"] is False
    assert result["items"]["session"]["ok"] is True
    assert result["items"]["storage"]["ok"] is True
    assert result["items"]["db"]["ok"] is False
    assert "RLS policy violation" in result["items"]["db"]["msg"]


def test_healthcheck_multiple_failures():
    """Testa healthcheck quando múltiplos checks falham."""
    from src.infra.healthcheck import healthcheck

    with patch("src.infra.healthcheck.SessionGuard.ensure_alive", return_value=False):
        with patch("src.infra.healthcheck.storage_check", return_value=(False, {"error": "Network error"})):
            with patch("src.infra.healthcheck.db_check", return_value=(False, "DB health falhou: Connection lost")):
                result = healthcheck(bucket="prod-bucket")

    assert result["ok"] is False
    assert result["bucket"] == "prod-bucket"
    assert result["items"]["session"]["ok"] is False
    assert result["items"]["storage"]["ok"] is False
    assert result["items"]["db"]["ok"] is False


def test_healthcheck_db_failure_logs_warning():
    """Testa que healthcheck loga warning quando DB falha."""
    from src.infra.healthcheck import healthcheck

    with patch("src.infra.healthcheck.SessionGuard.ensure_alive", return_value=True):
        with patch("src.infra.healthcheck.storage_check", return_value=(True, {"count": 1})):
            with patch("src.infra.healthcheck.db_check", return_value=(False, "DB health falhou: timeout")):
                with patch("src.infra.healthcheck.log") as mock_log:
                    result = healthcheck()

    # Verificar que warning foi logado
    mock_log.warning.assert_called_once()
    call_args = mock_log.warning.call_args[0]
    assert "HealthCheck DB FAIL" in call_args[0]
    assert "timeout" in call_args[1]

    assert result["items"]["db"]["ok"] is False


def test_healthcheck_session_none_treated_as_false():
    """Testa que healthcheck trata None de ensure_alive como False."""
    from src.infra.healthcheck import healthcheck

    with patch("src.infra.healthcheck.SessionGuard.ensure_alive", return_value=None):
        with patch("src.infra.healthcheck.storage_check", return_value=(True, {"count": 0})):
            with patch("src.infra.healthcheck.db_check", return_value=(True, "insert/delete OK")):
                result = healthcheck()

    # None é tratado como falsy
    assert result["ok"] is False
    assert result["items"]["session"]["ok"] is False


def test_healthcheck_default_bucket():
    """Testa que healthcheck usa bucket padrão 'rc-docs'."""
    from src.infra.healthcheck import healthcheck

    with patch("src.infra.healthcheck.SessionGuard.ensure_alive", return_value=True):
        with patch("src.infra.healthcheck.storage_check", return_value=(True, {"count": 10})) as mock_storage:
            with patch("src.infra.healthcheck.db_check", return_value=(True, "insert/delete OK")):
                result = healthcheck()  # Sem especificar bucket

    # Verificar que storage_check foi chamado com bucket padrão
    mock_storage.assert_called_once_with("rc-docs")
    assert result["bucket"] == "rc-docs"


def test_healthcheck_custom_bucket():
    """Testa que healthcheck aceita bucket customizado."""
    from src.infra.healthcheck import healthcheck

    with patch("src.infra.healthcheck.SessionGuard.ensure_alive", return_value=True):
        with patch("src.infra.healthcheck.storage_check", return_value=(True, {"count": 7})) as mock_storage:
            with patch("src.infra.healthcheck.db_check", return_value=(True, "insert/delete OK")):
                result = healthcheck(bucket="custom-bucket")

    mock_storage.assert_called_once_with("custom-bucket")
    assert result["bucket"] == "custom-bucket"


# ========================================
# Testes de UUIDs únicos em db_check
# ========================================


def test_db_check_uses_unique_uuids():
    """Testa que db_check usa UUIDs únicos para cada execução."""
    from src.infra.healthcheck import db_check

    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_insert = MagicMock()
    mock_delete = MagicMock()

    mock_sb.table.return_value = mock_table
    mock_table.insert.return_value = mock_insert
    mock_insert.execute.return_value = MagicMock()
    mock_table.delete.return_value = mock_delete
    mock_delete.eq.return_value = mock_delete
    mock_delete.execute.return_value = MagicMock()

    with patch("src.infra.healthcheck.get_supabase", return_value=mock_sb):
        # Primeira chamada
        db_check()
        first_insert_call = mock_table.insert.call_args_list[0][0][0]
        first_id = first_insert_call["id"]
        first_instance = first_insert_call["instance"]

        # Resetar mocks
        mock_table.reset_mock()

        # Segunda chamada
        db_check()
        second_insert_call = mock_table.insert.call_args_list[0][0][0]
        second_id = second_insert_call["id"]
        second_instance = second_insert_call["instance"]

    # UUIDs devem ser diferentes
    assert first_id != second_id
    assert first_instance != second_instance

    # Verificar formato UUID
    import uuid

    uuid.UUID(first_id)  # Não deve levantar exceção
    uuid.UUID(second_id)
