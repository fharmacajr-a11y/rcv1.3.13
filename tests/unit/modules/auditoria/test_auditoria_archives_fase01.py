"""
Testes para src/modules/auditoria/archives.py (Microfase 6).

Foco: Aumentar cobertura de ~22.5% para ≥95%

Cenários testados:
- Extração de arquivos (ZIP, RAR, 7z)
- Preparação de planos de upload (archive entries)
- Detecção de duplicatas e estratégias (skip, replace, rename)
- Construção de upload items
- Execução de uploads com callbacks (progress, cancel_check)
- Normalização de paths
- Detecção de mime types
- Cleanup de recursos temporários
- Tratamento de erros (formato não suportado, arquivo corrompido, etc.)
"""

from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from src.modules.auditoria.archives import (
    ArchiveError,
    AuditoriaArchiveEntry,
    AuditoriaArchivePlan,
    build_upload_items,
    cleanup_archive_plan,
    detect_duplicate_file_names,
    execute_archive_upload,
    extract_archive_to,
    guess_mime,
    is_supported_archive,
    prepare_archive_plan,
)
from src.modules.auditoria.storage import AuditoriaUploadContext


# --- Fixtures ---


@pytest.fixture
def mock_upload_context():
    """Mock de AuditoriaUploadContext."""
    return AuditoriaUploadContext(bucket="test-bucket", base_prefix="client-10/auditoria", org_id="org-1", client_id=10)


@pytest.fixture
def mock_zip_entries():
    """Mock de entradas de ZIP para testes."""
    return [
        AuditoriaArchiveEntry(relative_path="doc1.pdf", file_size=1024),
        AuditoriaArchiveEntry(relative_path="subfolder/doc2.pdf", file_size=2048),
        AuditoriaArchiveEntry(relative_path="image.png", file_size=512),
    ]


# --- Testes de is_supported_archive ---


def test_is_supported_archive_zip():
    """Testa que .zip é suportado."""
    with patch("src.modules.auditoria.archives._infra_is_supported_archive") as mock_check:
        mock_check.return_value = True
        assert is_supported_archive("/path/to/file.zip") is True
        mock_check.assert_called_once_with("/path/to/file.zip")


def test_is_supported_archive_rar():
    """Testa que .rar é suportado."""
    with patch("src.modules.auditoria.archives._infra_is_supported_archive") as mock_check:
        mock_check.return_value = True
        assert is_supported_archive("/path/to/file.rar") is True


def test_is_supported_archive_7z():
    """Testa que .7z é suportado."""
    with patch("src.modules.auditoria.archives._infra_is_supported_archive") as mock_check:
        mock_check.return_value = True
        assert is_supported_archive("/path/to/file.7z") is True


def test_is_supported_archive_unsupported():
    """Testa que extensões não suportadas retornam False."""
    with patch("src.modules.auditoria.archives._infra_is_supported_archive") as mock_check:
        mock_check.return_value = False
        assert is_supported_archive("/path/to/file.txt") is False


# --- Testes de extract_archive_to ---


def test_extract_archive_to_delegates_to_infra():
    """Testa que extract_archive_to delega para infra."""
    with patch("src.modules.auditoria.archives._infra_extract_archive") as mock_extract:
        mock_extract.return_value = Path("/tmp/extracted")

        result = extract_archive_to("/path/to/archive.zip", "/tmp/target")

        assert result == Path("/tmp/extracted")
        mock_extract.assert_called_once_with("/path/to/archive.zip", "/tmp/target")


# --- Testes de _normalize_archive_relative_path ---


def test_normalize_archive_relative_path_removes_leading_slash():
    """Testa que barras iniciais são removidas."""
    from src.modules.auditoria.archives import _normalize_archive_relative_path

    assert _normalize_archive_relative_path("/path/to/file.txt") == "path/to/file.txt"


def test_normalize_archive_relative_path_converts_backslashes():
    """Testa que backslashes são convertidas para forward slashes."""
    from src.modules.auditoria.archives import _normalize_archive_relative_path

    assert _normalize_archive_relative_path("path\\to\\file.txt") == "path/to/file.txt"


