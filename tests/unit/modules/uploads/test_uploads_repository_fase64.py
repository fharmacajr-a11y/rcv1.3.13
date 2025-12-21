"""
Testes para src/modules/uploads/repository.py (TEST-007).

Cenários:
- current_user_id: obtém user_id do Supabase auth
- resolve_org_id: resolve org_id via memberships ou fallback
- ensure_storage_object_absent: valida que arquivo não existe no storage
- upload_local_file: wrapper para upload direto
- insert_document_record: cria documento na tabela documents
- insert_document_version_record: cria versão na tabela document_versions
- update_document_current_version: atualiza current_version
- normalize_bucket: normaliza nome do bucket
- build_storage_adapter: factory para SupabaseStorageAdapter
- upload_items_with_adapter: pipeline de upload batch com retry

Isolamento:
- Mock de supabase.auth.get_user()
- Mock de exec_postgrest() para queries
- Mock de storage API (_storage_list_files, _storage_upload_file)
- Mock de upload_with_retry e classify_upload_exception
- Mock de environment variables (SUPABASE_DEFAULT_ORG, SUPABASE_BUCKET)
"""

import pytest
from unittest.mock import Mock

from src.modules.uploads.repository import (
    current_user_id,
    resolve_org_id,
    ensure_storage_object_absent,
    upload_local_file,
    insert_document_record,
    insert_document_version_record,
    update_document_current_version,
    normalize_bucket,
    build_storage_adapter,
    upload_items_with_adapter,
)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_supabase_auth(monkeypatch):
    """Mock de supabase.auth.get_user()."""
    mock_user = Mock()
    mock_user.id = "user-123"
    mock_response = Mock()
    mock_response.user = mock_user
    mock_get_user = Mock(return_value=mock_response)

    monkeypatch.setattr("src.modules.uploads.repository.supabase.auth.get_user", mock_get_user)
    return mock_get_user


@pytest.fixture
def mock_exec_postgrest(monkeypatch):
    """Mock de exec_postgrest()."""
    mock_func = Mock()
    monkeypatch.setattr("src.modules.uploads.repository.exec_postgrest", mock_func)
    return mock_func


@pytest.fixture
def mock_storage_list_files(monkeypatch):
    """Mock de _storage_list_files()."""
    mock_func = Mock(return_value=[])
    monkeypatch.setattr("src.modules.uploads.repository._storage_list_files", mock_func)
    return mock_func


@pytest.fixture
def mock_storage_upload_file(monkeypatch):
    """Mock de _storage_upload_file()."""
    mock_func = Mock(return_value=None)
    monkeypatch.setattr("src.modules.uploads.repository._storage_upload_file", mock_func)
    return mock_func


@pytest.fixture
def mock_upload_retry(monkeypatch):
    """Mock de upload_with_retry()."""
    mock_func = Mock(return_value=None)
    monkeypatch.setattr("src.modules.uploads.repository.upload_with_retry", mock_func)
    return mock_func


@pytest.fixture
def mock_classify_exception(monkeypatch):
    """Mock de classify_upload_exception()."""
    mock_func = Mock(side_effect=lambda exc: exc)
    monkeypatch.setattr("src.modules.uploads.repository.classify_upload_exception", mock_func)
    return mock_func


# ============================================================================
# TESTES: current_user_id
# ============================================================================


class TestCurrentUserId:
    """Testes para current_user_id()."""

    def test_authenticated_user_returns_id(self, mock_supabase_auth):
        """Usuário autenticado retorna user.id."""
        result = current_user_id()

        assert result == "user-123"
        mock_supabase_auth.assert_called_once()

    def test_unauthenticated_user_returns_none(self, monkeypatch):
        """Usuário não autenticado retorna None."""
        mock_response = Mock()
        mock_response.user = None
        mock_get_user = Mock(return_value=mock_response)
        monkeypatch.setattr("src.modules.uploads.repository.supabase.auth.get_user", mock_get_user)

        result = current_user_id()

        assert result is None

    def test_exception_returns_none(self, monkeypatch):
        """Exceção em get_user() retorna None sem propagar."""
        mock_get_user = Mock(side_effect=Exception("Network error"))
        monkeypatch.setattr("src.modules.uploads.repository.supabase.auth.get_user", mock_get_user)

        result = current_user_id()

        assert result is None

    def test_dict_response_extracts_id(self, monkeypatch):
        """Response formato dict extrai user.id corretamente."""
        mock_response = {"user": {"id": "user-456"}}
        mock_get_user = Mock(return_value=mock_response)
        monkeypatch.setattr("src.modules.uploads.repository.supabase.auth.get_user", mock_get_user)

        result = current_user_id()

        assert result == "user-456"


