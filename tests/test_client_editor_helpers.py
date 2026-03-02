# pyright: reportAttributeAccessIssue=false
# -*- coding: utf-8 -*-
"""Testes para helpers do ClientEditorDialog.

Importa _safe_get e _conflict_desc **diretamente do código-fonte real**
via AST (sem carregar o módulo inteiro, que depende de Tk/CTk).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from conftest import extract_functions_from_source

_SRC_FILE = (
    Path(__file__).resolve().parent.parent / "src" / "modules" / "clientes" / "ui" / "views" / "client_editor_dialog.py"
)

_fns = extract_functions_from_source(
    _SRC_FILE,
    "_safe_get",
    "_conflict_desc",
    extra_namespace={"Mapping": Mapping},
)
_safe_get = _fns["_safe_get"]
_conflict_desc = _fns["_conflict_desc"]


class TestSafeGet:
    """Testes para o helper _safe_get()."""

    def test_none_returns_default(self):
        """None retorna default."""
        assert _safe_get(None, "key", "default") == "default"
        assert _safe_get(None, "key") == ""

    def test_dict_access(self):
        """Acesso a dict funciona."""
        data = {"name": "João", "age": 30}
        assert _safe_get(data, "name") == "João"
        assert _safe_get(data, "age") == 30
        assert _safe_get(data, "missing", "N/A") == "N/A"

    def test_object_access(self):
        """Acesso a objeto com atributos funciona."""

        @dataclass
        class Cliente:
            id: int
            razao_social: str

        obj = Cliente(id=123, razao_social="Empresa Teste")
        assert _safe_get(obj, "id") == 123
        assert _safe_get(obj, "razao_social") == "Empresa Teste"
        assert _safe_get(obj, "missing", "fallback") == "fallback"

    def test_nested_dict(self):
        """Funciona com dicts aninhados."""
        data = {"user": {"name": "Maria"}}
        assert _safe_get(data, "user") == {"name": "Maria"}

    def test_empty_string_key(self):
        """Chave vazia retorna default."""
        data = {"": "valor"}
        assert _safe_get(data, "", "default") == "valor"


class TestConflictDesc:
    """Testes para o helper _conflict_desc()."""

    def test_none_returns_unknown(self):
        """None retorna 'cliente desconhecido'."""
        assert _conflict_desc(None) == "cliente desconhecido"

    def test_dict_with_all_fields(self):
        """Dict com todos os campos."""
        conflict = {
            "id": 123,
            "razao_social": "Empresa ABC",
            "cnpj": "12.345.678/0001-90",
        }
        result = _conflict_desc(conflict)
        assert result == "ID 123 - Empresa ABC (12.345.678/0001-90)"

    def test_dict_without_cnpj(self):
        """Dict sem CNPJ."""
        conflict = {
            "id": 456,
            "razao_social": "Empresa XYZ",
        }
        result = _conflict_desc(conflict)
        assert result == "ID 456 - Empresa XYZ"

    def test_object_with_all_fields(self):
        """Objeto com todos os campos."""

        @dataclass
        class Cliente:
            id: int
            razao_social: str
            cnpj: str

        obj = Cliente(id=789, razao_social="Empresa DEF", cnpj="98.765.432/0001-10")
        result = _conflict_desc(obj)
        assert result == "ID 789 - Empresa DEF (98.765.432/0001-10)"

    def test_missing_fields_use_defaults(self):
        """Campos faltantes usam defaults."""
        conflict = {}
        result = _conflict_desc(conflict)
        assert result == "ID ? - cliente desconhecido"

    def test_partial_fields(self):
        """Campos parciais."""
        conflict = {"id": 111}
        result = _conflict_desc(conflict)
        assert result == "ID 111 - cliente desconhecido"
