#!/usr/bin/env python
"""
Auditoria de código legado/compat sem modificar nada.
Gera relatórios em docs/ classificando arquivos Python em 4 categorias.
"""

import os
import re
import ast
import json
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Optional


# ============================================================================
# 1. DESCOBERTA DE ARQUIVOS
# ============================================================================

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
ENTRYPOINTS = {"src/app_gui.py", "src/__main__.py", "main.py", "src/cli.py"}


def discover_python_files(root_path: Path) -> Tuple[List[str], List[str]]:
    """Enumera arquivos .py em src/ e tests/, retorna (src_files, test_files)."""
    src_files = []
    test_files = []

    for dirpath, dirnames, filenames in os.walk(root_path):
        # Remove ignored dirs in-place
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


# ============================================================================
# 2. SINAIS DE LEGADO (scan de texto)
# ============================================================================

LEGACY_PATTERNS = re.compile(r"\b(deprecated|legacy|wrapper|compat)\b", re.IGNORECASE)


def scan_legacy_markers(file_path: Path) -> Optional[Dict]:
    """Procura por termos deprecated/legacy/wrapper/compat."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception:
        return None

    matches = LEGACY_PATTERNS.findall(content)
    if not matches:
        return None

    # Deduplica e normaliza
    unique_matches = sorted(set(m.lower() for m in matches))

    # Contexto (opcional): pegar 1-3 linhas onde aparece
    lines = content.split("\n")
    contexts = []
    for i, line in enumerate(lines[:100]):  # limita a primeiras 100 linhas
        if LEGACY_PATTERNS.search(line):
            contexts.append(f"L{i+1}: {line.strip()[:80]}")
            if len(contexts) >= 3:
                break

    return {"file": str(file_path).replace("\\", "/"), "matches": unique_matches, "contexts": contexts[:3]}


# ============================================================================
# 3. DETECTAR SHIMS/WRAPPERS (heurística)
# ============================================================================


def count_relevant_lines(content: str) -> int:
    """Conta linhas não vazias e que não começam com #."""
    lines = content.split("\n")
    return sum(1 for line in lines if line.strip() and not line.strip().startswith("#"))


def detect_shim(file_path: Path) -> Optional[Dict]:
    """Detecta se arquivo parece um shim/wrapper."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception:
        return None

    relevant_lines = count_relevant_lines(content)
    if relevant_lines > 30:
        return None

    try:
        tree = ast.parse(content, filename=str(file_path))
    except SyntaxError:
        return None

    if not hasattr(tree, "body"):
        return None

    total_nodes = len(tree.body)
    if total_nodes == 0:
        return None

    # Conta imports/assigns/docstrings
    simple_count = 0
    has_complexity = False

    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.Assign)):
            simple_count += 1
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            # Docstring
            simple_count += 1
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if len(node.body) > 1:
                has_complexity = True
        elif isinstance(node, (ast.For, ast.While, ast.Try, ast.With, ast.If)):
            has_complexity = True

    if has_complexity:
        return None

    ratio = simple_count / total_nodes if total_nodes > 0 else 0

    if ratio >= 0.8:
        return {
            "file": str(file_path).replace("\\", "/"),
            "reason": f"{relevant_lines} linhas relevantes; {int(ratio*100)}% imports/reexports; sem lógica",
            "lines_relevant": relevant_lines,
            "import_ratio": round(ratio, 2),
        }

    return None


# ============================================================================
# 4. CONSTRUIR MAPA DE MÓDULOS E INBOUND REFS
# ============================================================================


def build_module_index(src_files: List[str]) -> Dict[str, str]:
    """Constrói mapa module_name -> file_path para arquivos em src/."""
    index = {}
    for file_path in src_files:
        # src/foo/bar.py -> src.foo.bar
        # src/foo/__init__.py -> src.foo
        module_path = file_path.replace("/", ".").replace("\\", ".")
        if module_path.endswith(".py"):
            module_path = module_path[:-3]

        # Remove __init__
        if module_path.endswith(".__init__"):
            module_path = module_path[:-9]

        index[module_path] = file_path

    return index


def extract_imports_from_file(file_path: Path, module_index: Dict[str, str]) -> Tuple[List[str], List[Dict]]:
    """
    Extrai imports de um arquivo.
    Retorna (resolved_imports, unresolved_imports).
    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        tree = ast.parse(content, filename=str(file_path))
    except Exception as e:
        return [], [{"import": str(file_path), "error": str(e)}]

    # Determina o módulo atual
    rel_path = str(file_path).replace("\\", "/")
    current_module = rel_path.replace("/", ".").replace("\\", ".")
    if current_module.endswith(".py"):
        current_module = current_module[:-3]
    if current_module.endswith(".__init__"):
        current_module = current_module[:-9]

    resolved = []
    unresolved = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_name = alias.name
                if module_name in module_index:
                    resolved.append(module_index[module_name])
                else:
                    unresolved.append(
                        {"file": rel_path, "import": module_name, "kind": "Import", "note": "not in module_index"}
                    )

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            level = node.level

            # Resolve relativo
            if level > 0:
                parts = current_module.split(".")
                if level >= len(parts):
                    base_module = ""
                else:
                    base_module = ".".join(parts[:-level])

                if module:
                    full_module = f"{base_module}.{module}" if base_module else module
                else:
                    full_module = base_module
            else:
                full_module = module

            # Tenta resolver o módulo base
            if full_module in module_index:
                resolved.append(module_index[full_module])

            # Tenta também submódulos (from pkg import submod)
            for alias in node.names:
                candidate = f"{full_module}.{alias.name}" if full_module else alias.name
                if candidate in module_index:
                    resolved.append(module_index[candidate])
                elif full_module not in module_index:
                    # Só registra como unresolved se nem o base nem o submódulo foram resolvidos
                    unresolved.append(
                        {"file": rel_path, "import": candidate, "kind": "ImportFrom", "note": "not in module_index"}
                    )

    return list(set(resolved)), unresolved


