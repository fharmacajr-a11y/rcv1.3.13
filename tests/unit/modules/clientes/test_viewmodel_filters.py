"""Testes unit\u00e1rios para l\u00f3gica de filtros no ClientesViewModel.

MICROFASE 03 - Round 3: Testes de integra\u00e7\u00e3o dos filtros
Cobertura: set_search_text, set_status_filter, _rebuild_rows (filtragem)
"""

from __future__ import annotations

import pytest

from src.modules.clientes.viewmodel import ClienteRow, ClientesViewModel


@pytest.fixture
def sample_clientes_data():
    """Fixture com dados de clientes para testes."""
    return [
        {
            "id": "1",
            "razao_social": "ACME Corporation",
            "cnpj": "12345678000190",
            "nome": "Jo\u00e3o Silva",
            "whatsapp": "11999998888",
            "observacoes": "[Ativo] Cliente priorit\u00e1rio",
            "ultima_alteracao": "2025-11-28T10:00:00",
            "ultima_por": "user1",
        },
        {
            "id": "2",
            "razao_social": "Beta Industries",
            "cnpj": "98765432000110",
            "nome": "Maria Santos",
            "whatsapp": "11988887777",
            "observacoes": "[Inativo] Sem demanda",
            "ultima_alteracao": "2025-11-27T15:30:00",
            "ultima_por": "user2",
        },
        {
            "id": "3",
            "razao_social": "Gamma Corp",
            "cnpj": "11122233000144",
            "nome": "Pedro Costa",
            "whatsapp": "11977776666",
            "observacoes": "[Ativo] Novo cliente",
            "ultima_alteracao": "2025-11-29T08:00:00",
            "ultima_por": "user1",
        },
    ]


class TestViewModelSearchTextFilter:
    """Testes para filtro de texto de busca no ViewModel."""

    def test_set_search_text_filters_by_normalized_text(self, sample_clientes_data):
        """Deve filtrar clientes por texto de busca normalizado."""
        vm = ClientesViewModel()
        vm.load_from_iterable(sample_clientes_data)

        # Buscar por "acme" (case-insensitive)
        vm.set_search_text("acme")
        rows = vm.get_rows()

        assert len(rows) == 1
        assert rows[0].id == "1"
        assert "ACME" in rows[0].razao_social

    def test_set_search_text_case_insensitive(self, sample_clientes_data):
        """Deve fazer busca case-insensitive."""
        vm = ClientesViewModel()
        vm.load_from_iterable(sample_clientes_data)

        vm.set_search_text("BETA")
        rows = vm.get_rows()

        assert len(rows) == 1
        assert rows[0].id == "2"

    def test_set_search_text_partial_match(self, sample_clientes_data):
        """Deve fazer match parcial (substring)."""
        vm = ClientesViewModel()
        vm.load_from_iterable(sample_clientes_data)

        vm.set_search_text("corp")
        rows = vm.get_rows()

        # Deve encontrar "ACME Corporation" e "Gamma Corp"
        assert len(rows) == 2
        ids = {row.id for row in rows}
        assert ids == {"1", "3"}

    def test_set_search_text_empty_returns_all(self, sample_clientes_data):
        """Deve retornar todos os clientes quando busca \u00e9 vazia."""
        vm = ClientesViewModel()
        vm.load_from_iterable(sample_clientes_data)

        vm.set_search_text("")
        rows = vm.get_rows()

        assert len(rows) == 3

    def test_set_search_text_none_returns_all(self, sample_clientes_data):
        """Deve retornar todos os clientes quando busca \u00e9 None."""
        vm = ClientesViewModel()
        vm.load_from_iterable(sample_clientes_data)

        vm.set_search_text(None)  # type: ignore
        rows = vm.get_rows()

        assert len(rows) == 3

    def test_set_search_text_no_matches(self, sample_clientes_data):
        """Deve retornar lista vazia quando nenhum match."""
        vm = ClientesViewModel()
        vm.load_from_iterable(sample_clientes_data)

        vm.set_search_text("xyz123nonexistent")
        rows = vm.get_rows()

        assert len(rows) == 0

    def test_set_search_text_searches_multiple_fields(self, sample_clientes_data):
        """Deve buscar em m\u00faltiplos campos (nome, raz\u00e3o, CNPJ, etc.)."""
        vm = ClientesViewModel()
        vm.load_from_iterable(sample_clientes_data)

        # Buscar por nome
        vm.set_search_text("jo\u00e3o")
        rows = vm.get_rows()
        assert len(rows) == 1
        assert rows[0].id == "1"

        # Buscar por CNPJ parcial
        vm.set_search_text("12345")
        rows = vm.get_rows()
        assert len(rows) == 1
        assert rows[0].id == "1"

        # Buscar por observa\u00e7\u00e3o
        vm.set_search_text("priorit\u00e1rio")
        rows = vm.get_rows()
        assert len(rows) == 1
        assert rows[0].id == "1"

    def test_set_search_text_with_rebuild_false(self, sample_clientes_data):
        """Deve apenas armazenar texto sem reconstruir quando rebuild=False."""
        vm = ClientesViewModel()
        vm.load_from_iterable(sample_clientes_data)

        # Buscar sem rebuild
        vm.set_search_text("acme", rebuild=False)

        # Rows ainda devem ter todos os 3 clientes (n\u00e3o foi filtrado)
        rows = vm.get_rows()
        assert len(rows) == 3

        # Mas o texto de busca foi armazenado
        assert vm._search_text_raw == "acme"


