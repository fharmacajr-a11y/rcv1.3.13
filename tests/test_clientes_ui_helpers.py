# pyright: reportAttributeAccessIssue=false
# -*- coding: utf-8 -*-
"""Testes para helpers de UI do módulo Clientes.

Importa first_line_preview e one_line diretamente de column_layout,
onde foram extraídas de ClientesV2Frame como funções de módulo puras.
"""

from src.modules.clientes.ui.column_layout import (
    first_line_preview as _first_line_preview,
    one_line as _one_line,
)


class TestFirstLinePreview:
    """Testes para _first_line_preview() da view de clientes."""

    def test_empty_text(self):
        """Texto vazio retorna vazio."""
        assert _first_line_preview("") == ""
        assert _first_line_preview(None) == ""

    def test_single_line_short(self):
        """Linha única curta retorna sem modificação."""
        assert _first_line_preview("Cliente ativo") == "Cliente ativo"

    def test_single_line_exact_max(self):
        """Linha única no limite exato não trunca."""
        text = "A" * 40
        assert _first_line_preview(text, max_len=40) == text

    def test_single_line_over_max(self):
        """Linha única longa é truncada com …"""
        text = "A" * 50
        result = _first_line_preview(text, max_len=40)
        assert result == "A" * 39 + "…"
        assert len(result) == 40

    def test_multiple_lines_adds_ellipsis(self):
        """Múltiplas linhas adiciona … na primeira."""
        text = "Primeira linha\nSegunda linha"
        assert _first_line_preview(text) == "Primeira linha…"

    def test_multiple_lines_empty_second(self):
        """Segunda linha vazia não conta como 'mais conteúdo'."""
        text = "Primeira linha\n\n"
        assert _first_line_preview(text) == "Primeira linha"

    def test_multiple_lines_long_first(self):
        """Primeira linha longa com mais linhas: trunca com …"""
        text = "A" * 50 + "\nSegunda linha"
        result = _first_line_preview(text, max_len=40)
        assert result == "A" * 39 + "…"

    def test_crlf_normalization(self):
        """Normaliza \\r\\n para \\n."""
        text = "Linha 1\r\nLinha 2"
        assert _first_line_preview(text) == "Linha 1…"

    def test_cr_normalization(self):
        """Normaliza \\r para \\n."""
        text = "Linha 1\rLinha 2"
        assert _first_line_preview(text) == "Linha 1…"

    def test_whitespace_stripped(self):
        """Espaços são removidos da primeira linha."""
        text = "  Texto com espaços  \nOutra linha"
        assert _first_line_preview(text) == "Texto com espaços…"


class TestOneLine:
    """Testes para _one_line() (sanitização legada)."""

    def test_empty(self):
        assert _one_line("") == ""
        assert _one_line(None) == ""

    def test_single_line(self):
        assert _one_line("Texto simples") == "Texto simples"

    def test_multiple_lines_joined(self):
        assert _one_line("Linha 1\nLinha 2") == "Linha 1 Linha 2"

    def test_multiple_spaces_collapsed(self):
        assert _one_line("Texto   com    espaços") == "Texto com espaços"

    def test_mixed_newlines(self):
        assert _one_line("A\r\nB\rC\nD") == "A B C D"
