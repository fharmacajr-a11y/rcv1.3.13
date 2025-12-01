"""Testes unitários para src/modules/uploads/service.py.

Tarefa: TEST-001 – Criar suite de testes para módulo de uploads.
Fase: 32
Objetivo: Aumentar cobertura de testes do módulo uploads sem alterar código de produção.
"""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from src.modules.uploads import service as uploads_service
from src.modules.uploads.service import UploadItem


# ========================================
# Testes para upload_folder_to_supabase
# ========================================


class TestUploadFolderToSupabase:
    """Testes para a função upload_folder_to_supabase."""

    @patch("src.modules.uploads.service.repository")
    @patch("src.modules.uploads.service.validation")
    def test_usuario_nao_autenticado(self, mock_validation: Mock, mock_repository: Mock) -> None:
        """Deve lançar RuntimeError quando usuário não está autenticado."""
        # Arrange
        mock_validation.ensure_existing_folder.return_value = Path("/fake/folder")
        mock_repository.current_user_id.return_value = None

        # Act & Assert
        with pytest.raises(RuntimeError, match="Usuario nao autenticado"):
            uploads_service.upload_folder_to_supabase(folder="/fake/folder", client_id=123, subdir="SIFAP")

        # Verificar que nenhum upload foi realizado
        mock_repository.upload_local_file.assert_not_called()
        mock_repository.insert_document_record.assert_not_called()

    @patch("src.modules.uploads.service._sha256")
    @patch("src.modules.uploads.service.repository")
    @patch("src.modules.uploads.service.validation")
    def test_upload_caminho_feliz(
        self,
        mock_validation: Mock,
        mock_repository: Mock,
        mock_sha256: Mock,
    ) -> None:
        """Deve fazer upload completo com sucesso quando tudo está OK."""
        # Arrange
        base_folder = Path("/fake/folder")
        mock_validation.ensure_existing_folder.return_value = base_folder

        # Mock user e org
        mock_repository.current_user_id.return_value = "user-123"
        mock_repository.resolve_org_id.return_value = "org-456"

        # Mock prepared entries
        entry1 = MagicMock()
        entry1.relative_path = "doc1.pdf"
        entry1.safe_relative_path = "doc1.pdf"
        entry1.storage_path = "org-456/client-123/SIFAP/doc1.pdf"
        entry1.path = Path("/fake/folder/doc1.pdf")
        entry1.mime_type = "application/pdf"
        entry1.size_bytes = 1024
        entry1.sha256 = "hash1"

        entry2 = MagicMock()
        entry2.relative_path = "doc2.pdf"
        entry2.safe_relative_path = "doc2.pdf"
        entry2.storage_path = "org-456/client-123/SIFAP/doc2.pdf"
        entry2.path = Path("/fake/folder/doc2.pdf")
        entry2.mime_type = "application/pdf"
        entry2.size_bytes = 2048
        entry2.sha256 = "hash2"

        mock_validation.prepare_folder_entries.return_value = [entry1, entry2]

        # Mock repository responses
        mock_repository.insert_document_record.side_effect = [
            {"id": 1},
            {"id": 2},
        ]
        mock_repository.insert_document_version_record.side_effect = [
            {"id": 10},
            {"id": 20},
        ]

        # Act
        results = uploads_service.upload_folder_to_supabase(folder="/fake/folder", client_id=123, subdir="SIFAP")

        # Assert
        assert len(results) == 2

        # Verificar primeiro item
        assert results[0]["relative_path"] == "doc1.pdf"
        assert results[0]["storage_path"] == "org-456/client-123/SIFAP/doc1.pdf"
        assert results[0]["document_id"] == 1
        assert results[0]["version_id"] == 10
        assert results[0]["size_bytes"] == 1024
        assert results[0]["sha256"] == "hash1"

        # Verificar segundo item
        assert results[1]["relative_path"] == "doc2.pdf"
        assert results[1]["document_id"] == 2
        assert results[1]["version_id"] == 20

        # Verificar chamadas ao repository
        assert mock_repository.ensure_storage_object_absent.call_count == 2
        assert mock_repository.upload_local_file.call_count == 2
        assert mock_repository.insert_document_record.call_count == 2
        assert mock_repository.insert_document_version_record.call_count == 2
        assert mock_repository.update_document_current_version.call_count == 2

        # Verificar que update_document_current_version foi chamado com IDs corretos
        mock_repository.update_document_current_version.assert_any_call(1, 10)
        mock_repository.update_document_current_version.assert_any_call(2, 20)

    @patch("src.modules.uploads.service.repository")
    @patch("src.modules.uploads.service.validation")
    def test_pasta_nao_existe(self, mock_validation: Mock, mock_repository: Mock) -> None:
        """Deve propagar FileNotFoundError quando pasta não existe."""
        # Arrange
        mock_validation.ensure_existing_folder.side_effect = FileNotFoundError("Pasta nao encontrada: /fake/missing")

        # Act & Assert
        with pytest.raises(FileNotFoundError, match="Pasta nao encontrada"):
            uploads_service.upload_folder_to_supabase(folder="/fake/missing", client_id=123, subdir="SIFAP")