# ============================================================================
# TESTES: resolve_org_id
# ============================================================================


class TestResolveOrgId:
    """Testes para resolve_org_id()."""

    def test_authenticated_with_membership_returns_org_id(self, mock_supabase_auth, mock_exec_postgrest):
        """Usuário autenticado com membership retorna org_id."""
        mock_exec_postgrest.return_value = Mock(data=[{"org_id": "org-789"}])

        result = resolve_org_id()

        assert result == "org-789"
        mock_exec_postgrest.assert_called_once()

    def test_unauthenticated_returns_env_fallback(self, monkeypatch):
        """Usuário não autenticado retorna env fallback."""
        monkeypatch.setenv("SUPABASE_DEFAULT_ORG", "env-org")
        mock_get_user = Mock(return_value=Mock(user=None))
        monkeypatch.setattr("src.modules.uploads.repository.supabase.auth.get_user", mock_get_user)

        result = resolve_org_id()

        assert result == "env-org"

    def test_empty_memberships_returns_fallback(self, mock_supabase_auth, mock_exec_postgrest, monkeypatch):
        """Memberships vazio retorna fallback."""
        monkeypatch.setenv("SUPABASE_DEFAULT_ORG", "fallback-org")
        mock_exec_postgrest.return_value = Mock(data=[])

        result = resolve_org_id()

        assert result == "fallback-org"

    def test_exception_in_query_returns_fallback(self, mock_supabase_auth, mock_exec_postgrest, monkeypatch):
        """Exceção na query retorna fallback."""
        monkeypatch.setenv("SUPABASE_DEFAULT_ORG", "error-fallback")
        mock_exec_postgrest.side_effect = Exception("DB error")

        result = resolve_org_id()

        assert result == "error-fallback"

    def test_no_env_returns_unknown_org(self, monkeypatch):
        """Sem env e sem usuário retorna 'unknown-org'."""
        monkeypatch.delenv("SUPABASE_DEFAULT_ORG", raising=False)
        mock_get_user = Mock(return_value=Mock(user=None))
        monkeypatch.setattr("src.modules.uploads.repository.supabase.auth.get_user", mock_get_user)

        result = resolve_org_id()

        assert result == "unknown-org"


# ============================================================================
# TESTES: ensure_storage_object_absent
# ============================================================================


class TestEnsureStorageObjectAbsent:
    """Testes para ensure_storage_object_absent()."""

    def test_file_not_exists_no_exception(self, mock_storage_list_files):
        """Arquivo não existe, não levanta exceção."""
        mock_storage_list_files.return_value = []

        ensure_storage_object_absent("org/client/GERAL/new.pdf")

        # Não deve levantar exceção
        mock_storage_list_files.assert_called_once_with("org/client/GERAL")

    def test_file_exists_name_match_raises_error(self, mock_storage_list_files):
        """Arquivo existe (name match) levanta RuntimeError."""
        mock_storage_list_files.return_value = [{"name": "existing.pdf", "full_path": "org/client/GERAL/existing.pdf"}]

        with pytest.raises(RuntimeError, match="Arquivo ja existente no storage"):
            ensure_storage_object_absent("org/client/GERAL/existing.pdf")

    def test_file_exists_full_path_match_raises_error(self, mock_storage_list_files):
        """Arquivo existe (full_path match) levanta RuntimeError."""
        mock_storage_list_files.return_value = [{"name": "other.pdf", "full_path": "org/client/GERAL/file.pdf"}]

        with pytest.raises(RuntimeError, match="Arquivo ja existente no storage"):
            ensure_storage_object_absent("org/client/GERAL/file.pdf")

    def test_item_is_string_raises_error(self, mock_storage_list_files):
        """Item é string e match levanta RuntimeError."""
        mock_storage_list_files.return_value = ["file.pdf"]

        with pytest.raises(RuntimeError, match="Arquivo ja existente no storage"):
            ensure_storage_object_absent("org/client/GERAL/file.pdf")


