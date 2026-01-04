"""
TESTE_1 - infra/archive_utils

Objetivo: aumentar a cobertura de infra/archive_utils.py na fase 52,
cobrindo detecção de formatos, localização de 7z e extração de ZIP/RAR/7Z com erros e bordas.
"""

from __future__ import annotations

import types
import zipfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import src.infra.archive_utils as archive_utils


def test_is_supported_archive_cobre_formats():
    assert archive_utils.is_supported_archive("file.zip")
    assert archive_utils.is_supported_archive("file.rar")
    assert archive_utils.is_supported_archive("file.7z")
    assert archive_utils.is_supported_archive("file.7z.001")
    assert not archive_utils.is_supported_archive("file.tar")


def test_resource_path_usa_meipass(monkeypatch):
    monkeypatch.setattr(archive_utils, "sys", types.SimpleNamespace(_MEIPASS=Path("/tmp/app")))
    result = archive_utils.resource_path("a", "b")
    assert result == Path("/tmp/app/a/b")


def test_find_7z_retornando_none(monkeypatch):
    monkeypatch.setattr(archive_utils, "resource_path", lambda *a: Path("/nope"))
    monkeypatch.setattr(archive_utils.shutil, "which", lambda name: None)
    assert archive_utils.find_7z() is None


def test_find_7z_encontra_no_path(monkeypatch):
    monkeypatch.setattr(archive_utils, "resource_path", lambda *a: Path("/nope"))
    monkeypatch.setattr(archive_utils.shutil, "which", lambda name: "/usr/bin/7z")
    assert archive_utils.find_7z() == Path("/usr/bin/7z")


def test_extract_archive_zip_caminho_feliz(tmp_path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "a.txt").write_text("hello")
    zip_path = tmp_path / "file.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(src_dir / "a.txt", arcname="a.txt")

    out_dir = tmp_path / "out"
    result = archive_utils.extract_archive(zip_path, out_dir)

    assert result == out_dir
    assert (out_dir / "a.txt").read_text() == "hello"


def test_extract_archive_zip_corrompido(tmp_path):
    bad_zip = tmp_path / "bad.zip"
    bad_zip.write_bytes(b"not zip")
    with pytest.raises(archive_utils.ArchiveError):
        archive_utils.extract_archive(bad_zip, tmp_path / "out")


def test_extract_archive_rar_sem_7z(monkeypatch, tmp_path):
    rar = tmp_path / "file.rar"
    rar.write_bytes(b"fake")
    monkeypatch.setattr(archive_utils, "find_7z", lambda: None)
    with pytest.raises(archive_utils.ArchiveError):
        archive_utils.extract_archive(rar, tmp_path / "out")


def test_extract_archive_rar_com_erro_de_execucao(monkeypatch, tmp_path):
    rar = tmp_path / "file.rar"
    rar.write_bytes(b"fake")
    monkeypatch.setattr(archive_utils, "find_7z", lambda: Path("/bin/7z"))
    proc = MagicMock(returncode=1, stderr="erro", stdout="saida")
    monkeypatch.setattr(archive_utils.subprocess, "run", lambda *a, **k: proc)
    with pytest.raises(archive_utils.ArchiveError):
        archive_utils.extract_archive(rar, tmp_path / "out")


def test_extract_archive_rar_caminho_feliz(monkeypatch, tmp_path):
    rar = tmp_path / "file.rar"
    rar.write_bytes(b"fake")
    monkeypatch.setattr(archive_utils, "find_7z", lambda: Path("/bin/7z"))
    proc = MagicMock(returncode=0, stderr="", stdout="")
    monkeypatch.setattr(archive_utils.subprocess, "run", lambda *a, **k: proc)
    out_dir = tmp_path / "out"
    result = archive_utils.extract_archive(rar, out_dir)
    assert result == out_dir


def test_extract_archive_7z_importerror(monkeypatch, tmp_path):
    seven = tmp_path / "file.7z"
    seven.write_bytes(b"fake")
    monkeypatch.setitem(sys_modules := archive_utils.sys.modules, "py7zr", None)
    with pytest.raises(archive_utils.ArchiveError):
        archive_utils.extract_archive(seven, tmp_path / "out")
    sys_modules.pop("py7zr", None)


def test_extract_archive_7z_badfile(monkeypatch, tmp_path):
    seven = tmp_path / "file.7z"
    seven.write_bytes(b"fake")
    fake_py7zr = types.SimpleNamespace(
        Bad7zFile=type("Bad7zFile", (Exception,), {}),
        SevenZipFile=MagicMock(),
    )

    def raise_bad(*a, **k):
        raise fake_py7zr.Bad7zFile("bad")

    fake_py7zr.SevenZipFile.return_value.__enter__.return_value = MagicMock(extractall=raise_bad)
    monkeypatch.setitem(archive_utils.sys.modules, "py7zr", fake_py7zr)
    with pytest.raises(archive_utils.ArchiveError):
        archive_utils.extract_archive(seven, tmp_path / "out")
    archive_utils.sys.modules.pop("py7zr", None)


def test_extract_archive_7z_feliz(monkeypatch, tmp_path):
    seven = tmp_path / "file.7z"
    seven.write_bytes(b"fake")
    extracted = {"called": False}

    class FakeContext:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def extractall(self, path=None):
            extracted["called"] = True

    fake_py7zr = types.SimpleNamespace(
        Bad7zFile=type("Bad7zFile", (Exception,), {}),
        SevenZipFile=lambda *a, **k: FakeContext(),
    )
    monkeypatch.setitem(archive_utils.sys.modules, "py7zr", fake_py7zr)
    out = tmp_path / "out"
    result = archive_utils.extract_archive(seven, out)
    assert result == out
    assert extracted["called"] is True
    archive_utils.sys.modules.pop("py7zr", None)


def test_extract_archive_formato_nao_suportado(tmp_path):
    other = tmp_path / "file.txt"
    other.write_text("x")
    with pytest.raises(archive_utils.ArchiveError):
        archive_utils.extract_archive(other, tmp_path / "out")


def test_is_7z_available(monkeypatch):
    monkeypatch.setattr(archive_utils, "find_7z", lambda: Path("/bin/7z"))
    assert archive_utils.is_7z_available() is True
