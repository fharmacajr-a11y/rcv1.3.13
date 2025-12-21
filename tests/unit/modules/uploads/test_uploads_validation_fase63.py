"""
Testes para src/modules/uploads/validation.py (TEST-006).

Cenários:
- ensure_existing_folder: validação de diretório
- iter_local_files: iteração recursiva de arquivos
- guess_mime: detecção de MIME type
- normalize_relative_path: normalização e sanitização de paths
- prepare_folder_entries: preparação de metadados para upload
- collect_pdf_items_from_folder: coleta de PDFs recursivamente
- build_items_from_files: construção de items de lista explícita
- build_remote_path: montagem de chave de storage

Isolamento:
- tmp_path para criar arquivos reais pequenos
- Mock de hash_func para evitar SHA256 real
- Mock de funções externas (make_storage_key, client_prefix_for_id)
"""

import pytest
from pathlib import Path
from unittest.mock import Mock

from src.modules.uploads.validation import (
    PreparedUploadEntry,
    ensure_existing_folder,
    iter_local_files,
    guess_mime,
    normalize_relative_path,
    prepare_folder_entries,
    collect_pdf_items_from_folder,
    build_items_from_files,
    build_remote_path,
)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def fake_hash_func():
    """Mock hash function que retorna valor fixo."""
    return lambda p: "fake-sha256-hash"


@pytest.fixture
def mock_storage_key_functions(monkeypatch):
    """Mock de funções do storage_key module."""
    mock_make = Mock(return_value="org123/client456/GERAL/subdir/file.pdf")
    mock_slug_part = Mock(side_effect=lambda x: x.lower().replace(" ", "-"))
    mock_slug_filename = Mock(side_effect=lambda x: x.lower().replace(" ", "-"))

    monkeypatch.setattr("src.modules.uploads.validation.make_storage_key", mock_make)
    monkeypatch.setattr("src.modules.uploads.validation.storage_slug_part", mock_slug_part)
    monkeypatch.setattr("src.modules.uploads.validation.storage_slug_filename", mock_slug_filename)

    return {
        "make_storage_key": mock_make,
        "storage_slug_part": mock_slug_part,
        "storage_slug_filename": mock_slug_filename,
    }


@pytest.fixture
def mock_client_prefix(monkeypatch):
    """Mock de client_prefix_for_id (lazy import)."""
    mock_func = Mock(return_value="org123/client456")
    monkeypatch.setattr("src.modules.uploads.components.helpers.client_prefix_for_id", mock_func)
    return mock_func


# ============================================================================
# TESTES: ensure_existing_folder
# ============================================================================


class TestEnsureExistingFolder:
    """Testes para ensure_existing_folder()."""

    def test_existing_folder_returns_resolved_path(self, tmp_path):
        """Path válido retorna Path resolvido."""
        folder = tmp_path / "valid_folder"
        folder.mkdir()

        result = ensure_existing_folder(folder)

        assert isinstance(result, Path)
        assert result.is_absolute()
        assert result == folder.resolve()

    def test_nonexistent_folder_raises_file_not_found(self, tmp_path):
        """Path inexistente levanta FileNotFoundError."""
        nonexistent = tmp_path / "does_not_exist"

        with pytest.raises(FileNotFoundError, match="Pasta nao encontrada"):
            ensure_existing_folder(nonexistent)

    def test_string_path_works(self, tmp_path):
        """Aceita string como entrada e retorna Path."""
        folder = tmp_path / "valid_folder"
        folder.mkdir()

        result = ensure_existing_folder(str(folder))

        assert isinstance(result, Path)
        assert result == folder.resolve()


# ============================================================================
# TESTES: iter_local_files
# ============================================================================


class TestIterLocalFiles:
    """Testes para iter_local_files()."""

    def test_yields_files_in_flat_directory(self, tmp_path):
        """Itera arquivos em diretório plano."""
        (tmp_path / "file1.txt").write_text("a")
        (tmp_path / "file2.txt").write_text("b")

        result = list(iter_local_files(tmp_path))

        assert len(result) == 2
        assert all(isinstance(p, Path) for p in result)
        assert {p.name for p in result} == {"file1.txt", "file2.txt"}

    def test_yields_files_recursively(self, tmp_path):
        """Itera arquivos recursivamente em subdiretórios."""
        (tmp_path / "file1.txt").write_text("a")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file2.txt").write_text("b")

        result = list(iter_local_files(tmp_path))

        assert len(result) == 2
        names = {p.name for p in result}
        assert names == {"file1.txt", "file2.txt"}

    def test_empty_directory_yields_nothing(self, tmp_path):
        """Diretório vazio retorna iterator vazio."""
        result = list(iter_local_files(tmp_path))

        assert result == []


