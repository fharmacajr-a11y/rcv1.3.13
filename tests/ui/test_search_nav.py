"""Testes unitários para src.ui.search_nav.

Módulo testado: classe SearchNavigator (navegação em texto com highlights).
Cobertura esperada: 100% (~50 linhas, mock de ScrolledText).
"""

from unittest.mock import Mock, MagicMock
import pytest
from src.ui.search_nav import SearchNavigator, HIT_TAG


@pytest.fixture
def mock_text():
    """Cria mock de ScrolledText com métodos necessários."""
    text = MagicMock()
    text.tag_config = Mock()
    text.tag_raise = Mock()
    text.tag_remove = Mock()
    text.tag_add = Mock()
    text.search = Mock()
    text.see = Mock()
    return text


@pytest.fixture
def navigator(mock_text):
    """Cria SearchNavigator com mock de text widget."""
    return SearchNavigator(mock_text)


class TestSearchNavigatorInit:
    """Testes de inicialização do SearchNavigator."""

    def test_init_sets_text_widget(self, mock_text):
        """Inicialização armazena widget e configura tag."""
        nav = SearchNavigator(mock_text)
        assert nav.text is mock_text
        mock_text.tag_config.assert_called_once_with(HIT_TAG, background="#ffd54f")
        mock_text.tag_raise.assert_called_once_with("sel")

    def test_init_state(self, navigator):
        """Estado inicial: query vazia, sem hits, pos -1."""
        assert navigator.query == ""
        assert navigator.hits == []
        assert navigator.pos == -1


class TestSetQuery:
    """Testes de set_query() e reindexação."""

    def test_set_query_empty_string_clears(self, navigator, mock_text):
        """Query vazia limpa hits e remove tags."""
        # Primeiro define query não-vazia
        mock_text.search.return_value = ""
        navigator.set_query("test")
        mock_text.tag_remove.reset_mock()

        # Agora limpa
        navigator.set_query("")
        assert navigator.query == ""
        assert navigator.hits == []
        assert navigator.pos == -1
        mock_text.tag_remove.assert_called_with(HIT_TAG, "1.0", "end")

    def test_set_query_strips_whitespace(self, navigator, mock_text):
        """Query com espaços é normalizada."""
        mock_text.search.return_value = ""  # sem hits
        navigator.set_query("  test  ")
        assert navigator.query == "test"

    def test_set_query_same_value_skips_reindex(self, navigator, mock_text):
        """Definir mesma query não re-indexa."""
        mock_text.search.return_value = ""
        navigator.set_query("foo")
        mock_text.tag_remove.reset_mock()
        mock_text.search.reset_mock()

        navigator.set_query("foo")
        # Não deve chamar tag_remove ou search novamente
        mock_text.tag_remove.assert_not_called()
        mock_text.search.assert_not_called()

    def test_set_query_none_converts_to_empty(self, navigator, mock_text):
        """Query None é tratada como vazia."""
        navigator.set_query(None)
        assert navigator.query == ""
        assert navigator.hits == []


class TestReindex:
    """Testes de _reindex() - busca e highlight."""

    def test_reindex_no_query_clears_all(self, navigator, mock_text):
        """Sem query, limpa tags e hits."""
        navigator.query = ""
        navigator._reindex()
        mock_text.tag_remove.assert_called_with(HIT_TAG, "1.0", "end")
        assert navigator.hits == []
        assert navigator.pos == -1
        mock_text.search.assert_not_called()

    def test_reindex_single_hit(self, navigator, mock_text):
        """Uma ocorrência encontrada."""
        mock_text.search.side_effect = ["1.5", ""]  # encontra em 1.5, depois fim
        navigator.set_query("test")

        assert len(navigator.hits) == 1
        assert navigator.hits[0] == ("1.5", "1.5+4c")  # 'test' tem 4 chars
        mock_text.tag_add.assert_called_once_with(HIT_TAG, "1.5", "1.5+4c")

    def test_reindex_multiple_hits(self, navigator, mock_text):
        """Múltiplas ocorrências encontradas."""
        mock_text.search.side_effect = ["1.0", "2.10", "3.5", ""]
        navigator.set_query("word")

        assert len(navigator.hits) == 3
        assert navigator.hits == [
            ("1.0", "1.0+4c"),
            ("2.10", "2.10+4c"),
            ("3.5", "3.5+4c"),
        ]
        assert mock_text.tag_add.call_count == 3

    def test_reindex_no_hits(self, navigator, mock_text):
        """Nenhuma ocorrência encontrada."""
        mock_text.search.return_value = ""
        navigator.set_query("notfound")

        assert navigator.hits == []
        assert navigator.pos == -1
        mock_text.tag_add.assert_not_called()

    def test_reindex_clears_previous_hits(self, navigator, mock_text):
        """Nova busca limpa hits anteriores."""
        # Primeira busca
        mock_text.search.side_effect = ["1.0", ""]
        navigator.set_query("old")
        assert len(navigator.hits) == 1

        # Segunda busca
        mock_text.search.side_effect = ["2.0", "3.0", ""]
        navigator.set_query("new")
        assert len(navigator.hits) == 2
        assert navigator.hits[0][0] == "2.0"  # hits anteriores foram limpos