def build_inbound_refs(
    root_path: Path, src_files: List[str], test_files: List[str], module_index: Dict[str, str]
) -> Tuple[Dict, Dict, List]:
    """
    Constrói inbound_src e inbound_tests.
    Retorna (inbound_src, inbound_tests, all_unresolved).
    """
    inbound_src = defaultdict(set)
    inbound_tests = defaultdict(set)
    all_unresolved = []

    # Processa src/
    for src_file in src_files:
        resolved, unresolved = extract_imports_from_file(root_path / src_file, module_index)
        all_unresolved.extend(unresolved)
        for imported_file in resolved:
            inbound_src[imported_file].add(src_file)

    # Processa tests/
    for test_file in test_files:
        resolved, unresolved = extract_imports_from_file(root_path / test_file, module_index)
        all_unresolved.extend(unresolved)
        for imported_file in resolved:
            inbound_tests[imported_file].add(test_file)

    # Converte sets para listas
    inbound_src = {k: sorted(v) for k, v in inbound_src.items()}
    inbound_tests = {k: sorted(v) for k, v in inbound_tests.items()}

    return inbound_src, inbound_tests, all_unresolved


# ============================================================================
# 5. DETECTAR IMPORTS DINÂMICOS
# ============================================================================

DYNAMIC_IMPORT_FUNCS = {"import_module", "__import__", "iter_modules", "run_module"}
MODULE_STRING_PATTERN = re.compile(r"\bsrc\.[a-zA-Z0-9_]+(\.[a-zA-Z0-9_]+)+\b")


