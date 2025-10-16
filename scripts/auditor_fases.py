# scripts/auditor_fases.py
import os
import re
import ast
import sys
from pathlib import Path

ROOT = Path(".").resolve()
SKIP_DIRS = {".git", ".venv", "venv", "build", "dist", "__pycache__"}

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def py_files():
    for path in ROOT.rglob("*.py"):
        if any(seg in SKIP_DIRS for seg in path.parts):
            continue
        yield path


def parse(path: Path):
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except Exception:
        return None


def has_def(module: ast.AST, name: str, kind="func"):
    if not module:
        return False
    for node in ast.walk(module):
        if kind == "func" and isinstance(node, ast.FunctionDef) and node.name == name:
            return True
        if kind == "class" and isinstance(node, ast.ClassDef) and node.name == name:
            return True
    return False


def count_defs(name: str, kind="func"):
    hits = []
    for file_path in py_files():
        module = parse(file_path)
        if has_def(module, name, kind):
            hits.append(file_path.as_posix().lower())
    return hits


def exports_in_file(rel: str, symbol: str) -> bool:
    path = ROOT / rel
    module = parse(path)
    if not module:
        return False

    def _in_list(node) -> bool:
        if isinstance(node, (ast.List, ast.Tuple)):
            for element in node.elts:
                if (
                    isinstance(element, ast.Constant)
                    and isinstance(element.value, str)
                    and element.value == symbol
                ):
                    return True
        return False

    for node in ast.walk(module):
        if isinstance(node, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets):
                if _in_list(node.value):
                    return True
        if isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == "__all__":
                if _in_list(node.value):
                    return True
    return False


def has_import_use(target_files, patterns):
    found = {}
    for rel in target_files:
        path = ROOT / rel
        found[rel] = False
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            if re.search(pattern, text):
                found[rel] = True
                break
    return found


report = {"phase1": {}, "phase2": {}, "phase3": {}, "phase4": {}, "extras": {}}

# --- Fase 1
report["phase1"]["file_resource_path"] = (ROOT / "utils/resource_path.py").exists()
report["phase1"]["file_hash_utils"] = (ROOT / "utils/hash_utils.py").exists()

text = (
    (ROOT / "utils/resource_path.py").read_text(encoding="utf-8", errors="ignore")
    if report["phase1"]["file_resource_path"]
    else ""
)
report["phase1"]["resource_path_body_ok"] = (
    ("sys._MEIPASS" in text or 'getattr(sys, "_MEIPASS"' in text)
    and "os.path.join" in text
)
report["phase1"]["resource_path__all"] = exports_in_file(
    "utils/resource_path.py", "resource_path"
)

text = (
    (ROOT / "utils/hash_utils.py").read_text(encoding="utf-8", errors="ignore")
    if report["phase1"]["file_hash_utils"]
    else ""
)
report["phase1"]["sha256_body_ok"] = (
    "sha256" in text and "iter(lambda:" in text and "8192" in text and ".hexdigest()" in text
)
report["phase1"]["sha256__all"] = exports_in_file(
    "utils/hash_utils.py", "sha256_file"
)

dup_rp = [
    f for f in count_defs("resource_path") if not f.endswith("utils/resource_path.py")
]
dup_sh = [
    f for f in count_defs("sha256_file") if not f.endswith("utils/hash_utils.py")
]
report["phase1"]["resource_path_duplicates"] = dup_rp
report["phase1"]["sha256_duplicates"] = dup_sh

consumers = [
    "app_gui.py",
    "core/services/upload_service.py",
    "core/services/supabase_uploader.py",
    "ui/login/login.py",
    "ui/forms/actions.py",
]
imp_rp = has_import_use(
    consumers,
    [
        r"from\s+utils\.resource_path\s+import\s+resource_path",
        r"def\s+_resource_path\(",
    ],
)
imp_sh = has_import_use(
    consumers,
    [
        r"from\s+utils\.hash_utils\s+import\s+sha256_file",
        r"def\s+_sha256\(",
    ],
)
report["phase1"]["imports_resource_path"] = imp_rp
report["phase1"]["imports_sha256"] = imp_sh

# --- Fase 2
report["phase2"]["validators_file"] = (ROOT / "utils/validators.py").exists()
report["phase2"]["only_digits_duplicates"] = [
    f for f in count_defs("only_digits") if not f.endswith("utils/validators.py")
]
okm_hits = count_defs("OkCancelMixin", kind="class")
report["phase2"]["okcancel_in_ui_utils"] = any(
    x.endswith("ui/utils.py") for x in okm_hits
)

