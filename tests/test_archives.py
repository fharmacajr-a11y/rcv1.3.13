"""
Testes para extração de arquivos compactados (ZIP, RAR e 7Z).
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from infra.archive_utils import (
    ArchiveError,
    extract_archive,
    find_7z,
    is_7z_available,
)


class TestZipExtraction:
    """Testes para extração de arquivos ZIP."""

    def test_extract_zip_simple(self, tmp_path: Path) -> None:
        """Testa extração de arquivo ZIP simples."""
        # Criar um ZIP de teste
        zip_path = tmp_path / "test.zip"
        extract_dir = tmp_path / "extracted"

        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("file1.txt", "Conteúdo do arquivo 1")
            zf.writestr("subdir/file2.txt", "Conteúdo do arquivo 2")

        # Extrair
        result = extract_archive(zip_path, extract_dir)

        # Verificar
        assert result == extract_dir
        assert (extract_dir / "file1.txt").exists()
        assert (extract_dir / "subdir" / "file2.txt").exists()
        assert (extract_dir / "file1.txt").read_text(encoding="utf-8") == "Conteúdo do arquivo 1"
        assert (extract_dir / "subdir" / "file2.txt").read_text(encoding="utf-8") == "Conteúdo do arquivo 2"

    def test_extract_zip_with_special_chars(self, tmp_path: Path) -> None:
        """Testa extração de ZIP com caracteres especiais nos nomes."""
        zip_path = tmp_path / "test_special.zip"
        extract_dir = tmp_path / "extracted"

        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("arquivo_com_acentuação.txt", "Conteúdo com çãõ")
            zf.writestr("pasta/arquivo espaço.txt", "Texto com espaços")

        result = extract_archive(zip_path, extract_dir)

        assert result == extract_dir
        assert (extract_dir / "arquivo_com_acentuação.txt").exists()
        assert (extract_dir / "pasta" / "arquivo espaço.txt").exists()

    def test_extract_zip_empty(self, tmp_path: Path) -> None:
        """Testa extração de ZIP vazio."""
        zip_path = tmp_path / "empty.zip"
        extract_dir = tmp_path / "extracted"

        with zipfile.ZipFile(zip_path, "w"):
            pass  # ZIP vazio

        result = extract_archive(zip_path, extract_dir)

        assert result == extract_dir
        assert extract_dir.exists()
        assert list(extract_dir.iterdir()) == []  # Diretório vazio

    def test_extract_zip_corrupted(self, tmp_path: Path) -> None:
        """Testa que ZIP corrompido levanta ArchiveError."""
        zip_path = tmp_path / "corrupted.zip"
        extract_dir = tmp_path / "extracted"

        # Criar arquivo falso (não é ZIP válido)
        zip_path.write_text("Este não é um arquivo ZIP válido")

        with pytest.raises(ArchiveError, match="ZIP corrompido ou inválido"):
            extract_archive(zip_path, extract_dir)

    def test_extract_zip_allowZip64(self, tmp_path: Path) -> None:
        """Testa que ZIP64 é suportado."""
        zip_path = tmp_path / "test_zip64.zip"
        extract_dir = tmp_path / "extracted"

        # Criar ZIP com allowZip64
        with zipfile.ZipFile(zip_path, "w", allowZip64=True) as zf:
            zf.writestr("large_file.txt", "A" * 1000)

        result = extract_archive(zip_path, extract_dir)

        assert result == extract_dir
        assert (extract_dir / "large_file.txt").exists()


class TestRarExtraction:
    """Testes para extração de arquivos RAR (requer 7-Zip)."""

    @pytest.mark.skipif(not is_7z_available(), reason="7-Zip não encontrado")
    def test_find_7z(self) -> None:
        """Testa que find_7z encontra o executável."""
        seven_zip = find_7z()
        assert seven_zip is not None
        assert seven_zip.exists()
        assert seven_zip.name.lower() in ("7z.exe", "7z")

    @pytest.mark.skipif(not is_7z_available(), reason="7-Zip não encontrado")
    def test_extract_rar_if_available(self, tmp_path: Path) -> None:
        """
        Testa extração de RAR SE 7-Zip estiver disponível.

        Nota: Este teste requer um arquivo RAR de teste.
        Como não podemos criar RAR programaticamente sem ferramentas externas,
        este teste é apenas um placeholder.
        """
        # Para testar RAR de verdade, você precisaria:
        # 1. Ter um arquivo .rar de teste
        # 2. Colocá-lo em tests/fixtures/test.rar
        # 3. Descomente o código abaixo:

        # rar_path = Path(__file__).parent / "fixtures" / "test.rar"
        # if not rar_path.exists():
        #     pytest.skip("Arquivo RAR de teste não encontrado")
        #
        # extract_dir = tmp_path / "extracted_rar"
        # result = extract_archive(rar_path, extract_dir)
        #
        # assert result == extract_dir
        # assert len(list(extract_dir.rglob("*"))) > 0

        pytest.skip("Teste de RAR requer arquivo de teste .rar pré-existente")

    def test_extract_rar_without_7z(self, tmp_path: Path, monkeypatch) -> None:
        """Testa que RAR sem 7-Zip disponível levanta ArchiveError."""

        # Simular que 7-Zip não está disponível
        def mock_find_7z():
            return None

        monkeypatch.setattr("infra.archive_utils.find_7z", mock_find_7z)

        rar_path = tmp_path / "test.rar"
        rar_path.write_text("fake rar")
        extract_dir = tmp_path / "extracted"

        with pytest.raises(ArchiveError, match="7-Zip não encontrado"):
            extract_archive(rar_path, extract_dir)


class Test7ZExtraction:
    """Testes para extração de arquivos .7z."""

    def test_extract_7z_simple(self, tmp_path: Path) -> None:
        """Testa extração de arquivo .7z simples."""
        pytest.importorskip("py7zr", reason="py7zr não instalado")
        import py7zr

        # Criar arquivo .7z de teste
        seven_z_path = tmp_path / "test.7z"
        extract_dir = tmp_path / "extracted"

        # Criar estrutura para compactar
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "file1.txt").write_text("Conteúdo do arquivo 1", encoding="utf-8")
        subdir = source_dir / "subdir"
        subdir.mkdir()
        (subdir / "file2.txt").write_text("Conteúdo do arquivo 2", encoding="utf-8")

        # Compactar
        with py7zr.SevenZipFile(seven_z_path, "w") as archive:
            archive.writeall(source_dir, arcname="")

        # Extrair
        result = extract_archive(seven_z_path, extract_dir)

        # Verificar
        assert result == extract_dir
        assert (extract_dir / "file1.txt").exists()
        assert (extract_dir / "subdir" / "file2.txt").exists()
        assert (extract_dir / "file1.txt").read_text(encoding="utf-8") == "Conteúdo do arquivo 1"
        assert (extract_dir / "subdir" / "file2.txt").read_text(encoding="utf-8") == "Conteúdo do arquivo 2"

    def test_extract_7z_without_py7zr(self, tmp_path: Path, monkeypatch) -> None:
        """Testa que .7z sem py7zr disponível levanta ArchiveError."""
        # Simular ImportError ao importar py7zr
        import sys

        # Guardar módulo original se existir
        original_py7zr = sys.modules.get("py7zr")

        # Remover py7zr dos módulos
        if "py7zr" in sys.modules:
            sys.modules.pop("py7zr")

        # Forçar ImportError
        def mock_import(name, *args, **kwargs):
            if name == "py7zr":
                raise ImportError("Mocked import error")
            return original_import(name, *args, **kwargs)

        import builtins

        original_import = builtins.__import__
        monkeypatch.setattr(builtins, "__import__", mock_import)

        seven_z_path = tmp_path / "test.7z"
        seven_z_path.write_text("fake 7z")
        extract_dir = tmp_path / "extracted"

        try:
            with pytest.raises(ArchiveError, match="Suporte a .7z indisponível"):
                extract_archive(seven_z_path, extract_dir)
        finally:
            # Restaurar py7zr se estava carregado
            if original_py7zr is not None:
                sys.modules["py7zr"] = original_py7zr


class TestArchiveUtils:
    """Testes para funções utilitárias."""

    def test_unsupported_format(self, tmp_path: Path) -> None:
        """Testa que formato não suportado levanta ArchiveError."""
        tar_path = tmp_path / "test.tar"
        tar_path.write_text("fake tar")
        extract_dir = tmp_path / "extracted"

        with pytest.raises(ArchiveError, match="Formato não suportado: .tar"):
            extract_archive(tar_path, extract_dir)

    def test_extract_creates_output_dir(self, tmp_path: Path) -> None:
        """Testa que o diretório de saída é criado se não existir."""
        zip_path = tmp_path / "test.zip"
        extract_dir = tmp_path / "nested" / "dir" / "extracted"

        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("file.txt", "content")

        assert not extract_dir.exists()

        result = extract_archive(zip_path, extract_dir)

        assert result == extract_dir
        assert extract_dir.exists()
        assert (extract_dir / "file.txt").exists()

    def test_is_7z_available(self) -> None:
        """Testa que is_7z_available retorna bool."""
        result = is_7z_available()
        assert isinstance(result, bool)


class TestResourcePath:
    """Testes para a função resource_path."""

    def test_resource_path_returns_path(self) -> None:
        """Testa que resource_path retorna um Path."""
        from infra.archive_utils import resource_path

        result = resource_path("infra", "bin", "7zip")
        assert isinstance(result, Path)
        assert "infra" in str(result) or "_MEIPASS" in str(result) or "7zip" in str(result)

    def test_resource_path_with_meipass(self, monkeypatch, tmp_path: Path) -> None:
        """Testa resource_path quando rodando em bundle PyInstaller."""
        import sys
        from infra.archive_utils import resource_path

        # Simular _MEIPASS do PyInstaller (adicionar atributo temporário)
        monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

        result = resource_path("subdir", "file.txt")
        assert str(tmp_path) in str(result)
        assert result == tmp_path / "subdir" / "file.txt"
