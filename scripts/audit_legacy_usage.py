#!/usr/bin/env python
"""
Auditoria de uso de módulos legados (src.ui.*).
Reporta imports explícitos, dinâmicos e ocorrências textuais.
"""

import os
import re
import ast
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Tuple


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


def discover_python_files(root_path: Path) -> Tuple[List[str], List[str]]:
    """Enumera arquivos .py em src/ e tests/."""
    src_files = []
    test_files = []

    for dirpath, dirnames, filenames in os.walk(root_path):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        rel_dir = Path(dirpath).relative_to(root_path)

        for filename in filenames:
            if filename.endswith(".py") and not filename.endswith(".pyc"):
                rel_path = str(rel_dir / filename).replace("\\", "/")

                if rel_path.startswith("src/"):
                    src_files.append(rel_path)
                elif rel_path.startswith("tests/"):
                    test_files.append(rel_path)

    return sorted(src_files), sorted(test_files)


def find_explicit_imports(file_path: Path) -> List[Dict]:
    """Encontra imports explícitos de src.ui.*"""
    results = []

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception:
        return results

    for i, line in enumerate(lines, start=1):
        # Busca por: import src.ui ou from src.ui
        if re.search(r"\b(import|from)\s+src\.ui\b", line):
            results.append({"line": i, "code": line.strip()[:100]})

    return results


def find_dynamic_imports(file_path: Path) -> List[Dict]:
    """Encontra chamadas importlib.import_module com string literal contendo src.ui."""
    results = []

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        tree = ast.parse(content, filename=str(file_path))
    except Exception:
        return results

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # Verifica se é import_module
            func_name = None
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr

            if func_name == "import_module" and node.args:
                # Verifica se primeiro argumento é string literal
                first_arg = node.args[0]
                if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                    if "src.ui." in first_arg.value or first_arg.value == "src.ui":
                        results.append(
                            {
                                "line": getattr(node, "lineno", "?"),
                                "module": first_arg.value,
                            }
                        )

    return results


def find_textual_occurrences(file_path: Path) -> List[Dict]:
    """Encontra ocorrências textuais de 'src.ui.' em strings/docstrings."""
    results = []

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception:
        return results

    for i, line in enumerate(lines, start=1):
        # Busca literal "src.ui." mas exclui linhas que parecem imports
        if "src.ui." in line and not re.search(r"^\s*(import|from)\s+", line) and not line.strip().startswith("#"):
            results.append({"line": i, "snippet": line.strip()[:80]})

    return results


def generate_report(root_path: Path, src_files: List[str], test_files: List[str]) -> Dict:
    """Gera relatório de uso de src.ui.*"""
    report = {
        "src_explicit": defaultdict(list),
        "tests_explicit": defaultdict(list),
        "dynamic_imports": defaultdict(list),
        "textual_occurrences": defaultdict(list),
    }

    # Processa src/
    for src_file in src_files:
        file_path = root_path / src_file

        explicit = find_explicit_imports(file_path)
        if explicit:
            report["src_explicit"][src_file] = explicit

        dynamic = find_dynamic_imports(file_path)
        if dynamic:
            report["dynamic_imports"][src_file] = dynamic

        textual = find_textual_occurrences(file_path)
        if textual:
            report["textual_occurrences"][src_file] = textual

    # Processa tests/
    for test_file in test_files:
        file_path = root_path / test_file

        explicit = find_explicit_imports(file_path)
        if explicit:
            report["tests_explicit"][test_file] = explicit

        dynamic = find_dynamic_imports(file_path)
        if dynamic:
            report["dynamic_imports"][test_file] = dynamic

        textual = find_textual_occurrences(file_path)
        if textual:
            report["textual_occurrences"][test_file] = textual

    return report


