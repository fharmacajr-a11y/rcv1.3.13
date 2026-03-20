# -*- coding: utf-8 -*-
"""
FASE 6: Script de validação de política de uso de ttk.

Regras:
1. ttkbootstrap PROIBIDO em todo src/
2. ttk.Treeview SOMENTE permitido em ctk_treeview_container.py
3. ttk.Scrollbar SOMENTE permitido em ctk_treeview_container.py
4. ttk.Style SOMENTE permitido em arquivos de tema (allowlist)

Uso:
    python scripts/validate_ttk_policy.py
    python scripts/validate_ttk_policy.py --ci  # modo CI (exit code 1 = falha)

Exit codes:
    0 = pass
    1 = violações encontradas
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import NamedTuple

# Arquivos permitidos para usar ttk.* específico
ALLOWLIST_TTK_TREEVIEW = {
    "src/ui/widgets/ctk_treeview_container.py",  # Container único para Treeview
}

ALLOWLIST_TTK_SCROLLBAR = {
    "src/ui/widgets/ctk_treeview_container.py",  # Scrollbar do container
}

ALLOWLIST_TTK_STYLE = {
    "src/ui/widgets/ctk_treeview_container.py",  # Estilo do container
    "src/ui/ttk_theme_manager.py",  # Manager de tema
    "src/ui/ttk_treeview_theme.py",  # Tema do Treeview
    "src/modules/clientes/ui/tree_theme.py",  # Wrapper legado de tema (deprecated)
}

# Fallback permitido (só para quando CTk não disponível)
# FASE 7: dashboard_center.py migrado para tk.LabelFrame nativo — sem ttk
ALLOWLIST_TTK_FALLBACK: set[str] = set()


class Violation(NamedTuple):
    """Representa uma violação de política."""

    file: str
    line: int
    message: str
    rule: str


def normalize_path(path: Path, root: Path) -> str:
    """Normaliza caminho para comparação."""
    try:
        rel = path.relative_to(root)
        return str(rel).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def check_ttkbootstrap(content: str, file_path: str) -> list[Violation]:
    """Verifica uso de ttkbootstrap (PROIBIDO).

    Nota: bootstyle como atributo de dataclass ou semantic tag é permitido.
    Apenas imports e widgets tb.* são proibidos.
    """
    violations = []

    # Padrões proibidos - apenas imports e widgets tb.*
    patterns = [
        (r"^\s*import\s+ttkbootstrap", "import ttkbootstrap"),
        (r"^\s*from\s+ttkbootstrap", "from ttkbootstrap"),
        (
            r"\btb\.(Frame|Button|Label|Entry|Combobox|Toplevel|Checkbutton|Text|Scrollbar)\s*\(",
            "tb.Widget( (ttkbootstrap)",
        ),
    ]

    for pattern, msg in patterns:
        for match in re.finditer(pattern, content, re.MULTILINE):
            line_num = content[: match.start()].count("\n") + 1
            violations.append(
                Violation(
                    file=file_path,
                    line=line_num,
                    message=msg,
                    rule="NO_TTKBOOTSTRAP",
                )
            )

    return violations


def check_ttk_treeview(content: str, file_path: str, allowlist: set[str]) -> list[Violation]:
    """Verifica uso de ttk.Treeview fora do allowlist."""
    violations = []

    if file_path in allowlist:
        return violations

    # ttk.Treeview( = instanciação direta (proibido)
    pattern = r"ttk\.Treeview\s*\("
    for match in re.finditer(pattern, content):
        line_num = content[: match.start()].count("\n") + 1
        violations.append(
            Violation(
                file=file_path,
                line=line_num,
                message="ttk.Treeview( - use CTkTreeviewContainer",
                rule="TTK_TREEVIEW_ONLY_IN_CONTAINER",
            )
        )

    return violations


def check_ttk_scrollbar(content: str, file_path: str, allowlist: set[str]) -> list[Violation]:
    """Verifica uso de ttk.Scrollbar fora do allowlist."""
    violations = []

    if file_path in allowlist:
        return violations

    pattern = r"ttk\.Scrollbar\s*\("
    for match in re.finditer(pattern, content):
        line_num = content[: match.start()].count("\n") + 1
        violations.append(
            Violation(
                file=file_path,
                line=line_num,
                message="ttk.Scrollbar( - use CTkTreeviewContainer",
                rule="TTK_SCROLLBAR_ONLY_IN_CONTAINER",
            )
        )

    return violations


def check_ttk_style(content: str, file_path: str, allowlist: set[str]) -> list[Violation]:
    """Verifica uso de ttk.Style fora do allowlist."""
    violations = []

    if file_path in allowlist:
        return violations

    pattern = r"ttk\.Style\s*\("
    for match in re.finditer(pattern, content):
        line_num = content[: match.start()].count("\n") + 1
        violations.append(
            Violation(
                file=file_path,
                line=line_num,
                message="ttk.Style( - usar via ttk_treeview_theme",
                rule="TTK_STYLE_ONLY_IN_THEME",
            )
        )

    return violations


def check_ttk_forbidden_widgets(content: str, file_path: str, fallback_allowlist: set[str]) -> list[Violation]:
    """Verifica uso de widgets ttk proibidos (Frame, Notebook, Combobox, etc)."""
    violations = []

    # Widgets ttk totalmente proibidos (usar CTk equivalentes)
    forbidden = [
        ("ttk.Frame", "CTkFrame"),
        ("ttk.Notebook", "CTkTabview"),
        ("ttk.Combobox", "CTkComboBox ou CTkOptionMenu"),
        ("ttk.Button", "CTkButton"),
        ("ttk.Label", "CTkLabel"),
        ("ttk.Entry", "CTkEntry"),
        ("ttk.Checkbutton", "CTkCheckBox"),
        ("ttk.Radiobutton", "CTkRadioButton"),
        ("ttk.Progressbar", "CTkProgressBar"),
        ("ttk.Scale", "CTkSlider"),
    ]

    # Labelframe é permitido em fallback_allowlist
    if file_path not in fallback_allowlist:
        forbidden.append(("ttk.Labelframe", "CTkFrame com título ou CTkSection"))

    for ttk_widget, ctk_alternative in forbidden:
        # Busca ttk.Widget( mas não ttk.Widget sem parêntese (pode ser type hint)
        pattern = rf"{re.escape(ttk_widget)}\s*\("
        for match in re.finditer(pattern, content):
            line_num = content[: match.start()].count("\n") + 1
            violations.append(
                Violation(
                    file=file_path,
                    line=line_num,
                    message=f"{ttk_widget}( - use {ctk_alternative}",
                    rule="TTK_FORBIDDEN_WIDGET",
                )
            )

    return violations


def validate_file(py_file: Path, root: Path) -> list[Violation]:
    """Valida um arquivo Python."""
    violations = []

    try:
        content = py_file.read_text(encoding="utf-8")
        file_path = normalize_path(py_file, root)

        # 1. ttkbootstrap proibido em todo lugar
        violations.extend(check_ttkbootstrap(content, file_path))

        # 2. ttk.Treeview só no container
        violations.extend(check_ttk_treeview(content, file_path, ALLOWLIST_TTK_TREEVIEW))

        # 3. ttk.Scrollbar só no container
        violations.extend(check_ttk_scrollbar(content, file_path, ALLOWLIST_TTK_SCROLLBAR))

        # 4. ttk.Style só em arquivos de tema
        violations.extend(check_ttk_style(content, file_path, ALLOWLIST_TTK_STYLE))

        # 5. Widgets ttk proibidos
        violations.extend(check_ttk_forbidden_widgets(content, file_path, ALLOWLIST_TTK_FALLBACK))

    except Exception as e:
        print(f"⚠️  Erro ao processar {py_file}: {e}", file=sys.stderr)

    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="FASE 6: Valida política de uso de ttk")
    parser.add_argument(
        "--path",
        type=str,
        default="src",
        help="Caminho para validar (padrão: src)",
    )
    parser.add_argument(
        "--ci",
        action="store_true",
        help="Modo CI: saída compacta, exit 1 se houver violações",
    )
    args = parser.parse_args()

    root = Path(args.path)
    if not root.exists():
        print(f"❌ Caminho não encontrado: {root}", file=sys.stderr)
        return 1

    # Encontrar root do projeto para normalizar caminhos
    project_root = root
    while project_root.parent != project_root:
        if (project_root / "pyproject.toml").exists():
            break
        project_root = project_root.parent

    if not args.ci:
        print("=" * 60)
        print("FASE 6: Validação de Política de TTK")
        print("=" * 60)
        print(f"📂 Validando: {root.absolute()}")
        print()
        print("📋 Regras:")
        print("  1. ttkbootstrap: PROIBIDO")
        print("  2. ttk.Treeview: SOMENTE em CTkTreeviewContainer")
        print("  3. ttk.Scrollbar: SOMENTE em CTkTreeviewContainer")
        print("  4. ttk.Style: SOMENTE em arquivos de tema")
        print("  5. ttk.*: Use widgets CTk equivalentes")
        print()

    all_violations: list[Violation] = []

    for py_file in root.rglob("*.py"):
        violations = validate_file(py_file, project_root)
        all_violations.extend(violations)

    if all_violations:
        if args.ci:
            for v in all_violations:
                print(f"ERROR:{v.file}:{v.line}:{v.rule}:{v.message}")
        else:
            # Agrupa por arquivo
            by_file: dict[str, list[Violation]] = {}
            for v in all_violations:
                by_file.setdefault(v.file, []).append(v)

            for file_path, violations in sorted(by_file.items()):
                print(f"❌ {file_path}:")
                for v in sorted(violations, key=lambda x: x.line):
                    print(f"   L{v.line}: [{v.rule}] {v.message}")
                print()

        print(f"❌ {len(all_violations)} violação(ões) encontrada(s)!")
        return 1
    else:
        if not args.ci:
            print("✅ Nenhuma violação encontrada!")
            print("✅ Política de TTK respeitada!")
            print()
            print("📊 Arquivos permitidos para ttk específico:")
            for f in sorted(ALLOWLIST_TTK_TREEVIEW | ALLOWLIST_TTK_STYLE | ALLOWLIST_TTK_FALLBACK):
                print(f"   - {f}")
        else:
            print("PASS: TTK policy validated")
        return 0


if __name__ == "__main__":
    sys.exit(main())
