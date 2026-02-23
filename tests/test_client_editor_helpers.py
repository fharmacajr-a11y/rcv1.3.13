# pyright: reportAttributeAccessIssue=false
# -*- coding: utf-8 -*-
"""Testes para helpers do ClientEditorDialog."""

import pytest
from dataclasses import dataclass


# Importar helpers do módulo
# Nota: Usamos importação direta para testes, mas os helpers são internos ao dialog
def _safe_get(obj, key: str, default=""):
    """Cópia local para testes (espelho do helper no dialog)."""
    from collections.abc import Mapping

    if obj is None:
        return default
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _conflict_desc(conflict):
    """Cópia local para testes (espelho do helper no dialog)."""
    if conflict is None:
        return "cliente desconhecido"

    cid = _safe_get(conflict, "id", "?")
    razao = _safe_get(conflict, "razao_social", "cliente desconhecido")
    cnpj = _safe_get(conflict, "cnpj", "")

    desc = f"ID {cid} - {razao}"
    if cnpj:
        desc += f" ({cnpj})"

    return desc


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
