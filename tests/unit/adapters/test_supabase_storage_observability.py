# -*- coding: utf-8 -*-
"""Testes de observabilidade para adapters/storage/supabase_storage.py.

FASE INFRA-OBSERVABILIDADE-STORAGE-01

Valida que as operações de storage geram logs estruturados com:
- storage.op.start: operação iniciada
- storage.op.success: operação concluída com sucesso (+ duração)
- storage.op.error: operação falhou (+ duração + tipo de erro)
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.adapters.storage import supabase_storage


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_client():
    """Mock do cliente Supabase."""
    client = MagicMock()
    return client


@pytest.fixture
def temp_file(tmp_path):
    """Cria um arquivo temporário para testes."""
    file_path = tmp_path / "test.pdf"
    file_path.write_bytes(b"test content")
    return file_path


# ============================================================================
# TESTES - _upload() logging
# ============================================================================


def test_upload_logs_start_and_success(mock_client, temp_file, caplog):
    """Testa que _upload loga início e sucesso da operação."""
    # Arrange
    mock_client.storage.from_().upload.return_value = {"data": {"path": "docs/test.pdf"}}

    # Act
    with caplog.at_level("INFO", logger="src.infra.supabase.storage"):
        result = supabase_storage._upload(
            mock_client,
            "rc-docs",
            temp_file,
            "docs/test.pdf",
            None,
        )

    # Assert
    assert result == "docs/test.pdf"

    # Verifica logs
    log_messages = [rec.message for rec in caplog.records]

    # Log de início
    assert any("storage.op.start: op=upload" in msg for msg in log_messages)
    assert any("bucket=rc-docs" in msg for msg in log_messages)
    assert any("key=docs/test.pdf" in msg for msg in log_messages)

    # Log de sucesso
    assert any("storage.op.success: op=upload" in msg for msg in log_messages)
    assert any("duration_ms=" in msg for msg in log_messages)


def test_upload_logs_error_on_exception(mock_client, temp_file, caplog):
    """Testa que _upload loga erro quando exceção ocorre."""
    # Arrange
    mock_client.storage.from_().upload.side_effect = Exception("Network error")

    # Act & Assert
    with caplog.at_level("ERROR", logger="src.infra.supabase.storage"):
        with pytest.raises(Exception, match="Network error"):
            supabase_storage._upload(
                mock_client,
                "rc-docs",
                temp_file,
                "docs/test.pdf",
                None,
            )

    # Verifica logs de erro
    log_messages = [rec.message for rec in caplog.records]

    assert any("storage.op.error: op=upload" in msg for msg in log_messages)
    assert any("error=Exception" in msg for msg in log_messages)
    assert any("duration_ms=" in msg for msg in log_messages)


# ============================================================================
# TESTES - _download() logging
# ============================================================================


def test_download_logs_start_and_success_bytes(mock_client, caplog):
    """Testa que _download loga início e sucesso (modo bytes)."""
    # Arrange
    mock_client.storage.from_().download.return_value = b"file content"

    # Act
    with caplog.at_level("INFO", logger="src.infra.supabase.storage"):
        result = supabase_storage._download(
            mock_client,
            "rc-docs",
            "docs/test.pdf",
            None,  # sem local_path = retorna bytes
        )

    # Assert
    assert result == b"file content"

    # Verifica logs
    log_messages = [rec.message for rec in caplog.records]

    assert any("storage.op.start: op=download" in msg for msg in log_messages)
    assert any("bucket=rc-docs" in msg for msg in log_messages)

    assert any("storage.op.success: op=download" in msg for msg in log_messages)
    assert any("size=12" in msg for msg in log_messages)  # "file content" tem 12 bytes
    assert any("duration_ms=" in msg for msg in log_messages)


def test_download_logs_success_with_local_path(mock_client, tmp_path, caplog):
    """Testa que _download loga sucesso com path local."""
    # Arrange
    mock_client.storage.from_().download.return_value = b"file content"
    local_path = str(tmp_path / "downloaded.pdf")

    # Act
    with caplog.at_level("INFO", logger="src.infra.supabase.storage"):
        result = supabase_storage._download(
            mock_client,
            "rc-docs",
            "docs/test.pdf",
            local_path,
        )

    # Assert
    assert result == local_path

    # Verifica logs
    log_messages = [rec.message for rec in caplog.records]

    assert any("storage.op.success: op=download" in msg for msg in log_messages)
    assert any("local_path=" in msg for msg in log_messages)
    assert any("duration_ms=" in msg for msg in log_messages)


def test_download_logs_error_on_exception(mock_client, caplog):
    """Testa que _download loga erro quando exceção ocorre."""
    # Arrange
    mock_client.storage.from_().download.side_effect = Exception("File not found")

    # Act & Assert
    with caplog.at_level("ERROR", logger="src.infra.supabase.storage"):
        with pytest.raises(Exception, match="File not found"):
            supabase_storage._download(
                mock_client,
                "rc-docs",
                "docs/missing.pdf",
                None,
            )

    # Verifica logs de erro
    log_messages = [rec.message for rec in caplog.records]

    assert any("storage.op.error: op=download" in msg for msg in log_messages)
    assert any("error=Exception" in msg for msg in log_messages)
    assert any("duration_ms=" in msg for msg in log_messages)


# ============================================================================
# TESTES - _delete() logging
# ============================================================================


def test_delete_logs_start_and_success(mock_client, caplog):
    """Testa que _delete loga início e sucesso da operação."""
    # Arrange
    mock_client.storage.from_().remove.return_value = {"data": []}  # sucesso

    # Act
    with caplog.at_level("INFO", logger="src.infra.supabase.storage"):
        result = supabase_storage._delete(
            mock_client,
            "rc-docs",
            "docs/test.pdf",
        )

    # Assert
    assert result is True

    # Verifica logs
    log_messages = [rec.message for rec in caplog.records]

    assert any("storage.op.start: op=delete" in msg for msg in log_messages)
    assert any("bucket=rc-docs" in msg for msg in log_messages)
    assert any("key=docs/test.pdf" in msg for msg in log_messages)

    assert any("storage.op.success: op=delete" in msg for msg in log_messages)
    assert any("duration_ms=" in msg for msg in log_messages)


def test_delete_logs_warning_on_api_error(mock_client, caplog):
    """Testa que _delete loga warning quando API retorna erro."""
    # Arrange
    mock_client.storage.from_().remove.return_value = {"error": {"message": "Permission denied"}}

    # Act
    with caplog.at_level("WARNING", logger="src.infra.supabase.storage"):
        result = supabase_storage._delete(
            mock_client,
            "rc-docs",
            "docs/test.pdf",
        )

    # Assert
    assert result is False

    # Verifica logs
    log_messages = [rec.message for rec in caplog.records]

    assert any("storage.op.error: op=delete" in msg for msg in log_messages)
    assert any("error=RemoveFailed" in msg for msg in log_messages)


def test_delete_logs_error_on_exception(mock_client, caplog):
    """Testa que _delete loga erro quando exceção ocorre."""
    # Arrange
    mock_client.storage.from_().remove.side_effect = Exception("Network error")

    # Act & Assert
    with caplog.at_level("ERROR", logger="src.infra.supabase.storage"):
        with pytest.raises(Exception, match="Network error"):
            supabase_storage._delete(
                mock_client,
                "rc-docs",
                "docs/test.pdf",
            )

    # Verifica logs de erro
    log_messages = [rec.message for rec in caplog.records]

    assert any("storage.op.error: op=delete" in msg for msg in log_messages)
    assert any("error=Exception" in msg for msg in log_messages)


# ============================================================================
# TESTES - _list() logging
# ============================================================================


def test_list_logs_start_and_success(mock_client, caplog):
    """Testa que _list loga início e sucesso da operação."""
    # Arrange
    mock_client.storage.from_().list.return_value = [
        {"name": "file1.pdf"},
        {"name": "file2.pdf"},
    ]

    # Act
    with caplog.at_level("INFO", logger="src.infra.supabase.storage"):
        result = supabase_storage._list(
            mock_client,
            "rc-docs",
            "docs/clientes",
        )

    # Assert
    assert len(result) == 2

    # Verifica logs
    log_messages = [rec.message for rec in caplog.records]

    assert any("storage.op.start: op=list" in msg for msg in log_messages)
    assert any("bucket=rc-docs" in msg for msg in log_messages)
    assert any("prefix=docs/clientes" in msg for msg in log_messages)

    assert any("storage.op.success: op=list" in msg for msg in log_messages)
    assert any("count=2" in msg for msg in log_messages)
    assert any("duration_ms=" in msg for msg in log_messages)


def test_list_logs_error_on_exception(mock_client, caplog):
    """Testa que _list loga erro quando exceção ocorre."""
    # Arrange
    mock_client.storage.from_().list.side_effect = Exception("Bucket not found")

    # Act & Assert
    with caplog.at_level("ERROR", logger="src.infra.supabase.storage"):
        with pytest.raises(Exception, match="Bucket not found"):
            supabase_storage._list(
                mock_client,
                "rc-docs",
                "docs",
            )

    # Verifica logs de erro
    log_messages = [rec.message for rec in caplog.records]

    assert any("storage.op.error: op=list" in msg for msg in log_messages)
    assert any("error=Exception" in msg for msg in log_messages)
    assert any("duration_ms=" in msg for msg in log_messages)


# ============================================================================
# TESTES - Verificação de duration_ms
# ============================================================================


def test_upload_includes_duration_in_logs(mock_client, temp_file, caplog):
    """Testa que duration_ms está presente nos logs de upload."""
    # Arrange
    mock_client.storage.from_().upload.return_value = {"data": {"path": "test.pdf"}}

    # Act
    with caplog.at_level("INFO", logger="src.infra.supabase.storage"):
        supabase_storage._upload(mock_client, "rc-docs", temp_file, "test.pdf", None)

    # Assert
    success_logs = [rec for rec in caplog.records if "storage.op.success" in rec.message]
    assert len(success_logs) > 0

    # Verifica que duration_ms é um número
    for log in success_logs:
        if "op=upload" in log.message:
            assert "duration_ms=" in log.message
            # Extrai o valor de duration_ms
            import re

            match = re.search(r"duration_ms=([\d.]+)", log.message)
            assert match is not None
            duration = float(match.group(1))
            assert duration >= 0


def test_download_includes_size_in_logs(mock_client, caplog):
    """Testa que size está presente nos logs de download."""
    # Arrange
    test_data = b"x" * 1024  # 1KB
    mock_client.storage.from_().download.return_value = test_data

    # Act
    with caplog.at_level("INFO", logger="src.infra.supabase.storage"):
        supabase_storage._download(mock_client, "rc-docs", "test.pdf", None)

    # Assert
    success_logs = [rec for rec in caplog.records if "storage.op.success" in rec.message]
    assert len(success_logs) > 0

    # Verifica que size=1024 está nos logs
    for log in success_logs:
        if "op=download" in log.message:
            assert "size=1024" in log.message
