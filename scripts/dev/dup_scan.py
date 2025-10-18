#!/usr/bin/env python3
"""
dup_scan.py
-----------
AST-based scanner for detecting functional duplicates in Python codebase.

Detects:
- Exact clones (identical normalized AST)
- High-similarity clones (Jaccard coefficient ≥ 0.85)
- Ignores reexports in __init__.py and shim modules
- Tkinter handler awareness (command=, .bind(...))

Usage:
    python scripts/dev/dup_scan.py

Output:
    - docs/DUPLICATES-REPORT.md (human-readable)
    - docs/DUPLICATES-REPORT.json (machine-readable)
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Patterns to ignore
IGNORE_DIRS = {
    ".venv",
    ".git",
    "__pycache__",
    "build",
    "dist",
    ".pytest_cache",
    "tests",
}
SHIM_PATTERNS = {
    r"from .* import \*",  # reexport all
    r"^__all__ = ",  # explicit __all__
}


@dataclass
class Symbol:
    """Represents a function or class in the codebase."""

    name: str
    type: str  # "function" | "class"
    file: str
    line: int
    ast_hash: str
    tokens: Set[str]
    is_shim: bool = False
    is_tk_handler: bool = False

    def to_dict(self) -> dict:
        d = asdict(self)
        d["tokens"] = sorted(self.tokens)  # JSON-serializable
        return d


def is_ignored(path: Path) -> bool:
    """Check if path should be ignored."""
    return any(part in IGNORE_DIRS for part in path.parts)


def normalize_ast(node: ast.AST) -> str:
    """
    Normalize AST by removing location info, docstrings, and comments.
    Returns a canonical string representation.
    """
    # Remove docstrings
    if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module)):
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ):
            node.body = node.body[1:]  # Skip docstring

    # Remove location metadata
    for child in ast.walk(node):
        for attr in ("lineno", "col_offset", "end_lineno", "end_col_offset"):
            if hasattr(child, attr):
                delattr(child, attr)

    # Dump as string and hash
    return ast.dump(node, annotate_fields=False)


def extract_tokens(node: ast.AST) -> Set[str]:
    """
    Extract meaningful tokens from AST (identifiers, literals, operators).
    Used for similarity comparison via Jaccard coefficient.
    """
    tokens = set()

    for child in ast.walk(node):
        # Names (variables, functions, classes)
        if isinstance(child, ast.Name):
            tokens.add(f"name:{child.id}")

        # Attributes (obj.attr)
        elif isinstance(child, ast.Attribute):
            tokens.add(f"attr:{child.attr}")

        # Function calls
        elif isinstance(child, ast.Call):
            if isinstance(child.func, ast.Name):
                tokens.add(f"call:{child.func.id}")
            elif isinstance(child.func, ast.Attribute):
                tokens.add(f"call:{child.func.attr}")

        # Constants (literals)
        elif isinstance(child, ast.Constant):
            # Skip large strings (likely docstrings)
            if isinstance(child.value, str) and len(child.value) > 50:
                continue
            tokens.add(f"const:{type(child.value).__name__}")

        # Operators
        elif isinstance(child, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            tokens.add(f"op:{type(child).__name__}")

    return tokens


def jaccard_similarity(tokens1: Set[str], tokens2: Set[str]) -> float:
    """Calculate Jaccard coefficient between two token sets."""
    if not tokens1 or not tokens2:
        return 0.0

    intersection = tokens1 & tokens2
    union = tokens1 | tokens2

    return len(intersection) / len(union) if union else 0.0


def is_shim_module(content: str) -> bool:
    """Detect if module is a shim (reexport-only)."""
    for pattern in SHIM_PATTERNS:
        if re.search(pattern, content, re.MULTILINE):
            return True
    return False


def is_tk_handler(func_node: ast.FunctionDef, source: str) -> bool:
    """
    Detect if function is a Tkinter event handler.
    Looks for usage in command= or .bind(...) calls.
    """
    func_name = func_node.name

    # Pattern 1: command=func_name
    if re.search(rf"\bcommand\s*=\s*{re.escape(func_name)}\b", source):
        return True

    # Pattern 2: .bind("<event>", func_name)
    if re.search(rf"\.bind\([^,]+,\s*{re.escape(func_name)}\)", source):
        return True

    return False


def analyze_file(file_path: Path) -> List[Symbol]:
    """Extract all public symbols (functions/classes) from a Python file."""
    try:
        source = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return []

    symbols = []
    is_shim = is_shim_module(source)

    for node in ast.walk(tree):
        # Only extract top-level functions and classes
        if not isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            continue

        # Skip private symbols (leading underscore)
        if node.name.startswith("_"):
            continue

        # Get line number
        line = getattr(node, "lineno", 0)

        # Normalize AST and compute hash
        normalized = normalize_ast(node)
        ast_hash = hashlib.sha256(normalized.encode()).hexdigest()[:16]

        # Extract tokens for similarity
        tokens = extract_tokens(node)

        # Detect Tkinter handler
        is_handler = isinstance(node, ast.FunctionDef) and is_tk_handler(node, source)

        symbol = Symbol(
            name=node.name,
            type="function" if isinstance(node, ast.FunctionDef) else "class",
            file=str(file_path.relative_to(Path.cwd())),
            line=line,
            ast_hash=ast_hash,
            tokens=tokens,
            is_shim=is_shim,
            is_tk_handler=is_handler,
        )

        symbols.append(symbol)

    return symbols


def find_duplicates(
    symbols: List[Symbol], similarity_threshold: float = 0.85
) -> Tuple[Dict, List]:
    """
    Find exact and high-similarity duplicates.

    Returns:
        (exact_groups, similar_pairs)
        - exact_groups: {hash: [symbols]}
        - similar_pairs: [(symbol1, symbol2, score)]
    """
    # Group by hash (exact clones)
    exact_groups = defaultdict(list)
    for sym in symbols:
        if not sym.is_shim:  # Ignore shims
            exact_groups[sym.ast_hash].append(sym)

    # Remove single-element groups (no duplicates)
    exact_groups = {h: syms for h, syms in exact_groups.items() if len(syms) > 1}

    # Find high-similarity pairs
    similar_pairs = []

    # Compare all non-identical symbols
    for i, sym1 in enumerate(symbols):
        if sym1.is_shim:
            continue

        for sym2 in symbols[i + 1 :]:
            if sym2.is_shim:
                continue

            # Skip if already exact match
            if sym1.ast_hash == sym2.ast_hash:
                continue

            # Calculate similarity
            score = jaccard_similarity(sym1.tokens, sym2.tokens)

            if score >= similarity_threshold:
                similar_pairs.append((sym1, sym2, score))

    # Sort by score descending
    similar_pairs.sort(key=lambda x: x[2], reverse=True)

    return exact_groups, similar_pairs


def generate_markdown_report(
    exact_groups: Dict, similar_pairs: List, output_path: Path
) -> None:
    """Generate human-readable Markdown report."""
    lines = [
        "# Duplicates Report",
        "",
        "**Generated by:** `scripts/dev/dup_scan.py`  ",
        "**How to run:** `python scripts/dev/dup_scan.py`",
        "",
        "---",
        "",
    ]

    # Exact clones
    lines.extend(
        [
            "## 🔴 Exact Clones (Identical AST)",
            "",
            f"**Total groups:** {len(exact_groups)}",
            "",
        ]
    )

    if exact_groups:
        for hash_val, symbols in sorted(
            exact_groups.items(), key=lambda x: len(x[1]), reverse=True
        ):
            lines.append(f"### Clone Group: `{hash_val}`")
            lines.append("")
            lines.append(f"**Occurrences:** {len(symbols)}")
            lines.append("")
            lines.append("| Symbol | Type | File | Line | Notes |")
            lines.append("|--------|------|------|------|-------|")

            for sym in symbols:
                notes = []
                if sym.is_tk_handler:
                    notes.append("Tk handler")
                notes_str = ", ".join(notes) if notes else "—"

                lines.append(
                    f"| `{sym.name}` | {sym.type} | `{sym.file}` | {sym.line} | {notes_str} |"
                )

            lines.append("")
    else:
        lines.append("✅ No exact clones found.")
        lines.append("")

    # High-similarity pairs
    lines.extend(
        [
            "---",
            "",
            "## 🟡 High-Similarity Pairs (Jaccard ≥ 0.85)",
            "",
            f"**Total pairs:** {len(similar_pairs)}",
            "",
        ]
    )

    if similar_pairs:
        lines.append("| Symbol 1 | Symbol 2 | Score | File 1 | File 2 | Notes |")
        lines.append("|----------|----------|-------|--------|--------|-------|")

        for sym1, sym2, score in similar_pairs[:50]:  # Limit to top 50
            notes = []
            if sym1.is_tk_handler or sym2.is_tk_handler:
                notes.append("Tk handler")
            notes_str = ", ".join(notes) if notes else "—"

            lines.append(
                f"| `{sym1.name}` ({sym1.type}) | `{sym2.name}` ({sym2.type}) | "
                f"{score:.2f} | `{sym1.file}:{sym1.line}` | `{sym2.file}:{sym2.line}` | {notes_str} |"
            )

        if len(similar_pairs) > 50:
            lines.append("")
            lines.append(
                f"*... and {len(similar_pairs) - 50} more pairs (see JSON report)*"
            )

        lines.append("")
    else:
        lines.append("✅ No high-similarity pairs found.")
        lines.append("")

    # Summary
    lines.extend(
        [
            "---",
            "",
            "## 📊 Summary",
            "",
            f"- **Exact clone groups:** {len(exact_groups)}",
            f"- **High-similarity pairs:** {len(similar_pairs)}",
            "",
            "**Recommendations:**",
            "1. Review exact clones for consolidation opportunities",
            "2. Check high-similarity pairs for potential refactoring",
            "3. Tk handlers may have legitimate duplicates (ignore if intentional)",
            "",
        ]
    )

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"✅ Markdown report generated: {output_path}")


def generate_json_report(
    exact_groups: Dict, similar_pairs: List, output_path: Path
) -> None:
    """Generate machine-readable JSON report."""
    report = {
        "exact_clones": [
            {
                "hash": hash_val,
                "count": len(symbols),
                "symbols": [sym.to_dict() for sym in symbols],
            }
            for hash_val, symbols in exact_groups.items()
        ],
        "similar_pairs": [
            {
                "symbol1": sym1.to_dict(),
                "symbol2": sym2.to_dict(),
                "similarity_score": round(score, 3),
            }
            for sym1, sym2, score in similar_pairs
        ],
        "summary": {
            "exact_clone_groups": len(exact_groups),
            "similar_pairs": len(similar_pairs),
        },
    }

    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"✅ JSON report generated: {output_path}")


def main() -> int:
    root = Path.cwd()

    print("🔍 Scanning for Python files...")
    python_files = [p for p in root.rglob("*.py") if not is_ignored(p)]
    print(f"📁 Found {len(python_files)} Python files")

    print("\n🧬 Extracting symbols...")
    all_symbols = []
    for file_path in python_files:
        symbols = analyze_file(file_path)
        all_symbols.extend(symbols)

    print(f"🔣 Extracted {len(all_symbols)} public symbols")

    print("\n🔬 Analyzing duplicates...")
    exact_groups, similar_pairs = find_duplicates(all_symbols)

    print(f"🔴 Exact clones: {len(exact_groups)} groups")
    print(f"🟡 High-similarity pairs: {len(similar_pairs)}")

    # Generate reports
    md_path = root / "docs" / "DUPLICATES-REPORT.md"
    json_path = root / "docs" / "DUPLICATES-REPORT.json"

    md_path.parent.mkdir(parents=True, exist_ok=True)

    generate_markdown_report(exact_groups, similar_pairs, md_path)
    generate_json_report(exact_groups, similar_pairs, json_path)

    print("\n✅ Analysis complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
