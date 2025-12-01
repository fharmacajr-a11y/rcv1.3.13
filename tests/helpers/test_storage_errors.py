from __future__ import annotations

import pytest

from src.helpers.storage_errors import StorageErrorKind, classify_storage_error


class DummyError(Exception):
    """Erro fake para testar classificação."""


@pytest.mark.parametrize(
    "message,expected",
    [
        ("InvalidKey supplied", "invalid_key"),
        ("invalid key format", "invalid_key"),
        ("Row-Level Security violation", "rls"),
        ("permission denied (rls)", "rls"),
        ("error 42501", "rls"),
        ("403 Forbidden", "rls"),
        ("Object already exists", "exists"),
        ("keyAlreadyExists in storage", "exists"),
        ("status 409 conflict", "exists"),
        ("algum erro qualquer", "other"),
        ("", "other"),
    ],
)
def test_classify_storage_error(message: str, expected: StorageErrorKind):
    exc = DummyError(message)

    result = classify_storage_error(exc)

    assert result == expected