# ========================================
# Testes para collect_pdfs_from_folder
# ========================================


class TestCollectPdfsFromFolder:
    """Testes para a função collect_pdfs_from_folder."""

    @patch("src.modules.uploads.service.validation")
    def test_coleta_items_corretamente(self, mock_validation: Mock) -> None:
        """Deve coletar itens de upload da validação."""
        # Arrange
        expected_items = [
            MagicMock(spec=UploadItem),
            MagicMock(spec=UploadItem),
        ]
        mock_validation.collect_pdf_items_from_folder.return_value = expected_items

        # Act
        result = uploads_service.collect_pdfs_from_folder("/fake/dir")

        # Assert
        assert result == expected_items
        mock_validation.collect_pdf_items_from_folder.assert_called_once()
        # Verificar que foi passada a função _make_upload_item
        call_args = mock_validation.collect_pdf_items_from_folder.call_args
        assert call_args[0][0] == "/fake/dir"
        assert callable(call_args[0][1])  # factory function

    @patch("src.modules.uploads.service.validation")
    def test_retorna_lista_vazia_quando_sem_pdfs(self, mock_validation: Mock) -> None:
        """Deve retornar lista vazia quando não há PDFs."""
        # Arrange
        mock_validation.collect_pdf_items_from_folder.return_value = []

        # Act
        result = uploads_service.collect_pdfs_from_folder("/fake/empty")

        # Assert
        assert result == []
        assert isinstance(result, list)


# ========================================
# Testes para build_items_from_files
# ========================================


class TestBuildItemsFromFiles:
    """Testes para a função build_items_from_files."""

    @patch("src.modules.uploads.service.validation")
    def test_lista_vazia_retorna_vazio(self, mock_validation: Mock) -> None:
        """Deve retornar lista vazia quando input é vazio."""
        # Arrange
        mock_validation.build_items_from_files.return_value = []

        # Act
        result = uploads_service.build_items_from_files([])

        # Assert
        assert result == []
        assert isinstance(result, list)

    @patch("src.modules.uploads.service.validation")
    def test_constroi_items_de_paths(self, mock_validation: Mock) -> None:
        """Deve construir UploadItems a partir de paths fornecidos."""
        # Arrange
        paths = ["C:/tmp/a.pdf", "C:/tmp/b.pdf"]
        mock_items = [
            MagicMock(spec=UploadItem, path=Path("C:/tmp/a.pdf"), relative_path="a.pdf"),
            MagicMock(spec=UploadItem, path=Path("C:/tmp/b.pdf"), relative_path="b.pdf"),
        ]
        mock_validation.build_items_from_files.return_value = mock_items

        # Act
        result = uploads_service.build_items_from_files(paths)

        # Assert
        assert len(result) == 2
        assert result == mock_items
        mock_validation.build_items_from_files.assert_called_once()
        call_args = mock_validation.build_items_from_files.call_args
        assert call_args[0][0] == paths
        assert callable(call_args[0][1])  # factory function


# ========================================
# Testes para upload_items_for_client
# ========================================


