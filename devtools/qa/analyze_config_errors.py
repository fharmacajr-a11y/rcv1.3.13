"""Filter Pyright errors for config/settings/environment files and simple return types."""
import json
from pathlib import Path
from typing import Any, Dict, List

def main():
    pyright_file = Path("devtools/qa/pyright.json")
    if not pyright_file.exists():
        print("❌ pyright.json not found")
        return
    
    with pyright_file.open(encoding="utf-8-sig") as f:
        data: Dict[str, Any] = json.load(f)
    
    diagnostics: List[Dict[str, Any]] = data.get("generalDiagnostics", [])
    
    # Filter 1: Config/settings/environment/constants files
    config_keywords = ["settings", "config", "environment", "constants"]
    config_errors = [
        d for d in diagnostics
        if any(kw in d.get("file", "").lower() for kw in config_keywords)
    ]
    
    # Filter 2: Simple return type errors (bool, str, list, dict)
    return_keywords = [
        "return type",
        "declared return type",
        "is not assignable to return type",
        'return type "bool"',
        'return type "str"',
        'return type "list"',
        'return type "dict"',
    ]
    return_errors = [
        d for d in diagnostics
        if any(kw in d.get("message", "").lower() for kw in return_keywords)
        and "auth" not in d.get("file", "").lower()
        and "upload" not in d.get("file", "").lower()
        and "storage" not in d.get("file", "").lower()
        and "session" not in d.get("file", "").lower()
    ]
    
    print("=" * 80)
    print("ANÁLISE PYRIGHT - COMPATPACK-07 (Config/Settings & Simple Returns)")
    print("=" * 80)
    print(f"\nTotal Pyright errors: {len(diagnostics)}")
    print(f"Config/settings/environment errors: {len(config_errors)}")
    print(f"Simple return type errors (non-critical): {len(return_errors)}")
    
    # Combine and deduplicate
    all_target_errors = {
        (d["file"], d["range"]["start"]["line"]): d
        for d in config_errors + return_errors
    }
    
    print(f"\nCombined unique target errors: {len(all_target_errors)}")
    print("\n=== TOP 10 TARGET ERRORS ===\n")
    
    for idx, ((file, line), d) in enumerate(sorted(all_target_errors.items())[:10], 1):
        file_short = file.split("Copia")[-1].lstrip("\\").lstrip("/") if "Copia" in file else file
        msg_short = d["message"][:100].replace("\n", " ")
        print(f"{idx}. {file_short}:{line+1}")
        print(f"   {msg_short}")
        print()

if __name__ == "__main__":
    main()
