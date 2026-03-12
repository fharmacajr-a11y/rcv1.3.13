# -*- coding: utf-8 -*-
"""Testes para o pipeline de upload multi-formato.

Cobre:
- whitelist de extensões (permitidas e rejeitadas)
- coleta de pasta com múltiplos formatos
- build_items_from_files com tipos variados
- MIME type dinâmico por extensão
- rejeição de executáveis e scripts

Estes testes são unitários e não requerem Supabase nem Tkinter.
"""

from __future__ import annotations

import mimetypes
import os
import sys
import tempfile
from pathlib import Path

# Garante que src/ está no path (conftest já faz isso, mas repetimos p/ robustez)
_PROJECT = Path(__file__).resolve().parent.parent
if str(_PROJECT) not in sys.path:
    sys.path.insert(0, str(_PROJECT))

import pytest  # noqa: E402

from src.modules.uploads.file_validator import (  # noqa: E402
    DEFAULT_ALLOWED_EXTENSIONS,
    validate_upload_file,
    validate_upload_files,
)
from src.modules.uploads.validation import (  # noqa: E402
    build_items_from_files,
    collect_allowed_items_from_folder,
    collect_pdf_items_from_folder,
    guess_mime,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ALLOWED = sorted(DEFAULT_ALLOWED_EXTENSIONS)
_DISALLOWED = [".exe", ".bat", ".sh", ".js", ".py", ".ps1", ".cmd", ".dll", ".vbs", ".rb"]


def _tmp_file(suffix: str, content: bytes = b"dummy content for test") -> Path:
    """Cria arquivo temporário com suffix e retorna o Path."""
    fd, name = tempfile.mkstemp(suffix=suffix)
    os.write(fd, content)
    os.close(fd)
    return Path(name)


def _make_fake_pdf(suffix: str = ".pdf") -> Path:
    """Cria arquivo temporário que começa com magic bytes PDF."""
    return _tmp_file(suffix, b"%PDF-1.4 fake content")


# ---------------------------------------------------------------------------
# 1. Whitelist: extensões permitidas
# ---------------------------------------------------------------------------


class TestWhitelist:
    """Verifica que DEFAULT_ALLOWED_EXTENSIONS contém exatamente os tipos esperados."""

    EXPECTED = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".jpg", ".jpeg", ".png"}

    def test_default_extensions_contains_expected(self):
        assert self.EXPECTED.issubset(
            DEFAULT_ALLOWED_EXTENSIONS
        ), f"Extensões faltando: {self.EXPECTED - DEFAULT_ALLOWED_EXTENSIONS}"

    def test_default_extensions_has_no_executables(self):
        dangerous = {".exe", ".bat", ".sh", ".ps1", ".cmd", ".vbs", ".dll", ".js", ".py"}
        overlap = dangerous & DEFAULT_ALLOWED_EXTENSIONS
        assert not overlap, f"Extensões perigosas na whitelist: {overlap}"

    @pytest.mark.parametrize("ext", [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".jpg", ".jpeg", ".png"])
    def test_each_allowed_extension(self, ext: str):
        assert ext in DEFAULT_ALLOWED_EXTENSIONS


# ---------------------------------------------------------------------------
# 2. validate_upload_file: rejeição de tipos não permitidos
# ---------------------------------------------------------------------------


class TestValidateUploadFile:
    """Testa validate_upload_file contra tipos permitidos e proibidos."""

    @pytest.mark.parametrize("ext", [".exe", ".bat", ".sh", ".js", ".py"])
    def test_rejects_dangerous_extensions(self, ext: str):
        f = _tmp_file(ext)
        try:
            result = validate_upload_file(f)
            assert not result.valid, f"Deveria rejeitar {ext!r}"
            assert "não permitida" in (result.error or "").lower() or "permitid" in (result.error or "")
        finally:
            f.unlink(missing_ok=True)

    @pytest.mark.parametrize("ext", [".doc", ".docx", ".xls", ".xlsx", ".csv"])
    def test_accepts_office_extensions(self, ext: str):
        f = _tmp_file(ext)
        try:
            result = validate_upload_file(f)
            assert result.valid, f"Deveria aceitar {ext!r}: {result.error}"
        finally:
            f.unlink(missing_ok=True)

    @pytest.mark.parametrize("ext", [".jpg", ".jpeg", ".png"])
    def test_accepts_image_extensions(self, ext: str):
        f = _tmp_file(ext)
        try:
            result = validate_upload_file(f)
            assert result.valid, f"Deveria aceitar {ext!r}: {result.error}"
        finally:
            f.unlink(missing_ok=True)

    def test_accepts_pdf(self):
        f = _make_fake_pdf()
        try:
            result = validate_upload_file(f)
            assert result.valid, f"Deveria aceitar .pdf: {result.error}"
        finally:
            f.unlink(missing_ok=True)

    def test_pdf_magic_check_only_for_pdf(self):
        """magic bytes check só deve ser aplicado a .pdf, não a Word/Excel."""
        # Arquivo .docx sem magic bytes de PDF deve ser aceito
        f = _tmp_file(".docx", b"PK\x03\x04 fake docx zip header")
        try:
            result = validate_upload_file(f, check_magic=True)
            assert result.valid, f"Deveria aceitar .docx mesmo sem magic PDF: {result.error}"
        finally:
            f.unlink(missing_ok=True)

    def test_empty_file_rejected(self):
        f = _tmp_file(".pdf", b"")
        try:
            result = validate_upload_file(f)
            assert not result.valid
            assert result.error is not None
        finally:
            f.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 3. validate_upload_files em lote
