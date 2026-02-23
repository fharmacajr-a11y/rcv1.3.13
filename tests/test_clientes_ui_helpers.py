# pyright: reportAttributeAccessIssue=false
# -*- coding: utf-8 -*-
"""Testes para helpers de UI do módulo Clientes."""

import pytest


class TestFirstLinePreview:
    """Testes para _first_line_preview() da view de clientes."""

    @staticmethod
    def _first_line_preview(text: str | None, max_len: int = 40) -> str:
        """Cópia do método para testes isolados."""
        if not text:
            return ""

        normalized = str(text).replace("\r\n", "\n").replace("\r", "\n")
        lines = normalized.split("\n")
        first_line = lines[0].strip() if lines else ""
        has_more_lines = len(lines) > 1 and any(line.strip() for line in lines[1:])

        if len(first_line) > max_len:
            return first_line[: max_len - 1].rstrip() + "…"
        elif has_more_lines:
            return first_line + "…" if first_line else ""
        else:
            return first_line

    def test_empty_text(self):
        """Texto vazio retorna vazio."""
        assert self._first_line_preview("") == ""
        assert self._first_line_preview(None) == ""

    def test_single_line_short(self):
        """Linha única curta retorna sem modificação."""
        assert self._first_line_preview("Cliente ativo") == "Cliente ativo"

    def test_single_line_exact_max(self):
        """Linha única no limite exato não trunca."""
        text = "A" * 40
        assert self._first_line_preview(text, max_len=40) == text

    def test_single_line_over_max(self):
        """Linha única longa é truncada com …"""
        text = "A" * 50
        result = self._first_line_preview(text, max_len=40)
        assert result == "A" * 39 + "…"
        assert len(result) == 40

    def test_multiple_lines_adds_ellipsis(self):
        """Múltiplas linhas adiciona … na primeira."""
        text = "Primeira linha\nSegunda linha"
        assert self._first_line_preview(text) == "Primeira linha…"

    def test_multiple_lines_empty_second(self):
        """Segunda linha vazia não conta como 'mais conteúdo'."""
        text = "Primeira linha\n\n"
        assert self._first_line_preview(text) == "Primeira linha"

    def test_multiple_lines_long_first(self):
        """Primeira linha longa com mais linhas: trunca com …"""
        text = "A" * 50 + "\nSegunda linha"
        result = self._first_line_preview(text, max_len=40)
        assert result == "A" * 39 + "…"

    def test_crlf_normalization(self):
        """Normaliza \\r\\n para \\n."""
        text = "Linha 1\r\nLinha 2"
        assert self._first_line_preview(text) == "Linha 1…"

    def test_cr_normalization(self):
        """Normaliza \\r para \\n."""
        text = "Linha 1\rLinha 2"
        assert self._first_line_preview(text) == "Linha 1…"

    def test_whitespace_stripped(self):
        """Espaços são removidos da primeira linha."""
        text = "  Texto com espaços  \nOutra linha"
        assert self._first_line_preview(text) == "Texto com espaços…"


class TestOneLine:
    """Testes para _one_line() (sanitização legada)."""

    @staticmethod
    def _one_line(text: str | None) -> str:
        """Cópia do método para testes isolados."""
        if not text:
            return ""
        return " ".join(str(text).replace("\r", " ").replace("\n", " ").split())

    def test_empty(self):
        assert self._one_line("") == ""
        assert self._one_line(None) == ""

    def test_single_line(self):
        assert self._one_line("Texto simples") == "Texto simples"

    def test_multiple_lines_joined(self):
        assert self._one_line("Linha 1\nLinha 2") == "Linha 1 Linha 2"

    def test_multiple_spaces_collapsed(self):
        assert self._one_line("Texto   com    espaços") == "Texto com espaços"

    def test_mixed_newlines(self):
        assert self._one_line("A\r\nB\rC\nD") == "A B C D"
