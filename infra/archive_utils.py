"""
Utilitários para extração de arquivos compactados (ZIP, RAR e 7Z).

ZIP: Usa zipfile (built-in Python)
RAR: Usa 7-Zip CLI (empacotado com o aplicativo)
7Z: Usa py7zr (biblioteca Python) - suporta senha e volumes (.7z.001, .7z.002...)
"""
from __future__ import annotations

import sys
import subprocess
import zipfile
import shutil
from pathlib import Path
from typing import Union

# Constantes de extensões suportadas
SUPPORTED_ARCHIVES = {".zip", ".rar", ".7z"}
SUPPORTED_7Z_VOLUMES = True  # Suporta .7z.001, .7z.002, etc.


class ArchiveError(Exception):
    """Erro ao processar arquivo compactado."""
    pass


def resource_path(*parts: str) -> Path:
    """
    Retorna o caminho para um recurso, considerando se está empacotado com PyInstaller.

    Args:
        *parts: Partes do caminho a serem unidas

    Returns:
        Path absoluto para o recurso
    """
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return base.joinpath(*parts)


def find_7z() -> Path | None:
    """
    Procura o executável 7z.exe (primeiro no bundle, depois no PATH do sistema).

    Returns:
        Path para 7z.exe se encontrado, None caso contrário
    """
    # 1) Binário empacotado no build
    for p in (
        resource_path("infra", "bin", "7zip", "7z.exe"),
        resource_path("7z", "7z.exe"),
        resource_path("bin", "7zip", "7z.exe"),
    ):
        if p.is_file():
            return p

    # 2) PATH do sistema
    exe_path = shutil.which("7z.exe") or shutil.which("7z")
    return Path(exe_path) if exe_path else None


def extract_archive(
    src: Union[str, Path],
    out_dir: Union[str, Path],
    *,
    password: str | None = None
) -> Path:
    """
    Extrai arquivo compactado (ZIP, RAR ou 7Z) para o diretório de destino.

    Args:
        src: Caminho para o arquivo compactado (.zip, .rar, .7z ou .7z.001 para volumes)
        out_dir: Diretório onde os arquivos serão extraídos
        password: Senha opcional para arquivos protegidos (suportado apenas em .7z)

    Returns:
        Path para o diretório de extração

    Raises:
        ArchiveError: Se o formato não for suportado ou houver erro na extração

    Nota:
        - Volumes .7z (.7z.001, .7z.002...) devem ser abertos pelo primeiro volume (.7z.001)
        - Senha é suportada apenas para arquivos .7z
    """
    src = Path(src)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Detectar extensão e volumes
    name_lower = src.name.lower()
    ext = src.suffix.lower()

    # Verificar se é volume .7z (ex: arquivo.7z.001)
    is_7z_volume = ".7z." in name_lower and name_lower.split(".7z.")[-1].isdigit()

    if ext == ".zip":
        try:
            with zipfile.ZipFile(src, "r", allowZip64=True) as zf:
                zf.extractall(out)
            return out
        except zipfile.BadZipFile as e:
            raise ArchiveError(f"Arquivo ZIP corrompido ou inválido: {e}")
        except Exception as e:
            raise ArchiveError(f"Erro ao extrair ZIP: {e}")

    elif ext == ".rar":
        if password:
            raise ArchiveError("Senha não é suportada para arquivos .rar via 7-Zip CLI.")

        seven_zip = find_7z()
        if not seven_zip:
            raise ArchiveError(
                "7-Zip não encontrado para extrair .rar.\n"
                "Certifique-se de que o 7z.exe está incluído no build ou instalado no sistema."
            )

        try:
            cmd = [str(seven_zip), "x", "-y", f"-o{out}", str(src)]
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace"
            )

            if proc.returncode != 0:
                error_msg = f"Falha ao extrair .rar (7-Zip retornou código {proc.returncode})."
                if proc.stderr:
                    error_msg += f"\nErro: {proc.stderr}"
                if proc.stdout:
                    error_msg += f"\nSaída: {proc.stdout}"
                raise ArchiveError(error_msg)

            return out
        except FileNotFoundError:
            raise ArchiveError(f"7-Zip não encontrado em: {seven_zip}")
        except Exception as e:
            raise ArchiveError(f"Erro ao extrair RAR: {e}")

    elif ext == ".7z" or is_7z_volume:
        try:
            import py7zr  # Import tardio para não quebrar se py7zr não estiver instalado
        except ImportError as e:
            raise ArchiveError(
                "Suporte a .7z indisponível.\n"
                "Instale a dependência: pip install py7zr"
            ) from e

        try:
            # Para volumes, abrir diretamente pelo arquivo especificado (geralmente .7z.001)
            with py7zr.SevenZipFile(src, mode="r", password=password) as z:
                z.extractall(path=out)
            return out
        except (py7zr.Bad7zFile, AttributeError) as e:
            # Bad7zFile ou arquivo corrompido
            if is_7z_volume:
                raise ArchiveError(
                    f"Arquivo .7z volume inválido/corrompido.\n"
                    f"Certifique-se de que todos os volumes (.7z.001, .7z.002...) estão presentes.\n"
                    f"Erro: {e}"
                ) from e
            else:
                raise ArchiveError(f"Arquivo .7z corrompido ou inválido: {e}") from e
        except PermissionError as e:
            raise ArchiveError(f"Permissão negada ao extrair .7z: {e}") from e
        except Exception as e:
            # Capturar erros de senha ou CRC
            error_msg = str(e).lower()
            if "password" in error_msg or "encrypted" in error_msg:
                raise ArchiveError(
                    "Este arquivo .7z requer senha para extração.\n"
                    "Atualmente a interface não suporta arquivos protegidos por senha."
                ) from e
            elif "crc" in error_msg or "checksum" in error_msg:
                raise ArchiveError(
                    "Erro de CRC: arquivo .7z corrompido ou senha incorreta."
                ) from e
            else:
                raise ArchiveError(f"Erro ao extrair 7Z: {e}") from e

    else:
        raise ArchiveError(
            f"Formato não suportado: {ext}\n"
            f"Apenas arquivos {', '.join(SUPPORTED_ARCHIVES)} são aceitos.\n"
            f"Volumes .7z (.7z.001, .7z.002...) também são suportados."
        )


def is_7z_available() -> bool:
    """
    Verifica se o 7-Zip está disponível.

    Returns:
        True se 7z.exe foi encontrado, False caso contrário
    """
    return find_7z() is not None
