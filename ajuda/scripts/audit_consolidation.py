#!/usr/bin/env python3
"""
Auditoria & Proposta de Consolidação de Módulos (DRY-RUN)
==========================================================

Este script realiza uma análise profunda do projeto para encontrar:
- Módulos com nomes semelhantes (fuzzy matching)
- Conteúdo duplicado (AST comparison)
- Grafo de imports (quem usa quem)
- Módulos órfãos (não importados)
- Proposta de consolidação (sem aplicar nada)

Ferramentas usadas:
- RapidFuzz: Fuzzy matching de nomes
- LibCST: Análise AST e comparação de código
- AST: Extração de assinaturas
- Vulture: Detecção de código não usado
"""

import ast
import json
import re
from collections import defaultdict
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any

try:
    from rapidfuzz import fuzz

    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False
    print("⚠ RapidFuzz não disponível, usando difflib")

try:
    import libcst  # noqa: F401 - usado para verificar disponibilidade

    HAS_LIBCST = True
except ImportError:
    HAS_LIBCST = False
    print("⚠ LibCST não disponível, usando AST padrão")

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

ROOT = Path(__file__).parent.parent
OUTPUT_DIR = ROOT / "ajuda" / "dup-consolidacao"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Pastas a analisar
SOURCE_FOLDERS = [
    "application",
    "gui",
    "ui",
    "core",
    "infra",
    "adapters",
    "shared",
    "utils",
    "detectors",
    "config",
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
    "docs",
    ".github",
    ".git",
    ".pytest_cache",
    "*.egg-info",
    "_quarentena",
}

# Thresholds (ajustados conforme PROMPT ÚNICO)
FUZZY_NAME_THRESHOLD = 80  # token_set_ratio (RapidFuzz) - grupos por nome similar
FUZZY_CONSOLIDATE_THRESHOLD = 85  # Para sugerir consolidação automática
AST_SIMILARITY_THRESHOLD = 60  # Similaridade estrutural CST/AST
SIGNATURE_OVERLAP_THRESHOLD = 60  # % de assinaturas em comum
MAX_REWRITE_FILES = 40  # Máximo de arquivos para reescrever imports

# Prioridade de camadas (maior = mais prioritário para ser canônico)
LAYER_PRIORITY = {
    "application": 100,
    "core": 90,
    "adapters": 70,
    "shared": 60,
    "infra": 50,
    "gui": 40,
    "ui": 30,
    "utils": 20,
    "config": 10,
    "detectors": 10,
}

# ============================================================================
# UTILIDADES
# ============================================================================


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


def normalize_name(name: str) -> str:
    """Normaliza nome de arquivo para comparação."""
    # Remove .py
    name = name.replace(".py", "")
    # Normaliza underscores/hífens
    name = name.replace("-", "_")
    # Snake case
    name = name.lower()
    return name


def fuzzy_match_names(name1: str, name2: str) -> float:
    """Calcula similaridade entre nomes (0-100) usando token_set_ratio."""
    if HAS_RAPIDFUZZ:
        # token_set_ratio é melhor para nomes com palavras reordenadas
        # Ex: "login_dialog" vs "dialog_login" = 100%
        return fuzz.token_set_ratio(name1, name2)
    else:
        return SequenceMatcher(None, name1, name2).ratio() * 100


# ============================================================================
# ANÁLISE AST
# ============================================================================