def detect_dynamic_imports(file_path: Path) -> Optional[Dict]:
    """Detecta possíveis imports dinâmicos."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        tree = ast.parse(content, filename=str(file_path))
    except Exception:
        return None

    examples = []

    # Procura chamadas de função
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func_name = None
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr

            if func_name in DYNAMIC_IMPORT_FUNCS:
                examples.append(f"call: {func_name}(...)")

    # Procura strings com padrão de módulo
    module_strings = MODULE_STRING_PATTERN.findall(content)
    for match in module_strings[:3]:  # Limita a 3 exemplos
        examples.append(f"string: src.{match}")

    if examples:
        return {
            "file": str(file_path).replace("\\", "/"),
            "examples": examples[:5],  # Limita a 5 exemplos
        }

    return None


# ============================================================================
# 6. SEM INBOUND REFS (candidatos a revisão)
# ============================================================================


def check_build_refs(root_path: Path, file_path: str) -> bool:
    """Verifica se arquivo é mencionado em arquivo de build."""
    spec_file = root_path / "rcgestor.spec"
    if not spec_file.exists():
        return False

    try:
        with open(spec_file, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return file_path in content or file_path.replace("/", "\\") in content
    except Exception:
        return False


def check_docs_mentions(root_path: Path, file_path: str) -> List[str]:
    """Verifica se arquivo é mencionado em docs/."""
    docs_path = root_path / "docs"
    if not docs_path.exists():
        return []

    mentions = []
    file_name = Path(file_path).name

    try:
        for doc_file in docs_path.glob("**/*.md"):
            try:
                with open(doc_file, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                if file_name in content or file_path in content:
                    rel_path = str(doc_file.relative_to(root_path)).replace("\\", "/")
                    mentions.append(rel_path)
            except Exception:
                continue
    except Exception:
        pass

    return mentions


def find_orphans(root_path: Path, src_files: List[str], inbound_src: Dict, inbound_tests: Dict) -> List[Dict]:
    """Encontra arquivos sem inbound refs (exceto entrypoints)."""
    orphans = []

    for src_file in src_files:
        # Exceções: __init__.py e entrypoints
        if src_file.endswith("__init__.py"):
            continue
        if src_file in ENTRYPOINTS:
            continue

        # Verifica inbound
        has_inbound_src = src_file in inbound_src and len(inbound_src[src_file]) > 0

        if not has_inbound_src:
            build_ref = check_build_refs(root_path, src_file)
            docs_mentions = check_docs_mentions(root_path, src_file)

            # Se tem build ref, por padrão não lista (mas registra metadata)
            if build_ref:
                continue

            orphans.append(
                {
                    "file": src_file,
                    "inbound_src": len(inbound_src.get(src_file, [])),
                    "inbound_tests": len(inbound_tests.get(src_file, [])),
                    "entrypoint_build_ref": build_ref,
                    "docs_mentions": docs_mentions,
                }
            )

    return orphans


# ============================================================================
# 7. GERAR RELATÓRIOS
# ============================================================================


def generate_markdown_report(output_path: Path, categories: Dict, totals: Dict):
    """Gera relatório em Markdown."""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# Relatório de Auditoria de Código Legado\n\n")
        f.write(f"**Data:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")

        # A. Shims/Compat
        f.write(f"## A. Shims/Compat prováveis ({totals['A']} arquivos)\n\n")
        if categories["A_shims_compat"]:
            for item in categories["A_shims_compat"]:
                f.write(f"- **{item['file']}**\n")
                f.write(f"  - Razão: {item['reason']}\n")
                f.write(f"  - Linhas relevantes: {item['lines_relevant']}\n")
                f.write(f"  - Ratio imports: {item['import_ratio']}\n\n")
        else:
            f.write("_Nenhum arquivo detectado._\n\n")

        # B. Deprecated/Legacy
        f.write(f"## B. Marcados DEPRECATED/LEGACY ({totals['B']} arquivos)\n\n")
        if categories["B_deprecated_legacy"]:
            for item in categories["B_deprecated_legacy"]:
                f.write(f"- **{item['file']}**\n")
                f.write(f"  - Termos: {', '.join(item['matches'])}\n")
                if item.get("contexts"):
                    f.write("  - Contexto:\n")
                    for ctx in item["contexts"]:
                        f.write(f"    - {ctx}\n")
                f.write("\n")
        else:
            f.write("_Nenhum arquivo detectado._\n\n")

        # C. Sem inbound refs
        f.write(f"## C. Sem inbound refs (candidatos a revisão) ({totals['C']} arquivos)\n\n")
        if categories["C_sem_inbound"]:
            for item in categories["C_sem_inbound"]:
                f.write(f"- **{item['file']}**\n")
                f.write(f"  - Inbound src: {item['inbound_src']}\n")
                f.write(f"  - Inbound tests: {item['inbound_tests']}\n")
                if item.get("docs_mentions"):
                    f.write(f"  - Mencionado em docs: {', '.join(item['docs_mentions'])}\n")
                f.write("\n")
        else:
            f.write("_Nenhum arquivo detectado._\n\n")

        # D. Imports dinâmicos
        f.write(f"## D. Possíveis imports dinâmicos ({totals['D']} arquivos)\n\n")
        if categories["D_imports_dinamicos"]:
            for item in categories["D_imports_dinamicos"]:
                f.write(f"- **{item['file']}**\n")
                f.write(f"  - Exemplos: {', '.join(item['examples'])}\n\n")
        else:
            f.write("_Nenhum arquivo detectado._\n\n")

        # Rodapé
        f.write("---\n\n")
        f.write("## Resumo\n\n")
        f.write(f"- **A - Shims/Compat:** {totals['A']}\n")
        f.write(f"- **B - Deprecated/Legacy:** {totals['B']}\n")
        f.write(f"- **C - Sem inbound refs:** {totals['C']}\n")
        f.write(f"- **D - Imports dinâmicos:** {totals['D']}\n")
        f.write(f"- **Imports não resolvidos:** {totals['unresolved']}\n")
        f.write(f"- **Erros de parse:** {totals['parse_errors']}\n")


def generate_json_report(output_path: Path, data: Dict):
    """Gera relatório em JSON."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ============================================================================
