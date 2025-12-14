"""
Testes para src/modules/auditoria/storage.py (Microfase 8).

Foco: Aumentar cobertura de ~39.1% para ≥95%

Cenários testados:
- Construção de prefixos e contextos de storage
- Criação de pastas de auditoria (.keep file)
- Listagem de arquivos existentes (com paginação)
- Upload de bytes para storage
- Remoção de objetos do storage
- Tratamento de erros (falhas de conexão, objetos não encontrados)
- Edge cases (listas vazias, prefixos inválidos, respostas vazias)
"""

from __future__ import annotations

from unittest.mock import MagicMock, Mock

import pytest

from src.modules.auditoria.storage import (
    CLIENTS_BUCKET,
    AuditoriaStorageContext,
    AuditoriaUploadContext,
    build_auditoria_prefix,
    build_client_prefix,
    ensure_auditoria_folder,
    get_clients_bucket,
    list_existing_file_names,
    make_storage_context,
    remove_storage_objects,
    upload_storage_bytes,
)


# --- Testes de get_clients_bucket ---


def test_get_clients_bucket_returns_default():
    """Testa que get_clients_bucket retorna bucket padrão."""
    result = get_clients_bucket()
    assert result == CLIENTS_BUCKET
    assert isinstance(result, str)
    assert len(result) > 0


# --- Testes de build_client_prefix ---


def test_build_client_prefix_with_valid_data():
    """Testa construção de prefixo com org_id e client_id válidos."""
    # Esta função delega para _build_client_prefix_shared
    # Vamos testar que ela chama corretamente
    result = build_client_prefix(client_id=123, org_id="org-abc")
    assert isinstance(result, str)
    assert len(result) > 0


def test_build_client_prefix_with_different_client_ids():
    """Testa que diferentes client_ids geram prefixos diferentes."""
    prefix1 = build_client_prefix(client_id=100, org_id="org-1")
    prefix2 = build_client_prefix(client_id=200, org_id="org-1")
    # Prefixos devem ser diferentes
    assert prefix1 != prefix2


# --- Testes de build_auditoria_prefix ---


def test_build_auditoria_prefix_with_valid_root():
    """Testa construção de prefixo de auditoria."""
    client_root = "orgs/org-123/clients/456"
    result = build_auditoria_prefix(client_root)

    assert "/GERAL/Auditoria" in result
    assert result.startswith(client_root)
    assert not result.endswith("/")  # strip("/") deve remover trailing slash


def test_build_auditoria_prefix_strips_slashes():
    """Testa que build_auditoria_prefix remove slashes extras."""
    result = build_auditoria_prefix("/some/path/")
    assert not result.startswith("/")
    assert not result.endswith("/")


def test_build_auditoria_prefix_with_empty_root():
    """Testa com client_root vazio."""
    result = build_auditoria_prefix("")
    assert result == "GERAL/Auditoria"


# --- Testes de make_storage_context ---


def test_make_storage_context_creates_valid_context():
    """Testa criação de contexto de storage completo."""
    context = make_storage_context(client_id=100, org_id="org-abc")

    assert isinstance(context, AuditoriaStorageContext)
    assert context.bucket == CLIENTS_BUCKET
    assert context.org_id == "org-abc"
    assert len(context.client_root) > 0
    assert "/GERAL/Auditoria" in context.auditoria_prefix


def test_make_storage_context_build_path():
    """Testa método build_path do contexto."""
    context = make_storage_context(client_id=100, org_id="org-abc")

    path = context.build_path("documento.pdf")
    assert "documento.pdf" in path
    assert context.auditoria_prefix in path
    assert not path.endswith("/")


def test_make_storage_context_build_path_with_subdirs():
    """Testa build_path com subdiretórios."""
    context = make_storage_context(client_id=100, org_id="org-abc")

    path = context.build_path("subdir/file.txt")
    assert "subdir/file.txt" in path


def test_make_storage_context_build_path_strips_slashes():
    """Testa que build_path normaliza slashes."""
    context = make_storage_context(client_id=100, org_id="org-abc")

    path = context.build_path("/leading/slash/")
    assert not path.startswith("/")
    assert not path.endswith("/")


# --- Testes de AuditoriaStorageContext dataclass ---


def test_auditoria_storage_context_frozen():
    """Testa que AuditoriaStorageContext é imutável (frozen)."""
    context = AuditoriaStorageContext(
        bucket="test-bucket",
        org_id="org-1",
        client_root="root/path",
        auditoria_prefix="root/path/GERAL/Auditoria",
    )

    with pytest.raises(Exception):  # dataclass frozen raise FrozenInstanceError
        context.bucket = "new-bucket"  # type: ignore


