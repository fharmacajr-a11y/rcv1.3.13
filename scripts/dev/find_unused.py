#!/usr/bin/env python3
"""
find_unused.py (Enhanced)
-------------------------
Advanced scanner for finding unused Python symbols (functions/classes) and modules.

Features:
- Symbol-level reference counting (not just module-level)
- Package-aware imports (__init__.py reexports)
- Tkinter handler detection (command=, .bind(...))
- Word boundary matching to avoid false positives

Usage:
    python scripts/dev/find_unused.py [--verbose] [--symbols-only]

Output:
    docs/UNUSED-REPORT.md

Arguments:
    --verbose: Show progress during scan
    --symbols-only: Only report unused symbols (skip module-level analysis)
"""
from __future__ import annotations

import argparse
import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Ignore these patterns when scanning for references
IGNORE_PATTERNS = {
    "__pycache__",
    ".git",
    ".venv",
    "build",
    "dist",
    ".pytest_cache",
    ".mypy_cache",
    "tests",  # Skip tests in reference counting
}

# Files that are entry points or configuration (never report as unused)
SAFE_FILES = {
    "app_gui.py",
    "app_core.py",
    "__init__.py",
    "setup.py",
    "pyproject.toml",
    "requirements.txt",
}


@dataclass
class SymbolInfo:
    """Represents a public symbol (function/class) in the codebase."""

    name: str
    type: str  # "function" | "class"
    file: str
    line: int
    references: int = 0
    is_tk_handler: bool = False
    exported_by_init: bool = False


def is_ignored(path: Path) -> bool:
    """Check if path should be ignored during scanning."""
    return any(part in IGNORE_PATTERNS for part in path.parts)


def find_python_files(root: Path) -> List[Path]:
    """Find all Python files in workspace, excluding ignored patterns."""
    return [
        p.relative_to(root)
        for p in root.rglob("*.py")
        if not is_ignored(p) and p.is_file()
    ]


def extract_public_symbols(file_path: Path, source: str) -> List[SymbolInfo]:
    """Extract all public symbols (functions/classes) from a Python file."""
    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return []

    symbols = []

    for node in ast.walk(tree):
        # Only extract top-level definitions
        if not isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            continue

        # Skip private symbols
        if node.name.startswith("_"):
            continue

        # Get line number
        line = getattr(node, "lineno", 0)

        # Detect Tkinter handler
        is_handler = False
        if isinstance(node, ast.FunctionDef):
            # Pattern 1: command=func_name
            if re.search(rf"\bcommand\s*=\s*{re.escape(node.name)}\b", source):
                is_handler = True
            # Pattern 2: .bind("<event>", func_name)
            elif re.search(rf"\.bind\([^,]+,\s*{re.escape(node.name)}\)", source):
                is_handler = True

        symbol = SymbolInfo(
            name=node.name,
            type="function" if isinstance(node, ast.FunctionDef) else "class",
            file=str(file_path),
            line=line,
            is_tk_handler=is_handler,
        )

        symbols.append(symbol)

    return symbols


def get_exported_symbols(init_file: Path) -> Set[str]:
    """
    Extract symbols exported by __init__.py via __all__ or explicit imports.
    """
    if not init_file.exists():
        return set()

    try:
        source = init_file.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source)
    except Exception:
        return set()

    exported = set()

    for node in ast.walk(tree):
        # __all__ = ["symbol1", "symbol2"]
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Constant) and isinstance(
                                elt.value, str
                            ):
                                exported.add(elt.value)

        # from .module import symbol
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.names:
                for alias in node.names:
                    if alias.name != "*":
                        exported.add(alias.name)

    return exported


def count_symbol_references(
    root: Path, symbol_name: str, file_path: Path, all_files: List[Path]
) -> int:
    """
    Count references to a specific symbol across the codebase.
    Uses word boundaries to avoid false positives.
    """
    count = 0

    # Pattern with word boundaries
    pattern = re.compile(rf"\b{re.escape(symbol_name)}\b")

    for py_file in all_files:
        # Skip the file where symbol is defined
        if py_file == file_path:
            continue

        try:
            content = (root / py_file).read_text(encoding="utf-8", errors="ignore")
            matches = pattern.findall(content)
            count += len(matches)
        except Exception:
            continue

    return count