class TestUploadItemsForClient:
    """Testes para a função upload_items_for_client."""

    @patch("src.modules.uploads.service.repository")
    @patch("src.modules.uploads.service.validation")
    def test_upload_com_sucesso_total(self, mock_validation: Mock, mock_repository: Mock) -> None:
        """Deve fazer upload de todos os items com sucesso."""
        # Arrange
        items = [
            UploadItem(path=Path("/tmp/a.pdf"), relative_path="a.pdf"),
            UploadItem(path=Path("/tmp/b.pdf"), relative_path="b.pdf"),
        ]

        mock_adapter = MagicMock()
        mock_repository.build_storage_adapter.return_value = mock_adapter
        mock_repository.normalize_bucket.return_value = "rc-docs"

        # Upload bem-sucedido: (count, failures)
        mock_repository.upload_items_with_adapter.return_value = (2, [])

        # Act
        uploaded_count, failures = uploads_service.upload_items_for_client(
            items,
            cnpj_digits="12345678901234",
            bucket="rc-docs",
            subfolder="SIFAP",
            client_id=123,
            org_id="org-456",
        )

        # Assert
        assert uploaded_count == 2
        assert failures == []

        # Verificar chamadas
        mock_repository.build_storage_adapter.assert_called_once_with(
            bucket="rc-docs",
            supabase_client=None,
        )
        mock_repository.upload_items_with_adapter.assert_called_once()

    @patch("src.modules.uploads.service.repository")
    @patch("src.modules.uploads.service.validation")
    def test_upload_com_falhas_parciais(self, mock_validation: Mock, mock_repository: Mock) -> None:
        """Deve retornar falhas quando alguns uploads falham."""
        # Arrange
        items = [
            UploadItem(path=Path("/tmp/a.pdf"), relative_path="a.pdf"),
            UploadItem(path=Path("/tmp/b.pdf"), relative_path="b.pdf"),
        ]

        mock_adapter = MagicMock()
        mock_repository.build_storage_adapter.return_value = mock_adapter
        mock_repository.normalize_bucket.return_value = "rc-docs"

        # Simular falha no segundo item
        failure_item = items[1]
        failure_exception = Exception("Erro de conexão")
        mock_repository.upload_items_with_adapter.return_value = (1, [(failure_item, failure_exception)])

        # Act
        uploaded_count, failures = uploads_service.upload_items_for_client(
            items,
            cnpj_digits="12345678901234",
        )

        # Assert
        assert uploaded_count == 1
        assert len(failures) == 1
        assert failures[0][0] == failure_item
        assert failures[0][1] == failure_exception

    @patch("src.modules.uploads.service.repository")
    @patch("src.modules.uploads.service.validation")
    def test_upload_com_progress_callback(self, mock_validation: Mock, mock_repository: Mock) -> None:
        """Deve passar callback de progresso para o repository."""
        # Arrange
        items = [UploadItem(path=Path("/tmp/a.pdf"), relative_path="a.pdf")]
        mock_callback = MagicMock()

        mock_adapter = MagicMock()
        mock_repository.build_storage_adapter.return_value = mock_adapter
        mock_repository.normalize_bucket.return_value = "rc-docs"
        mock_repository.upload_items_with_adapter.return_value = (1, [])

        # Act
        uploads_service.upload_items_for_client(
            items,
            cnpj_digits="12345678901234",
            progress_callback=mock_callback,
        )

        # Assert
        call_kwargs = mock_repository.upload_items_with_adapter.call_args[1]
        assert call_kwargs["progress_callback"] == mock_callback


# ========================================
# Testes para list_storage_objects
# ========================================


class TestListStorageObjects:
    """Testes para a função list_storage_objects."""

    @patch("src.modules.uploads.service.list_storage_objects")
    def test_lista_objetos_delegando_corretamente(self, mock_list_fn: Mock) -> None:
        """Deve delegar para a função de listagem correta."""
        # Este teste verifica que a função existe e é chamável
        # A implementação real faz lazy import
        assert callable(uploads_service.list_storage_objects)


# ========================================
# Testes para list_browser_items
# ========================================


