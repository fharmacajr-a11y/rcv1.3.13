#!/usr/bin/env python
"""
Analisa issues de estilo do Ruff e Flake8.
Agrupa por código de erro e arquivo para facilitar correções.
"""

import json
from collections import defaultdict
from pathlib import Path


def analyze_ruff():
    """Analisa issues do Ruff."""
    ruff_file = Path("devtools/qa/ruff.json")
    if not ruff_file.exists():
        print("❌ devtools/qa/ruff.json não encontrado")
        return

    with open(ruff_file, encoding="utf-8-sig") as f:
        issues = json.load(f)

    print(f"\n{'='*70}")
    print(f"RUFF ANALYSIS - Total Issues: {len(issues)}")
    print(f"{'='*70}\n")

    # Agrupar por código
    by_code = defaultdict(list)
    for issue in issues:
        code = issue.get("code", "UNKNOWN")
        by_code[code].append(issue)

    # Mostrar resumo por código
    print("Issues por código:")
    for code in sorted(by_code.keys()):
        count = len(by_code[code])
        print(f"  {code}: {count} issues")

    # Detalhar cada código
    for code in sorted(by_code.keys()):
        issues_list = by_code[code]
        print(f"\n{'-'*70}")
        print(f"{code} - {len(issues_list)} issues:")
        print(f"{'-'*70}")

        # Agrupar por arquivo
        by_file = defaultdict(list)
        for issue in issues_list:
            filename = issue.get("filename", "UNKNOWN")
            # Simplificar path
            if "v1.1.45" in filename:
                filename = filename.split("v1.1.45\\")[-1]
            by_file[filename].append(issue)

        for filename in sorted(by_file.keys()):
            file_issues = by_file[filename]
            print(f"\n  📄 {filename} ({len(file_issues)} issues):")
            for issue in file_issues[:3]:  # Mostrar max 3 por arquivo
                row = issue.get("location", {}).get("row", "?")
                col = issue.get("location", {}).get("column", "?")
                msg = issue.get("message", "")
                print(f"    Line {row}:{col} - {msg}")
            if len(file_issues) > 3:
                print(f"    ... and {len(file_issues) - 3} more")


def analyze_flake8():
    """Analisa issues do Flake8."""
    flake8_file = Path("devtools/qa/flake8.txt")
    if not flake8_file.exists():
        print("❌ devtools/qa/flake8.txt não encontrado")
        return

    with open(flake8_file, encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    print(f"\n{'='*70}")
    print(f"FLAKE8 ANALYSIS - Total Issues: {len(lines)}")
    print(f"{'='*70}\n")

    # Agrupar por código
    by_code = defaultdict(list)
    by_file = defaultdict(list)

    for line in lines:
        # Format: path:row:col:code:text
        parts = line.split(":", 4)
        if len(parts) >= 4:
            filepath, row, col, code = parts[:4]
            msg = parts[4] if len(parts) > 4 else ""

            # Simplificar path
            if "v1.1.45" in filepath:
                filepath = filepath.split("v1.1.45\\")[-1]

            by_code[code].append((filepath, row, col, msg))
            by_file[filepath].append((code, row, col, msg))

    # Mostrar resumo por código
    print("Issues por código:")
    for code in sorted(by_code.keys()):
        count = len(by_code[code])
        print(f"  {code}: {count} issues")

    # Detalhar top códigos
    print(f"\n{'-'*70}")
    print("Top codes detailed:")
    print(f"{'-'*70}")

    for code in sorted(by_code.keys(), key=lambda c: len(by_code[c]), reverse=True)[:5]:
        issues_list = by_code[code]
        print(f"\n{code} - {len(issues_list)} issues:")

        # Agrupar por arquivo
        code_by_file = defaultdict(int)
        for filepath, _, _, _ in issues_list:
            code_by_file[filepath] += 1

        for filepath in sorted(code_by_file.keys(), key=lambda f: code_by_file[f], reverse=True)[:5]:
            count = code_by_file[filepath]
            print(f"  📄 {filepath}: {count} issues")


if __name__ == "__main__":
    analyze_ruff()
    analyze_flake8()
    print(f"\n{'='*70}\n")