class CodeAnalyzer:
    """Analisa código Python extraindo assinaturas e estrutura."""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.content = None
        self.tree = None
        self.functions = []
        self.classes = []
        self.imports = []
        self.all_names = set()

    def analyze(self) -> bool:
        """Analisa o arquivo."""
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                self.content = f.read()

            self.tree = ast.parse(self.content)
            self._extract_signatures()
            self._extract_imports()
            return True
        except Exception as e:
            print(f"  ⚠ Erro analisando {self.file_path}: {e}")
            return False

    def _extract_signatures(self):
        """Extrai assinaturas de funções e classes."""
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef):
                sig = self._get_function_signature(node)
                self.functions.append(sig)
                self.all_names.add(node.name)

            elif isinstance(node, ast.ClassDef):
                methods = []
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        methods.append(item.name)

                self.classes.append(
                    {
                        "name": node.name,
                        "methods": methods,
                    }
                )
                self.all_names.add(node.name)

    def _get_function_signature(self, node: ast.FunctionDef) -> Dict:
        """Extrai assinatura de uma função."""
        args = []
        for arg in node.args.args:
            args.append(arg.arg)

        return {
            "name": node.name,
            "args": args,
            "returns": ast.unparse(node.returns) if node.returns else None,
        }

    def _extract_imports(self):
        """Extrai imports do arquivo."""
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.imports.append(alias.name.split(".")[0])

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self.imports.append(node.module.split(".")[0])

    def get_signature_set(self) -> Set[str]:
        """Retorna conjunto de assinaturas únicas."""
        sigs = set()
        for func in self.functions:
            sig_str = f"{func['name']}({','.join(func['args'])})"
            sigs.add(sig_str)
        for cls in self.classes:
            sigs.add(f"class:{cls['name']}")
            for method in cls["methods"]:
                sigs.add(f"{cls['name']}.{method}")
        return sigs

    def compute_ast_similarity(self, other: "CodeAnalyzer") -> float:
        """Calcula similaridade AST entre dois arquivos (0-100)."""
        if not self.tree or not other.tree:
            return 0.0

        # Comparar estrutura normalizada
        self_dump = ast.dump(self.tree, annotate_fields=False)
        other_dump = ast.dump(other.tree, annotate_fields=False)

        # Remove literals/strings específicos para comparar estrutura
        self_clean = re.sub(r"'[^']*'", "STR", self_dump)
        other_clean = re.sub(r"'[^']*'", "STR", other_dump)

        return SequenceMatcher(None, self_clean, other_clean).ratio() * 100


# ============================================================================
# GRAFO DE IMPORTS
# ============================================================================


class ImportGraph:
    """Grafo de imports do projeto."""

    def __init__(self):
        self.nodes = {}  # module_name -> file_path
        self.edges = defaultdict(list)  # module_name -> [imported_modules]
        self.reverse_edges = defaultdict(list)  # module_name -> [importers]
        self.analyzers = {}  # file_path -> CodeAnalyzer

    def build(self, files: List[Path]):
        """Constrói o grafo a partir dos arquivos."""
        print("\n📊 Construindo grafo de imports...")

        # Primeira passagem: mapear arquivos para módulos
        for file_path in files:
            rel_path = file_path.relative_to(ROOT)
            module_name = (
                str(rel_path.with_suffix("")).replace("\\", ".").replace("/", ".")
            )
            self.nodes[module_name] = file_path

            # Analisar arquivo
            analyzer = CodeAnalyzer(file_path)
            if analyzer.analyze():
                self.analyzers[file_path] = analyzer

        print(f"   ✓ {len(self.nodes)} módulos mapeados")

        # Segunda passagem: construir arestas
        for module_name, file_path in self.nodes.items():
            if file_path not in self.analyzers:
                continue

            analyzer = self.analyzers[file_path]
            for imported_pkg in analyzer.imports:
                # Tentar encontrar módulo local
                for candidate in self.nodes.keys():
                    if candidate.startswith(imported_pkg):
                        self.edges[module_name].append(candidate)
                        self.reverse_edges[candidate].append(module_name)

        print(
            f"   ✓ {sum(len(v) for v in self.edges.values())} dependências encontradas"
        )

    def get_importers(self, module_name: str) -> List[str]:
        """Retorna módulos que importam este módulo."""
        return self.reverse_edges.get(module_name, [])

    def get_imports(self, module_name: str) -> List[str]:
        """Retorna módulos importados por este módulo."""
        return self.edges.get(module_name, [])

    def get_in_degree(self, module_name: str) -> int:
        """Retorna número de importadores (centralidade)."""
        return len(self.get_importers(module_name))

    def is_orphan(self, module_name: str) -> bool:
        """Verifica se módulo é órfão (não importado)."""
        return self.get_in_degree(module_name) == 0

    def get_top_referenced(self, n: int = 10) -> List[Tuple[str, int]]:
        """Retorna os N módulos mais referenciados."""
        scores = [(mod, self.get_in_degree(mod)) for mod in self.nodes.keys()]
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:n]

    def export_summary(self) -> Dict:
        """Exporta resumo do grafo."""
        return {
            "total_nodes": len(self.nodes),
            "total_edges": sum(len(v) for v in self.edges.values()),
            "orphans": sum(1 for mod in self.nodes if self.is_orphan(mod)),
            "top_referenced": [
                {"module": mod, "in_degree": deg}
                for mod, deg in self.get_top_referenced(20)
            ],
        }


