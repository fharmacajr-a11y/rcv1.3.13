"""Testes para gerenciamento de arquivos temporários (temp_files.py)."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.modules.uploads.temp_files import (
    cleanup_old_files,
    cleanup_on_startup,
    create_temp_file,
    get_temp_directory,
)


class TestGetTempDirectory:
    """Testes para get_temp_directory()."""

    def test_returns_path_object(self):
        """Deve retornar um objeto Path."""
        result = get_temp_directory()
        assert isinstance(result, Path)

    def test_creates_directory_if_not_exists(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Deve criar o diretório se não existir."""
        fake_temp = tmp_path / "fake_system_temp"
        fake_temp.mkdir()

        monkeypatch.setattr("tempfile.gettempdir", lambda: str(fake_temp))

        result = get_temp_directory()

        expected = fake_temp / "rc_gestor_uploads"
        assert result == expected
        assert result.exists()
        assert result.is_dir()

    def test_returns_existing_directory(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Se o diretório já existir, deve retorná-lo sem erro."""
        fake_temp = tmp_path / "fake_system_temp"
        fake_temp.mkdir()
        app_dir = fake_temp / "rc_gestor_uploads"
        app_dir.mkdir()

        monkeypatch.setattr("tempfile.gettempdir", lambda: str(fake_temp))

        result = get_temp_directory()

        assert result == app_dir
        assert result.exists()


class TestCreateTempFile:
    """Testes para create_temp_file()."""

    def test_creates_temp_file_info(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Deve retornar TempFileInfo com path, directory e filename."""
        fake_temp = tmp_path / "fake_system_temp"
        fake_temp.mkdir()

        monkeypatch.setattr("tempfile.gettempdir", lambda: str(fake_temp))

        result = create_temp_file("documento.pdf")

        assert result.filename == "documento.pdf"
        assert result.directory == str(fake_temp / "rc_gestor_uploads")
        assert result.path == str(fake_temp / "rc_gestor_uploads" / "documento.pdf")

    def test_sanitizes_filename_with_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Deve usar apenas o basename se passar path completo."""
        fake_temp = tmp_path / "fake_system_temp"
        fake_temp.mkdir()

        monkeypatch.setattr("tempfile.gettempdir", lambda: str(fake_temp))

        result = create_temp_file("clientes/123/arquivo.pdf")

        assert result.filename == "arquivo.pdf"
        assert "clientes" not in result.path

    def test_handles_duplicate_filename_with_timestamp(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Se arquivo já existir, deve adicionar timestamp ao nome."""
        fake_temp = tmp_path / "fake_system_temp"
        fake_temp.mkdir()
        app_dir = fake_temp / "rc_gestor_uploads"
        app_dir.mkdir()

        # Criar arquivo existente
        existing = app_dir / "relatorio.pdf"
        existing.write_text("conteúdo antigo")

        monkeypatch.setattr("tempfile.gettempdir", lambda: str(fake_temp))

        result = create_temp_file("relatorio.pdf")

        # Nome deve ter timestamp
        assert result.filename != "relatorio.pdf"
        assert result.filename.startswith("relatorio_")
        assert result.filename.endswith(".pdf")


class TestCleanupOldFiles:
    """Testes para cleanup_old_files()."""

    def test_removes_old_files(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Deve remover arquivos mais antigos que max_age_seconds."""
        fake_temp = tmp_path / "fake_system_temp"
        fake_temp.mkdir()
        app_dir = fake_temp / "rc_gestor_uploads"
        app_dir.mkdir()

        # Criar arquivos
        old_file = app_dir / "old.pdf"
        old_file.write_text("conteúdo antigo")

        recent_file = app_dir / "recent.pdf"
        recent_file.write_text("conteúdo recente")

        monkeypatch.setattr("tempfile.gettempdir", lambda: str(fake_temp))

        # Modificar mtime do arquivo antigo
        old_time = time.time() - (8 * 24 * 60 * 60)  # 8 dias atrás
        import os

        os.utime(old_file, (old_time, old_time))

        result = cleanup_old_files(max_age_seconds=7 * 24 * 60 * 60)

        assert result["removed"] == 1
        assert result["failed"] == 0
        assert not old_file.exists()
        assert recent_file.exists()

    def test_keeps_recent_files(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Não deve remover arquivos recentes."""
        fake_temp = tmp_path / "fake_system_temp"
        fake_temp.mkdir()
        app_dir = fake_temp / "rc_gestor_uploads"
        app_dir.mkdir()

        recent = app_dir / "recent.pdf"
        recent.write_text("recente")

        monkeypatch.setattr("tempfile.gettempdir", lambda: str(fake_temp))

        result = cleanup_old_files(max_age_seconds=7 * 24 * 60 * 60)

        assert result["removed"] == 0
        assert recent.exists()

    def test_handles_missing_directory(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Se diretório não existir, deve retornar stats zeradas."""
        fake_temp = tmp_path / "fake_system_temp"
        fake_temp.mkdir()

        monkeypatch.setattr("tempfile.gettempdir", lambda: str(fake_temp))

        result = cleanup_old_files()

        assert result["removed"] == 0
        assert result["failed"] == 0

    def test_counts_total_bytes_removed(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Deve contar total de bytes removidos."""
        fake_temp = tmp_path / "fake_system_temp"
        fake_temp.mkdir()
        app_dir = fake_temp / "rc_gestor_uploads"
        app_dir.mkdir()

        old_file = app_dir / "old.pdf"
        old_file.write_bytes(b"x" * 1024)  # 1 KB

        monkeypatch.setattr("tempfile.gettempdir", lambda: str(fake_temp))

        # Modificar mtime
        old_time = time.time() - (8 * 24 * 60 * 60)
        import os

        os.utime(old_file, (old_time, old_time))

        result = cleanup_old_files(max_age_seconds=7 * 24 * 60 * 60)

        assert result["total_bytes"] == 1024

    def test_ignores_subdirectories(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Deve ignorar subdiretórios, apenas processar arquivos."""
        fake_temp = tmp_path / "fake_system_temp"
        fake_temp.mkdir()
        app_dir = fake_temp / "rc_gestor_uploads"
        app_dir.mkdir()

        subdir = app_dir / "subdir"
        subdir.mkdir()

        monkeypatch.setattr("tempfile.gettempdir", lambda: str(fake_temp))

        result = cleanup_old_files()

        assert result["removed"] == 0
        assert subdir.exists()


class TestCleanupOnStartup:
    """Testes para cleanup_on_startup()."""

    @patch("src.modules.uploads.temp_files.cleanup_old_files")
    def test_calls_cleanup_old_files(self, mock_cleanup: Mock):
        """Deve chamar cleanup_old_files()."""
        mock_cleanup.return_value = {"removed": 0, "failed": 0, "total_bytes": 0}

        cleanup_on_startup()

        mock_cleanup.assert_called_once()

    @patch("src.modules.uploads.temp_files.cleanup_old_files")
    def test_handles_cleanup_errors_gracefully(self, mock_cleanup: Mock):
        """Se cleanup falhar, não deve propagar exceção."""
        mock_cleanup.side_effect = RuntimeError("Falha no cleanup")

        # Não deve levantar exceção
        cleanup_on_startup()
