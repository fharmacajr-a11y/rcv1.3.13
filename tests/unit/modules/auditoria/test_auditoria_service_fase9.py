"""
Testes para src/modules/auditoria/service.py (TEST-001 Fase 9).

Cobertura:
- CRUD auditorias (fetch, start, update, delete)
- Storage operations (org_id, folders, uploads, removals)
- Pipeline de upload (contextos, planos, duplicatas)
- Error handling (offline, empty responses, exceptions)
"""

from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

import pytest

from src.modules.auditoria.service import (
    AuditoriaOfflineError,
    AuditoriaServiceError,
    AuditoriaStorageContext,
    AuditoriaUploadContext,
    delete_auditorias,
    ensure_auditoria_folder,
    ensure_storage_ready,
    fetch_auditorias,
    fetch_clients,
    get_current_org_id,
    get_storage_context,
    is_online,
    list_existing_file_names,
    prepare_upload_context,
    remove_storage_objects,
    reset_org_cache,
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
    sb.in_ = MagicMock(return_value=sb)
    sb.execute = MagicMock(return_value=sb)
    sb.storage = MagicMock()
    return sb


@pytest.fixture(autouse=True)
def reset_cache():
    """Limpa cache de org_id antes de cada teste."""
    reset_org_cache()
    yield
    reset_org_cache()


# --- Testes: is_online / offline ---


def test_is_online_when_supabase_available():
    """is_online() retorna True quando Supabase está disponível."""
    with patch("src.modules.auditoria.service.get_supabase", return_value=MagicMock()):
        assert is_online() is True


def test_is_online_when_supabase_unavailable():
    """is_online() retorna False quando Supabase não está disponível."""
    with patch("src.modules.auditoria.service.get_supabase", return_value=None):
        assert is_online() is False


def test_is_online_when_supabase_raises_exception():
    """is_online() retorna False quando get_supabase lança exceção."""
    with patch("src.modules.auditoria.service.get_supabase", side_effect=RuntimeError("Connection failed")):
        assert is_online() is False


# --- Testes: fetch_clients ---


def test_fetch_clients_success(mock_supabase):
    """fetch_clients() retorna lista de clientes."""
    mock_supabase.data = [{"id": 1, "name": "Cliente A"}, {"id": 2, "name": "Cliente B"}]
    with (
        patch("src.modules.auditoria.service.get_supabase", return_value=mock_supabase),
        patch("src.modules.auditoria.service.repository.fetch_clients", return_value=mock_supabase.data),
    ):
        result = fetch_clients()
        assert len(result) == 2
        assert result[0]["name"] == "Cliente A"


def test_fetch_clients_offline():
    """fetch_clients() lança AuditoriaOfflineError quando Supabase offline."""
    with patch("src.modules.auditoria.service.get_supabase", return_value=None):
        with pytest.raises(AuditoriaOfflineError, match="Supabase client is not available"):
            fetch_clients()


def test_fetch_clients_exception_wrapped(mock_supabase):
    """fetch_clients() wrapa exceções do repository em AuditoriaServiceError."""
    with (
        patch("src.modules.auditoria.service.get_supabase", return_value=mock_supabase),
        patch("src.modules.auditoria.service.repository.fetch_clients", side_effect=RuntimeError("DB error")),
    ):
        with pytest.raises(AuditoriaServiceError, match="Falha ao carregar clientes"):
            fetch_clients()


# --- Testes: fetch_auditorias ---


def test_fetch_auditorias_success(mock_supabase):
    """fetch_auditorias() retorna lista de auditorias."""
    mock_supabase.data = [{"id": "a1", "cliente_id": 1, "status": "em_andamento"}]
    with (
        patch("src.modules.auditoria.service.get_supabase", return_value=mock_supabase),
        patch("src.modules.auditoria.service.repository.fetch_auditorias", return_value=mock_supabase.data),
    ):
        result = fetch_auditorias()
        assert len(result) == 1
        assert result[0]["status"] == "em_andamento"


def test_fetch_auditorias_empty_list(mock_supabase):
    """fetch_auditorias() retorna lista vazia quando não há auditorias."""
    with (
        patch("src.modules.auditoria.service.get_supabase", return_value=mock_supabase),
        patch("src.modules.auditoria.service.repository.fetch_auditorias", return_value=[]),
    ):
        result = fetch_auditorias()
        assert result == []


# --- Testes: start_auditoria ---


def test_start_auditoria_success(mock_supabase):
    """start_auditoria() cria nova auditoria com sucesso."""
    mock_response = Mock()
    mock_response.data = [{"id": "new-audit", "cliente_id": 123, "status": "em_andamento"}]
    with (
        patch("src.modules.auditoria.service.get_supabase", return_value=mock_supabase),
        patch("src.modules.auditoria.service.repository.insert_auditoria", return_value=mock_response),
    ):
        result = start_auditoria(cliente_id=123)
        assert result["id"] == "new-audit"
        assert result["status"] == "em_andamento"


def test_start_auditoria_custom_status(mock_supabase):
    """start_auditoria() aceita status customizado."""
    mock_response = Mock()
    mock_response.data = [{"id": "audit-2", "cliente_id": 456, "status": "concluida"}]
    with (
        patch("src.modules.auditoria.service.get_supabase", return_value=mock_supabase),
        patch("src.modules.auditoria.service.repository.insert_auditoria", return_value=mock_response),
    ):
        result = start_auditoria(cliente_id=456, status="concluida")
        assert result["status"] == "concluida"


def test_start_auditoria_empty_response_raises_error(mock_supabase):
    """start_auditoria() lança erro quando Supabase retorna lista vazia."""
    mock_response = Mock()
    mock_response.data = []
    with (
        patch("src.modules.auditoria.service.get_supabase", return_value=mock_supabase),
        patch("src.modules.auditoria.service.repository.insert_auditoria", return_value=mock_response),
    ):
        with pytest.raises(AuditoriaServiceError, match="Supabase nao retornou dados"):
            start_auditoria(cliente_id=999)


def test_start_auditoria_no_data_attribute(mock_supabase):
    """start_auditoria() lança erro quando response não tem atributo data."""
    mock_response = Mock(spec=[])  # sem atributo data
    with (
        patch("src.modules.auditoria.service.get_supabase", return_value=mock_supabase),
        patch("src.modules.auditoria.service.repository.insert_auditoria", return_value=mock_response),
    ):
        with pytest.raises(AuditoriaServiceError, match="Supabase nao retornou dados"):
            start_auditoria(cliente_id=888)


# --- Testes: update_auditoria_status ---


def test_update_auditoria_status_success(mock_supabase):
    """update_auditoria_status() atualiza status corretamente."""
    mock_response = Mock()
    mock_response.data = [{"id": "audit-x", "status": "concluida"}]
    with (
        patch("src.modules.auditoria.service.get_supabase", return_value=mock_supabase),
        patch("src.modules.auditoria.service.repository.update_auditoria", return_value=mock_response),
    ):
        result = update_auditoria_status(auditoria_id="audit-x", status="concluida")
        assert result["status"] == "concluida"


def test_update_auditoria_status_not_found(mock_supabase):
    """update_auditoria_status() lança erro quando auditoria não encontrada."""
    mock_response = Mock()
    mock_response.data = []
    with (
        patch("src.modules.auditoria.service.get_supabase", return_value=mock_supabase),
        patch("src.modules.auditoria.service.repository.update_auditoria", return_value=mock_response),
    ):
        with pytest.raises(AuditoriaServiceError, match="Auditoria nao encontrada"):
            update_auditoria_status(auditoria_id="nonexistent", status="cancelada")


# --- Testes: delete_auditorias ---


def test_delete_auditorias_success(mock_supabase):
    """delete_auditorias() exclui múltiplas auditorias."""
    with (
        patch("src.modules.auditoria.service.get_supabase", return_value=mock_supabase),
        patch("src.modules.auditoria.service.repository.delete_auditorias") as mock_delete,
    ):
        delete_auditorias(["id1", "id2", "id3"])
        mock_delete.assert_called_once()
        call_args = mock_delete.call_args[0]
        assert "id1" in call_args[1]
        assert "id2" in call_args[1]
        assert "id3" in call_args[1]


def test_delete_auditorias_mixed_types(mock_supabase):
    """delete_auditorias() aceita mixed types (int, str) e filtra None."""
    with (
        patch("src.modules.auditoria.service.get_supabase", return_value=mock_supabase),
        patch("src.modules.auditoria.service.repository.delete_auditorias") as mock_delete,
    ):
        delete_auditorias([123, "abc", None, "", "  ", 456])
        call_args = mock_delete.call_args[0]
        ids = call_args[1]
        assert "123" in ids
        assert "abc" in ids
        assert "456" in ids
        assert len(ids) == 3  # None e strings vazias filtradas


def test_delete_auditorias_empty_list(mock_supabase):
    """delete_auditorias() com lista vazia não chama repository."""
    with (
        patch("src.modules.auditoria.service.get_supabase", return_value=mock_supabase),
        patch("src.modules.auditoria.service.repository.delete_auditorias") as mock_delete,
    ):
        delete_auditorias([])
        mock_delete.assert_not_called()


def test_delete_auditorias_only_none_and_empty(mock_supabase):
    """delete_auditorias() com apenas None e vazios não chama repository."""
    with (
        patch("src.modules.auditoria.service.get_supabase", return_value=mock_supabase),
        patch("src.modules.auditoria.service.repository.delete_auditorias") as mock_delete,
    ):
        delete_auditorias([None, "", "  ", None])
        mock_delete.assert_not_called()


# --- Testes: get_current_org_id ---


def test_get_current_org_id_success(mock_supabase):
    """get_current_org_id() busca org_id e cacheia."""
    with (
        patch("src.modules.auditoria.service.get_supabase", return_value=mock_supabase),
        patch("src.modules.auditoria.service.repository.fetch_current_user_id", return_value="user-123"),
        patch("src.modules.auditoria.service.repository.fetch_org_id_for_user", return_value="org-abc"),
    ):
        org_id = get_current_org_id()
        assert org_id == "org-abc"
        # Segunda chamada usa cache
        org_id_cached = get_current_org_id()
        assert org_id_cached == "org-abc"


def test_get_current_org_id_force_refresh(mock_supabase):
    """get_current_org_id(force_refresh=True) invalida cache."""
    with (
        patch("src.modules.auditoria.service.get_supabase", return_value=mock_supabase),
        patch("src.modules.auditoria.service.repository.fetch_current_user_id", return_value="user-456"),
        patch("src.modules.auditoria.service.repository.fetch_org_id_for_user", return_value="org-xyz"),
    ):
        org_id1 = get_current_org_id()
        assert org_id1 == "org-xyz"
        # Force refresh
        org_id2 = get_current_org_id(force_refresh=True)
        assert org_id2 == "org-xyz"


def test_get_current_org_id_lookup_error(mock_supabase):
    """get_current_org_id() wrapa LookupError em AuditoriaServiceError."""
    with (
        patch("src.modules.auditoria.service.get_supabase", return_value=mock_supabase),
        patch(
            "src.modules.auditoria.service.repository.fetch_current_user_id", side_effect=LookupError("User not found")
        ),
    ):
        with pytest.raises(AuditoriaServiceError, match="User not found"):
            get_current_org_id()


# --- Testes: ensure_auditoria_folder ---


def test_ensure_auditoria_folder_success(mock_supabase):
    """ensure_auditoria_folder() cria pasta AUDITORIA com sucesso."""
    with (
        patch("src.modules.auditoria.service.get_supabase", return_value=mock_supabase),
        patch("src.modules.auditoria.service.get_current_org_id", return_value="org-123"),
        patch("src.modules.auditoria.service.storage.make_storage_context") as mock_ctx,
        patch("src.modules.auditoria.service.storage.ensure_auditoria_folder") as mock_ensure,
    ):
        mock_ctx.return_value = AuditoriaStorageContext(
            bucket="clients",
            org_id="org-123",
            client_root="org-123/456",
            auditoria_prefix="org-123/456/GERAL/Auditoria",
        )
        ensure_auditoria_folder(client_id=456)
        mock_ensure.assert_called_once()


def test_ensure_auditoria_folder_custom_org_id(mock_supabase):
    """ensure_auditoria_folder() aceita org_id customizado."""
    with (
        patch("src.modules.auditoria.service.get_supabase", return_value=mock_supabase),
        patch("src.modules.auditoria.service.storage.make_storage_context") as mock_ctx,
        patch("src.modules.auditoria.service.storage.ensure_auditoria_folder") as mock_ensure,
    ):
        mock_ctx.return_value = AuditoriaStorageContext(
            bucket="clients",
            org_id="custom-org",
            client_root="custom-org/789",
            auditoria_prefix="custom-org/789/GERAL/Auditoria",
        )
        ensure_auditoria_folder(client_id=789, org_id="custom-org")
        mock_ensure.assert_called_once()


# --- Testes: list_existing_file_names ---


def test_list_existing_file_names_success(mock_supabase):
    """list_existing_file_names() lista arquivos existentes."""
    with (
        patch("src.modules.auditoria.service.get_supabase", return_value=mock_supabase),
        patch(
            "src.modules.auditoria.service.storage.list_existing_file_names", return_value={"file1.pdf", "file2.zip"}
        ),
    ):
        result = list_existing_file_names(bucket="clients", prefix="org-123/456/AUDITORIA")
        assert result == {"file1.pdf", "file2.zip"}


def test_list_existing_file_names_empty(mock_supabase):
    """list_existing_file_names() retorna set vazio quando pasta vazia."""
    with (
        patch("src.modules.auditoria.service.get_supabase", return_value=mock_supabase),
        patch("src.modules.auditoria.service.storage.list_existing_file_names", return_value=set()),
    ):
        result = list_existing_file_names(bucket="clients", prefix="org-123/empty")
        assert result == set()


# --- Testes: upload_storage_bytes ---


def test_upload_storage_bytes_success(mock_supabase):
    """upload_storage_bytes() envia bytes para storage."""
    with (
        patch("src.modules.auditoria.service.get_supabase", return_value=mock_supabase),
        patch("src.modules.auditoria.service.storage.upload_storage_bytes") as mock_upload,
    ):
        upload_storage_bytes(
            bucket="clients", dest_path="org/file.pdf", data=b"PDF content", content_type="application/pdf"
        )
        mock_upload.assert_called_once()


def test_upload_storage_bytes_with_upsert(mock_supabase):
    """upload_storage_bytes() aceita upsert=True."""
    with (
        patch("src.modules.auditoria.service.get_supabase", return_value=mock_supabase),
        patch("src.modules.auditoria.service.storage.upload_storage_bytes") as mock_upload,
    ):
        upload_storage_bytes(
            bucket="clients", dest_path="org/file.pdf", data=b"content", content_type="application/pdf", upsert=True
        )
        call_kwargs = mock_upload.call_args[1]
        assert call_kwargs["upsert"] is True


# --- Testes: remove_storage_objects ---


def test_remove_storage_objects_success(mock_supabase):
    """remove_storage_objects() remove múltiplos arquivos."""
    with (
        patch("src.modules.auditoria.service.get_supabase", return_value=mock_supabase),
        patch("src.modules.auditoria.service.storage.remove_storage_objects") as mock_remove,
    ):
        remove_storage_objects(bucket="clients", paths=["path1", "path2"])
        mock_remove.assert_called_once()


def test_remove_storage_objects_empty_list(mock_supabase):
    """remove_storage_objects() com lista vazia não chama storage."""
    with (
        patch("src.modules.auditoria.service.get_supabase", return_value=mock_supabase),
        patch("src.modules.auditoria.service.storage.remove_storage_objects") as mock_remove,
    ):
        remove_storage_objects(bucket="clients", paths=[])
        mock_remove.assert_not_called()


# --- Testes: ensure_storage_ready ---


def test_ensure_storage_ready_success():
    """ensure_storage_ready() valida Supabase online."""
    with (
        patch("src.modules.auditoria.service.is_online", return_value=True),
        patch("src.modules.auditoria.service.get_clients_bucket", return_value="clients"),
    ):
        ensure_storage_ready()  # Não deve lançar exceção


def test_ensure_storage_ready_offline():
    """ensure_storage_ready() lança erro quando Supabase offline."""
    with patch("src.modules.auditoria.service.is_online", return_value=False):
        with pytest.raises(AuditoriaOfflineError, match="Supabase client is not available"):
            ensure_storage_ready()


def test_ensure_storage_ready_no_bucket():
    """ensure_storage_ready() lança erro quando bucket não configurado."""
    with (
        patch("src.modules.auditoria.service.is_online", return_value=True),
        patch("src.modules.auditoria.service.get_clients_bucket", return_value=""),
    ):
        with pytest.raises(AuditoriaServiceError, match="Defina RC_STORAGE_BUCKET_CLIENTS"):
            ensure_storage_ready()


# --- Testes: prepare_upload_context ---


def test_prepare_upload_context_success():
    """prepare_upload_context() cria contexto de upload."""
    with patch("src.modules.auditoria.service.get_storage_context") as mock_get_ctx:
        mock_get_ctx.return_value = AuditoriaStorageContext(
            bucket="clients",
            org_id="org-123",
            client_root="org-123/456",
            auditoria_prefix="org-123/456/GERAL/Auditoria",
        )
        ctx = prepare_upload_context(client_id=456)
        assert isinstance(ctx, AuditoriaUploadContext)
        assert ctx.bucket == "clients"
        assert ctx.base_prefix == "org-123/456/GERAL/Auditoria"
        assert ctx.client_id == 456


def test_prepare_upload_context_custom_org_id():
    """prepare_upload_context() aceita org_id customizado."""
    with patch("src.modules.auditoria.service.get_storage_context") as mock_get_ctx:
        mock_get_ctx.return_value = AuditoriaStorageContext(
            bucket="clients",
            org_id="custom-org",
            client_root="custom-org/789",
            auditoria_prefix="custom-org/789/GERAL/Auditoria",
        )
        ctx = prepare_upload_context(client_id=789, org_id="custom-org")
        assert ctx.org_id == "custom-org"


# --- Testes: get_storage_context ---


def test_get_storage_context_uses_current_org_id():
    """get_storage_context() usa get_current_org_id() quando org_id não fornecido."""
    with (
        patch("src.modules.auditoria.service.get_current_org_id", return_value="auto-org"),
        patch("src.modules.auditoria.service.storage.make_storage_context") as mock_make,
    ):
        mock_make.return_value = AuditoriaStorageContext(
            bucket="clients",
            org_id="auto-org",
            client_root="auto-org/100",
            auditoria_prefix="auto-org/100/GERAL/Auditoria",
        )
        ctx = get_storage_context(client_id=100)
        assert ctx.org_id == "auto-org"
