# tests/unit/modules/uploads/test_uploads_service_fase62.py
"""
Testes para uploads/service.py (upload/download/delete de arquivos no Storage).

Escopo (sem network/FS real):
1) download_and_open_file: 3 platforms (win/mac/linux), 2 modes (external/internal), error paths
2) delete_storage_folder: recursão, parcial ok, edge cases
3) delete_storage_object: error handling sem exceção
4) upload_folder_to_supabase: auth check, validação
5) list_browser_items: wrapper com normalização
6) download_storage_object: wrapper
7) upload_items_for_client: callback + partial errors

Cobertura: Mocks de repository + validation + storage API + system calls.
Isolamento: sem network, sem FS (tmp_path/monkeypatch), sem subprocess real.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

from src.modules.uploads.service import (
    UploadItem,
    build_items_from_files,
    collect_pdfs_from_folder,
    delete_storage_folder,
    delete_storage_object,
    download_and_open_file,
    download_storage_object,
    list_browser_items,
    upload_folder_to_supabase,
    upload_items_for_client,
)


# ==========================================
# Fixtures: mocking de dependências
# ==========================================
@pytest.fixture
def mock_repository(monkeypatch: pytest.MonkeyPatch) -> dict[str, Mock]:
    """Mock completo do módulo repository."""
    mocks = {
        "current_user_id": Mock(return_value="user-123"),
        "resolve_org_id": Mock(return_value="org-456"),
        "build_storage_adapter": Mock(),
        "normalize_bucket": Mock(return_value="rc-docs"),
        "upload_items_with_adapter": Mock(return_value=(2, [])),
        "ensure_storage_object_absent": Mock(),
        "upload_local_file": Mock(),
        "insert_document_record": Mock(return_value={"id": 1}),
        "insert_document_version_record": Mock(return_value={"id": 1}),
        "update_document_current_version": Mock(),
    }
    for name, mock in mocks.items():
        monkeypatch.setattr(f"src.modules.uploads.service.repository.{name}", mock)
    return mocks


@pytest.fixture
def mock_validation(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, Mock]:
    """Mock completo do módulo validation."""
    mock_entry = Mock()
    mock_entry.relative_path = "file.pdf"
    mock_entry.storage_path = "org/client/file.pdf"
    mock_entry.safe_relative_path = "file.pdf"
    mock_entry.path = tmp_path / "file.pdf"
    mock_entry.size_bytes = 1024
    mock_entry.sha256 = "abc123"
    mock_entry.mime_type = "application/pdf"

    mocks = {
        "ensure_existing_folder": Mock(return_value=tmp_path),
        "prepare_folder_entries": Mock(return_value=[mock_entry]),
        "collect_pdf_items_from_folder": Mock(return_value=[]),
        "build_items_from_files": Mock(return_value=[]),
        "build_remote_path": Mock(return_value="org/client/file.pdf"),
    }
    for name, mock in mocks.items():
        monkeypatch.setattr(f"src.modules.uploads.service.validation.{name}", mock)
    return mocks


@pytest.fixture
def mock_storage_api(monkeypatch: pytest.MonkeyPatch) -> dict[str, Mock]:
    """Mock de adapters.storage.api."""
    mock_context = Mock()
    mock_context.__enter__ = Mock(return_value=None)
    mock_context.__exit__ = Mock(return_value=False)

    mocks = {
        "delete_file": Mock(return_value=True),
        "using_storage_backend": Mock(return_value=mock_context),
        "download_folder_zip": Mock(),
    }
    monkeypatch.setattr("src.modules.uploads.service._delete_file", mocks["delete_file"])
    monkeypatch.setattr("src.modules.uploads.service.using_storage_backend", mocks["using_storage_backend"])
    monkeypatch.setattr("src.modules.uploads.service._download_folder_zip", mocks["download_folder_zip"])
    return mocks


@pytest.fixture
def mock_temp_files(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Mock:
    """Mock de create_temp_file."""
    mock_temp_info = Mock()
    mock_temp_info.path = str(tmp_path / "temp_file.pdf")
    mock = Mock(return_value=mock_temp_info)
    monkeypatch.setattr("src.modules.uploads.service.create_temp_file", mock)
    return mock


@pytest.fixture
def mock_download_file(monkeypatch: pytest.MonkeyPatch) -> Mock:
    """Mock de download_file (lazy import)."""
    mock = Mock(return_value={"ok": True, "message": "Success", "local_path": "/tmp/file.pdf"})
    monkeypatch.setattr("src.modules.forms.view.download_file", mock)
    return mock


@pytest.fixture
def mock_list_storage_objects(monkeypatch: pytest.MonkeyPatch) -> Mock:
    """Mock de list_storage_objects (lazy import)."""
    mock = Mock(return_value=[])
    monkeypatch.setattr("src.modules.forms.view.list_storage_objects", mock)
    return mock


@pytest.fixture
def mock_helpers(monkeypatch: pytest.MonkeyPatch) -> dict[str, Mock]:
    """Mock de funções helper."""
    mocks = {
        "get_clients_bucket": Mock(return_value="rc-docs"),
        "get_current_org_id": Mock(return_value="org-456"),
    }
    monkeypatch.setattr("src.modules.uploads.service.get_clients_bucket", mocks["get_clients_bucket"])
    monkeypatch.setattr("src.modules.uploads.service.get_current_org_id", mocks["get_current_org_id"])
    return mocks


# ==========================================
# Testes: download_and_open_file
# ==========================================
def test_download_and_open_file_invalid_mode(
    mock_helpers: dict[str, Mock],
) -> None:
    """download_and_open_file levanta ValueError se mode inválido."""
    with pytest.raises(ValueError, match="Modo inválido"):
        download_and_open_file("file.pdf", mode="invalid")


def test_download_and_open_file_internal_mode_success(
    mock_helpers: dict[str, Mock],
    mock_temp_files: Mock,
    mock_download_file: Mock,
    tmp_path: Path,
) -> None:
    """download_and_open_file mode='internal' retorna temp_path sem abrir."""
    # Criar arquivo temporário para os.path.getsize
    temp_file = tmp_path / "temp_file.pdf"
    temp_file.write_bytes(b"fake pdf content")
    mock_temp_files.return_value.path = str(temp_file)

    result = download_and_open_file("org/client/file.pdf", mode="internal")

    assert result["ok"] is True
    assert result["mode"] == "internal"
    assert "temp_path" in result
    assert result["display_name"] == "file.pdf"
    # Não deve chamar os.startfile nem subprocess


def test_download_and_open_file_external_windows(
    mock_helpers: dict[str, Mock],
    mock_temp_files: Mock,
    mock_download_file: Mock,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """download_and_open_file mode='external' no Windows usa os.startfile."""
    monkeypatch.setattr(sys, "platform", "win32")
    mock_startfile = Mock()
    monkeypatch.setattr("os.startfile", mock_startfile, raising=False)

    temp_file = tmp_path / "temp_file.pdf"
    temp_file.write_bytes(b"fake pdf")
    mock_temp_files.return_value.path = str(temp_file)

    result = download_and_open_file("org/client/file.pdf", mode="external")

    assert result["ok"] is True
    assert "temp_path" in result
    mock_startfile.assert_called_once_with(str(temp_file))


def test_download_and_open_file_external_macos(
    mock_helpers: dict[str, Mock],
    mock_temp_files: Mock,
    mock_download_file: Mock,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """download_and_open_file mode='external' no macOS usa 'open'."""
    monkeypatch.setattr(sys, "platform", "darwin")
    mock_which = Mock(return_value="/usr/bin/open")
    mock_popen = Mock()
    monkeypatch.setattr("shutil.which", mock_which)
    monkeypatch.setattr("subprocess.Popen", mock_popen)

    temp_file = tmp_path / "temp_file.pdf"
    temp_file.write_bytes(b"fake pdf")
    mock_temp_files.return_value.path = str(temp_file)

    result = download_and_open_file("org/client/file.pdf", mode="external")

    assert result["ok"] is True
    mock_which.assert_called_once_with("open")
    mock_popen.assert_called_once()
    call_args = mock_popen.call_args[0][0]
    assert call_args == ["/usr/bin/open", str(temp_file)]


def test_download_and_open_file_external_linux(
    mock_helpers: dict[str, Mock],
    mock_temp_files: Mock,
    mock_download_file: Mock,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """download_and_open_file mode='external' no Linux usa 'xdg-open'."""
    monkeypatch.setattr(sys, "platform", "linux")
    mock_which = Mock(return_value="/usr/bin/xdg-open")
    mock_popen = Mock()
    monkeypatch.setattr("shutil.which", mock_which)
    monkeypatch.setattr("subprocess.Popen", mock_popen)

    temp_file = tmp_path / "temp_file.pdf"
    temp_file.write_bytes(b"fake pdf")
    mock_temp_files.return_value.path = str(temp_file)

    result = download_and_open_file("org/client/file.pdf", mode="external")

    assert result["ok"] is True
    mock_which.assert_called_once_with("xdg-open")
    mock_popen.assert_called_once()
    call_args = mock_popen.call_args[0][0]
    assert call_args == ["/usr/bin/xdg-open", str(temp_file)]


def test_download_and_open_file_external_command_not_found(
    mock_helpers: dict[str, Mock],
    mock_temp_files: Mock,
    mock_download_file: Mock,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """download_and_open_file retorna erro se comando não encontrado."""
    monkeypatch.setattr(sys, "platform", "linux")
    mock_which = Mock(return_value=None)  # xdg-open não encontrado
    monkeypatch.setattr("shutil.which", mock_which)

    temp_file = tmp_path / "temp_file.pdf"
    temp_file.write_bytes(b"fake pdf")
    mock_temp_files.return_value.path = str(temp_file)

    result = download_and_open_file("org/client/file.pdf", mode="external")

    assert result["ok"] is False
    assert "não foi possível abri-lo" in result["message"]
    assert "temp_path" in result


def test_download_and_open_file_download_fails(
    mock_helpers: dict[str, Mock],
    mock_temp_files: Mock,
    mock_download_file: Mock,
) -> None:
    """download_and_open_file retorna erro se download falhar."""
    mock_download_file.return_value = {"ok": False, "message": "Network error"}

    result = download_and_open_file("org/client/file.pdf")

    assert result["ok"] is False
    assert result["message"] == "Network error"
    assert "error" in result


def test_download_and_open_file_temp_creation_fails(
    mock_helpers: dict[str, Mock],
    mock_temp_files: Mock,
) -> None:
    """download_and_open_file retorna erro se criar temp file falhar."""
    mock_temp_files.side_effect = OSError("Disk full")

    result = download_and_open_file("org/client/file.pdf")

    assert result["ok"] is False
    assert "Erro ao preparar arquivo temporário" in result["message"]


# ==========================================
# Testes: delete_storage_folder
# ==========================================
def test_delete_storage_folder_empty_prefix(
    mock_helpers: dict[str, Mock],
) -> None:
    """delete_storage_folder retorna erro se prefix vazio."""
    result = delete_storage_folder("")

    assert result["ok"] is False
    assert "prefix vazio" in result["errors"]


def test_delete_storage_folder_success(
    mock_helpers: dict[str, Mock],
    mock_list_storage_objects: Mock,
    mock_storage_api: dict[str, Mock],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """delete_storage_folder deleta todos os arquivos com sucesso."""
    # Mock list_storage_objects para retornar arquivos
    mock_list_storage_objects.return_value = [
        {"full_path": "org/client/file1.pdf", "is_folder": False},
        {"full_path": "org/client/file2.pdf", "is_folder": False},
    ]

    result = delete_storage_folder("org/client")

    assert result["ok"] is True
    assert result["deleted"] == 2
    assert result["errors"] == []
    assert "2 arquivo(s)" in result["message"]
    # Verifica que delete_file foi chamado 2 vezes
    assert mock_storage_api["delete_file"].call_count == 2


def test_delete_storage_folder_partial_failure(
    mock_helpers: dict[str, Mock],
    mock_list_storage_objects: Mock,
    mock_storage_api: dict[str, Mock],
) -> None:
    """delete_storage_folder deleta o que conseguir, acumula erros."""
    mock_list_storage_objects.return_value = [
        {"full_path": "org/client/file1.pdf", "is_folder": False},
        {"full_path": "org/client/file2.pdf", "is_folder": False},
    ]
    # Simular falha no segundo arquivo
    mock_storage_api["delete_file"].side_effect = [True, False]

    result = delete_storage_folder("org/client")

    assert result["ok"] is False
    assert result["deleted"] == 1
    assert len(result["errors"]) == 1
    assert "file2.pdf" in result["errors"][0]


def test_delete_storage_folder_exception_on_delete(
    mock_helpers: dict[str, Mock],
    mock_list_storage_objects: Mock,
    mock_storage_api: dict[str, Mock],
) -> None:
    """delete_storage_folder captura exceção ao deletar, continua."""
    mock_list_storage_objects.return_value = [
        {"full_path": "org/client/file1.pdf", "is_folder": False},
        {"full_path": "org/client/file2.pdf", "is_folder": False},
    ]
    mock_storage_api["delete_file"].side_effect = [RuntimeError("Network error"), True]

    result = delete_storage_folder("org/client")

    assert result["ok"] is False
    assert result["deleted"] == 1
    assert len(result["errors"]) == 1
    assert "Network error" in result["errors"][0]


def test_delete_storage_folder_recursive(
    mock_helpers: dict[str, Mock],
    monkeypatch: pytest.MonkeyPatch,
    mock_storage_api: dict[str, Mock],
) -> None:
    """delete_storage_folder coleta arquivos recursivamente de subpastas."""
    # Mock _collect_storage_keys diretamente (mais simples que mockar list_storage_objects recursivamente)
    mock_collect = Mock(return_value=["org/client/sub/file1.pdf", "org/client/sub/file2.pdf"])
    monkeypatch.setattr("src.modules.uploads.service._collect_storage_keys", mock_collect)

    result = delete_storage_folder("org/client")

    assert result["ok"] is True
    assert result["deleted"] == 2
    mock_collect.assert_called_once_with("rc-docs", "org/client")


# ==========================================
# Testes: delete_storage_object
# ==========================================
def test_delete_storage_object_success(
    mock_helpers: dict[str, Mock],
    mock_storage_api: dict[str, Mock],
) -> None:
    """delete_storage_object retorna True em sucesso."""
    result = delete_storage_object("org/client/file.pdf")

    assert result is True
    mock_storage_api["delete_file"].assert_called_once_with("org/client/file.pdf")


def test_delete_storage_object_failure(
    mock_helpers: dict[str, Mock],
    mock_storage_api: dict[str, Mock],
) -> None:
    """delete_storage_object retorna False se delete_file retornar False."""
    mock_storage_api["delete_file"].return_value = False

    result = delete_storage_object("org/client/file.pdf")

    assert result is False


def test_delete_storage_object_exception(
    mock_helpers: dict[str, Mock],
    mock_storage_api: dict[str, Mock],
) -> None:
    """delete_storage_object retorna False se exceção, sem propagar."""
    mock_storage_api["delete_file"].side_effect = RuntimeError("Network error")

    result = delete_storage_object("org/client/file.pdf")

    assert result is False


# ==========================================
# Testes: upload_folder_to_supabase
# ==========================================
def test_upload_folder_to_supabase_success(
    mock_repository: dict[str, Mock],
    mock_validation: dict[str, Mock],
    tmp_path: Path,
) -> None:
    """upload_folder_to_supabase retorna lista de metadados em sucesso."""
    folder = tmp_path / "uploads"
    folder.mkdir()

    result = upload_folder_to_supabase(str(folder), client_id=123)

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["document_id"] == 1
    assert result[0]["version_id"] == 1
    assert result[0]["storage_path"] == "org/client/file.pdf"
    # Verifica chamadas
    mock_repository["current_user_id"].assert_called_once()
    mock_repository["resolve_org_id"].assert_called_once()
    mock_repository["insert_document_record"].assert_called_once()
    mock_repository["insert_document_version_record"].assert_called_once()


def test_upload_folder_to_supabase_no_user(
    mock_repository: dict[str, Mock],
    mock_validation: dict[str, Mock],
    tmp_path: Path,
) -> None:
    """upload_folder_to_supabase levanta RuntimeError se sem usuário."""
    mock_repository["current_user_id"].return_value = None
    folder = tmp_path / "uploads"
    folder.mkdir()

    with pytest.raises(RuntimeError, match="Usuario nao autenticado"):
        upload_folder_to_supabase(str(folder), client_id=123)


# ==========================================
# Testes: upload_items_for_client
# ==========================================
def test_upload_items_for_client_success(
    mock_repository: dict[str, Mock],
    tmp_path: Path,
) -> None:
    """upload_items_for_client retorna (success_count, []) em sucesso."""
    items = [
        UploadItem(path=tmp_path / "file1.pdf", relative_path="file1.pdf"),
        UploadItem(path=tmp_path / "file2.pdf", relative_path="file2.pdf"),
    ]
    mock_repository["upload_items_with_adapter"].return_value = (2, [])

    success, errors = upload_items_for_client(items, cnpj_digits="12345678000110")

    assert success == 2
    assert errors == []
    mock_repository["build_storage_adapter"].assert_called_once()
    mock_repository["upload_items_with_adapter"].assert_called_once()


def test_upload_items_for_client_partial_errors(
    mock_repository: dict[str, Mock],
    tmp_path: Path,
) -> None:
    """upload_items_for_client retorna (partial_count, errors) se houver falhas."""
    items = [
        UploadItem(path=tmp_path / "file1.pdf", relative_path="file1.pdf"),
        UploadItem(path=tmp_path / "file2.pdf", relative_path="file2.pdf"),
    ]
    error_tuple = (items[1], RuntimeError("Upload failed"))
    mock_repository["upload_items_with_adapter"].return_value = (1, [error_tuple])

    success, errors = upload_items_for_client(items, cnpj_digits="12345678000110")

    assert success == 1
    assert len(errors) == 1
    assert errors[0][0] == items[1]
    assert isinstance(errors[0][1], RuntimeError)


def test_upload_items_for_client_progress_callback(
    mock_repository: dict[str, Mock],
    tmp_path: Path,
) -> None:
    """upload_items_for_client passa callback para repository."""
    items = [UploadItem(path=tmp_path / "file1.pdf", relative_path="file1.pdf")]
    callback = Mock()

    upload_items_for_client(items, cnpj_digits="12345678000110", progress_callback=callback)

    # Verifica que callback foi passado
    call_kwargs = mock_repository["upload_items_with_adapter"].call_args[1]
    assert call_kwargs["progress_callback"] == callback


# ==========================================
# Testes: list_browser_items
# ==========================================
def test_list_browser_items_normalizes_prefix(
    mock_helpers: dict[str, Mock],
    mock_list_storage_objects: Mock,
) -> None:
    """list_browser_items normaliza prefix removendo '/'."""
    list_browser_items("/org/client/")

    # Verifica que chamou com prefix normalizado
    mock_list_storage_objects.assert_called_once_with("rc-docs", "org/client")


def test_list_browser_items_uses_default_bucket(
    mock_helpers: dict[str, Mock],
    mock_list_storage_objects: Mock,
) -> None:
    """list_browser_items usa bucket padrão se não fornecido."""
    list_browser_items("org/client")

    mock_helpers["get_clients_bucket"].assert_called_once()
    mock_list_storage_objects.assert_called_once_with("rc-docs", "org/client")


def test_list_browser_items_uses_explicit_bucket(
    mock_helpers: dict[str, Mock],
    mock_list_storage_objects: Mock,
) -> None:
    """list_browser_items usa bucket explícito se fornecido."""
    list_browser_items("org/client", bucket="custom-bucket")

    # Não deve chamar get_clients_bucket
    mock_helpers["get_clients_bucket"].assert_not_called()
    mock_list_storage_objects.assert_called_once_with("custom-bucket", "org/client")


# ==========================================
# Testes: download_storage_object
# ==========================================
def test_download_storage_object_success(
    mock_helpers: dict[str, Mock],
    mock_download_file: Mock,
) -> None:
    """download_storage_object retorna dict com ok=True em sucesso."""
    result = download_storage_object("org/client/file.pdf", "/tmp/file.pdf")

    assert result["ok"] is True
    mock_download_file.assert_called_once_with("rc-docs", "org/client/file.pdf", "/tmp/file.pdf")


def test_download_storage_object_failure(
    mock_helpers: dict[str, Mock],
    mock_download_file: Mock,
) -> None:
    """download_storage_object retorna dict com ok=False em falha."""
    mock_download_file.return_value = {"ok": False, "message": "Network error"}

    result = download_storage_object("org/client/file.pdf", "/tmp/file.pdf")

    assert result["ok"] is False
    assert result["message"] == "Network error"


# ==========================================
# Testes: collect_pdfs_from_folder
# ==========================================
def test_collect_pdfs_from_folder_delegates(
    mock_validation: dict[str, Mock],
) -> None:
    """collect_pdfs_from_folder delega para validation."""
    mock_validation["collect_pdf_items_from_folder"].return_value = [
        UploadItem(path=Path("/tmp/file.pdf"), relative_path="file.pdf")
    ]

    result = collect_pdfs_from_folder("/tmp")

    assert len(result) == 1
    assert result[0].relative_path == "file.pdf"
    mock_validation["collect_pdf_items_from_folder"].assert_called_once()


# ==========================================
# Testes: build_items_from_files
# ==========================================
def test_build_items_from_files_delegates(
    mock_validation: dict[str, Mock],
) -> None:
    """build_items_from_files delega para validation."""
    mock_validation["build_items_from_files"].return_value = [
        UploadItem(path=Path("/tmp/file.pdf"), relative_path="file.pdf")
    ]

    result = build_items_from_files(["/tmp/file.pdf"])

    assert len(result) == 1
    assert result[0].relative_path == "file.pdf"
    mock_validation["build_items_from_files"].assert_called_once()


# ==========================================
# Testes: edge cases
# ==========================================
def test_download_and_open_file_default_bucket(
    mock_helpers: dict[str, Mock],
    mock_temp_files: Mock,
    mock_download_file: Mock,
    tmp_path: Path,
) -> None:
    """download_and_open_file usa bucket padrão se não fornecido."""
    temp_file = tmp_path / "temp_file.pdf"
    temp_file.write_bytes(b"fake pdf")
    mock_temp_files.return_value.path = str(temp_file)

    download_and_open_file("org/client/file.pdf", mode="internal")

    mock_helpers["get_clients_bucket"].assert_called()


def test_delete_storage_folder_empty_result(
    mock_helpers: dict[str, Mock],
    mock_list_storage_objects: Mock,
    mock_storage_api: dict[str, Mock],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """delete_storage_folder com pasta vazia retorna ok=True, deleted=0."""
    mock_collect = Mock(return_value=[])
    monkeypatch.setattr("src.modules.uploads.service._collect_storage_keys", mock_collect)

    result = delete_storage_folder("org/client")

    assert result["ok"] is True
    assert result["deleted"] == 0
    # Não deve chamar delete_file
    mock_storage_api["delete_file"].assert_not_called()


def test_upload_folder_to_supabase_multiple_files(
    mock_repository: dict[str, Mock],
    mock_validation: dict[str, Mock],
    tmp_path: Path,
) -> None:
    """upload_folder_to_supabase processa múltiplos arquivos."""
    # Mock múltiplas entries
    entry1 = Mock()
    entry1.relative_path = "file1.pdf"
    entry1.storage_path = "org/client/file1.pdf"
    entry1.safe_relative_path = "file1.pdf"
    entry1.path = tmp_path / "file1.pdf"
    entry1.size_bytes = 1024
    entry1.sha256 = "abc123"
    entry1.mime_type = "application/pdf"

    entry2 = Mock()
    entry2.relative_path = "file2.pdf"
    entry2.storage_path = "org/client/file2.pdf"
    entry2.safe_relative_path = "file2.pdf"
    entry2.path = tmp_path / "file2.pdf"
    entry2.size_bytes = 2048
    entry2.sha256 = "def456"
    entry2.mime_type = "application/pdf"

    mock_validation["prepare_folder_entries"].return_value = [entry1, entry2]
    mock_repository["insert_document_record"].side_effect = [{"id": 1}, {"id": 2}]
    mock_repository["insert_document_version_record"].side_effect = [{"id": 10}, {"id": 20}]

    folder = tmp_path / "uploads"
    folder.mkdir()

    result = upload_folder_to_supabase(str(folder), client_id=123)

    assert len(result) == 2
    assert result[0]["document_id"] == 1
    assert result[1]["document_id"] == 2
    # Verifica que insert_document_record foi chamado 2 vezes
    assert mock_repository["insert_document_record"].call_count == 2
