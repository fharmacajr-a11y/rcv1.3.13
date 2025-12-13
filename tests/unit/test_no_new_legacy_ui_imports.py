"""
Teste de guarda: impede novos imports de src.ui.* (fora da allowlist).

Este teste falha se encontrar imports de src.ui em arquivos de produção
que não estão na allowlist de módulos de compatibilidade permitidos.
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

import pytest


# Allowlist de módulos que ainda podem importar src.ui.*
ALLOWED_LEGACY_UI_IMPORTERS = {
    "src/ui/placeholders.py",
    "src/ui/login_dialog.py",
    "src/ui/window_utils.py",
    "src/ui/components/progress_dialog.py",
    "src/utils/resource_path.py",
    # Adicione mais conforme necessário durante migração
}

IGNORE_DIRS = {
    "__pycache__",
    ".venv",
    "venv",
    ".git",
    ".pytest_cache",
    "build",
    "dist",
    "htmlcov",
    ".eggs",
    "node_modules",
}


def discover_src_files(root_path: Path) -> List[str]:
    """Enumera todos os arquivos .py em src/."""
    src_files = []

    for dirpath, dirnames, filenames in os.walk(root_path / "src"):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        rel_dir = Path(dirpath).relative_to(root_path)

        for filename in filenames:
            if filename.endswith(".py") and not filename.endswith(".pyc"):
                rel_path = str(rel_dir / filename).replace("\\", "/")
                src_files.append(rel_path)

    return sorted(src_files)


def find_legacy_ui_imports(file_path: Path) -> List[Tuple[int, str]]:
    """Encontra imports de src.ui.* no arquivo."""
    results = []

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception:
        return results

    for i, line in enumerate(lines, start=1):
        # Busca por: import src.ui ou from src.ui
        if re.search(r"\b(import|from)\s+src\.ui\b", line):
            results.append((i, line.strip()))

    return results


def test_no_new_legacy_ui_imports():
    """
    Teste de guarda: nenhum novo arquivo em src/ deve importar src.ui.*
    (exceto os da allowlist).
    """
    root_path = Path.cwd()
    violations = []

    # Descobre todos os arquivos em src/
    src_files = discover_src_files(root_path)

    for src_file in src_files:
        # Pula arquivos na allowlist
        if src_file in ALLOWED_LEGACY_UI_IMPORTERS:
            continue

        file_path = root_path / src_file
        imports = find_legacy_ui_imports(file_path)

        if imports:
            violations.append((src_file, imports))

    # Se houver violações, falha o teste com mensagem detalhada
    if violations:
        msg = ["\n❌ Encontrados imports de src.ui.* em arquivos não permitidos:\n"]
        for file_path, imports in violations:
            msg.append(f"\n  {file_path}:")
            for line_num, line_content in imports:
                msg.append(f"    Linha {line_num}: {line_content}")

        msg.append(
            "\n\n💡 Para corrigir:"
            "\n  1. Remova o import de src.ui.* deste arquivo"
            "\n  2. Use módulos migrados (src.modules.*)"
            "\n  3. Ou adicione o arquivo à ALLOWED_LEGACY_UI_IMPORTERS se for compat necessária"
        )

        pytest.fail("".join(msg))


def test_allowlist_files_exist():
    """Verifica que todos os arquivos na allowlist existem."""
    root_path = Path.cwd()
    missing = []

    for allowed_file in ALLOWED_LEGACY_UI_IMPORTERS:
        if not (root_path / allowed_file).exists():
            missing.append(allowed_file)

    if missing:
        msg = ["\n⚠️  Arquivos na allowlist não encontrados:\n"]
        for file_path in missing:
            msg.append(f"  - {file_path}\n")
        msg.append("\n💡 Remova-os de ALLOWED_LEGACY_UI_IMPORTERS se foram deletados.")
        pytest.fail("".join(msg))