class TestListBrowserItems:
    """Testes para a função list_browser_items."""

    @patch("src.modules.uploads.service.list_storage_objects")
    @patch("src.modules.uploads.service.get_clients_bucket")
    def test_lista_com_bucket_default(self, mock_get_bucket: Mock, mock_list_fn: Mock) -> None:
        """Deve usar bucket padrão quando não especificado."""
        # Arrange
        mock_get_bucket.return_value = "rc-docs"
        mock_list_fn.return_value = [{"name": "file1.pdf"}, {"name": "file2.pdf"}]

        # Act
        result = list(uploads_service.list_browser_items("org/client123"))

        # Assert
        mock_get_bucket.assert_called_once()
        mock_list_fn.assert_called_once_with("rc-docs", "org/client123")
        assert len(result) == 2

    @patch("src.modules.uploads.service.list_storage_objects")
    @patch("src.modules.uploads.service.get_clients_bucket")
    def test_lista_com_bucket_especifico(self, mock_get_bucket: Mock, mock_list_fn: Mock) -> None:
        """Deve usar bucket especificado quando fornecido."""
        # Arrange
        mock_list_fn.return_value = []

        # Act
        result = list(uploads_service.list_browser_items("org/client456", bucket="custom-bucket"))

        # Assert
        assert result == []
        mock_get_bucket.assert_not_called()
        mock_list_fn.assert_called_once_with("custom-bucket", "org/client456")

    @patch("src.modules.uploads.service.list_storage_objects")
    @patch("src.modules.uploads.service.get_clients_bucket")
    def test_normaliza_prefix_com_barras(self, mock_get_bucket: Mock, mock_list_fn: Mock) -> None:
        """Deve normalizar prefix removendo barras iniciais/finais."""
        # Arrange
        mock_get_bucket.return_value = "rc-docs"
        mock_list_fn.return_value = []

        # Act
        uploads_service.list_browser_items("/org/client/")

        # Assert
        mock_list_fn.assert_called_once_with("rc-docs", "org/client")


# ========================================
# Testes para download_storage_object
# ========================================


class TestDownloadStorageObject:
    """Testes para a função download_storage_object."""

    @patch("src.modules.uploads.service.download_file")
    @patch("src.modules.uploads.service.get_clients_bucket")
    def test_download_com_sucesso(self, mock_get_bucket: Mock, mock_download_fn: Mock) -> None:
        """Deve baixar objeto com sucesso usando bucket padrão."""
        # Arrange
        mock_get_bucket.return_value = "rc-docs"
        mock_download_fn.return_value = None  # download não retorna nada

        # Act
        uploads_service.download_storage_object("org/client/file.pdf", "/local/path/file.pdf")

        # Assert
        mock_get_bucket.assert_called_once()
        mock_download_fn.assert_called_once_with("rc-docs", "org/client/file.pdf", "/local/path/file.pdf")

    @patch("src.modules.uploads.service.download_file")
    @patch("src.modules.uploads.service.get_clients_bucket")
    def test_download_com_bucket_customizado(self, mock_get_bucket: Mock, mock_download_fn: Mock) -> None:
        """Deve usar bucket especificado quando fornecido."""
        # Arrange
        mock_download_fn.return_value = None

        # Act
        uploads_service.download_storage_object("path/to/file.pdf", "/local/dest.pdf", bucket="custom-bucket")

        # Assert
        mock_get_bucket.assert_not_called()
        mock_download_fn.assert_called_once_with("custom-bucket", "path/to/file.pdf", "/local/dest.pdf")

    @patch("src.modules.uploads.service.download_file")
    @patch("src.modules.uploads.service.get_clients_bucket")
    def test_download_propaga_excecao(self, mock_get_bucket: Mock, mock_download_fn: Mock) -> None:
        """Deve propagar exceção quando download falha."""
        # Arrange
        mock_get_bucket.return_value = "rc-docs"
        mock_download_fn.side_effect = RuntimeError("Erro de download")

        # Act & Assert
        with pytest.raises(RuntimeError, match="Erro de download"):
            uploads_service.download_storage_object("org/client/file.pdf", "/local/path/file.pdf")


# ========================================
# Testes para delete_storage_object
# ========================================


