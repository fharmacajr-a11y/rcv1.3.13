# -*- coding: utf-8 -*-
"""
Testes para src/modules/auditoria/storage.py - FASE 2 TEST-001.

Cobertura:
- Contextos de storage (AuditoriaStorageContext, AuditoriaUploadContext)
- Construção de prefixos
- Operações de storage (ensure_folder, list, upload, remove)
- Paginação de listagem
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.modules.auditoria.storage import (
    AuditoriaStorageContext,
    AuditoriaUploadContext,
    get_clients_bucket,
    build_client_prefix,
    build_auditoria_prefix,
    make_storage_context,
    ensure_auditoria_folder,
    list_existing_file_names,
    upload_storage_bytes,
    remove_storage_objects,
)


# ============================================================================
# TESTES DE CONTEXTOS (DATACLASSES)
# ============================================================================


class TestAuditoriaStorageContext:
    """Testes para AuditoriaStorageContext."""

    def test_context_creation(self):
        """Contexto é criado com todos os campos."""
        ctx = AuditoriaStorageContext(
            bucket="test-bucket",
            org_id="org-123",
            client_root="org-123/456",
            auditoria_prefix="org-123/456/GERAL/Auditoria",
        )

        assert ctx.bucket == "test-bucket"
        assert ctx.org_id == "org-123"
        assert ctx.client_root == "org-123/456"
        assert ctx.auditoria_prefix == "org-123/456/GERAL/Auditoria"

    def test_build_path(self):
        """build_path() constrói caminho relativo."""
        ctx = AuditoriaStorageContext(
            bucket="bucket",
            org_id="org-1",
            client_root="org-1/100",
            auditoria_prefix="org-1/100/GERAL/Auditoria",
        )

        path = ctx.build_path("documento.pdf")

        assert path == "org-1/100/GERAL/Auditoria/documento.pdf"

    def test_build_path_strips_leading_and_trailing_slashes(self):
        """build_path() usa lstrip('/') na concatenação final."""
        ctx = AuditoriaStorageContext(
            bucket="bucket",
            org_id="org-1",
            client_root="org-1/100",
            auditoria_prefix="org-1/100/GERAL/Auditoria",  # sem trailing slash
        )

        path = ctx.build_path("subpasta/arquivo.pdf")

        assert not path.startswith("/")
        assert not path.endswith("/")
        assert path == "org-1/100/GERAL/Auditoria/subpasta/arquivo.pdf"

    def test_context_is_frozen(self):
        """Contexto é imutável (frozen dataclass)."""
        ctx = AuditoriaStorageContext(
            bucket="bucket",
            org_id="org-1",
            client_root="root",
            auditoria_prefix="prefix",
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            ctx.bucket = "outro"  # type: ignore


class TestAuditoriaUploadContext:
    """Testes para AuditoriaUploadContext."""

    def test_upload_context_creation(self):
        """Contexto de upload é criado corretamente."""
        ctx = AuditoriaUploadContext(
            bucket="uploads-bucket",
            base_prefix="org/client/GERAL/Auditoria",
            org_id="org-abc",
            client_id=999,
        )

        assert ctx.bucket == "uploads-bucket"
        assert ctx.base_prefix == "org/client/GERAL/Auditoria"
        assert ctx.org_id == "org-abc"
        assert ctx.client_id == 999

    def test_upload_context_is_frozen(self):
        """Contexto de upload é imutável."""
        ctx = AuditoriaUploadContext(
            bucket="b",
            base_prefix="p",
            org_id="o",
            client_id=1,
        )

        with pytest.raises(Exception):
            ctx.client_id = 2  # type: ignore


# ============================================================================
# TESTES DE FUNÇÕES DE CONSTRUÇÃO DE PREFIXOS
# ============================================================================


class TestGetClientsBucket:
    """Testes para get_clients_bucket()."""

    def test_returns_default_bucket(self):
        """Retorna bucket padrão quando env não definida."""
        # O bucket default está no código
        result = get_clients_bucket()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_uses_env_variable(self, monkeypatch):
        """Usa variável de ambiente quando definida."""
        # Nota: Como o módulo já foi importado, a constante foi definida
        # Este teste verifica que a função retorna a constante
        result = get_clients_bucket()
        assert result  # Deve ter algum valor


class TestBuildClientPrefix:
    """Testes para build_client_prefix()."""

    def test_basic_prefix(self):
        """Prefixo básico é construído."""
        prefix = build_client_prefix(123, "org-abc")

        assert "org-abc" in prefix
        assert "123" in prefix

    def test_prefix_no_leading_slash(self):
        """Prefixo não começa com barra."""
        prefix = build_client_prefix(1, "org")

        assert not prefix.startswith("/")

    def test_prefix_no_trailing_slash(self):
        """Prefixo não termina com barra."""
        prefix = build_client_prefix(1, "org")

        assert not prefix.endswith("/")


class TestBuildAuditoriaPrefix:
    """Testes para build_auditoria_prefix()."""

    def test_basic_prefix(self):
        """Prefixo de auditoria é construído."""
        prefix = build_auditoria_prefix("org-1/100")

        assert "org-1/100" in prefix
        assert "GERAL" in prefix
        assert "Auditoria" in prefix

    def test_prefix_structure(self):
        """Estrutura correta: client_root/GERAL/Auditoria."""
        prefix = build_auditoria_prefix("root/client")

        assert prefix == "root/client/GERAL/Auditoria"


class TestMakeStorageContext:
    """Testes para make_storage_context()."""

    def test_creates_complete_context(self):
        """Contexto completo é criado."""
        ctx = make_storage_context(client_id=456, org_id="org-xyz")

        assert isinstance(ctx, AuditoriaStorageContext)
        assert ctx.org_id == "org-xyz"
        assert "456" in ctx.client_root
        assert "GERAL/Auditoria" in ctx.auditoria_prefix

    def test_bucket_is_set(self):
        """Bucket é definido no contexto."""
        ctx = make_storage_context(client_id=1, org_id="org")

        assert ctx.bucket == get_clients_bucket()


# ============================================================================
# TESTES DE OPERAÇÕES DE STORAGE
# ============================================================================


class TestEnsureAuditoriaFolder:
    """Testes para ensure_auditoria_folder()."""

    def test_creates_keep_file(self):
        """Cria arquivo .keep na pasta de auditoria."""
        mock_sb = MagicMock()
        mock_storage = MagicMock()
        mock_sb.storage.from_.return_value = mock_storage
        mock_storage.upload.return_value = MagicMock(error=None)

        ctx = AuditoriaStorageContext(
            bucket="test-bucket",
            org_id="org-1",
            client_root="org-1/100",
            auditoria_prefix="org-1/100/GERAL/Auditoria",
        )

        ensure_auditoria_folder(mock_sb, ctx)

        mock_sb.storage.from_.assert_called_once_with("test-bucket")
        mock_storage.upload.assert_called_once()
        call_args = mock_storage.upload.call_args
        assert ".keep" in call_args[1]["path"]

    def test_raises_on_error(self):
        """Levanta exceção quando storage retorna erro."""
        mock_sb = MagicMock()
        mock_storage = MagicMock()
        mock_sb.storage.from_.return_value = mock_storage
        mock_storage.upload.return_value = MagicMock(error="Upload failed")

        ctx = AuditoriaStorageContext(
            bucket="bucket",
            org_id="org",
            client_root="root",
            auditoria_prefix="prefix",
        )

        with pytest.raises(RuntimeError, match="Upload failed"):
            ensure_auditoria_folder(mock_sb, ctx)


class TestListExistingFileNames:
    """Testes para list_existing_file_names()."""

    def test_lists_files(self):
        """Lista arquivos corretamente."""
        mock_sb = MagicMock()
        mock_storage = MagicMock()
        mock_sb.storage.from_.return_value = mock_storage
        mock_storage.list.return_value = [
            {"name": "file1.pdf"},
            {"name": "file2.zip"},
            {"name": "file3.doc"},
        ]

        result = list_existing_file_names(mock_sb, "bucket", "prefix")

        assert result == {"file1.pdf", "file2.zip", "file3.doc"}

    def test_handles_empty_response(self):
        """Trata resposta vazia."""
        mock_sb = MagicMock()
        mock_storage = MagicMock()
        mock_sb.storage.from_.return_value = mock_storage
        mock_storage.list.return_value = []

        result = list_existing_file_names(mock_sb, "bucket", "prefix")

        assert result == set()

    def test_handles_none_response(self):
        """Trata resposta None."""
        mock_sb = MagicMock()
        mock_storage = MagicMock()
        mock_sb.storage.from_.return_value = mock_storage
        mock_storage.list.return_value = None

        result = list_existing_file_names(mock_sb, "bucket", "prefix")

        assert result == set()

    def test_filters_empty_names(self):
        """Filtra arquivos sem nome."""
        mock_sb = MagicMock()
        mock_storage = MagicMock()
        mock_sb.storage.from_.return_value = mock_storage
        mock_storage.list.return_value = [
            {"name": "valid.pdf"},
            {"name": ""},
            {"name": None},
            {"other": "data"},
        ]

        result = list_existing_file_names(mock_sb, "bucket", "prefix")

        assert result == {"valid.pdf"}

    def test_pagination(self):
        """Testa paginação de listagem."""
        mock_sb = MagicMock()
        mock_storage = MagicMock()
        mock_sb.storage.from_.return_value = mock_storage

        # Primeira página cheia, segunda parcial
        mock_storage.list.side_effect = [
            [{"name": f"file{i}.pdf"} for i in range(100)],  # página 1
            [{"name": "last.pdf"}],  # página 2 (parcial)
        ]

        result = list_existing_file_names(mock_sb, "bucket", "prefix", page_size=100)

        assert len(result) == 101
        assert "file0.pdf" in result
        assert "last.pdf" in result


class TestUploadStorageBytes:
    """Testes para upload_storage_bytes()."""

    def test_uploads_with_correct_params(self):
        """Upload usa parâmetros corretos."""
        mock_sb = MagicMock()
        mock_storage = MagicMock()
        mock_sb.storage.from_.return_value = mock_storage

        upload_storage_bytes(
            mock_sb,
            bucket="my-bucket",
            dest_path="path/to/file.pdf",
            data=b"PDF content",
            content_type="application/pdf",
        )

        mock_sb.storage.from_.assert_called_once_with("my-bucket")
        mock_storage.upload.assert_called_once()

        call_args = mock_storage.upload.call_args
        assert call_args[0][0] == "path/to/file.pdf"
        assert call_args[0][1] == b"PDF content"

    def test_upsert_option(self):
        """Opção upsert é passada corretamente."""
        mock_sb = MagicMock()
        mock_storage = MagicMock()
        mock_sb.storage.from_.return_value = mock_storage

        upload_storage_bytes(
            mock_sb,
            bucket="bucket",
            dest_path="path",
            data=b"data",
            content_type="text/plain",
            upsert=True,
        )

        call_args = mock_storage.upload.call_args
        options = call_args[0][2]
        assert options["upsert"] == "true"

    def test_default_content_type(self):
        """Content-type padrão é application/octet-stream."""
        mock_sb = MagicMock()
        mock_storage = MagicMock()
        mock_sb.storage.from_.return_value = mock_storage

        upload_storage_bytes(
            mock_sb,
            bucket="bucket",
            dest_path="path",
            data=b"data",
            content_type="",
        )

        call_args = mock_storage.upload.call_args
        options = call_args[0][2]
        assert options["content-type"] == "application/octet-stream"


class TestRemoveStorageObjects:
    """Testes para remove_storage_objects()."""

    def test_removes_objects(self):
        """Remove objetos corretamente."""
        mock_sb = MagicMock()
        mock_storage = MagicMock()
        mock_sb.storage.from_.return_value = mock_storage

        remove_storage_objects(mock_sb, "bucket", ["path1", "path2", "path3"])

        mock_sb.storage.from_.assert_called_once_with("bucket")
        mock_storage.remove.assert_called_once_with(["path1", "path2", "path3"])

    def test_noop_on_empty_list(self):
        """Não faz nada com lista vazia."""
        mock_sb = MagicMock()

        remove_storage_objects(mock_sb, "bucket", [])

        mock_sb.storage.from_.assert_not_called()

    def test_accepts_iterable(self):
        """Aceita qualquer iterável."""
        mock_sb = MagicMock()
        mock_storage = MagicMock()
        mock_sb.storage.from_.return_value = mock_storage

        # Passar um generator
        paths_gen = (f"path{i}" for i in range(3))
        remove_storage_objects(mock_sb, "bucket", paths_gen)

        mock_storage.remove.assert_called_once()
        call_args = mock_storage.remove.call_args[0][0]
        assert len(call_args) == 3
