# -*- coding: utf-8 -*-
"""Pytest configuration and shared test utilities.

Provides:
  - sys.path setup so ``src`` is importable (when deps allow)
  - ``extract_functions_from_source`` helper: loads real function code from
    source files via AST parsing, without importing the module (avoids
    needing UI/Tk stubs for pure-logic functions).
"""

from __future__ import annotations

import ast
import sys
import textwrap
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# AST-based function extractor
# ---------------------------------------------------------------------------


def extract_functions_from_source(
    filepath: Path | str,
    *func_names: str,
    class_name: str | None = None,
    extra_namespace: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Extract function objects from a source file via AST + exec.

    This lets tests exercise the **real** function code without importing
    the surrounding module (which may depend on Tk / customtkinter / etc.).

    Parameters
    ----------
    filepath:
        Absolute or relative path to the ``.py`` file.
    *func_names:
        Names of the functions to extract.
    class_name:
        If given, look for *static methods* inside `class_name` instead
        of module-level functions.  The ``@staticmethod`` decorator (if
        present) is stripped automatically.
    extra_namespace:
        Extra names to inject into the ``exec`` namespace so that the
        function body can reference them (e.g. ``{"Mapping": Mapping}``).

    Returns
    -------
    dict mapping each name in *func_names* to the compiled function object.

    Raises
    ------
    RuntimeError
        If any requested function is not found.
    """
    filepath = Path(filepath)
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)

    # Decide where to look: top-level or inside a class
    if class_name is not None:
        container: ast.AST | None = None
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                container = node
                break
        if container is None:
            msg = f"Class {class_name!r} not found in {filepath}"
            raise RuntimeError(msg)
    else:
        container = tree

    remaining = set(func_names)
    fragments: list[str] = []

    for node in ast.iter_child_nodes(container):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in remaining:
            raw = "".join(lines[node.lineno - 1 : node.end_lineno])

            # If inside a class, dedent and strip ``@staticmethod``
            if class_name is not None:
                raw = textwrap.dedent(raw)
                # Remove @staticmethod decorator line if present
                clean_lines = []
                for ln in raw.splitlines(keepends=True):
                    if ln.strip() == "@staticmethod":
                        continue
                    clean_lines.append(ln)
                raw = "".join(clean_lines)

            fragments.append(raw)
            remaining.discard(node.name)

    if remaining:
        msg = f"Functions not found in {filepath}: {remaining}"
        raise RuntimeError(msg)

    ns: dict[str, Any] = {}
    if extra_namespace:
        ns.update(extra_namespace)

    for frag in fragments:
        exec(compile(frag, str(filepath), "exec"), ns)  # noqa: S102

    return {name: ns[name] for name in func_names}
