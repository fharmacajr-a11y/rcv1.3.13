# pyright: reportAttributeAccessIssue=false
# -*- coding: utf-8 -*-
"""
Teste de regressão — Restore da lixeira NÃO cria pastas artificiais.

Prova que:
1. restaurar_clientes_da_lixeira (service.py) faz apenas DB update.
2. restore_clients (lixeira_service.py) faz apenas DB update.
3. ensure_mandatory_subfolders foi removido de api.py.
4. MANDATORY_SUBPASTAS e get_mandatory_subpastas foram removidos de subpastas_config.py.
5. get_mandatory_subfolder_names foi removido de subfolders.py.
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

_SERVICE = _ROOT / "src" / "modules" / "clientes" / "core" / "service.py"
_LIXEIRA = _ROOT / "src" / "core" / "services" / "lixeira_service.py"
_STORAGE_API = _ROOT / "src" / "adapters" / "storage" / "api.py"
_SUBPASTAS_CFG = _ROOT / "src" / "utils" / "subpastas_config.py"
_SUBFOLDERS = _ROOT / "src" / "utils" / "subfolders.py"


class TestRestoreNoArtificialFolders(unittest.TestCase):
    """O restore da lixeira NÃO deve criar pastas artificiais (SIFAP, ANVISA etc.)."""

    def test_service_restore_no_ensure_mandatory_subfolders(self) -> None:
        source = _SERVICE.read_text(encoding="utf-8")
        self.assertNotIn(
            "ensure_mandatory_subfolders",
            source,
            "service.py não deve chamar ensure_mandatory_subfolders no restore",
        )

    def test_lixeira_service_no_ensure_mandatory_subfolders(self) -> None:
        source = _LIXEIRA.read_text(encoding="utf-8")
        self.assertNotIn(
            "ensure_mandatory_subfolders",
            source,
            "lixeira_service.py não deve chamar ensure_mandatory_subfolders",
        )

    def test_storage_api_no_ensure_mandatory_subfolders(self) -> None:
        source = _STORAGE_API.read_text(encoding="utf-8")
        self.assertNotIn(
            "def ensure_mandatory_subfolders",
            source,
            "api.py não deve definir ensure_mandatory_subfolders",
        )


class TestLegacyMandatorySubfoldersRemoved(unittest.TestCase):
    """O conceito de 'subpastas obrigatórias' não deve existir como produto."""

    def test_subpastas_config_no_mandatory_tuple(self) -> None:
        source = _SUBPASTAS_CFG.read_text(encoding="utf-8")
        self.assertNotIn(
            "MANDATORY_SUBPASTAS",
            source,
            "MANDATORY_SUBPASTAS não deve existir em subpastas_config.py",
        )

    def test_subpastas_config_no_get_mandatory(self) -> None:
        source = _SUBPASTAS_CFG.read_text(encoding="utf-8")
        self.assertNotIn(
            "def get_mandatory_subpastas",
            source,
            "get_mandatory_subpastas não deve existir em subpastas_config.py",
        )

    def test_subfolders_no_get_mandatory_subfolder_names(self) -> None:
        source = _SUBFOLDERS.read_text(encoding="utf-8")
        self.assertNotIn(
            "def get_mandatory_subfolder_names",
            source,
            "get_mandatory_subfolder_names não deve existir em subfolders.py",
        )

    def test_service_restore_is_db_only(self) -> None:
        """restaurar_clientes_da_lixeira deve fazer APENAS update na tabela clients."""
        source = _SERVICE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "restaurar_clientes_da_lixeira":
                # Extrai apenas as statements do corpo (sem a docstring)
                body_stmts = node.body
                # Pula a docstring se presente
                if body_stmts and isinstance(body_stmts[0], ast.Expr) and isinstance(body_stmts[0].value, ast.Constant):
                    body_stmts = body_stmts[1:]
                code_lines = [ast.get_source_segment(source, stmt) or "" for stmt in body_stmts]
                code_text = "\n".join(code_lines).lower()
                self.assertIn("deleted_at", code_text, "Deve setar deleted_at para None")
                self.assertNotIn("storage", code_text, "Não deve manipular storage")
                self.assertNotIn("upload", code_text, "Não deve fazer upload")
                self.assertNotIn(".keep", code_text, "Não deve criar .keep files")
                return
        self.fail("restaurar_clientes_da_lixeira não encontrada no service.py")


if __name__ == "__main__":
    unittest.main()