class TestViewModelStatusFilter:
    """Testes para filtro de status no ViewModel."""

    def test_set_status_filter_filters_by_status(self, sample_clientes_data):
        """Deve filtrar clientes por status."""
        vm = ClientesViewModel()
        vm.load_from_iterable(sample_clientes_data)

        vm.set_status_filter("Ativo")
        rows = vm.get_rows()

        assert len(rows) == 2
        ids = {row.id for row in rows}
        assert ids == {"1", "3"}

    def test_set_status_filter_case_insensitive(self, sample_clientes_data):
        """Deve fazer filtro case-insensitive."""
        vm = ClientesViewModel()
        vm.load_from_iterable(sample_clientes_data)

        vm.set_status_filter("inativo")
        rows = vm.get_rows()

        assert len(rows) == 1
        assert rows[0].id == "2"

    def test_set_status_filter_none_returns_all(self, sample_clientes_data):
        """Deve retornar todos quando status \u00e9 None."""
        vm = ClientesViewModel()
        vm.load_from_iterable(sample_clientes_data)

        vm.set_status_filter(None)
        rows = vm.get_rows()

        assert len(rows) == 3

    def test_set_status_filter_empty_string_returns_all(self, sample_clientes_data):
        """Deve retornar todos quando status \u00e9 string vazia."""
        vm = ClientesViewModel()
        vm.load_from_iterable(sample_clientes_data)

        vm.set_status_filter("")
        rows = vm.get_rows()

        assert len(rows) == 3

    def test_set_status_filter_with_rebuild_false(self, sample_clientes_data):
        """Deve apenas armazenar status sem reconstruir quando rebuild=False."""
        vm = ClientesViewModel()
        vm.load_from_iterable(sample_clientes_data)

        vm.set_status_filter("Ativo", rebuild=False)

        # Rows ainda devem ter todos os 3 clientes
        rows = vm.get_rows()
        assert len(rows) == 3

        # Mas o status foi armazenado
        assert vm._status_filter == "Ativo"


class TestViewModelCombinedFilters:
    """Testes para combina\u00e7\u00e3o de filtros no ViewModel."""

    def test_search_text_and_status_filter_combined(self, sample_clientes_data):
        """Deve combinar filtro de texto e status."""
        vm = ClientesViewModel()
        vm.load_from_iterable(sample_clientes_data)

        # Filtrar por status "Ativo" e buscar "corp"
        vm.set_status_filter("Ativo")
        vm.set_search_text("corp")
        rows = vm.get_rows()

        # Deve retornar apenas clientes ativos com "corp" no nome
        assert len(rows) == 2
        ids = {row.id for row in rows}
        assert ids == {"1", "3"}

    def test_filters_applied_in_sequence(self, sample_clientes_data):
        """Deve aplicar filtros em sequ\u00eancia corretamente."""
        vm = ClientesViewModel()
        vm.load_from_iterable(sample_clientes_data)

        # Primeiro filtro: status
        vm.set_status_filter("Ativo")
        rows = vm.get_rows()
        assert len(rows) == 2

        # Segundo filtro: busca
        vm.set_search_text("gamma")
        rows = vm.get_rows()
        assert len(rows) == 1
        assert rows[0].id == "3"

    def test_removing_filters_restores_full_list(self, sample_clientes_data):
        """Deve restaurar lista completa ao remover filtros."""
        vm = ClientesViewModel()
        vm.load_from_iterable(sample_clientes_data)

        # Aplicar filtros
        vm.set_status_filter("Ativo")
        vm.set_search_text("acme")
        assert len(vm.get_rows()) == 1

        # Remover filtro de busca
        vm.set_search_text("")
        rows = vm.get_rows()
        assert len(rows) == 2  # Todos os ativos

        # Remover filtro de status
        vm.set_status_filter(None)
        rows = vm.get_rows()
        assert len(rows) == 3  # Todos

    def test_no_matches_with_combined_filters(self, sample_clientes_data):
        """Deve retornar lista vazia quando filtros combinados n\u00e3o t\u00eam matches."""
        vm = ClientesViewModel()
        vm.load_from_iterable(sample_clientes_data)

        # Buscar "acme" em status "Inativo" (n\u00e3o existe)
        vm.set_status_filter("Inativo")
        vm.set_search_text("acme")
        rows = vm.get_rows()

        assert len(rows) == 0