# ============================================================================
# DETECÇÃO DE DUPLICADOS
# ============================================================================


def find_similar_names(
    files: List[Path], threshold: float = FUZZY_NAME_THRESHOLD
) -> Dict[str, List[Path]]:
    """Agrupa arquivos por similaridade de nome."""
    print(f"\n🔍 Buscando nomes similares (threshold={threshold})...")

    groups = defaultdict(list)
    processed = set()

    for i, file1 in enumerate(files):
        if file1 in processed:
            continue

        name1 = normalize_name(file1.name)
        group = [file1]
        processed.add(file1)

        for file2 in files[i + 1 :]:
            if file2 in processed:
                continue

            name2 = normalize_name(file2.name)
            score = fuzzy_match_names(name1, name2)

            if score >= threshold:
                group.append(file2)
                processed.add(file2)

        if len(group) > 1:
            groups[name1] = group

    print(f"   ✓ {len(groups)} grupos encontrados")
    return dict(groups)


def analyze_duplicate_groups(
    groups: Dict[str, List[Path]], graph: ImportGraph
) -> Dict[str, Any]:
    """Analisa grupos duplicados em profundidade."""
    print("\n🔬 Analisando grupos duplicados...")

    results = {}

    for group_name, files in groups.items():
        print(f"\n  📦 Grupo: {group_name} ({len(files)} arquivos)")

        group_data = {
            "files": [],
            "canonical_suggestion": None,
            "consolidation_feasible": False,
            "reasons": [],
        }

        # Analisar cada arquivo do grupo
        for file_path in files:
            rel_path = file_path.relative_to(ROOT)
            module_name = (
                str(rel_path.with_suffix("")).replace("\\", ".").replace("/", ".")
            )

            analyzer = graph.analyzers.get(file_path)
            if not analyzer:
                continue

            file_data = {
                "path": str(rel_path),
                "module_name": module_name,
                "layer": rel_path.parts[0] if rel_path.parts else "",
                "in_degree": graph.get_in_degree(module_name),
                "importers": graph.get_importers(module_name),
                "functions": [f["name"] for f in analyzer.functions],
                "classes": [c["name"] for c in analyzer.classes],
                "signatures": list(analyzer.get_signature_set()),
                "size_bytes": file_path.stat().st_size,
                "lines": len(analyzer.content.splitlines()) if analyzer.content else 0,
            }

            group_data["files"].append(file_data)

        # Calcular similaridades AST
        if len(group_data["files"]) >= 2:
            similarities = []
            for i, file1_data in enumerate(group_data["files"]):
                for file2_data in group_data["files"][i + 1 :]:
                    file1_path = ROOT / file1_data["path"]
                    file2_path = ROOT / file2_data["path"]

                    analyzer1 = graph.analyzers.get(file1_path)
                    analyzer2 = graph.analyzers.get(file2_path)

                    if analyzer1 and analyzer2:
                        ast_sim = analyzer1.compute_ast_similarity(analyzer2)

                        # Overlap de assinaturas
                        sigs1 = set(file1_data["signatures"])
                        sigs2 = set(file2_data["signatures"])
                        if sigs1 or sigs2:
                            sig_overlap = (
                                len(sigs1 & sigs2) / max(len(sigs1), len(sigs2)) * 100
                            )
                        else:
                            sig_overlap = 0

                        similarities.append(
                            {
                                "pair": [file1_data["path"], file2_data["path"]],
                                "ast_similarity": round(ast_sim, 2),
                                "signature_overlap": round(sig_overlap, 2),
                            }
                        )

            group_data["similarities"] = similarities

        # Eleger canônico
        canonical = elect_canonical(group_data, graph)
        group_data["canonical_suggestion"] = canonical

        # Avaliar viabilidade de consolidação
        feasibility = assess_consolidation_feasibility(group_data)
        group_data.update(feasibility)

        results[group_name] = group_data

    return results


