#!/usr/bin/env python3
"""Analyze Pyright errors specific to Supabase repository and client modules.

Filters diagnostics for supabase_repo.py and supabase_client.py to identify
type annotation opportunities for CompatPack-08.
"""

import json
from pathlib import Path


def main() -> None:
    """Filter and display Supabase-related Pyright errors."""
    qa_dir = Path(__file__).parent
    pyright_json = qa_dir / "pyright.json"

    if not pyright_json.exists():
        print(f"❌ {pyright_json} not found. Run pyright first.")
        return

    # Read with UTF-8-sig to handle BOM if present
    with open(pyright_json, encoding="utf-8-sig") as f:
        data = json.load(f)

    diagnostics = data.get("generalDiagnostics", [])
    
    # Filter for Supabase-related files
    supabase_keywords = ["supabase_repo", "supabase_client", "supabase_auth"]
    supabase_errors = [
        d for d in diagnostics
        if any(kw in d.get("file", "").lower() for kw in supabase_keywords)
    ]

    # Also filter return type errors across all files (useful for context)
    return_type_errors = [
        d for d in diagnostics
        if any(pattern in d.get("message", "").lower() for pattern in [
            "return type",
            "declared return type",
            "inferred return type",
        ])
    ]

    print(f"📊 Total Pyright errors: {len(diagnostics)}")
    print(f"🔍 Supabase-related errors: {len(supabase_errors)}")
    print(f"📤 Return type errors (all files): {len(return_type_errors)}")
    print()

    if supabase_errors:
        print("=" * 80)
        print("SUPABASE MODULE ERRORS (supabase_repo, supabase_client, supabase_auth)")
        print("=" * 80)
        
        # Group by file
        by_file: dict[str, list[dict]] = {}
        for err in supabase_errors:
            file_path = err.get("file", "unknown")
            by_file.setdefault(file_path, []).append(err)
        
        for idx, (file_path, errors) in enumerate(sorted(by_file.items()), 1):
            print(f"\n{idx}. {file_path} ({len(errors)} errors)")
            print("-" * 80)
            
            # Show first 15 errors per file
            for err in errors[:15]:
                line = err.get("range", {}).get("start", {}).get("line", 0) + 1
                msg = err.get("message", "")
                # Truncate long messages
                if len(msg) > 100:
                    msg = msg[:97] + "..."
                print(f"   Line {line:4d}: {msg}")
            
            if len(errors) > 15:
                print(f"   ... and {len(errors) - 15} more errors")

    print("\n" + "=" * 80)
    print("PRIORITY TARGETS FOR COMPATPACK-08")
    print("=" * 80)
    
    # Filter high-priority error messages
    priority_patterns = [
        "return type of function is unknown",
        "return type is partially unknown",
        "expression of type",
        "type of parameter",
    ]
    
    priority_errors = [
        err for err in supabase_errors
        if any(pattern in err.get("message", "").lower() for pattern in priority_patterns)
    ]
    
    print(f"\n🎯 High-priority type errors: {len(priority_errors)}")
    for idx, err in enumerate(priority_errors[:20], 1):
        file_path = Path(err.get("file", "")).name
        line = err.get("range", {}).get("start", {}).get("line", 0) + 1
        msg = err.get("message", "")
        if len(msg) > 80:
            msg = msg[:77] + "..."
        print(f"{idx:2d}. {file_path}:{line:4d} | {msg}")
    
    if len(priority_errors) > 20:
        print(f"    ... and {len(priority_errors) - 20} more priority errors")


if __name__ == "__main__":
    main()
