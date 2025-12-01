"""Round 13: Cobertura mínima viável para _upload.py

Baseline: 30.4% → Target: 90%+
Foco: Branches críticas não cobertas
"""

from __future__ import annotations

import os
import tempfile
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.modules.clientes.forms._prepare import UploadCtx
from src.modules.clientes.forms._upload import (
    _build_document_version_payload,
    perform_uploads,
)


def _make_tmp_path(*parts: str) -> str:
    """Helper para construir caminhos temporários sem hardcode."""
    return os.path.join(tempfile.gettempdir(), *parts)


class TestBuildDocumentVersionPayload:
    """Linhas 34-47: testa fallbacks."""

    def test_payload_with_none_user_id(self):
        """Linha 45: user_id None → 'unknown'."""
        ctx = MagicMock(user_id=None, created_at="2025-01-10T10:30:00Z")
        payload = _build_document_version_payload(
            ctx=ctx, document_id=456, storage_path="path.pdf", size_bytes=2048, sha256_hash="hash123"
        )
        if payload["uploaded_by"] != "unknown":
            pytest.fail("uploaded_by deveria ser 'unknown'")

    def test_payload_with_none_created_at(self):
        """Linha 46: created_at None → now_iso_z()."""
        ctx = MagicMock(user_id="user-123", created_at=None)
        with patch("src.modules.clientes.forms._upload.now_iso_z", return_value="2025-01-10T11:00:00Z"):
            payload = _build_document_version_payload(
                ctx=ctx, document_id=101, storage_path="file.pdf", size_bytes=512, sha256_hash="hash456"
            )
            if payload["created_at"] != "2025-01-10T11:00:00Z":
                pytest.fail("created_at não corresponde ao valor esperado")


class TestGetsizeException:
    """Linhas 130-133: exception em os.path.getsize."""

    def test_getsize_exception_is_caught(self):
        """Exception em getsize é capturada e logged."""
        mock_self = MagicMock()
        ctx = UploadCtx(app=mock_self, row={"id": 1}, ents={}, arquivos_selecionados=["f1.pdf"], win=None)
        ctx.abort = False
        tmpdir = tempfile.gettempdir()
        ctx.files = [(os.path.join(tmpdir, "f1.pdf"), "f1.pdf")]
        ctx.client_id = 123
        ctx.org_id = "org456"
        ctx.bucket = "test-bucket"
        ctx.pasta_local = tmpdir
        ctx.subpasta = None
        mock_self._upload_ctx = ctx

        with (
            patch("src.modules.clientes.forms._upload.UploadProgressDialog") as mock_dialog_cls,
            patch("src.modules.clientes.forms._upload.threading.Thread"),
            patch("src.modules.clientes.forms._upload.os.path.getsize", side_effect=OSError("Permission denied")),
            patch("src.modules.clientes.forms._upload.logger") as mock_logger,
        ):
            mock_dialog_cls.return_value = MagicMock()
            perform_uploads(mock_self, {"id": 1}, {}, [], None)

            if not mock_logger.debug.called:
                pytest.fail("logger.debug deveria ter sido chamado")
            calls = [str(c) for c in mock_logger.debug.call_args_list]
            if not any("Falha ao obter tamanho" in c for c in calls):
                pytest.fail("esperado log de 'Falha ao obter tamanho'")