def elect_canonical(group_data: Dict, graph: ImportGraph) -> Dict:
    """Elege arquivo canônico de um grupo."""
    files = group_data["files"]
    if not files:
        return None

    # Calcular scores
    scores = []
    for file_data in files:
        layer_priority = LAYER_PRIORITY.get(file_data["layer"], 0)
        in_degree = file_data["in_degree"]
        size = file_data["lines"]

        # Score ponderado
        score = (
            layer_priority * 10  # Camada certa
            + in_degree * 50  # Mais referenciado
            + size * 0.1  # Maior (desempate)
        )

        scores.append(
            {
                "path": file_data["path"],
                "module_name": file_data["module_name"],
                "score": score,
                "layer_priority": layer_priority,
                "in_degree": in_degree,
                "lines": size,
            }
        )

    # Ordenar por score
    scores.sort(key=lambda x: x["score"], reverse=True)
    winner = scores[0]

    # Justificativa
    reasons = []
    if winner["layer_priority"] > 0:
        reasons.append(f"camada prioritária ({winner['layer_priority']})")
    if winner["in_degree"] > 0:
        reasons.append(f"mais referenciado ({winner['in_degree']} importers)")
    reasons.append(f"{winner['lines']} linhas")

    winner["justification"] = " + ".join(reasons)
    winner["alternatives"] = scores[1:] if len(scores) > 1 else []

    return winner


def assess_consolidation_feasibility(group_data: Dict) -> Dict:
    """
    Avalia se consolidação é viável usando os critérios do PROMPT ÚNICO:
    - score_fuzzy ≥ 85 (já filtrado no agrupamento)
    - score_struct ≥ 60 (AST similarity)
    - somatório de importadores < 40
    Caso contrário, marcar como "camadas diferentes" ou "alto custo de reescrita".
    """
    files = group_data["files"]
    similarities = group_data.get("similarities", [])
    fuzzy_score = group_data.get("fuzzy_score", 0)

    # Critérios
    consolidation_feasible = False
    reasons = []
    risks = []

    # 1. Verificar similaridade de nome (fuzzy) - já deve estar ≥ 80 para estar aqui
    if fuzzy_score < FUZZY_CONSOLIDATE_THRESHOLD:
        reasons.append(
            f"Similaridade de nome insuficiente ({fuzzy_score:.1f} < {FUZZY_CONSOLIDATE_THRESHOLD})"
        )

    # 2. Verificar similaridade estrutural (AST)
    if similarities:
        max_ast_sim = max((s["ast_similarity"] for s in similarities), default=0)
        max_sig_overlap = max((s["signature_overlap"] for s in similarities), default=0)

        if max_ast_sim >= AST_SIMILARITY_THRESHOLD:
            reasons.append(f"Similaridade AST suficiente ({max_ast_sim:.1f}%)")
        else:
            reasons.append(
                f"Similaridade AST baixa ({max_ast_sim:.1f}% < {AST_SIMILARITY_THRESHOLD}%)"
            )

        if max_sig_overlap >= SIGNATURE_OVERLAP_THRESHOLD:
            reasons.append(
                f"Overlap de assinaturas suficiente ({max_sig_overlap:.1f}%)"
            )
        else:
            reasons.append(
                f"Overlap de assinaturas baixo ({max_sig_overlap:.1f}% < {SIGNATURE_OVERLAP_THRESHOLD}%)"
            )

        # Critério combinado para consolidação automática
        # fuzzy ≥ 85 E struct ≥ 60 E importers < 40
        total_importers = sum(len(f["importers"]) for f in files)

        if (
            fuzzy_score >= FUZZY_CONSOLIDATE_THRESHOLD
            and max_ast_sim >= AST_SIMILARITY_THRESHOLD
            and total_importers < MAX_REWRITE_FILES
        ):
            consolidation_feasible = True
            reasons.append(
                f"✅ CRITÉRIOS ATENDIDOS: fuzzy={fuzzy_score:.1f}≥85, AST={max_ast_sim:.1f}≥60, importers={total_importers}<40"
            )
        else:
            reasons.append("❌ Critérios não atendidos para consolidação automática")
    else:
        reasons.append("Sem análise de similaridade disponível")

    # 3. Verificar se são camadas diferentes
    layers = set(f["layer"] for f in files)
    if len(layers) > 1:
        # Camadas diferentes: cautela
        if "application" in layers and "adapters" in layers:
            risks.append(
                "Camadas diferentes (application vs adapters) - podem ter propósitos distintos"
            )
        elif "core" in layers and "ui" in layers:
            risks.append("Violação de arquitetura (core vs ui) - NÃO consolidar")
            consolidation_feasible = False
        else:
            risks.append(
                f"Camadas diferentes ({', '.join(layers)}) - verificar propósito"
            )

    # 4. Verificar custo de reescrita
    total_importers = sum(len(f["importers"]) for f in files)
    if total_importers > MAX_REWRITE_FILES:
        risks.append(
            f"Muitos importers ({total_importers} > {MAX_REWRITE_FILES}) - custo alto de reescrita"
        )
        consolidation_feasible = False
    else:
        if total_importers > 0:
            reasons.append(
                f"Custo de reescrita aceitável ({total_importers} importers)"
            )

    # 5. Verificar se algum é órfão
    orphans = [f for f in files if f["in_degree"] == 0]
    if orphans:
        reasons.append(f"{len(orphans)} arquivo(s) órfão(s) - pode(m) ser removido(s)")

    return {
        "consolidation_feasible": consolidation_feasible,
        "consolidation_reasons": reasons,
        "consolidation_risks": risks,
    }


