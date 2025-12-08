"""Testes específicos de SEC-001 para upload_retry."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.modules.uploads.upload_retry import upload_with_retry


def test_upload_with_retry_raises_runtime_when_no_attempts() -> None:
    mock_fn = MagicMock()

    with pytest.raises(RuntimeError) as exc_info:
        upload_with_retry(mock_fn, max_retries=-1)

    mock_fn.assert_not_called()
    assert "sem exceção registrada" in str(exc_info.value).lower()