class TestViewModelStatusChoices:
    """Testes para extra\u00e7\u00e3o de op\u00e7\u00f5es de status."""

    def test_get_status_choices_returns_unique_sorted(self, sample_clientes_data):
        """Deve retornar status \u00fanicos e ordenados."""
        vm = ClientesViewModel()
        vm.load_from_iterable(sample_clientes_data)

        choices = vm.get_status_choices()

        assert choices == ["Ativo", "Inativo"]

    def test_get_status_choices_includes_all_from_filtered_rows(self, sample_clientes_data):
        """Deve extrair status dos clientes após filtragem."""
        vm = ClientesViewModel()
        vm.load_from_iterable(sample_clientes_data)

        # Filtrar por busca (apenas "acme")
        vm.set_search_text("acme")
        choices = vm.get_status_choices()

        # ViewModel extrai status de _rows (após filtragem), então todos os status originais
        # podem aparecer se algum cliente com aquele status passou pelo filtro
        assert "Ativo" in choices
        assert len(choices) >= 1

    def test_get_status_choices_empty_list(self):
        """Deve retornar lista vazia para VM sem dados."""
        vm = ClientesViewModel()
        choices = vm.get_status_choices()

        assert choices == []


class TestViewModelRowConstruction:
    """Testes para constru\u00e7\u00e3o de ClienteRow."""

    def test_row_contains_all_fields(self, sample_clientes_data):
        """Deve construir ClienteRow com todos os campos."""
        vm = ClientesViewModel()
        vm.load_from_iterable(sample_clientes_data)

        rows = vm.get_rows()
        assert len(rows) == 3

        row = rows[0]
        assert isinstance(row, ClienteRow)
        assert row.id == "1"
        assert row.razao_social == "ACME Corporation"
        assert row.nome == "Jo\u00e3o Silva"
        assert row.status == "Ativo"
        assert row.observacoes == "Cliente priorit\u00e1rio"  # Sem [status]

    def test_row_extracts_status_from_observacoes(self, sample_clientes_data):
        """Deve extrair status de observa\u00e7\u00f5es corretamente."""
        vm = ClientesViewModel()
        vm.load_from_iterable(sample_clientes_data)

        rows = vm.get_rows()

        # Cliente 1: [Ativo] Cliente priorit\u00e1rio
        row1 = next(r for r in rows if r.id == "1")
        assert row1.status == "Ativo"
        assert row1.observacoes == "Cliente priorit\u00e1rio"

        # Cliente 2: [Inativo] Sem demanda
        row2 = next(r for r in rows if r.id == "2")
        assert row2.status == "Inativo"
        assert row2.observacoes == "Sem demanda"

    def test_row_has_search_norm_field(self, sample_clientes_data):
        """Deve gerar campo search_norm para busca."""
        vm = ClientesViewModel()
        vm.load_from_iterable(sample_clientes_data)

        rows = vm.get_rows()
        row = rows[0]

        assert row.search_norm != ""
        assert isinstance(row.search_norm, str)

        # search_norm deve conter dados normalizados
        # (lowercase, sem acentos, etc. - depende da implementa\u00e7\u00e3o de join_and_normalize)
        assert len(row.search_norm) > 0


