#!/usr/bin/env python3
"""
Script de consolidação de módulos duplicados.
Detecta arquivos com mesmo nome, constrói grafo de imports,
elege módulos canônicos e gera relatórios.
"""
import ast
import hashlib
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# Configurações
ROOT = Path(__file__).parent.parent
AJUDA = ROOT / "ajuda"
AJUDA.mkdir(exist_ok=True)

# Pastas a analisar
SOURCE_FOLDERS = [
    "application",
    "gui",
    "ui",
    "core",
    "infra",
    "utils",
    "adapters",
    "shared",
    "detectors",
    "config",
    "assets",
]

# Ignorar
IGNORE_PATTERNS = {
    ".venv",
    "runtime",
    "build",
    "dist",
    "__pycache__",
    "tests",
    "ajuda",
    ".github",
    ".git",
    ".pytest_cache",
    "*.egg-info",
}

# Classificação de camadas
LAYER_PRIORITY = {
    "ui": 10,  # UI é a camada mais externa
    "gui": 9,
    "application": 8,
    "core": 7,  # Core/domínio no meio
    "adapters": 6,
    "shared": 5,
    "infra": 4,  # Infra é a camada mais interna
    "utils": 3,
    "config": 2,
    "detectors": 2,
    "assets": 1,
}

# Mapeamento de assunto → camada ideal
SUBJECT_TO_LAYER = {
    "login": "ui/login",
    "theme": "ui",
    "theme_toggle": "ui",
    "auth": "core/auth",
    "db_manager": "core/db_manager",
    "session": "core/session",
    "supabase_client": "infra",
    "supabase_auth": "infra",
    "storage": "adapters/storage",
}


def should_ignore(path: Path) -> bool:
    """Verifica se o caminho deve ser ignorado."""
    parts = path.parts
    for pattern in IGNORE_PATTERNS:
        if pattern.startswith("*"):
            if path.name.endswith(pattern[1:]):
                return True
        else:
            if pattern in parts:
                return True
    return False


def compute_sha256(filepath: Path) -> str:
    """Calcula SHA-256 de um arquivo."""
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            sha.update(chunk)
    return sha.hexdigest()


def count_lines(filepath: Path) -> int:
    """Conta linhas de código (não vazias, não comentários)."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = [
                line.strip()
                for line in f
                if line.strip() and not line.strip().startswith("#")
            ]
        return len(lines)
    except Exception:
        return 0


def count_imports(filepath: Path) -> int:
    """Conta número de imports no arquivo."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = [
                line.strip()
                for line in f
                if line.strip().startswith(("import ", "from "))
            ]
        return len(lines)
    except Exception:
        return 0


def find_all_python_files() -> List[Path]:
    """Encontra todos os arquivos Python nas pastas de código."""
    files = []
    for folder in SOURCE_FOLDERS:
        folder_path = ROOT / folder
        if not folder_path.exists():
            continue
        for py_file in folder_path.rglob("*.py"):
            if not should_ignore(py_file):
                files.append(py_file)
    return files


def group_by_basename(files: List[Path]) -> Dict[str, List[Path]]:
    """Agrupa arquivos por basename."""
    groups = defaultdict(list)
    for file in files:
        groups[file.name].append(file)
    return dict(groups)


def get_file_info(filepath: Path) -> Dict:
    """Extrai informações de um arquivo."""
    stat = filepath.stat()
    return {
        "path": str(filepath.relative_to(ROOT)),
        "full_path": str(filepath),
        "size": stat.st_size,
        "sha256": compute_sha256(filepath),
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "lines": count_lines(filepath),
        "imports": count_imports(filepath),
    }


class SimpleImportGraph:
    """Grafo de imports simplificado usando AST."""

    def __init__(self):
        self.modules = {}  # module_name -> file_path
        self.imports = {}  # module_name -> [imported_modules]
        self.importers = defaultdict(list)  # module_name -> [modules_that_import_it]

    def add_module(self, module_name: str, file_path: Path):
        """Adiciona um módulo ao grafo."""
        self.modules[module_name] = file_path

    def add_import(self, importer: str, imported: str):
        """Registra uma relação de import."""
        if importer not in self.imports:
            self.imports[importer] = []
        self.imports[importer].append(imported)
        self.importers[imported].append(importer)

    def get_importers(self, module_name: str) -> List[str]:
        """Retorna lista de módulos que importam este módulo."""
        return self.importers.get(module_name, [])

    def get_imports(self, module_name: str) -> List[str]:
        """Retorna lista de módulos importados por este módulo."""
        return self.imports.get(module_name, [])

    def get_centrality(self, module_name: str) -> int:
        """Retorna número de importadores (centralidade)."""
        return len(self.get_importers(module_name))