def test_normalize_archive_relative_path_rejects_dot_prefix():
    """Testa que paths começando com . são rejeitados."""
    from src.modules.auditoria.archives import _normalize_archive_relative_path

    assert _normalize_archive_relative_path(".hidden/file.txt") == ""
    assert _normalize_archive_relative_path("./relative.txt") == ""


def test_normalize_archive_relative_path_rejects_macosx():
    """Testa que paths __MACOSX são rejeitados."""
    from src.modules.auditoria.archives import _normalize_archive_relative_path

    assert _normalize_archive_relative_path("__MACOSX/._file.txt") == ""


def test_normalize_archive_relative_path_rejects_parent_traversal():
    """Testa que paths com .. são rejeitados."""
    from src.modules.auditoria.archives import _normalize_archive_relative_path

    assert _normalize_archive_relative_path("path/../file.txt") == ""
    assert _normalize_archive_relative_path("../file.txt") == ""


def test_normalize_archive_relative_path_empty_string():
    """Testa que string vazia retorna vazio."""
    from src.modules.auditoria.archives import _normalize_archive_relative_path

    assert _normalize_archive_relative_path("") == ""
    assert _normalize_archive_relative_path(None) == ""


# --- Testes de prepare_archive_plan (ZIP) ---


def test_prepare_archive_plan_zip_success():
    """Testa preparação de plano para arquivo ZIP."""
    mock_zip_path = Path("/path/to/archive.zip")

    # Mock ZipFile
    mock_info1 = MagicMock()
    mock_info1.is_dir.return_value = False
    mock_info1.filename = "doc1.pdf"
    mock_info1.file_size = 1024

    mock_info2 = MagicMock()
    mock_info2.is_dir.return_value = False
    mock_info2.filename = "subfolder/doc2.pdf"
    mock_info2.file_size = 2048

    mock_info_dir = MagicMock()
    mock_info_dir.is_dir.return_value = True
    mock_info_dir.filename = "subfolder/"

    with patch("src.modules.auditoria.archives.zipfile.ZipFile") as mock_zipfile:
        mock_zf = MagicMock()
        mock_zf.infolist.return_value = [mock_info1, mock_info2, mock_info_dir]
        mock_zf.__enter__.return_value = mock_zf
        mock_zf.__exit__.return_value = None
        mock_zipfile.return_value = mock_zf

        plan = prepare_archive_plan(mock_zip_path)

        assert plan.archive_path == mock_zip_path
        assert plan.extension == "zip"
        assert len(plan.entries) == 2
        assert plan.entries[0].relative_path == "doc1.pdf"
        assert plan.entries[0].file_size == 1024
        assert plan.entries[1].relative_path == "subfolder/doc2.pdf"
        assert plan.entries[1].file_size == 2048
        assert plan.extracted_dir is None
        assert plan._temp_dir is None


def test_prepare_archive_plan_zip_bad_zipfile():
    """Testa que BadZipFile é convertido para ArchiveError."""
    mock_zip_path = Path("/path/to/corrupt.zip")

    with patch("src.modules.auditoria.archives.zipfile.ZipFile") as mock_zipfile:
        mock_zipfile.side_effect = zipfile.BadZipFile("File is not a zip file")

        with pytest.raises(ArchiveError, match="Arquivo ZIP invalido"):
            prepare_archive_plan(mock_zip_path)


def test_prepare_archive_plan_zip_filters_hidden_files():
    """Testa que arquivos ocultos/sistema são filtrados."""
    mock_zip_path = Path("/path/to/archive.zip")

    mock_info_normal = MagicMock()
    mock_info_normal.is_dir.return_value = False
    mock_info_normal.filename = "normal.txt"
    mock_info_normal.file_size = 100

    mock_info_hidden = MagicMock()
    mock_info_hidden.is_dir.return_value = False
    mock_info_hidden.filename = ".hidden"
    mock_info_hidden.file_size = 50

    mock_info_macosx = MagicMock()
    mock_info_macosx.is_dir.return_value = False
    mock_info_macosx.filename = "__MACOSX/._file"
    mock_info_macosx.file_size = 200

    with patch("src.modules.auditoria.archives.zipfile.ZipFile") as mock_zipfile:
        mock_zf = MagicMock()
        mock_zf.infolist.return_value = [mock_info_normal, mock_info_hidden, mock_info_macosx]
        mock_zf.__enter__.return_value = mock_zf
        mock_zf.__exit__.return_value = None
        mock_zipfile.return_value = mock_zf

        plan = prepare_archive_plan(mock_zip_path)

        assert len(plan.entries) == 1
        assert plan.entries[0].relative_path == "normal.txt"