class TestViewModelFilterEdgeCases:
    """Testes de casos extremos de filtros."""

    def test_clients_without_status_field(self):
        """Deve tratar clientes sem campo 'status' nas observa\u00e7\u00f5es."""
        data = [
            {"id": "1", "razao_social": "ACME", "observacoes": "Sem status"},
            {"id": "2", "razao_social": "Beta", "observacoes": "[Ativo] Com status"},
        ]

        vm = ClientesViewModel()
        vm.load_from_iterable(data)

        rows = vm.get_rows()
        assert len(rows) == 2

        # Cliente sem status
        row1 = next(r for r in rows if r.id == "1")
        assert row1.status == ""
        assert row1.observacoes == "Sem status"

    def test_clients_with_unicode_characters(self):
        """Deve funcionar com caracteres unicode."""
        data = [
            {
                "id": "1",
                "razao_social": "Farm\u00e1cia S\u00e3o Jos\u00e9",
                "nome": "Jo\u00e3o \u00d1o\u00f1o",
                "observacoes": "[Ativo] Cliente",
            }
        ]

        vm = ClientesViewModel()
        vm.load_from_iterable(data)

        # Buscar com acentos
        vm.set_search_text("farm\u00e1cia")
        rows = vm.get_rows()
        assert len(rows) == 1

    def test_very_long_client_list(self):
        """Deve funcionar com listas grandes."""
        data = [
            {
                "id": str(i),
                "razao_social": f"Cliente {i}",
                "observacoes": f"[Ativo] Cliente {i}",
            }
            for i in range(100)
        ]

        vm = ClientesViewModel()
        vm.load_from_iterable(data)

        vm.set_status_filter("Ativo")
        rows = vm.get_rows()
        assert len(rows) == 100

    def test_empty_client_list(self):
        """Deve funcionar com lista vazia."""
        vm = ClientesViewModel()
        vm.load_from_iterable([])

        vm.set_search_text("acme")
        vm.set_status_filter("Ativo")
        rows = vm.get_rows()

        assert rows == []
        assert vm.get_status_choices() == []


class TestViewModelFilterPerformance:
    """Testes de performance e efici\u00eancia dos filtros."""

    def test_rebuild_false_does_not_trigger_rebuild(self, sample_clientes_data):
        """Deve evitar rebuild quando rebuild=False."""
        vm = ClientesViewModel()
        vm.load_from_iterable(sample_clientes_data)

        # Armazenar estado inicial
        initial_rows = vm.get_rows()
        assert len(initial_rows) == 3

        # Mudar filtros sem rebuild
        vm.set_search_text("acme", rebuild=False)
        vm.set_status_filter("Ativo", rebuild=False)

        # Rows n\u00e3o devem ter mudado
        assert vm.get_rows() == initial_rows

        # Mas os filtros foram armazenados
        assert vm._search_text_raw == "acme"
        assert vm._status_filter == "Ativo"

    def test_sequential_rebuilds(self, sample_clientes_data):
        """Deve permitir rebuilds sequenciais sem problemas."""
        vm = ClientesViewModel()
        vm.load_from_iterable(sample_clientes_data)

        # Rebuild 1
        vm.set_search_text("acme")
        assert len(vm.get_rows()) == 1

        # Rebuild 2
        vm.set_search_text("beta")
        assert len(vm.get_rows()) == 1

        # Rebuild 3
        vm.set_search_text("")
        assert len(vm.get_rows()) == 3


# Testes de integra\u00e7\u00e3o completos


class TestViewModelFilterIntegration:
    """Testes de integra\u00e7\u00e3o completos simulando uso real."""

    def test_full_user_workflow(self, sample_clientes_data):
        """Simula workflow completo de usu\u00e1rio filtrando clientes."""
        vm = ClientesViewModel()
        vm.load_from_iterable(sample_clientes_data)

        # 1. Lista inicial: 3 clientes
        assert len(vm.get_rows()) == 3

        # 2. Usuário escolhe status "Ativo"
        vm.set_status_filter("Ativo")
        rows = vm.get_rows()
        assert len(rows) == 2

        # 3. Opções de status refletem os clientes após filtragem
        choices = vm.get_status_choices()
        assert "Ativo" in choices

        # 4. Usu\u00e1rio digita "gamma" na busca
        vm.set_search_text("gamma")
        rows = vm.get_rows()
        assert len(rows) == 1
        assert rows[0].razao_social == "Gamma Corp"

        # 5. Usu\u00e1rio limpa filtros
        vm.set_status_filter(None)
        vm.set_search_text("")
        rows = vm.get_rows()
        assert len(rows) == 3

    def test_rebuild_optimization_workflow(self, sample_clientes_data):
        """Simula otimiza\u00e7\u00e3o de m\u00faltiplos filtros sem rebuilds intermedi\u00e1rios."""
        vm = ClientesViewModel()
        vm.load_from_iterable(sample_clientes_data)

        # Aplicar m\u00faltiplos filtros sem rebuild
        vm.set_search_text("corp", rebuild=False)
        vm.set_status_filter("Ativo", rebuild=False)

        # Estado ainda n\u00e3o filtrado
        assert len(vm.get_rows()) == 3

        # Rebuild manual via refresh_from_service ou load_from_iterable
        vm.load_from_iterable(sample_clientes_data)

        # Agora filtros foram aplicados
        rows = vm.get_rows()
        assert len(rows) == 2
        ids = {row.id for row in rows}
        assert ids == {"1", "3"}