# ============================================================================
# ÓRFÃOS
# ============================================================================


def find_orphans(graph: ImportGraph) -> List[Dict]:
    """Encontra módulos órfãos (não importados)."""
    print("\n🔍 Buscando módulos órfãos...")

    orphans = []
    for module_name, file_path in graph.nodes.items():
        if graph.is_orphan(module_name):
            rel_path = file_path.relative_to(ROOT)

            # Verificar se é __init__.py ou arquivo especial
            is_init = file_path.name == "__init__.py"
            is_main = file_path.name in ["__main__.py", "main.py", "app.py"]
            is_script = any(p in str(rel_path) for p in ["scripts", "tests"])

            orphans.append(
                {
                    "module": module_name,
                    "path": str(rel_path),
                    "is_init": is_init,
                    "is_main": is_main,
                    "is_script": is_script,
                    "likely_safe_to_remove": not (is_init or is_main or is_script),
                }
            )

    print(f"   ✓ {len(orphans)} órfãos encontrados")
    return orphans


# ============================================================================
# GERAÇÃO DE RELATÓRIOS
# ============================================================================


def generate_reports(
    duplicate_groups: Dict,
    graph: ImportGraph,
    orphans: List[Dict],
):
    """Gera todos os relatórios."""
    print("\n📝 Gerando relatórios...")

    # 1. DUP_GROUPS.json
    dup_groups_path = OUTPUT_DIR / "DUP_GROUPS.json"
    with open(dup_groups_path, "w", encoding="utf-8") as f:
        json.dump(duplicate_groups, f, indent=2, ensure_ascii=False)
    print(f"   ✓ {dup_groups_path}")

    # 2. IMPORT_GRAPH_SUMMARY.json
    graph_summary = graph.export_summary()
    graph_path = OUTPUT_DIR / "IMPORT_GRAPH_SUMMARY.json"
    with open(graph_path, "w", encoding="utf-8") as f:
        json.dump(graph_summary, f, indent=2, ensure_ascii=False)
    print(f"   ✓ {graph_path}")

    # 3. CANONICAL_PROPOSAL.md
    canonical_md = generate_canonical_proposal_md(duplicate_groups)
    canonical_path = OUTPUT_DIR / "CANONICAL_PROPOSAL.md"
    with open(canonical_path, "w", encoding="utf-8") as f:
        f.write(canonical_md)
    print(f"   ✓ {canonical_path}")

    # 4. ORPHANS.md
    orphans_md = generate_orphans_md(orphans)
    orphans_path = OUTPUT_DIR / "ORPHANS.md"
    with open(orphans_path, "w", encoding="utf-8") as f:
        f.write(orphans_md)
    print(f"   ✓ {orphans_path}")

    # 5. ACTIONS_DRY_RUN.md
    actions_md = generate_actions_md(duplicate_groups, orphans)
    actions_path = OUTPUT_DIR / "ACTIONS_DRY_RUN.md"
    with open(actions_path, "w", encoding="utf-8") as f:
        f.write(actions_md)
    print(f"   ✓ {actions_path}")

    # 6. RISKS.md
    risks_md = generate_risks_md(duplicate_groups)
    risks_path = OUTPUT_DIR / "RISKS.md"
    with open(risks_path, "w", encoding="utf-8") as f:
        f.write(risks_md)
    print(f"   ✓ {risks_path}")

    # 7. HOW_TO_APPLY.md
    how_to_md = generate_how_to_apply_md(duplicate_groups, orphans)
    how_to_path = OUTPUT_DIR / "HOW_TO_APPLY.md"
    with open(how_to_path, "w", encoding="utf-8") as f:
        f.write(how_to_md)
    print(f"   ✓ {how_to_path}")


