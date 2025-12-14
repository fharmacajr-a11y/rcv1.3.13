"""Testes unitários para retry de uploads.

FASE 7 - Cobertura de:
- upload_with_retry com diferentes tipos de erro
- Classificação de exceções (classify_upload_exception)
- Backoff exponencial
- Callback de retry
"""

from __future__ import annotations

import logging
import socket
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.modules.uploads.upload_retry import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_BACKOFF_BASE,
    upload_with_retry,
    classify_upload_exception,
)
from src.modules.uploads.exceptions import (
    UploadError,
    UploadNetworkError,
    UploadServerError,
)


# ============================================================================
# Testes de upload_with_retry
# ============================================================================


class TestUploadWithRetry:
    """Testes para upload_with_retry."""

    def test_success_on_first_try(self) -> None:
        mock_fn = MagicMock(return_value="success")

        result = upload_with_retry(mock_fn, "arg1", kwarg1="value1")

        assert result == "success"
        mock_fn.assert_called_once_with("arg1", kwarg1="value1")

    def test_retry_on_network_error(self) -> None:
        call_count = 0

        def failing_then_success(*args: Any, **kwargs: Any) -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Connection refused")
            return "success"

        result = upload_with_retry(
            failing_then_success,
            max_retries=3,
            backoff_base=0.01,  # Rápido para teste
        )

        assert result == "success"
        assert call_count == 3

    def test_retry_on_server_error_5xx(self) -> None:
        call_count = 0

        def failing_then_success(*args: Any, **kwargs: Any) -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RuntimeError("HTTP 503 Service Unavailable")
            return "success"

        result = upload_with_retry(
            failing_then_success,
            max_retries=3,
            backoff_base=0.01,
        )

        assert result == "success"
        assert call_count == 2

    def test_no_retry_on_client_error_4xx(self) -> None:
        def raise_client_error(*args: Any, **kwargs: Any) -> str:
            raise RuntimeError("HTTP 400 Bad Request")

        with pytest.raises(UploadError) as exc_info:
            upload_with_retry(
                raise_client_error,
                max_retries=3,
                backoff_base=0.01,
            )

        # Deve falhar imediatamente sem retry
        assert "400" in str(exc_info.value) or "código" in exc_info.value.message

    def test_exhaust_retries_raises_network_error(self) -> None:
        def always_fails(*args: Any, **kwargs: Any) -> str:
            raise ConnectionError("Network unreachable")

        with pytest.raises(UploadNetworkError):
            upload_with_retry(
                always_fails,
                max_retries=2,
                backoff_base=0.01,
            )

    def test_exhaust_retries_raises_server_error(self) -> None:
        def always_fails(*args: Any, **kwargs: Any) -> str:
            raise RuntimeError("HTTP 500 Internal Server Error")

        with pytest.raises(UploadServerError):
            upload_with_retry(
                always_fails,
                max_retries=2,
                backoff_base=0.01,
            )

    def test_callback_called_on_retry(self) -> None:
        call_count = 0
        retry_callback = MagicMock()

        def failing_then_success(*args: Any, **kwargs: Any) -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("timeout")
            return "success"

        upload_with_retry(
            failing_then_success,
            max_retries=3,
            backoff_base=0.01,
            on_retry=retry_callback,
        )

        # Callback deve ser chamado 2 vezes (antes de cada retry)
        assert retry_callback.call_count == 2

    def test_callback_receives_correct_args(self) -> None:
        retry_info: list[tuple[int, Exception, float]] = []

        def capture_retry(attempt: int, exc: Exception, delay: float) -> None:
            retry_info.append((attempt, exc, delay))

        def failing_then_success(*args: Any, **kwargs: Any) -> str:
            if len(retry_info) < 1:
                raise ConnectionError("test error")
            return "success"

        upload_with_retry(
            failing_then_success,
            max_retries=2,
            backoff_base=0.01,
            on_retry=capture_retry,
        )

        assert len(retry_info) == 1
        attempt, exc, delay = retry_info[0]
        assert attempt == 1
        assert isinstance(exc, ConnectionError)
        assert delay > 0

    def test_backoff_increases_with_attempts(self, monkeypatch: pytest.MonkeyPatch) -> None:
        delays: list[float] = []
        sleep_calls: list[float] = []

        def capture_delay(attempt: int, exc: Exception, delay: float) -> None:
            delays.append(delay)

        def always_fails(*args: Any, **kwargs: Any) -> str:
            raise ConnectionError("fail")

        # Patch time.sleep para não esperar de verdade (PERF-001)
        def fake_sleep(seconds: float) -> None:
            sleep_calls.append(seconds)

        monkeypatch.setattr("src.modules.uploads.upload_retry.time.sleep", fake_sleep)

        with pytest.raises(UploadNetworkError):
            upload_with_retry(
                always_fails,
                max_retries=3,
                backoff_base=0.1,
                jitter=0,  # Sem jitter para teste previsível
                on_retry=capture_delay,
            )

        # Delays devem aumentar (exponencial)
        assert len(delays) == 3
        assert delays[1] > delays[0]
        assert delays[2] > delays[1]
        # Verificar que sleep foi chamado com os delays corretos
        assert len(sleep_calls) == 3
        assert sleep_calls == delays

    def test_permission_error_no_retry(self) -> None:
        def raise_permission_error(*args: Any, **kwargs: Any) -> str:
            raise RuntimeError("HTTP 403 Forbidden - Permission denied")

        with pytest.raises(UploadServerError) as exc_info:
            upload_with_retry(
                raise_permission_error,
                max_retries=3,
                backoff_base=0.01,
            )

        assert "permissão" in exc_info.value.message.lower()

    def test_duplicate_error_no_retry(self) -> None:
        def raise_duplicate_error(*args: Any, **kwargs: Any) -> str:
            raise RuntimeError("409 Conflict - Duplicate file")

        with pytest.raises(UploadServerError) as exc_info:
            upload_with_retry(
                raise_duplicate_error,
                max_retries=3,
                backoff_base=0.01,
            )

        assert "existe" in exc_info.value.message.lower()

    def test_logging_records_success_details(self, caplog: pytest.LogCaptureFixture) -> None:
        mock_fn = MagicMock(return_value="ok")
        caplog.set_level(logging.INFO, logger="src.modules.uploads.upload_retry")

        upload_with_retry(mock_fn, "local.pdf", "remote/key.pdf")

        info_records = [
            record
            for record in caplog.records
            if record.levelname == "INFO"
            and getattr(record, "remote_key", None) == "remote/key.pdf"
            and getattr(record, "local_path", None) == "local.pdf"
        ]
        assert any(getattr(record, "max_retries", None) is None for record in info_records)

    def test_logging_records_retry_warning(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        mock_fn = MagicMock(side_effect=[ConnectionError("fail"), "ok"])
        caplog.set_level(logging.DEBUG, logger="src.modules.uploads.upload_retry")

        upload_with_retry(
            mock_fn,
            "local.pdf",
            "remote/key.pdf",
            max_retries=2,
            backoff_base=0,
        )

        warning_records = [
            record for record in caplog.records if record.levelname == "WARNING" and getattr(record, "error_type", None)
        ]
        assert any(
            getattr(record, "attempt", None) == 1 and record.error_type == "ConnectionError"
            for record in warning_records
        )
        assert any(
            record.levelname == "INFO"
            and getattr(record, "remote_key", None) == "remote/key.pdf"
            and getattr(record, "local_path", None) == "local.pdf"
            for record in caplog.records
        )


# ============================================================================
# Testes de classify_upload_exception
# ============================================================================


class TestClassifyUploadException:
    """Testes para classify_upload_exception."""

    def test_already_upload_error_returned_as_is(self) -> None:
        original = UploadNetworkError("já é upload error")
        result = classify_upload_exception(original)

        assert result is original

    def test_connection_error_becomes_network_error(self) -> None:
        exc = ConnectionError("Connection refused")
        result = classify_upload_exception(exc)

        assert isinstance(result, UploadNetworkError)

    def test_socket_error_becomes_network_error(self) -> None:
        exc = socket.error("Socket error")
        result = classify_upload_exception(exc)

        assert isinstance(result, UploadNetworkError)

    def test_timeout_becomes_network_error(self) -> None:
        exc = TimeoutError("Request timed out")
        result = classify_upload_exception(exc)

        assert isinstance(result, UploadNetworkError)

    def test_500_error_becomes_server_error(self) -> None:
        exc = RuntimeError("HTTP 500 Internal Server Error")
        result = classify_upload_exception(exc)

        assert isinstance(result, UploadServerError)

    def test_503_error_becomes_server_error(self) -> None:
        exc = RuntimeError("503 Service Unavailable")
        result = classify_upload_exception(exc)

        assert isinstance(result, UploadServerError)

    def test_403_error_becomes_permission_error(self) -> None:
        exc = RuntimeError("403 Forbidden")
        result = classify_upload_exception(exc)

        assert isinstance(result, UploadServerError)
        assert "permissão" in result.message.lower()

    def test_duplicate_becomes_server_error(self) -> None:
        exc = RuntimeError("Duplicate entry detected")
        result = classify_upload_exception(exc)

        assert isinstance(result, UploadServerError)
        assert "existe" in result.message.lower()

    def test_unknown_error_becomes_upload_error(self) -> None:
        exc = ValueError("Something weird")
        result = classify_upload_exception(exc)

        assert isinstance(result, UploadError)
        assert "inesperado" in result.message.lower()


# ============================================================================
# Testes de configuração padrão
# ============================================================================


class TestDefaults:
    """Testes para valores padrão."""

    def test_default_max_retries(self) -> None:
        assert DEFAULT_MAX_RETRIES == 3

    def test_default_backoff_base(self) -> None:
        assert DEFAULT_BACKOFF_BASE == 0.5
