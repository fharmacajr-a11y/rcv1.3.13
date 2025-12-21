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