class TestGoto:
    """Testes de _goto() - navegação interna."""

    def test_goto_no_hits_does_nothing(self, navigator, mock_text):
        """_goto sem hits não faz nada."""
        navigator._goto(0)
        mock_text.see.assert_not_called()
        mock_text.tag_add.assert_not_called()

    def test_goto_first_hit(self, navigator, mock_text):
        """Navegar para primeira ocorrência."""
        navigator.hits = [("1.0", "1.0+4c"), ("2.0", "2.0+4c")]
        navigator._goto(0)

        assert navigator.pos == 0
        mock_text.see.assert_called_once_with("1.0")
        mock_text.tag_remove.assert_called_with("sel", "1.0", "end")
        mock_text.tag_add.assert_called_with("sel", "1.0", "1.0+4c")

    def test_goto_wraps_around_forward(self, navigator, mock_text):
        """_goto com índice >= len(hits) faz wrap."""
        navigator.hits = [("1.0", "1.0+4c"), ("2.0", "2.0+4c")]
        navigator._goto(2)  # 2 % 2 = 0

        assert navigator.pos == 0
        mock_text.see.assert_called_with("1.0")

    def test_goto_wraps_around_backward(self, navigator, mock_text):
        """_goto com índice negativo faz wrap reverso."""
        navigator.hits = [("1.0", "1.0+4c"), ("2.0", "2.0+4c")]
        navigator._goto(-1)  # -1 % 2 = 1 (último)

        assert navigator.pos == 1
        mock_text.see.assert_called_with("2.0")


class TestNext:
    """Testes de next() - próxima ocorrência."""

    def test_next_no_hits_does_nothing(self, navigator):
        """next() sem hits não faz nada."""
        navigator.next()
        assert navigator.pos == -1

    def test_next_advances_position(self, navigator, mock_text):
        """next() avança para próxima ocorrência."""
        navigator.hits = [("1.0", "1.0+4c"), ("2.0", "2.0+4c"), ("3.0", "3.0+4c")]
        navigator.pos = 0

        navigator.next()
        assert navigator.pos == 1
        mock_text.see.assert_called_with("2.0")

    def test_next_wraps_to_beginning(self, navigator, mock_text):
        """next() no último item volta para o primeiro."""
        navigator.hits = [("1.0", "1.0+4c"), ("2.0", "2.0+4c")]
        navigator.pos = 1

        navigator.next()
        assert navigator.pos == 0
        mock_text.see.assert_called_with("1.0")

    def test_next_from_initial_state(self, navigator, mock_text):
        """next() a partir de pos=-1 vai para primeiro."""
        navigator.hits = [("1.0", "1.0+4c"), ("2.0", "2.0+4c")]

        navigator.next()
        assert navigator.pos == 0


class TestPrev:
    """Testes de prev() - ocorrência anterior."""

    def test_prev_no_hits_does_nothing(self, navigator):
        """prev() sem hits não faz nada."""
        navigator.prev()
        assert navigator.pos == -1

    def test_prev_goes_backward(self, navigator, mock_text):
        """prev() volta para ocorrência anterior."""
        navigator.hits = [("1.0", "1.0+4c"), ("2.0", "2.0+4c"), ("3.0", "3.0+4c")]
        navigator.pos = 2

        navigator.prev()
        assert navigator.pos == 1
        mock_text.see.assert_called_with("2.0")

    def test_prev_wraps_to_end(self, navigator, mock_text):
        """prev() no primeiro item volta para o último."""
        navigator.hits = [("1.0", "1.0+4c"), ("2.0", "2.0+4c")]
        navigator.pos = 0

        navigator.prev()
        assert navigator.pos == 1
        mock_text.see.assert_called_with("2.0")

    def test_prev_from_initial_state(self, navigator, mock_text):
        """prev() a partir de pos=-1 vai para o penúltimo (wrap)."""
        navigator.hits = [("1.0", "1.0+4c"), ("2.0", "2.0+4c")]

        navigator.prev()
        # pos = -1, _goto(-1 - 1) = _goto(-2), -2 % 2 = 0
        assert navigator.pos == 0


class TestIntegrationScenarios:
    """Testes de cenários integrados."""

    def test_full_search_cycle(self, navigator, mock_text):
        """Ciclo completo: buscar, navegar, rebuscar."""
        # Busca inicial
        mock_text.search.side_effect = ["1.0", "2.0", ""]
        navigator.set_query("test")
        assert len(navigator.hits) == 2

        # Navegar
        navigator.next()
        assert navigator.pos == 0
        navigator.next()
        assert navigator.pos == 1
        navigator.next()  # wrap
        assert navigator.pos == 0

        # Nova busca
        mock_text.search.side_effect = ["5.0", ""]
        navigator.set_query("other")
        assert len(navigator.hits) == 1
        assert navigator.pos == -1  # reset após nova busca
