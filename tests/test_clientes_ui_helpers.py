# pyright: reportAttributeAccessIssue=false
# -*- coding: utf-8 -*-
"""Testes para helpers de UI do módulo Clientes.

Importa _first_line_preview e _one_line **diretamente do código-fonte real**
(são @staticmethod da classe na view.py) via AST — sem carregar o módulo
inteiro, que depende de Tk/CTk.
"""

from pathlib import Path

from conftest import extract_functions_from_source

_SRC_FILE = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "modules"
    / "clientes"
    / "ui"
    / "view.py"
)

# Buscar qual classe contém os métodos
import ast as _ast

_tree = _ast.parse(_SRC_FILE.read_text(encoding="utf-8"))
_view_class_name: str | None = None
for _node in _ast.iter_child_nodes(_tree):
    if isinstance(_node, _ast.ClassDef):
        for _body in _node.body:
            if isinstance(_body, _ast.FunctionDef) and _body.name == "_one_line":
                _view_class_name = _node.name
                break
        if _view_class_name:
            break

assert _view_class_name is not None, "_one_line not found in any class in view.py"

_fns = extract_functions_from_source(
    _SRC_FILE,
    "_first_line_preview",
    "_one_line",
    class_name=_view_class_name,
)
_first_line_preview = _fns["_first_line_preview"]
_one_line = _fns["_one_line"]


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
