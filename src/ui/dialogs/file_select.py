"""
Utilitários para seleção de arquivos no diálogo do Windows.

Fornece helpers padronizados para seleção de arquivos compactados (ZIP/RAR)
com logging adequado para debugging.
"""
from __future__ import annotations

import inspect
import logging
from tkinter import filedialog as fd
from typing import Optional

import tkinter as tk

log = logging.getLogger("rc.ui.file_select")

# Filetypes padronizado para arquivos compactados
# Formato Tkinter: lista de tuplas (label, padrão)
# O padrão pode ser uma tupla com múltiplas extensões
ARCHIVE_FILETYPES = [
    ("Arquivos compactados", ("*.zip", "*.rar")),  # Tupla de padrões
    ("ZIP", "*.zip"),
    ("RAR", "*.rar"),
    ("Todos os arquivos", "*.*"),
]


def select_archive_file(
    title: str = "Selecione um arquivo .ZIP ou .RAR",
    parent: Optional[tk.Misc] = None
) -> str:
    """
    Abre diálogo para seleção de arquivo ZIP ou RAR.
    
    Args:
        title: Título da janela de diálogo
        parent: Widget pai (opcional)
        
    Returns:
        Caminho do arquivo selecionado ou string vazia se cancelado
    """
    # Loga quem chamou e o filetypes usado
    caller = inspect.stack()[1]
    log.debug(
        "Abrindo askopenfilename | caller=%s:%s | filetypes=%r",
        caller.filename, caller.lineno, ARCHIVE_FILETYPES
    )

    path = fd.askopenfilename(
        title=title,
        filetypes=ARCHIVE_FILETYPES,
        parent=parent,
    )
    
    log.debug("askopenfilename retornou: %r", path)
    return path or ""


def select_archive_files(
    title: str = "Selecione arquivo(s) .ZIP ou .RAR",
    parent: Optional[tk.Misc] = None
) -> tuple[str, ...]:
    """
    Abre diálogo para seleção de múltiplos arquivos ZIP ou RAR.
    
    Args:
        title: Título da janela de diálogo
        parent: Widget pai (opcional)
        
    Returns:
        Tupla com caminhos dos arquivos selecionados (vazia se cancelado)
    """
    # Loga quem chamou e o filetypes usado
    caller = inspect.stack()[1]
    log.debug(
        "Abrindo askopenfilenames | caller=%s:%s | filetypes=%r",
        caller.filename, caller.lineno, ARCHIVE_FILETYPES
    )

    paths = fd.askopenfilenames(
        title=title,
        filetypes=ARCHIVE_FILETYPES,
        parent=parent,
    )
    
    log.debug("askopenfilenames retornou: %r", paths)
    return paths or ()


def validate_archive_extension(path: str) -> bool:
    """
    Valida se o arquivo tem extensão .zip ou .rar.
    
    Args:
        path: Caminho do arquivo
        
    Returns:
        True se a extensão for válida, False caso contrário
    """
    return path.lower().endswith((".zip", ".rar"))
