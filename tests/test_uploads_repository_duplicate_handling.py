# -*- coding: utf-8 -*-
"""Testes para tratamento de duplicatas no repositório de uploads.

Verifica que:
- 409 Duplicate -> UploadDuplicateError no failures, NÃO contado como ok
- 400 "already exists" -> UploadDuplicateError no failures, NÃO contado como ok
- 500 -> UploadServerError no failures (não duplicata)
- Sucesso -> ok += 1, failures vazio
- overwrite=False não passa upsert=True ao adapter (por padrão)
- overwrite=True passa upsert=True ao adapter
"""

import unittest
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

from src.modules.uploads.exceptions import (
    UploadDuplicateError,
    UploadServerError,
    make_server_error,
)
from src.modules.uploads.repository import (
    build_storage_adapter,
    upload_items_with_adapter,
)

_MOD = "src.modules.uploads.repository"
_RET_MOD = "src.modules.uploads.upload_retry"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_item(path: str = "/tmp/doc.pdf", relative_path: str = "doc.pdf") -> SimpleNamespace:
    return SimpleNamespace(path=path, relative_path=relative_path)


def _make_adapter(bucket: str = "rc-docs") -> MagicMock:
    adapter = MagicMock()
    adapter.bucket = bucket
    return adapter


def _remote_path_builder(cnpj: str, rel: str, sub: str | None, **kw: object) -> str:
    return f"org/{cnpj}/{sub or 'root'}/{rel}"


# ---------------------------------------------------------------------------
# Testes para make_server_error / UploadDuplicateError
# ---------------------------------------------------------------------------


class TestMakeServerError(unittest.TestCase):
    """Verifica que make_server_error retorna o tipo correto."""

    def test_duplicate_retorna_upload_duplicate_error(self):
        exc = make_server_error("duplicate")
        self.assertIsInstance(exc, UploadDuplicateError)

    def test_server_retorna_upload_server_error(self):
        exc = make_server_error("server")
        self.assertIsInstance(exc, UploadServerError)
        self.assertNotIsInstance(exc, UploadDuplicateError)

    def test_permission_retorna_upload_server_error(self):
        exc = make_server_error("permission")
        self.assertIsInstance(exc, UploadServerError)
        self.assertNotIsInstance(exc, UploadDuplicateError)

    def test_duplicate_mensagem_clara(self):
        exc = make_server_error("duplicate")
        self.assertIn("destino", str(exc).lower())

    def test_duplicate_e_subclasse_de_upload_server_error(self):
        """UploadDuplicateError deve ser capturável como UploadServerError."""
        exc = make_server_error("duplicate")
        self.assertIsInstance(exc, UploadServerError)


# ---------------------------------------------------------------------------
# Testes para upload_items_with_adapter
# ---------------------------------------------------------------------------


