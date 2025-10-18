#!/usr/bin/env python3
"""Wrapper para executar import-linter."""
import sys
from importlinter.cli import lint_imports_command

if __name__ == "__main__":
    sys.exit(lint_imports_command())