# ============================================================================
# TESTES: guess_mime
# ============================================================================


class TestGuessMime:
    """Testes para guess_mime()."""

    def test_pdf_returns_application_pdf(self, tmp_path):
        """Arquivo .pdf retorna 'application/pdf'."""
        file = tmp_path / "document.pdf"
        file.touch()

        mime = guess_mime(file)

        assert mime == "application/pdf"

    def test_jpg_returns_image_jpeg(self, tmp_path):
        """Arquivo .jpg retorna 'image/jpeg'."""
        file = tmp_path / "photo.jpg"
        file.touch()

        mime = guess_mime(file)

        assert mime == "image/jpeg"

    def test_txt_returns_text_plain(self, tmp_path):
        """Arquivo .txt retorna 'text/plain'."""
        file = tmp_path / "readme.txt"
        file.touch()

        mime = guess_mime(file)

        assert mime == "text/plain"

    def test_unknown_extension_returns_octet_stream(self, tmp_path):
        """Extensão desconhecida retorna 'application/octet-stream'."""
        file = tmp_path / "unknown.xyz"
        file.touch()

        mime = guess_mime(file)

        assert mime == "application/octet-stream"


# ============================================================================
# TESTES: normalize_relative_path
# ============================================================================


class TestNormalizeRelativePath:
    """Testes para normalize_relative_path()."""

    def test_normalizes_backslashes_to_forward_slashes(self):
        """Converte backslashes para forward slashes."""
        result = normalize_relative_path(r"pasta\arquivo.pdf")

        assert result == "pasta/arquivo.pdf"

    def test_removes_path_traversal(self):
        """Remove '..' para evitar path traversal."""
        result = normalize_relative_path("../../../etc/passwd")

        assert result == "etc/passwd"
        assert ".." not in result

    def test_removes_dot_slash(self):
        """Remove './' do início e meio do path."""
        result = normalize_relative_path("./pasta/./arquivo.pdf")

        assert result == "pasta/arquivo.pdf"

    def test_removes_leading_slash(self):
        """Remove '/' do início."""
        result = normalize_relative_path("/pasta/arquivo.pdf")

        assert result == "pasta/arquivo.pdf"

    def test_removes_trailing_slash(self):
        """Remove '/' do final."""
        result = normalize_relative_path("pasta/arquivo.pdf/")

        assert result == "pasta/arquivo.pdf"


# ============================================================================
# TESTES: prepare_folder_entries
# ============================================================================


