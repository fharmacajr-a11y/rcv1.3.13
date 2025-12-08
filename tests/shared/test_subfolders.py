# -*- coding: utf-8 -*-
"""Testes para shared/subfolders.py."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.shared.subfolders import (
    sanitize_subfolder_name,
    suggest_client_subfolder,
    list_storage_subfolders,
    get_mandatory_subfolder_names,
    build_storage_path,
)


class TestSanitizeSubfolderName:
    """Testes para sanitize_subfolder_name."""

    def test_sanitize_basic(self):
        """Testa sanitização básica."""
        assert sanitize_subfolder_name("GERAL") == "GERAL"
        assert sanitize_subfolder_name("SIFAP") == "SIFAP"

    def test_sanitize_with_spaces(self):
        """Testa remoção de espaços."""
        assert sanitize_subfolder_name("Nome Com Espaços") == "NomeComEspacos"

    def test_sanitize_with_special_chars(self):
        """Testa remoção de caracteres especiais."""
        assert sanitize_subfolder_name("Nome@Com#Especiais!") == "NomeComEspeciais"

    def test_sanitize_keeps_hyphen_underscore(self):
        """Testa que hífen e underscore são mantidos."""
        assert sanitize_subfolder_name("Nome-Com_Separadores") == "Nome-Com_Separadores"

    def test_sanitize_empty(self):
        """Testa com string vazia."""
        assert sanitize_subfolder_name("") == ""

    def test_sanitize_none(self):
        """Testa com None."""
        assert sanitize_subfolder_name(None) == ""


class TestSuggestClientSubfolder:
    """Testes para suggest_client_subfolder."""

    def test_suggest_default(self):
        """Testa sugestão com valor padrão."""
        result = suggest_client_subfolder("org123", 456)
        assert result == "GERAL"

    def test_suggest_custom_default(self):
        """Testa sugestão com default customizado."""
        result = suggest_client_subfolder("org123", 456, default="CUSTOM")
        assert result == "CUSTOM"

    def test_suggest_sanitizes(self):
        """Testa que sanitiza o default."""
        result = suggest_client_subfolder("org123", 456, default="Nome Com Espaços")
        assert result == "NomeComEspacos"


class TestListStorageSubfolders:
    """Testes para list_storage_subfolders."""

    def test_list_empty(self):
        """Testa listagem vazia."""
        mock_client = MagicMock()
        mock_client.list.return_value = []

        result = list_storage_subfolders(mock_client, "org123/client456/")
        assert result == []

    def test_list_with_folders(self):
        """Testa listagem com pastas."""
        mock_client = MagicMock()
        mock_client.list.return_value = [
            {"name": "org123/client456/GERAL/"},
            {"name": "org123/client456/SIFAP/"},
            {"name": "org123/client456/ANVISA/"},
        ]

        result = list_storage_subfolders(mock_client, "org123/client456/")
        assert result == ["ANVISA", "GERAL", "SIFAP"]  # ordenado

    def test_list_handles_exception(self):
        """Testa tratamento de exceção."""
        mock_client = MagicMock()
        mock_client.list.side_effect = Exception("Storage error")

        result = list_storage_subfolders(mock_client, "org123/client456/")
        assert result == []


class TestGetMandatorySubfolderNames:
    """Testes para get_mandatory_subfolder_names."""

    def test_get_mandatory(self):
        """Testa retorno de subpastas obrigatórias."""
        result = get_mandatory_subfolder_names()
        assert isinstance(result, tuple)
        assert "SIFAP" in result
        assert "ANVISA" in result
        assert "FARMACIA_POPULAR" in result
        assert "AUDITORIA" in result


class TestBuildStoragePath:
    """Testes para build_storage_path."""

    def test_build_without_subfolder(self):
        """Testa construção sem subpasta."""
        result = build_storage_path("org123", 456)
        assert result == "org123/client456/"

    def test_build_with_subfolder(self):
        """Testa construção com subpasta."""
        result = build_storage_path("org123", 456, "GERAL")
        assert result == "org123/client456/GERAL/"

    def test_build_sanitizes_subfolder(self):
        """Testa que sanitiza subpasta."""
        result = build_storage_path("org123", 456, "Nome Com Espaços")
        assert result == "org123/client456/NomeComEspacos/"