class TestWorkerExecution:
    """Linhas 152-272: execução do worker (thread capture)."""

    def test_worker_executes_successfully(self):
        """Worker executa com sucesso: delete → upload → DB inserts."""
        mock_self = MagicMock()
        ctx = UploadCtx(app=mock_self, row={"id": 1}, ents={}, arquivos_selecionados=["doc.pdf"], win=None)
        ctx.abort = False
        ctx.files = [(_make_tmp_path("doc.pdf"), "doc.pdf")]
        ctx.client_id = 123
        ctx.org_id = "org456"
        ctx.bucket = "test-bucket"
        ctx.pasta_local = "/base"
        ctx.subpasta = None
        ctx.src_dir = None
        ctx.user_id = "user-uuid-123"
        ctx.created_at = "2025-01-10T12:00:00Z"
        mock_self._upload_ctx = ctx

        worker_func = None

        def capture_worker(*args, **kwargs):
            nonlocal worker_func
            worker_func = kwargs.get("target")
            return MagicMock()

        with (
            patch("src.modules.clientes.forms._upload.UploadProgressDialog") as mock_dialog_cls,
            patch("src.modules.clientes.forms._upload.threading.Thread", side_effect=capture_worker),
            patch("src.modules.clientes.forms._upload.os.path.getsize", return_value=2048),
            patch("src.modules.clientes.forms._upload.using_storage_backend") as mock_backend,
            patch("src.modules.clientes.forms._upload.storage_delete_file") as mock_delete,
            patch("src.modules.clientes.forms._upload.Path") as mock_path_cls,
            patch("src.modules.clientes.forms._upload.make_storage_key", return_value="org456/123/GERAL/doc.pdf"),
            patch("src.modules.clientes.forms._upload.storage_upload_file") as mock_upload,
            patch("src.modules.clientes.forms._upload.exec_postgrest") as mock_exec,
            patch("src.modules.clientes.forms._upload.finalize_state"),
        ):
            # Setup context manager
            mock_backend.return_value.__enter__ = MagicMock(return_value=None)
            mock_backend.return_value.__exit__ = MagicMock(return_value=False)

            mock_dialog_cls.return_value = MagicMock()

            # Mock Path.read_bytes
            mock_path_inst = MagicMock()
            mock_path_inst.read_bytes.return_value = b"PDF content"
            mock_path_cls.return_value = mock_path_inst

            # Mock DB responses
            mock_exec.side_effect = [
                Mock(data=[{"id": 456}]),  # INSERT documents
                Mock(data=[{"id": 789}]),  # INSERT document_versions
                Mock(),  # UPDATE documents
            ]

            perform_uploads(mock_self, {"id": 1}, {}, [], None)

            if worker_func is None:
                pytest.fail("worker_func não deveria ser None")
            worker_func()

            # Verifica fluxo completo
            mock_delete.assert_called_once()
            mock_upload.assert_called_once()
            if mock_exec.call_count != 3:
                pytest.fail(f"esperado 3 chamadas de exec, obteve {mock_exec.call_count}")
            # finalize_state não é sempre chamado (depende de after() timing)

    def test_worker_handles_upload_error_rls(self):
        """Linha 213-217: erro 'rls' é classificado e logged."""
        mock_self = MagicMock()
        ctx = UploadCtx(app=mock_self, row={"id": 1}, ents={}, arquivos_selecionados=["doc.pdf"], win=None)
        ctx.abort = False
        ctx.files = [(_make_tmp_path("doc.pdf"), "doc.pdf")]
        ctx.client_id = 123
        ctx.org_id = "org456"
        ctx.bucket = "test-bucket"
        ctx.pasta_local = "/base"
        ctx.subpasta = None
        ctx.src_dir = None
        mock_self._upload_ctx = ctx

        worker_func = None

        def capture_worker(*args, **kwargs):
            nonlocal worker_func
            worker_func = kwargs.get("target")
            return MagicMock()

        with (
            patch("src.modules.clientes.forms._upload.UploadProgressDialog") as mock_dialog_cls,
            patch("src.modules.clientes.forms._upload.threading.Thread", side_effect=capture_worker),
            patch("src.modules.clientes.forms._upload.os.path.getsize", return_value=1024),
            patch("src.modules.clientes.forms._upload.using_storage_backend") as mock_backend,
            patch("src.modules.clientes.forms._upload.storage_delete_file"),
            patch("src.modules.clientes.forms._upload.Path") as mock_path_cls,
            patch("src.modules.clientes.forms._upload.make_storage_key", return_value="org456/123/GERAL/doc.pdf"),
            patch("src.modules.clientes.forms._upload.storage_upload_file", side_effect=RuntimeError("RLS violation")),
            patch("src.modules.clientes.forms._upload.classify_storage_error", return_value="rls"),
            patch("src.modules.clientes.forms._upload.logger") as mock_logger,
        ):
            mock_backend.return_value.__enter__ = MagicMock(return_value=None)
            mock_backend.return_value.__exit__ = MagicMock(return_value=False)

            mock_dialog_cls.return_value = MagicMock()

            mock_path_inst = MagicMock()
            mock_path_inst.read_bytes.return_value = b"content"
            mock_path_cls.return_value = mock_path_inst

            perform_uploads(mock_self, {"id": 1}, {}, [], None)

            if worker_func is None:
                pytest.fail("worker_func não deveria ser None")
            worker_func()

            # Verifica erro logged
            error_calls = [str(c) for c in mock_logger.error.call_args_list]
            if not any("permissão" in c.lower() or "rls" in c.lower() for c in error_calls):
                pytest.fail("esperado log de erro sobre permissão ou RLS")

    def test_worker_handles_upload_error_exists(self):
        """Linha 218-222: erro 'exists' gera warning."""
        mock_self = MagicMock()
        ctx = UploadCtx(app=mock_self, row={"id": 1}, ents={}, arquivos_selecionados=["doc.pdf"], win=None)
        ctx.abort = False
        ctx.files = [(_make_tmp_path("doc.pdf"), "doc.pdf")]
        ctx.client_id = 123
        ctx.org_id = "org456"
        ctx.bucket = "test-bucket"
        ctx.pasta_local = "/base"
        ctx.subpasta = None
        ctx.src_dir = None
        mock_self._upload_ctx = ctx

        worker_func = None

        def capture_worker(*args, **kwargs):
            nonlocal worker_func
            worker_func = kwargs.get("target")
            return MagicMock()

        with (
            patch("src.modules.clientes.forms._upload.UploadProgressDialog") as mock_dialog_cls,
            patch("src.modules.clientes.forms._upload.threading.Thread", side_effect=capture_worker),
            patch("src.modules.clientes.forms._upload.os.path.getsize", return_value=1024),
            patch("src.modules.clientes.forms._upload.using_storage_backend") as mock_backend,
            patch("src.modules.clientes.forms._upload.storage_delete_file"),
            patch("src.modules.clientes.forms._upload.Path") as mock_path_cls,
            patch("src.modules.clientes.forms._upload.make_storage_key", return_value="org456/123/GERAL/doc.pdf"),
            patch("src.modules.clientes.forms._upload.storage_upload_file", side_effect=RuntimeError("File exists")),
            patch("src.modules.clientes.forms._upload.classify_storage_error", return_value="exists"),
            patch("src.modules.clientes.forms._upload.logger") as mock_logger,
        ):
            mock_backend.return_value.__enter__ = MagicMock(return_value=None)
            mock_backend.return_value.__exit__ = MagicMock(return_value=False)

            mock_dialog_cls.return_value = MagicMock()

            mock_path_inst = MagicMock()
            mock_path_inst.read_bytes.return_value = b"content"
            mock_path_cls.return_value = mock_path_inst

            perform_uploads(mock_self, {"id": 1}, {}, [], None)

            if worker_func is None:
                pytest.fail("worker_func não deveria ser None")
            worker_func()

            # Verifica warning
            warning_calls = [str(c) for c in mock_logger.warning.call_args_list]
            if not any("existia" in c.lower() for c in warning_calls):
                pytest.fail("esperado warning sobre arquivo que já existia")

    def test_worker_handles_upload_error_unknown(self):
        """Linha 223-227: erro 'unknown' usa exception()."""
        mock_self = MagicMock()
        ctx = UploadCtx(app=mock_self, row={"id": 1}, ents={}, arquivos_selecionados=["doc.pdf"], win=None)
        ctx.abort = False
        ctx.files = [(_make_tmp_path("doc.pdf"), "doc.pdf")]
        ctx.client_id = 123
        ctx.org_id = "org456"
        ctx.bucket = "test-bucket"
        ctx.pasta_local = "/base"
        ctx.subpasta = None
        ctx.src_dir = None
        mock_self._upload_ctx = ctx

        worker_func = None

        def capture_worker(*args, **kwargs):
            nonlocal worker_func
            worker_func = kwargs.get("target")
            return MagicMock()

        with (
            patch("src.modules.clientes.forms._upload.UploadProgressDialog") as mock_dialog_cls,
            patch("src.modules.clientes.forms._upload.threading.Thread", side_effect=capture_worker),
            patch("src.modules.clientes.forms._upload.os.path.getsize", return_value=1024),
            patch("src.modules.clientes.forms._upload.using_storage_backend") as mock_backend,
            patch("src.modules.clientes.forms._upload.storage_delete_file"),
            patch("src.modules.clientes.forms._upload.Path") as mock_path_cls,
            patch("src.modules.clientes.forms._upload.make_storage_key", return_value="org456/123/GERAL/doc.pdf"),
            patch("src.modules.clientes.forms._upload.storage_upload_file", side_effect=RuntimeError("Network error")),
            patch("src.modules.clientes.forms._upload.classify_storage_error", return_value="unknown"),
            patch("src.modules.clientes.forms._upload.logger") as mock_logger,
        ):
            mock_backend.return_value.__enter__ = MagicMock(return_value=None)
            mock_backend.return_value.__exit__ = MagicMock(return_value=False)

            mock_dialog_cls.return_value = MagicMock()

            mock_path_inst = MagicMock()
            mock_path_inst.read_bytes.return_value = b"content"
            mock_path_cls.return_value = mock_path_inst

            perform_uploads(mock_self, {"id": 1}, {}, [], None)

            if worker_func is None:
                pytest.fail("worker_func não deveria ser None")
            worker_func()

            # Verifica exception
            if not mock_logger.exception.called:
                pytest.fail("logger.exception deveria ter sido chamado")