# ---------------------------------------------------------------------------


class TestValidateUploadFiles:
    def test_splits_valid_and_invalid(self):
        ok_f = _tmp_file(".pdf", b"%PDF fake")
        bad_f = _tmp_file(".exe")
        try:
            valid, invalid = validate_upload_files([ok_f, bad_f])
            assert len(valid) == 1
            assert len(invalid) == 1
            assert valid[0].path == ok_f
            assert invalid[0].path == bad_f
        finally:
            ok_f.unlink(missing_ok=True)
            bad_f.unlink(missing_ok=True)

    def test_all_valid_returns_empty_invalid(self):
        files = [_tmp_file(ext) for ext in [".pdf", ".docx", ".jpg"]]
        # injetar content PDF para o .pdf
        files[0].write_bytes(b"%PDF-1.4 fake")
        try:
            valid, invalid = validate_upload_files(files)
            assert len(invalid) == 0
            assert len(valid) == 3
        finally:
            for f in files:
                f.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 4. collect_pdf_items_from_folder / collect_allowed_items_from_folder
# ---------------------------------------------------------------------------


class TestCollectFromFolder:
    """Verifica que a coleta de pasta pega todos os tipos, não só PDF."""

    def _factory(self, path: Path, relative: str):
        return (path, relative)

    def test_collects_all_allowed_types(self, tmp_path: Path):
        extensions = [".pdf", ".docx", ".xlsx", ".csv", ".jpg", ".png"]
        for ext in extensions:
            (tmp_path / f"file{ext}").write_bytes(b"test")

        items = collect_pdf_items_from_folder(str(tmp_path), self._factory)
        collected_exts = {Path(rel).suffix.lower() for _, rel in items}
        for ext in extensions:
            assert ext in collected_exts, f"Extensão {ext!r} não foi coletada da pasta"

    def test_ignores_disallowed_types(self, tmp_path: Path):
        for ext in [".exe", ".bat", ".js"]:
            (tmp_path / f"bad{ext}").write_bytes(b"bad")
        (tmp_path / "ok.pdf").write_bytes(b"%PDF")

        items = collect_pdf_items_from_folder(str(tmp_path), self._factory)
        collected_exts = {Path(rel).suffix.lower() for _, rel in items}
        assert ".exe" not in collected_exts
        assert ".bat" not in collected_exts
        assert ".js" not in collected_exts

    def test_collects_recursively(self, tmp_path: Path):
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "doc.docx").write_bytes(b"docx")
        (tmp_path / "root.pdf").write_bytes(b"%PDF")

        items = collect_pdf_items_from_folder(str(tmp_path), self._factory)
        assert len(items) == 2

    def test_collect_allowed_alias_same_as_collect_pdf(self, tmp_path: Path):
        """Os dois nomes devem retornar o mesmo resultado."""
        (tmp_path / "a.pdf").write_bytes(b"%PDF")
        (tmp_path / "b.docx").write_bytes(b"docx")

        r1 = collect_pdf_items_from_folder(str(tmp_path), self._factory)
        r2 = collect_allowed_items_from_folder(str(tmp_path), self._factory)
        assert r1 == r2

    def test_empty_folder_returns_empty(self, tmp_path: Path):
        items = collect_pdf_items_from_folder(str(tmp_path), self._factory)
        assert items == []


# ---------------------------------------------------------------------------
# 5. build_items_from_files
# ---------------------------------------------------------------------------


