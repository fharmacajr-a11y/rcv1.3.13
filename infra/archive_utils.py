"""
Utilitários para extração de arquivos compactados (ZIP e RAR).

ZIP: Usa zipfile (built-in Python)
RAR: Usa 7-Zip CLI (empacotado com o aplicativo)
"""
from __future__ import annotations

import sys
import subprocess
import zipfile
import shutil
from pathlib import Path
from typing import Union


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


def extract_archive(src: Union[str, Path], out_dir: Union[str, Path]) -> Path:
    """
    Extrai arquivo compactado (ZIP ou RAR) para o diretório de destino.

    Args:
        src: Caminho para o arquivo compactado (.zip ou .rar)
        out_dir: Diretório onde os arquivos serão extraídos

    Returns:
        Path para o diretório de extração

    Raises:
        ArchiveError: Se o formato não for suportado ou houver erro na extração
    """
    src = Path(src)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    ext = src.suffix.lower()

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

    else:
        raise ArchiveError(
            f"Formato não suportado: {ext}\n"
            "Apenas arquivos .zip e .rar são aceitos."
        )


def is_7z_available() -> bool:
    """
    Verifica se o 7-Zip está disponível.

    Returns:
        True se 7z.exe foi encontrado, False caso contrário
    """
    return find_7z() is not None
