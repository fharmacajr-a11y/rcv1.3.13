"""
Testes para o módulo de seleção de arquivos (file_select).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.ui.dialogs.file_select import (
    ARCHIVE_FILETYPES,
    validate_archive_extension,
)


class TestArchiveFiletypes:
    """Testes para a constante ARCHIVE_FILETYPES."""

    def test_filetypes_structure(self) -> None:
        """Testa que ARCHIVE_FILETYPES tem a estrutura correta."""
        assert isinstance(ARCHIVE_FILETYPES, list)
        assert len(ARCHIVE_FILETYPES) == 4
        
        # Primeiro item: tupla com label e tupla de padrões
        first = ARCHIVE_FILETYPES[0]
        assert first[0] == "Arquivos compactados"
        assert isinstance(first[1], tuple)
        assert first[1] == ("*.zip", "*.rar")
        
        # Segundo item: ZIP
        assert ARCHIVE_FILETYPES[1] == ("ZIP", "*.zip")
        
        # Terceiro item: RAR
        assert ARCHIVE_FILETYPES[2] == ("RAR", "*.rar")
        
        # Quarto item: Todos os arquivos
        assert ARCHIVE_FILETYPES[3] == ("Todos os arquivos", "*.*")

    def test_filetypes_uses_tuples_not_strings(self) -> None:
        """
        Testa que o primeiro item usa tupla de padrões, não string concatenada.
        
        Isso é importante porque Tkinter suporta tuplas, mas não strings
        concatenadas como "*.zip *.rar".
        """
        first_pattern = ARCHIVE_FILETYPES[0][1]
        assert isinstance(first_pattern, tuple), \
            "O padrão deve ser uma tupla, não string"
        assert len(first_pattern) == 2
        assert "*.zip" in first_pattern
        assert "*.rar" in first_pattern


class TestValidateArchiveExtension:
    """Testes para a função validate_archive_extension."""

    def test_accepts_zip_lowercase(self) -> None:
        """Testa que aceita .zip em minúsculas."""
        assert validate_archive_extension("arquivo.zip") is True
        assert validate_archive_extension("/path/to/file.zip") is True

    def test_accepts_zip_uppercase(self) -> None:
        """Testa que aceita .ZIP em maiúsculas."""
        assert validate_archive_extension("ARQUIVO.ZIP") is True
        assert validate_archive_extension("/path/to/FILE.ZIP") is True

    def test_accepts_zip_mixed_case(self) -> None:
        """Testa que aceita .ZiP em caso misto."""
        assert validate_archive_extension("arquivo.ZiP") is True

    def test_accepts_rar_lowercase(self) -> None:
        """Testa que aceita .rar em minúsculas."""
        assert validate_archive_extension("arquivo.rar") is True
        assert validate_archive_extension("/path/to/file.rar") is True

    def test_accepts_rar_uppercase(self) -> None:
        """Testa que aceita .RAR em maiúsculas."""
        assert validate_archive_extension("ARQUIVO.RAR") is True
        assert validate_archive_extension("/path/to/FILE.RAR") is True

    def test_accepts_rar_mixed_case(self) -> None:
        """Testa que aceita .RaR em caso misto."""
        assert validate_archive_extension("arquivo.RaR") is True

    def test_rejects_7z(self) -> None:
        """Testa que rejeita arquivos .7z."""
        assert validate_archive_extension("arquivo.7z") is False
        assert validate_archive_extension("ARQUIVO.7Z") is False

    def test_rejects_tar(self) -> None:
        """Testa que rejeita arquivos .tar."""
        assert validate_archive_extension("arquivo.tar") is False
        assert validate_archive_extension("arquivo.tar.gz") is False

    def test_rejects_other_extensions(self) -> None:
        """Testa que rejeita outras extensões."""
        assert validate_archive_extension("arquivo.txt") is False
        assert validate_archive_extension("arquivo.pdf") is False
        assert validate_archive_extension("arquivo.exe") is False
        assert validate_archive_extension("arquivo") is False

    def test_accepts_path_objects(self) -> None:
        """Testa que funciona com objetos Path."""
        assert validate_archive_extension(str(Path("arquivo.zip"))) is True
        assert validate_archive_extension(str(Path("arquivo.rar"))) is True
        assert validate_archive_extension(str(Path("arquivo.7z"))) is False

    def test_handles_multiple_dots(self) -> None:
        """Testa arquivos com múltiplos pontos no nome."""
        assert validate_archive_extension("arquivo.backup.zip") is True
        assert validate_archive_extension("arquivo.v1.0.rar") is True
        assert validate_archive_extension("arquivo.old.7z") is False


class TestFileSelectIntegration:
    """Testes de integração (se necessário)."""

    def test_module_imports_correctly(self) -> None:
        """Testa que o módulo pode ser importado sem erros."""
        from src.ui.dialogs.file_select import (
            select_archive_file,
            select_archive_files,
            validate_archive_extension,
            ARCHIVE_FILETYPES,
        )
        
        # Verificar que as funções foram importadas
        assert callable(select_archive_file)
        assert callable(select_archive_files)
        assert callable(validate_archive_extension)
        assert isinstance(ARCHIVE_FILETYPES, list)

    def test_module_in_dialogs_init(self) -> None:
        """Testa que o módulo está exposto em __init__.py."""
        from src.ui.dialogs import (
            select_archive_file,
            select_archive_files,
            validate_archive_extension,
            ARCHIVE_FILETYPES,
        )
        
        assert callable(select_archive_file)
        assert callable(select_archive_files)
        assert callable(validate_archive_extension)
        assert isinstance(ARCHIVE_FILETYPES, list)