class TestCloudOnlyBranches:
    """Linhas 156-173: branches CLOUD_ONLY."""

    def test_worker_with_cloud_only_false_copies_files(self):
        """CLOUD_ONLY=False: worker copia arquivos localmente."""
        mock_self = MagicMock()
        ctx = UploadCtx(app=mock_self, row={"id": 1}, ents={}, arquivos_selecionados=["doc.pdf"], win=None)
        ctx.abort = False
        tmpdir = tempfile.gettempdir()
        src_dir = os.path.join(tmpdir, "src")
        ctx.files = [(os.path.join(src_dir, "doc.pdf"), "doc.pdf")]
        ctx.client_id = 123
        ctx.org_id = "org456"
        ctx.bucket = "test-bucket"
        ctx.pasta_local = "/base"
        ctx.subpasta = None
        ctx.src_dir = src_dir
        mock_self._upload_ctx = ctx

        worker_func = None

        def capture_worker(*args, **kwargs):
            nonlocal worker_func
            worker_func = kwargs.get("target")
            return MagicMock()

        with (
            patch("src.modules.clientes.forms._upload.UploadProgressDialog") as mock_dialog_cls,
            patch("src.modules.clientes.forms._upload.threading.Thread", side_effect=capture_worker),
            patch("src.modules.clientes.forms._upload.os.path.getsize", return_value=1024),
            patch("src.modules.clientes.forms._upload.CLOUD_ONLY", False),
            patch("src.modules.clientes.forms._upload.os.makedirs") as mock_makedirs,
            patch("src.modules.clientes.forms._upload.shutil.copy2") as mock_copy,
            patch("src.modules.clientes.forms._upload.using_storage_backend") as mock_backend,
        ):
            mock_backend.return_value.__enter__ = MagicMock(return_value=None)
            mock_backend.return_value.__exit__ = MagicMock(return_value=False)

            mock_dialog_cls.return_value = MagicMock()

            perform_uploads(mock_self, {"id": 1}, {}, [], None)

            if worker_func is None:
                pytest.fail("worker_func não deveria ser None")
            worker_func()

            # Verifica que makedirs e copy foram chamados
            if not mock_makedirs.called:
                pytest.fail("os.makedirs deveria ter sido chamado")
            if not mock_copy.called:
                pytest.fail("shutil.copy2 deveria ter sido chamado")


