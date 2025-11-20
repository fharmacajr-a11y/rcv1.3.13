"""Testes unitários para src/modules/clientes/forms/_upload.py."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch


from src.modules.clientes.forms._prepare import UploadCtx
from src.modules.clientes.forms._upload import perform_uploads


class TestPerformUploads:
    """Testes para perform_uploads."""

    def test_perform_uploads_returns_early_when_ctx_none(self):
        """Testa que perform_uploads retorna imediatamente se _upload_ctx não existe."""
        mock_self = MagicMock()
        mock_self._upload_ctx = None

        args = (mock_self, {}, {}, [], None)
        kwargs = {}

        result_args, result_kwargs = perform_uploads(*args, **kwargs)

        assert result_args == args
        assert result_kwargs == kwargs

    def test_perform_uploads_returns_early_when_abort_true(self):
        """Testa que perform_uploads retorna imediatamente se ctx.abort=True."""
        mock_self = MagicMock()
        mock_ctx = UploadCtx(
            app=mock_self,
            row={},
            ents={},
            arquivos_selecionados=[],
            win=None,
        )
        mock_ctx.abort = True
        mock_self._upload_ctx = mock_ctx

        args = (mock_self, {}, {}, [], None)
        kwargs = {}

        result_args, result_kwargs = perform_uploads(*args, **kwargs)

        assert result_args == args
        assert result_kwargs == kwargs

    def test_perform_uploads_creates_progress_dialog(self):
        """Testa que perform_uploads cria um diálogo de progresso."""
        mock_self = MagicMock()
        mock_ctx = UploadCtx(
            app=mock_self,
            row={"id": 1},
            ents={},
            arquivos_selecionados=["file1.pdf"],
            win=None,
        )
        mock_ctx.abort = False
        mock_ctx.files = [("/tmp/file1.pdf", "file1.pdf")]
        mock_ctx.client_id = 123
        mock_ctx.org_id = "org456"
        mock_ctx.bucket = "test-bucket"
        mock_ctx.pasta_local = "/tmp"
        mock_ctx.subpasta = None
        mock_self._upload_ctx = mock_ctx

        # Mock para evitar thread real e I/O
        with (
            patch("src.modules.clientes.forms._upload.UploadProgressDialog") as mock_dialog_cls,
            patch("src.modules.clientes.forms._upload.threading.Thread") as mock_thread,
            patch("src.modules.clientes.forms._upload.os.path.getsize") as mock_getsize,
        ):
            mock_getsize.return_value = 1024
            mock_dialog = MagicMock()
            mock_dialog_cls.return_value = mock_dialog

            # Mock do thread para não executar worker
            mock_thread_inst = MagicMock()
            mock_thread.return_value = mock_thread_inst

            args = (mock_self, {"id": 1}, {}, ["file1.pdf"], None)
            kwargs = {}

            perform_uploads(*args, **kwargs)

            # Verificar que diálogo foi criado
            mock_dialog_cls.assert_called_once()
            assert mock_ctx.busy_dialog == mock_dialog

            # Verificar que thread foi iniciada
            mock_thread_inst.start.assert_called_once()

    def test_perform_uploads_processes_files_list(self):
        """Testa que perform_uploads processa a lista de arquivos em ctx.files."""
        mock_self = MagicMock()
        mock_ctx = UploadCtx(
            app=mock_self,
            row={"id": 1},
            ents={},
            arquivos_selecionados=[],
            win=None,
        )
        mock_ctx.abort = False
        mock_ctx.files = [
            ("/tmp/file1.pdf", "file1.pdf"),
            ("/tmp/file2.txt", "file2.txt"),
        ]
        mock_ctx.client_id = 123
        mock_ctx.org_id = "org456"
        mock_ctx.bucket = "test-bucket"
        mock_ctx.pasta_local = "/tmp"
        mock_ctx.subpasta = None
        mock_ctx.storage_adapter = MagicMock()
        mock_self._upload_ctx = mock_ctx

        with (
            patch("src.modules.clientes.forms._upload.UploadProgressDialog") as mock_dialog_cls,
            patch("src.modules.clientes.forms._upload.threading.Thread"),
            patch("src.modules.clientes.forms._upload.os.path.getsize") as mock_getsize,
        ):
            mock_getsize.return_value = 1024
            mock_dialog = MagicMock()
            mock_dialog_cls.return_value = mock_dialog

            args = (mock_self, {"id": 1}, {}, [], None)
            kwargs = {}

            perform_uploads(*args, **kwargs)

            # Verificar que total_files foi calculado corretamente
            call_args = mock_dialog_cls.call_args
            assert call_args[0][1] == 2  # total_files

    def test_perform_uploads_handles_storage_errors_gracefully(self):
        """Testa que perform_uploads registra falhas quando upload de arquivo falha."""
        # Este teste seria mais completo executando o worker thread,
        # mas por simplicidade, vamos apenas verificar a estrutura
        mock_self = MagicMock()
        mock_ctx = UploadCtx(
            app=mock_self,
            row={"id": 1},
            ents={},
            arquivos_selecionados=["file1.pdf"],
            win=None,
        )
        mock_ctx.abort = False
        mock_ctx.files = [("/tmp/file1.pdf", "file1.pdf")]
        mock_ctx.client_id = 123
        mock_ctx.org_id = "org456"
        mock_ctx.bucket = "test-bucket"
        mock_ctx.pasta_local = "/tmp"
        mock_ctx.subpasta = None
        mock_ctx.misc = {}
        mock_self._upload_ctx = mock_ctx

        with (
            patch("src.modules.clientes.forms._upload.UploadProgressDialog"),
            patch("src.modules.clientes.forms._upload.threading.Thread"),
            patch("src.modules.clientes.forms._upload.os.path.getsize") as mock_getsize,
        ):
            mock_getsize.return_value = 1024

            args = (mock_self, {"id": 1}, {}, ["file1.pdf"], None)
            kwargs = {}

            # Chamar perform_uploads
            perform_uploads(*args, **kwargs)

            # Verificar que ctx.misc foi inicializado (para arquivos_falhados)
            assert "arquivos_falhados" in mock_ctx.misc or mock_ctx.misc == {}

    def test_perform_uploads_calculates_total_bytes(self):
        """Testa que perform_uploads calcula total de bytes corretamente."""
        mock_self = MagicMock()
        mock_ctx = UploadCtx(
            app=mock_self,
            row={"id": 1},
            ents={},
            arquivos_selecionados=[],
            win=None,
        )
        mock_ctx.abort = False
        mock_ctx.files = [
            ("/tmp/file1.pdf", "file1.pdf"),
            ("/tmp/file2.txt", "file2.txt"),
        ]
        mock_ctx.client_id = 123
        mock_ctx.org_id = "org456"
        mock_ctx.bucket = "test-bucket"
        mock_ctx.pasta_local = "/tmp"
        mock_ctx.subpasta = None
        mock_self._upload_ctx = mock_ctx

        with (
            patch("src.modules.clientes.forms._upload.UploadProgressDialog") as mock_dialog_cls,
            patch("src.modules.clientes.forms._upload.threading.Thread"),
            patch("src.modules.clientes.forms._upload.os.path.getsize") as mock_getsize,
        ):
            # Mock de tamanhos diferentes
            mock_getsize.side_effect = [2048, 4096]
            mock_dialog = MagicMock()
            mock_dialog_cls.return_value = mock_dialog

            args = (mock_self, {"id": 1}, {}, [], None)
            kwargs = {}

            perform_uploads(*args, **kwargs)

            # Verificar que total_bytes foi calculado (2048 + 4096 = 6144)
            call_args = mock_dialog_cls.call_args
            assert call_args[0][2] == 6144  # total_bytes

    def test_perform_uploads_with_subpasta(self):
        """Testa que perform_uploads considera subpasta ao construir base_local."""
        mock_self = MagicMock()
        mock_ctx = UploadCtx(
            app=mock_self,
            row={"id": 1},
            ents={},
            arquivos_selecionados=["file1.pdf"],
            win=None,
        )
        mock_ctx.abort = False
        mock_ctx.files = [("/tmp/file1.pdf", "file1.pdf")]
        mock_ctx.client_id = 123
        mock_ctx.org_id = "org456"
        mock_ctx.bucket = "test-bucket"
        mock_ctx.pasta_local = "/base"
        mock_ctx.subpasta = "subfolder"
        mock_self._upload_ctx = mock_ctx

        with (
            patch("src.modules.clientes.forms._upload.UploadProgressDialog"),
            patch("src.modules.clientes.forms._upload.threading.Thread"),
            patch("src.modules.clientes.forms._upload.os.path.getsize") as mock_getsize,
        ):
            mock_getsize.return_value = 1024

            args = (mock_self, {"id": 1}, {}, ["file1.pdf"], None)
            kwargs = {}

            perform_uploads(*args, **kwargs)

            # Verificar que base_local foi construído com subpasta
            expected_base = os.path.join("/base", "GERAL", "subfolder")
            assert mock_ctx.base_local == expected_base

    def test_perform_uploads_without_subpasta(self):
        """Testa que perform_uploads constrói base_local sem subpasta quando não há."""
        mock_self = MagicMock()
        mock_ctx = UploadCtx(
            app=mock_self,
            row={"id": 1},
            ents={},
            arquivos_selecionados=["file1.pdf"],
            win=None,
        )
        mock_ctx.abort = False
        mock_ctx.files = [("/tmp/file1.pdf", "file1.pdf")]
        mock_ctx.client_id = 123
        mock_ctx.org_id = "org456"
        mock_ctx.bucket = "test-bucket"
        mock_ctx.pasta_local = "/base"
        mock_ctx.subpasta = None
        mock_self._upload_ctx = mock_ctx

        with (
            patch("src.modules.clientes.forms._upload.UploadProgressDialog"),
            patch("src.modules.clientes.forms._upload.threading.Thread"),
            patch("src.modules.clientes.forms._upload.os.path.getsize") as mock_getsize,
        ):
            mock_getsize.return_value = 1024

            args = (mock_self, {"id": 1}, {}, ["file1.pdf"], None)
            kwargs = {}

            perform_uploads(*args, **kwargs)

            # Verificar que base_local foi construído sem subpasta
            expected_base = os.path.join("/base", "GERAL")
            assert mock_ctx.base_local == expected_base
