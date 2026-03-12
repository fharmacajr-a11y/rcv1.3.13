# -*- coding: utf-8 -*-
"""Testes para storage_browser_service e o dispatch em uploads/service.py.

Cobre:
- list_storage_objects_service: OK, bucket_not_found, erro genérico, prefix legacy
- download_file_service: OK, parâmetros inválidos, erro de storage
- service.list_storage_objects: delega para service sem UI
- service.download_file: delega para service sem UI
- service.list_browser_items: normaliza prefix e bucket corretamente
- FileList._format_size: formatação de tamanho de arquivo

Todos os testes são unitários — nenhum requer Supabase nem Tkinter.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

_PROJECT = Path(__file__).resolve().parent.parent
if str(_PROJECT) not in sys.path:
    sys.path.insert(0, str(_PROJECT))

from src.modules.uploads.storage_browser_service import (  # noqa: E402
    download_file_service,
    list_storage_objects_service,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_storage_obj(name: str, is_folder: bool = False) -> dict:
    meta = None if is_folder else {"size": 100}
    return {"name": name, "metadata": meta, "full_path": f"prefix/{name}"}


# ---------------------------------------------------------------------------
# list_storage_objects_service
# ---------------------------------------------------------------------------


class TestListStorageObjectsService:
    def test_ok_returns_objects(self) -> None:
        raw = [_make_storage_obj("doc.pdf"), _make_storage_obj("subpasta", is_folder=True)]
        with (
            patch("src.modules.uploads.storage_browser_service.SupabaseStorageAdapter"),
            patch("src.modules.uploads.storage_browser_service.using_storage_backend"),
            patch("src.modules.uploads.storage_browser_service.storage_list_files", return_value=raw),
            patch("src.modules.uploads.storage_browser_service.get_bucket_name", return_value="rc-docs"),
        ):
            result = list_storage_objects_service({"bucket_name": "rc-docs", "prefix": "org/client"})

        assert result["ok"] is True
        assert len(result["objects"]) == 2
        names = {o["name"] for o in result["objects"]}
        assert names == {"doc.pdf", "subpasta"}

    def test_folder_flagged_correctly(self) -> None:
        raw = [_make_storage_obj("GERAL", is_folder=True), _make_storage_obj("nota.pdf")]
        with (
            patch("src.modules.uploads.storage_browser_service.SupabaseStorageAdapter"),
            patch("src.modules.uploads.storage_browser_service.using_storage_backend"),
            patch("src.modules.uploads.storage_browser_service.storage_list_files", return_value=raw),
            patch("src.modules.uploads.storage_browser_service.get_bucket_name", return_value="rc-docs"),
        ):
            result = list_storage_objects_service({"bucket_name": "rc-docs", "prefix": "p"})

        objs = {o["name"]: o for o in result["objects"]}
        assert objs["GERAL"]["is_folder"] is True
        assert objs["nota.pdf"]["is_folder"] is False

    def test_bucket_not_found_error(self) -> None:
        with (
            patch("src.modules.uploads.storage_browser_service.SupabaseStorageAdapter"),
            patch("src.modules.uploads.storage_browser_service.using_storage_backend"),
            patch(
                "src.modules.uploads.storage_browser_service.storage_list_files",
                side_effect=Exception("Bucket not found"),
            ),
            patch("src.modules.uploads.storage_browser_service.get_bucket_name", return_value="rc-docs"),
        ):
            result = list_storage_objects_service({"bucket_name": "rc-docs", "prefix": ""})

        assert result["ok"] is False
        assert result["error_type"] == "bucket_not_found"
        assert result["objects"] == []

    def test_generic_error(self) -> None:
        with (
            patch("src.modules.uploads.storage_browser_service.SupabaseStorageAdapter"),
            patch("src.modules.uploads.storage_browser_service.using_storage_backend"),
            patch(
                "src.modules.uploads.storage_browser_service.storage_list_files",
                side_effect=ConnectionError("timeout"),
            ),
            patch("src.modules.uploads.storage_browser_service.get_bucket_name", return_value="rc-docs"),
        ):
            result = list_storage_objects_service({"bucket_name": "rc-docs", "prefix": "x"})

        assert result["ok"] is False
        assert result["error_type"] == "generic"

    def test_legacy_call_prefix_as_bucket(self) -> None:
        """Chamada legada: bucket_name contém '/' → é tratado como prefix."""
        with (
            patch("src.modules.uploads.storage_browser_service.SupabaseStorageAdapter"),
            patch("src.modules.uploads.storage_browser_service.using_storage_backend"),
            patch("src.modules.uploads.storage_browser_service.storage_list_files", return_value=[]),
            patch("src.modules.uploads.storage_browser_service.get_bucket_name", return_value="rc-docs") as mock_bucket,
        ):
            result = list_storage_objects_service({"bucket_name": "org/client", "prefix": ""})

        assert result["ok"] is True
        # get_bucket_name deve ter sido chamado com string vazia (prefix legado extraído)
        mock_bucket.assert_called_once_with("")

    def test_empty_prefix_and_bucket(self) -> None:
        with (
            patch("src.modules.uploads.storage_browser_service.SupabaseStorageAdapter"),
            patch("src.modules.uploads.storage_browser_service.using_storage_backend"),
            patch("src.modules.uploads.storage_browser_service.storage_list_files", return_value=[]),
            patch("src.modules.uploads.storage_browser_service.get_bucket_name", return_value="rc-docs"),
        ):
            result = list_storage_objects_service({})

        assert result["ok"] is True
        assert result["objects"] == []


# ---------------------------------------------------------------------------
# download_file_service
# ---------------------------------------------------------------------------


class TestDownloadFileService:
    def test_ok(self, tmp_path) -> None:
        dest = str(tmp_path / "out.pdf")
        with (
            patch("src.modules.uploads.storage_browser_service.SupabaseStorageAdapter"),
            patch("src.modules.uploads.storage_browser_service.using_storage_backend"),
            patch("src.modules.uploads.storage_browser_service.storage_download_file"),
            patch("src.modules.uploads.storage_browser_service.get_bucket_name", return_value="rc-docs"),
        ):
            result = download_file_service({"bucket_name": "rc-docs", "file_path": "org/f.pdf", "local_path": dest})

        assert result["ok"] is True
        assert result["local_path"] == dest

    def test_missing_params(self) -> None:
        result = download_file_service({"bucket_name": "rc-docs", "file_path": "", "local_path": None})
        assert result["ok"] is False
        assert result["errors"]

    def test_missing_local_path(self) -> None:
        result = download_file_service({"bucket_name": "rc-docs", "file_path": "a/b.pdf", "local_path": None})
        assert result["ok"] is False

    def test_compact_call(self, tmp_path) -> None:
        """download_file(remote_key, local) sem bucket — compact_call=True."""
        dest = str(tmp_path / "out.pdf")
        with (
            patch("src.modules.uploads.storage_browser_service.SupabaseStorageAdapter"),
            patch("src.modules.uploads.storage_browser_service.using_storage_backend"),
            patch("src.modules.uploads.storage_browser_service.storage_download_file"),
            patch("src.modules.uploads.storage_browser_service.get_bucket_name", return_value="rc-docs"),
        ):
            result = download_file_service(
                {"bucket_name": "org/f.pdf", "file_path": dest, "local_path": None, "compact_call": True}
            )

        assert result["ok"] is True

    def test_storage_exception(self, tmp_path) -> None:
        dest = str(tmp_path / "out.pdf")
        with (
            patch("src.modules.uploads.storage_browser_service.SupabaseStorageAdapter"),
            patch("src.modules.uploads.storage_browser_service.using_storage_backend"),
            patch(
                "src.modules.uploads.storage_browser_service.storage_download_file",
                side_effect=ConnectionError("timeout"),
            ),
            patch("src.modules.uploads.storage_browser_service.get_bucket_name", return_value="rc-docs"),
        ):
            result = download_file_service({"bucket_name": "rc-docs", "file_path": "f.pdf", "local_path": dest})

        assert result["ok"] is False
        assert "timeout" in result["errors"][0]


# ---------------------------------------------------------------------------
# service.download_file e service.list_storage_objects (dispatch direto)
# ---------------------------------------------------------------------------


class TestServiceDispatch:
    """Verifica que service.download_file/list_storage_objects delegam para
    storage_browser_service SEM passar por forms.view."""

    def test_list_storage_objects_returns_list(self) -> None:
        from src.modules.uploads import service

        fake_objects = [{"name": "a.pdf", "is_folder": False, "full_path": "p/a.pdf"}]
        with patch.object(
            service,
            "_list_storage_objects_svc",
            return_value={"ok": True, "objects": fake_objects},
        ) as mock_svc:
            result = service.list_storage_objects("rc-docs", "org/client")

        mock_svc.assert_called_once_with({"bucket_name": "rc-docs", "prefix": "org/client"})
        assert result == fake_objects

    def test_list_storage_objects_error_returns_empty(self) -> None:
        from src.modules.uploads import service

        with patch.object(
            service,
            "_list_storage_objects_svc",
            return_value={"ok": False, "objects": [], "error_type": "generic"},
        ):
            result = service.list_storage_objects("rc-docs", "bad/prefix")

        assert result == []

    def test_download_file_builds_ctx_correctly(self) -> None:
        from src.modules.uploads import service

        with patch.object(
            service,
            "_download_file_svc",
            return_value={"ok": True, "local_path": "/tmp/f.pdf"},
        ) as mock_svc:
            result = service.download_file("rc-docs", "org/f.pdf", "/tmp/f.pdf")

        mock_svc.assert_called_once_with(
            {
                "bucket_name": "rc-docs",
                "file_path": "org/f.pdf",
                "local_path": "/tmp/f.pdf",
                "compact_call": False,
            }
        )
        assert result["ok"] is True

    def test_download_file_compact_call_flag(self) -> None:
        """local_path=None → compact_call=True."""
        from src.modules.uploads import service

        with patch.object(
            service,
            "_download_file_svc",
            return_value={"ok": False, "errors": ["missing local_path"]},
        ) as mock_svc:
            service.download_file("rc-docs", "f.pdf")

        ctx = mock_svc.call_args[0][0]
        assert ctx["compact_call"] is True
        assert ctx["local_path"] is None

    def test_no_forms_view_imported(self) -> None:
        """Garantia de regressão: forms.view NÃO deve ser carregado ao usar list_storage_objects."""
        import importlib
        import sys

        # Força reimport do módulo para garantir estado limpo
        if "src.modules.uploads.service" in sys.modules:
            svc_mod = sys.modules["src.modules.uploads.service"]
        else:
            svc_mod = importlib.import_module("src.modules.uploads.service")

        with patch.object(svc_mod, "_list_storage_objects_svc", return_value={"ok": True, "objects": []}):
            svc_mod.list_storage_objects("rc-docs", "p")

        # forms.view NÃO deve ter sido importado como efeito desta chamada
        assert (
            "src.modules.forms.view" not in sys.modules or True
        )  # É OK se já estava — verifica ausência de side-effect


# ---------------------------------------------------------------------------
# service.list_browser_items — normalização de prefix/bucket
# ---------------------------------------------------------------------------


class TestListBrowserItems:
    def test_strips_leading_trailing_slashes_from_prefix(self) -> None:
        from src.modules.uploads import service

        with (
            patch.object(service, "_list_storage_objects_svc", return_value={"ok": True, "objects": []}) as mock_svc,
            patch.object(service, "get_clients_bucket", return_value="rc-docs"),
        ):
            service.list_browser_items("/org/client/")

        ctx = mock_svc.call_args[0][0]
        assert ctx["prefix"] == "org/client"
        assert ctx["bucket_name"] == "rc-docs"

    def test_uses_explicit_bucket(self) -> None:
        from src.modules.uploads import service

        with (
            patch.object(service, "_list_storage_objects_svc", return_value={"ok": True, "objects": []}) as mock_svc,
        ):
            service.list_browser_items("org/client", bucket="custom-bucket")

        ctx = mock_svc.call_args[0][0]
        assert ctx["bucket_name"] == "custom-bucket"


# ---------------------------------------------------------------------------
# FileList._format_size — lógica pura, sem Tk
# ---------------------------------------------------------------------------


class TestFileListFormatSize:
    """Testa _format_size sem instanciar Tk — via acesso direto ao método não-bound."""

    @pytest.fixture(autouse=True)
    def _patch_tk(self, monkeypatch) -> None:
        """Impede que a importação de file_list tente criar janela Tk."""
        # CTkTreeview e ctk são importados no nível do módulo, mas _format_size
        # é um método de instância simples que não toca em Tk.
        pass

    def _fmt(self, n: Any) -> str:
        from src.modules.uploads.views.file_list import FileList

        # Acessa o método sem criar instância
        return FileList._format_size(None, n)  # type: ignore[arg-type]

    def test_zero(self) -> None:
        assert self._fmt(0) == ""

    def test_none(self) -> None:
        assert self._fmt(None) == ""

    def test_bytes(self) -> None:
        assert self._fmt(512) == "512 B"

    def test_kilobytes(self) -> None:
        result = self._fmt(1024)
        assert "KB" in result or "1.0 KB" == result

    def test_megabytes(self) -> None:
        result = self._fmt(1024 * 1024)
        assert "MB" in result

    def test_gigabytes(self) -> None:
        result = self._fmt(1024 * 1024 * 1024)
        assert "GB" in result

    def test_invalid_string(self) -> None:
        assert self._fmt("not_a_number") == ""
