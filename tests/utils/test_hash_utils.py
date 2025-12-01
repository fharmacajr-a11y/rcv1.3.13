from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from src.utils import hash_utils


def test_sha256_file_returns_expected_digest_for_small_file(tmp_path: Path) -> None:
    target = tmp_path / "small.txt"
    data = b"abc123"
    target.write_bytes(data)

    expected = hashlib.sha256(data).hexdigest()
    result = hash_utils.sha256_file(target)

    assert result == expected


def test_sha256_file_handles_large_file_in_chunks(tmp_path: Path) -> None:
    target = tmp_path / "large.bin"
    block = b"0123456789abcdef" * 1024  # ~16 KB
    target.write_bytes(block * 10)  # ~160 KB to ensure multiple chunks

    expected = hashlib.sha256(target.read_bytes()).hexdigest()
    result = hash_utils.sha256_file(target)

    assert result == expected


def test_sha256_file_accepts_string_path(tmp_path: Path) -> None:
    target = tmp_path / "string_path.txt"
    data = b"path-string"
    target.write_bytes(data)

    expected = hashlib.sha256(data).hexdigest()
    result = hash_utils.sha256_file(str(target))

    assert result == expected


def test_sha256_file_raises_for_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing.txt"

    with pytest.raises(FileNotFoundError):
        hash_utils.sha256_file(missing)