# --- Fase 3
center_defs = count_defs("center_on_parent")
report["phase3"]["center_defined_in_ui_utils"] = any(
    x.endswith("ui/utils.py") for x in center_defs
)
users = ["ui/login/login.py", "ui/forms/actions.py", "ui/dialogs.py", "app_gui.py"]
imp_center = has_import_use(
    users,
    [
        r"from\s+ui\s+import\s+center_on_parent",
        r"from\s+ui\.utils\s+import\s+center_on_parent",
        r"center_on_parent\(",
    ],
)
report["phase3"]["center_imports_usage"] = imp_center

# --- Fase 4
report["phase4"]["ui_utils_all"] = exports_in_file(
    "ui/utils.py", "center_on_parent"
)
report["phase4"]["ui_dunder_init"] = (ROOT / "ui/__init__.py").exists()

# --- Smoke imports (sem executar GUI)
import_ok = {}
for mod in ["utils.resource_path", "utils.hash_utils", "utils.validators", "ui.utils"]:
    try:
        __import__(mod)
        import_ok[mod] = True
    except Exception:
        import_ok[mod] = False
report["extras"]["import_smoke"] = import_ok


def status(ok):
    return "✅" if ok else "❌"


lines = []
lines.append("# Relatório de Verificação — v1.0.14 (Fases 1–4)")
lines.append("")
lines.append("## Fase 1 — resource_path & sha256_file")
lines.append(
    f"- utils/resource_path.py: {status(report['phase1']['file_resource_path'])} | __all__: {status(report['phase1']['resource_path__all'])} | corpo: {status(report['phase1']['resource_path_body_ok'])}"
)
lines.append(
    f"- utils/hash_utils.py: {status(report['phase1']['file_hash_utils'])} | __all__: {status(report['phase1']['sha256__all'])} | corpo: {status(report['phase1']['sha256_body_ok'])}"
)
if report["phase1"]["resource_path_duplicates"]:
    lines.append(
        f"- Duplicações de `resource_path` fora de utils: {len(report['phase1']['resource_path_duplicates'])}"
    )
    for item in report["phase1"]["resource_path_duplicates"]:
        lines.append(f"  - {item}")
if report["phase1"]["sha256_duplicates"]:
    lines.append(
        f"- Duplicações de `sha256_file` fora de utils: {len(report['phase1']['sha256_duplicates'])}"
    )
    for item in report["phase1"]["sha256_duplicates"]:
        lines.append(f"  - {item}")
lines.append("- **Consumidores (imports/fallbacks):**")
for rel in consumers:
    rp = report["phase1"]["imports_resource_path"].get(rel, False)
    sh = report["phase1"]["imports_sha256"].get(rel, False)
    mark = status(rp or sh)
    lines.append(f"  - {rel}: resource_path {status(rp)} / sha256 {status(sh)} -> {mark}")

lines.append("\n## Fase 2 — validators & OkCancelMixin")
lines.append(f"- utils/validators.py: {status(report['phase2']['validators_file'])}")
lines.append(
    f"- `only_digits` duplicado(s) fora de utils: {len(report['phase2']['only_digits_duplicates'])}"
)
for item in report["phase2"]["only_digits_duplicates"]:
    lines.append(f"  - {item}")
lines.append(
    f"- OkCancelMixin em ui/utils.py: {status(report['phase2']['okcancel_in_ui_utils'])}"
)

lines.append("\n## Fase 3 — center_on_parent")
lines.append(
    f"- Definido em ui/utils.py: {status(report['phase3']['center_defined_in_ui_utils'])}"
)
lines.append("- Uso/imports:")
for rel, ok in report["phase3"]["center_imports_usage"].items():
    lines.append(f"  - {rel}: {status(ok)}")

lines.append("\n## Fase 4 — imports absolutos & __all__")
lines.append(
    f"- __all__ em ui/utils.py (expondo center_on_parent): {status(report['phase4']['ui_utils_all'])}"
)
lines.append(
    f"- ui/__init__.py presente (reexport possível): {status(report['phase4']['ui_dunder_init'])}"
)

lines.append("\n## Import smoke (sem executar GUI)")
for mod, ok in report["extras"]["import_smoke"].items():
    lines.append(f"- import {mod}: {status(ok)}")

output = "\n".join(lines)
(ROOT / "VARREDURA-RELATORIO.md").write_text(output, encoding="utf-8")
try:
    sys.stdout.buffer.write(output.encode("utf-8", errors="replace"))
    sys.stdout.buffer.write(b"\n")
except Exception:
    print(output.encode("utf-8", errors="replace").decode("utf-8", errors="replace"))
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