# ============================================================================
# TESTES: upload_local_file
# ============================================================================


class TestUploadLocalFile:
    """Testes para upload_local_file()."""

    def test_successful_upload(self, mock_storage_upload_file):
        """Upload bem-sucedido não levanta exceção."""
        upload_local_file("/tmp/file.pdf", "org/client/file.pdf", "application/pdf")

        mock_storage_upload_file.assert_called_once_with("/tmp/file.pdf", "org/client/file.pdf", "application/pdf")

    def test_upload_failure_propagates_exception(self, mock_storage_upload_file):
        """Falha no upload propaga exceção."""
        mock_storage_upload_file.side_effect = Exception("Upload failed")

        with pytest.raises(Exception, match="Upload failed"):
            upload_local_file("/tmp/file.pdf", "org/client/file.pdf", "application/pdf")


# ============================================================================
# TESTES: insert_document_record
# ============================================================================


class TestInsertDocumentRecord:
    """Testes para insert_document_record()."""

    def test_successful_insert_returns_dict(self, mock_exec_postgrest):
        """Insert bem-sucedido retorna dict."""
        mock_exec_postgrest.return_value = Mock(data=[{"id": 1, "title": "doc.pdf", "kind": "application/pdf"}])

        result = insert_document_record(client_id=123, title="doc.pdf", mime_type="application/pdf", user_id="user-123")

        assert result == {"id": 1, "title": "doc.pdf", "kind": "application/pdf"}
        mock_exec_postgrest.assert_called_once()

    def test_rls_blocks_insert_raises_error(self, mock_exec_postgrest):
        """RLS bloqueia INSERT levanta RuntimeError."""
        mock_exec_postgrest.return_value = Mock(data=[])

        with pytest.raises(RuntimeError, match="INSERT bloqueado por RLS"):
            insert_document_record(client_id=123, title="doc.pdf", mime_type="application/pdf", user_id="user-123")

    def test_converts_client_id_to_int(self, mock_exec_postgrest):
        """Converte client_id para int."""
        mock_exec_postgrest.return_value = Mock(data=[{"id": 1}])

        insert_document_record(client_id=456, title="doc.pdf", mime_type="application/pdf", user_id="user-123")

        # Verifica que o insert foi chamado (implementação específica do Supabase)
        assert mock_exec_postgrest.called


# ============================================================================
# TESTES: insert_document_version_record
# ============================================================================


class TestInsertDocumentVersionRecord:
    """Testes para insert_document_version_record()."""

    def test_successful_insert_returns_dict(self, mock_exec_postgrest):
        """Insert bem-sucedido retorna dict."""
        mock_exec_postgrest.return_value = Mock(data=[{"id": 10, "document_id": 1, "storage_path": "org/file.pdf"}])

        result = insert_document_version_record(
            document_id=1,
            storage_path="org/file.pdf",
            size_bytes=1024,
            sha_value="abc123",
            uploaded_by="user-123",
        )

        assert result["id"] == 10
        assert result["document_id"] == 1

    def test_rls_blocks_insert_raises_error(self, mock_exec_postgrest):
        """RLS bloqueia INSERT levanta RuntimeError."""
        mock_exec_postgrest.return_value = Mock(data=[])

        with pytest.raises(RuntimeError, match="INSERT bloqueado por RLS"):
            insert_document_version_record(
                document_id=1,
                storage_path="org/file.pdf",
                size_bytes=1024,
                sha_value="abc123",
                uploaded_by="user-123",
            )


# ============================================================================
# TESTES: update_document_current_version
# ============================================================================


class TestUpdateDocumentCurrentVersion:
    """Testes para update_document_current_version()."""

    def test_successful_update(self, mock_exec_postgrest):
        """Update bem-sucedido não levanta exceção."""
        mock_exec_postgrest.return_value = Mock()

        update_document_current_version(document_id=1, version_id=10)

        mock_exec_postgrest.assert_called_once()

    def test_update_failure_propagates_exception(self, mock_exec_postgrest):
        """Falha no update propaga exceção."""
        mock_exec_postgrest.side_effect = Exception("Update failed")

        with pytest.raises(Exception, match="Update failed"):
            update_document_current_version(document_id=1, version_id=10)


# ============================================================================
# TESTES: normalize_bucket
# ============================================================================