# --- Testes de prepare_archive_plan (RAR/7z) ---


def test_prepare_archive_plan_rar_with_extraction():
    """Testa preparação de plano para arquivo RAR (requer extração)."""
    mock_rar_path = Path("/path/to/archive.rar")
    mock_extract_func = MagicMock()
    mock_extract_func.return_value = Path("/tmp/extracted")

    # Mock extracted files
    mock_file1 = MagicMock(spec=Path)
    mock_file1.is_file.return_value = True
    mock_file1.relative_to.return_value = Path("doc1.pdf")
    mock_file1.stat.return_value.st_size = 1024

    mock_file2 = MagicMock(spec=Path)
    mock_file2.is_file.return_value = True
    mock_file2.relative_to.return_value = Path("subfolder/doc2.pdf")
    mock_file2.stat.return_value.st_size = 2048

    with (
        patch("src.modules.auditoria.archives.tempfile.TemporaryDirectory") as mock_tempdir,
        patch.object(Path, "rglob") as mock_rglob,
    ):
        mock_temp_instance = MagicMock()
        mock_temp_instance.name = "/tmp/temp123"
        mock_tempdir.return_value = mock_temp_instance

        # Configurar rglob para retornar arquivos mockados
        mock_extracted_path = Path("/tmp/temp123")
        mock_rglob.return_value = [mock_file1, mock_file2]

        with patch("src.modules.auditoria.archives.Path") as mock_path_class:
            mock_path_class.return_value = mock_extracted_path
            mock_path_class.side_effect = lambda x: Path(x) if isinstance(x, str) else x

            plan = prepare_archive_plan(mock_rar_path, extract_func=mock_extract_func)

            assert plan.archive_path == mock_rar_path
            assert plan.extension == "rar"
            assert plan._temp_dir is not None
            mock_extract_func.assert_called_once()


def test_prepare_archive_plan_7z_standard():
    """Testa preparação de plano para arquivo .7z padrão."""
    mock_7z_path = Path("/path/to/archive.7z")
    mock_extract_func = MagicMock()

    with patch("src.modules.auditoria.archives.tempfile.TemporaryDirectory") as mock_tempdir:
        mock_temp_instance = MagicMock()
        mock_temp_instance.name = "/tmp/temp123"
        mock_tempdir.return_value = mock_temp_instance

        with patch.object(Path, "rglob", return_value=[]):
            plan = prepare_archive_plan(mock_7z_path, extract_func=mock_extract_func)

            assert plan.extension == "7z"


def test_prepare_archive_plan_7z_multipart():
    """Testa preparação de plano para arquivo .7z multi-part (e.g., archive.7z.001)."""
    mock_7z_path = Path("/path/to/archive.7z.001")
    mock_extract_func = MagicMock()

    with patch("src.modules.auditoria.archives.tempfile.TemporaryDirectory") as mock_tempdir:
        mock_temp_instance = MagicMock()
        mock_temp_instance.name = "/tmp/temp123"
        mock_tempdir.return_value = mock_temp_instance

        with patch.object(Path, "rglob", return_value=[]):
            plan = prepare_archive_plan(mock_7z_path, extract_func=mock_extract_func)

            assert plan.extension == "7z"


def test_prepare_archive_plan_unsupported_format():
    """Testa que formato não suportado levanta ValueError."""
    mock_txt_path = Path("/path/to/file.txt")

    with pytest.raises(ValueError, match="Formato nao suportado"):
        prepare_archive_plan(mock_txt_path)


