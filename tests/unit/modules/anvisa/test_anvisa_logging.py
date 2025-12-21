"""Testes para utilitários de logging do módulo ANVISA."""

import logging


from src.modules.anvisa.utils.anvisa_logging import (
    AnvisaContextFilter,
    add_anvisa_filter,
    fmt_ctx,
    get_anvisa_logger,
)


def test_get_anvisa_logger():
    """Testa criação de logger."""
    logger = get_anvisa_logger(__name__)
    assert isinstance(logger, logging.Logger)
    assert logger.name == __name__


def test_anvisa_context_filter_adds_missing_attributes():
    """Testa que o filter adiciona atributos ausentes."""
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="test",
        args=(),
        exc_info=None,
    )

    filt = AnvisaContextFilter()
    result = filt.filter(record)

    assert result is True
    assert hasattr(record, "org_id")
    assert hasattr(record, "client_id")
    assert hasattr(record, "request_id")
    assert hasattr(record, "action")
    assert record.org_id == "-"
    assert record.client_id == "-"
    assert record.request_id == "-"
    assert record.action == "-"


def test_anvisa_context_filter_preserves_existing_attributes():
    """Testa que o filter preserva atributos existentes."""
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="test",
        args=(),
        exc_info=None,
    )

    # Adicionar atributos customizados
    record.org_id = "org-123"
    record.client_id = "456"
    record.request_id = "req-789"
    record.action = "create"

    filt = AnvisaContextFilter()
    result = filt.filter(record)

    assert result is True
    assert record.org_id == "org-123"
    assert record.client_id == "456"
    assert record.request_id == "req-789"
    assert record.action == "create"


def test_add_anvisa_filter_idempotent():
    """Testa que add_anvisa_filter é idempotente."""
    logger = get_anvisa_logger("test_logger")

    # Remover filtros existentes
    logger.filters.clear()

    # Adicionar filter
    add_anvisa_filter(logger)
    assert len(logger.filters) == 1
    assert isinstance(logger.filters[0], AnvisaContextFilter)

    # Adicionar novamente (deve ser idempotente)
    add_anvisa_filter(logger)
    assert len(logger.filters) == 1


def test_fmt_ctx_with_all_fields():
    """Testa formatação de contexto com todos os campos."""
    result = fmt_ctx(
        org_id="org-123",
        client_id=456,
        request_id="req-789",
        action="create",
    )

    assert result == "org=org-123 client=456 request=req-789 action=create"


def test_fmt_ctx_with_partial_fields():
    """Testa formatação de contexto com campos parciais."""
    result = fmt_ctx(
        org_id="org-123",
        action="delete",
    )

    assert result == "org=org-123 action=delete"


def test_fmt_ctx_ignores_none_and_empty():
    """Testa que fmt_ctx ignora valores None e strings vazias."""
    result = fmt_ctx(
        org_id="org-123",
        client_id=None,
        request_id="",
        action="-",
    )

    assert result == "org=org-123"


def test_fmt_ctx_with_extra_fields():
    """Testa formatação com campos extras não padrão."""
    result = fmt_ctx(
        org_id="org-123",
        action="upload",
        file_name="test.pdf",
        size=1024,
    )

    # Campos padrão vêm primeiro
    assert "org=org-123" in result
    assert "action=upload" in result

    # Campos extras aparecem depois
    assert "file_name=test.pdf" in result
    assert "size=1024" in result


def test_fmt_ctx_empty():
    """Testa formatação com contexto vazio."""
    result = fmt_ctx()

    assert result == ""


def test_fmt_ctx_with_only_extras():
    """Testa formatação com apenas campos extras."""
    result = fmt_ctx(
        custom_field="value",
        another="test",
    )

    assert "custom_field=value" in result
    assert "another=test" in result