def extract_imports_from_file(file_path: Path) -> List[str]:
    """Extrai imports de um arquivo Python usando AST."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content)
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module.split(".")[0])

        return list(set(imports))
    except Exception:
        return []


def build_import_graph() -> SimpleImportGraph:
    """Constrói grafo de imports do projeto usando AST."""
    print("📊 Construindo grafo de imports (análise AST)...")

    graph = SimpleImportGraph()

    # Encontrar todos os arquivos Python
    files = find_all_python_files()

    # Mapear arquivos para nomes de módulos
    file_to_module = {}
    module_to_file = {}

    for file_path in files:
        rel_path = file_path.relative_to(ROOT)
        module_name = str(rel_path.with_suffix("")).replace("\\", ".").replace("/", ".")

        file_to_module[file_path] = module_name
        module_to_file[module_name] = file_path
        graph.add_module(module_name, file_path)

    # Extrair imports de cada arquivo
    for file_path, module_name in file_to_module.items():
        imports = extract_imports_from_file(file_path)

        for imported in imports:
            # Tentar encontrar se é um módulo local
            for candidate_module in module_to_file.keys():
                if candidate_module.startswith(imported):
                    graph.add_import(module_name, candidate_module)
                    break

    print(f"   ✓ Grafo construído: {len(graph.modules)} módulos")
    return graph


def analyze_dependencies(graph: SimpleImportGraph, module_path: Path) -> Dict:
    """Analisa dependências de um módulo no grafo."""
    if graph is None:
        return {"importers": [], "imports": [], "centrality": 0}

    # Converter path para nome de módulo (ex: ui/login/login.py -> ui.login.login)
    rel_path = module_path.relative_to(ROOT)
    module_name = str(rel_path.with_suffix("")).replace("\\", ".").replace("/", ".")

    try:
        importers = graph.get_importers(module_name)
        imports = graph.get_imports(module_name)
        centrality = graph.get_centrality(module_name)

        return {
            "importers": importers,
            "imports": imports,
            "centrality": centrality,
        }
    except Exception as e:
        print(f"   ⚠ Erro analisando {module_name}: {e}")
        return {"importers": [], "imports": [], "centrality": 0}


def get_layer_priority(filepath: Path) -> int:
    """Retorna prioridade da camada do arquivo."""
    parts = filepath.relative_to(ROOT).parts
    if not parts:
        return 0

    first_part = parts[0]
    return LAYER_PRIORITY.get(first_part, 0)


def get_ideal_layer(basename: str) -> str:
    """Retorna camada ideal para um assunto."""
    base = basename.replace(".py", "")
    return SUBJECT_TO_LAYER.get(base, "")


def elect_canonical(
    group_name: str, files: List[Path], graph: SimpleImportGraph
) -> Tuple[Path, str]:
    """
    Elege o arquivo canônico de um grupo.

    Heurística:
    1. Camada certa (se definida)
    2. Mais referenciado (centralidade)
    3. Mais recente
    4. Maior (linhas)

    Retorna: (arquivo_canônico, justificativa)
    """
    ideal_layer = get_ideal_layer(group_name)

    # Coletar métricas
    candidates = []
    for file in files:
        deps = analyze_dependencies(graph, file)
        info = get_file_info(file)
        layer_priority = get_layer_priority(file)

        # Verificar se está na camada ideal
        rel_path = str(file.relative_to(ROOT)).replace("\\", "/")
        in_ideal_layer = ideal_layer and rel_path.startswith(ideal_layer)

        candidates.append(
            {
                "file": file,
                "in_ideal_layer": in_ideal_layer,
                "layer_priority": layer_priority,
                "centrality": deps["centrality"],
                "modified": info["modified"],
                "lines": info["lines"],
                "info": info,
                "deps": deps,
            }
        )

    # Ordenar por heurística
    def sort_key(c):
        return (
            c["in_ideal_layer"],  # Camada ideal (True > False)
            c["centrality"],  # Mais importado
            c["modified"],  # Mais recente
            c["lines"],  # Maior
        )

    candidates.sort(key=sort_key, reverse=True)
    winner = candidates[0]

    # Justificativa
    reasons = []
    if winner["in_ideal_layer"]:
        reasons.append(f"camada ideal ({ideal_layer})")
    if winner["centrality"] > 0:
        reasons.append(f"mais importado ({winner['centrality']} refs)")
    reasons.append(f"{winner['lines']} linhas")

    justification = " + ".join(reasons) if reasons else "único candidato"

    return winner["file"], justification


def generate_markdown_report(duplicates: Dict, canonicals: Dict) -> str:
    """Gera relatório em Markdown."""
    lines = [
        "# Relatório de Módulos Duplicados\n",
        f"**Data:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        f"**Total de grupos duplicados:** {len(duplicates)}\n",
        "---\n",
    ]

    for group_name in sorted(duplicates.keys()):
        files_info = duplicates[group_name]
        canonical = canonicals.get(group_name, {})

        lines.append(f"\n## 📦 Grupo: `{group_name}`\n")
        lines.append(f"**Total de arquivos:** {len(files_info)}\n")

        if canonical:
            lines.append(f"**✅ Canônico eleito:** `{canonical['path']}`\n")
            lines.append(f"**Justificativa:** {canonical['justification']}\n")

        lines.append("\n### Arquivos no grupo:\n")
        lines.append(
            "| Caminho | Linhas | Imports | SHA-256 (6) | Modificado | Centralidade |\n"
        )
        lines.append(
            "|---------|--------|---------|-------------|------------|-------------|\n"
        )

        for info in files_info:
            is_canonical = canonical and info["path"] == canonical["path"]
            marker = "**✅**" if is_canonical else ""

            lines.append(
                f"| {marker} `{info['path']}` | {info['lines']} | {info['imports']} | "
                f"`{info['sha256'][:6]}...` | {info['modified'][:10]} | "
                f"{info.get('centrality', 0)} |\n"
            )

        lines.append("\n")

    return "".join(lines)


def generate_canonicals_report(canonicals: Dict) -> str:
    """Gera relatório de módulos canônicos."""
    lines = [
        "# Módulos Canônicos Eleitos\n",
        f"**Data:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        "---\n\n",
    ]

    for group_name in sorted(canonicals.keys()):
        canonical = canonicals[group_name]
        lines.append(f"## `{group_name}`\n")
        lines.append(f"- **Canônico:** `{canonical['path']}`\n")
        lines.append(f"- **Justificativa:** {canonical['justification']}\n")
        lines.append(f"- **Linhas:** {canonical.get('lines', 0)}\n")
        lines.append(f"- **Centralidade:** {canonical.get('centrality', 0)}\n")
        lines.append("\n")

    return "".join(lines)


def main():
    """Execução principal."""
    print("🔍 Etapa 1: Scanner de duplicados + grafo de imports\n")

    # 1. Encontrar todos os arquivos Python
    print("📂 Buscando arquivos Python...")
    files = find_all_python_files()
    print(f"   ✓ Encontrados {len(files)} arquivos\n")

    # 2. Agrupar por basename
    print("📑 Agrupando por basename...")
    groups = group_by_basename(files)
    duplicates = {name: paths for name, paths in groups.items() if len(paths) > 1}
    print(f"   ✓ {len(duplicates)} grupos com duplicados\n")

    # 3. Construir grafo de imports
    graph = build_import_graph()
    print()

    # 4. Analisar cada grupo
    print("🔎 Analisando grupos duplicados...")
    duplicates_info = {}
    canonicals = {}

    for group_name, paths in duplicates.items():
        print(f"   • {group_name}: {len(paths)} arquivos")

        # Coletar info de cada arquivo
        files_info = []
        for path in paths:
            info = get_file_info(path)
            deps = analyze_dependencies(graph, path)
            info["centrality"] = deps["centrality"]
            info["importers"] = deps["importers"]
            info["imports"] = deps["imports"]
            files_info.append(info)

        duplicates_info[group_name] = files_info

        # Eleger canônico
        canonical_path, justification = elect_canonical(group_name, paths, graph)
        canonical_info = next(
            f for f in files_info if f["path"] == str(canonical_path.relative_to(ROOT))
        )

        canonicals[group_name] = {
            "path": canonical_info["path"],
            "full_path": canonical_info["full_path"],
            "justification": justification,
            "lines": canonical_info["lines"],
            "centrality": canonical_info["centrality"],
        }

    print(f"   ✓ {len(canonicals)} canônicos eleitos\n")

    # 5. Salvar relatórios
    print("💾 Salvando relatórios...")

    # JSON
    json_report = {
        "timestamp": datetime.now().isoformat(),
        "total_files": len(files),
        "duplicate_groups": len(duplicates),
        "duplicates": duplicates_info,
        "canonicals": canonicals,
    }

    json_path = AJUDA / "DUPES_REPORT.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_report, f, indent=2, ensure_ascii=False)
    print(f"   ✓ {json_path}")

    # Markdown
    md_report = generate_markdown_report(duplicates_info, canonicals)
    md_path = AJUDA / "DUPES_REPORT.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_report)
    print(f"   ✓ {md_path}")

    # Canônicos
    canonicals_md = generate_canonicals_report(canonicals)
    canonicals_path = AJUDA / "CANONICOS.md"
    with open(canonicals_path, "w", encoding="utf-8") as f:
        f.write(canonicals_md)
    print(f"   ✓ {canonicals_path}")

    print("\n✅ Etapa 1 concluída!")
    print("\n📊 Resumo:")
    print(f"   • {len(files)} arquivos analisados")
    print(f"   • {len(duplicates)} grupos duplicados")
    print(f"   • {len(canonicals)} canônicos eleitos")
    print(f"\n📁 Relatórios salvos em: {AJUDA}")


if __name__ == "__main__":
    main()