class TestPrepareFolderEntries:
    """Testes para prepare_folder_entries()."""

    def test_prepares_entries_for_two_pdfs(self, tmp_path, fake_hash_func, mock_storage_key_functions):
        """Prepara entries com metadados completos para 2 PDFs."""
        (tmp_path / "file1.pdf").write_text("content1")
        (tmp_path / "file2.pdf").write_text("content2")

        entries = prepare_folder_entries(
            base=tmp_path,
            client_id=123,
            subdir="GERAL",
            org_id="org-abc",
            hash_func=fake_hash_func,
        )

        assert len(entries) == 2
        assert all(isinstance(e, PreparedUploadEntry) for e in entries)
        assert {e.path.name for e in entries} == {"file1.pdf", "file2.pdf"}
        assert all(e.sha256 == "fake-sha256-hash" for e in entries)
        assert all(e.mime_type == "application/pdf" for e in entries)

    def test_preserves_relative_path_structure(self, tmp_path, fake_hash_func, mock_storage_key_functions):
        """Preserva estrutura de diretórios em relative_path."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "nested.pdf").write_text("content")

        entries = prepare_folder_entries(
            base=tmp_path,
            client_id=123,
            subdir="GERAL",
            org_id="org-abc",
            hash_func=fake_hash_func,
        )

        assert len(entries) == 1
        assert entries[0].relative_path == "subdir/nested.pdf"

    def test_calls_hash_func_for_each_file(self, tmp_path, mock_storage_key_functions):
        """Chama hash_func para cada arquivo."""
        (tmp_path / "file1.pdf").write_text("a")
        (tmp_path / "file2.pdf").write_text("b")

        mock_hash = Mock(return_value="mocked-sha256")

        entries = prepare_folder_entries(
            base=tmp_path,
            client_id=123,
            subdir="GERAL",
            org_id="org-abc",
            hash_func=mock_hash,
        )

        assert mock_hash.call_count == 2
        assert all(e.sha256 == "mocked-sha256" for e in entries)

    def test_calculates_size_bytes(self, tmp_path, fake_hash_func, mock_storage_key_functions):
        """Calcula size_bytes corretamente."""
        (tmp_path / "file.pdf").write_bytes(b"0123456789")  # 10 bytes

        entries = prepare_folder_entries(
            base=tmp_path,
            client_id=123,
            subdir="GERAL",
            org_id="org-abc",
            hash_func=fake_hash_func,
        )

        assert len(entries) == 1
        assert entries[0].size_bytes == 10

    def test_calls_make_storage_key(self, tmp_path, fake_hash_func, mock_storage_key_functions):
        """Chama make_storage_key com argumentos corretos."""
        (tmp_path / "file.pdf").write_text("content")

        entries = prepare_folder_entries(
            base=tmp_path,
            client_id=456,
            subdir="ANVISA",
            org_id="org-xyz",
            hash_func=fake_hash_func,
        )

        assert len(entries) == 1
        make_mock = mock_storage_key_functions["make_storage_key"]
        assert make_mock.call_count == 1
        call_args = make_mock.call_args[0]
        assert call_args[0] == "org-xyz"
        assert call_args[1] == "456"
        assert call_args[2] == "ANVISA"

    def test_empty_folder_returns_empty_list(self, tmp_path, fake_hash_func, mock_storage_key_functions):
        """Pasta vazia retorna lista vazia."""
        entries = prepare_folder_entries(
            base=tmp_path,
            client_id=123,
            subdir="GERAL",
            org_id="org-abc",
            hash_func=fake_hash_func,
        )

        assert entries == []


# ============================================================================
# TESTES: collect_pdf_items_from_folder
# ============================================================================


class TestCollectPdfItemsFromFolder:
    """Testes para collect_pdf_items_from_folder()."""

    def test_collects_only_pdf_files(self, tmp_path):
        """Retorna só arquivos .pdf, ignora outros."""
        (tmp_path / "file1.pdf").write_text("a")
        (tmp_path / "file2.txt").write_text("b")
        (tmp_path / "file3.pdf").write_text("c")

        def factory(path, rel):
            return (path.name, rel)

        items = collect_pdf_items_from_folder(str(tmp_path), factory)

        assert len(items) == 2
        names = {item[0] for item in items}
        assert names == {"file1.pdf", "file3.pdf"}

    def test_empty_directory_returns_empty_list(self, tmp_path):
        """Diretório vazio retorna []."""

        def factory(path, rel):
            return (path.name, rel)

        items = collect_pdf_items_from_folder(str(tmp_path), factory)

        assert items == []

    def test_nonexistent_directory_returns_empty_list(self, tmp_path):
        """Diretório inexistente retorna []."""
        nonexistent = tmp_path / "does_not_exist"

        def factory(path, rel):
            return (path.name, rel)

        items = collect_pdf_items_from_folder(str(nonexistent), factory)

        assert items == []

    def test_file_instead_of_directory_returns_empty_list(self, tmp_path):
        """Path apontando para arquivo retorna []."""
        file = tmp_path / "file.txt"
        file.write_text("content")

        def factory(path, rel):
            return (path.name, rel)

        items = collect_pdf_items_from_folder(str(file), factory)

        assert items == []

    def test_sorts_by_lowercase(self, tmp_path):
        """Ordena por lowercase do relative_path."""
        (tmp_path / "B.pdf").write_text("b")
        (tmp_path / "a.pdf").write_text("a")
        (tmp_path / "C.pdf").write_text("c")

        def factory(path, rel):
            return rel

        items = collect_pdf_items_from_folder(str(tmp_path), factory)

        assert items == ["a.pdf", "B.pdf", "C.pdf"]


# ============================================================================
# TESTES: build_items_from_files
# ============================================================================


class TestBuildItemsFromFiles:
    """Testes para build_items_from_files()."""

    def test_empty_list_returns_empty(self):
        """Lista vazia retorna []."""

        def factory(path, rel):
            return (path.name, rel)

        items = build_items_from_files([], factory)

        assert items == []

    def test_builds_items_from_pdf_paths(self, tmp_path):
        """Cria items de lista de paths de PDF."""
        file1 = tmp_path / "file1.pdf"
        file2 = tmp_path / "file2.pdf"
        file1.write_text("a")
        file2.write_text("b")

        def factory(path, rel):
            return (path.name, rel)

        items = build_items_from_files([str(file1), str(file2)], factory)

        assert len(items) == 2
        names = {item[0] for item in items}
        assert names == {"file1.pdf", "file2.pdf"}

    def test_filters_non_pdf_files(self, tmp_path):
        """Filtra arquivos que não são .pdf."""
        pdf = tmp_path / "doc.pdf"
        txt = tmp_path / "readme.txt"
        pdf.write_text("a")
        txt.write_text("b")

        def factory(path, rel):
            return path.name

        items = build_items_from_files([str(pdf), str(txt)], factory)

        assert len(items) == 1
        assert items[0] == "doc.pdf"

    def test_sorts_by_filename_lowercase(self, tmp_path):
        """Ordena por filename lowercase."""
        (tmp_path / "B.pdf").write_text("b")
        (tmp_path / "a.pdf").write_text("a")
        (tmp_path / "C.pdf").write_text("c")

        paths = [
            str(tmp_path / "B.pdf"),
            str(tmp_path / "a.pdf"),
            str(tmp_path / "C.pdf"),
        ]

        def factory(path, rel):
            return rel

        items = build_items_from_files(paths, factory)

        assert items == ["a.pdf", "B.pdf", "C.pdf"]


# ============================================================================
# TESTES: build_remote_path
# ============================================================================


class TestBuildRemotePath:
    """Testes para build_remote_path()."""

    def test_mode_with_client_id_and_org_id(self, mock_client_prefix):
        """Modo 1: usa client_prefix_for_id quando client_id e org_id fornecidos."""
        result = build_remote_path(
            cnpj_digits="12345678",
            relative_path="doc.pdf",
            subfolder="ANVISA",
            client_id=123,
            org_id="org-abc",
        )

        mock_client_prefix.assert_called_once_with(123, "org-abc")
        assert result.startswith("org123/client456/GERAL")
        assert "ANVISA" in result

    def test_fallback_mode_without_client_id(self):
        """Modo 2: fallback usa cnpj_digits quando sem client_id."""
        result = build_remote_path(
            cnpj_digits="12345678",
            relative_path="doc.pdf",
            subfolder="ANVISA",
            client_id=None,
            org_id=None,
        )

        assert result.startswith("12345678")
        assert "ANVISA" in result
        assert "doc.pdf" in result

    def test_omits_subfolder_when_none(self, mock_client_prefix):
        """Omite subfolder quando None."""
        result = build_remote_path(
            cnpj_digits="12345678",
            relative_path="doc.pdf",
            subfolder=None,
            client_id=123,
            org_id="org-abc",
        )

        assert "ANVISA" not in result
        assert "GERAL" in result  # DEFAULT_IMPORT_SUBFOLDER

    def test_normalizes_relative_path_backslashes(self):
        """Normaliza backslashes em relative_path."""
        result = build_remote_path(
            cnpj_digits="12345678",
            relative_path=r"pasta\doc.pdf",
            subfolder=None,
            client_id=None,
            org_id=None,
        )

        assert "pasta/doc.pdf" in result
        assert "\\" not in result

    def test_removes_path_traversal_from_relative_path(self):
        """Remove '..' do relative_path."""
        result = build_remote_path(
            cnpj_digits="12345678",
            relative_path="../../../etc/passwd",
            subfolder=None,
            client_id=None,
            org_id=None,
        )

        assert ".." not in result
        assert "etc/passwd" in result
