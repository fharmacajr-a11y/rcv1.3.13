"""
Utilitários para seleção de arquivos no diálogo do Windows.

Fornece helpers padronizados para seleção de arquivos compactados (ZIP/RAR/7Z)
com logging adequado para debugging.
"""

from __future__ import annotations

import inspect
import logging
from tkinter import filedialog as fd
from typing import Optional

import tkinter as tk

# Importar constantes centralizadas
from infra.archive_utils import ARCHIVE_GLOBS, is_supported_archive

log = logging.getLogger("rc.ui.file_select")

# Filetypes padronizado para arquivos compactados
# Formato Tkinter: lista de tuplas (label, padrão)
# O padrão pode ser uma tupla com múltiplas extensões
ARCHIVE_FILETYPES = [
    ("Arquivos compactados", ARCHIVE_GLOBS),  # Usa constante centralizada
    ("ZIP", "*.zip"),
    ("RAR", "*.rar"),
    ("7-Zip", "*.7z"),
    ("7-Zip (volumes)", "*.7z.*"),
    ("Todos os arquivos", "*.*"),
]


def select_archive_file(title: str = "Selecione arquivo .ZIP, .RAR ou .7Z (volumes: selecione .7z.001)", parent: Optional[tk.Misc] = None) -> str:
    """
    Abre diálogo para seleção de arquivo ZIP, RAR ou 7Z (incluindo volumes .7z.001).

    Args:
        title: Título da janela de diálogo
        parent: Widget pai (opcional)

    Returns:
        Caminho do arquivo selecionado ou string vazia se cancelado
    """
    # Loga quem chamou e o filetypes usado
    caller = inspect.stack()[1]
    log.debug("Abrindo askopenfilename | caller=%s:%s | filetypes=%r", caller.filename, caller.lineno, ARCHIVE_FILETYPES)

    path = fd.askopenfilename(
        title=title,
        filetypes=ARCHIVE_FILETYPES,
        parent=parent,
    )

    log.debug("askopenfilename retornou: %r", path)
    return path or ""


def select_archive_files(title: str = "Selecione arquivo(s) .ZIP, .RAR ou .7Z", parent: Optional[tk.Misc] = None) -> tuple[str, ...]:
    """
    Abre diálogo para seleção de múltiplos arquivos ZIP, RAR ou 7Z.

    Args:
        title: Título da janela de diálogo
        parent: Widget pai (opcional)

    Returns:
        Tupla com caminhos dos arquivos selecionados (vazia se cancelado)
    """
    # Loga quem chamou e o filetypes usado
    caller = inspect.stack()[1]
    log.debug("Abrindo askopenfilenames | caller=%s:%s | filetypes=%r", caller.filename, caller.lineno, ARCHIVE_FILETYPES)

    paths = fd.askopenfilenames(
        title=title,
        filetypes=ARCHIVE_FILETYPES,
        parent=parent,
    )

    log.debug("askopenfilenames retornou: %r", paths)
    return paths or ()


def validate_archive_extension(path: str) -> bool:
    """
    Valida se o arquivo tem extensão .zip, .rar, .7z ou volume .7z.001.

    DEPRECADO: Use `is_supported_archive()` de `infra.archive_utils` diretamente.
    Esta função é mantida para compatibilidade com código existente.

    Args:
        path: Caminho do arquivo

    Returns:
        True se a extensão for válida, False caso contrário

    Exemplos:
        >>> validate_archive_extension("arquivo.zip")
        True
        >>> validate_archive_extension("arquivo.7z.001")
        True
        >>> validate_archive_extension("arquivo.tar")
        False
    """
    # Delega para a função centralizada
    return is_supported_archive(path)

    return False
