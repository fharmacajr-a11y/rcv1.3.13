#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analyze top Pyright errors by file and severity.

This script reads the Pyright JSON report and provides a summary of:
1. Top files with most errors
2. Detailed error messages for those files
3. Breakdown by error rule/code

Usage:
    python devtools/qa/analyze_top_errors.py
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def main() -> None:
    """Analyze and display top Pyright errors."""
    pyright_json = Path("devtools/qa/pyright.json")

    if not pyright_json.exists():
        print(f"Error: {pyright_json} not found. Run Pyright first.")
        return

    # Load Pyright report
    with open(pyright_json, "r", encoding="utf-8-sig") as f:
        data: dict[str, Any] = json.load(f)

    summary = data.get("summary", {})
    diagnostics = data.get("generalDiagnostics", [])

    # Print summary
    print("=" * 80)
    print("PYRIGHT SUMMARY")
    print("=" * 80)
    print(f"Total errors: {summary.get('errorCount', 0)}")
    print(f"Total warnings: {summary.get('warningCount', 0)}")
    print(f"Total informations: {summary.get('informationCount', 0)}")
    print()

    # Filter only errors
    errors = [d for d in diagnostics if d.get("severity") == "error"]

    if not errors:
        print("✅ No errors found!")
        return

    print("=" * 80)
    print(f"TOP PYRIGHT ERRORS (total: {len(errors)})")
    print("=" * 80)
    print()

    # Group errors by file
    errors_by_file: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for error in errors:
        file_path = error.get("file", "")
        errors_by_file[file_path].append(error)

    # Sort files by error count (descending)
    sorted_files = sorted(
        errors_by_file.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )

    # Display top 10 files with most errors
    print("TOP 10 FILES WITH MOST ERRORS:")
    print("-" * 80)
    for i, (file_path, file_errors) in enumerate(sorted_files[:10], 1):
        # Shorten path for display
        short_path = file_path.replace("c:\\Users\\Pichau\\Desktop\\v1.1.31 - Copia\\", "")
        short_path = short_path.replace("\\", "/")
        print(f"{i:2d}. {short_path}: {len(file_errors)} errors")
    print()

    # Display detailed errors for top 3 files
    print("=" * 80)
    print("DETAILED ERRORS (TOP 3 FILES)")
    print("=" * 80)
    print()

    for rank, (file_path, file_errors) in enumerate(sorted_files[:3], 1):
        short_path = file_path.replace("c:\\Users\\Pichau\\Desktop\\v1.1.31 - Copia\\", "")
        short_path = short_path.replace("\\", "/")

        print(f"[{rank}] {short_path} ({len(file_errors)} errors)")
        print("-" * 80)

        for error in file_errors[:20]:  # Limit to first 20 errors per file
            line = error.get("range", {}).get("start", {}).get("line", 0) + 1
            rule = error.get("rule", "unknown")
            message = error.get("message", "")[:100]  # Truncate long messages

            print(f"  Line {line:4d} | {rule:30s} | {message}")

        if len(file_errors) > 20:
            print(f"  ... and {len(file_errors) - 20} more errors")
        print()

    # Breakdown by error rule
    print("=" * 80)
    print("ERROR BREAKDOWN BY RULE")
    print("=" * 80)
    print()

    errors_by_rule: dict[str, int] = defaultdict(int)
    for error in errors:
        rule = error.get("rule", "unknown")
        errors_by_rule[rule] += 1

    sorted_rules = sorted(errors_by_rule.items(), key=lambda x: x[1], reverse=True)

    for rule, count in sorted_rules[:15]:  # Top 15 rules
        print(f"{rule:40s}: {count:3d} errors")
    print()

    # Suggest focus areas
    print("=" * 80)
    print("SUGGESTED FOCUS AREAS (Group A - Safe to fix)")
    print("=" * 80)
    print()

    safe_rules = [
        "reportUndefinedVariable",
        "reportGeneralTypeIssues",
        "reportOptionalMemberAccess",
        "reportReturnType",
        "reportArgumentType"
    ]

    for rule in safe_rules:
        count = errors_by_rule.get(rule, 0)
        if count > 0:
            print(f"✓ {rule}: {count} errors (potentially safe)")

    print()
    print("=" * 80)
    print("Next steps:")
    print("1. Review top 3 files for obvious errors (undefined vars, typos, etc.)")
    print("2. Select up to 10 safe errors from UI/helpers/devtools")
    print("3. Avoid auth/upload/storage modules (Group C/D)")
    print("=" * 80)


if __name__ == "__main__":
    main()
