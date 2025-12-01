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
    is_supported_archive,
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

        Nota: Este teste valida comportamento com arquivo inexistente.
        Como não podemos criar RAR programaticamente sem ferramentas externas,
        validamos apenas o tratamento de erro.
        """
        # Testar com arquivo inexistente
        rar_path = tmp_path / "nonexistent.rar"
        extract_dir = tmp_path / "extracted_rar"

        with pytest.raises(ArchiveError, match="Erro ao extrair RAR"):
            extract_archive(rar_path, extract_dir)

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


class TestIsSupportedArchive:
    """Testes para a função is_supported_archive."""

    def test_is_supported_archive_zip(self) -> None:
        """Testa que .zip é suportado."""
        assert is_supported_archive("arquivo.zip")
        assert is_supported_archive("arquivo.ZIP")
        assert is_supported_archive(Path("arquivo.zip"))
        assert is_supported_archive("/caminho/completo/arquivo.zip")

    def test_is_supported_archive_rar(self) -> None:
        """Testa que .rar é suportado."""
        assert is_supported_archive("arquivo.rar")
        assert is_supported_archive("arquivo.RAR")
        assert is_supported_archive(Path("arquivo.rar"))

    def test_is_supported_archive_7z(self) -> None:
        """Testa que .7z é suportado."""
        assert is_supported_archive("arquivo.7z")
        assert is_supported_archive("arquivo.7Z")
        assert is_supported_archive(Path("arquivo.7z"))

    def test_is_supported_archive_7z_volumes(self) -> None:
        """Testa que volumes .7z são suportados (.7z.001, .7z.002, etc.)."""
        assert is_supported_archive("arquivo.7z.001")
        assert is_supported_archive("arquivo.7z.002")
        assert is_supported_archive("arquivo.7z.999")
        assert is_supported_archive("arquivo.7Z.001")
        assert is_supported_archive(Path("arquivo.7z.001"))

    def test_is_supported_archive_not_supported(self) -> None:
        """Testa que formatos não suportados retornam False."""
        assert not is_supported_archive("arquivo.tar")
        assert not is_supported_archive("arquivo.tar.gz")
        assert not is_supported_archive("arquivo.txt")
        assert not is_supported_archive("arquivo.pdf")
        assert not is_supported_archive("arquivo")
        assert not is_supported_archive("")

    def test_is_supported_archive_7z_invalid_volume(self) -> None:
        """Testa que volumes .7z inválidos retornam False."""
        assert not is_supported_archive("arquivo.7z.abc")
        assert not is_supported_archive("arquivo.7z.1a2")
        assert not is_supported_archive("arquivo.7z.")


class TestExtractArchiveEdgeCases:
    """Testes para casos extremos de extract_archive."""

    def test_extract_zip_nonexistent_file(self, tmp_path: Path) -> None:
        """Testa que arquivo ZIP inexistente levanta ArchiveError."""
        zip_path = tmp_path / "nonexistent.zip"
        extract_dir = tmp_path / "extracted"

        with pytest.raises(ArchiveError, match="Erro ao extrair ZIP"):
            extract_archive(zip_path, extract_dir)

    def test_extract_rar_with_password_raises_error(self, tmp_path: Path, monkeypatch) -> None:
        """Testa que RAR com senha levanta ArchiveError (não suportado)."""
        # Criar arquivo RAR fake
        rar_path = tmp_path / "test.rar"
        rar_path.write_text("fake rar")
        extract_dir = tmp_path / "extracted"

        # Simular 7-Zip disponível
        def mock_find_7z():
            return Path("/fake/7z.exe")

        monkeypatch.setattr("infra.archive_utils.find_7z", mock_find_7z)

        with pytest.raises(ArchiveError, match="Senha não é suportada para arquivos .rar"):
            extract_archive(rar_path, extract_dir, password="secret")

    def test_extract_7z_corrupted(self, tmp_path: Path) -> None:
        """Testa que .7z corrompido levanta ArchiveError."""
        pytest.importorskip("py7zr", reason="py7zr não instalado")

        seven_z_path = tmp_path / "corrupted.7z"
        extract_dir = tmp_path / "extracted"

        # Criar arquivo falso (não é 7z válido)
        seven_z_path.write_text("Este não é um arquivo 7z válido")

        with pytest.raises(ArchiveError, match="7z corrompido ou inválido"):
            extract_archive(seven_z_path, extract_dir)

    def test_extract_7z_volume_corrupted(self, tmp_path: Path) -> None:
        """Testa que volume .7z corrompido levanta ArchiveError específico."""
        pytest.importorskip("py7zr", reason="py7zr não instalado")

        volume_path = tmp_path / "archive.7z.001"
        extract_dir = tmp_path / "extracted"

        # Criar arquivo falso de volume
        volume_path.write_text("Fake 7z volume")

        with pytest.raises(ArchiveError, match="volume inválido/corrompido"):
            extract_archive(volume_path, extract_dir)

    def test_extract_7z_with_password(self, tmp_path: Path) -> None:
        """Testa extração de .7z com senha."""
        pytest.importorskip("py7zr", reason="py7zr não instalado")
        import py7zr

        seven_z_path = tmp_path / "protected.7z"
        extract_dir = tmp_path / "extracted"

        # Criar arquivo com senha
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "secret.txt").write_text("Conteúdo secreto", encoding="utf-8")

        with py7zr.SevenZipFile(seven_z_path, "w", password="mypassword") as archive:
            archive.writeall(source_dir, arcname="")

        # Extrair com senha correta
        result = extract_archive(seven_z_path, extract_dir, password="mypassword")

        assert result == extract_dir
        assert (extract_dir / "secret.txt").exists()
        assert (extract_dir / "secret.txt").read_text(encoding="utf-8") == "Conteúdo secreto"

    def test_extract_7z_volume_file(self, tmp_path: Path) -> None:
        """Testa extração de volume .7z (arquivo.7z.001)."""
        pytest.importorskip("py7zr", reason="py7zr não instalado")
        import py7zr

        # Criar arquivo .7z normal primeiro (simulando volume único)
        volume_path = tmp_path / "archive.7z.001"
        extract_dir = tmp_path / "extracted"

        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "file_in_volume.txt").write_text("Conteúdo do volume", encoding="utf-8")

        # Criar como .7z normal (py7zr não cria volumes multi-parte facilmente)
        with py7zr.SevenZipFile(volume_path, "w") as archive:
            archive.writeall(source_dir, arcname="")

        # Extrair via volume
        result = extract_archive(volume_path, extract_dir)

        assert result == extract_dir
        assert (extract_dir / "file_in_volume.txt").exists()


class TestRarExtractionWithSubprocess:
    """Testes para cenários de RAR usando subprocess."""

    @pytest.mark.skipif(not is_7z_available(), reason="7-Zip não encontrado")
    def test_extract_rar_subprocess_error(self, tmp_path: Path, monkeypatch) -> None:
        """Testa erro de subprocess ao extrair RAR."""
        import subprocess

        rar_path = tmp_path / "test.rar"
        rar_path.write_text("fake rar content")
        extract_dir = tmp_path / "extracted"

        # Mock subprocess.run para simular falha
        def mock_run(*args, **kwargs):
            class MockResult:
                returncode = 2
                stderr = "Erro simulado do 7-Zip"
                stdout = "Saída de debug"

            return MockResult()

        monkeypatch.setattr(subprocess, "run", mock_run)

        with pytest.raises(ArchiveError, match="Falha ao extrair .rar"):
            extract_archive(rar_path, extract_dir)

    @pytest.mark.skipif(not is_7z_available(), reason="7-Zip não encontrado")
    def test_extract_rar_subprocess_error_stderr_only(self, tmp_path: Path, monkeypatch) -> None:
        """Testa erro de subprocess com apenas stderr."""
        import subprocess

        rar_path = tmp_path / "test.rar"
        rar_path.write_text("fake rar content")
        extract_dir = tmp_path / "extracted"

        def mock_run(*args, **kwargs):
            class MockResult:
                returncode = 1
                stderr = "Erro crítico"
                stdout = ""

            return MockResult()

        monkeypatch.setattr(subprocess, "run", mock_run)

        with pytest.raises(ArchiveError, match="Erro: Erro crítico"):
            extract_archive(rar_path, extract_dir)

    @pytest.mark.skipif(not is_7z_available(), reason="7-Zip não encontrado")
    def test_extract_rar_subprocess_error_stdout_only(self, tmp_path: Path, monkeypatch) -> None:
        """Testa erro de subprocess com apenas stdout."""
        import subprocess

        rar_path = tmp_path / "test.rar"
        rar_path.write_text("fake rar content")
        extract_dir = tmp_path / "extracted"

        def mock_run(*args, **kwargs):
            class MockResult:
                returncode = 1
                stderr = ""
                stdout = "Informação de debug"

            return MockResult()

        monkeypatch.setattr(subprocess, "run", mock_run)

        with pytest.raises(ArchiveError, match="Saída: Informação de debug"):
            extract_archive(rar_path, extract_dir)

    def test_extract_rar_file_not_found_error(self, tmp_path: Path, monkeypatch) -> None:
        """Testa FileNotFoundError ao executar 7-Zip."""
        import subprocess

        rar_path = tmp_path / "test.rar"
        rar_path.write_text("fake rar")
        extract_dir = tmp_path / "extracted"

        # Mock find_7z para retornar caminho inexistente
        def mock_find_7z():
            return Path("/caminho/inexistente/7z.exe")

        monkeypatch.setattr("infra.archive_utils.find_7z", mock_find_7z)

        # Mock subprocess.run para levantar FileNotFoundError
        def mock_run(*args, **kwargs):
            raise FileNotFoundError("7z.exe não encontrado")

        monkeypatch.setattr(subprocess, "run", mock_run)

        with pytest.raises(ArchiveError, match="7-Zip não encontrado em:"):
            extract_archive(rar_path, extract_dir)

    def test_extract_rar_generic_exception(self, tmp_path: Path, monkeypatch) -> None:
        """Testa Exception genérica ao extrair RAR."""
        import subprocess

        rar_path = tmp_path / "test.rar"
        rar_path.write_text("fake rar")
        extract_dir = tmp_path / "extracted"

        # Mock find_7z
        def mock_find_7z():
            return Path("/fake/7z.exe")

        monkeypatch.setattr("infra.archive_utils.find_7z", mock_find_7z)

        # Mock subprocess.run para levantar exceção genérica
        def mock_run(*args, **kwargs):
            raise RuntimeError("Erro inesperado no subprocess")

        monkeypatch.setattr(subprocess, "run", mock_run)

        with pytest.raises(ArchiveError, match="Erro ao extrair RAR"):
            extract_archive(rar_path, extract_dir)

    def test_extract_rar_success(self, tmp_path: Path, monkeypatch) -> None:
        """Testa extração bem-sucedida de RAR via mock."""
        import subprocess

        rar_path = tmp_path / "test.rar"
        rar_path.write_text("fake rar")
        extract_dir = tmp_path / "extracted"

        # Mock find_7z
        def mock_find_7z():
            return Path("/fake/7z.exe")

        monkeypatch.setattr("infra.archive_utils.find_7z", mock_find_7z)

        # Mock subprocess.run para simular sucesso
        def mock_run(*args, **kwargs):
            # Criar arquivo de saída para simular extração
            extract_dir.mkdir(parents=True, exist_ok=True)
            (extract_dir / "extracted_file.txt").write_text("content")

            class MockResult:
                returncode = 0
                stderr = ""
                stdout = ""

            return MockResult()

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = extract_archive(rar_path, extract_dir)
        assert result == extract_dir
        assert (extract_dir / "extracted_file.txt").exists()


class Test7ZExtractionErrors:
    """Testes para erros específicos de extração 7z."""

    def test_extract_7z_permission_error(self, tmp_path: Path, monkeypatch) -> None:
        """Testa PermissionError ao extrair .7z."""
        pytest.importorskip("py7zr", reason="py7zr não instalado")
        import py7zr

        seven_z_path = tmp_path / "test.7z"
        extract_dir = tmp_path / "extracted"

        # Criar arquivo 7z válido
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "file.txt").write_text("content", encoding="utf-8")

        with py7zr.SevenZipFile(seven_z_path, "w") as archive:
            archive.writeall(source_dir, arcname="")

        # Mock extractall para levantar PermissionError

        def mock_extractall(self, path=None, **kwargs):
            raise PermissionError("Acesso negado")

        monkeypatch.setattr(py7zr.SevenZipFile, "extractall", mock_extractall)

        with pytest.raises(ArchiveError, match="Permissão negada ao extrair .7z"):
            extract_archive(seven_z_path, extract_dir)

    def test_extract_7z_password_required(self, tmp_path: Path, monkeypatch) -> None:
        """Testa erro quando .7z requer senha mas não foi fornecida."""
        pytest.importorskip("py7zr", reason="py7zr não instalado")
        import py7zr

        seven_z_path = tmp_path / "protected.7z"
        extract_dir = tmp_path / "extracted"

        # Criar arquivo com senha
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "file.txt").write_text("content", encoding="utf-8")

        with py7zr.SevenZipFile(seven_z_path, "w", password="secret") as archive:
            archive.writeall(source_dir, arcname="")

        # Mock extractall para levantar exceção com "password" na mensagem

        def mock_extractall(self, path=None, **kwargs):
            raise Exception("Password is required for encrypted archive")

        monkeypatch.setattr(py7zr.SevenZipFile, "extractall", mock_extractall)

        with pytest.raises(ArchiveError, match="requer senha para extração"):
            extract_archive(seven_z_path, extract_dir)

    def test_extract_7z_crc_error(self, tmp_path: Path, monkeypatch) -> None:
        """Testa erro de CRC ao extrair .7z."""
        pytest.importorskip("py7zr", reason="py7zr não instalado")
        import py7zr

        seven_z_path = tmp_path / "test.7z"
        extract_dir = tmp_path / "extracted"

        # Criar arquivo 7z válido
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "file.txt").write_text("content", encoding="utf-8")

        with py7zr.SevenZipFile(seven_z_path, "w") as archive:
            archive.writeall(source_dir, arcname="")

        # Mock extractall para levantar exceção com "crc" na mensagem

        def mock_extractall(self, path=None, **kwargs):
            raise Exception("CRC check failed")

        monkeypatch.setattr(py7zr.SevenZipFile, "extractall", mock_extractall)

        with pytest.raises(ArchiveError, match="Erro de CRC"):
            extract_archive(seven_z_path, extract_dir)

    def test_extract_7z_generic_error(self, tmp_path: Path, monkeypatch) -> None:
        """Testa exceção genérica ao extrair .7z."""
        pytest.importorskip("py7zr", reason="py7zr não instalado")
        import py7zr

        seven_z_path = tmp_path / "test.7z"
        extract_dir = tmp_path / "extracted"

        # Criar arquivo 7z válido
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "file.txt").write_text("content", encoding="utf-8")

        with py7zr.SevenZipFile(seven_z_path, "w") as archive:
            archive.writeall(source_dir, arcname="")

        # Mock extractall para levantar exceção genérica

        def mock_extractall(self, path=None, **kwargs):
            raise RuntimeError("Unexpected error during extraction")

        monkeypatch.setattr(py7zr.SevenZipFile, "extractall", mock_extractall)

        with pytest.raises(ArchiveError, match="Erro ao extrair 7Z"):
            extract_archive(seven_z_path, extract_dir)


class TestFind7z:
    """Testes para a função find_7z."""

    def test_find_7z_in_bundled_paths(self, tmp_path: Path, monkeypatch) -> None:
        """Testa que find_7z encontra executável em caminhos empacotados."""
        # Criar um 7z.exe fake em um dos caminhos
        fake_7z_dir = tmp_path / "infra" / "bin" / "7zip"
        fake_7z_dir.mkdir(parents=True)
        fake_7z = fake_7z_dir / "7z.exe"
        fake_7z.write_text("fake 7z")

        # Mock resource_path para retornar nosso caminho temporário
        def mock_resource_path(*parts):
            return tmp_path.joinpath(*parts)

        monkeypatch.setattr("infra.archive_utils.resource_path", mock_resource_path)

        # Mock shutil.which para não encontrar no PATH
        monkeypatch.setattr("shutil.which", lambda x: None)

        result = find_7z()
        assert result == fake_7z

    def test_find_7z_in_system_path_exe(self, tmp_path: Path, monkeypatch) -> None:
        """Testa que find_7z encontra 7z.exe no PATH do sistema."""
        fake_7z = tmp_path / "7z.exe"
        fake_7z.write_text("fake 7z")

        # Mock resource_path para retornar caminhos inexistentes
        def mock_resource_path(*parts):
            return Path("/nonexistent") / Path(*parts)

        monkeypatch.setattr("infra.archive_utils.resource_path", mock_resource_path)

        # Mock shutil.which para retornar nosso executável
        def mock_which(name):
            if name == "7z.exe":
                return str(fake_7z)
            return None

        monkeypatch.setattr("shutil.which", mock_which)

        result = find_7z()
        assert result == fake_7z

    def test_find_7z_in_system_path_no_ext(self, tmp_path: Path, monkeypatch) -> None:
        """Testa que find_7z encontra 7z (sem .exe) no PATH."""
        fake_7z = tmp_path / "7z"
        fake_7z.write_text("fake 7z")

        # Mock resource_path
        def mock_resource_path(*parts):
            return Path("/nonexistent") / Path(*parts)

        monkeypatch.setattr("infra.archive_utils.resource_path", mock_resource_path)

        # Mock shutil.which - 7z.exe não encontrado, mas 7z sim
        def mock_which(name):
            if name == "7z":
                return str(fake_7z)
            return None

        monkeypatch.setattr("shutil.which", mock_which)

        result = find_7z()
        assert result == fake_7z