def test_prepare_archive_plan_extraction_failure_cleanup():
    """Testa que tempdir é limpo quando extração falha."""
    mock_rar_path = Path("/path/to/archive.rar")
    mock_extract_func = MagicMock()
    mock_extract_func.side_effect = RuntimeError("Extraction failed")

    with patch("src.modules.auditoria.archives.tempfile.TemporaryDirectory") as mock_tempdir:
        mock_temp_instance = MagicMock()
        mock_temp_instance.name = "/tmp/temp123"
        mock_tempdir.return_value = mock_temp_instance

        with pytest.raises(RuntimeError, match="Extraction failed"):
            prepare_archive_plan(mock_rar_path, extract_func=mock_extract_func)

        # Verificar que cleanup foi chamado
        mock_temp_instance.cleanup.assert_called_once()


# --- Testes de cleanup_archive_plan ---


def test_cleanup_archive_plan_with_temp_dir():
    """Testa cleanup de plano com temp_dir."""
    mock_temp_dir = MagicMock(spec=tempfile.TemporaryDirectory)
    plan = AuditoriaArchivePlan(
        archive_path=Path("/path/to/archive.zip"), extension="zip", entries=[], _temp_dir=mock_temp_dir
    )

    cleanup_archive_plan(plan)

    mock_temp_dir.cleanup.assert_called_once()
    assert plan._temp_dir is None


def test_cleanup_archive_plan_with_none():
    """Testa cleanup com None (não deve causar erro)."""
    cleanup_archive_plan(None)  # Não deve lançar exceção


def test_cleanup_archive_plan_idempotent():
    """Testa que cleanup pode ser chamado múltiplas vezes."""
    mock_temp_dir = MagicMock(spec=tempfile.TemporaryDirectory)
    plan = AuditoriaArchivePlan(
        archive_path=Path("/path/to/archive.zip"), extension="zip", entries=[], _temp_dir=mock_temp_dir
    )

    cleanup_archive_plan(plan)
    cleanup_archive_plan(plan)  # Segunda chamada não deve causar erro

    # Cleanup deve ter sido chamado apenas uma vez (segunda chamada vê _temp_dir=None)
    mock_temp_dir.cleanup.assert_called_once()


# --- Testes de detect_duplicate_file_names ---


def test_detect_duplicate_file_names_found(mock_zip_entries):
    """Testa detecção de duplicatas existentes."""
    plan = AuditoriaArchivePlan(archive_path=Path("/path/to/archive.zip"), extension="zip", entries=mock_zip_entries)
    existing_names = {"doc1.pdf", "other.txt"}

    duplicates = detect_duplicate_file_names(plan, existing_names)

    assert duplicates == {"doc1.pdf"}


def test_detect_duplicate_file_names_none_found(mock_zip_entries):
    """Testa que nenhuma duplicata é encontrada quando não há overlap."""
    plan = AuditoriaArchivePlan(archive_path=Path("/path/to/archive.zip"), extension="zip", entries=mock_zip_entries)
    existing_names = {"other1.txt", "other2.pdf"}

    duplicates = detect_duplicate_file_names(plan, existing_names)

    assert duplicates == set()


def test_detect_duplicate_file_names_multiple(mock_zip_entries):
    """Testa detecção de múltiplas duplicatas."""
    plan = AuditoriaArchivePlan(archive_path=Path("/path/to/archive.zip"), extension="zip", entries=mock_zip_entries)
    existing_names = {"doc1.pdf", "doc2.pdf", "image.png"}

    duplicates = detect_duplicate_file_names(plan, existing_names)

    assert duplicates == {"doc1.pdf", "doc2.pdf", "image.png"}


# --- Testes de _next_copy_name ---


def test_next_copy_name_simple():
    """Testa geração de nome de cópia simples."""
    from src.modules.auditoria.archives import _next_copy_name

    result = _next_copy_name("doc.pdf", set())
    assert result == "doc (2).pdf"


def test_next_copy_name_increments():
    """Testa incremento quando nome já existe."""
    from src.modules.auditoria.archives import _next_copy_name

    existing = {"doc (2).pdf", "doc (3).pdf"}
    result = _next_copy_name("doc.pdf", existing)
    assert result == "doc (4).pdf"


