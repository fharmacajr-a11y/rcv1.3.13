"""Testes para utilitários de tratamento de erros do módulo ANVISA."""

import logging


from src.modules.anvisa.utils.anvisa_errors import (
    extract_postgrest_error,
    log_exception,
    user_message_from_error,
)


def test_extract_postgrest_error_with_attributes():
    """Testa extração de erro com atributos."""
    exc = Exception("test error")
    exc.code = "23514"
    exc.message = "Check constraint violation"
    exc.details = "Some detail"
    exc.hint = "Some hint"

    result = extract_postgrest_error(exc)

    assert result["code"] == "23514"
    assert result["message"] == "Check constraint violation"
    assert result["details"] == "Some detail"
    assert result["hint"] == "Some hint"


def test_extract_postgrest_error_with_dict_args():
    """Testa extração de erro com dict nos args."""
    payload = {
        "code": "23503",
        "message": "Foreign key violation",
        "details": "Detail here",
        "hint": "Hint here",
    }
    exc = Exception(payload)

    result = extract_postgrest_error(exc)

    assert result["code"] == "23503"
    assert result["message"] == "Foreign key violation"
    assert result["details"] == "Detail here"
    assert result["hint"] == "Hint here"


def test_extract_postgrest_error_fallback():
    """Testa fallback para exceção simples."""
    exc = ValueError("Simple error message")

    result = extract_postgrest_error(exc)

    assert result["code"] is None
    assert result["message"] == "Simple error message"
    assert result["details"] is None
    assert result["hint"] is None


def test_user_message_from_error_constraint_violation():
    """Testa mensagem para violação de constraint."""
    err = {"code": "23514", "message": "Check constraint violated"}

    result = user_message_from_error(err, default="Erro genérico")

    assert "Dados inválidos" in result
    assert "status/tipo" in result
    assert "Check constraint violated" in result


def test_user_message_from_error_foreign_key():
    """Testa mensagem para violação de foreign key."""
    err = {"code": "23503", "message": "FK violation"}

    result = user_message_from_error(err, default="Erro genérico")

    assert "Referência inválida" in result
    assert "cliente ou organização" in result


def test_user_message_from_error_permission():
    """Testa mensagem para erro de permissão."""
    err = {"code": "42501"}

    result = user_message_from_error(err, default="Erro genérico")

    assert "Sem permissão" in result


def test_user_message_from_error_not_found():
    """Testa mensagem para registro não encontrado."""
    err = {"code": "PGRST116"}

    result = user_message_from_error(err, default="Erro genérico")

    assert "Registro não encontrado" in result


def test_user_message_from_error_default():
    """Testa fallback para mensagem padrão."""
    err = {"code": "99999", "message": "Unknown error"}

    result = user_message_from_error(err, default="Erro personalizado")

    assert "Erro personalizado" in result
    assert "Unknown error" in result


def test_user_message_from_error_long_message_truncated():
    """Testa que mensagens longas não são adicionadas."""
    err = {
        "code": "23514",
        "message": "A" * 200,  # Mensagem muito longa
    }

    result = user_message_from_error(err, default="Erro")

    # Mensagem base deve estar presente
    assert "Dados inválidos" in result

    # Mensagem longa NÃO deve estar presente
    assert "A" * 200 not in result


def test_user_message_from_error_no_code():
    """Testa mensagem quando não há código."""
    err = {"message": "Generic error"}

    result = user_message_from_error(err, default="Erro padrão")

    assert "Erro padrão" in result
    assert "Generic error" in result


def test_log_exception_with_context(caplog):
    """Testa log de exceção com contexto."""
    logger = logging.getLogger("test")
    logger.setLevel(logging.DEBUG)

    exc = ValueError("Test exception")

    with caplog.at_level(logging.ERROR):
        log_exception(
            logger,
            "Erro ao processar",
            exc,
            org_id="org-123",
            client_id=456,
            action="test",
        )

    # Verificar que log foi criado
    assert len(caplog.records) == 1
    record = caplog.records[0]

    # Verificar mensagem
    assert "Erro ao processar" in record.message
    assert "org=org-123" in record.message
    assert "client=456" in record.message
    assert "action=test" in record.message

    # Verificar que exc_info foi incluído
    assert record.exc_info is not None