def count_module_references(
    root: Path, module_path: Path, module_name: str, all_files: List[Path]
) -> int:
    """
    Count how many times this module is imported across the workspace.

    Searches for patterns like:
    - from gui.menu_bar import AppMenuBar
    - import gui.menu_bar
    - from gui import menu_bar (package import)
    """
    count = 0

    # Build search patterns
    module_parts = module_name.split(".")
    patterns = [
        rf"\bfrom\s+{re.escape(module_name)}\s+import\b",  # from gui.menu_bar import X
        rf"\bimport\s+{re.escape(module_name)}\b",  # import gui.menu_bar
    ]

    # Also search for partial imports (e.g., from gui import menu_bar)
    if len(module_parts) > 1:
        parent = ".".join(module_parts[:-1])
        child = module_parts[-1]
        patterns.append(
            rf"\bfrom\s+{re.escape(parent)}\s+import\s+.*\b{re.escape(child)}\b"
        )

    compiled_patterns = [re.compile(p) for p in patterns]

    # Search all Python files
    for py_file in all_files:
        if py_file == module_path:
            continue

        try:
            content = (root / py_file).read_text(encoding="utf-8", errors="ignore")
            for pattern in compiled_patterns:
                matches = pattern.findall(content)
                count += len(matches)
        except Exception:
            continue

    return count


def get_module_name(file_path: Path) -> str:
    """Convert file path to Python module name (e.g., gui/menu_bar.py -> gui.menu_bar)."""
    if file_path.name == "__init__.py":
        # For __init__.py, use the parent directory as module name
        return ".".join(file_path.parent.parts)
    else:
        # Remove .py extension and convert path separators to dots
        return ".".join(file_path.with_suffix("").parts)


def classify_module(module_path: Path, ref_count: int) -> Tuple[str, str, str]:
    """
    Classify module into type, status, and recommendation.

    Returns:
        (module_type, status, recommendation)
    """
    name = module_path.name

    # Determine module type
    if name == "__init__.py":
        module_type = "package_init"
    elif name.endswith("_test.py") or name.startswith("test_"):
        module_type = "test"
    elif "script" in str(module_path) or "dev" in str(module_path):
        module_type = "script"
    elif any(part in str(module_path) for part in ["core", "application", "adapters"]):
        module_type = "domain"
    elif "gui" in str(module_path) or "ui" in str(module_path):
        module_type = "ui"
    else:
        module_type = "utility"

    # Determine status and recommendation
    if ref_count == 0:
        status = "ORPHAN"
        if module_type in ("script", "test"):
            recommendation = "REVIEW (may be CLI tool)"
        else:
            recommendation = "REMOVE or ARCHIVE"
    elif ref_count <= 2:
        status = "LOW_USAGE"
        recommendation = "REVIEW for consolidation"
    else:
        status = "ACTIVE"
        recommendation = "KEEP"

    return module_type, status, recommendation


