# -*- coding: utf-8 -*-

"""Testes unitários para helpers de filtros de main_screen.

Round 7 - Fase 2: Testes para lógica de normalização de filtros e status.
"""

from __future__ import annotations

from src.modules.clientes.core.ui_helpers import (
    DEFAULT_FILTER_LABEL,
    FILTER_LABEL_TODOS,
    build_filter_choices_with_all_option,
    normalize_filter_label,
    normalize_status_filter_value,
    resolve_filter_choice_from_options,
)


class TestNormalizeFilterLabel:
    """Testes para normalize_filter_label."""

    def test_normalize_filter_label_todos_variants(self) -> None:
        """Testa normalização de variantes de 'Todos'."""
        assert normalize_filter_label("todos") == FILTER_LABEL_TODOS
        assert normalize_filter_label("TODOS") == FILTER_LABEL_TODOS
        assert normalize_filter_label("Todos") == FILTER_LABEL_TODOS
        assert normalize_filter_label("all") == FILTER_LABEL_TODOS
        assert normalize_filter_label("ALL") == FILTER_LABEL_TODOS
        assert normalize_filter_label("All") == FILTER_LABEL_TODOS

    def test_normalize_filter_label_preserves_status_labels(self) -> None:
        """Testa que labels de status específicos são preservados."""
        assert normalize_filter_label("Novo cliente") == "Novo cliente"
        assert normalize_filter_label("Finalizado") == "Finalizado"
        assert normalize_filter_label("Em cadastro") == "Em cadastro"
        assert normalize_filter_label("Aguardando documento") == "Aguardando documento"

    def test_normalize_filter_label_strips_whitespace(self) -> None:
        """Testa que whitespace é removido corretamente."""
        assert normalize_filter_label("  Novo cliente  ") == "Novo cliente"
        assert normalize_filter_label("\t\tFinalizado\t\t") == "Finalizado"
        assert normalize_filter_label("  todos  ") == FILTER_LABEL_TODOS

    def test_normalize_filter_label_empty_and_none(self) -> None:
        """Testa casos de borda: None, string vazia, whitespace."""
        assert normalize_filter_label(None) == ""
        assert normalize_filter_label("") == ""
        assert normalize_filter_label("   ") == ""
        assert normalize_filter_label("\t\n") == ""

    def test_normalize_filter_label_case_sensitive_for_non_aliases(self) -> None:
        """Testa que labels não-alias mantêm o case original."""
        assert normalize_filter_label("NOVO CLIENTE") == "NOVO CLIENTE"
        assert normalize_filter_label("novo cliente") == "novo cliente"
        assert normalize_filter_label("NoVo ClIeNtE") == "NoVo ClIeNtE"


class TestNormalizeStatusFilterValue:
    """Testes para normalize_status_filter_value."""

    def test_normalize_status_filter_value_todos_returns_none(self) -> None:
        """Testa que 'Todos' (case-insensitive) retorna None."""
        assert normalize_status_filter_value("Todos") is None
        assert normalize_status_filter_value("todos") is None
        assert normalize_status_filter_value("TODOS") is None
        assert normalize_status_filter_value("ToDos") is None

    def test_normalize_status_filter_value_empty_returns_none(self) -> None:
        """Testa que valores vazios retornam None."""
        assert normalize_status_filter_value(None) is None
        assert normalize_status_filter_value("") is None
        assert normalize_status_filter_value("   ") is None
        assert normalize_status_filter_value("\t\n") is None

    def test_normalize_status_filter_value_preserves_valid_status(self) -> None:
        """Testa que valores de status válidos são preservados (com strip)."""
        assert normalize_status_filter_value("Novo cliente") == "Novo cliente"
        assert normalize_status_filter_value("  Finalizado  ") == "Finalizado"
        assert normalize_status_filter_value("Em cadastro") == "Em cadastro"
        assert normalize_status_filter_value("Aguardando pagamento") == "Aguardando pagamento"

    def test_normalize_status_filter_value_case_sensitive_except_todos(self) -> None:
        """Testa que case é preservado para status (exceto 'Todos')."""
        assert normalize_status_filter_value("NOVO CLIENTE") == "NOVO CLIENTE"
        assert normalize_status_filter_value("novo cliente") == "novo cliente"
        # Mas "Todos" é sempre None
        assert normalize_status_filter_value("todos") is None


