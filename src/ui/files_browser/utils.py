# -*- coding: utf-8 -*-
"""
Utilitários do File Browser.

Funções auxiliares puras (sem estado) que podem ser usadas
independentemente da janela principal.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath


def sanitize_filename(name: str) -> str:
    """
    Remove caracteres inválidos de nomes de arquivo.

    Args:
        name: Nome original do arquivo

    Returns:
        Nome sanitizado (safe para filesystem)

    Examples:
        >>> sanitize_filename('arquivo:invalido?.txt')
        'arquivo_invalido_.txt'
    """
    invalid_chars: str = r'[<>:"/\\|?*]'
    sanitized: str = re.sub(invalid_chars, "_", name).strip()
    return sanitized.rstrip(" .")


def format_file_size(size: int | float | None) -> str:
    """
    Formata tamanho de arquivo em formato legível.

    Args:
        size: Tamanho em bytes (None para pastas)

    Returns:
        String formatada (ex: "1.5 MB", "—" para pastas)

    Examples:
        >>> format_file_size(1536)
        '1.5 KB'
        >>> format_file_size(None)
        '—'
    """
    if size is None:
        return "—"
    if size == 0:
        return "0 B"

    units: list[str] = ["B", "KB", "MB", "GB", "TB"]
    size_value: float = float(size)
    unit_index: int = 0

    while size_value >= 1024 and unit_index < len(units) - 1:
        size_value /= 1024
        unit_index += 1

    if unit_index == 0:
        return f"{int(size_value)} {units[unit_index]}"
    return f"{size_value:.1f} {units[unit_index]}"


def resolve_posix_path(base: str, path: str) -> str:
    """
    Resolve caminho relativo contra uma base POSIX.

    Args:
        base: Caminho base (ex: "org/client")
        path: Caminho relativo (ex: "../other" ou "subfolder")

    Returns:
        Caminho resolvido (normalizado, sem ..)

    Examples:
        >>> resolve_posix_path("org/client/docs", "../data")
        'org/client/data'
        >>> resolve_posix_path("org/client", "")
        'org/client'
    """
    if not path or path == ".":
        return base.strip("/")

    # Usar PurePosixPath para resolver .. e .
    base_path: PurePosixPath = PurePosixPath(base)
    rel_path: PurePosixPath = PurePosixPath(path)

    # Se relativo for absoluto, retorna ele mesmo
    if rel_path.is_absolute():
        return str(rel_path).strip("/")

    # Resolve relativo contra base
    resolved = (base_path / rel_path).as_posix()
    return resolved.strip("/")


def suggest_zip_filename(path: str) -> str:
    """
    Sugere nome para arquivo ZIP baseado no caminho.

    Args:
        path: Caminho da pasta a ser zipada

    Returns:
        Nome sugerido para o ZIP (sem extensão)

    Examples:
        >>> suggest_zip_filename("org/client/GERAL/Auditoria")
        'Auditoria'
        >>> suggest_zip_filename("org/client/")
        'arquivos'
    """
    parts: list[str] = [p for p in path.strip("/").split("/") if p]
    if not parts:
        return "arquivos"

    # Pegar última parte não-vazia
    folder_name: str = parts[-1]
    return sanitize_filename(folder_name) or "arquivos"
