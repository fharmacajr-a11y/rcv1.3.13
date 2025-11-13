#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyze project modules and classify them by architecture layer.

This script scans the project directory structure, identifies Python modules,
and categorizes them into layers: UI, Core, Infra, Adapter, Domain, Typing.

Output: devtools/arch/module_map.json
"""

import json
import os
from pathlib import Path
from typing import Any


def classify_module(file_path: Path, content: str) -> str:
    """
    Classify a Python module based on its path and imports.

    Args:
        file_path: Path to the Python file
        content: File content as string

    Returns:
        Layer name: 'ui', 'core', 'infra', 'adapter', 'domain', 'typing', 'script', 'third_party'
    """
    path_str = str(file_path).replace("\\", "/")
    content_lower = content.lower()

    # Typing stubs
    if "typings/" in path_str:
        return "typing"

    # Third party
    if "third_party/" in path_str:
        return "third_party"

    # Scripts (utilities, tests, demos)
    if any(x in path_str for x in ["scripts/", "devtools/", "tests/"]):
        return "script"

    # Adapters
    if "adapters/" in path_str:
        return "adapter"

    # Infrastructure
    if "infra/" in path_str:
        return "infra"

    # Domain/Data
    if "data/" in path_str:
        return "domain"

    # Security (treat as infra)
    if "security/" in path_str:
        return "infra"

    # Helpers (could be core or infra, check imports)
    if "helpers/" in path_str:
        # If imports UI libs, it's UI helper; otherwise core
        if any(ui_lib in content_lower for ui_lib in ["tkinter", "ttk", "ttkbootstrap"]):
            return "ui"
        return "core"

    # UI detection (src/ui or imports UI libraries)
    if "src/ui/" in path_str or "src\\ui\\" in path_str:
        return "ui"

    # Check imports for UI indicators
    ui_indicators = ["tkinter", "ttkbootstrap", "from src.ui", "import src.ui"]
    if any(indicator in content_lower for indicator in ui_indicators):
        return "ui"

    # Infrastructure indicators
    infra_indicators = [
        "supabase", "httpx", "requests", "psycopg", "sqlalchemy",
        "redis", "cache", "from infra", "import infra"
    ]
    if any(indicator in content_lower for indicator in infra_indicators):
        return "infra"

    # If in src/ but not UI and not infra, likely core
    if "src/" in path_str:
        return "core"

    # Default fallback
    return "core"


def extract_key_imports(content: str, limit: int = 10) -> list[str]:
    """
    Extract key import statements from Python file content.

    Args:
        content: File content
        limit: Maximum number of imports to extract

    Returns:
        List of import statements
    """
    imports = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("import ") or stripped.startswith("from "):
            # Skip comments
            if "#" in stripped:
                stripped = stripped.split("#")[0].strip()
            imports.append(stripped)
            if len(imports) >= limit:
                break
    return imports


def analyze_modules(project_root: Path) -> dict[str, Any]:
    """
    Analyze all Python modules in the project.

    Args:
        project_root: Path to project root directory

    Returns:
        Dictionary with module analysis results
    """
    module_map: dict[str, Any] = {
        "project_root": str(project_root),
        "layers": {
            "ui": [],
            "core": [],
            "infra": [],
            "adapter": [],
            "domain": [],
            "typing": [],
            "script": [],
            "third_party": []
        },
        "stats": {}
    }

    scan_dirs = [
        "src", "adapters", "infra", "data", "helpers",
        "security", "scripts", "third_party", "typings"
    ]

    total_files = 0
    for scan_dir in scan_dirs:
        dir_path = project_root / scan_dir
        if not dir_path.exists():
            continue

        for root, _dirs, files in os.walk(dir_path):
            for file in files:
                if not file.endswith(".py"):
                    continue

                file_path = Path(root) / file
                relative_path = file_path.relative_to(project_root)

                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                except Exception as e:
                    print(f"Warning: Could not read {relative_path}: {e}")
                    continue

                layer = classify_module(file_path, content)
                key_imports = extract_key_imports(content)

                module_info = {
                    "path": str(relative_path).replace("\\", "/"),
                    "name": file.replace(".py", ""),
                    "layer": layer,
                    "imports": key_imports[:5]  # Keep top 5 imports for reference
                }

                module_map["layers"][layer].append(module_info)
                total_files += 1

    # Calculate stats
    for layer, modules in module_map["layers"].items():
        module_map["stats"][layer] = len(modules)

    module_map["stats"]["total"] = total_files

    return module_map


def main() -> None:
    """Main entry point."""
    project_root = Path(__file__).parent.parent.parent
    output_path = project_root / "devtools" / "arch" / "module_map.json"

    print(f"Analyzing modules in: {project_root}")

    module_map = analyze_modules(project_root)

    # Save to JSON
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(module_map, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Module map saved to: {output_path}")
    print("\nLayer Statistics:")
    for layer, count in sorted(module_map["stats"].items()):
        if layer != "total":
            print(f"  {layer:15s}: {count:3d} modules")
    print(f"  {'total':15s}: {module_map['stats']['total']:3d} modules")


if __name__ == "__main__":
    main()
