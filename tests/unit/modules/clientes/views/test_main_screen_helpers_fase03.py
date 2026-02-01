"""Testes unitários para main_screen_helpers do módulo clientes - FASE 03.

REFACTOR-UI-007 - Fase 03: Filter Logic
Cobertura: filter_by_status, filter_by_search_text, apply_combined_filters,
           extract_unique_status_values, build_status_filter_choices,
           normalize_status_choice
"""

from __future__ import annotations


from src.modules.clientes.core.ui_helpers import (
    apply_combined_filters,
    build_status_filter_choices,
    extract_unique_status_values,
    filter_by_search_text,
    filter_by_status,
    normalize_status_choice,
)


class TestFilterByStatus:
    """Testes para filtro por status."""

    def test_with_matching_status(self):
        """Deve retornar clientes com status correspondente (case-insensitive)."""
        clients = [
            {"id": "1", "status": "Ativo"},
            {"id": "2", "status": "Inativo"},
            {"id": "3", "status": "Ativo"},
        ]
        result = filter_by_status(clients, "ativo")
        assert len(result) == 2
        assert result[0]["id"] == "1"
        assert result[1]["id"] == "3"

    def test_with_no_filter(self):
        """Deve retornar todos os clientes quando status_filter é None."""
        clients = [
            {"id": "1", "status": "Ativo"},
            {"id": "2", "status": "Inativo"},
        ]
        result = filter_by_status(clients, None)
        assert len(result) == 2

    def test_with_empty_string_filter(self):
        """Deve retornar todos os clientes quando status_filter é string vazia."""
        clients = [{"id": "1", "status": "Ativo"}]
        result = filter_by_status(clients, "")
        assert len(result) == 1

    def test_case_insensitive_match(self):
        """Deve fazer match case-insensitive."""
        clients = [{"id": "1", "status": "Ativo"}]
        result = filter_by_status(clients, "ATIVO")
        assert len(result) == 1
        assert result[0]["id"] == "1"

    def test_no_matches(self):
        """Deve retornar lista vazia quando nenhum cliente corresponde."""
        clients = [{"id": "1", "status": "Ativo"}]
        result = filter_by_status(clients, "Inexistente")
        assert result == []

    def test_empty_clients_list(self):
        """Deve retornar lista vazia para entrada vazia."""
        result = filter_by_status([], "Ativo")
        assert result == []

    def test_clients_with_missing_status_field(self):
        """Deve tratar clientes sem campo 'status'."""
        clients = [
            {"id": "1", "status": "Ativo"},
            {"id": "2"},  # sem status
        ]
        result = filter_by_status(clients, "ativo")
        assert len(result) == 1
        assert result[0]["id"] == "1"

    def test_clients_with_empty_status(self):
        """Deve ignorar clientes com status vazio."""
        clients = [
            {"id": "1", "status": "Ativo"},
            {"id": "2", "status": ""},
        ]
        result = filter_by_status(clients, "ativo")
        assert len(result) == 1


class TestFilterBySearchText:
    """Testes para filtro por texto de busca."""

    def test_with_matching_text(self):
        """Deve retornar clientes contendo o texto (case-insensitive)."""
        clients = [
            {"id": "1", "search_norm": "acme corporation"},
            {"id": "2", "search_norm": "beta industries"},
        ]
        result = filter_by_search_text(clients, "acme")
        assert len(result) == 1
        assert result[0]["id"] == "1"

    def test_with_no_filter(self):
        """Deve retornar todos os clientes quando search_text é None."""
        clients = [{"id": "1", "search_norm": "acme"}]
        result = filter_by_search_text(clients, None)
        assert len(result) == 1

    def test_with_empty_string_filter(self):
        """Deve retornar todos quando search_text é string vazia."""
        clients = [{"id": "1", "search_norm": "acme"}]
        result = filter_by_search_text(clients, "")
        assert len(result) == 1

    def test_case_insensitive_match(self):
        """Deve fazer busca case-insensitive."""
        clients = [{"id": "1", "search_norm": "acme corporation"}]
        result = filter_by_search_text(clients, "ACME")
        assert len(result) == 1

    def test_partial_match(self):
        """Deve fazer match parcial (substring)."""
        clients = [{"id": "1", "search_norm": "acme corporation inc"}]
        result = filter_by_search_text(clients, "corp")
        assert len(result) == 1

    def test_no_matches(self):
        """Deve retornar lista vazia quando nenhum match."""
        clients = [{"id": "1", "search_norm": "acme"}]
        result = filter_by_search_text(clients, "xyz")
        assert result == []

    def test_empty_clients_list(self):
        """Deve retornar lista vazia para entrada vazia."""
        result = filter_by_search_text([], "acme")
        assert result == []

    def test_custom_search_field(self):
        """Deve buscar em campo customizado."""
        clients = [{"id": "1", "nome": "João Silva"}]
        result = filter_by_search_text(clients, "joão", search_field="nome")
        assert len(result) == 1

    def test_missing_search_field(self):
        """Deve ignorar clientes sem o campo de busca."""
        clients = [
            {"id": "1", "search_norm": "acme"},
            {"id": "2"},  # sem search_norm
        ]
        result = filter_by_search_text(clients, "acme")
        assert len(result) == 1


