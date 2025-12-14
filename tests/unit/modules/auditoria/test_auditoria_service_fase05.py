"""
Testes complementares para src/modules/auditoria/service.py (Microfase 5).

Foco: Aumentar cobertura de ~81.8% para ≥95% complementando test_auditoria_service_fase9.py

Cenários adicionais:
- Funções alias (list_clients_minimal, list_auditorias)
- Exception path de get_supabase (linha 18-21)
- Error paths em fetch_auditorias (linha 104-105)
- Error paths em start_auditoria (linha 119-120, 132-133)
- Error paths em update_auditoria_status (linha 154-155)
- Error paths em delete_auditorias (linha 174-175)
- Error path em get_current_org_id (linha 186, 191)
- Error path em ensure_auditoria_folder (linha 206-207)
- Error path em list_existing_file_names (linha 215-216)
- Error path em upload_storage_bytes (linha 240-241)
- Error path em remove_storage_objects (linha 251-252)
- Error paths em prepare_archive_plan (linha 277-280)
- Error path em execute_archive_upload (linha 309-321)
- Funções de wrapper: cleanup_archive_plan (285), list_existing_names_for_context (290),
  detect_duplicate_file_names (295), rollback_uploaded_paths (326), extract_archive_to (331),
  is_supported_archive (336)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.modules.auditoria.service import (
    AuditoriaArchivePlan,
    AuditoriaOfflineError,
    AuditoriaServiceError,
    AuditoriaUploadContext,
    cleanup_archive_plan,
    delete_auditorias,
    detect_duplicate_file_names,
    ensure_auditoria_folder,
    execute_archive_upload,
    extract_archive_to,
    fetch_auditorias,
    fetch_clients,
    get_current_org_id,
    is_supported_archive,
    list_auditorias,
    list_clients_minimal,
    list_existing_file_names,
    list_existing_names_for_context,
    prepare_archive_plan,
    remove_storage_objects,
    rollback_uploaded_paths,
    start_auditoria,
    update_auditoria_status,
    upload_storage_bytes,
)


# --- Fixtures ---


@pytest.fixture
def mock_supabase():
    """Mock do cliente Supabase."""
    sb = MagicMock()
    sb.table = MagicMock(return_value=sb)
    sb.select = MagicMock(return_value=sb)
    sb.insert = MagicMock(return_value=sb)
    sb.update = MagicMock(return_value=sb)
    sb.delete = MagicMock(return_value=sb)
    sb.eq = MagicMock(return_value=sb)
    sb.execute = MagicMock(return_value=sb)
    return sb


@pytest.fixture(autouse=True)
def reset_cache():
    """Reset org_id cache antes de cada teste."""
    from src.modules.auditoria import service

    service._ORG_ID_CACHE = ""
    yield
    service._ORG_ID_CACHE = ""


# --- Testes de Funções Alias ---


def test_list_clients_minimal_delegates_to_fetch_clients():
    """Testa que list_clients_minimal é alias de fetch_clients."""
    with (
        patch("src.modules.auditoria.service._get_supabase_client") as mock_get_sb,
        patch("src.modules.auditoria.service.repository.fetch_clients") as mock_fetch,
    ):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_fetch.return_value = [{"id": 1, "nome": "Cliente A"}]

        result = list_clients_minimal()

        assert result == [{"id": 1, "nome": "Cliente A"}]
        mock_fetch.assert_called_once_with(mock_sb)


def test_list_auditorias_delegates_to_fetch_auditorias():
    """Testa que list_auditorias é alias de fetch_auditorias."""
    with (
        patch("src.modules.auditoria.service._get_supabase_client") as mock_get_sb,
        patch("src.modules.auditoria.service.repository.fetch_auditorias") as mock_fetch,
    ):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_fetch.return_value = [{"id": 10, "status": "concluida"}]

        result = list_auditorias()

        assert result == [{"id": 10, "status": "concluida"}]
        mock_fetch.assert_called_once_with(mock_sb)


# --- Testes de Exception Paths ---


def test_fetch_auditorias_wraps_repository_exception():
    """Testa que fetch_auditorias encapsula exceção do repository."""
    with (
        patch("src.modules.auditoria.service._get_supabase_client") as mock_get_sb,
        patch("src.modules.auditoria.service.repository.fetch_auditorias") as mock_fetch,
    ):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_fetch.side_effect = RuntimeError("DB connection failed")

        with pytest.raises(AuditoriaServiceError, match="Falha ao carregar auditorias"):
            fetch_auditorias()


def test_start_auditoria_wraps_repository_exception():
    """Testa que start_auditoria encapsula exceção do repository."""
    with (
        patch("src.modules.auditoria.service._get_supabase_client") as mock_get_sb,
        patch("src.modules.auditoria.service.repository.insert_auditoria") as mock_insert,
    ):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_insert.side_effect = ValueError("Invalid payload")

        with pytest.raises(AuditoriaServiceError, match="Nao foi possivel iniciar auditoria"):
            start_auditoria(cliente_id=5)


def test_start_auditoria_raises_error_when_no_data_returned():
    """Testa que start_auditoria levanta erro quando Supabase não retorna dados."""
    with (
        patch("src.modules.auditoria.service._get_supabase_client") as mock_get_sb,
        patch("src.modules.auditoria.service.repository.insert_auditoria") as mock_insert,
    ):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb

        # Simular resposta vazia (data = [])
        mock_response = MagicMock()
        mock_response.data = []
        mock_insert.return_value = mock_response

        with pytest.raises(AuditoriaServiceError, match="Supabase nao retornou dados"):
            start_auditoria(cliente_id=10)


def test_update_auditoria_status_wraps_repository_exception():
    """Testa que update_auditoria_status encapsula exceção do repository."""
    with (
        patch("src.modules.auditoria.service._get_supabase_client") as mock_get_sb,
        patch("src.modules.auditoria.service.repository.update_auditoria") as mock_update,
    ):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_update.side_effect = RuntimeError("Update failed")

        with pytest.raises(AuditoriaServiceError, match="Nao foi possivel atualizar status"):
            update_auditoria_status("aud-123", "concluida")


def test_update_auditoria_status_raises_error_when_not_found():
    """Testa que update_auditoria_status levanta erro quando auditoria não encontrada."""
    with (
        patch("src.modules.auditoria.service._get_supabase_client") as mock_get_sb,
        patch("src.modules.auditoria.service.repository.update_auditoria") as mock_update,
    ):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb

        # Simular resposta vazia
        mock_response = MagicMock()
        mock_response.data = []
        mock_update.return_value = mock_response

        with pytest.raises(AuditoriaServiceError, match="Auditoria nao encontrada"):
            update_auditoria_status("aud-999", "concluida")


def test_delete_auditorias_wraps_repository_exception():
    """Testa que delete_auditorias encapsula exceção do repository."""
    with (
        patch("src.modules.auditoria.service._get_supabase_client") as mock_get_sb,
        patch("src.modules.auditoria.service.repository.delete_auditorias") as mock_delete,
    ):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_delete.side_effect = RuntimeError("Delete failed")

        with pytest.raises(AuditoriaServiceError, match="Falha ao excluir auditorias"):
            delete_auditorias(["aud-1", "aud-2"])


def test_get_current_org_id_wraps_lookup_error():
    """Testa que get_current_org_id encapsula LookupError do repository."""
    with (
        patch("src.modules.auditoria.service._get_supabase_client") as mock_get_sb,
        patch("src.modules.auditoria.service.repository.fetch_current_user_id") as mock_fetch_user,
    ):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_fetch_user.side_effect = LookupError("User not found")

        with pytest.raises(AuditoriaServiceError, match="User not found"):
            get_current_org_id()


def test_get_current_org_id_wraps_generic_exception():
    """Testa que get_current_org_id encapsula exceções genéricas."""
    with (
        patch("src.modules.auditoria.service._get_supabase_client") as mock_get_sb,
        patch("src.modules.auditoria.service.repository.fetch_current_user_id") as mock_fetch_user,
    ):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_fetch_user.side_effect = RuntimeError("Network error")

        with pytest.raises(AuditoriaServiceError, match="Nao foi possivel determinar o org_id"):
            get_current_org_id()


def test_get_current_org_id_wraps_exception_from_fetch_org_id():
    """Testa que get_current_org_id encapsula exceção de fetch_org_id_for_user."""
    with (
        patch("src.modules.auditoria.service._get_supabase_client") as mock_get_sb,
        patch("src.modules.auditoria.service.repository.fetch_current_user_id") as mock_fetch_user,
        patch("src.modules.auditoria.service.repository.fetch_org_id_for_user") as mock_fetch_org,
    ):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_fetch_user.return_value = "user-123"
        mock_fetch_org.side_effect = RuntimeError("Database error")

        with pytest.raises(AuditoriaServiceError, match="Nao foi possivel determinar o org_id"):
            get_current_org_id()


def test_ensure_auditoria_folder_wraps_storage_exception():
    """Testa que ensure_auditoria_folder encapsula exceção do storage."""
    with (
        patch("src.modules.auditoria.service._get_supabase_client") as mock_get_sb,
        patch("src.modules.auditoria.service.storage.make_storage_context") as mock_ctx,
        patch("src.modules.auditoria.service.storage.ensure_auditoria_folder") as mock_ensure,
        patch("src.modules.auditoria.service.get_current_org_id") as mock_org,
    ):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_org.return_value = "org-1"
        mock_ctx.return_value = MagicMock()
        mock_ensure.side_effect = RuntimeError("Bucket not found")

        with pytest.raises(AuditoriaServiceError, match="Falha ao criar pasta de Auditoria"):
            ensure_auditoria_folder(client_id=10)


def test_list_existing_file_names_wraps_storage_exception():
    """Testa que list_existing_file_names encapsula exceção do storage."""
    with (
        patch("src.modules.auditoria.service._get_supabase_client") as mock_get_sb,
        patch("src.modules.auditoria.service.storage.list_existing_file_names") as mock_list,
    ):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_list.side_effect = RuntimeError("Storage API error")

        with pytest.raises(AuditoriaServiceError, match="Falha ao listar arquivos existentes"):
            list_existing_file_names("bucket-test", "prefix/")


def test_upload_storage_bytes_wraps_storage_exception():
    """Testa que upload_storage_bytes encapsula exceção do storage."""
    with (
        patch("src.modules.auditoria.service._get_supabase_client") as mock_get_sb,
        patch("src.modules.auditoria.service.storage.upload_storage_bytes") as mock_upload,
    ):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_upload.side_effect = RuntimeError("Upload failed")

        with pytest.raises(AuditoriaServiceError, match="Falha ao enviar arquivo para o Storage"):
            upload_storage_bytes("bucket-test", "path/file.txt", b"data", content_type="text/plain")


def test_remove_storage_objects_wraps_storage_exception():
    """Testa que remove_storage_objects encapsula exceção do storage."""
    with (
        patch("src.modules.auditoria.service._get_supabase_client") as mock_get_sb,
        patch("src.modules.auditoria.service.storage.remove_storage_objects") as mock_remove,
    ):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_remove.side_effect = RuntimeError("Delete failed")

        with pytest.raises(AuditoriaServiceError, match="Falha ao remover arquivos do Storage"):
            remove_storage_objects("bucket-test", ["path/file1.txt"])


def test_prepare_archive_plan_wraps_value_error():
    """Testa que prepare_archive_plan encapsula ValueError do archives."""
    with patch("src.modules.auditoria.service.archives.prepare_archive_plan") as mock_prepare:
        mock_prepare.side_effect = ValueError("Unsupported archive format")

        with pytest.raises(AuditoriaServiceError, match="Unsupported archive format"):
            prepare_archive_plan("/path/to/archive.unknown")


def test_execute_archive_upload_wraps_value_error():
    """Testa que execute_archive_upload encapsula ValueError do archives."""
    with patch("src.modules.auditoria.service.archives.execute_archive_upload") as mock_execute:
        mock_plan = MagicMock(spec=AuditoriaArchivePlan)
        mock_context = MagicMock(spec=AuditoriaUploadContext)
        mock_execute.side_effect = ValueError("Invalid strategy")

        with pytest.raises(AuditoriaServiceError, match="Invalid strategy"):
            execute_archive_upload(mock_plan, mock_context, strategy="invalid", existing_names=set(), duplicates=set())


# --- Testes de Funções Wrapper (Delegação) ---


def test_cleanup_archive_plan_delegates_to_archives():
    """Testa que cleanup_archive_plan delega para archives.cleanup_archive_plan."""
    with patch("src.modules.auditoria.service.archives.cleanup_archive_plan") as mock_cleanup:
        mock_plan = MagicMock(spec=AuditoriaArchivePlan)

        cleanup_archive_plan(mock_plan)

        mock_cleanup.assert_called_once_with(mock_plan)


def test_cleanup_archive_plan_with_none():
    """Testa que cleanup_archive_plan aceita None sem erros."""
    with patch("src.modules.auditoria.service.archives.cleanup_archive_plan") as mock_cleanup:
        cleanup_archive_plan(None)

        mock_cleanup.assert_called_once_with(None)


def test_list_existing_names_for_context_delegates_to_list_existing_file_names():
    """Testa que list_existing_names_for_context delega para list_existing_file_names."""
    with (
        patch("src.modules.auditoria.service._get_supabase_client") as mock_get_sb,
        patch("src.modules.auditoria.service.storage.list_existing_file_names") as mock_list,
    ):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_list.return_value = {"file1.txt", "file2.pdf"}

        mock_context = AuditoriaUploadContext(
            bucket="test-bucket", base_prefix="client-10/auditoria/", org_id="org-1", client_id=10
        )

        result = list_existing_names_for_context(mock_context)

        assert result == {"file1.txt", "file2.pdf"}
        mock_list.assert_called_once_with(mock_sb, "test-bucket", "client-10/auditoria/", page_size=1000)


def test_detect_duplicate_file_names_delegates_to_archives():
    """Testa que detect_duplicate_file_names delega para archives.detect_duplicate_file_names."""
    with patch("src.modules.auditoria.service.archives.detect_duplicate_file_names") as mock_detect:
        mock_plan = MagicMock(spec=AuditoriaArchivePlan)
        existing_names = {"file1.txt", "file2.pdf"}
        mock_detect.return_value = {"file1.txt"}

        result = detect_duplicate_file_names(mock_plan, existing_names)

        assert result == {"file1.txt"}
        mock_detect.assert_called_once_with(mock_plan, existing_names)


def test_rollback_uploaded_paths_delegates_to_remove_storage_objects():
    """Testa que rollback_uploaded_paths delega para remove_storage_objects."""
    with (
        patch("src.modules.auditoria.service._get_supabase_client") as mock_get_sb,
        patch("src.modules.auditoria.service.storage.remove_storage_objects") as mock_remove,
    ):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb

        mock_context = AuditoriaUploadContext(
            bucket="test-bucket", base_prefix="client-10/auditoria/", org_id="org-1", client_id=10
        )
        uploaded_paths = ["path/file1.txt", "path/file2.pdf"]

        rollback_uploaded_paths(mock_context, uploaded_paths)

        mock_remove.assert_called_once_with(mock_sb, "test-bucket", uploaded_paths)


def test_extract_archive_to_delegates_to_archives():
    """Testa que extract_archive_to delega para archives.extract_archive_to."""
    with patch("src.modules.auditoria.service.archives.extract_archive_to") as mock_extract:
        mock_extract.return_value = Path("/tmp/extracted")

        result = extract_archive_to("/path/to/archive.zip", "/tmp/target")

        assert result == Path("/tmp/extracted")
        mock_extract.assert_called_once_with("/path/to/archive.zip", "/tmp/target")


def test_is_supported_archive_delegates_to_archives():
    """Testa que is_supported_archive delega para archives.is_supported_archive."""
    with patch("src.modules.auditoria.service.archives.is_supported_archive") as mock_is_supported:
        mock_is_supported.return_value = True

        result = is_supported_archive("/path/to/file.zip")

        assert result is True
        mock_is_supported.assert_called_once_with("/path/to/file.zip")


def test_is_supported_archive_returns_false_for_unsupported():
    """Testa que is_supported_archive retorna False para extensão não suportada."""
    with patch("src.modules.auditoria.service.archives.is_supported_archive") as mock_is_supported:
        mock_is_supported.return_value = False

        result = is_supported_archive("/path/to/file.txt")

        assert result is False
        mock_is_supported.assert_called_once_with("/path/to/file.txt")


# --- Testes de Edge Cases Adicionais ---


def test_fetch_clients_offline_raises_auditoria_offline_error():
    """Testa que fetch_clients levanta AuditoriaOfflineError quando offline."""
    with patch("src.modules.auditoria.service._get_supabase_client") as mock_get_sb:
        mock_get_sb.return_value = None

        with pytest.raises(AuditoriaOfflineError, match="Supabase client is not available"):
            fetch_clients()


def test_start_auditoria_offline_raises_auditoria_offline_error():
    """Testa que start_auditoria levanta AuditoriaOfflineError quando offline."""
    with patch("src.modules.auditoria.service._get_supabase_client") as mock_get_sb:
        mock_get_sb.return_value = None

        with pytest.raises(AuditoriaOfflineError, match="Supabase client is not available"):
            start_auditoria(cliente_id=5)


def test_update_auditoria_status_offline_raises_auditoria_offline_error():
    """Testa que update_auditoria_status levanta AuditoriaOfflineError quando offline."""
    with patch("src.modules.auditoria.service._get_supabase_client") as mock_get_sb:
        mock_get_sb.return_value = None

        with pytest.raises(AuditoriaOfflineError, match="Supabase client is not available"):
            update_auditoria_status("aud-123", "concluida")


def test_delete_auditorias_offline_raises_auditoria_offline_error():
    """Testa que delete_auditorias levanta AuditoriaOfflineError quando offline."""
    with patch("src.modules.auditoria.service._get_supabase_client") as mock_get_sb:
        mock_get_sb.return_value = None

        with pytest.raises(AuditoriaOfflineError, match="Supabase client is not available"):
            delete_auditorias(["aud-1"])