def generate_canonical_proposal_md(duplicate_groups: Dict) -> str:
    """Gera relatório de propostas canônicas."""
    lines = [
        "# Proposta de Módulos Canônicos\n",
        f"**Data:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        f"**Grupos analisados:** {len(duplicate_groups)}\n",
        "---\n\n",
    ]

    for group_name, group_data in duplicate_groups.items():
        lines.append(f"## 📦 Grupo: `{group_name}`\n\n")

        canonical = group_data.get("canonical_suggestion")
        if canonical:
            lines.append("### ✅ Canônico Sugerido\n\n")
            lines.append(f"**Arquivo:** `{canonical['path']}`\n\n")
            lines.append(f"**Justificativa:** {canonical['justification']}\n\n")
            lines.append(f"**Score:** {canonical['score']:.2f}\n\n")

        lines.append("### Arquivos no Grupo\n\n")
        lines.append("| Arquivo | Camada | In-Degree | Linhas | Funções | Classes |\n")
        lines.append("|---------|--------|-----------|--------|---------|----------|\n")

        for file_data in group_data["files"]:
            is_canonical = canonical and file_data["path"] == canonical["path"]
            marker = "**✅**" if is_canonical else ""

            lines.append(
                f"| {marker} `{file_data['path']}` | {file_data['layer']} | "
                f"{file_data['in_degree']} | {file_data['lines']} | "
                f"{len(file_data['functions'])} | {len(file_data['classes'])} |\n"
            )

        # Similaridades
        if "similarities" in group_data and group_data["similarities"]:
            lines.append("\n### Similaridades\n\n")
            lines.append("| Par | AST Sim % | Sig Overlap % |\n")
            lines.append("|-----|-----------|---------------|\n")

            for sim in group_data["similarities"]:
                pair_str = " ↔ ".join(f"`{p.split('/')[-1]}`" for p in sim["pair"])
                lines.append(
                    f"| {pair_str} | {sim['ast_similarity']} | "
                    f"{sim['signature_overlap']} |\n"
                )

        # Viabilidade
        lines.append("\n### 🎯 Consolidação\n\n")
        feasible = group_data.get("consolidation_feasible", False)
        lines.append(f"**Viável:** {'✅ SIM' if feasible else '⚠️ NÃO'}\n\n")

        if group_data.get("consolidation_reasons"):
            lines.append("**Razões:**\n")
            for reason in group_data["consolidation_reasons"]:
                lines.append(f"- {reason}\n")
            lines.append("\n")

        if group_data.get("consolidation_risks"):
            lines.append("**Riscos:**\n")
            for risk in group_data["consolidation_risks"]:
                lines.append(f"- ⚠️ {risk}\n")
            lines.append("\n")

        lines.append("---\n\n")

    return "".join(lines)


def generate_orphans_md(orphans: List[Dict]) -> str:
    """Gera relatório de módulos órfãos."""
    lines = [
        "# Módulos Órfãos (Não Importados)\n",
        f"**Data:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        f"**Total:** {len(orphans)}\n",
        "---\n\n",
    ]

    # Agrupar por tipo
    safe_to_remove = [o for o in orphans if o["likely_safe_to_remove"]]
    inits = [o for o in orphans if o["is_init"]]
    mains = [o for o in orphans if o["is_main"]]
    scripts = [o for o in orphans if o["is_script"]]

    if safe_to_remove:
        lines.append(f"## ⚠️ Candidatos à Remoção ({len(safe_to_remove)})\n\n")
        lines.append("| Módulo | Caminho |\n")
        lines.append("|--------|----------|\n")
        for orphan in safe_to_remove:
            lines.append(f"| `{orphan['module']}` | `{orphan['path']}` |\n")
        lines.append("\n")

    if inits:
        lines.append(f"## 📦 `__init__.py` Órfãos ({len(inits)})\n\n")
        lines.append(
            "Arquivos `__init__.py` que não são importados (normal se vazio).\n\n"
        )
        for orphan in inits:
            lines.append(f"- `{orphan['path']}`\n")
        lines.append("\n")

    if mains:
        lines.append(f"## 🚀 Entry Points ({len(mains)})\n\n")
        lines.append("Entry points não importados (esperado).\n\n")
        for orphan in mains:
            lines.append(f"- `{orphan['path']}`\n")
        lines.append("\n")

    if scripts:
        lines.append(f"## 🔧 Scripts ({len(scripts)})\n\n")
        lines.append("Scripts que não são importados (esperado).\n\n")
        for orphan in scripts:
            lines.append(f"- `{orphan['path']}`\n")
        lines.append("\n")

    return "".join(lines)