def test_next_copy_name_no_extension():
    """Testa geração de nome sem extensão."""
    from src.modules.auditoria.archives import _next_copy_name

    result = _next_copy_name("README", set())
    assert result == "README (2)"


# --- Testes de build_upload_items ---


def test_build_upload_items_no_duplicates(mock_zip_entries):
    """Testa construção de upload items sem duplicatas."""
    items, skipped = build_upload_items(mock_zip_entries, set(), set(), "skip")

    assert len(items) == 3
    assert skipped == 0
    assert items[0].relative_path == "doc1.pdf"
    assert items[0].dest_name == "doc1.pdf"
    assert items[0].upsert is False


def test_build_upload_items_skip_strategy(mock_zip_entries):
    """Testa estratégia skip para duplicatas."""
    existing = {"doc1.pdf"}
    duplicates = {"doc1.pdf"}

    items, skipped = build_upload_items(mock_zip_entries, existing, duplicates, "skip")

    assert len(items) == 2  # doc1.pdf foi pulado
    assert skipped == 1
    assert items[0].relative_path == "subfolder/doc2.pdf"


def test_build_upload_items_replace_strategy(mock_zip_entries):
    """Testa estratégia replace para duplicatas."""
    existing = {"doc1.pdf"}
    duplicates = {"doc1.pdf"}

    items, skipped = build_upload_items(mock_zip_entries, existing, duplicates, "replace")

    assert len(items) == 3
    assert skipped == 0
    assert items[0].upsert is True  # doc1.pdf com upsert=True
    assert items[1].upsert is False  # outros sem upsert


def test_build_upload_items_rename_strategy(mock_zip_entries):
    """Testa estratégia rename para duplicatas."""
    existing = {"doc1.pdf"}
    duplicates = {"doc1.pdf"}

    items, skipped = build_upload_items(mock_zip_entries, existing, duplicates, "rename")

    assert len(items) == 3
    assert skipped == 0
    assert items[0].dest_name == "doc1 (2).pdf"  # Renomeado
    assert items[0].upsert is False


def test_build_upload_items_rename_preserves_path(mock_zip_entries):
    """Testa que rename preserva path de pastas."""
    existing = {"doc2.pdf"}
    duplicates = {"doc2.pdf"}

    items, skipped = build_upload_items(mock_zip_entries, existing, duplicates, "rename")

    # Encontrar o item renomeado
    renamed_item = next(item for item in items if "doc2" in item.dest_name)
    assert renamed_item.dest_name == "subfolder/doc2 (2).pdf"


def test_build_upload_items_invalid_strategy(mock_zip_entries):
    """Testa que estratégia inválida levanta ValueError."""
    with pytest.raises(ValueError, match="Estrategia de duplicatas invalida"):
        build_upload_items(mock_zip_entries, set(), set(), "invalid")


def test_build_upload_items_empty_strategy_defaults_to_skip(mock_zip_entries):
    """Testa que estratégia vazia/None usa skip como padrão."""
    existing = {"doc1.pdf"}
    duplicates = {"doc1.pdf"}

    items, skipped = build_upload_items(mock_zip_entries, existing, duplicates, "")

    assert skipped == 1  # skip foi aplicado


# --- Testes de guess_mime ---


def test_guess_mime_7z():
    """Testa detecção de MIME para .7z."""
    assert guess_mime("archive.7z") == "application/x-7z-compressed"
    assert guess_mime("archive.7z.001") == "application/x-7z-compressed"


def test_guess_mime_zip():
    """Testa detecção de MIME para .zip."""
    assert guess_mime("archive.zip") == "application/zip"


def test_guess_mime_rar():
    """Testa detecção de MIME para .rar."""
    assert guess_mime("archive.rar") == "application/x-rar-compressed"


def test_guess_mime_fallback():
    """Testa fallback para mimetypes.guess_type."""
    # PDF deve ser detectado por mimetypes
    mime = guess_mime("document.pdf")
    assert "pdf" in mime.lower() or mime == "application/octet-stream"