class TestApplyCombinedFilters:
    """Testes para filtros combinados."""

    def test_both_filters_active(self):
        """Deve aplicar status + texto quando ambos fornecidos."""
        clients = [
            {"id": "1", "status": "Ativo", "search_norm": "acme corp"},
            {"id": "2", "status": "Inativo", "search_norm": "beta corp"},
            {"id": "3", "status": "Ativo", "search_norm": "gamma corp"},
        ]
        result = apply_combined_filters(
            clients,
            status_filter="ativo",
            search_text="acme",
        )
        assert len(result) == 1
        assert result[0]["id"] == "1"

    def test_only_status_filter(self):
        """Deve aplicar apenas filtro de status."""
        clients = [
            {"id": "1", "status": "Ativo", "search_norm": "acme"},
            {"id": "2", "status": "Inativo", "search_norm": "beta"},
        ]
        result = apply_combined_filters(clients, status_filter="ativo")
        assert len(result) == 1
        assert result[0]["id"] == "1"

    def test_only_search_text_filter(self):
        """Deve aplicar apenas filtro de texto."""
        clients = [
            {"id": "1", "status": "Ativo", "search_norm": "acme"},
            {"id": "2", "status": "Ativo", "search_norm": "beta"},
        ]
        result = apply_combined_filters(clients, search_text="acme")
        assert len(result) == 1
        assert result[0]["id"] == "1"

    def test_no_filters(self):
        """Deve retornar todos quando nenhum filtro fornecido."""
        clients = [{"id": "1"}, {"id": "2"}]
        result = apply_combined_filters(clients)
        assert len(result) == 2

    def test_no_matches(self):
        """Deve retornar lista vazia quando nenhum match."""
        clients = [{"id": "1", "status": "Ativo", "search_norm": "acme"}]
        result = apply_combined_filters(
            clients,
            status_filter="inativo",
            search_text="beta",
        )
        assert result == []

    def test_custom_search_field(self):
        """Deve usar campo de busca customizado."""
        clients = [
            {"id": "1", "status": "Ativo", "nome": "João"},
            {"id": "2", "status": "Ativo", "nome": "Maria"},
        ]
        result = apply_combined_filters(
            clients,
            status_filter="ativo",
            search_text="joão",
            search_field="nome",
        )
        assert len(result) == 1
        assert result[0]["id"] == "1"


class TestExtractUniqueStatusValues:
    """Testes para extração de status únicos."""

    def test_multiple_clients_unique_statuses(self):
        """Deve retornar lista de status únicos."""
        clients = [
            {"id": "1", "status": "Ativo"},
            {"id": "2", "status": "Inativo"},
            {"id": "3", "status": "Ativo"},
        ]
        result = extract_unique_status_values(clients)
        assert result == ["Ativo", "Inativo"]

    def test_empty_clients_list(self):
        """Deve retornar lista vazia para entrada vazia."""
        result = extract_unique_status_values([])
        assert result == []

    def test_clients_with_empty_status(self):
        """Deve ignorar clientes com status vazio."""
        clients = [
            {"id": "1", "status": "Ativo"},
            {"id": "2", "status": ""},
            {"id": "3", "status": "Inativo"},
        ]
        result = extract_unique_status_values(clients)
        assert result == ["Ativo", "Inativo"]

    def test_case_sensitivity_preservation(self):
        """Deve preservar capitalização original (primeiro encontrado)."""
        clients = [
            {"id": "1", "status": "Ativo"},
            {"id": "2", "status": "ATIVO"},  # mesmo status, case diferente
        ]
        result = extract_unique_status_values(clients)
        assert len(result) == 1
        assert result[0] == "Ativo"  # primeiro encontrado

    def test_sorted_by_default(self):
        """Deve ordenar alfabeticamente por padrão."""
        clients = [
            {"id": "1", "status": "Zebra"},
            {"id": "2", "status": "Alpha"},
            {"id": "3", "status": "Beta"},
        ]
        result = extract_unique_status_values(clients)
        assert result == ["Alpha", "Beta", "Zebra"]

    def test_unsorted_when_requested(self):
        """Deve preservar ordem de inserção quando sort=False."""
        clients = [
            {"id": "1", "status": "Zebra"},
            {"id": "2", "status": "Alpha"},
        ]
        result = extract_unique_status_values(clients, sort=False)
        assert result == ["Zebra", "Alpha"]

    def test_clients_without_status_field(self):
        """Deve ignorar clientes sem campo 'status'."""
        clients = [
            {"id": "1", "status": "Ativo"},
            {"id": "2"},  # sem status
        ]
        result = extract_unique_status_values(clients)
        assert result == ["Ativo"]