def generate_report(
    symbols: List[SymbolInfo],
    module_results: List[Tuple[Path, str, int, str, str, str]],
    output_path: Path,
    verbose: bool = False,
) -> None:
    """Generate Markdown report."""
    lines = [
        "# Unused Code Report",
        "",
        "**Generated by:** `scripts/dev/find_unused.py`  ",
        "**How to run:** `python scripts/dev/find_unused.py [--verbose] [--symbols-only]`",
        "",
        "---",
        "",
    ]

    # Unused symbols section
    unused_symbols = [s for s in symbols if s.references == 0 and not s.is_tk_handler]

    lines.extend(
        [
            "## 🔴 Unused Symbols (0 references)",
            "",
            f"**Total:** {len(unused_symbols)} symbols",
            "",
        ]
    )

    if unused_symbols:
        lines.append("| Symbol | Type | File | Line | Notes |")
        lines.append("|--------|------|------|------|-------|")

        for sym in sorted(unused_symbols, key=lambda s: (s.file, s.line)):
            notes = []
            if sym.exported_by_init:
                notes.append("Exported by __init__.py")
            notes_str = ", ".join(notes) if notes else "—"

            lines.append(
                f"| `{sym.name}` | {sym.type} | `{sym.file}` | {sym.line} | {notes_str} |"
            )

        lines.append("")
    else:
        lines.append("✅ No unused symbols found.")
        lines.append("")

    # Low-usage symbols
    low_usage = [s for s in symbols if 1 <= s.references <= 2 and not s.is_tk_handler]

    lines.extend(
        [
            "---",
            "",
            "## 🟡 Low-Usage Symbols (1-2 references)",
            "",
            f"**Total:** {len(low_usage)} symbols",
            "",
        ]
    )

    if low_usage and verbose:
        lines.append("| Symbol | Type | Refs | File | Line |")
        lines.append("|--------|------|------|------|------|")

        for sym in sorted(low_usage, key=lambda s: s.references)[:30]:  # Top 30
            lines.append(
                f"| `{sym.name}` | {sym.type} | {sym.references} | `{sym.file}` | {sym.line} |"
            )

        if len(low_usage) > 30:
            lines.append("")
            lines.append(
                f"*... and {len(low_usage) - 30} more (run with --verbose to see all)*"
            )

        lines.append("")
    elif low_usage:
        lines.append("*Run with --verbose to see details*")
        lines.append("")
    else:
        lines.append("✅ No low-usage symbols found.")
        lines.append("")

    # Module-level analysis
    orphan_modules = [
        (p, n, r, t, s, rec) for p, n, r, t, s, rec in module_results if s == "ORPHAN"
    ]

    lines.extend(
        [
            "---",
            "",
            "## 📦 Module-Level Analysis",
            "",
            f"**Orphan modules:** {len(orphan_modules)}",
            "",
        ]
    )

    if orphan_modules:
        lines.append("| Module Path | Module Name | Type | Recommendation |")
        lines.append("|-------------|-------------|------|----------------|")

        for (
            module_path,
            module_name,
            _,
            module_type,
            _,
            recommendation,
        ) in orphan_modules:
            lines.append(
                f"| `{module_path}` | `{module_name}` | {module_type} | {recommendation} |"
            )

        lines.append("")
    else:
        lines.append("✅ No orphan modules found.")
        lines.append("")

    # Summary
    tk_handlers = len([s for s in symbols if s.is_tk_handler])

    lines.extend(
        [
            "---",
            "",
            "## 📊 Summary",
            "",
            f"- **Unused symbols:** {len(unused_symbols)}",
            f"- **Low-usage symbols:** {len(low_usage)}",
            f"- **Orphan modules:** {len(orphan_modules)}",
            f"- **Tk handlers detected:** {tk_handlers} (excluded from unused count)",
            "",
            "**Recommendations:**",
            "1. Review unused symbols for removal (may be dead code)",
            "2. Check if low-usage symbols can be inlined or consolidated",
            "3. Verify orphan modules are not entry points or CLI tools",
            "4. Tk handlers may have 0 direct references (bound via command=/bind)",
            "",
        ]
    )

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"✅ Report generated: {output_path}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Find unused Python symbols and modules"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed output"
    )
    parser.add_argument(
        "--symbols-only",
        action="store_true",
        help="Only analyze symbols (skip module-level)",
    )
    args = parser.parse_args()

    root = Path.cwd()

    print("🔍 Scanning for Python files...")
    all_files = find_python_files(root)
    print(f"📁 Found {len(all_files)} Python files")

    print("\n🔬 Extracting symbols...")
    all_symbols: List[SymbolInfo] = []

    # Build map of package exports
    package_exports: Dict[str, Set[str]] = {}
    for file_path in all_files:
        if file_path.name == "__init__.py":
            parent = str(file_path.parent)
            package_exports[parent] = get_exported_symbols(root / file_path)

    # Extract symbols from each file
    for file_path in all_files:
        if file_path.name in SAFE_FILES:
            continue

        try:
            source = (root / file_path).read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        symbols = extract_public_symbols(file_path, source)

        # Check if exported by parent __init__.py
        parent = str(file_path.parent)
        if parent in package_exports:
            for sym in symbols:
                if sym.name in package_exports[parent]:
                    sym.exported_by_init = True

        all_symbols.extend(symbols)

    print(f"🔣 Extracted {len(all_symbols)} public symbols")

    print("\n📊 Counting symbol references...")
    for i, sym in enumerate(all_symbols):
        if args.verbose and (i + 1) % 50 == 0:
            print(f"  Processed {i + 1}/{len(all_symbols)} symbols...")

        # Count references to this symbol
        sym.references = count_symbol_references(
            root, sym.name, Path(sym.file), all_files
        )

    # Module-level analysis
    module_results = []
    if not args.symbols_only:
        print("\n📦 Analyzing modules...")
        candidates = [p for p in all_files if p.name not in SAFE_FILES]

        for module_path in candidates:
            module_name = get_module_name(module_path)
            ref_count = count_module_references(
                root, module_path, module_name, all_files
            )
            module_type, status, recommendation = classify_module(
                module_path, ref_count
            )

            module_results.append(
                (
                    module_path,
                    module_name,
                    ref_count,
                    module_type,
                    status,
                    recommendation,
                )
            )

    # Generate report
    output_path = root / "docs" / "UNUSED-REPORT.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    generate_report(all_symbols, module_results, output_path, args.verbose)

    # Print summary
    unused_count = len(
        [s for s in all_symbols if s.references == 0 and not s.is_tk_handler]
    )
    orphan_count = len([r for r in module_results if r[4] == "ORPHAN"])

    print("\n📊 Analysis complete!")
    print(f"   Unused symbols: {unused_count}")
    print(f"   Orphan modules: {orphan_count}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
