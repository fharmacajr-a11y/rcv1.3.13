#!/usr/bin/env python3
"""Analyze Pyright errors specific to Supabase repository and client modules.

Filters diagnostics for supabase_repo.py and supabase_client.py to identify
type annotation opportunities for CompatPack-08.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypedDict


# -----------------------------------------------------------------------------
# Pyright JSON structure types
# -----------------------------------------------------------------------------
class PyrightRangePos(TypedDict, total=False):
    """Position in a text file (line, character)."""

    line: int
    character: int


class PyrightRange(TypedDict, total=False):
    """Range in a text file (start, end positions)."""

    start: PyrightRangePos
    end: PyrightRangePos


class PyrightDiagnostic(TypedDict, total=False):
    """Pyright diagnostic entry from generalDiagnostics array."""

    file: str
    message: str
    severity: str
    rule: str
    range: PyrightRange


class PyrightReport(TypedDict, total=False):
    """Top-level Pyright JSON report structure."""

    generalDiagnostics: list[PyrightDiagnostic]
    summary: dict[str, Any]


# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------
def load_pyright_report(path: Path) -> PyrightReport | None:
    """Load Pyright JSON report from file.

    Args:
        path: Path to pyright.json file

    Returns:
        Parsed Pyright report or None if file not found
    """
    if not path.exists():
        print(f"❌ {path} not found. Run pyright first.")
        return None

    # Read with UTF-8-sig to handle BOM if present
    with open(path, encoding="utf-8-sig") as f:
        data: PyrightReport = json.load(f)
    return data


def filter_supabase_errors(diagnostics: list[PyrightDiagnostic]) -> list[PyrightDiagnostic]:
    """Filter diagnostics for Supabase-related files.

    Args:
        diagnostics: List of all Pyright diagnostics

    Returns:
        List of diagnostics from supabase_repo, supabase_client, supabase_auth
    """
    supabase_keywords: list[str] = ["supabase_repo", "supabase_client", "supabase_auth"]
    return [d for d in diagnostics if any(kw in d.get("file", "").lower() for kw in supabase_keywords)]


def filter_return_type_errors(diagnostics: list[PyrightDiagnostic]) -> list[PyrightDiagnostic]:
    """Filter diagnostics for return type related errors.

    Args:
        diagnostics: List of all Pyright diagnostics

    Returns:
        List of diagnostics mentioning return types
    """
    return_patterns: list[str] = [
        "return type",
        "declared return type",
        "inferred return type",
    ]
    return [d for d in diagnostics if any(pattern in d.get("message", "").lower() for pattern in return_patterns)]


def get_line_number(diagnostic: PyrightDiagnostic) -> int:
    """Extract line number from diagnostic (1-indexed for display).

    Args:
        diagnostic: Pyright diagnostic entry

    Returns:
        Line number (1-indexed), or 0 if not found
    """
    range_data: PyrightRange | None = diagnostic.get("range")
    if range_data:
        start_pos: PyrightRangePos | None = range_data.get("start")
        if start_pos:
            line_zero_indexed: int | None = start_pos.get("line")
            if line_zero_indexed is not None:
                return line_zero_indexed + 1
    return 0


def print_grouped_errors(errors_by_file: dict[str, list[PyrightDiagnostic]]) -> None:
    """Print errors grouped by file.

    Args:
        errors_by_file: Dictionary mapping file paths to lists of diagnostics
    """
    for idx, (file_path, file_errors) in enumerate(sorted(errors_by_file.items()), 1):
        error_count: int = len(file_errors)
        print(f"\n{idx}. {file_path} ({error_count} errors)")
        print("-" * 80)

        # Show first 15 errors per file
        max_display: int = 15
        for err in file_errors[:max_display]:
            line_num: int = get_line_number(err)
            msg: str = err.get("message", "")
            # Truncate long messages
            if len(msg) > 100:
                msg = msg[:97] + "..."
            print(f"   Line {line_num:4d}: {msg}")

        remaining: int = error_count - max_display
        if remaining > 0:
            print(f"   ... and {remaining} more errors")


def print_priority_errors(priority_errors: list[PyrightDiagnostic]) -> None:
    """Print high-priority errors in compact format.

    Args:
        priority_errors: List of priority diagnostics to display
    """
    max_display: int = 20
    for idx, err in enumerate(priority_errors[:max_display], 1):
        file_name: str = Path(err.get("file", "")).name
        line_num: int = get_line_number(err)
        msg: str = err.get("message", "")
        if len(msg) > 80:
            msg = msg[:77] + "..."
        print(f"{idx:2d}. {file_name}:{line_num:4d} | {msg}")

    remaining: int = len(priority_errors) - max_display
    if remaining > 0:
        print(f"    ... and {remaining} more priority errors")


# -----------------------------------------------------------------------------
# Main analysis function
# -----------------------------------------------------------------------------
def main() -> None:
    """Filter and display Supabase-related Pyright errors."""
    qa_dir: Path = Path(__file__).parent
    pyright_json: Path = qa_dir / "pyright.json"

    report: PyrightReport | None = load_pyright_report(pyright_json)
    if report is None:
        return

    diagnostics: list[PyrightDiagnostic] = report.get("generalDiagnostics", [])
    supabase_errors: list[PyrightDiagnostic] = filter_supabase_errors(diagnostics)
    return_type_errors: list[PyrightDiagnostic] = filter_return_type_errors(diagnostics)

    # Print summary
    print(f"📊 Total Pyright errors: {len(diagnostics)}")
    print(f"🔍 Supabase-related errors: {len(supabase_errors)}")
    print(f"📤 Return type errors (all files): {len(return_type_errors)}")
    print()

    if supabase_errors:
        print("=" * 80)
        print("SUPABASE MODULE ERRORS (supabase_repo, supabase_client, supabase_auth)")
        print("=" * 80)

        # Group by file
        by_file: dict[str, list[PyrightDiagnostic]] = {}
        for err in supabase_errors:
            file_path: str = err.get("file", "unknown")
            file_errors: list[PyrightDiagnostic] = by_file.setdefault(file_path, [])
            file_errors.append(err)

        print_grouped_errors(by_file)

    print("\n" + "=" * 80)
    print("PRIORITY TARGETS FOR COMPATPACK-08")
    print("=" * 80)

    # Filter high-priority error messages
    priority_patterns: list[str] = [
        "return type of function is unknown",
        "return type is partially unknown",
        "expression of type",
        "type of parameter",
    ]

    priority_errors: list[PyrightDiagnostic] = [
        err
        for err in supabase_errors
        if any(pattern in err.get("message", "").lower() for pattern in priority_patterns)
    ]

    print(f"\n🎯 High-priority type errors: {len(priority_errors)}")
    print_priority_errors(priority_errors)


if __name__ == "__main__":
    main()