def generate_actions_md(duplicate_groups: Dict, orphans: List[Dict]) -> str:
    """Gera lista de ações propostas (dry-run)."""
    lines = [
        "# Ações Propostas (DRY-RUN)\n",
        f"**Data:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        "**ATENÇÃO:** Nenhuma ação será executada agora.\n",
        "---\n\n",
    ]

    action_count = 0

    for group_name, group_data in duplicate_groups.items():
        if not group_data.get("consolidation_feasible"):
            continue

        canonical = group_data.get("canonical_suggestion")
        if not canonical:
            continue

        lines.append(f"## 📦 Grupo: `{group_name}`\n\n")

        # Ação: consolidar
        non_canonical = [
            f for f in group_data["files"] if f["path"] != canonical["path"]
        ]

        for file_data in non_canonical:
            action_count += 1
            lines.append(
                f"### Ação {action_count}: Consolidar `{file_data['path']}`\n\n"
            )
            lines.append(f"**De:** `{file_data['path']}`\n")
            lines.append(f"**Para:** `{canonical['path']}`\n\n")

            if file_data["importers"]:
                lines.append(
                    f"**Importers a atualizar ({len(file_data['importers'])}):**\n"
                )
                for importer in file_data["importers"][:10]:
                    lines.append(f"- `{importer}`\n")
                if len(file_data["importers"]) > 10:
                    lines.append(f"- ... e mais {len(file_data['importers']) - 10}\n")
                lines.append("\n")

            lines.append("**Passos:**\n")
            lines.append("1. Revisar código de ambos os arquivos\n")
            lines.append(f"2. Mesclar funcionalidade em `{canonical['path']}`\n")
            lines.append(
                f"3. Reescrever imports nos {len(file_data['importers'])} importers\n"
            )
            lines.append(f"4. Criar stub de compatibilidade em `{file_data['path']}`\n")
            lines.append("5. Testar tudo\n")
            lines.append(
                f"6. Remover `{file_data['path']}` (após período de deprecação)\n\n"
            )

        lines.append("---\n\n")

    # Órfãos
    safe_orphans = [o for o in orphans if o["likely_safe_to_remove"]]
    if safe_orphans:
        lines.append("## 🗑️ Remover Órfãos\n\n")
        for orphan in safe_orphans:
            action_count += 1
            lines.append(f"### Ação {action_count}: Remover `{orphan['path']}`\n\n")
            lines.append("**Razão:** Módulo não é importado por ninguém\n\n")
            lines.append("**Passos:**\n")
            lines.append(
                "1. Verificar se não é usado via `importlib` ou `__import__`\n"
            )
            lines.append("2. Mover para `ajuda/_quarentena/`\n")
            lines.append("3. Testar tudo\n")
            lines.append("4. Remover após confirmação\n\n")

    lines.append(f"\n**Total de ações:** {action_count}\n")

    return "".join(lines)


def generate_risks_md(duplicate_groups: Dict) -> str:
    """Gera análise de riscos."""
    lines = [
        "# Análise de Riscos\n",
        f"**Data:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        "---\n\n",
    ]

    all_risks = []
    for group_name, group_data in duplicate_groups.items():
        if group_data.get("consolidation_risks"):
            all_risks.append(
                {
                    "group": group_name,
                    "risks": group_data["consolidation_risks"],
                }
            )

    if all_risks:
        lines.append("## ⚠️ Riscos Identificados\n\n")
        for item in all_risks:
            lines.append(f"### Grupo: `{item['group']}`\n\n")
            for risk in item["risks"]:
                lines.append(f"- {risk}\n")
            lines.append("\n")
    else:
        lines.append("✅ Nenhum risco crítico identificado.\n")

    lines.append("\n## 🛡️ Recomendações Gerais\n\n")
    lines.append("1. **Backup:** Fazer commit antes de qualquer mudança\n")
    lines.append("2. **Testes:** Executar smoke test após cada consolidação\n")
    lines.append("3. **Stubs:** Manter stubs de compatibilidade por 1-2 releases\n")
    lines.append("4. **Gradual:** Consolidar um grupo por vez\n")
    lines.append("5. **Revisão:** Code review obrigatório\n")

    return "".join(lines)