# MAIN
# ============================================================================


def main():
    """Executa auditoria completa."""
    root_path = Path.cwd()
    print(f"🔍 Auditando repositório: {root_path}\n")

    # 1. Descoberta
    print("📂 Descobrindo arquivos Python...")
    src_files, test_files = discover_python_files(root_path)
    print(f"   ✓ {len(src_files)} arquivos em src/")
    print(f"   ✓ {len(test_files)} arquivos em tests/\n")

    # 2. Categorias
    categories = {
        "A_shims_compat": [],
        "B_deprecated_legacy": [],
        "C_sem_inbound": [],
        "D_imports_dinamicos": [],
        "unresolved_imports": [],
        "parse_errors": [],
    }

    # 3. Análise de legado/shims
    print("🔎 Analisando marcadores de legado e shims...")
    for src_file in src_files:
        file_path = root_path / src_file

        # Shims
        shim = detect_shim(file_path)
        if shim:
            categories["A_shims_compat"].append(shim)

        # Legacy markers
        legacy = scan_legacy_markers(file_path)
        if legacy:
            categories["B_deprecated_legacy"].append(legacy)

        # Dynamic imports
        dynamic = detect_dynamic_imports(file_path)
        if dynamic:
            categories["D_imports_dinamicos"].append(dynamic)

    print(f"   ✓ {len(categories['A_shims_compat'])} shims/compat")
    print(f"   ✓ {len(categories['B_deprecated_legacy'])} deprecated/legacy")
    print(f"   ✓ {len(categories['D_imports_dinamicos'])} imports dinâmicos\n")

    # 4. Build module index e inbound refs
    print("📊 Construindo mapa de módulos e referências...")
    module_index = build_module_index(src_files)
    inbound_src, inbound_tests, unresolved = build_inbound_refs(root_path, src_files, test_files, module_index)
    categories["unresolved_imports"] = unresolved
    print(f"   ✓ {len(module_index)} módulos indexados")
    print(f"   ✓ {len(unresolved)} imports não resolvidos\n")

    # 5. Encontrar órfãos
    print("🔍 Identificando arquivos sem inbound refs...")
    orphans = find_orphans(root_path, src_files, inbound_src, inbound_tests)
    categories["C_sem_inbound"] = orphans
    print(f"   ✓ {len(orphans)} candidatos a revisão\n")

    # 6. Totais
    totals = {
        "A": len(categories["A_shims_compat"]),
        "B": len(categories["B_deprecated_legacy"]),
        "C": len(categories["C_sem_inbound"]),
        "D": len(categories["D_imports_dinamicos"]),
        "unresolved": len(categories["unresolved_imports"]),
        "parse_errors": len(categories["parse_errors"]),
    }

    # 7. Gerar relatórios
    print("📝 Gerando relatórios...")
    docs_path = root_path / "docs"
    docs_path.mkdir(exist_ok=True)

    md_path = docs_path / "legacy_audit_report.md"
    json_path = docs_path / "legacy_audit_report.json"

    generate_markdown_report(md_path, categories, totals)

    json_data = {**categories, "totals": totals}
    generate_json_report(json_path, json_data)

    print(f"   ✓ {md_path}")
    print(f"   ✓ {json_path}\n")

    # 8. Resumo no terminal
    print("=" * 60)
    print("📊 RESUMO DA AUDITORIA")
    print("=" * 60)
    print(f"A - Shims/Compat prováveis:      {totals['A']:4d}")
    print(f"B - Marcados DEPRECATED/LEGACY:  {totals['B']:4d}")
    print(f"C - Sem inbound refs:            {totals['C']:4d}")
    print(f"D - Imports dinâmicos:           {totals['D']:4d}")
    print("-" * 60)
    print(f"Imports não resolvidos:          {totals['unresolved']:4d}")
    print(f"Erros de parse:                  {totals['parse_errors']:4d}")
    print("=" * 60)
    print("\n✅ Auditoria concluída com sucesso!")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        import traceback

        traceback.print_exc()
