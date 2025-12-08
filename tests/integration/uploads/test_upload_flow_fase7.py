"""Testes de integração para fluxo de upload.

FASE 7 - Testes de integração leve usando:
- Validação real de arquivos
- Repo fake que simula erros
- Retry com backoff real (valores pequenos)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from src.modules.uploads.file_validator import (
    PDF_MAGIC,
    validate_upload_file,
    validate_upload_files,
)
from src.modules.uploads.upload_retry import upload_with_retry
from src.modules.uploads.exceptions import (
    UploadNetworkError,
    UploadServerError,
)


# ============================================================================
# Fake Repository
# ============================================================================


@dataclass
class FakeStorageItem:
    """Representa um arquivo no storage fake."""

    key: str
    content: bytes
    content_type: str


class FakeUploadRepository:
    """Repositório fake para testes de integração.

    Simula comportamentos de:
    - Upload bem-sucedido
    - Erros de rede (retry)
    - Erros de servidor 5xx (retry)
    - Duplicatas (sem retry)
    """

    def __init__(self) -> None:
        self.storage: dict[str, FakeStorageItem] = {}
        self.upload_calls: list[tuple[str, str]] = []
        self.error_sequence: list[Exception | None] = []
        self._call_index = 0

    def configure_errors(self, *errors: Exception | None) -> None:
        """Configura sequência de erros a serem lançados.

        Ex: configure_errors(ConnectionError(), None) -> primeiro upload falha, segundo sucesso
        """
        self.error_sequence = list(errors)
        self._call_index = 0

    def upload_file(
        self,
        local_path: str | Path,
        remote_key: str,
        content_type: str = "application/pdf",
    ) -> str:
        """Simula upload de arquivo."""
        self.upload_calls.append((str(local_path), remote_key))

        # Verificar se deve lançar erro
        if self._call_index < len(self.error_sequence):
            error = self.error_sequence[self._call_index]
            self._call_index += 1
            if error is not None:
                raise error

        # Verificar duplicata
        if remote_key in self.storage:
            raise RuntimeError("409 Conflict - Duplicate file already exists")

        # Simular leitura do arquivo
        path = Path(local_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {local_path}")

        content = path.read_bytes()
        self.storage[remote_key] = FakeStorageItem(
            key=remote_key,
            content=content,
            content_type=content_type,
        )
        return remote_key

    def list_files(self, prefix: str = "") -> list[dict[str, Any]]:
        """Lista arquivos no storage fake."""
        results = []
        for key, item in self.storage.items():
            if key.startswith(prefix):
                results.append(
                    {
                        "name": key,
                        "full_path": key,
                        "size": len(item.content),
                        "content_type": item.content_type,
                    }
                )
        return results


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def fake_repo() -> FakeUploadRepository:
    """Cria repositório fake para testes."""
    return FakeUploadRepository()


@pytest.fixture
def valid_pdf(tmp_path: Path) -> Path:
    """Cria PDF válido para teste."""
    pdf = tmp_path / "documento.pdf"
    pdf.write_bytes(PDF_MAGIC + b"-1.4\n%test content for upload")
    return pdf


@pytest.fixture
def multiple_pdfs(tmp_path: Path) -> list[Path]:
    """Cria múltiplos PDFs para teste."""
    pdfs = []
    for i in range(5):
        pdf = tmp_path / f"doc{i}.pdf"
        pdf.write_bytes(PDF_MAGIC + f"-1.4\n%content {i}".encode())
        pdfs.append(pdf)
    return pdfs


# ============================================================================
# Testes de integração: Validação + Upload
# ============================================================================


class TestValidationThenUpload:
    """Testes de fluxo: validar arquivo, depois fazer upload."""

    def test_valid_file_uploads_successfully(self, fake_repo: FakeUploadRepository, valid_pdf: Path) -> None:
        # 1. Validar arquivo
        validation = validate_upload_file(valid_pdf)
        assert validation.valid is True

        # 2. Fazer upload
        result = fake_repo.upload_file(valid_pdf, "org/client/doc.pdf")

        assert result == "org/client/doc.pdf"
        assert len(fake_repo.storage) == 1
        assert "org/client/doc.pdf" in fake_repo.storage

    def test_invalid_file_not_uploaded(self, fake_repo: FakeUploadRepository, tmp_path: Path) -> None:
        # Criar arquivo com extensão inválida
        exe_file = tmp_path / "malware.exe"
        exe_file.write_bytes(b"MZ\x90\x00")

        # 1. Validar arquivo - deve falhar
        validation = validate_upload_file(exe_file)
        assert validation.valid is False
        error_message = validation.error
        assert error_message is not None
        normalized_error = error_message.lower()
        assert "não permitida" in normalized_error or ".exe" in error_message

        # 2. Não fazer upload (simulando lógica de app)
        assert len(fake_repo.storage) == 0
        assert len(fake_repo.upload_calls) == 0

    def test_batch_validation_filters_invalid(
        self, fake_repo: FakeUploadRepository, multiple_pdfs: list[Path], tmp_path: Path
    ) -> None:
        # Adicionar arquivo inválido à lista
        exe = tmp_path / "bad.exe"
        exe.write_bytes(b"MZ")
        all_files = [str(p) for p in multiple_pdfs] + [str(exe)]

        # 1. Validar todos
        valid, invalid = validate_upload_files(all_files)

        assert len(valid) == 5  # PDFs válidos
        assert len(invalid) == 1  # EXE inválido

        # 2. Upload apenas válidos
        for result in valid:
            fake_repo.upload_file(result.path, f"org/client/{result.path.name}")

        assert len(fake_repo.storage) == 5


# ============================================================================
# Testes de integração: Upload + Retry
# ============================================================================


class TestUploadWithRetryIntegration:
    """Testes de upload com retry usando repo fake."""

    def test_retry_on_network_error_then_success(self, fake_repo: FakeUploadRepository, valid_pdf: Path) -> None:
        # Configurar: 2 erros de rede, depois sucesso
        fake_repo.configure_errors(
            ConnectionError("Network unreachable"),
            ConnectionError("Timeout"),
            None,  # Sucesso
        )

        result = upload_with_retry(
            fake_repo.upload_file,
            valid_pdf,
            "org/client/doc.pdf",
            max_retries=3,
            backoff_base=0.01,
        )

        assert result == "org/client/doc.pdf"
        assert len(fake_repo.upload_calls) == 3

    def test_retry_on_server_error_then_success(self, fake_repo: FakeUploadRepository, valid_pdf: Path) -> None:
        # Configurar: 1 erro 503, depois sucesso
        fake_repo.configure_errors(
            RuntimeError("503 Service Unavailable"),
            None,
        )

        result = upload_with_retry(
            fake_repo.upload_file,
            valid_pdf,
            "org/client/doc.pdf",
            max_retries=2,
            backoff_base=0.01,
        )

        assert result == "org/client/doc.pdf"
        assert len(fake_repo.upload_calls) == 2

    def test_exhaust_retries_raises_network_error(self, fake_repo: FakeUploadRepository, valid_pdf: Path) -> None:
        # Configurar: sempre erro de rede
        fake_repo.configure_errors(
            ConnectionError("fail1"),
            ConnectionError("fail2"),
            ConnectionError("fail3"),
            ConnectionError("fail4"),
        )

        with pytest.raises(UploadNetworkError):
            upload_with_retry(
                fake_repo.upload_file,
                valid_pdf,
                "org/client/doc.pdf",
                max_retries=3,
                backoff_base=0.01,
            )

        # 1 tentativa inicial + 3 retries = 4 chamadas
        assert len(fake_repo.upload_calls) == 4

    def test_duplicate_error_no_retry(self, fake_repo: FakeUploadRepository, valid_pdf: Path) -> None:
        # Primeiro upload bem-sucedido
        fake_repo.upload_file(valid_pdf, "org/client/doc.pdf")

        # Segundo upload deve falhar como duplicata (sem retry)
        with pytest.raises(UploadServerError) as exc_info:
            upload_with_retry(
                fake_repo.upload_file,
                valid_pdf,
                "org/client/doc.pdf",  # Mesmo key
                max_retries=3,
                backoff_base=0.01,
            )

        assert "existe" in exc_info.value.message.lower()
        # Apenas 2 chamadas: original + tentativa de duplicata
        assert len(fake_repo.upload_calls) == 2


# ============================================================================
# Testes de integração: Fluxo completo
# ============================================================================


class TestFullUploadFlow:
    """Testes de fluxo completo: validação + upload + retry."""

    def test_full_flow_success(self, fake_repo: FakeUploadRepository, multiple_pdfs: list[Path]) -> None:
        """Fluxo completo com múltiplos arquivos."""
        # 1. Validar todos
        paths = [str(p) for p in multiple_pdfs]
        valid, invalid = validate_upload_files(paths)

        assert len(valid) == 5
        assert len(invalid) == 0

        # 2. Upload cada um (simulando service)
        ok_count = 0
        failures: list[tuple[Path, Exception]] = []

        for result in valid:
            try:
                upload_with_retry(
                    fake_repo.upload_file,
                    result.path,
                    f"org/client/{result.path.name}",
                    max_retries=2,
                    backoff_base=0.01,
                )
                ok_count += 1
            except Exception as exc:
                failures.append((result.path, exc))

        assert ok_count == 5
        assert len(failures) == 0
        assert len(fake_repo.storage) == 5

    def test_full_flow_with_partial_failures(self, fake_repo: FakeUploadRepository, multiple_pdfs: list[Path]) -> None:
        """Fluxo com algumas falhas de rede persistentes."""
        # Configurar: primeiros 3 uploads OK, depois sempre falha
        errors: list[Exception | None] = [None, None, None]
        for _ in range(10):
            errors.append(ConnectionError("fail"))
        fake_repo.configure_errors(*errors)

        paths = [str(p) for p in multiple_pdfs]
        valid, _ = validate_upload_files(paths)

        ok_count = 0
        failures: list[tuple[Path, Exception]] = []

        for result in valid:
            try:
                upload_with_retry(
                    fake_repo.upload_file,
                    result.path,
                    f"org/client/{result.path.name}",
                    max_retries=2,
                    backoff_base=0.01,
                )
                ok_count += 1
            except Exception as exc:
                failures.append((result.path, exc))

        # 3 sucessos, 2 falhas
        assert ok_count == 3
        assert len(failures) == 2
        assert all(isinstance(exc, UploadNetworkError) for _, exc in failures)

    def test_flow_tracks_retry_attempts(self, fake_repo: FakeUploadRepository, valid_pdf: Path) -> None:
        """Verificar que retries são rastreados corretamente."""
        retry_log: list[tuple[int, str]] = []

        def on_retry(attempt: int, exc: Exception, delay: float) -> None:
            retry_log.append((attempt, str(exc)))

        # 2 falhas, depois sucesso
        fake_repo.configure_errors(
            ConnectionError("timeout 1"),
            ConnectionError("timeout 2"),
            None,
        )

        upload_with_retry(
            fake_repo.upload_file,
            valid_pdf,
            "org/client/doc.pdf",
            max_retries=3,
            backoff_base=0.01,
            on_retry=on_retry,
        )

        assert len(retry_log) == 2
        assert retry_log[0][0] == 1  # Primeira retry
        assert retry_log[1][0] == 2  # Segunda retry