def generate_how_to_apply_md(duplicate_groups: Dict, orphans: List[Dict]) -> str:
    """Gera instruções de como aplicar."""
    lines = [
        "# Como Aplicar as Consolidações\n",
        f"**Data:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        "---\n\n",
        "## 📋 Pré-requisitos\n\n",
        "```powershell\n",
        "# 1. Fazer backup/commit\n",
        "git add .\n",
        'git commit -m "backup antes de consolidação"\n\n',
        "# 2. Instalar ferramentas\n",
        "python -m pip install libcst rapidfuzz\n",
        "```\n\n",
        "## 🚀 PROMPT 2 - Executar Consolidação\n\n",
        "```\n",
        "Execute as consolidações propostas em `ajuda/dup-consolidacao/ACTIONS_DRY_RUN.md`.\n\n",
        "Para cada grupo marcado como viável:\n",
        "1. Revise manualmente o código canônico e alternativas\n",
        "2. Mescle funcionalidades se necessário\n",
        "3. Reescreva imports usando LibCST\n",
        "4. Crie stubs de compatibilidade\n",
        "5. Execute smoke test\n",
        "6. Documente mudanças\n\n",
        "Grupos a consolidar:\n",
    ]

    feasible_groups = [
        (name, data)
        for name, data in duplicate_groups.items()
        if data.get("consolidation_feasible")
    ]

    if feasible_groups:
        for group_name, group_data in feasible_groups:
            canonical = group_data.get("canonical_suggestion", {})
            lines.append(f"- {group_name} → {canonical.get('path', 'N/A')}\n")
    else:
        lines.append("- (Nenhum grupo viável para consolidação automática)\n")

    lines.append("```\n\n")

    lines.append("## ⚠️ Atenção\n\n")
    lines.append("- Este é um processo **semi-automático**\n")
    lines.append("- Sempre revise o código antes de mesclar\n")
    lines.append("- Execute testes após cada mudança\n")
    lines.append("- Mantenha stubs por pelo menos 1 release\n")

    return "".join(lines)


# ============================================================================
# MAIN
# ============================================================================


def main():
    """Execução principal."""
    print("=" * 70)
    print("🔍 AUDITORIA & PROPOSTA DE CONSOLIDAÇÃO (DRY-RUN)")
    print("=" * 70)
    print(f"\n📁 Projeto: {ROOT}")
    print(f"📂 Output: {OUTPUT_DIR}\n")

    # 1. Encontrar arquivos
    print("📂 Buscando arquivos Python...")
    files = find_all_python_files()
    print(f"   ✓ {len(files)} arquivos encontrados\n")

    # 2. Construir grafo de imports
    graph = ImportGraph()
    graph.build(files)

    # 3. Encontrar nomes similares
    similar_groups = find_similar_names(files, threshold=FUZZY_NAME_THRESHOLD)

    # 4. Analisar grupos em profundidade
    duplicate_groups = analyze_duplicate_groups(similar_groups, graph)

    # 5. Encontrar órfãos
    orphans = find_orphans(graph)

    # 6. Gerar relatórios
    generate_reports(duplicate_groups, graph, orphans)

    # Sumário
    print("\n" + "=" * 70)
    print("📊 SUMÁRIO")
    print("=" * 70)
    print(f"Arquivos analisados: {len(files)}")
    print(f"Grupos similares: {len(duplicate_groups)}")
    print(
        f"Grupos viáveis para consolidação: {sum(1 for g in duplicate_groups.values() if g.get('consolidation_feasible'))}"
    )
    print(f"Módulos órfãos: {len(orphans)}")
    print(f"Órfãos removíveis: {sum(1 for o in orphans if o['likely_safe_to_remove'])}")
    print(f"\n📁 Relatórios salvos em: {OUTPUT_DIR}")
    print("\n✅ Auditoria concluída! Revise os relatórios antes de aplicar.")


if __name__ == "__main__":
    main()