class TestBuildStatusFilterChoices:
    """Testes para construção de opções de filtro."""

    def test_with_all_option(self):
        """Deve incluir 'Todos' no início por padrão."""
        clients = [
            {"status": "Ativo"},
            {"status": "Inativo"},
        ]
        result = build_status_filter_choices(clients)
        assert result == ["Todos", "Ativo", "Inativo"]

    def test_without_all_option(self):
        """Deve omitir 'Todos' quando include_all_option=False."""
        clients = [{"status": "Ativo"}]
        result = build_status_filter_choices(clients, include_all_option=False)
        assert result == ["Ativo"]

    def test_custom_all_option_label(self):
        """Deve usar label customizado para 'todos'."""
        clients = [{"status": "Ativo"}]
        result = build_status_filter_choices(clients, all_option_label="All")
        assert result == ["All", "Ativo"]

    def test_empty_clients_list(self):
        """Deve retornar apenas 'Todos' para lista vazia."""
        result = build_status_filter_choices([])
        assert result == ["Todos"]

    def test_sorted_statuses(self):
        """Deve ordenar status alfabeticamente."""
        clients = [
            {"status": "Zebra"},
            {"status": "Alpha"},
        ]
        result = build_status_filter_choices(clients)
        assert result == ["Todos", "Alpha", "Zebra"]


class TestNormalizeStatusChoice:
    """Testes para normalização de escolha de status."""

    def test_exact_match(self):
        """Deve retornar a versão exata quando há match."""
        result = normalize_status_choice(
            "Ativo",
            ["Todos", "Ativo", "Inativo"],
        )
        assert result == "Ativo"

    def test_case_insensitive_match(self):
        """Deve fazer match case-insensitive."""
        result = normalize_status_choice(
            "ativo",
            ["Todos", "Ativo", "Inativo"],
        )
        assert result == "Ativo"

    def test_invalid_choice_returns_default(self):
        """Deve retornar all_option_label para escolha inválida."""
        result = normalize_status_choice(
            "Inexistente",
            ["Todos", "Ativo"],
        )
        assert result == "Todos"

    def test_none_choice_returns_default(self):
        """Deve retornar all_option_label quando choice é None."""
        result = normalize_status_choice(None, ["Todos", "Ativo"])
        assert result == "Todos"

    def test_empty_string_choice_returns_default(self):
        """Deve retornar all_option_label quando choice é string vazia."""
        result = normalize_status_choice("", ["Todos", "Ativo"])
        assert result == "Todos"

    def test_custom_all_option_label(self):
        """Deve usar all_option_label customizado."""
        result = normalize_status_choice(
            "Inexistente",
            ["All", "Ativo"],
            all_option_label="All",
        )
        assert result == "All"

    def test_whitespace_choice(self):
        """Deve tratar espaços como string vazia."""
        result = normalize_status_choice("   ", ["Todos", "Ativo"])
        assert result == "Todos"


# Testes de integração