class TestUploadProgressDialogViaTrigger:
    """Linhas 53-114: UploadProgressDialog testado via perform_uploads."""

    def test_dialog_initialization_and_update(self):
        """Dialog é criada e update_for_file é chamado via worker."""
        mock_self = MagicMock()
        ctx = UploadCtx(app=mock_self, row={"id": 1}, ents={}, arquivos_selecionados=["doc.pdf"], win=None)
        ctx.abort = False
        ctx.files = [(_make_tmp_path("doc.pdf"), "doc.pdf")]
        ctx.client_id = 123
        ctx.org_id = "org456"
        ctx.bucket = "test-bucket"
        ctx.pasta_local = "/base"
        ctx.subpasta = None
        ctx.src_dir = None
        ctx.user_id = "user-uuid"
        ctx.created_at = "2025-01-10T12:00:00Z"
        mock_self._upload_ctx = ctx

        worker_func = None

        def capture_worker(*args, **kwargs):
            nonlocal worker_func
            worker_func = kwargs.get("target")
            return MagicMock()

        with (
            patch("src.modules.clientes.forms._upload.UploadProgressDialog") as mock_dialog_cls,
            patch("src.modules.clientes.forms._upload.threading.Thread", side_effect=capture_worker),
            patch("src.modules.clientes.forms._upload.os.path.getsize", return_value=2048),
            patch("src.modules.clientes.forms._upload.using_storage_backend") as mock_backend,
            patch("src.modules.clientes.forms._upload.storage_delete_file"),
            patch("src.modules.clientes.forms._upload.Path") as mock_path_cls,
            patch("src.modules.clientes.forms._upload.make_storage_key", return_value="org456/123/GERAL/doc.pdf"),
            patch("src.modules.clientes.forms._upload.storage_upload_file"),
            patch("src.modules.clientes.forms._upload.exec_postgrest") as mock_exec,
            patch("src.modules.clientes.forms._upload.finalize_state"),
        ):
            mock_backend.return_value.__enter__ = MagicMock(return_value=None)
            mock_backend.return_value.__exit__ = MagicMock(return_value=False)

            mock_dialog = MagicMock()
            mock_dialog_cls.return_value = mock_dialog

            mock_path_inst = MagicMock()
            mock_path_inst.read_bytes.return_value = b"content"
            mock_path_cls.return_value = mock_path_inst

            mock_exec.side_effect = [
                Mock(data=[{"id": 456}]),
                Mock(data=[{"id": 789}]),
                Mock(),
            ]

            perform_uploads(mock_self, {"id": 1}, {}, [], None)

            # Dialog foi criada
            if not mock_dialog_cls.called:
                pytest.fail("UploadProgressDialog deveria ter sido instanciada")

            if worker_func is None:
                pytest.fail("worker_func não deveria ser None")
            worker_func()

            # Verifica que DB inserts foram executados (prova que worker rodou completamente)
            if mock_exec.call_count != 3:
                pytest.fail(f"esperado 3 chamadas de exec, obteve {mock_exec.call_count}")

    def test_dialog_with_zero_files(self):
        """Dialog com total_files=0 usa fallback para 1 (linha 54)."""
        mock_self = MagicMock()
        ctx = UploadCtx(app=mock_self, row={"id": 1}, ents={}, arquivos_selecionados=[], win=None)
        ctx.abort = False
        ctx.files = []  # Nenhum arquivo
        ctx.client_id = 123
        ctx.org_id = "org456"
        ctx.bucket = "test-bucket"
        ctx.pasta_local = "/base"
        ctx.subpasta = None
        mock_self._upload_ctx = ctx

        with (
            patch("src.modules.clientes.forms._upload.UploadProgressDialog") as mock_dialog_cls,
            patch("src.modules.clientes.forms._upload.threading.Thread"),
            patch("src.modules.clientes.forms._upload.os.path.getsize", return_value=0),
        ):
            mock_dialog_cls.return_value = MagicMock()

            perform_uploads(mock_self, {"id": 1}, {}, [], None)

            # Dialog criada com total_files=1 (não 0)
            call_args = mock_dialog_cls.call_args
            if call_args[0][1] < 1:
                pytest.fail("total_files deveria ser no mínimo 1")