def write_markdown_report(output_path: Path, report: Dict):
    """Escreve relatório em Markdown."""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# Relatório de Uso de Módulos Legados (src.ui.*)\n\n")
        f.write(f"**Gerado em:** {Path.cwd()}\n\n")
        f.write("---\n\n")

        # Imports diretos em src/
        f.write(f"## Imports diretos em src/ ({len(report['src_explicit'])} arquivos)\n\n")
        if report["src_explicit"]:
            for file_path, imports in sorted(report["src_explicit"].items()):
                f.write(f"### {file_path}\n\n")
                for imp in imports:
                    f.write(f"- Linha {imp['line']}: `{imp['code']}`\n")
                f.write("\n")
        else:
            f.write("_Nenhum import direto encontrado._\n\n")

        # Imports diretos em tests/
        f.write(f"## Imports diretos em tests/ ({len(report['tests_explicit'])} arquivos)\n\n")
        if report["tests_explicit"]:
            for file_path, imports in sorted(report["tests_explicit"].items()):
                f.write(f"### {file_path}\n\n")
                for imp in imports:
                    f.write(f"- Linha {imp['line']}: `{imp['code']}`\n")
                f.write("\n")
        else:
            f.write("_Nenhum import direto encontrado._\n\n")

        # Imports dinâmicos
        f.write(f"## Imports dinâmicos (literal) ({len(report['dynamic_imports'])} arquivos)\n\n")
        if report["dynamic_imports"]:
            for file_path, imports in sorted(report["dynamic_imports"].items()):
                f.write(f"### {file_path}\n\n")
                for imp in imports:
                    f.write(f"- Linha {imp['line']}: `import_module('{imp['module']}')`\n")
                f.write("\n")
        else:
            f.write("_Nenhum import dinâmico encontrado._\n\n")

        # Ocorrências textuais
        f.write(f"## Ocorrências textuais ({len(report['textual_occurrences'])} arquivos)\n\n")
        if report["textual_occurrences"]:
            for file_path, occurrences in sorted(report["textual_occurrences"].items()):
                f.write(f"### {file_path}\n\n")
                for occ in occurrences[:10]:  # Limita a 10 por arquivo
                    f.write(f"- Linha {occ['line']}: `{occ['snippet']}`\n")
                if len(occurrences) > 10:
                    f.write(f"- _... e mais {len(occurrences) - 10} ocorrências_\n")
                f.write("\n")
        else:
            f.write("_Nenhuma ocorrência textual encontrada._\n\n")

        # Resumo
        f.write("---\n\n")
        f.write("## Resumo\n\n")
        f.write(f"- **Imports diretos em src/:** {len(report['src_explicit'])}\n")
        f.write(f"- **Imports diretos em tests/:** {len(report['tests_explicit'])}\n")
        f.write(f"- **Imports dinâmicos:** {len(report['dynamic_imports'])}\n")
        f.write(f"- **Ocorrências textuais:** {len(report['textual_occurrences'])}\n")

        total_files = (
            len(report["src_explicit"])
            + len(report["tests_explicit"])
            + len(report["dynamic_imports"])
            + len(report["textual_occurrences"])
        )
        f.write(f"\n**Total de arquivos com referências a src.ui.*:** {total_files}\n")


def main():
    """Executa auditoria de uso de src.ui.*"""
    root_path = Path.cwd()
    print(f"🔍 Auditando uso de src.ui.* em: {root_path}\n")

    # Descoberta
    print("📂 Descobrindo arquivos Python...")
    src_files, test_files = discover_python_files(root_path)
    print(f"   ✓ {len(src_files)} arquivos em src/")
    print(f"   ✓ {len(test_files)} arquivos em tests/\n")

    # Análise
    print("🔎 Analisando uso de src.ui.*...")
    report = generate_report(root_path, src_files, test_files)
    print(f"   ✓ {len(report['src_explicit'])} imports diretos em src/")
    print(f"   ✓ {len(report['tests_explicit'])} imports diretos em tests/")
    print(f"   ✓ {len(report['dynamic_imports'])} imports dinâmicos")
    print(f"   ✓ {len(report['textual_occurrences'])} ocorrências textuais\n")

    # Gerar relatório
    print("📝 Gerando relatório...")
    docs_path = root_path / "docs"
    docs_path.mkdir(exist_ok=True)
    output_path = docs_path / "legacy_usage_report.md"
    write_markdown_report(output_path, report)
    print(f"   ✓ {output_path}\n")

    # Resumo
    print("=" * 60)
    print("📊 RESUMO DO USO DE src.ui.*")
    print("=" * 60)
    print(f"Imports diretos em src/:      {len(report['src_explicit']):4d}")
    print(f"Imports diretos em tests/:    {len(report['tests_explicit']):4d}")
    print(f"Imports dinâmicos:            {len(report['dynamic_imports']):4d}")
    print(f"Ocorrências textuais:         {len(report['textual_occurrences']):4d}")
    print("=" * 60)
    print("\n✅ Auditoria de uso concluída!")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        import traceback

        traceback.print_exc()
