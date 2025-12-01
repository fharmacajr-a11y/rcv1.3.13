# -*- coding: utf-8 -*-
"""Testes adicionais para adapters/storage/supabase_storage.py - Coverage Pack 02.

Foco em branches não cobertas:
- Erros de upload/download/delete
- Normalização de keys com acentos
- Tratamento de buckets inválidos
- Exceções de cliente Supabase
- Edge cases em list_files
- Download de folders (zip)
- Content-type detection
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from adapters.storage import supabase_storage


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_supabase_client():
    """Mock do cliente Supabase."""
    client = MagicMock()
    return client


# ============================================================================
# TESTES - _normalize_bucket()
# ============================================================================


def test_normalize_bucket_uses_default_when_none():
    """Testa que _normalize_bucket usa bucket padrão quando None."""
    result = supabase_storage._normalize_bucket(None)

    assert result == "rc-docs"


def test_normalize_bucket_uses_default_when_empty():
    """Testa que _normalize_bucket usa bucket padrão quando string vazia."""
    result = supabase_storage._normalize_bucket("")

    assert result == "rc-docs"


def test_normalize_bucket_strips_whitespace():
    """Testa que _normalize_bucket remove espaços em branco."""
    result = supabase_storage._normalize_bucket("  my-bucket  ")

    assert result == "my-bucket"


def test_normalize_bucket_preserves_valid_name():
    """Testa que _normalize_bucket mantém nome válido."""
    result = supabase_storage._normalize_bucket("custom-bucket")

    assert result == "custom-bucket"


# ============================================================================
# TESTES - _strip_accents()
# ============================================================================


def test_strip_accents_removes_accents():
    """Testa remoção de acentos."""
    result = supabase_storage._strip_accents("Relatório")

    assert result == "Relatorio"


def test_strip_accents_handles_cedilla():
    """Testa remoção de cedilha."""
    result = supabase_storage._strip_accents("Configuração")

    assert result == "Configuracao"


def test_strip_accents_handles_multiple_accents():
    """Testa remoção de múltiplos acentos."""
    result = supabase_storage._strip_accents("Análise técnica")

    assert result == "Analise tecnica"


def test_strip_accents_preserves_plain_text():
    """Testa que texto sem acentos permanece inalterado."""
    result = supabase_storage._strip_accents("Simple text")

    assert result == "Simple text"


# ============================================================================
# TESTES - normalize_key_for_storage()
# ============================================================================


def test_normalize_key_removes_accents_from_filename():
    """Testa que normalização remove acentos apenas do filename."""
    result = supabase_storage.normalize_key_for_storage("docs/clientes/relatório.pdf")

    assert result == "docs/clientes/relatorio.pdf"


def test_normalize_key_strips_leading_slash():
    """Testa que normalização remove barra inicial."""
    result = supabase_storage.normalize_key_for_storage("/docs/file.pdf")

    assert result == "docs/file.pdf"


def test_normalize_key_strips_trailing_slash():
    """Testa que normalização remove barra final."""
    result = supabase_storage.normalize_key_for_storage("docs/folder/")

    assert result == "docs/folder"


def test_normalize_key_converts_backslashes():
    """Testa que normalização converte backslashes."""
    result = supabase_storage.normalize_key_for_storage("docs\\clientes\\file.pdf")

    assert result == "docs/clientes/file.pdf"


def test_normalize_key_handles_complex_path():
    """Testa normalização de path complexo com backslashes."""
    # A função substitui backslashes por forward slashes
    # Mas o comportamento de strip depende do input original
    result = supabase_storage.normalize_key_for_storage("docs\\análise\\relatório_técnico.pdf")

    # Deve converter backslashes e remover acentos do filename
    assert result == "docs/análise/relatorio_tecnico.pdf"


# ============================================================================
# TESTES - _guess_content_type()
# ============================================================================


def test_guess_content_type_returns_explicit():
    """Testa que content-type explícito é preservado."""
    result = supabase_storage._guess_content_type("file.pdf", "application/custom")

    assert result == "application/custom"


def test_guess_content_type_guesses_pdf():
    """Testa detecção de PDF."""
    result = supabase_storage._guess_content_type("document.pdf", None)

    assert result == "application/pdf"


def test_guess_content_type_guesses_docx():
    """Testa detecção de DOCX."""
    result = supabase_storage._guess_content_type("document.docx", None)

    assert "wordprocessingml" in result


def test_guess_content_type_defaults_to_octet_stream():
    """Testa que tipo desconhecido retorna octet-stream."""
    result = supabase_storage._guess_content_type("file.unknown", None)

    assert result == "application/octet-stream"


# ============================================================================
# TESTES - _read_data()
# ============================================================================


def test_read_data_from_bytes():
    """Testa leitura de bytes."""
    data = b"test content"

    result = supabase_storage._read_data(data)

    assert result == data
    assert isinstance(result, bytes)


def test_read_data_from_bytearray():
    """Testa leitura de bytearray."""
    data = bytearray(b"test content")

    result = supabase_storage._read_data(data)

    assert result == bytes(data)
    assert isinstance(result, bytes)


def test_read_data_from_file(tmp_path, monkeypatch):
    """Testa leitura de arquivo."""
    # Cria arquivo temporário
    test_file = tmp_path / "test.txt"
    test_file.write_bytes(b"file content")

    result = supabase_storage._read_data(str(test_file))

    assert result == b"file content"


# ============================================================================
# TESTES - _upload() com erros
# ============================================================================


def test_upload_normalizes_key(mock_supabase_client):
    """Testa que upload normaliza a key."""
    mock_storage = MagicMock()
    mock_storage.from_.return_value = mock_storage
    mock_storage.upload.return_value = {"data": {"path": "docs/relatorio.pdf"}}
    mock_supabase_client.storage = mock_storage

    supabase_storage._upload(
        mock_supabase_client,
        "test-bucket",
        b"content",
        "/docs/relatório.pdf/",
        None,
    )

    # Verifica chamada com key normalizada
    call_args = mock_storage.upload.call_args
    assert "relatorio.pdf" in call_args[0][0]


def test_upload_sets_upsert_flag(mock_supabase_client):
    """Testa que upload configura flag upsert corretamente."""
    mock_storage = MagicMock()
    mock_storage.from_.return_value = mock_storage
    mock_storage.upload.return_value = {"data": {"path": "file.pdf"}}
    mock_supabase_client.storage = mock_storage

    supabase_storage._upload(
        mock_supabase_client,
        "test-bucket",
        b"content",
        "file.pdf",
        None,
        upsert=False,
    )

    # Verifica que upsert foi configurado como string "false"
    call_args = mock_storage.upload.call_args
    file_options = call_args[1]["file_options"]
    assert file_options["upsert"] == "false"


def test_upload_returns_path_from_response(mock_supabase_client):
    """Testa que upload retorna path do response."""
    mock_storage = MagicMock()
    mock_storage.from_.return_value = mock_storage
    mock_storage.upload.return_value = {"data": {"path": "uploaded/file.pdf"}}
    mock_supabase_client.storage = mock_storage

    result = supabase_storage._upload(
        mock_supabase_client,
        "test-bucket",
        b"content",
        "file.pdf",
        None,
    )

    assert result == "uploaded/file.pdf"


def test_upload_returns_key_when_response_invalid(mock_supabase_client):
    """Testa que upload retorna key quando response é inválido."""
    mock_storage = MagicMock()
    mock_storage.from_.return_value = mock_storage
    mock_storage.upload.return_value = "invalid response"
    mock_supabase_client.storage = mock_storage

    result = supabase_storage._upload(
        mock_supabase_client,
        "test-bucket",
        b"content",
        "file.pdf",
        None,
    )

    assert result == "file.pdf"


# ============================================================================
# TESTES - _download() com erros
# ============================================================================


def test_download_normalizes_key(mock_supabase_client):
    """Testa que download normaliza a key."""
    mock_storage = MagicMock()
    mock_storage.from_.return_value = mock_storage
    mock_storage.download.return_value = b"content"
    mock_supabase_client.storage = mock_storage

    supabase_storage._download(mock_supabase_client, "test-bucket", "/docs/relatório.pdf/", None)

    # Verifica chamada com key normalizada
    call_args = mock_storage.download.call_args
    assert "relatorio.pdf" in call_args[0][0]


def test_download_returns_bytes_when_no_local_path(mock_supabase_client):
    """Testa que download retorna bytes quando local_path é None."""
    mock_storage = MagicMock()
    mock_storage.from_.return_value = mock_storage
    mock_storage.download.return_value = b"file content"
    mock_supabase_client.storage = mock_storage

    result = supabase_storage._download(mock_supabase_client, "test-bucket", "file.pdf", None)

    assert result == b"file content"
    assert isinstance(result, bytes)


def test_download_extracts_data_from_dict_response(mock_supabase_client):
    """Testa que download extrai data quando response é dict."""
    mock_storage = MagicMock()
    mock_storage.from_.return_value = mock_storage
    mock_storage.download.return_value = {"data": b"wrapped content"}
    mock_supabase_client.storage = mock_storage

    result = supabase_storage._download(mock_supabase_client, "test-bucket", "file.pdf", None)

    assert result == b"wrapped content"


def test_download_saves_to_file(mock_supabase_client, tmp_path, monkeypatch):
    """Testa que download salva em arquivo."""
    mock_storage = MagicMock()
    mock_storage.from_.return_value = mock_storage
    mock_storage.download.return_value = b"file content"
    mock_supabase_client.storage = mock_storage

    # Mock CLOUD_ONLY
    monkeypatch.setattr(supabase_storage, "CLOUD_ONLY", False)

    local_path = tmp_path / "downloaded.pdf"
    result = supabase_storage._download(
        mock_supabase_client,
        "test-bucket",
        "file.pdf",
        str(local_path),
    )

    assert result == str(local_path)
    assert local_path.read_bytes() == b"file content"


# ============================================================================
# TESTES - _delete() com erros
# ============================================================================


def test_delete_normalizes_key(mock_supabase_client):
    """Testa que delete normaliza a key."""
    mock_storage = MagicMock()
    mock_storage.from_.return_value = mock_storage
    mock_storage.remove.return_value = {}
    mock_supabase_client.storage = mock_storage

    supabase_storage._delete(mock_supabase_client, "test-bucket", "/docs/relatório.pdf/")

    # Verifica chamada com key normalizada
    call_args = mock_storage.remove.call_args
    assert "relatorio.pdf" in call_args[0][0][0]


def test_delete_returns_true_on_success(mock_supabase_client):
    """Testa que delete retorna True quando bem-sucedido."""
    mock_storage = MagicMock()
    mock_storage.from_.return_value = mock_storage
    mock_storage.remove.return_value = {}
    mock_supabase_client.storage = mock_storage

    result = supabase_storage._delete(mock_supabase_client, "test-bucket", "file.pdf")

    assert result is True


def test_delete_returns_false_on_error(mock_supabase_client):
    """Testa que delete retorna False quando há erro."""
    mock_storage = MagicMock()
    mock_storage.from_.return_value = mock_storage
    mock_storage.remove.return_value = {"error": "File not found"}
    mock_supabase_client.storage = mock_storage

    result = supabase_storage._delete(mock_supabase_client, "test-bucket", "file.pdf")

    assert result is False


def test_delete_returns_true_for_non_dict_response(mock_supabase_client):
    """Testa que delete retorna True para response não-dict."""
    mock_storage = MagicMock()
    mock_storage.from_.return_value = mock_storage
    mock_storage.remove.return_value = "success"
    mock_supabase_client.storage = mock_storage

    result = supabase_storage._delete(mock_supabase_client, "test-bucket", "file.pdf")

    assert result is True


# ============================================================================
# TESTES - _list() com edge cases
# ============================================================================


def test_list_with_empty_prefix(mock_supabase_client):
    """Testa listagem com prefix vazio."""
    mock_storage = MagicMock()
    mock_storage.from_.return_value = mock_storage
    mock_storage.list.return_value = [{"name": "file1.pdf"}, {"name": "file2.pdf"}]
    mock_supabase_client.storage = mock_storage

    result = supabase_storage._list(mock_supabase_client, "test-bucket", "")

    assert len(result) == 2
    # Verifica que chamou com path vazio
    call_args = mock_storage.list.call_args
    assert call_args[1]["path"] == ""


def test_list_with_prefix(mock_supabase_client):
    """Testa listagem com prefix."""
    mock_storage = MagicMock()
    mock_storage.from_.return_value = mock_storage
    mock_storage.list.return_value = [{"name": "doc1.pdf"}]
    mock_supabase_client.storage = mock_storage

    result = supabase_storage._list(mock_supabase_client, "test-bucket", "docs/clientes")

    assert len(result) == 1
    # Verifica que adicionou full_path
    assert result[0]["full_path"] == "docs/clientes/doc1.pdf"


def test_list_strips_slashes_from_prefix(mock_supabase_client):
    """Testa que list remove barras do prefix."""
    mock_storage = MagicMock()
    mock_storage.from_.return_value = mock_storage
    mock_storage.list.return_value = []
    mock_supabase_client.storage = mock_storage

    supabase_storage._list(mock_supabase_client, "test-bucket", "/docs/")

    # Verifica que chamou com path limpo
    call_args = mock_storage.list.call_args
    assert call_args[1]["path"] == "docs/"


def test_list_handles_non_dict_items(mock_supabase_client):
    """Testa que list ignora items não-dict."""
    mock_storage = MagicMock()
    mock_storage.from_.return_value = mock_storage
    mock_storage.list.return_value = [
        {"name": "file1.pdf"},
        "invalid",  # Não é dict
        {"name": "file2.pdf"},
    ]
    mock_supabase_client.storage = mock_storage

    result = supabase_storage._list(mock_supabase_client, "test-bucket", "")

    # Deve ignorar item inválido
    assert len(result) == 2


def test_list_handles_none_response(mock_supabase_client):
    """Testa que list trata response None."""
    mock_storage = MagicMock()
    mock_storage.from_.return_value = mock_storage
    mock_storage.list.return_value = None
    mock_supabase_client.storage = mock_storage

    result = supabase_storage._list(mock_supabase_client, "test-bucket", "")

    assert result == []


# ============================================================================
# TESTES - SupabaseStorageAdapter
# ============================================================================


def test_adapter_init_with_custom_bucket():
    """Testa inicialização do adapter com bucket customizado."""
    adapter = supabase_storage.SupabaseStorageAdapter(bucket="custom-bucket")

    assert adapter._bucket == "custom-bucket"


def test_adapter_init_with_custom_client():
    """Testa inicialização do adapter com cliente customizado."""
    mock_client = MagicMock()
    adapter = supabase_storage.SupabaseStorageAdapter(client=mock_client)

    assert adapter._client is mock_client


def test_adapter_init_with_overwrite_false():
    """Testa inicialização do adapter com overwrite=False."""
    adapter = supabase_storage.SupabaseStorageAdapter(overwrite=False)

    assert adapter._overwrite is False


def test_adapter_upload_file_delegates_to_upload(monkeypatch):
    """Testa que upload_file delega para _upload."""
    mock_upload = MagicMock(return_value="uploaded/path")
    monkeypatch.setattr(supabase_storage, "_upload", mock_upload)

    adapter = supabase_storage.SupabaseStorageAdapter(bucket="test")
    result = adapter.upload_file("local.pdf", "remote.pdf", "application/pdf")

    assert result == "uploaded/path"
    assert mock_upload.called


def test_adapter_download_file_delegates_to_download(monkeypatch):
    """Testa que download_file delega para _download."""
    mock_download = MagicMock(return_value=b"content")
    monkeypatch.setattr(supabase_storage, "_download", mock_download)

    adapter = supabase_storage.SupabaseStorageAdapter(bucket="test")
    result = adapter.download_file("remote.pdf")

    assert result == b"content"
    assert mock_download.called


def test_adapter_delete_file_delegates_to_delete(monkeypatch):
    """Testa que delete_file delega para _delete."""
    mock_delete = MagicMock(return_value=True)
    monkeypatch.setattr(supabase_storage, "_delete", mock_delete)

    adapter = supabase_storage.SupabaseStorageAdapter(bucket="test")
    result = adapter.delete_file("remote.pdf")

    assert result is True
    assert mock_delete.called


def test_adapter_list_files_delegates_to_list(monkeypatch):
    """Testa que list_files delega para _list."""
    mock_list = MagicMock(return_value=[{"name": "file.pdf"}])
    monkeypatch.setattr(supabase_storage, "_list", mock_list)

    adapter = supabase_storage.SupabaseStorageAdapter(bucket="test")
    result = adapter.list_files("docs")

    assert len(result) == 1
    assert mock_list.called


def test_adapter_download_folder_zip_calls_baixar_pasta_zip(monkeypatch):
    """Testa que download_folder_zip chama baixar_pasta_zip."""
    mock_baixar = MagicMock(return_value="path/to/zip")
    monkeypatch.setattr(supabase_storage, "baixar_pasta_zip", mock_baixar)

    adapter = supabase_storage.SupabaseStorageAdapter(bucket="test")
    result = adapter.download_folder_zip("docs/clientes", zip_name="backup.zip")

    assert result == "path/to/zip"
    assert mock_baixar.called


# ============================================================================
# TESTES - Funções de conveniência
# ============================================================================


def test_upload_file_uses_default_adapter(monkeypatch):
    """Testa que upload_file usa adapter padrão."""
    mock_adapter = MagicMock()
    mock_adapter.upload_file.return_value = "path"
    monkeypatch.setattr(supabase_storage, "_default_adapter", mock_adapter)

    result = supabase_storage.upload_file("local.pdf", "remote.pdf")

    assert result == "path"
    assert mock_adapter.upload_file.called


def test_download_file_uses_default_adapter(monkeypatch):
    """Testa que download_file usa adapter padrão."""
    mock_adapter = MagicMock()
    mock_adapter.download_file.return_value = b"content"
    monkeypatch.setattr(supabase_storage, "_default_adapter", mock_adapter)

    result = supabase_storage.download_file("remote.pdf")

    assert result == b"content"
    assert mock_adapter.download_file.called


def test_delete_file_uses_default_adapter(monkeypatch):
    """Testa que delete_file usa adapter padrão."""
    mock_adapter = MagicMock()
    mock_adapter.delete_file.return_value = True
    monkeypatch.setattr(supabase_storage, "_default_adapter", mock_adapter)

    result = supabase_storage.delete_file("remote.pdf")

    assert result is True
    assert mock_adapter.delete_file.called


def test_list_files_uses_default_adapter(monkeypatch):
    """Testa que list_files usa adapter padrão."""
    mock_adapter = MagicMock()
    mock_adapter.list_files.return_value = [{"name": "file.pdf"}]
    monkeypatch.setattr(supabase_storage, "_default_adapter", mock_adapter)

    result = list(supabase_storage.list_files("docs"))

    assert len(result) == 1
    assert mock_adapter.list_files.called


def test_download_folder_zip_creates_adapter_for_custom_bucket(monkeypatch):
    """Testa que download_folder_zip cria adapter para bucket customizado."""
    mock_baixar = MagicMock(return_value="zip_path")
    monkeypatch.setattr(supabase_storage, "baixar_pasta_zip", mock_baixar)

    # Mock do construtor do adapter
    original_adapter_class = supabase_storage.SupabaseStorageAdapter
    created_adapters = []

    class MockAdapter(original_adapter_class):
        def __init__(self, *args, **kwargs):
            created_adapters.append((args, kwargs))
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(supabase_storage, "SupabaseStorageAdapter", MockAdapter)

    supabase_storage.download_folder_zip("docs", bucket="custom-bucket")

    # Verifica que criou novo adapter com bucket customizado
    assert len(created_adapters) > 0


def test_get_default_adapter_returns_singleton():
    """Testa que get_default_adapter retorna sempre a mesma instância."""
    adapter1 = supabase_storage.get_default_adapter()
    adapter2 = supabase_storage.get_default_adapter()

    assert adapter1 is adapter2