# --- Testes de AuditoriaUploadContext dataclass ---


def test_auditoria_upload_context_creation():
    """Testa criação de AuditoriaUploadContext."""
    upload_ctx = AuditoriaUploadContext(bucket="test-bucket", base_prefix="prefix/path", org_id="org-1", client_id=123)

    assert upload_ctx.bucket == "test-bucket"
    assert upload_ctx.base_prefix == "prefix/path"
    assert upload_ctx.org_id == "org-1"
    assert upload_ctx.client_id == 123


def test_auditoria_upload_context_frozen():
    """Testa que AuditoriaUploadContext é imutável."""
    upload_ctx = AuditoriaUploadContext(bucket="test-bucket", base_prefix="prefix", org_id="org-1", client_id=123)

    with pytest.raises(Exception):
        upload_ctx.client_id = 999  # type: ignore


# --- Testes de ensure_auditoria_folder ---


def test_ensure_auditoria_folder_creates_keep_file():
    """Testa que ensure_auditoria_folder cria arquivo .keep."""
    mock_sb = MagicMock()
    mock_storage = MagicMock()
    mock_bucket = MagicMock()
    mock_upload_response = MagicMock()
    mock_upload_response.error = None

    mock_sb.storage = mock_storage
    mock_storage.from_.return_value = mock_bucket
    mock_bucket.upload.return_value = mock_upload_response

    context = AuditoriaStorageContext(
        bucket="test-bucket",
        org_id="org-1",
        client_root="root",
        auditoria_prefix="root/GERAL/Auditoria",
    )

    ensure_auditoria_folder(mock_sb, context)

    mock_storage.from_.assert_called_once_with("test-bucket")
    mock_bucket.upload.assert_called_once()

    # Verificar que o path contém .keep
    call_args = mock_bucket.upload.call_args
    assert ".keep" in call_args[1]["path"]
    assert call_args[1]["file"] == b""


def test_ensure_auditoria_folder_raises_on_error():
    """Testa que ensure_auditoria_folder lança exceção em caso de erro."""
    mock_sb = MagicMock()
    mock_storage = MagicMock()
    mock_bucket = MagicMock()
    mock_upload_response = MagicMock()
    mock_upload_response.error = "Upload failed"

    mock_sb.storage = mock_storage
    mock_storage.from_.return_value = mock_bucket
    mock_bucket.upload.return_value = mock_upload_response

    context = AuditoriaStorageContext(
        bucket="test-bucket",
        org_id="org-1",
        client_root="root",
        auditoria_prefix="root/GERAL/Auditoria",
    )

    with pytest.raises(RuntimeError, match="Upload failed"):
        ensure_auditoria_folder(mock_sb, context)


def test_ensure_auditoria_folder_handles_no_error_attribute():
    """Testa comportamento quando response não tem atributo error."""
    mock_sb = MagicMock()
    mock_storage = MagicMock()
    mock_bucket = MagicMock()
    mock_upload_response = Mock(spec=[])  # Sem atributo error

    mock_sb.storage = mock_storage
    mock_storage.from_.return_value = mock_bucket
    mock_bucket.upload.return_value = mock_upload_response

    context = AuditoriaStorageContext(
        bucket="test-bucket",
        org_id="org-1",
        client_root="root",
        auditoria_prefix="root/GERAL/Auditoria",
    )

    # getattr(..., None) deve retornar None e não lançar exceção
    ensure_auditoria_folder(mock_sb, context)
    mock_bucket.upload.assert_called_once()


# --- Testes de list_existing_file_names ---


def test_list_existing_file_names_single_page():
    """Testa listagem de arquivos em uma única página."""
    mock_sb = MagicMock()
    mock_storage = MagicMock()
    mock_bucket = MagicMock()

    mock_sb.storage = mock_storage
    mock_storage.from_.return_value = mock_bucket

    # Simular resposta com 3 arquivos
    mock_bucket.list.return_value = [
        {"name": "file1.pdf"},
        {"name": "file2.txt"},
        {"name": "file3.jpg"},
    ]

    result = list_existing_file_names(mock_sb, bucket="test-bucket", prefix="docs/")

    assert result == {"file1.pdf", "file2.txt", "file3.jpg"}
    mock_storage.from_.assert_called_once_with("test-bucket")
    mock_bucket.list.assert_called_once_with("docs/", {"limit": 1000, "offset": 0})


