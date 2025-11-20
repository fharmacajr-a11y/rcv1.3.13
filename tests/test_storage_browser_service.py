"""Testes unitários para src/modules/uploads/storage_browser_service.py (esqueleto)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


from src.modules.uploads.storage_browser_service import (
    download_file_service,
    list_storage_objects_service,
)


class TestListStorageObjectsService:
    """Testes para list_storage_objects_service."""

    @patch("src.modules.uploads.storage_browser_service.storage_list_files")
    @patch("src.modules.uploads.storage_browser_service.using_storage_backend")
    @patch("src.modules.uploads.storage_browser_service.get_bucket_name")
    def test_normalizes_bucket_name(self, mock_get_bucket, mock_using, mock_list_files):
        """Testa que o service normaliza bucket_name (usa padrão se None)."""
        mock_get_bucket.return_value = "default-bucket"
        mock_list_files.return_value = iter([])
        mock_using.__enter__ = MagicMock()
        mock_using.__exit__ = MagicMock()

        ctx = {"bucket_name": None, "prefix": "test/path"}
        result = list_storage_objects_service(ctx)

        # Verifica que get_bucket_name foi chamado com string vazia
        mock_get_bucket.assert_called_once_with("")
        assert result["ok"] is True
        assert result["objects"] == []

    @patch("src.modules.uploads.storage_browser_service.storage_list_files")
    @patch("src.modules.uploads.storage_browser_service.using_storage_backend")
    @patch("src.modules.uploads.storage_browser_service.get_bucket_name")
    def test_lists_files_via_adapter(self, mock_get_bucket, mock_using, mock_list_files):
        """Testa que o service lista arquivos via SupabaseStorageAdapter."""
        mock_get_bucket.return_value = "test-bucket"
        mock_using.__enter__ = MagicMock()
        mock_using.__exit__ = MagicMock()

        # Mock de 2 arquivos e 1 pasta
        mock_list_files.return_value = iter(
            [
                {"name": "file1.pdf", "metadata": {"size": 100}, "full_path": "org/client/file1.pdf"},
                {"name": "file2.pdf", "metadata": {"size": 200}, "full_path": "org/client/file2.pdf"},
                {"name": "subfolder", "metadata": None, "full_path": "org/client/subfolder"},
            ]
        )

        ctx = {"bucket_name": "test-bucket", "prefix": "org/client"}
        result = list_storage_objects_service(ctx)

        assert result["ok"] is True
        assert len(result["objects"]) == 3
        assert result["objects"][0]["name"] == "file1.pdf"
        assert result["objects"][0]["is_folder"] is False
        assert result["objects"][2]["name"] == "subfolder"
        assert result["objects"][2]["is_folder"] is True

    @patch("src.modules.uploads.storage_browser_service.storage_list_files")
    @patch("src.modules.uploads.storage_browser_service.using_storage_backend")
    @patch("src.modules.uploads.storage_browser_service.get_bucket_name")
    def test_processes_response_and_builds_objects_list(self, mock_get_bucket, mock_using, mock_list_files):
        """Testa que o service processa resposta e monta lista de objetos."""
        mock_get_bucket.return_value = "test-bucket"
        mock_using.__enter__ = MagicMock()
        mock_using.__exit__ = MagicMock()

        mock_list_files.return_value = iter([{"name": "doc.pdf", "metadata": {"size": 500}, "full_path": "path/doc.pdf"}])

        ctx = {"bucket_name": "test-bucket", "prefix": "path"}
        result = list_storage_objects_service(ctx)

        assert result["ok"] is True
        assert len(result["objects"]) == 1
        obj = result["objects"][0]
        assert obj["name"] == "doc.pdf"
        assert obj["is_folder"] is False
        assert obj["full_path"] == "path/doc.pdf"

    @patch("src.modules.uploads.storage_browser_service.storage_list_files")
    @patch("src.modules.uploads.storage_browser_service.using_storage_backend")
    @patch("src.modules.uploads.storage_browser_service.get_bucket_name")
    def test_classifies_folders_vs_files(self, mock_get_bucket, mock_using, mock_list_files):
        """Testa que o service classifica objetos como pasta (is_folder=True) ou arquivo."""
        mock_get_bucket.return_value = "test-bucket"
        mock_using.__enter__ = MagicMock()
        mock_using.__exit__ = MagicMock()

        # Pasta: metadata=None, Arquivo: metadata presente
        mock_list_files.return_value = iter(
            [
                {"name": "folder1", "metadata": None},
                {"name": "file.txt", "metadata": {"size": 123}},
            ]
        )

        ctx = {"bucket_name": "test-bucket", "prefix": ""}
        result = list_storage_objects_service(ctx)

        assert result["ok"] is True
        assert result["objects"][0]["is_folder"] is True
        assert result["objects"][1]["is_folder"] is False

    @patch("src.modules.uploads.storage_browser_service.storage_list_files")
    @patch("src.modules.uploads.storage_browser_service.using_storage_backend")
    @patch("src.modules.uploads.storage_browser_service.get_bucket_name")
    def test_handles_bucket_not_found_error(self, mock_get_bucket, mock_using, mock_list_files):
        """Testa que o service trata erro de bucket não encontrado."""
        mock_get_bucket.return_value = "missing-bucket"
        mock_list_files.side_effect = Exception("Bucket not found")

        # Context manager mock
        mock_cm = MagicMock()
        mock_using.return_value = mock_cm
        mock_cm.__enter__.return_value = None
        mock_cm.__exit__.return_value = None

        ctx = {"bucket_name": "missing-bucket", "prefix": ""}
        result = list_storage_objects_service(ctx)

        assert result["ok"] is False
        assert result["error_type"] == "bucket_not_found"
        assert "Bucket não encontrado" in result["message"]
        assert len(result["errors"]) > 0

    @patch("src.modules.uploads.storage_browser_service.storage_list_files")
    @patch("src.modules.uploads.storage_browser_service.using_storage_backend")
    @patch("src.modules.uploads.storage_browser_service.get_bucket_name")
    def test_handles_generic_errors(self, mock_get_bucket, mock_using, mock_list_files):
        """Testa que o service trata erros genéricos."""
        mock_get_bucket.return_value = "test-bucket"
        mock_list_files.side_effect = Exception("Network timeout")

        # Context manager mock
        mock_cm = MagicMock()
        mock_using.return_value = mock_cm
        mock_cm.__enter__.return_value = None
        mock_cm.__exit__.return_value = None

        ctx = {"bucket_name": "test-bucket", "prefix": ""}
        result = list_storage_objects_service(ctx)

        assert result["ok"] is False
        assert result["error_type"] == "generic"
        assert "Erro ao listar objetos" in result["message"]
        assert "Network timeout" in result["errors"][0]

    @patch("src.modules.uploads.storage_browser_service.storage_list_files")
    @patch("src.modules.uploads.storage_browser_service.using_storage_backend")
    @patch("src.modules.uploads.storage_browser_service.get_bucket_name")
    def test_returns_correct_result_structure(self, mock_get_bucket, mock_using, mock_list_files):
        """Testa que o service retorna dict com ok, objects, errors, message."""
        mock_get_bucket.return_value = "test-bucket"
        mock_using.__enter__ = MagicMock()
        mock_using.__exit__ = MagicMock()
        mock_list_files.return_value = iter([])

        ctx = {"bucket_name": "test-bucket", "prefix": ""}
        result = list_storage_objects_service(ctx)

        # Verificar estrutura do retorno
        assert "ok" in result
        assert "objects" in result
        assert "errors" in result
        assert "message" in result
        assert "error_type" in result
        assert isinstance(result["objects"], list)
        assert isinstance(result["errors"], list)


class TestDownloadFileService:
    """Testes para download_file_service."""

    @patch("src.modules.uploads.storage_browser_service.storage_download_file")
    @patch("src.modules.uploads.storage_browser_service.using_storage_backend")
    @patch("src.modules.uploads.storage_browser_service.get_bucket_name")
    def test_downloads_file_via_adapter(self, mock_get_bucket, mock_using, mock_download):
        """Testa que o service faz download via storage_download_file."""
        mock_get_bucket.return_value = "test-bucket"
        mock_using.__enter__ = MagicMock()
        mock_using.__exit__ = MagicMock()

        ctx = {"bucket_name": "test-bucket", "file_path": "path/to/file.pdf", "local_path": "/tmp/file.pdf"}
        result = download_file_service(ctx)

        # Verifica que storage_download_file foi chamado
        mock_download.assert_called_once_with("path/to/file.pdf", "/tmp/file.pdf")
        assert result["ok"] is True
        assert result["local_path"] == "/tmp/file.pdf"

    @patch("src.modules.uploads.storage_browser_service.get_bucket_name")
    def test_validates_bucket_and_file_path(self, mock_get_bucket):
        """Testa que o service valida bucket_name e file_path."""
        mock_get_bucket.return_value = "test-bucket"

        # Caso 1: file_path vazio
        ctx = {"bucket_name": "test-bucket", "file_path": "", "local_path": "/tmp/file.pdf"}
        result = download_file_service(ctx)

        assert result["ok"] is False
        assert "inválidos" in result["message"]

        # Caso 2: local_path vazio
        ctx = {"bucket_name": "test-bucket", "file_path": "file.pdf", "local_path": ""}
        result = download_file_service(ctx)

        assert result["ok"] is False
        assert "inválidos" in result["message"]

    @patch("src.modules.uploads.storage_browser_service.storage_download_file")
    @patch("src.modules.uploads.storage_browser_service.using_storage_backend")
    @patch("src.modules.uploads.storage_browser_service.get_bucket_name")
    def test_handles_download_errors(self, mock_get_bucket, mock_using, mock_download):
        """Testa que o service trata erros de download adequadamente."""
        mock_get_bucket.return_value = "test-bucket"
        mock_using.__enter__ = MagicMock()
        mock_using.__exit__ = MagicMock()
        mock_download.side_effect = Exception("File not found in storage")

        ctx = {"bucket_name": "test-bucket", "file_path": "missing.pdf", "local_path": "/tmp/missing.pdf"}
        result = download_file_service(ctx)

        assert result["ok"] is False
        assert "Erro ao baixar arquivo" in result["message"]
        assert "File not found in storage" in result["errors"][0]

    @patch("src.modules.uploads.storage_browser_service.storage_download_file")
    @patch("src.modules.uploads.storage_browser_service.using_storage_backend")
    @patch("src.modules.uploads.storage_browser_service.get_bucket_name")
    def test_returns_file_bytes(self, mock_get_bucket, mock_using, mock_download):
        """Testa que o service retorna bytes do arquivo baixado."""
        mock_get_bucket.return_value = "test-bucket"
        mock_using.__enter__ = MagicMock()
        mock_using.__exit__ = MagicMock()

        ctx = {"bucket_name": "test-bucket", "file_path": "doc.pdf", "local_path": "/tmp/doc.pdf"}
        result = download_file_service(ctx)

        assert result["ok"] is True
        assert result["local_path"] == "/tmp/doc.pdf"
        assert "baixado com sucesso" in result["message"]

    @patch("src.modules.uploads.storage_browser_service.storage_download_file")
    @patch("src.modules.uploads.storage_browser_service.using_storage_backend")
    @patch("src.modules.uploads.storage_browser_service.get_bucket_name")
    def test_returns_correct_result_structure(self, mock_get_bucket, mock_using, mock_download):
        """Testa que o service retorna dict com ok, data, errors."""
        mock_get_bucket.return_value = "test-bucket"
        mock_using.__enter__ = MagicMock()
        mock_using.__exit__ = MagicMock()

        ctx = {"bucket_name": "test-bucket", "file_path": "file.pdf", "local_path": "/tmp/file.pdf"}
        result = download_file_service(ctx)

        # Verificar estrutura do retorno
        assert "ok" in result
        assert "errors" in result
        assert "message" in result
        assert "local_path" in result
        assert isinstance(result["errors"], list)