def test_log_exception_without_context(caplog):
    """Testa log de exceção sem contexto."""
    logger = logging.getLogger("test")
    logger.setLevel(logging.DEBUG)

    exc = RuntimeError("Another exception")

    with caplog.at_level(logging.ERROR):
        log_exception(logger, "Erro simples", exc)

    # Verificar que log foi criado
    assert len(caplog.records) == 1
    record = caplog.records[0]

    # Verificar mensagem (sem contexto adicional)
    assert "Erro simples" in record.message
    assert "org=" not in record.message

    # Verificar que exc_info foi incluído
    assert record.exc_info is not None


# ===== Testes adicionais de cobertura =====


def test_extract_postgrest_error_mixed_sources():
    """Testa extração com atributos E dict args (dict tem prioridade)."""
    exc = Exception({"code": "DICT_CODE", "message": "Dict message"})
    exc.code = "ATTR_CODE"
    exc.message = "Attr message"

    result = extract_postgrest_error(exc)

    # Dict deve ter prioridade
    assert result["code"] == "DICT_CODE"
    assert result["message"] == "Dict message"


def test_extract_postgrest_error_partial_attributes():
    """Testa extração com apenas alguns atributos."""
    exc = Exception("fallback message")
    exc.code = "PARTIAL"
    # Sem message, details, hint

    result = extract_postgrest_error(exc)

    assert result["code"] == "PARTIAL"
    assert result["message"] == "fallback message"
    assert result["details"] is None
    assert result["hint"] is None


def test_user_message_from_error_connection_errors():
    """Testa mensagens para erros de conexão."""
    # Erro de conexão genérico
    err = {"code": "08000"}
    result = user_message_from_error(err)
    assert "Erro de conexão" in result

    # Conexão perdida
    err = {"code": "08006"}
    result = user_message_from_error(err)
    assert "Conexão perdida" in result


def test_user_message_from_error_unique_constraint():
    """Testa mensagem para violação de unique constraint."""
    err = {"code": "23505", "message": "Duplicate key"}
    result = user_message_from_error(err)
    assert "duplicação" in result


def test_user_message_from_error_empty_dict():
    """Testa mensagem com dict vazio."""
    err = {}
    result = user_message_from_error(err, default="Erro vazio")
    assert "Erro vazio" in result


def test_user_message_from_error_short_message_included():
    """Testa que mensagem curta é incluída nos detalhes."""
    err = {"code": "23514", "message": "Short msg"}
    result = user_message_from_error(err)

    assert "Dados inválidos" in result
    assert "Short msg" in result


def test_user_message_from_error_default_with_long_message():
    """Testa fallback com mensagem longa (não deve ser adicionada)."""
    long_msg = "x" * 200
    err = {"code": "UNKNOWN", "message": long_msg}
    result = user_message_from_error(err, default="Erro padrão")

    assert "Erro padrão" in result
    assert long_msg not in result


def test_log_exception_multiple_context_keys(caplog):
    """Testa log com múltiplos parâmetros de contexto."""
    logger = logging.getLogger("test_multi")
    logger.setLevel(logging.ERROR)

    exc = Exception("Multi-context error")

    with caplog.at_level(logging.ERROR):
        log_exception(
            logger,
            "Erro complexo",
            exc,
            org_id="org-999",
            client_id=789,
            request_id="req-abc",
            action="update",
            status="failed",
        )

    assert len(caplog.records) == 1
    record = caplog.records[0]

    # Verificar que todos os parâmetros aparecem (request_id vira "request=" no log)
    assert "org=org-999" in record.message
    assert "client=789" in record.message
    assert "request=req-abc" in record.message  # request_id → request
    assert "action=update" in record.message
    assert "status=failed" in record.message