def test_list_existing_file_names_multiple_pages():
    """Testa paginação na listagem de arquivos."""
    mock_sb = MagicMock()
    mock_storage = MagicMock()
    mock_bucket = MagicMock()

    mock_sb.storage = mock_storage
    mock_storage.from_.return_value = mock_bucket

    # Primeira página: 2 arquivos (page_size=2)
    # Segunda página: 1 arquivo (menos que page_size → última página)
    mock_bucket.list.side_effect = [
        [{"name": "file1.pdf"}, {"name": "file2.txt"}],  # offset=0
        [{"name": "file3.jpg"}],  # offset=2
    ]

    result = list_existing_file_names(mock_sb, bucket="test-bucket", prefix="docs/", page_size=2)

    assert result == {"file1.pdf", "file2.txt", "file3.jpg"}
    assert mock_bucket.list.call_count == 2


def test_list_existing_file_names_empty_response():
    """Testa listagem quando não há arquivos."""
    mock_sb = MagicMock()
    mock_storage = MagicMock()
    mock_bucket = MagicMock()

    mock_sb.storage = mock_storage
    mock_storage.from_.return_value = mock_bucket
    mock_bucket.list.return_value = []

    result = list_existing_file_names(mock_sb, bucket="test-bucket", prefix="empty/")

    assert result == set()
    mock_bucket.list.assert_called_once()


def test_list_existing_file_names_none_response():
    """Testa listagem quando API retorna None."""
    mock_sb = MagicMock()
    mock_storage = MagicMock()
    mock_bucket = MagicMock()

    mock_sb.storage = mock_storage
    mock_storage.from_.return_value = mock_bucket
    mock_bucket.list.return_value = None

    result = list_existing_file_names(mock_sb, bucket="test-bucket", prefix="none/")

    assert result == set()


def test_list_existing_file_names_filters_items_without_name():
    """Testa que itens sem 'name' são filtrados."""
    mock_sb = MagicMock()
    mock_storage = MagicMock()
    mock_bucket = MagicMock()

    mock_sb.storage = mock_storage
    mock_storage.from_.return_value = mock_bucket

    mock_bucket.list.return_value = [
        {"name": "file1.pdf"},
        {"id": "123"},  # Sem 'name'
        {"name": ""},  # name vazio
        {"name": "file2.txt"},
        {},  # Dict vazio
    ]

    result = list_existing_file_names(mock_sb, bucket="test-bucket", prefix="docs/")

    assert result == {"file1.pdf", "file2.txt"}  # name vazio não é adicionado


def test_list_existing_file_names_pagination_exact_page_size():
    """Testa que paginação continua quando resposta tem exatamente page_size itens."""
    mock_sb = MagicMock()
    mock_storage = MagicMock()
    mock_bucket = MagicMock()

    mock_sb.storage = mock_storage
    mock_storage.from_.return_value = mock_bucket

    # Primeira página: exatamente 3 itens (page_size=3) → continua
    # Segunda página: 0 itens → para
    mock_bucket.list.side_effect = [
        [{"name": "f1"}, {"name": "f2"}, {"name": "f3"}],  # offset=0
        [],  # offset=3
    ]

    result = list_existing_file_names(mock_sb, bucket="test-bucket", prefix="p/", page_size=3)

    assert result == {"f1", "f2", "f3"}
    assert mock_bucket.list.call_count == 2


# --- Testes de upload_storage_bytes ---


def test_upload_storage_bytes_success():
    """Testa upload de bytes com sucesso."""
    mock_sb = MagicMock()
    mock_storage = MagicMock()
    mock_bucket = MagicMock()

    mock_sb.storage = mock_storage
    mock_storage.from_.return_value = mock_bucket

    data = b"conteudo do arquivo"
    upload_storage_bytes(
        mock_sb,
        bucket="test-bucket",
        dest_path="docs/file.pdf",
        data=data,
        content_type="application/pdf",
    )

    mock_storage.from_.assert_called_once_with("test-bucket")
    mock_bucket.upload.assert_called_once()

    call_args = mock_bucket.upload.call_args
    assert call_args[0][0] == "docs/file.pdf"
    assert call_args[0][1] == data
    assert call_args[0][2]["content-type"] == "application/pdf"
    assert call_args[0][2]["upsert"] == "false"
    assert call_args[0][2]["cacheControl"] == "3600"


def test_upload_storage_bytes_with_upsert():
    """Testa upload com upsert=True."""
    mock_sb = MagicMock()
    mock_storage = MagicMock()
    mock_bucket = MagicMock()

    mock_sb.storage = mock_storage
    mock_storage.from_.return_value = mock_bucket

    upload_storage_bytes(
        mock_sb,
        bucket="test-bucket",
        dest_path="docs/file.txt",
        data=b"data",
        content_type="text/plain",
        upsert=True,
    )

    call_args = mock_bucket.upload.call_args
    assert call_args[0][2]["upsert"] == "true"


