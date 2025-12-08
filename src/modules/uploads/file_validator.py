"""Validação de arquivos para upload seguindo OWASP File Upload Cheat Sheet.

FASE 7 - Validação robusta antes de iniciar qualquer upload:
1. Whitelist de extensões permitidas
2. Limite de tamanho configurável
3. Verificação de arquivo legível (não corrompido)
4. Magic bytes (sniffing) para PDFs (opcional)

Referência: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html

Não confiamos em Content-Type reportado pelo cliente/OS.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Sequence

from src.config.environment import env_str

from .exceptions import UploadValidationError

# ============================================================================
# Configuração de validação (pode ser sobrescrita via env)
# ============================================================================

# Extensões permitidas (whitelist). Apenas PDF por padrão.


def _load_default_allowed_extensions() -> frozenset[str]:
    raw = env_str("RC_UPLOAD_ALLOWED_EXTENSIONS", ".pdf") or ".pdf"
    parts = [part.strip().lower() for part in raw.split(",")]
    extensions = {part if part.startswith(".") else f".{part}" for part in parts if part}
    return frozenset(extensions or {".pdf"})


DEFAULT_ALLOWED_EXTENSIONS: Final[frozenset[str]] = _load_default_allowed_extensions()
ALLOWED_EXTENSIONS: Final[frozenset[str]] = DEFAULT_ALLOWED_EXTENSIONS

# Extensões permitidas incluindo imagens (se habilitado)
ALLOWED_EXTENSIONS_WITH_IMAGES: Final[frozenset[str]] = frozenset({".pdf", ".jpg", ".jpeg", ".png", ".gif"})

# Tamanho máximo em bytes (padrão: 50 MB)
DEFAULT_MAX_SIZE_BYTES: Final[int] = 50 * 1024 * 1024  # 50 MB
MAX_SIZE_BYTES: int = int(os.getenv("RC_UPLOAD_MAX_SIZE_MB", "50")) * 1024 * 1024

# Magic bytes para PDF (primeiros bytes do arquivo)
PDF_MAGIC: Final[bytes] = b"%PDF"


# ============================================================================
# Resultado da validação
# ============================================================================


@dataclass(slots=True, frozen=True)
class FileValidationResult:
    """Resultado da validação de arquivo para upload.

    Atributos:
        valid: True se o arquivo passou em todas as validações.
        path: Caminho do arquivo validado.
        size_bytes: Tamanho do arquivo em bytes.
        extension: Extensão do arquivo (lowercase, com ponto).
        error: Mensagem de erro se inválido, None se válido.
    """

    valid: bool
    path: Path
    size_bytes: int
    extension: str
    error: str | None = None


# ============================================================================
# Funções de validação
# ============================================================================


def _check_extension(path: Path, allowed: frozenset[str]) -> str | None:
    """Verifica se a extensão do arquivo está na whitelist.

    Returns:
        None se válido, mensagem de erro se inválido.
    """
    ext = path.suffix.lower()
    if ext not in allowed:
        allowed_list = ", ".join(sorted(allowed))
        return f"Extensão '{ext}' não permitida. Permitidas: {allowed_list}"
    return None


def _check_size(path: Path, max_bytes: int) -> tuple[int, str | None]:
    """Verifica se o arquivo não excede o tamanho máximo.

    Returns:
        Tupla (tamanho_bytes, erro_ou_none).
    """
    try:
        size = path.stat().st_size
    except OSError as exc:
        return 0, f"Não foi possível verificar o tamanho: {exc}"

    if size == 0:
        return 0, "O arquivo está vazio."

    if size > max_bytes:
        max_mb = max_bytes / (1024 * 1024)
        size_mb = size / (1024 * 1024)
        return size, f"Arquivo muito grande ({size_mb:.1f} MB). Máximo: {max_mb:.0f} MB."

    return size, None


def _check_readable(path: Path) -> str | None:
    """Verifica se o arquivo pode ser aberto para leitura.

    Returns:
        None se legível, mensagem de erro se não.
    """
    try:
        with path.open("rb") as f:
            # Tenta ler os primeiros bytes para confirmar que não está corrompido
            f.read(1024)
        return None
    except OSError as exc:
        return f"Arquivo não pode ser lido: {exc}"


def _check_pdf_magic(path: Path) -> str | None:
    """Verifica magic bytes de PDF (opcional, apenas para .pdf).

    Returns:
        None se válido/não-aplicável, mensagem de erro se inválido.
    """
    if path.suffix.lower() != ".pdf":
        return None  # Não aplicável a outros tipos

    try:
        with path.open("rb") as f:
            header = f.read(len(PDF_MAGIC))
        if not header.startswith(PDF_MAGIC):
            return "O arquivo não parece ser um PDF válido."
        return None
    except OSError:
        return None  # Erro de leitura já tratado em _check_readable


def validate_upload_file(
    path: str | Path,
    *,
    allowed_extensions: frozenset[str] | None = None,
    max_size_bytes: int | None = None,
    check_magic: bool = True,
) -> FileValidationResult:
    """Valida um arquivo para upload.

    Args:
        path: Caminho do arquivo a validar.
        allowed_extensions: Whitelist de extensões (padrão: ALLOWED_EXTENSIONS).
        max_size_bytes: Tamanho máximo em bytes (padrão: MAX_SIZE_BYTES).
        check_magic: Se True, verifica magic bytes de PDFs.

    Returns:
        FileValidationResult com resultado da validação.

    Não levanta exceção - retorna resultado com valid=False se inválido.
    Use validate_upload_file_strict() para levantar exceção.
    """
    file_path = Path(path)
    allowed = allowed_extensions or DEFAULT_ALLOWED_EXTENSIONS
    max_size = max_size_bytes or MAX_SIZE_BYTES

    # 1. Verificar se arquivo existe
    if not file_path.exists():
        return FileValidationResult(
            valid=False,
            path=file_path,
            size_bytes=0,
            extension="",
            error=f"Arquivo não encontrado: {file_path.name}",
        )

    # 2. Verificar se é arquivo (não diretório)
    if not file_path.is_file():
        return FileValidationResult(
            valid=False,
            path=file_path,
            size_bytes=0,
            extension="",
            error=f"Não é um arquivo válido: {file_path.name}",
        )

    ext = file_path.suffix.lower()

    # 3. Verificar extensão (whitelist)
    ext_error = _check_extension(file_path, allowed)
    if ext_error:
        return FileValidationResult(
            valid=False,
            path=file_path,
            size_bytes=0,
            extension=ext,
            error=ext_error,
        )

    # 4. Verificar tamanho
    size, size_error = _check_size(file_path, max_size)
    if size_error:
        return FileValidationResult(
            valid=False,
            path=file_path,
            size_bytes=size,
            extension=ext,
            error=size_error,
        )

    # 5. Verificar legibilidade
    read_error = _check_readable(file_path)
    if read_error:
        return FileValidationResult(
            valid=False,
            path=file_path,
            size_bytes=size,
            extension=ext,
            error=read_error,
        )

    # 6. Verificar magic bytes (opcional)
    if check_magic:
        magic_error = _check_pdf_magic(file_path)
        if magic_error:
            return FileValidationResult(
                valid=False,
                path=file_path,
                size_bytes=size,
                extension=ext,
                error=magic_error,
            )

    # Tudo OK
    return FileValidationResult(
        valid=True,
        path=file_path,
        size_bytes=size,
        extension=ext,
        error=None,
    )


def validate_upload_file_strict(
    path: str | Path,
    *,
    allowed_extensions: frozenset[str] | None = None,
    max_size_bytes: int | None = None,
    check_magic: bool = True,
) -> FileValidationResult:
    """Valida arquivo para upload, levantando exceção se inválido.

    Args:
        path: Caminho do arquivo a validar.
        allowed_extensions: Whitelist de extensões.
        max_size_bytes: Tamanho máximo em bytes.
        check_magic: Se True, verifica magic bytes de PDFs.

    Returns:
        FileValidationResult se válido.

    Raises:
        UploadValidationError: Se o arquivo não passar na validação.
    """
    result = validate_upload_file(
        path,
        allowed_extensions=allowed_extensions,
        max_size_bytes=max_size_bytes,
        check_magic=check_magic,
    )

    if not result.valid:
        raise UploadValidationError(
            result.error or "Arquivo inválido para upload",
            detail=f"path={path}, ext={result.extension}, size={result.size_bytes}",
        )

    return result


def validate_upload_files(
    paths: Sequence[str | Path],
    *,
    allowed_extensions: frozenset[str] | None = None,
    max_size_bytes: int | None = None,
    check_magic: bool = True,
) -> tuple[list[FileValidationResult], list[FileValidationResult]]:
    """Valida múltiplos arquivos para upload.

    Args:
        paths: Lista de caminhos de arquivos.
        allowed_extensions: Whitelist de extensões.
        max_size_bytes: Tamanho máximo em bytes.
        check_magic: Se True, verifica magic bytes de PDFs.

    Returns:
        Tupla (válidos, inválidos) com listas de FileValidationResult.
    """
    valid: list[FileValidationResult] = []
    invalid: list[FileValidationResult] = []

    for path in paths:
        result = validate_upload_file(
            path,
            allowed_extensions=allowed_extensions,
            max_size_bytes=max_size_bytes,
            check_magic=check_magic,
        )
        if result.valid:
            valid.append(result)
        else:
            invalid.append(result)

    return valid, invalid


__all__ = [
    "ALLOWED_EXTENSIONS",
    "DEFAULT_ALLOWED_EXTENSIONS",
    "ALLOWED_EXTENSIONS_WITH_IMAGES",
    "MAX_SIZE_BYTES",
    "DEFAULT_MAX_SIZE_BYTES",
    "PDF_MAGIC",
    "FileValidationResult",
    "validate_upload_file",
    "validate_upload_file_strict",
    "validate_upload_files",
]
