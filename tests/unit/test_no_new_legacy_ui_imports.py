"""
Teste de guarda: policy de imports de src.ui.*.

Regras:
1. Toolkit ativo (window_utils, components, dialogs, widgets) → PERMITIDO
2. Wrappers deprecated (hub, lixeira, main_window, etc) → PROIBIDO

Nota: src.ui.forms foi removido em T09.1 - use src.modules.forms.
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

import pytest


# Prefixos de toolkit ativo (permitidos)
ALLOWED_PREFIXES = [
    "src.ui.window_utils",
    "src.ui.components",
    "src.ui.dialogs",
    "src.ui.widgets",
    "src.ui.files_browser",
    "src.ui.login_dialog",
    "src.ui.splash",
    "src.ui.menu_bar",
    "src.ui.topbar",
    "src.ui.status_footer",
    "src.ui.window_policy",
    "src.ui.search_nav",
    "src.ui.pdf_preview_native",
    "src.ui.wheel_windows",
    "src.ui.placeholders",
    "src.ui.custom_dialogs",
    "src.ui.utils",  # OkCancelMixin, center_on_parent
    "src.ui.progress.pdf_batch_progress",  # PDF batch progress específico
    "src.ui.theme_manager",  # Gerenciador de temas
    "src.ui.themes",  # Definições de temas
    "src.ui.controllers",  # Controllers de UI (NotificationVM, TopbarNotificationsController)
    "src.ui.theme_toggle",  # Toggle de tema dark/light
    "src.ui.win_titlebar",  # Dark mode para titlebar Windows
    "src.ui.feedback",  # UIFeedback protocol (T08)
]

# Prefixos de wrappers deprecated (proibidos)
BANNED_PREFIXES = [
    "src.ui.hub",
    "src.ui.hub_screen",
    "src.ui.lixeira",
    "src.ui.main_window",
    "src.ui.main_screen",
    "src.ui.login.login",
    # src.ui.forms removido em T09.1 - migrado para src.modules.forms
]

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


def find_legacy_ui_imports(file_path: Path) -> List[Tuple[int, str, str]]:
    """Encontra imports de src.ui.* no arquivo.

    Retorna: List[(line_num, line_content, imported_module)]
    """
    results = []

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception:
        return results

    for i, line in enumerate(lines, start=1):
        # Busca por: from src.ui import X ou from src.ui.Y import Z
        from_match = re.search(r"\bfrom\s+(src\.ui(?:\.\w+)*)\s+import\s+(\w+)", line)
        if from_match:
            base_module = from_match.group(1)
            imported_name = from_match.group(2)
            # Constrói o módulo completo: src.ui.custom_dialogs
            imported_module = f"{base_module}.{imported_name}"
            results.append((i, line.strip(), imported_module))
            continue

        # Busca por: import src.ui.X
        import_match = re.search(r"\bimport\s+(src\.ui(?:\.\w+)*)", line)
        if import_match:
            imported_module = import_match.group(1)
            results.append((i, line.strip(), imported_module))

    return results


def is_import_allowed(imported_module: str, source_file: str) -> Tuple[bool, str]:
    """Verifica se o import é permitido.

    Retorna: (is_allowed, reason)
    """
    # 1. Verifica se é wrapper banned
    for banned_prefix in BANNED_PREFIXES:
        if imported_module.startswith(banned_prefix):
            return False, f"❌ BANNED: {banned_prefix} (deprecated/migrado)"

    # 2. Verifica se é toolkit ativo permitido
    for allowed_prefix in ALLOWED_PREFIXES:
        if imported_module.startswith(allowed_prefix):
            return True, f"✓ ALLOWED: {allowed_prefix}"

    # 3. Se não é nenhum dos acima, proibido
    return False, f"❌ UNKNOWN: {imported_module} não está em ALLOWED_PREFIXES nem BANNED_PREFIXES"


def test_no_new_legacy_ui_imports():
    """
    Teste de guarda: policy de imports de src.ui.*.

    Regras:
    1. Toolkit ativo → PERMITIDO
    2. Wrappers deprecated → PROIBIDO
    """
    root_path = Path.cwd()
    violations = []

    # Descobre todos os arquivos em src/
    src_files = discover_src_files(root_path)

    for src_file in src_files:
        file_path = root_path / src_file
        imports = find_legacy_ui_imports(file_path)

        for line_num, line_content, imported_module in imports:
            allowed, reason = is_import_allowed(imported_module, src_file)

            if not allowed:
                violations.append((src_file, line_num, line_content, reason))

    # Se houver violações, falha o teste com mensagem detalhada
    if violations:
        msg = ["\n" + "=" * 70]
        msg.append("\n❌ POLICY VIOLATION: Imports proibidos de src.ui.*")
        msg.append("\n" + "=" * 70 + "\n")

        # Agrupa por arquivo
        by_file = {}
        for file_path, line_num, line_content, reason in violations:
            if file_path not in by_file:
                by_file[file_path] = []
            by_file[file_path].append((line_num, line_content, reason))

        for file_path, file_violations in sorted(by_file.items()):
            msg.append(f"\n📁 {file_path}")
            for line_num, line_content, reason in file_violations:
                msg.append(f"\n   Linha {line_num}: {line_content}")
                msg.append(f"\n   {reason}")
            msg.append("\n")

        msg.append("\n" + "=" * 70)
        msg.append("\n💡 PARA CORRIGIR:")
        msg.append("\n" + "=" * 70)
        msg.append("\n1. TOOLKIT ATIVO → Use prefixos em ALLOWED_PREFIXES")
        msg.append("\n2. WRAPPERS BANNED → Migre para src.modules.*")
        msg.append("\n")

        pytest.fail("".join(msg))