def test_upload_storage_bytes_with_custom_cache_control():
    """Testa upload com cache_control customizado."""
    mock_sb = MagicMock()
    mock_storage = MagicMock()
    mock_bucket = MagicMock()

    mock_sb.storage = mock_storage
    mock_storage.from_.return_value = mock_bucket

    upload_storage_bytes(
        mock_sb,
        bucket="test-bucket",
        dest_path="docs/file.txt",
        data=b"data",
        content_type="text/plain",
        cache_control="7200",
    )

    call_args = mock_bucket.upload.call_args
    assert call_args[0][2]["cacheControl"] == "7200"


def test_upload_storage_bytes_empty_content_type_uses_default():
    """Testa que content_type vazio usa fallback."""
    mock_sb = MagicMock()
    mock_storage = MagicMock()
    mock_bucket = MagicMock()

    mock_sb.storage = mock_storage
    mock_storage.from_.return_value = mock_bucket

    upload_storage_bytes(mock_sb, bucket="test-bucket", dest_path="file", data=b"data", content_type="")

    call_args = mock_bucket.upload.call_args
    assert call_args[0][2]["content-type"] == "application/octet-stream"


def test_upload_storage_bytes_none_content_type_uses_default():
    """Testa que content_type None usa fallback."""
    mock_sb = MagicMock()
    mock_storage = MagicMock()
    mock_bucket = MagicMock()

    mock_sb.storage = mock_storage
    mock_storage.from_.return_value = mock_bucket

    upload_storage_bytes(
        mock_sb,
        bucket="test-bucket",
        dest_path="file",
        data=b"data",
        content_type=None,  # type: ignore
    )

    call_args = mock_bucket.upload.call_args
    assert call_args[0][2]["content-type"] == "application/octet-stream"


# --- Testes de remove_storage_objects ---


def test_remove_storage_objects_with_paths():
    """Testa remoção de múltiplos objetos."""
    mock_sb = MagicMock()
    mock_storage = MagicMock()
    mock_bucket = MagicMock()

    mock_sb.storage = mock_storage
    mock_storage.from_.return_value = mock_bucket

    paths = ["docs/file1.pdf", "docs/file2.txt", "images/photo.jpg"]
    remove_storage_objects(mock_sb, bucket="test-bucket", paths=paths)

    mock_storage.from_.assert_called_once_with("test-bucket")
    mock_bucket.remove.assert_called_once_with(paths)


def test_remove_storage_objects_with_single_path():
    """Testa remoção de um único objeto."""
    mock_sb = MagicMock()
    mock_storage = MagicMock()
    mock_bucket = MagicMock()

    mock_sb.storage = mock_storage
    mock_storage.from_.return_value = mock_bucket

    paths = ["docs/file1.pdf"]
    remove_storage_objects(mock_sb, bucket="test-bucket", paths=paths)

    mock_bucket.remove.assert_called_once_with(["docs/file1.pdf"])


def test_remove_storage_objects_with_empty_list():
    """Testa que lista vazia não chama remove."""
    mock_sb = MagicMock()
    mock_storage = MagicMock()
    mock_bucket = MagicMock()

    mock_sb.storage = mock_storage
    mock_storage.from_.return_value = mock_bucket

    remove_storage_objects(mock_sb, bucket="test-bucket", paths=[])

    # Não deve chamar from_ nem remove
    mock_storage.from_.assert_not_called()
    mock_bucket.remove.assert_not_called()


def test_remove_storage_objects_with_generator():
    """Testa que aceita generator/iterable como paths."""
    mock_sb = MagicMock()
    mock_storage = MagicMock()
    mock_bucket = MagicMock()

    mock_sb.storage = mock_storage
    mock_storage.from_.return_value = mock_bucket

    def path_generator():
        yield "file1.txt"
        yield "file2.txt"

    remove_storage_objects(mock_sb, bucket="test-bucket", paths=path_generator())

    mock_bucket.remove.assert_called_once_with(["file1.txt", "file2.txt"])


def test_remove_storage_objects_converts_iterable_to_list():
    """Testa que iterable é convertido para lista."""
    mock_sb = MagicMock()
    mock_storage = MagicMock()
    mock_bucket = MagicMock()

    mock_sb.storage = mock_storage
    mock_storage.from_.return_value = mock_bucket

    paths = {"file1.txt", "file2.txt"}  # Set é iterable
    remove_storage_objects(mock_sb, bucket="test-bucket", paths=paths)

    mock_bucket.remove.assert_called_once()
    # Verificar que foi convertido para lista
    called_paths = mock_bucket.remove.call_args[0][0]
    assert isinstance(called_paths, list)
    assert len(called_paths) == 2