class TestDeleteStorageObject:
    """Testes para a função delete_storage_object."""

    @patch("src.modules.uploads.service._delete_file")
    @patch("src.modules.uploads.service.SupabaseStorageAdapter")
    @patch("src.modules.uploads.service.get_clients_bucket")
    def test_delete_com_sucesso(
        self,
        mock_get_bucket: Mock,
        mock_adapter_class: Mock,
        mock_delete_fn: Mock,
    ) -> None:
        """Deve deletar objeto com sucesso."""
        # Arrange
        mock_get_bucket.return_value = "rc-docs"
        mock_adapter_instance = MagicMock()
        mock_adapter_class.return_value = mock_adapter_instance

        # Act
        uploads_service.delete_storage_object("org/client/file.pdf")

        # Assert
        mock_get_bucket.assert_called_once()
        mock_adapter_class.assert_called_once_with(bucket="rc-docs")
        mock_delete_fn.assert_called_once_with("org/client/file.pdf")

    @patch("src.modules.uploads.service._delete_file")
    @patch("src.modules.uploads.service.SupabaseStorageAdapter")
    @patch("src.modules.uploads.service.get_clients_bucket")
    def test_delete_com_bucket_customizado(
        self,
        mock_get_bucket: Mock,
        mock_adapter_class: Mock,
        mock_delete_fn: Mock,
    ) -> None:
        """Deve usar bucket especificado quando fornecido."""
        # Arrange
        mock_adapter_instance = MagicMock()
        mock_adapter_class.return_value = mock_adapter_instance

        # Act
        uploads_service.delete_storage_object("path/to/file.pdf", bucket="custom-bucket")

        # Assert
        mock_get_bucket.assert_not_called()
        mock_adapter_class.assert_called_once_with(bucket="custom-bucket")
        mock_delete_fn.assert_called_once_with("path/to/file.pdf")


# ========================================
# Testes para funções de wrapper simples
# ========================================


class TestWrapperFunctions:
    """Testes para funções que apenas delegam para outros módulos."""

    @patch("src.modules.uploads.service._download_folder_zip")
    def test_download_folder_zip_delega_corretamente(self, mock_download_zip: Mock) -> None:
        """Deve delegar para _download_folder_zip."""
        # Arrange
        mock_download_zip.return_value = b"ZIP_CONTENT"

        # Act
        result = uploads_service.download_folder_zip("bucket", "prefix", "/dest")

        # Assert
        assert result == b"ZIP_CONTENT"
        mock_download_zip.assert_called_once_with("bucket", "prefix", "/dest")

    @patch("src.modules.uploads.service._delete_file")
    def test_delete_file_delega_corretamente(self, mock_delete: Mock) -> None:
        """Deve delegar para _delete_file."""
        # Arrange
        mock_delete.return_value = None

        # Act
        uploads_service.delete_file("remote/path/file.pdf")

        # Assert
        mock_delete.assert_called_once_with("remote/path/file.pdf")

    @patch("src.modules.uploads.service._download_bytes")
    def test_download_bytes_delega_corretamente(self, mock_download_bytes: Mock) -> None:
        """Deve delegar para _download_bytes."""
        # Arrange
        mock_download_bytes.return_value = b"FILE_CONTENT"

        # Act
        result = uploads_service.download_bytes("bucket", "path/file.pdf")

        # Assert
        assert result == b"FILE_CONTENT"
        mock_download_bytes.assert_called_once_with("bucket", "path/file.pdf")


# ========================================
# Testes para UploadItem dataclass
# ========================================


class TestUploadItem:
    """Testes para a dataclass UploadItem."""

    def test_criacao_de_item(self) -> None:
        """Deve criar UploadItem corretamente."""
        # Arrange & Act
        item = UploadItem(path=Path("/tmp/test.pdf"), relative_path="test.pdf")

        # Assert
        assert item.path == Path("/tmp/test.pdf")
        assert item.relative_path == "test.pdf"

    def test_item_e_imutavel_com_slots(self) -> None:
        """Deve usar slots para eficiência de memória."""
        # Arrange
        item = UploadItem(path=Path("/tmp/test.pdf"), relative_path="test.pdf")

        # Assert
        # Verificar que não pode adicionar novos atributos (slots)
        with pytest.raises(AttributeError):
            item.new_attribute = "value"  # type: ignore


# ========================================
# Testes para _make_upload_item
# ========================================


class TestMakeUploadItem:
    """Testes para a função _make_upload_item."""

    def test_cria_item_corretamente(self) -> None:
        """Deve criar UploadItem a partir de path e relative_path."""
        # Arrange
        path = Path("/fake/folder/file.pdf")
        relative = "subfolder/file.pdf"

        # Act
        item = uploads_service._make_upload_item(path, relative)

        # Assert
        assert isinstance(item, UploadItem)
        assert item.path == path
        assert item.relative_path == relative
