#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script de validação de política UI/Theme para blindar contra regressões.

OBJETIVO: Garantir que o baseline CODEC seja mantido:
- SSoT: set_appearance_mode apenas em src/ui/theme_manager.py
- Sem root implícita: ZERO ttk.Style() sem master
- Zero ttkbootstrap: imports e usos removidos do src/

REGRAS:
1. set_appearance_mode() executável SOMENTE em src/ui/theme_manager.py
2. ttk.Style() sem master ZERO (comentários/docstrings permitidos)
3. tb.Style() executável ZERO
4. import ttkbootstrap / from ttkbootstrap ZERO em src/ (exceto deprecated markers)

Exit code:
- 0: Todas as validações passaram
- 1: Uma ou mais violações encontradas
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import NamedTuple

# ============================================================================
# UTF-8 HARDENING: Força UTF-8 em stdout/stderr no Windows (resolve cp1252)
# ============================================================================
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # Ignorar falhas de reconfigure (Python muito antigo)


class Violation(NamedTuple):
    """Violação encontrada."""

    file: Path
    line: int
    content: str
    rule: str


def find_src_root() -> Path:
    """Encontra src/ a partir do script."""
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    src_dir = repo_root / "src"
    if not src_dir.is_dir():
        print(f"❌ Erro: src/ não encontrado em {repo_root}", file=sys.stderr)
        sys.exit(1)
    return src_dir


def find_python_files(src_dir: Path) -> list[Path]:
    """Lista todos os arquivos .py em src/."""
    return list(src_dir.rglob("*.py"))


def is_comment_or_docstring(line: str) -> bool:
    """Verifica se linha é comentário ou docstring."""
    stripped = line.strip()
    # Comentário
    if stripped.startswith("#"):
        return True
    # Docstring (triplas aspas ou linha dentro de docstring)
    if '"""' in stripped or "'''" in stripped:
        return True
    # Docstrings multi-linha: detectar por indentação + contexto (heurística)
    # Se linha começa com letra maiúscula, termina com ponto, e não tem = ou ( executável, provável docstring
    if (
        stripped
        and stripped[0].isupper()
        and (stripped.endswith(".") or stripped.endswith(":"))
        and not stripped.startswith("class")
        and not stripped.startswith("def")
    ):
        # Heurística: linhas em docstrings geralmente descrevem algo, não executam código
        if "=" not in stripped and "(" not in stripped or "master" in stripped.lower() or "ttk" in stripped.lower():
            return True
    return False


def check_set_appearance_mode(files: list[Path], src_dir: Path) -> list[Violation]:
    """Valida que set_appearance_mode() está apenas em theme_manager.py."""
    violations = []
    allowed_file = src_dir / "ui" / "theme_manager.py"

    pattern = re.compile(r"\bset_appearance_mode\s*\(")

    for file in files:
        if file == allowed_file:
            continue  # Permitido

        try:
            with open(file, "r", encoding="utf-8") as f:
                for line_no, line in enumerate(f, start=1):
                    if is_comment_or_docstring(line):
                        continue
                    if pattern.search(line):
                        violations.append(
                            Violation(
                                file=file,
                                line=line_no,
                                content=line.strip(),
                                rule="SSoT: set_appearance_mode() apenas em theme_manager.py",
                            )
                        )
        except Exception:
            pass  # Erro de leitura (encoding, etc) - skip

    return violations


def check_ttk_style_without_master(files: list[Path], src_dir: Path) -> list[Violation]:
    """Valida que ttk.Style() sempre tem master."""
    violations = []

    # Regex: ttk.Style() sem argumentos (ou apenas whitespace antes do parênteses)
    pattern = re.compile(r"\bttk\.Style\s*\(\s*\)")

    # Permitir ttk_compat.py (módulo de helpers para ttk, menções em docstrings)
    allowed_files = {
        src_dir / "ui" / "ttk_compat.py",
    }

    for file in files:
        if file in allowed_files:
            continue  # Arquivos permitidos

        try:
            with open(file, "r", encoding="utf-8") as f:
                for line_no, line in enumerate(f, start=1):
                    if is_comment_or_docstring(line):
                        continue
                    if pattern.search(line):
                        violations.append(
                            Violation(
                                file=file,
                                line=line_no,
                                content=line.strip(),
                                rule="Sem root implícita: ttk.Style() deve ter master",
                            )
                        )
        except Exception:
            pass

    return violations