def test_guess_mime_unknown():
    """Testa fallback para application/octet-stream."""
    assert guess_mime("file.xyz") == "application/octet-stream"


# --- Testes de execute_archive_upload (ZIP) ---


def test_execute_archive_upload_zip_success(mock_upload_context, mock_zip_entries):
    """Testa execução de upload de ZIP com sucesso."""
    plan = AuditoriaArchivePlan(archive_path=Path("/path/to/archive.zip"), extension="zip", entries=mock_zip_entries)

    mock_upload_callback = MagicMock()

    # Mock ZipFile.read
    with patch("src.modules.auditoria.archives.zipfile.ZipFile") as mock_zipfile:
        mock_zf = MagicMock()
        mock_zf.read.side_effect = [b"data1", b"data2", b"data3"]
        mock_zf.__enter__.return_value = mock_zf
        mock_zf.__exit__.return_value = None
        mock_zipfile.return_value = mock_zf

        result = execute_archive_upload(
            plan,
            mock_upload_context,
            strategy="skip",
            existing_names=set(),
            duplicates=set(),
            upload_callback=mock_upload_callback,
        )

        assert result.done_files == 3
        assert result.total_files == 3
        assert result.skipped_duplicates == 0
        assert result.cancelled is False
        assert len(result.uploaded_paths) == 3
        assert mock_upload_callback.call_count == 3


def test_execute_archive_upload_with_progress_callback(mock_upload_context, mock_zip_entries):
    """Testa que progress_callback é chamado."""
    plan = AuditoriaArchivePlan(archive_path=Path("/path/to/archive.zip"), extension="zip", entries=mock_zip_entries)

    mock_upload_callback = MagicMock()
    mock_progress_callback = MagicMock()

    with patch("src.modules.auditoria.archives.zipfile.ZipFile") as mock_zipfile:
        mock_zf = MagicMock()
        mock_zf.read.side_effect = [b"data1", b"data2", b"data3"]
        mock_zf.__enter__.return_value = mock_zf
        mock_zf.__exit__.return_value = None
        mock_zipfile.return_value = mock_zf

        execute_archive_upload(
            plan,
            mock_upload_context,
            strategy="skip",
            existing_names=set(),
            duplicates=set(),
            upload_callback=mock_upload_callback,
            progress_callback=mock_progress_callback,
        )

        # Progress callback deve ser chamado: inicial + após cada arquivo
        assert mock_progress_callback.call_count >= 4


def test_execute_archive_upload_with_cancel_check(mock_upload_context, mock_zip_entries):
    """Testa que cancel_check interrompe upload."""
    plan = AuditoriaArchivePlan(archive_path=Path("/path/to/archive.zip"), extension="zip", entries=mock_zip_entries)

    mock_upload_callback = MagicMock()
    mock_cancel_check = MagicMock()
    mock_cancel_check.side_effect = [False, True]  # Cancela após primeiro arquivo

    with patch("src.modules.auditoria.archives.zipfile.ZipFile") as mock_zipfile:
        mock_zf = MagicMock()
        mock_zf.read.return_value = b"data"
        mock_zf.__enter__.return_value = mock_zf
        mock_zf.__exit__.return_value = None
        mock_zipfile.return_value = mock_zf

        result = execute_archive_upload(
            plan,
            mock_upload_context,
            strategy="skip",
            existing_names=set(),
            duplicates=set(),
            upload_callback=mock_upload_callback,
            cancel_check=mock_cancel_check,
        )

        assert result.cancelled is True
        assert result.done_files < 3  # Não completou todos