class TestBuildItemsFromFiles:
    """Verifica que build_items_from_files aceita todos os tipos permitidos."""

    def _factory(self, path: Path, relative: str):
        return (path, relative)

    def test_accepts_all_allowed_types(self, tmp_path: Path):
        files = []
        for ext in [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".jpg", ".jpeg", ".png"]:
            f = tmp_path / f"file{ext}"
            f.write_bytes(b"content")
            files.append(str(f))

        items = build_items_from_files(files, self._factory)
        assert len(items) == 9, f"Esperado 9 itens, obteve {len(items)}"

    def test_rejects_disallowed_types(self, tmp_path: Path):
        allowed = tmp_path / "ok.pdf"
        allowed.write_bytes(b"%PDF")
        bad = tmp_path / "bad.exe"
        bad.write_bytes(b"MZ bad exec")

        items = build_items_from_files([str(allowed), str(bad)], self._factory)
        assert len(items) == 1
        assert items[0][0] == allowed

    def test_returns_sorted(self, tmp_path: Path):
        files = []
        for letter in ["z", "a", "m"]:
            f = tmp_path / f"{letter}.pdf"
            f.write_bytes(b"%PDF")
            files.append(str(f))

        items = build_items_from_files(files, self._factory)
        names = [Path(rel).stem for _, rel in items]
        assert names == sorted(names)


# ---------------------------------------------------------------------------
# 6. MIME type dinâmico (guess_mime)
# ---------------------------------------------------------------------------


class TestGuessMime:
    """Verifica que guess_mime retorna MIME correto para cada tipo suportado."""

    EXPECTED_MIMES = {
        ".pdf": "application/pdf",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xls": "application/vnd.ms-excel",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        # .csv: Windows (registro) pode retornar 'application/vnd.ms-excel', enquanto
        # Linux/macOS retornam 'text/csv'. Ambos são aceitáveis para upload.
        ".csv": "text/csv",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
    }
    # Mimes alternativos aceitos por plataforma (registro do Windows, etc.)
    _ALTERNATE_MIMES: dict[str, str] = {
        ".csv": "application/vnd.ms-excel",
    }

    @pytest.mark.parametrize("ext,expected", list(EXPECTED_MIMES.items()))
    def test_mime_not_hardcoded_pdf(self, ext: str, expected: str, tmp_path: Path):
        f = tmp_path / f"file{ext}"
        f.write_bytes(b"content")
        mime = guess_mime(f)
        alternate = self._ALTERNATE_MIMES.get(ext)
        assert (
            mime == expected or mime == alternate
        ), f"Para {ext!r} esperado {expected!r} (ou {alternate!r}), obteve {mime!r}"

    def test_fallback_for_unknown_extension(self, tmp_path: Path):
        f = tmp_path / "file.xyz_unknown"
        f.write_bytes(b"??")
        mime = guess_mime(f)
        assert mime == "application/octet-stream"

    def test_mimetypes_module_for_dynamic_upload(self, tmp_path: Path):
        """Simula o que repository.py faz: mimetypes.guess_type(str(path))."""
        _csv_ok = {"text/csv", "application/vnd.ms-excel"}  # aceitar ambas as plataformas
        for ext, expected in self.EXPECTED_MIMES.items():
            f = tmp_path / f"file{ext}"
            f.write_bytes(b"content")
            guessed, _ = mimetypes.guess_type(str(f))
            result = guessed or "application/octet-stream"
            alternate = self._ALTERNATE_MIMES.get(ext)
            assert (
                result == expected or result == alternate
            ), f"mimetypes direto para {ext!r}: esperado {expected!r} (ou {alternate!r}), obteve {result!r}"


# ---------------------------------------------------------------------------
# 7. RC_UPLOAD_ALLOWED_EXTENSIONS env override
# ---------------------------------------------------------------------------


class TestEnvOverride:
    """Verifica que RC_UPLOAD_ALLOWED_EXTENSIONS sobrescreve o default."""

    def test_env_override_restricts_extensions(self, monkeypatch, tmp_path: Path):
        """Se env restringir a só .pdf, .docx deve ser rejeitado."""
        monkeypatch.setenv("RC_UPLOAD_ALLOWED_EXTENSIONS", ".pdf")
        # Reimportar a função de carregamento para pegar o novo env
        from src.modules.uploads.file_validator import _load_default_allowed_extensions

        restricted = _load_default_allowed_extensions()
        assert ".pdf" in restricted
        assert ".docx" not in restricted

    def test_env_override_accepts_custom_list(self, monkeypatch):
        """Lista personalizada via env deve ser carregada corretamente."""
        monkeypatch.setenv("RC_UPLOAD_ALLOWED_EXTENSIONS", ".pdf,.png,.csv")
        from src.modules.uploads.file_validator import _load_default_allowed_extensions

        custom = _load_default_allowed_extensions()
        assert ".pdf" in custom
        assert ".png" in custom
        assert ".csv" in custom
        assert ".docx" not in custom
