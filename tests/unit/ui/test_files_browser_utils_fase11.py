"""
Testes para src/ui/files_browser/utils.py (TEST-001 Fase 11).

Cobertura:
- sanitize_filename (sanitização de nomes de arquivo)
- format_file_size (formatação humana de tamanho)
- resolve_posix_path (resolução simples de caminhos POSIX)
- suggest_zip_filename (sugestão de nomes para ZIP)
"""

from __future__ import annotations

import pytest

from src.ui.files_browser.utils import (
    format_file_size,
    resolve_posix_path,
    sanitize_filename,
    suggest_zip_filename,
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("relatorio.pdf", "relatorio.pdf"),
        ("repor<t>:?.pdf", "repor_t___.pdf"),
        ("  relatório .pdf  ", "relatório .pdf"),
        ("ação çãõ.pdf", "ação çãõ.pdf"),
        ("relatorio.", "relatorio"),
        ("", ""),
    ],
)
def test_sanitize_filename_cases(raw: str, expected: str) -> None:
    assert sanitize_filename(raw) == expected


@pytest.mark.parametrize(
    "bytes_val,expected",
    [
        (None, "—"),
        (0, "0 B"),
        (1, "1 B"),
        (1536, "1.5 KB"),
        (1024**2, "1.0 MB"),
        (1024**3, "1.0 GB"),
        (1024**4, "1.0 TB"),
        (-5, "-5 B"),
    ],
)
def test_format_file_size_values(bytes_val: int | None, expected: str) -> None:
    assert format_file_size(bytes_val) == expected


@pytest.mark.parametrize(
    "base,relative,expected",
    [
        ("org/client/docs", "../data", "org/client/docs/../data"),
        ("org/client", "", "org/client"),
        ("org/client", ".", "org/client"),
        ("org/client/docs", "../data/report.pdf", "org/client/docs/../data/report.pdf"),
        ("org/client", "/absolute/path", "absolute/path"),
        ("org/client/docs", "./sub/../file.txt", "org/client/docs/sub/../file.txt"),
    ],
)
def test_resolve_posix_path_cases(base: str, relative: str, expected: str) -> None:
    assert resolve_posix_path(base, relative) == expected


@pytest.mark.parametrize(
    "prefix_path,expected",
    [
        ("org/client/GERAL/Auditoria", "Auditoria"),
        ("org/client/", "client"),
        ("////", "arquivos"),
        ("org/client/Relatórios 2025?:", "Relatórios 2025__"),
        ("org/client/...", "arquivos"),
        ("", "arquivos"),
    ],
)
def test_suggest_zip_filename(prefix_path: str, expected: str) -> None:
    assert suggest_zip_filename(prefix_path) == expected