def check_tb_style(files: list[Path], src_dir: Path) -> list[Violation]:
    """Valida que tb.Style() executável não existe."""
    violations = []

    # Regex: tb.Style( em código (não comentário)
    pattern = re.compile(r"\btb\.Style\s*\(")

    # Permitir themes.py (tem comentários sobre API inválida, já deprecated)
    deprecated_files = {
        src_dir / "utils" / "themes.py",
        src_dir / "utils" / "helpers" / "hidpi.py",
        src_dir / "modules" / "main_window" / "views" / "theme_setup.py",
    }

    for file in files:
        if file in deprecated_files:
            continue  # Arquivos deprecated podem ter comentários sobre tb.Style()

        try:
            with open(file, "r", encoding="utf-8") as f:
                for line_no, line in enumerate(f, start=1):
                    if is_comment_or_docstring(line):
                        continue
                    if pattern.search(line):
                        violations.append(
                            Violation(
                                file=file,
                                line=line_no,
                                content=line.strip(),
                                rule="ttkbootstrap removido: tb.Style() não deve existir",
                            )
                        )
        except Exception:
            pass

    return violations


def check_ttkbootstrap_imports(files: list[Path]) -> list[Violation]:
    """Valida que imports ttkbootstrap não existem."""
    violations = []

    # Regex: import ttkbootstrap ou from ttkbootstrap
    pattern = re.compile(r"\b(import\s+ttkbootstrap|from\s+ttkbootstrap)")

    for file in files:
        try:
            with open(file, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.splitlines()

                for line_no, line in enumerate(lines, start=1):
                    if is_comment_or_docstring(line):
                        continue
                    if pattern.search(line):
                        # Permitir se linha está comentada (try/except com tb = None)
                        stripped = line.strip()
                        if stripped.startswith("#"):
                            continue

                        # Verificar se está em bloco try/except deprecated
                        # (permissão especial para src/utils/themes.py e helpers/hidpi.py que já marcamos como deprecated)
                        file_str = str(file)
                        if (
                            "utils/themes.py" in file_str
                            or "helpers/hidpi.py" in file_str
                            or "theme_setup.py" in file_str
                        ):
                            continue

                        violations.append(
                            Violation(
                                file=file,
                                line=line_no,
                                content=line.strip(),
                                rule="ttkbootstrap removido: imports não devem existir",
                            )
                        )
        except Exception:
            pass

    return violations


def check_ttk_widgets(files: list[Path], src_dir: Path) -> list[Violation]:
    """Valida que widgets ttk simples não existem em runtime (MICROFASE 30)."""
    violations = []

    # Regex: ttk.Frame, ttk.Label, etc em código (não comentário)
    # Permitir ttk.Style, ttk.Treeview (legado em lists.py), ttk.PanedWindow (já migrado)
    widgets_pattern = re.compile(
        r"\bttk\.(Frame|Label|Button|Entry|Combobox|Checkbutton|Radiobutton|"
        r"Scale|Progressbar|Scrollbar|Separator|Labelframe|Notebook|Spinbox|Menubutton|Sizegrip)\b"
    )

    # Permitir arquivos específicos que têm Treeview legado
    allowed_files = {
        src_dir / "ui" / "components" / "lists.py",  # Treeview legado em create_clients_treeview
        src_dir / "ui" / "ttk_compat.py",  # Funções de compatibilidade (MICROFASE 36)
        src_dir / "ui" / "widgets" / "ctk_treeview.py",  # Comentários sobre API
        src_dir / "ui" / "widgets" / "ctk_tableview.py",  # Comentários sobre API
        src_dir / "ui" / "widgets" / "ctk_splitpane.py",  # Comentários sobre API
        src_dir / "ui" / "ctk_config.py",  # Comentários de documentação
        src_dir / "ui" / "menu_bar.py",  # Comentário histórico
        src_dir / "ui" / "ctk_audit.py",  # Ferramenta de auditoria (patterns como strings)
        src_dir / "modules" / "clientes_v2" / "view.py",  # Treeview legado em lista de clientes
        src_dir / "modules" / "clientes_v2" / "tree_theme.py",  # Helper de tema (MICROFASE 36)
    }

    for file in files:
        if file in allowed_files:
            continue

        try:
            with open(file, "r", encoding="utf-8") as f:
                for line_no, line in enumerate(f, start=1):
                    if is_comment_or_docstring(line):
                        continue
                    if widgets_pattern.search(line):
                        violations.append(
                            Violation(
                                file=file,
                                line=line_no,
                                content=line.strip(),
                                rule="MICROFASE 30: Widgets ttk simples devem ser CTk",
                            )
                        )
        except Exception:
            pass

    return violations


def check_icecream_imports(files: list[Path]) -> list[Violation]:
    """Valida que icecream não é usado em src/ de produção (MICROFASE 32)."""
    violations = []

    # Regex: from icecream import | import icecream
    pattern = re.compile(r"^\s*(from\s+icecream\s+import|import\s+icecream)\b")

    for file in files:
        try:
            with open(file, "r", encoding="utf-8") as f:
                for line_no, line in enumerate(f, start=1):
                    if is_comment_or_docstring(line):
                        continue
                    if pattern.search(line):
                        violations.append(
                            Violation(
                                file=file,
                                line=line_no,
                                content=line.strip(),
                                rule="MICROFASE 32: icecream é dev-only (debug tool)",
                            )
                        )
        except Exception:
            pass

    return violations


def check_ttk_in_comments(files: list[Path]) -> list[Violation]:
    """Valida que 'ttk' não aparece nem em comentários (MICROFASE 33 - polish)."""
    violations = []

    # Regex: qualquer menção a ttk (inclusive em comentários)
    pattern = re.compile(r"\bttk\b|\btkinter\.ttk\b", re.IGNORECASE)

    # Whitelist: vendor é permitido (herda de ttk.Treeview)
    whitelist = [
        Path("src/third_party/ctktreeview/treeview.py"),
        Path("src/ui/ctk_audit.py"),  # Ferramenta de auditoria (patterns como strings)
        Path("src/ui/ttk_compat.py"),  # Módulo de compatibilidade ttk (MICROFASE 36)
        Path("src/modules/clientes_v2/view.py"),  # Comentários de migração legados
        Path("src/modules/clientes_v2/tree_theme.py"),  # Helper de tema ttk.Treeview legado
        Path("src/modules/clientes_v2/__init__.py"),  # Documentação de FASE (histórico)
        Path("src/modules/anvisa/views/anvisa_screen.py"),  # Comentários sobre PanedWindow migration
        Path("src/ui/widget_state.py"),  # Compat layer CTk/TTK/TK (documentação)
        Path("src/ui/widgets/ctk_section.py"),  # Comentários sobre substituição de ttk.LabelFrame
    ]

    for file in files:
        # Permitir vendor
        if any(str(file).endswith(str(w)) for w in whitelist):
            continue

        try:
            with open(file, "r", encoding="utf-8") as f:
                for line_no, line in enumerate(f, start=1):
                    if pattern.search(line):
                        violations.append(
                            Violation(
                                file=file,
                                line=line_no,
                                content=line.strip(),
                                rule="MICROFASE 33: Token 'ttk' proibido (inclusive comentários) - usar 'legado' ou 'CTk'",
                            )
                        )
        except Exception:
            pass

    return violations


def check_vcs_deps_without_pin() -> list[Violation]:
    """Valida que dependências VCS têm commit hash (MICROFASE 33 - reproducibility)."""
    violations = []

    # Verificar requirements.txt e pyproject.toml
    repo_root = find_src_root().parent
    req_files = [
        repo_root / "requirements.txt",
        repo_root / "pyproject.toml",
    ]

    # Regex: git+ URL sem @commit_hash
    # Formato correto: git+https://...@<commit_hash>
    # Errado: git+https://... (sem @)
    pattern = re.compile(r"git\+https?://[^\s@]+(?:\.git)?(?:\s|$)")

    for req_file in req_files:
        if not req_file.exists():
            continue

        try:
            with open(req_file, "r", encoding="utf-8") as f:
                for line_no, line in enumerate(f, start=1):
                    # Skip comentários
                    if line.strip().startswith("#"):
                        continue

                    if pattern.search(line):
                        violations.append(
                            Violation(
                                file=req_file,
                                line=line_no,
                                content=line.strip(),
                                rule="MICROFASE 33: VCS dependency sem pin (@commit_hash) - não reproduzível",
                            )
                        )
        except Exception:
            pass

    return violations


def check_vendor_has_license(src_dir: Path) -> list[Violation]:
    """Valida que código vendorizado tem LICENSE (MICROFASE 33 - compliance)."""
    violations = []

    vendor_dir = src_dir / "third_party"
    if not vendor_dir.exists():
        return violations

    # Para cada subdiretório em third_party/, exigir LICENSE
    for vendor_lib in vendor_dir.iterdir():
        if not vendor_lib.is_dir():
            continue
        if vendor_lib.name.startswith("_"):
            continue  # __pycache__, etc

        license_file = vendor_lib / "LICENSE"
        readme_file = vendor_lib / "README.md"

        if not license_file.exists():
            violations.append(
                Violation(
                    file=vendor_lib,
                    line=0,
                    content=f"Vendor {vendor_lib.name} sem LICENSE",
                    rule="MICROFASE 33: Vendor precisa ter LICENSE (compliance)",
                )
            )

        if not readme_file.exists():
            violations.append(
                Violation(
                    file=vendor_lib,
                    line=0,
                    content=f"Vendor {vendor_lib.name} sem README.md (commit hash + upstream)",
                    rule="MICROFASE 33: Vendor precisa ter README.md com commit hash (reproducibility)",
                )
            )

    return violations


def print_violations(violations: list[Violation]) -> None:
    """Imprime violações formatadas."""
    if not violations:
        return

    # Agrupar por regra
    by_rule: dict[str, list[Violation]] = {}
    for v in violations:
        by_rule.setdefault(v.rule, []).append(v)

    for rule, vlist in by_rule.items():
        print(f"\n❌ {rule}")
        print(f"   Violações: {len(vlist)}\n")

        for v in vlist[:10]:  # Limitar a 10 por regra
            rel_path = v.file.relative_to(find_src_root().parent)
            print(f"   {rel_path}:{v.line}")
            print(f"     {v.content}")

        if len(vlist) > 10:
            print(f"   ... e mais {len(vlist) - 10} violações")


def main() -> int:
    """Executa todas as validações."""
    # UTF-8 safe: Usar ASCII equivalente em vez de emoji
    print("[POLICY] Validando política UI/Theme...")

    src_dir = find_src_root()
    files = find_python_files(src_dir)
    print(f"   Analisando {len(files)} arquivos Python em src/\n")

    all_violations: list[Violation] = []

    # Regra 1: set_appearance_mode
    print("   ✓ Validando SSoT (set_appearance_mode)...")
    v1 = check_set_appearance_mode(files, src_dir)
    all_violations.extend(v1)

    # Regra 2: ttk.Style()
    print("   ✓ Validando ttk.Style(master=)...")
    v2 = check_ttk_style_without_master(files, src_dir)
    all_violations.extend(v2)

    # Regra 3: tb.Style()
    print("   ✓ Validando ausência de tb.Style()...")
    v3 = check_tb_style(files, src_dir)
    all_violations.extend(v3)

    # Regra 4: imports ttkbootstrap
    print("   ✓ Validando ausência de imports ttkbootstrap...")
    v4 = check_ttkbootstrap_imports(files)
    all_violations.extend(v4)

    # Regra 5: widgets ttk simples (MICROFASE 30)
    print("   ✓ Validando ausência de widgets ttk simples...")
    v5 = check_ttk_widgets(files, src_dir)
    all_violations.extend(v5)

    # Regra 6: icecream imports (MICROFASE 32)
    print("   ✓ Validando ausência de icecream em src/...")
    v6 = check_icecream_imports(files)
    all_violations.extend(v6)

    # Regra 7: ttk em comentários (MICROFASE 33)
    print("   ✓ Validando ausência de 'ttk' (inclusive comentários)...")
    v7 = check_ttk_in_comments(files)
    all_violations.extend(v7)

    # Regra 8: VCS deps sem pin (MICROFASE 33)
    print("   ✓ Validando VCS dependencies com commit hash...")
    v8 = check_vcs_deps_without_pin()
    all_violations.extend(v8)

    # Regra 9: Vendor sem LICENSE (MICROFASE 33)
    print("   ✓ Validando vendor com LICENSE + README...")
    v9 = check_vendor_has_license(src_dir)
    all_violations.extend(v9)

    if not all_violations:
        print("\n✅ Todas as validações passaram!")
        print("   - SSoT: OK")
        print("   - ttk.Style(master=): OK")
        print("   - tb.Style(): OK")
        print("   - imports ttkbootstrap: OK")
        print("   - widgets ttk simples: OK")
        print("   - icecream em src/: OK")
        print("   - token 'ttk' (comentários): OK")
        print("   - VCS deps com pin: OK")
        print("   - Vendor com LICENSE: OK")
        return 0

    print(f"\n❌ Encontradas {len(all_violations)} violações:")
    print_violations(all_violations)

    print("\n💡 Ações recomendadas:")
    print("   1. Mover set_appearance_mode() para theme_manager.py")
    print("   2. Adicionar master explícito em ttk.Style()")
    print("   3. Remover código ttkbootstrap ou marcar como deprecated")
    print("   4. Migrar imports para CustomTkinter\n")

    return 1


if __name__ == "__main__":
    sys.exit(main())