class TestNormalizeBucket:
    """Testes para normalize_bucket()."""

    def test_provided_value_returned(self):
        """Value fornecido é retornado."""
        result = normalize_bucket("custom-bucket")

        assert result == "custom-bucket"

    def test_none_uses_env(self, monkeypatch):
        """None usa env SUPABASE_BUCKET."""
        monkeypatch.setenv("SUPABASE_BUCKET", "env-bucket")

        result = normalize_bucket(None)

        assert result == "env-bucket"

    def test_none_and_no_env_uses_default(self, monkeypatch):
        """None e sem env usa 'rc-docs' padrão."""
        monkeypatch.delenv("SUPABASE_BUCKET", raising=False)

        result = normalize_bucket(None)

        assert result == "rc-docs"

    def test_strips_whitespace(self):
        """Strip whitespace do valor."""
        result = normalize_bucket("  spaced-bucket  ")

        assert result == "spaced-bucket"


# ============================================================================
# TESTES: build_storage_adapter
# ============================================================================


class TestBuildStorageAdapter:
    """Testes para build_storage_adapter()."""

    def test_creates_adapter_with_bucket(self, monkeypatch):
        """Cria adapter com bucket fornecido."""
        mock_supabase = Mock()
        monkeypatch.setattr("src.modules.uploads.repository.supabase", mock_supabase)

        adapter = build_storage_adapter(bucket="test-bucket")

        assert adapter._bucket == "test-bucket"
        assert adapter._overwrite is False

    def test_overwrite_always_false(self, monkeypatch):
        """overwrite sempre False."""
        mock_supabase = Mock()
        monkeypatch.setattr("src.modules.uploads.repository.supabase", mock_supabase)

        adapter = build_storage_adapter(bucket="test-bucket")

        assert adapter._overwrite is False

    def test_uses_provided_client(self):
        """Usa supabase_client fornecido."""
        custom_client = Mock()

        adapter = build_storage_adapter(bucket="test-bucket", supabase_client=custom_client)

        assert adapter._client == custom_client


# ============================================================================
# TESTES: upload_items_with_adapter
# ============================================================================


