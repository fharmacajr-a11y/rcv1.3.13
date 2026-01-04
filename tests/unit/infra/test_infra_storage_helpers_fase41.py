# tests/test_infra_storage_helpers_fase41.py
"""
Testes para infra/supabase/storage_helpers.py (COV-INFRA-SUPABASE-HELPERS).
Foco: download_bytes cobrindo fluxos de validação, retorno None e conversão de dados.
"""

from __future__ import annotations

import importlib
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def storage_helpers_module(monkeypatch):
    """Isola o import com stub leve de infra.supabase_client."""
    stub_client_mod = ModuleType("src.infra.supabase_client")
    stub_client_mod.get_supabase = MagicMock()
    monkeypatch.setitem(sys.modules, "src.infra.supabase_client", stub_client_mod)
    sys.modules.pop("src.infra.supabase.storage_helpers", None)
    module = importlib.import_module("src.infra.supabase.storage_helpers")
    return module


class FakeStorage:
    def __init__(self, data):
        self._data = data
        self.last_key = None
        self.last_bucket = None

    def from_(self, bucket):
        self.last_bucket = bucket
        return self

    def download(self, key):
        self.last_key = key
        return self._data


def _build_client(data):
    fake_storage = FakeStorage(data)
    return SimpleNamespace(storage=fake_storage), fake_storage


def test_download_bytes_success(monkeypatch, storage_helpers_module):
    storage_helpers = storage_helpers_module
    client, fake_storage = _build_client(b"content")
    monkeypatch.setattr(storage_helpers, "get_supabase", lambda: client)

    result = storage_helpers.download_bytes(" my-bucket ", "/path/to/file.txt")

    assert result == b"content"
    assert fake_storage.last_bucket == "my-bucket"
    assert fake_storage.last_key == "path/to/file.txt"


def test_download_bytes_dict_wrapper(monkeypatch, storage_helpers_module):
    storage_helpers = storage_helpers_module
    client, fake_storage = _build_client({"data": bytearray(b"wrapped")})
    monkeypatch.setattr(storage_helpers, "get_supabase", lambda: client)

    result = storage_helpers.download_bytes("bucket", "folder/blob.bin")

    assert result == b"wrapped"
    assert fake_storage.last_bucket == "bucket"
    assert fake_storage.last_key == "folder/blob.bin"


def test_download_bytes_returns_none(monkeypatch, storage_helpers_module):
    storage_helpers = storage_helpers_module
    client, fake_storage = _build_client(None)
    monkeypatch.setattr(storage_helpers, "get_supabase", lambda: client)

    result = storage_helpers.download_bytes("bucket", "no/data")

    assert result is None
    assert fake_storage.last_key == "no/data"


def test_download_bytes_requires_bucket(storage_helpers_module):
    storage_helpers = storage_helpers_module
    with pytest.raises(ValueError) as exc:
        storage_helpers.download_bytes("", "path")

    assert "bucket" in str(exc.value)


def test_download_bytes_requires_path(storage_helpers_module):
    storage_helpers = storage_helpers_module
    with pytest.raises(ValueError) as exc:
        storage_helpers.download_bytes("bucket", "")

    assert "path" in str(exc.value)
