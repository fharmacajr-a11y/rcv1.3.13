"""Testes unitários para validação de arquivos (OWASP).

FASE 7 - Cobertura de:
- Validação de extensão (whitelist)
- Validação de tamanho
- Validação de arquivo legível
- Validação de magic bytes (PDF)
- Função validate_upload_files para lotes
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

import src.modules.uploads.file_validator as file_validator_module
from src.modules.uploads.file_validator import (
    ALLOWED_EXTENSIONS,
    MAX_SIZE_BYTES,
    PDF_MAGIC,
    FileValidationResult,
    validate_upload_file,
    validate_upload_file_strict,
    validate_upload_files,
)
from src.modules.uploads.exceptions import UploadValidationError


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def valid_pdf(tmp_path: Path) -> Path:
    """Cria um PDF válido para teste."""
    pdf_file = tmp_path / "documento.pdf"
    pdf_file.write_bytes(PDF_MAGIC + b"-1.4\n%test content")
    return pdf_file


@pytest.fixture
def invalid_extension_file(tmp_path: Path) -> Path:
    """Cria arquivo com extensão não permitida."""
    exe_file = tmp_path / "programa.exe"
    exe_file.write_bytes(b"MZ\x90\x00")  # Magic bytes de EXE
    return exe_file


@pytest.fixture
def oversized_file(tmp_path: Path) -> Path:
    """Cria arquivo muito grande (simula via tamanho mínimo)."""
    big_file = tmp_path / "grande.pdf"
    # Vamos testar com limite baixo, não criar arquivo gigante
    big_file.write_bytes(PDF_MAGIC + b"x" * 1000)
    return big_file


@pytest.fixture
def empty_file(tmp_path: Path) -> Path:
    """Cria arquivo vazio."""
    empty = tmp_path / "vazio.pdf"
    empty.write_bytes(b"")
    return empty


@pytest.fixture
def fake_pdf(tmp_path: Path) -> Path:
    """Cria arquivo .pdf com conteúdo não-PDF."""
    fake = tmp_path / "falso.pdf"
    fake.write_bytes(b"Este nao e um PDF")
    return fake


# ============================================================================
# Testes de validação individual
# ============================================================================


class TestValidateUploadFile:
    """Testes para validate_upload_file."""

    def test_valid_pdf_passes(self, valid_pdf: Path) -> None:
        result = validate_upload_file(valid_pdf)

        assert result.valid is True
        assert result.path == valid_pdf
        assert result.extension == ".pdf"
        assert result.size_bytes > 0
        assert result.error is None

    def test_invalid_extension_fails(self, invalid_extension_file: Path) -> None:
        result = validate_upload_file(invalid_extension_file)

        assert result.valid is False
        error_message = result.error
        assert error_message is not None
        normalized_error = error_message.lower()
        assert ".exe" in normalized_error or "não permitida" in normalized_error

    def test_custom_allowed_extensions(self, tmp_path: Path) -> None:
        txt_file = tmp_path / "doc.txt"
        txt_file.write_text("conteudo")

        # Sem whitelist customizada: falha
        result_default = validate_upload_file(txt_file)
        assert result_default.valid is False

        # Com whitelist customizada: passa
        result_custom = validate_upload_file(txt_file, allowed_extensions=frozenset({".txt"}))
        assert result_custom.valid is True

    def test_empty_file_fails(self, empty_file: Path) -> None:
        result = validate_upload_file(empty_file)

        assert result.valid is False
        error_message = result.error
        assert error_message is not None
        assert "vazio" in error_message.lower()

    def test_oversized_file_fails(self, valid_pdf: Path) -> None:
        # Testar com limite muito baixo
        result = validate_upload_file(valid_pdf, max_size_bytes=5)

        assert result.valid is False
        error_message = result.error
        assert error_message is not None
        normalized_error = error_message.lower()
        assert "grande" in normalized_error or "máximo" in normalized_error

    def test_nonexistent_file_fails(self, tmp_path: Path) -> None:
        missing = tmp_path / "nao_existe.pdf"
        result = validate_upload_file(missing)

        assert result.valid is False
        error_message = result.error
        assert error_message is not None
        normalized_error = error_message.lower()
        assert "não encontrado" in normalized_error or "encontrado" in normalized_error

    def test_directory_fails(self, tmp_path: Path) -> None:
        result = validate_upload_file(tmp_path)

        assert result.valid is False
        error_message = result.error
        assert error_message is not None
        normalized_error = error_message.lower()
        assert "não é um arquivo" in normalized_error or "válido" in normalized_error

    def test_fake_pdf_fails_magic_check(self, fake_pdf: Path) -> None:
        result = validate_upload_file(fake_pdf, check_magic=True)

        assert result.valid is False
        error_message = result.error
        assert error_message is not None
        assert "pdf válido" in error_message.lower()

    def test_fake_pdf_passes_without_magic_check(self, fake_pdf: Path) -> None:
        result = validate_upload_file(fake_pdf, check_magic=False)

        # Deve passar se magic check desabilitado
        assert result.valid is True

    def test_accepts_string_path(self, valid_pdf: Path) -> None:
        result = validate_upload_file(str(valid_pdf))

        assert result.valid is True


class TestValidateUploadFileStrict:
    """Testes para validate_upload_file_strict (levanta exceção)."""

    def test_valid_file_returns_result(self, valid_pdf: Path) -> None:
        result = validate_upload_file_strict(valid_pdf)

        assert isinstance(result, FileValidationResult)
        assert result.valid is True

    def test_invalid_file_raises_exception(self, invalid_extension_file: Path) -> None:
        with pytest.raises(UploadValidationError) as exc_info:
            validate_upload_file_strict(invalid_extension_file)

        assert "não permitida" in exc_info.value.message.lower() or ".exe" in exc_info.value.message

    def test_exception_has_detail(self, invalid_extension_file: Path) -> None:
        with pytest.raises(UploadValidationError) as exc_info:
            validate_upload_file_strict(invalid_extension_file)

        assert exc_info.value.detail  # Deve ter detalhes técnicos


class TestValidateUploadFiles:
    """Testes para validate_upload_files (lote)."""

    def test_all_valid(self, tmp_path: Path) -> None:
        # Criar vários PDFs válidos
        files = []
        for i in range(3):
            pdf = tmp_path / f"doc{i}.pdf"
            pdf.write_bytes(PDF_MAGIC + b"content")
            files.append(str(pdf))

        valid, invalid = validate_upload_files(files)

        assert len(valid) == 3
        assert len(invalid) == 0

    def test_all_invalid(self, tmp_path: Path) -> None:
        # Criar vários arquivos inválidos
        files = []
        for i in range(3):
            exe = tmp_path / f"prog{i}.exe"
            exe.write_bytes(b"MZ")
            files.append(str(exe))

        valid, invalid = validate_upload_files(files)

        assert len(valid) == 0
        assert len(invalid) == 3

    def test_mixed_valid_and_invalid(self, tmp_path: Path) -> None:
        # PDF válido
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(PDF_MAGIC + b"content")

        # EXE inválido
        exe = tmp_path / "prog.exe"
        exe.write_bytes(b"MZ")

        # Arquivo inexistente
        missing = tmp_path / "missing.pdf"

        valid, invalid = validate_upload_files([str(pdf), str(exe), str(missing)])

        assert len(valid) == 1
        assert len(invalid) == 2
        assert valid[0].path == pdf

    def test_empty_list(self) -> None:
        valid, invalid = validate_upload_files([])

        assert valid == []
        assert invalid == []


# ============================================================================
# Testes de configuração
# ============================================================================


class TestConfiguration:
    """Testes para constantes de configuração."""

    def test_allowed_extensions_is_frozen(self) -> None:
        assert isinstance(ALLOWED_EXTENSIONS, frozenset)

    def test_pdf_in_allowed(self) -> None:
        assert ".pdf" in ALLOWED_EXTENSIONS

    def test_max_size_is_positive(self) -> None:
        assert MAX_SIZE_BYTES > 0

    def test_pdf_magic_is_bytes(self) -> None:
        assert isinstance(PDF_MAGIC, bytes)
        assert PDF_MAGIC == b"%PDF"

    def test_default_extensions_remain_pdf_without_env(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Sem env, apenas PDF deve ser permitido."""
        monkeypatch.delenv("RC_UPLOAD_ALLOWED_EXTENSIONS", raising=False)
        importlib.reload(file_validator_module)

        png_file = tmp_path / "imagem.png"
        png_file.write_bytes(b"\x89PNG\r\n")
        result = file_validator_module.validate_upload_file(png_file)

        assert result.valid is False
        assert ".pdf" in file_validator_module.DEFAULT_ALLOWED_EXTENSIONS

        importlib.reload(file_validator_module)

    def test_allowed_extensions_can_be_configured_via_env(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Whitelist customizada via env deve aceitar novas extens?es."""
        monkeypatch.setenv("RC_UPLOAD_ALLOWED_EXTENSIONS", ".pdf,.png")
        importlib.reload(file_validator_module)

        png_file = tmp_path / "foto.png"
        png_file.write_bytes(b"\x89PNG\r\n")
        result = file_validator_module.validate_upload_file(png_file)

        assert result.valid is True
        assert {".pdf", ".png"}.issubset(file_validator_module.DEFAULT_ALLOWED_EXTENSIONS)

        monkeypatch.delenv("RC_UPLOAD_ALLOWED_EXTENSIONS", raising=False)
        importlib.reload(file_validator_module)


# ============================================================================
# Testes de FileValidationResult
# ============================================================================


class TestFileValidationResult:
    """Testes para dataclass FileValidationResult."""

    def test_valid_result_attributes(self, valid_pdf: Path) -> None:
        result = validate_upload_file(valid_pdf)

        assert hasattr(result, "valid")
        assert hasattr(result, "path")
        assert hasattr(result, "size_bytes")
        assert hasattr(result, "extension")
        assert hasattr(result, "error")

    def test_result_is_immutable(self, valid_pdf: Path) -> None:
        result = validate_upload_file(valid_pdf)

        with pytest.raises(AttributeError):
            result.valid = False  # type: ignore[misc]
