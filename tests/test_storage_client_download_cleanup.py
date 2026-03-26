# pyright: reportAttributeAccessIssue=false
# -*- coding: utf-8 -*-
"""
Testes unitários para cleanup de arquivos temporários em baixar_pasta_zip()
(Fase 8 — storage_client.py).

Estratégia de isolamento:
  - Nenhuma rede real: _sess() é patchado para retornar um Mock.
  - Os chunks são simulados por um iterador in-memory.
  - O diretório de destino é um tempfile.TemporaryDirectory() real,
    descartado após cada teste.
"""

from __future__ import annotations

import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.infra.supabase.storage_client import baixar_pasta_zip, DownloadCancelledError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response(
    status_code: int = 200,
    content_type: str = "application/zip",
    chunks: list | None = None,
    content_length: str | None = None,
    raise_on_chunk: Exception | None = None,
    raise_on_chunk_index: int = 0,
) -> MagicMock:
    """Cria um mock de requests.Response compatível com uso como context manager.

    Args:
        status_code: HTTP status
        content_type: Content-Type header
        chunks: Lista de bytes para simular o stream
        content_length: Valor do cabeçalho Content-Length (opcional)
        raise_on_chunk: Exceção a lançar durante iteração de chunks
        raise_on_chunk_index: Índice do chunk onde raise é lançado
    """
    if chunks is None:
        chunks = [b"ZIPDATA_PART1", b"ZIPDATA_PART2"]

    resp = MagicMock()
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    resp.status_code = status_code

    headers = {
        "Content-Type": content_type,
        "Content-Disposition": 'attachment; filename="test.zip"',
    }
    if content_length is not None:
        headers["Content-Length"] = content_length

    resp.headers = headers
    resp.raw = MagicMock()
    resp.raw.decode_content = False

    if raise_on_chunk is not None:

        def _iter_content(chunk_size=None):
            for i, chunk in enumerate(chunks):
                if i == raise_on_chunk_index:
                    raise raise_on_chunk
                yield chunk

        resp.iter_content = _iter_content
    else:
        resp.iter_content = MagicMock(return_value=iter(chunks))

    return resp


def _make_session(resp: MagicMock) -> MagicMock:
    sess = MagicMock()
    sess.get = MagicMock(return_value=resp)
    return sess


# ---------------------------------------------------------------------------
# Cenário (a): sucesso — arquivo final existe, temp não existe
# ---------------------------------------------------------------------------