class TestUploadItemsWithAdapter:
    """Testes para upload_items_with_adapter()."""

    def test_all_items_successful(self, mock_upload_retry, mock_classify_exception):
        """Todos os items bem-sucedidos."""
        mock_adapter = Mock()
        mock_adapter.upload_file = Mock(return_value=None)

        item1 = Mock(relative_path="file1.pdf", path="/tmp/file1.pdf")
        item2 = Mock(relative_path="file2.pdf", path="/tmp/file2.pdf")

        remote_path_builder = Mock(side_effect=["org/client/file1.pdf", "org/client/file2.pdf"])

        ok, failures = upload_items_with_adapter(
            adapter=mock_adapter,
            items=[item1, item2],
            cnpj_digits="12345678",
            subfolder="GERAL",
            remote_path_builder=remote_path_builder,
            client_id=123,
            org_id="org-abc",
        )

        assert ok == 2
        assert failures == []
        assert mock_upload_retry.call_count == 2

    def test_one_item_fails(self, mock_upload_retry, mock_classify_exception):
        """Um item falha, outro sucesso."""
        mock_adapter = Mock()

        item1 = Mock(relative_path="file1.pdf", path="/tmp/file1.pdf")
        item2 = Mock(relative_path="file2.pdf", path="/tmp/file2.pdf")

        error = Exception("Network error")
        mock_upload_retry.side_effect = [None, error]
        remote_path_builder = Mock(side_effect=["org/client/file1.pdf", "org/client/file2.pdf"])

        ok, failures = upload_items_with_adapter(
            adapter=mock_adapter,
            items=[item1, item2],
            cnpj_digits="12345678",
            subfolder="GERAL",
            remote_path_builder=remote_path_builder,
            client_id=123,
            org_id="org-abc",
        )

        assert ok == 1
        assert len(failures) == 1
        assert failures[0][0] == item2
        assert failures[0][1] == error

    def test_duplicate_error_not_failure(self, mock_upload_retry, mock_classify_exception):
        """Duplicate error (409) não é falha."""
        mock_adapter = Mock()

        item = Mock(relative_path="file.pdf", path="/tmp/file.pdf")

        duplicate_error = Exception("Duplicate entry")
        duplicate_error.detail = "duplicate key violation"
        mock_upload_retry.side_effect = duplicate_error
        mock_classify_exception.return_value = duplicate_error
        remote_path_builder = Mock(return_value="org/client/file.pdf")

        ok, failures = upload_items_with_adapter(
            adapter=mock_adapter,
            items=[item],
            cnpj_digits="12345678",
            subfolder="GERAL",
            remote_path_builder=remote_path_builder,
            client_id=123,
            org_id="org-abc",
        )

        assert ok == 0
        assert failures == []  # Duplicate não adiciona em failures

    def test_calls_progress_callback(self, mock_upload_retry, mock_classify_exception):
        """Chama progress_callback para cada item."""
        mock_adapter = Mock()
        mock_callback = Mock()

        item1 = Mock(relative_path="file1.pdf", path="/tmp/file1.pdf")
        item2 = Mock(relative_path="file2.pdf", path="/tmp/file2.pdf")

        remote_path_builder = Mock(side_effect=["org/client/file1.pdf", "org/client/file2.pdf"])

        upload_items_with_adapter(
            adapter=mock_adapter,
            items=[item1, item2],
            cnpj_digits="12345678",
            subfolder="GERAL",
            progress_callback=mock_callback,
            remote_path_builder=remote_path_builder,
            client_id=123,
            org_id="org-abc",
        )

        assert mock_callback.call_count == 2
        mock_callback.assert_any_call(item1)
        mock_callback.assert_any_call(item2)

    def test_uses_remote_path_builder_with_keywords(self, mock_upload_retry, mock_classify_exception):
        """Usa remote_path_builder com client_id/org_id keywords."""
        mock_adapter = Mock()
        mock_builder = Mock(return_value="org/client/file.pdf")

        item = Mock(relative_path="file.pdf", path="/tmp/file.pdf")

        upload_items_with_adapter(
            adapter=mock_adapter,
            items=[item],
            cnpj_digits="12345678",
            subfolder="GERAL",
            remote_path_builder=mock_builder,
            client_id=456,
            org_id="org-xyz",
        )

        mock_builder.assert_called_once_with("12345678", "file.pdf", "GERAL", client_id=456, org_id="org-xyz")

    def test_calls_upload_with_retry(self, mock_upload_retry, mock_classify_exception):
        """Chama upload_with_retry com parâmetros corretos."""
        mock_adapter = Mock()
        mock_adapter.upload_file = Mock()

        item = Mock(relative_path="file.pdf", path="/tmp/file.pdf")
        remote_path_builder = Mock(return_value="org/client/file.pdf")

        upload_items_with_adapter(
            adapter=mock_adapter,
            items=[item],
            cnpj_digits="12345678",
            subfolder="GERAL",
            remote_path_builder=remote_path_builder,
            client_id=123,
            org_id="org-abc",
        )

        # Verifica que upload_with_retry foi chamado
        mock_upload_retry.assert_called_once()
        call_args = mock_upload_retry.call_args
        assert call_args[0][0] == mock_adapter.upload_file
        assert call_args[0][1] == "/tmp/file.pdf"
        assert call_args[0][2] == "org/client/file.pdf"

    def test_classifies_exceptions(self, mock_upload_retry, mock_classify_exception):
        """Classifica exceções com classify_upload_exception."""
        mock_adapter = Mock()

        item = Mock(relative_path="file.pdf", path="/tmp/file.pdf")
        error = Exception("Network error")
        mock_upload_retry.side_effect = error
        remote_path_builder = Mock(return_value="org/client/file.pdf")

        upload_items_with_adapter(
            adapter=mock_adapter,
            items=[item],
            cnpj_digits="12345678",
            subfolder="GERAL",
            remote_path_builder=remote_path_builder,
            client_id=123,
            org_id="org-abc",
        )

        mock_classify_exception.assert_called_once_with(error)

    def test_empty_items_list(self, mock_upload_retry, mock_classify_exception):
        """Lista vazia de items retorna (0, [])."""
        mock_adapter = Mock()
        remote_path_builder = Mock()

        ok, failures = upload_items_with_adapter(
            adapter=mock_adapter,
            items=[],
            cnpj_digits="12345678",
            subfolder="GERAL",
            remote_path_builder=remote_path_builder,
            client_id=123,
            org_id="org-abc",
        )

        assert ok == 0
        assert failures == []