def test_execute_archive_upload_with_duplicates_skip(mock_upload_context, mock_zip_entries):
    """Testa skip de duplicatas durante upload."""
    plan = AuditoriaArchivePlan(archive_path=Path("/path/to/archive.zip"), extension="zip", entries=mock_zip_entries)

    mock_upload_callback = MagicMock()
    existing = {"doc1.pdf"}
    duplicates = {"doc1.pdf"}

    with patch("src.modules.auditoria.archives.zipfile.ZipFile") as mock_zipfile:
        mock_zf = MagicMock()
        mock_zf.read.side_effect = [b"data2", b"data3"]
        mock_zf.__enter__.return_value = mock_zf
        mock_zf.__exit__.return_value = None
        mock_zipfile.return_value = mock_zf

        result = execute_archive_upload(
            plan,
            mock_upload_context,
            strategy="skip",
            existing_names=existing,
            duplicates=duplicates,
            upload_callback=mock_upload_callback,
        )

        assert result.skipped_duplicates == 1
        assert result.done_files == 2
        assert mock_upload_callback.call_count == 2


# --- Testes de execute_archive_upload (RAR/7z) ---


def test_execute_archive_upload_extracted_success(mock_upload_context):
    """Testa execução de upload de arquivo extraído (RAR/7z)."""
    entries = [AuditoriaArchiveEntry(relative_path="doc1.pdf", file_size=1024)]

    mock_extracted_dir = Path("/tmp/extracted")
    plan = AuditoriaArchivePlan(
        archive_path=Path("/path/to/archive.rar"),
        extension="rar",
        entries=entries,
        extracted_dir=mock_extracted_dir,
    )

    mock_upload_callback = MagicMock()

    # Mock file read
    mock_file_data = b"file content"
    with patch("builtins.open", mock_open(read_data=mock_file_data)):
        result = execute_archive_upload(
            plan,
            mock_upload_context,
            strategy="skip",
            existing_names=set(),
            duplicates=set(),
            upload_callback=mock_upload_callback,
        )

        assert result.done_files == 1
        assert result.total_files == 1
        assert len(result.uploaded_paths) == 1
        mock_upload_callback.assert_called_once()


def test_execute_archive_upload_extracted_no_dir_error(mock_upload_context):
    """Testa erro quando extracted_dir é None para formato RAR/7z."""
    entries = [AuditoriaArchiveEntry(relative_path="doc1.pdf", file_size=1024)]

    plan = AuditoriaArchivePlan(
        archive_path=Path("/path/to/archive.rar"), extension="rar", entries=entries, extracted_dir=None
    )

    mock_upload_callback = MagicMock()

    with pytest.raises(ValueError, match="Diretorio extraido nao encontrado"):
        execute_archive_upload(
            plan,
            mock_upload_context,
            strategy="skip",
            existing_names=set(),
            duplicates=set(),
            upload_callback=mock_upload_callback,
        )


def test_execute_archive_upload_cleans_up_plan(mock_upload_context, mock_zip_entries):
    """Testa que execute_archive_upload sempre faz cleanup do plano."""
    plan = AuditoriaArchivePlan(archive_path=Path("/path/to/archive.zip"), extension="zip", entries=mock_zip_entries)

    mock_upload_callback = MagicMock()

    with (
        patch("src.modules.auditoria.archives.zipfile.ZipFile") as mock_zipfile,
        patch("src.modules.auditoria.archives.cleanup_archive_plan") as mock_cleanup,
    ):
        mock_zf = MagicMock()
        mock_zf.read.side_effect = [b"data1", b"data2", b"data3"]
        mock_zf.__enter__.return_value = mock_zf
        mock_zf.__exit__.return_value = None
        mock_zipfile.return_value = mock_zf

        execute_archive_upload(
            plan,
            mock_upload_context,
            strategy="skip",
            existing_names=set(),
            duplicates=set(),
            upload_callback=mock_upload_callback,
        )

        # Cleanup deve ser chamado no finally
        mock_cleanup.assert_called_once_with(plan)


# --- Testes de AuditoriaArchivePlan.__del__ ---


def test_archive_plan_del_calls_cleanup():
    """Testa que __del__ chama cleanup."""
    mock_temp_dir = MagicMock(spec=tempfile.TemporaryDirectory)
    plan = AuditoriaArchivePlan(
        archive_path=Path("/path/to/archive.zip"), extension="zip", entries=[], _temp_dir=mock_temp_dir
    )

    # Simular destruição do objeto
    plan.__del__()

    mock_temp_dir.cleanup.assert_called_once()
