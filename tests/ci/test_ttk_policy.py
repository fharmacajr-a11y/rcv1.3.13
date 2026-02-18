# -*- coding: utf-8 -*-
"""FASE 6: Testes de CI para política de uso de ttk.

Estes testes garantem que:
1. Não há imports de ttkbootstrap em src/
2. ttk.Treeview( só existe em CTkTreeviewContainer
3. ttk.Style( só existe em arquivos de tema permitidos
4. Widgets ttk proibidos não são usados

Execute: pytest tests/ci/test_ttk_policy.py -v
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Generator

import pytest

# Diretório raiz do projeto
PROJECT_ROOT = Path(__file__).parents[2]
SRC_DIR = PROJECT_ROOT / "src"

# Allowlists para arquivos que podem usar ttk específico
ALLOWLIST_TTK_TREEVIEW = {
    "src/ui/widgets/ctk_treeview_container.py",
}

ALLOWLIST_TTK_SCROLLBAR = {
    "src/ui/widgets/ctk_treeview_container.py",
}

ALLOWLIST_TTK_STYLE = {
    "src/ui/widgets/ctk_treeview_container.py",
    "src/ui/ttk_theme_manager.py",
    "src/ui/ttk_treeview_theme.py",
    "src/modules/clientes/ui/tree_theme.py",  # wrapper legado
}

# FASE 7: dashboard_center.py migrado — sem ttk fallback
ALLOWLIST_TTK_FALLBACK: set[str] = set()


def iter_python_files() -> Generator[Path, None, None]:
    """Itera sobre todos os arquivos .py em src/."""
    yield from SRC_DIR.rglob("*.py")


def normalize_path(path: Path) -> str:
    """Normaliza caminho relativo ao projeto."""
    try:
        rel = path.relative_to(PROJECT_ROOT)
        return str(rel).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


class TestNoTtkbootstrap:
    """Testes para garantir ausência de ttkbootstrap."""

    def test_no_import_ttkbootstrap(self) -> None:
        """Verifica que não há 'import ttkbootstrap' em src/."""
        violations = []
        pattern = re.compile(r"^\s*import\s+ttkbootstrap", re.MULTILINE)

        for py_file in iter_python_files():
            content = py_file.read_text(encoding="utf-8")
            for match in pattern.finditer(content):
                line_num = content[: match.start()].count("\n") + 1
                violations.append(f"{normalize_path(py_file)}:{line_num}")

        assert not violations, f"Imports de ttkbootstrap encontrados: {violations}"

    def test_no_from_ttkbootstrap(self) -> None:
        """Verifica que não há 'from ttkbootstrap' em src/."""
        violations = []
        pattern = re.compile(r"^\s*from\s+ttkbootstrap", re.MULTILINE)

        for py_file in iter_python_files():
            content = py_file.read_text(encoding="utf-8")
            for match in pattern.finditer(content):
                line_num = content[: match.start()].count("\n") + 1
                violations.append(f"{normalize_path(py_file)}:{line_num}")

        assert not violations, f"Imports from ttkbootstrap encontrados: {violations}"


class TestTtkTreeviewPolicy:
    """Testes para garantir que ttk.Treeview só é usado no container."""

    def test_treeview_only_in_container(self) -> None:
        """Verifica que ttk.Treeview( só existe em CTkTreeviewContainer."""
        violations = []
        pattern = re.compile(r"ttk\.Treeview\s*\(")

        for py_file in iter_python_files():
            rel_path = normalize_path(py_file)
            if rel_path in ALLOWLIST_TTK_TREEVIEW:
                continue

            content = py_file.read_text(encoding="utf-8")
            for match in pattern.finditer(content):
                line_num = content[: match.start()].count("\n") + 1
                violations.append(f"{rel_path}:{line_num} - use CTkTreeviewContainer")

        assert not violations, f"ttk.Treeview( fora do container: {violations}"


class TestTtkStylePolicy:
    """Testes para garantir que ttk.Style só é usado em arquivos de tema."""

    def test_style_only_in_theme_files(self) -> None:
        """Verifica que ttk.Style( só existe em arquivos de tema permitidos."""
        violations = []
        pattern = re.compile(r"ttk\.Style\s*\(")

        for py_file in iter_python_files():
            rel_path = normalize_path(py_file)
            if rel_path in ALLOWLIST_TTK_STYLE:
                continue

            content = py_file.read_text(encoding="utf-8")
            for match in pattern.finditer(content):
                line_num = content[: match.start()].count("\n") + 1
                violations.append(f"{rel_path}:{line_num} - usar via ttk_treeview_theme")

        assert not violations, f"ttk.Style( fora de arquivos permitidos: {violations}"


class TestTtkScrollbarPolicy:
    """Testes para garantir que ttk.Scrollbar só é usado no container."""

    def test_scrollbar_only_in_container(self) -> None:
        """Verifica que ttk.Scrollbar( só existe em CTkTreeviewContainer."""
        violations = []
        pattern = re.compile(r"ttk\.Scrollbar\s*\(")

        for py_file in iter_python_files():
            rel_path = normalize_path(py_file)
            if rel_path in ALLOWLIST_TTK_SCROLLBAR:
                continue

            content = py_file.read_text(encoding="utf-8")
            for match in pattern.finditer(content):
                line_num = content[: match.start()].count("\n") + 1
                violations.append(f"{rel_path}:{line_num} - use CTkTreeviewContainer")

        assert not violations, f"ttk.Scrollbar( fora do container: {violations}"


class TestTtkForbiddenWidgets:
    """Testes para garantir que widgets ttk proibidos não são usados."""

    FORBIDDEN_WIDGETS = [
        ("ttk.Frame", "CTkFrame"),
        ("ttk.Notebook", "CTkTabview"),
        ("ttk.Combobox", "CTkComboBox/CTkOptionMenu"),
        ("ttk.Button", "CTkButton"),
        ("ttk.Label", "CTkLabel"),
        ("ttk.Entry", "CTkEntry"),
        ("ttk.Checkbutton", "CTkCheckBox"),
        ("ttk.Radiobutton", "CTkRadioButton"),
        ("ttk.Progressbar", "CTkProgressBar"),
        ("ttk.Scale", "CTkSlider"),
    ]

    @pytest.mark.parametrize("ttk_widget,ctk_alternative", FORBIDDEN_WIDGETS)
    def test_no_forbidden_widget(self, ttk_widget: str, ctk_alternative: str) -> None:
        """Verifica que widgets ttk proibidos não são usados."""
        violations = []
        pattern = re.compile(rf"{re.escape(ttk_widget)}\s*\(")

        for py_file in iter_python_files():
            rel_path = normalize_path(py_file)

            content = py_file.read_text(encoding="utf-8")
            for match in pattern.finditer(content):
                line_num = content[: match.start()].count("\n") + 1
                violations.append(f"{rel_path}:{line_num}")

        assert not violations, f"{ttk_widget}( encontrado (use {ctk_alternative}): {violations}"

    def test_labelframe_only_in_fallback(self) -> None:
        """Verifica que ttk.Labelframe só é usado em fallbacks permitidos."""
        violations = []
        pattern = re.compile(r"ttk\.Labelframe\s*\(", re.IGNORECASE)

        for py_file in iter_python_files():
            rel_path = normalize_path(py_file)
            if rel_path in ALLOWLIST_TTK_FALLBACK:
                continue

            content = py_file.read_text(encoding="utf-8")
            for match in pattern.finditer(content):
                line_num = content[: match.start()].count("\n") + 1
                violations.append(f"{rel_path}:{line_num} - use CTkFrame/CTkSection")

        assert not violations, f"ttk.Labelframe( fora de fallbacks permitidos: {violations}"