class TestWorkerCopyExceptions:
    """Linhas 170-173: exception handling ao copiar arquivos."""

    def test_worker_copy_exception_is_logged(self):
        """Exception em shutil.copy2 é capturada e logged (linha 171)."""
        mock_self = MagicMock()
        ctx = UploadCtx(app=mock_self, row={"id": 1}, ents={}, arquivos_selecionados=["doc.pdf"], win=None)
        ctx.abort = False
        tmpdir = tempfile.gettempdir()
        src_dir = os.path.join(tmpdir, "src")
        ctx.files = [(os.path.join(src_dir, "doc.pdf"), "doc.pdf")]
        ctx.client_id = 123
        ctx.org_id = "org456"
        ctx.bucket = "test-bucket"
        ctx.pasta_local = "/base"
        ctx.subpasta = None
        ctx.src_dir = src_dir
        mock_self._upload_ctx = ctx

        worker_func = None

        def capture_worker(*args, **kwargs):
            nonlocal worker_func
            worker_func = kwargs.get("target")
            return MagicMock()

        with (
            patch("src.modules.clientes.forms._upload.UploadProgressDialog") as mock_dialog_cls,
            patch("src.modules.clientes.forms._upload.threading.Thread", side_effect=capture_worker),
            patch("src.modules.clientes.forms._upload.os.path.getsize", return_value=1024),
            patch("src.modules.clientes.forms._upload.CLOUD_ONLY", False),
            patch("src.modules.clientes.forms._upload.os.makedirs"),
            patch("src.modules.clientes.forms._upload.shutil.copy2", side_effect=OSError("Disk full")),
            patch("src.modules.clientes.forms._upload.logger") as mock_logger,
            patch("src.modules.clientes.forms._upload.using_storage_backend") as mock_backend,
        ):
            mock_backend.return_value.__enter__ = MagicMock(return_value=None)
            mock_backend.return_value.__exit__ = MagicMock(return_value=False)

            mock_dialog_cls.return_value = MagicMock()

            perform_uploads(mock_self, {"id": 1}, {}, [], None)

            if worker_func is None:
                pytest.fail("worker_func não deveria ser None")
            worker_func()

            # Verifica que exception foi logged
            debug_calls = [str(c) for c in mock_logger.debug.call_args_list]
            if not any("Falha ao copiar arquivo local" in c for c in debug_calls):
                pytest.fail("esperado log de 'Falha ao copiar arquivo local'")