class TestUploadItemsWithAdapterDuplicates(unittest.TestCase):
    """Verifica comportamento de duplicatas no lote de uploads."""

    def _run_with_upload_side_effect(self, side_effect, items=None):
        """Abstrai a execução com mock de upload_with_retry."""
        if items is None:
            items = [_make_item()]
        adapter = _make_adapter()

        with patch(f"{_MOD}.upload_with_retry", side_effect=side_effect):
            return upload_items_with_adapter(
                adapter,
                items,
                cnpj_digits="12345678000190",
                subfolder=None,
                remote_path_builder=_remote_path_builder,
            )

    # --- 409 Duplicate ---

    def test_409_duplicate_nao_contado_como_ok(self):
        """409 Duplicate deve resultar em ok=0."""
        exc = RuntimeError("409 Duplicate")
        ok, failures = self._run_with_upload_side_effect(exc)
        self.assertEqual(ok, 0)

    def test_409_duplicate_registrado_em_failures_como_upload_duplicate_error(self):
        """409 Duplicate deve aparecer em failures como UploadDuplicateError."""
        exc = RuntimeError("409 Duplicate")
        ok, failures = self._run_with_upload_side_effect(exc)
        self.assertEqual(len(failures), 1)
        _, err = failures[0]
        self.assertIsInstance(err, UploadDuplicateError)

    def test_409_mensagem_user_friendly(self):
        """UploadDuplicateError em failures deve ter mensagem clara."""
        exc = RuntimeError("409 Duplicate")
        _, failures = self._run_with_upload_side_effect(exc)
        _, err = failures[0]
        self.assertIn("destino", str(err).lower())

    # --- 400 "already exists" ---

    def test_400_already_exists_nao_contado_como_ok(self):
        """400 'already exists' deve resultar em ok=0."""
        exc = RuntimeError("400 Asset already exists")
        ok, failures = self._run_with_upload_side_effect(exc)
        self.assertEqual(ok, 0)

    def test_400_already_exists_registrado_como_duplicate_error(self):
        """400 'already exists' deve aparecer em failures como UploadDuplicateError."""
        exc = RuntimeError("400 Asset already exists")
        ok, failures = self._run_with_upload_side_effect(exc)
        self.assertEqual(len(failures), 1)
        _, err = failures[0]
        self.assertIsInstance(err, UploadDuplicateError)

    def test_400_conflict_registrado_como_duplicate_error(self):
        """400 'conflict' deve ser classificado como UploadDuplicateError."""
        exc = RuntimeError("400 conflict")
        ok, failures = self._run_with_upload_side_effect(exc)
        _, err = failures[0]
        self.assertIsInstance(err, UploadDuplicateError)

    # --- 500 Server Error ---

    def test_500_classificado_como_server_error_nao_duplicate(self):
        """500 deve aparecer em failures como UploadServerError, não UploadDuplicateError."""
        exc = RuntimeError("500 Internal Server Error")
        ok, failures = self._run_with_upload_side_effect(exc)
        self.assertEqual(ok, 0)
        self.assertEqual(len(failures), 1)
        _, err = failures[0]
        self.assertIsInstance(err, UploadServerError)
        self.assertNotIsInstance(err, UploadDuplicateError)

    # --- Sucesso ---

    def test_sucesso_contado_em_ok(self):
        """Upload bem-sucedido deve incrementar ok e não gerar failures."""
        ok, failures = self._run_with_upload_side_effect(None)  # sem exceção
        self.assertEqual(ok, 1)
        self.assertEqual(failures, [])

    # --- Mix de itens ---

    def test_mix_sucesso_e_duplicata(self):
        """Batch com 1 sucesso e 1 duplicata: ok=1, failures=[duplicate]."""
        items = [_make_item("/tmp/a.pdf", "a.pdf"), _make_item("/tmp/b.pdf", "b.pdf")]
        adapter = _make_adapter()
        call_count = {"n": 0}

        def side_effect(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise RuntimeError("409 Duplicate")

        with patch(f"{_MOD}.upload_with_retry", side_effect=side_effect):
            ok, failures = upload_items_with_adapter(
                adapter,
                items,
                "12345678000190",
                None,
                remote_path_builder=_remote_path_builder,
            )

        self.assertEqual(ok, 1)
        self.assertEqual(len(failures), 1)
        _, err = failures[0]
        self.assertIsInstance(err, UploadDuplicateError)

    def test_mix_sucesso_e_falha_real(self):
        """Batch com 1 sucesso e 1 falha de rede: ok=1, failures=[network_error]."""
        items = [_make_item("/tmp/a.pdf", "a.pdf"), _make_item("/tmp/b.pdf", "b.pdf")]
        adapter = _make_adapter()
        call_count = {"n": 0}

        def side_effect(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise ConnectionError("network unreachable")

        with patch(f"{_MOD}.upload_with_retry", side_effect=side_effect):
            ok, failures = upload_items_with_adapter(
                adapter,
                items,
                "12345678000190",
                None,
                remote_path_builder=_remote_path_builder,
            )

        self.assertEqual(ok, 1)
        self.assertEqual(len(failures), 1)
        _, err = failures[0]
        self.assertNotIsInstance(err, UploadDuplicateError)

    def test_duplicata_nao_e_contada_em_ok_mesmo_com_upload_duplicate_error_direto(self):
        """Se upload_with_retry levanta UploadDuplicateError diretamente, também não conta como ok."""
        exc = UploadDuplicateError("Arquivo já existe no destino; upload ignorado.", detail="duplicate | HTTP 409")
        ok, failures = self._run_with_upload_side_effect(exc)
        self.assertEqual(ok, 0)
        _, err = failures[0]
        self.assertIsInstance(err, UploadDuplicateError)


# ---------------------------------------------------------------------------
# Testes para build_storage_adapter
# ---------------------------------------------------------------------------


class TestBuildStorageAdapter(unittest.TestCase):
    """Verifica parâmetro overwrite de build_storage_adapter."""

    def _build(self, overwrite: bool) -> Any:
        with (
            patch("src.modules.uploads.repository.SupabaseStorageAdapter") as mock_adapter,
            patch("src.modules.uploads.repository.supabase", MagicMock()),
        ):
            build_storage_adapter(bucket="test-bucket", overwrite=overwrite)
            return mock_adapter.call_args

    def test_overwrite_false_por_padrao_passa_false_ao_adapter(self):
        """Padrão overwrite=False não deve usar upsert no Supabase."""
        with (
            patch("src.modules.uploads.repository.SupabaseStorageAdapter") as mock_adapter,
            patch("src.modules.uploads.repository.supabase", MagicMock()),
        ):
            build_storage_adapter(bucket="b")
            _, kwargs = mock_adapter.call_args
            self.assertFalse(kwargs.get("overwrite", False))

    def test_overwrite_true_passa_true_ao_adapter(self):
        """overwrite=True deve ser propagado ao SupabaseStorageAdapter."""
        with (
            patch("src.modules.uploads.repository.SupabaseStorageAdapter") as mock_adapter,
            patch("src.modules.uploads.repository.supabase", MagicMock()),
        ):
            build_storage_adapter(bucket="b", overwrite=True)
            _, kwargs = mock_adapter.call_args
            self.assertTrue(kwargs.get("overwrite", False))


if __name__ == "__main__":
    unittest.main()