class TestDownloadSuccess(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.out_dir = Path(self.tmpdir.name)
        self._env_patcher = patch.dict(os.environ, {"SUPABASE_URL": "http://test.local"})
        self._env_patcher.start()

    def tearDown(self):
        self._env_patcher.stop()
        self.tmpdir.cleanup()

    def test_success_final_file_exists(self):
        chunks = [b"PK\x03\x04", b"FAKECONTENT"]
        resp = _make_response(chunks=chunks)
        sess = _make_session(resp)

        with (
            patch("src.infra.supabase.storage_client._sess", return_value=sess),
            patch("src.infra.supabase.storage_client.CLOUD_ONLY", False),
        ):
            result = baixar_pasta_zip(
                bucket="test-bucket",
                prefix="org/client/",
                out_dir=self.out_dir,
            )

        self.assertTrue(result.exists(), "arquivo final deve existir após sucesso")
        self.assertEqual(result.suffix, ".zip")

    def test_success_no_temp_file_remains(self):
        chunks = [b"PK\x03\x04", b"FAKECONTENT"]
        resp = _make_response(chunks=chunks)
        sess = _make_session(resp)

        with (
            patch("src.infra.supabase.storage_client._sess", return_value=sess),
            patch("src.infra.supabase.storage_client.CLOUD_ONLY", False),
        ):
            result = baixar_pasta_zip(
                bucket="test-bucket",
                prefix="org/client/",
                out_dir=self.out_dir,
            )

        temp = result.with_suffix(result.suffix + ".part")
        self.assertFalse(temp.exists(), "arquivo .part não deve existir após sucesso")

    def test_success_returns_path_in_out_dir(self):
        resp = _make_response()
        sess = _make_session(resp)

        with (
            patch("src.infra.supabase.storage_client._sess", return_value=sess),
            patch("src.infra.supabase.storage_client.CLOUD_ONLY", False),
        ):
            result = baixar_pasta_zip(
                bucket="bucket",
                prefix="a/b/",
                out_dir=self.out_dir,
            )

        self.assertEqual(result.parent, self.out_dir)

    def test_success_content_correct(self):
        data = b"PK\x03\x04ZIPBODY"
        resp = _make_response(chunks=[data])
        sess = _make_session(resp)

        with (
            patch("src.infra.supabase.storage_client._sess", return_value=sess),
            patch("src.infra.supabase.storage_client.CLOUD_ONLY", False),
        ):
            result = baixar_pasta_zip(
                bucket="bucket",
                prefix="a/b/",
                out_dir=self.out_dir,
            )

        self.assertEqual(result.read_bytes(), data)


# ---------------------------------------------------------------------------
# Cenário (b): erro no meio — final não existe, temp removido
# ---------------------------------------------------------------------------


class TestDownloadErrorMidStream(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.out_dir = Path(self.tmpdir.name)
        self._env_patcher = patch.dict(os.environ, {"SUPABASE_URL": "http://test.local"})
        self._env_patcher.start()

    def tearDown(self):
        self._env_patcher.stop()
        self.tmpdir.cleanup()

    def test_exception_during_iter_content_no_final_file(self):
        """Exceção durante iteração de chunks → arquivo final não existe."""
        exc = OSError("disk full")
        resp = _make_response(
            chunks=[b"CHUNK1", b"CHUNK2"],
            raise_on_chunk=exc,
            raise_on_chunk_index=1,
        )
        sess = _make_session(resp)

        with (
            patch("src.infra.supabase.storage_client._sess", return_value=sess),
            patch("src.infra.supabase.storage_client.CLOUD_ONLY", False),
        ):
            with self.assertRaises(OSError):
                baixar_pasta_zip(
                    bucket="bucket",
                    prefix="a/b/",
                    out_dir=self.out_dir,
                )

        # Nenhum arquivo .zip deve existir
        zips = list(self.out_dir.glob("*.zip"))
        self.assertEqual(zips, [], "arquivo final não deve existir após erro")

    def test_exception_during_iter_content_temp_removed(self):
        """Exceção durante stream → .part removido."""
        exc = RuntimeError("stream error")
        resp = _make_response(
            chunks=[b"CHUNK1", b"CHUNK2"],
            raise_on_chunk=exc,
            raise_on_chunk_index=0,
        )
        sess = _make_session(resp)

        with (
            patch("src.infra.supabase.storage_client._sess", return_value=sess),
            patch("src.infra.supabase.storage_client.CLOUD_ONLY", False),
        ):
            with self.assertRaises(RuntimeError):
                baixar_pasta_zip(
                    bucket="bucket",
                    prefix="a/b/",
                    out_dir=self.out_dir,
                )

        parts = list(self.out_dir.glob("*.part"))
        self.assertEqual(parts, [], "arquivo .part não deve existir após erro")

    def test_truncated_download_no_final_file(self):
        """Download truncado (Content-Length diferente) → final não existe."""
        data = b"SHORT"
        resp = _make_response(
            chunks=[data],
            content_length="9999",  # indica 9999 bytes, mas só escreveu 5
        )
        sess = _make_session(resp)

        with (
            patch("src.infra.supabase.storage_client._sess", return_value=sess),
            patch("src.infra.supabase.storage_client.CLOUD_ONLY", False),
        ):
            with self.assertRaises(IOError):
                baixar_pasta_zip(
                    bucket="bucket",
                    prefix="a/b/",
                    out_dir=self.out_dir,
                )

        zips = list(self.out_dir.glob("*.zip"))
        self.assertEqual(zips, [])

    def test_truncated_download_temp_removed(self):
        """Download truncado → .part removido."""
        data = b"SHORT"
        resp = _make_response(chunks=[data], content_length="9999")
        sess = _make_session(resp)

        with (
            patch("src.infra.supabase.storage_client._sess", return_value=sess),
            patch("src.infra.supabase.storage_client.CLOUD_ONLY", False),
        ):
            with self.assertRaises(IOError):
                baixar_pasta_zip(
                    bucket="bucket",
                    prefix="a/b/",
                    out_dir=self.out_dir,
                )

        parts = list(self.out_dir.glob("*.part"))
        self.assertEqual(parts, [])


# ---------------------------------------------------------------------------
# Cenário (c): erro antes de escrever — temp removido
# ---------------------------------------------------------------------------


class TestDownloadErrorBeforeWrite(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.out_dir = Path(self.tmpdir.name)
        self._env_patcher = patch.dict(os.environ, {"SUPABASE_URL": "http://test.local"})
        self._env_patcher.start()

    def tearDown(self):
        self._env_patcher.stop()
        self.tmpdir.cleanup()

    def test_empty_chunks_with_length_mismatch_temp_removed(self):
        """Nenhum chunk escrito + Content-Length!=0 → temp removido."""
        resp = _make_response(chunks=[], content_length="100")
        sess = _make_session(resp)

        with (
            patch("src.infra.supabase.storage_client._sess", return_value=sess),
            patch("src.infra.supabase.storage_client.CLOUD_ONLY", False),
        ):
            with self.assertRaises(IOError):
                baixar_pasta_zip(
                    bucket="bucket",
                    prefix="a/b/",
                    out_dir=self.out_dir,
                )

        all_temp = list(self.out_dir.iterdir())
        # Pode restar o arquivo final (não existe) mas nenhum .part
        parts = [f for f in all_temp if f.suffix == ".part"]
        self.assertEqual(parts, [])

    def test_first_chunk_raises_temp_removed(self):
        """Exceção no primeiro chunk (antes de escrever qualquer byte) → temp removido."""
        exc = ConnectionError("server dropped")
        resp = _make_response(
            chunks=[b"DATA"],
            raise_on_chunk=exc,
            raise_on_chunk_index=0,
        )
        sess = _make_session(resp)

        with (
            patch("src.infra.supabase.storage_client._sess", return_value=sess),
            patch("src.infra.supabase.storage_client.CLOUD_ONLY", False),
        ):
            with self.assertRaises(Exception):
                baixar_pasta_zip(
                    bucket="bucket",
                    prefix="a/b/",
                    out_dir=self.out_dir,
                )

        parts = list(self.out_dir.glob("*.part"))
        self.assertEqual(parts, [])


# ---------------------------------------------------------------------------
# Cenário (d): cancelamento via cancel_event — temp removido
# ---------------------------------------------------------------------------


class TestDownloadCancellation(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.out_dir = Path(self.tmpdir.name)
        self._env_patcher = patch.dict(os.environ, {"SUPABASE_URL": "http://test.local"})
        self._env_patcher.start()

    def tearDown(self):
        self._env_patcher.stop()
        self.tmpdir.cleanup()

    def _chunks_with_cancel(self, cancel_event: threading.Event):
        yield b"CHUNK1"
        cancel_event.set()
        yield b"CHUNK2"

    def test_cancel_mid_stream_raises(self):
        cancel = threading.Event()
        resp = _make_response(chunks=[b"C1", b"C2"])
        resp.iter_content = MagicMock(return_value=self._chunks_with_cancel(cancel))
        sess = _make_session(resp)

        with (
            patch("src.infra.supabase.storage_client._sess", return_value=sess),
            patch("src.infra.supabase.storage_client.CLOUD_ONLY", False),
        ):
            with self.assertRaises(DownloadCancelledError):
                baixar_pasta_zip(
                    bucket="bucket",
                    prefix="a/b/",
                    out_dir=self.out_dir,
                    cancel_event=cancel,
                )

    def test_cancel_mid_stream_temp_removed(self):
        cancel = threading.Event()
        resp = _make_response(chunks=[b"C1", b"C2"])
        resp.iter_content = MagicMock(return_value=self._chunks_with_cancel(cancel))
        sess = _make_session(resp)

        with (
            patch("src.infra.supabase.storage_client._sess", return_value=sess),
            patch("src.infra.supabase.storage_client.CLOUD_ONLY", False),
        ):
            with self.assertRaises(DownloadCancelledError):
                baixar_pasta_zip(
                    bucket="bucket",
                    prefix="a/b/",
                    out_dir=self.out_dir,
                    cancel_event=cancel,
                )

        parts = list(self.out_dir.glob("*.part"))
        self.assertEqual(parts, [], ".part deve ser removido ao cancelar")

    def test_cancel_mid_stream_no_final_file(self):
        cancel = threading.Event()
        resp = _make_response(chunks=[b"C1", b"C2"])
        resp.iter_content = MagicMock(return_value=self._chunks_with_cancel(cancel))
        sess = _make_session(resp)

        with (
            patch("src.infra.supabase.storage_client._sess", return_value=sess),
            patch("src.infra.supabase.storage_client.CLOUD_ONLY", False),
        ):
            with self.assertRaises(DownloadCancelledError):
                baixar_pasta_zip(
                    bucket="bucket",
                    prefix="a/b/",
                    out_dir=self.out_dir,
                    cancel_event=cancel,
                )

        zips = list(self.out_dir.glob("*.zip"))
        self.assertEqual(zips, [], "arquivo final não deve existir após cancelamento")


if __name__ == "__main__":
    unittest.main()