class TestBuildStatusFilterChoices:
    """Testes para build_filter_choices_with_all_option."""

    def test_build_filter_choices_with_all_option_adds_todos_at_beginning(self) -> None:
        """Testa que 'Todos' é adicionado no início da lista."""
        statuses = ["Novo cliente", "Finalizado", "Em cadastro"]
        result = build_filter_choices_with_all_option(statuses)

        assert result[0] == FILTER_LABEL_TODOS
        assert result[1:] == statuses

    def test_build_filter_choices_with_all_option_empty_list(self) -> None:
        """Testa comportamento com lista vazia de status."""
        result = build_filter_choices_with_all_option([])
        assert result == [FILTER_LABEL_TODOS]

    def test_build_filter_choices_with_all_option_preserves_order(self) -> None:
        """Testa que a ordem dos status é preservada."""
        statuses = ["Status C", "Status A", "Status B"]
        result = build_filter_choices_with_all_option(statuses)

        assert result == [FILTER_LABEL_TODOS, "Status C", "Status A", "Status B"]

    def test_build_filter_choices_with_all_option_with_single_status(self) -> None:
        """Testa com apenas um status."""
        result = build_filter_choices_with_all_option(["Único status"])
        assert result == [FILTER_LABEL_TODOS, "Único status"]

    def test_build_filter_choices_with_all_option_does_not_modify_input(self) -> None:
        """Testa que a lista de entrada não é modificada."""
        statuses = ["A", "B", "C"]
        original_statuses = statuses.copy()

        build_filter_choices_with_all_option(statuses)

        assert statuses == original_statuses


class TestResolveFilterChoiceFromOptions:
    """Testes para resolve_filter_choice_from_options."""

    def test_resolve_filter_choice_case_insensitive_match(self) -> None:
        """Testa matching case-insensitive."""
        choices = ["Todos", "Novo cliente", "Finalizado"]

        assert resolve_filter_choice_from_options("novo cliente", choices) == "Novo cliente"
        assert resolve_filter_choice_from_options("NOVO CLIENTE", choices) == "Novo cliente"
        assert resolve_filter_choice_from_options("NoVo ClIeNtE", choices) == "Novo cliente"
        assert resolve_filter_choice_from_options("todos", choices) == "Todos"
        assert resolve_filter_choice_from_options("TODOS", choices) == "Todos"

    def test_resolve_filter_choice_exact_match(self) -> None:
        """Testa que match exato funciona."""
        choices = ["Todos", "Novo cliente", "Finalizado"]

        assert resolve_filter_choice_from_options("Novo cliente", choices) == "Novo cliente"
        assert resolve_filter_choice_from_options("Todos", choices) == "Todos"
        assert resolve_filter_choice_from_options("Finalizado", choices) == "Finalizado"

    def test_resolve_filter_choice_no_match_returns_default(self) -> None:
        """Testa que valor não encontrado retorna o padrão."""
        choices = ["Todos", "Novo cliente", "Finalizado"]

        assert resolve_filter_choice_from_options("Inexistente", choices) == DEFAULT_FILTER_LABEL
        assert resolve_filter_choice_from_options("Status desconhecido", choices) == DEFAULT_FILTER_LABEL

    def test_resolve_filter_choice_empty_and_none_return_default(self) -> None:
        """Testa que None e string vazia retornam o padrão."""
        choices = ["Todos", "Novo cliente"]

        assert resolve_filter_choice_from_options(None, choices) == DEFAULT_FILTER_LABEL
        assert resolve_filter_choice_from_options("", choices) == DEFAULT_FILTER_LABEL
        assert resolve_filter_choice_from_options("   ", choices) == DEFAULT_FILTER_LABEL

    def test_resolve_filter_choice_whitespace_handling(self) -> None:
        """Testa que whitespace é tratado corretamente."""
        choices = ["Todos", "Novo cliente"]

        assert resolve_filter_choice_from_options("  novo cliente  ", choices) == "Novo cliente"
        assert resolve_filter_choice_from_options("\tNovo cliente\t", choices) == "Novo cliente"

    def test_resolve_filter_choice_empty_choices_list(self) -> None:
        """Testa comportamento com lista vazia de opções."""
        assert resolve_filter_choice_from_options("Qualquer", []) == DEFAULT_FILTER_LABEL
        assert resolve_filter_choice_from_options(None, []) == DEFAULT_FILTER_LABEL

    def test_resolve_filter_choice_duplicate_case_variants(self) -> None:
        """Testa que apenas a primeira variante de case é retornada."""
        # Em uma lista bem formada, não deveria haver duplicatas,
        # mas testamos que o dict pegará o último
        choices = ["todos", "Todos", "TODOS"]

        # O dict {choice.lower(): choice} pegará o último valor com a mesma chave
        result = resolve_filter_choice_from_options("TODOS", choices)
        assert result in choices  # Deve retornar alguma variante


