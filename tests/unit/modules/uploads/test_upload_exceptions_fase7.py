"""Testes unitários para exceções do módulo de uploads.

FASE 7 - Cobertura de:
- Exceções tipadas (UploadError, UploadValidationError, etc.)
- Factory functions (make_validation_error, make_network_error, etc.)
- Mensagens de erro padronizadas
"""

from __future__ import annotations

import pytest

from src.modules.uploads.exceptions import (
    UploadError,
    UploadValidationError,
    UploadNetworkError,
    UploadServerError,
    ERROR_MESSAGES,
    make_validation_error,
    make_network_error,
    make_server_error,
)


# ============================================================================
# Testes de exceções base
# ============================================================================


class TestUploadError:
    """Testes para UploadError base."""

    def test_basic_creation(self) -> None:
        exc = UploadError("mensagem de teste")
        assert exc.message == "mensagem de teste"
        assert exc.detail == ""
        assert str(exc) == "mensagem de teste"

    def test_with_detail(self) -> None:
        exc = UploadError("mensagem", detail="detalhes técnicos")
        assert exc.message == "mensagem"
        assert exc.detail == "detalhes técnicos"

    def test_inherits_from_exception(self) -> None:
        exc = UploadError("teste")
        assert isinstance(exc, Exception)

    def test_can_be_raised_and_caught(self) -> None:
        with pytest.raises(UploadError) as exc_info:
            raise UploadError("erro de upload")
        assert exc_info.value.message == "erro de upload"


class TestUploadValidationError:
    """Testes para UploadValidationError."""

    def test_inherits_from_upload_error(self) -> None:
        exc = UploadValidationError("arquivo inválido")
        assert isinstance(exc, UploadError)

    def test_can_be_caught_as_base(self) -> None:
        with pytest.raises(UploadError):
            raise UploadValidationError("extensão inválida")


class TestUploadNetworkError:
    """Testes para UploadNetworkError."""

    def test_inherits_from_upload_error(self) -> None:
        exc = UploadNetworkError("falha de rede")
        assert isinstance(exc, UploadError)

    def test_with_detail(self) -> None:
        exc = UploadNetworkError("conexão falhou", detail="timeout after 30s")
        assert exc.detail == "timeout after 30s"


class TestUploadServerError:
    """Testes para UploadServerError."""

    def test_inherits_from_upload_error(self) -> None:
        exc = UploadServerError("erro do servidor")
        assert isinstance(exc, UploadError)

    def test_with_detail(self) -> None:
        exc = UploadServerError("erro 500", detail="HTTP 500: Internal Server Error")
        assert "500" in exc.detail


# ============================================================================
# Testes de factory functions
# ============================================================================


class TestMakeValidationError:
    """Testes para make_validation_error."""

    def test_extension_error(self) -> None:
        exc = make_validation_error("extension")
        assert isinstance(exc, UploadValidationError)
        assert "não permitido" in exc.message.lower() or "pdf" in exc.message.lower()
        assert exc.detail == "validation:extension"

    def test_size_error_with_formatting(self) -> None:
        exc = make_validation_error("size", max_mb=10)
        assert isinstance(exc, UploadValidationError)
        assert "10" in exc.message
        assert "MB" in exc.message

    def test_empty_file_error(self) -> None:
        exc = make_validation_error("empty")
        assert "vazio" in exc.message.lower() or "lido" in exc.message.lower()

    def test_not_found_error(self) -> None:
        exc = make_validation_error("not_found", path="/caminho/arquivo.pdf")
        assert "/caminho/arquivo.pdf" in exc.message

    def test_unknown_type_fallback(self) -> None:
        exc = make_validation_error("tipo_inexistente")
        assert exc.message == ERROR_MESSAGES["unknown"]


class TestMakeNetworkError:
    """Testes para make_network_error."""

    def test_network_error_default(self) -> None:
        exc = make_network_error()
        assert isinstance(exc, UploadNetworkError)
        assert "conexão" in exc.message.lower() or "internet" in exc.message.lower()

    def test_timeout_error(self) -> None:
        exc = make_network_error("timeout")
        assert "demorou" in exc.message.lower() or "instantes" in exc.message.lower()

    def test_with_original_exception(self) -> None:
        original = ConnectionError("Connection refused")
        exc = make_network_error("network", original=original)
        assert "ConnectionError" in exc.detail
        assert "Connection refused" in exc.detail


class TestMakeServerError:
    """Testes para make_server_error."""

    def test_server_error_default(self) -> None:
        exc = make_server_error()
        assert isinstance(exc, UploadServerError)
        assert "servidor" in exc.message.lower()

    def test_permission_error(self) -> None:
        exc = make_server_error("permission")
        assert "permissão" in exc.message.lower()

    def test_duplicate_error(self) -> None:
        exc = make_server_error("duplicate")
        assert "existe" in exc.message.lower()

    def test_with_status_code(self) -> None:
        exc = make_server_error("server", status_code=503)
        assert "HTTP 503" in exc.detail

    def test_with_original_and_status(self) -> None:
        original = RuntimeError("Service unavailable")
        exc = make_server_error("server", original=original, status_code=503)
        assert "503" in exc.detail
        assert "RuntimeError" in exc.detail


# ============================================================================
# Testes de ERROR_MESSAGES
# ============================================================================


class TestErrorMessages:
    """Testes para constantes de mensagens."""

    def test_all_keys_exist(self) -> None:
        required_keys = [
            "extension",
            "size",
            "empty",
            "not_found",
            "network",
            "timeout",
            "server",
            "permission",
            "duplicate",
            "unknown",
        ]
        for key in required_keys:
            assert key in ERROR_MESSAGES

    def test_messages_are_strings(self) -> None:
        for key, value in ERROR_MESSAGES.items():
            assert isinstance(value, str), f"ERROR_MESSAGES[{key!r}] não é string"

    def test_size_message_has_placeholder(self) -> None:
        assert "{max_mb}" in ERROR_MESSAGES["size"]

    def test_not_found_message_has_placeholder(self) -> None:
        assert "{path}" in ERROR_MESSAGES["not_found"]