class TestFilterWorkflows:
    """Testes de workflows completos de filtros."""

    def test_build_and_normalize_workflow(self):
        """Simula workflow de popular combobox e normalizar escolha."""
        clients = [
            {"status": "Ativo"},
            {"status": "Inativo"},
            {"status": "Pendente"},
        ]

        # 1. Construir opções
        choices = build_status_filter_choices(clients)
        assert choices == ["Todos", "Ativo", "Inativo", "Pendente"]

        # 2. Normalizar escolha do usuário (case diferente)
        normalized = normalize_status_choice("ativo", choices)
        assert normalized == "Ativo"

        # 3. Filtrar usando escolha normalizada
        if normalized != "Todos":
            result = filter_by_status(clients, normalized)
            assert len(result) == 1
            assert result[0]["status"] == "Ativo"

    def test_combined_filter_workflow(self):
        """Simula workflow completo: status + busca."""
        clients = [
            {"id": "1", "status": "Ativo", "search_norm": "acme corp"},
            {"id": "2", "status": "Ativo", "search_norm": "beta corp"},
            {"id": "3", "status": "Inativo", "search_norm": "acme industries"},
        ]

        # Usuário escolhe "Ativo" e busca "acme"
        filtered = apply_combined_filters(
            clients,
            status_filter="ativo",
            search_text="acme",
        )

        assert len(filtered) == 1
        assert filtered[0]["id"] == "1"

    def test_progressive_filtering(self):
        """Testa aplicação progressiva de filtros."""
        clients = [
            {"id": "1", "status": "Ativo", "search_norm": "acme"},
            {"id": "2", "status": "Ativo", "search_norm": "beta"},
            {"id": "3", "status": "Inativo", "search_norm": "acme"},
        ]

        # Primeiro filtro: status
        step1 = filter_by_status(clients, "ativo")
        assert len(step1) == 2

        # Segundo filtro: busca
        step2 = filter_by_search_text(step1, "acme")
        assert len(step2) == 1
        assert step2[0]["id"] == "1"

    def test_extract_and_build_workflow(self):
        """Testa extração de status e construção de choices."""
        clients = [
            {"status": "Zebra"},
            {"status": "Alpha"},
            {"status": "Zebra"},  # duplicado
        ]

        # Extrair únicos
        statuses = extract_unique_status_values(clients)
        assert statuses == ["Alpha", "Zebra"]

        # Construir choices
        choices = build_status_filter_choices(clients)
        assert choices == ["Todos", "Alpha", "Zebra"]

    def test_empty_state_workflow(self):
        """Testa workflow com lista vazia."""
        clients = []

        # Build choices
        choices = build_status_filter_choices(clients)
        assert choices == ["Todos"]

        # Normalize
        normalized = normalize_status_choice("Ativo", choices)
        assert normalized == "Todos"

        # Filter
        result = apply_combined_filters(clients, status_filter="Ativo")
        assert result == []


class TestFilterEdgeCases:
    """Testes de casos extremos de filtros."""

    def test_status_with_special_characters(self):
        """Deve funcionar com status contendo caracteres especiais."""
        clients = [{"id": "1", "status": "Ativo (Principal)"}]
        result = filter_by_status(clients, "ativo (principal)")
        assert len(result) == 1

    def test_search_with_unicode(self):
        """Deve funcionar com texto unicode."""
        clients = [{"id": "1", "search_norm": "josé silva ñoño"}]
        result = filter_by_search_text(clients, "josé")
        assert len(result) == 1

    def test_very_long_client_list(self):
        """Deve funcionar com listas grandes."""
        clients = [{"id": str(i), "status": "Ativo"} for i in range(1000)]
        result = filter_by_status(clients, "Ativo")
        assert len(result) == 1000

    def test_clients_with_none_values(self):
        """Deve tratar valores None graciosamente."""
        clients = [
            {"id": "1", "status": None},
            {"id": "2", "status": "Ativo"},
        ]
        result = filter_by_status(clients, "Ativo")
        assert len(result) == 1

    def test_mixed_data_types(self):
        """Deve converter tipos para string."""
        clients = [{"id": "1", "status": 123}]  # int instead of str
        result = filter_by_status(clients, "123")
        assert len(result) == 1

    def test_filter_order_independence(self):
        """Filtros combinados devem dar mesmo resultado independente da ordem."""
        clients = [
            {"id": "1", "status": "Ativo", "search_norm": "acme"},
            {"id": "2", "status": "Inativo", "search_norm": "beta"},
        ]

        # Ordem 1: status → busca
        result1 = apply_combined_filters(
            clients,
            status_filter="ativo",
            search_text="acme",
        )

        # Ordem 2: busca → status (manual)
        step1 = filter_by_search_text(clients, "acme")
        result2 = filter_by_status(step1, "ativo")

        assert result1 == result2