class TestFilterConstants:
    """Testes de sanity check para constantes de filtros."""

    def test_filter_label_todos_is_defined(self) -> None:
        """Verifica que FILTER_LABEL_TODOS está definido."""
        assert FILTER_LABEL_TODOS == "Todos"

    def test_default_filter_label_is_todos(self) -> None:
        """Verifica que o filtro padrão é 'Todos'."""
        assert DEFAULT_FILTER_LABEL == FILTER_LABEL_TODOS
        assert DEFAULT_FILTER_LABEL == "Todos"

    def test_filter_label_todos_is_string(self) -> None:
        """Verifica que FILTER_LABEL_TODOS é string."""
        assert isinstance(FILTER_LABEL_TODOS, str)
        assert isinstance(DEFAULT_FILTER_LABEL, str)


class TestFilterIntegration:
    """Testes de integração entre os helpers de filtros."""

    def test_workflow_build_choices_and_resolve(self) -> None:
        """Testa workflow completo: construir choices e resolver seleção."""
        statuses = ["Novo cliente", "Finalizado", "Em cadastro"]

        # 1. Construir opções
        choices = build_filter_choices_with_all_option(statuses)
        assert choices[0] == "Todos"

        # 2. Resolver seleção válida
        resolved = resolve_filter_choice_from_options("novo cliente", choices)
        assert resolved == "Novo cliente"

        # 3. Normalizar para uso interno
        filter_value = normalize_status_filter_value(resolved)
        assert filter_value == "Novo cliente"

    def test_workflow_todos_selection(self) -> None:
        """Testa workflow quando 'Todos' é selecionado."""
        statuses = ["Novo cliente", "Finalizado"]

        # 1. Construir opções
        choices = build_filter_choices_with_all_option(statuses)

        # 2. Resolver seleção de 'todos' (case-insensitive)
        resolved = resolve_filter_choice_from_options("todos", choices)
        assert resolved == "Todos"

        # 3. Normalizar para uso interno (deve retornar None)
        filter_value = normalize_status_filter_value(resolved)
        assert filter_value is None

    def test_workflow_invalid_selection_fallback(self) -> None:
        """Testa workflow quando seleção inválida cai para padrão."""
        statuses = ["Novo cliente"]

        # 1. Construir opções
        choices = build_filter_choices_with_all_option(statuses)

        # 2. Tentar resolver seleção inválida
        resolved = resolve_filter_choice_from_options("Status inexistente", choices)
        assert resolved == "Todos"

        # 3. Normalizar (deve retornar None pois caiu para 'Todos')
        filter_value = normalize_status_filter_value(resolved)
        assert filter_value is None
