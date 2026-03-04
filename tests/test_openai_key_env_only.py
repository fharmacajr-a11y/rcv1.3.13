# -*- coding: utf-8 -*-
"""Testes para PR8 — OpenAI key somente via variável de ambiente."""

from __future__ import annotations

import os
from unittest import mock

import pytest

from src.modules.chatgpt.service import get_openai_api_key


# ═══════════════════════════════════════════════════════════════════════════
# get_openai_api_key(): com e sem env var
# ═══════════════════════════════════════════════════════════════════════════


class TestGetOpenaiApiKey:
    """Verifica que a chave vem SOMENTE de OPENAI_API_KEY."""

    def test_returns_key_when_env_is_set(self) -> None:
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-123"}):
            assert get_openai_api_key() == "sk-test-123"

    def test_strips_whitespace(self) -> None:
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "  sk-test-456  "}):
            assert get_openai_api_key() == "sk-test-456"

    def test_raises_when_env_not_set(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError, match="OPENAI_API_KEY não está definida"):
                get_openai_api_key()

    def test_raises_when_env_is_empty(self) -> None:
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            with pytest.raises(RuntimeError, match="OPENAI_API_KEY não está definida"):
                get_openai_api_key()

    def test_raises_when_env_is_whitespace_only(self) -> None:
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "   "}):
            with pytest.raises(RuntimeError, match="OPENAI_API_KEY não está definida"):
                get_openai_api_key()

    def test_error_message_includes_instructions(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError, match=r"PowerShell.*\$env:OPENAI_API_KEY"):
                get_openai_api_key()


# ═══════════════════════════════════════════════════════════════════════════
# Garantir que NENHUM arquivo é aberto para ler chave
# ═══════════════════════════════════════════════════════════════════════════


class TestNoFileAccess:
    """Verifica que o módulo NÃO tenta ler chave de arquivo."""

    def test_does_not_open_any_file_when_env_set(self) -> None:
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-ok"}):
            with mock.patch("builtins.open", side_effect=AssertionError("open() não deveria ser chamado")):
                result = get_openai_api_key()
                assert result == "sk-ok"

    def test_does_not_open_any_file_when_env_missing(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch("builtins.open", side_effect=AssertionError("open() não deveria ser chamado")):
                with pytest.raises(RuntimeError):
                    get_openai_api_key()

    def test_no_file_path_constants_in_module(self) -> None:
        """Confirma que não existem constantes de caminho de arquivo de chave no módulo."""
        import src.modules.chatgpt.service as svc

        # Não deve existir referência a arquivo de key
        assert not hasattr(svc, "OPENAI_KEY_FILE")
        assert not hasattr(svc, "BASE_DIR")

    def test_no_pathlib_import(self) -> None:
        """O módulo não deveria mais importar pathlib (era usado apenas para OPENAI_KEY_FILE)."""
        import src.modules.chatgpt.service as svc

        source = open(svc.__file__, "r", encoding="utf-8").read()
        # pathlib não deve ser importado no módulo
        assert "from pathlib" not in source
        assert "import pathlib" not in source
