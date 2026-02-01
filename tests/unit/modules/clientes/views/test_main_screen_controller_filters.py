# -*- coding: utf-8 -*-

"""Testes de filtros e ordenação via controller.

Migrado de test_viewmodel_filters.py e test_viewmodel_round15.py.
Valida comportamento de filtros/ordenação através do main_screen_controller
em vez da pipeline LEGACY do ViewModel.
"""

from __future__ import annotations

import pytest

from src.modules.clientes.core.viewmodel import ClienteRow
from src.modules.clientes.views.main_screen_controller import (
    compute_main_screen_state,
)
from tests.unit.modules.clientes.views.factories_main_screen_state import (
    make_main_screen_state,
)


# ============================================================================
# Fixtures e Helpers
# ============================================================================


def make_client(
    *,
    id: str,
    razao_social: str = "Cliente",
    cnpj: str = "12.345.678/0001-99",
    nome: str = "",
    whatsapp: str = "",
    observacoes: str = "",
    status: str = "Ativo",
    ultima_alteracao: str = "",
    search_norm: str | None = None,
) -> ClienteRow:
    """Factory para criar ClienteRow de teste."""
    if search_norm is None:
        # Gerar search_norm automaticamente
        parts = [id, razao_social, cnpj, nome, whatsapp, observacoes, status]
        search_norm = " ".join(str(p).lower() for p in parts if p)

    return ClienteRow(
        id=id,
        razao_social=razao_social,
        cnpj=cnpj,
        nome=nome,
        whatsapp=whatsapp,
        observacoes=observacoes,
        status=status,
        ultima_alteracao=ultima_alteracao,
        search_norm=search_norm,
        raw={},
    )


def compute_visible_clients(
    clients: list[ClienteRow],
    *,
    order_label: str = "Razão Social (A→Z)",
    filter_label: str = "Todos",
    search_text: str = "",
    is_trash_screen: bool = False,
) -> list[ClienteRow]:
    """Helper para computar clientes visíveis via controller."""
    state = make_main_screen_state(
        clients=clients,
        order_label=order_label,
        filter_label=filter_label,
        search_text=search_text,
        is_trash_screen=is_trash_screen,
    )
    computed = compute_main_screen_state(state)
    return list(computed.visible_clients)


@pytest.fixture
def sample_clients():
    """Fixture com dados de clientes para testes."""
    return [
        make_client(
            id="1",
            razao_social="ACME Corporation",
            cnpj="12.345.678/0001-90",
            nome="João Silva",
            whatsapp="(11) 99999-8888",
            observacoes="Cliente prioritário",
            status="Ativo",
            search_norm="1 acme corporation 12345678000190 joão silva 11999998888 cliente prioritário ativo",
        ),
        make_client(
            id="2",
            razao_social="Beta Industries",
            cnpj="98.765.432/0001-10",
            nome="Maria Santos",
            whatsapp="(11) 98888-7777",
            observacoes="Sem demanda",
            status="Inativo",
            search_norm="2 beta industries 98765432000110 maria santos 11988887777 sem demanda inativo",
        ),
        make_client(
            id="3",
            razao_social="Gamma Corp",
            cnpj="11.122.233/0001-44",
            nome="Pedro Costa",
            whatsapp="(11) 97777-6666",
            observacoes="Novo cliente",
            status="Ativo",
            search_norm="3 gamma corp 11122233000144 pedro costa 11977776666 novo cliente ativo",
        ),
    ]


# ============================================================================
# Testes de Filtro de Texto de Busca
# ============================================================================


class TestControllerSearchTextFilter:
    """Testes para filtro de texto de busca via controller."""

    def test_filter_by_search_text_normalized(self, sample_clients):
        """Deve filtrar clientes por texto de busca normalizado."""
        result = compute_visible_clients(
            sample_clients,
            search_text="acme",
        )

        assert len(result) == 1
        assert result[0].id == "1"
        assert "ACME" in result[0].razao_social

    def test_filter_case_insensitive(self, sample_clients):
        """Deve fazer busca case-insensitive."""
        result = compute_visible_clients(
            sample_clients,
            search_text="BETA",
        )

        assert len(result) == 1
        assert result[0].id == "2"

    def test_filter_partial_match(self, sample_clients):
        """Deve fazer match parcial (substring)."""
        result = compute_visible_clients(
            sample_clients,
            search_text="corp",
        )

        # Deve encontrar "ACME Corporation" e "Gamma Corp"
        assert len(result) == 2
        ids = {row.id for row in result}
        assert ids == {"1", "3"}

    def test_filter_empty_search_returns_all(self, sample_clients):
        """Deve retornar todos os clientes quando busca é vazia."""
        result = compute_visible_clients(
            sample_clients,
            search_text="",
        )

        assert len(result) == 3

    def test_filter_no_matches(self, sample_clients):
        """Deve retornar lista vazia quando nenhum match."""
        result = compute_visible_clients(
            sample_clients,
            search_text="xyz123nonexistent",
        )

        assert len(result) == 0

    def test_filter_searches_multiple_fields(self, sample_clients):
        """Deve buscar em múltiplos campos (nome, razão, CNPJ, etc.)."""
        # Buscar por nome
        result = compute_visible_clients(sample_clients, search_text="joão")
        assert len(result) == 1
        assert result[0].id == "1"

        # Buscar por CNPJ parcial
        result = compute_visible_clients(sample_clients, search_text="12345")
        assert len(result) == 1
        assert result[0].id == "1"

        # Buscar por observação
        result = compute_visible_clients(sample_clients, search_text="prioritário")
        assert len(result) == 1
        assert result[0].id == "1"


# ============================================================================
# Testes de Filtro de Status
# ============================================================================


class TestControllerStatusFilter:
    """Testes para filtro de status via controller."""

    def test_filter_by_status(self, sample_clients):
        """Deve filtrar clientes por status."""
        result = compute_visible_clients(
            sample_clients,
            filter_label="Ativo",
        )

        assert len(result) == 2
        ids = {row.id for row in result}
        assert ids == {"1", "3"}

    def test_filter_status_case_insensitive(self, sample_clients):
        """Deve fazer filtro case-insensitive."""
        result = compute_visible_clients(
            sample_clients,
            filter_label="inativo",
        )

        assert len(result) == 1
        assert result[0].id == "2"

    def test_filter_status_todos_returns_all(self, sample_clients):
        """Deve retornar todos quando status é 'Todos'."""
        result = compute_visible_clients(
            sample_clients,
            filter_label="Todos",
        )

        assert len(result) == 3

    def test_filter_status_empty_returns_all(self, sample_clients):
        """Deve retornar todos quando status é string vazia."""
        result = compute_visible_clients(
            sample_clients,
            filter_label="",
        )

        assert len(result) == 3


# ============================================================================
# Testes de Filtros Combinados
# ============================================================================


class TestControllerCombinedFilters:
    """Testes para combinação de filtros via controller."""

    def test_search_and_status_combined(self, sample_clients):
        """Deve combinar filtro de texto e status."""
        result = compute_visible_clients(
            sample_clients,
            filter_label="Ativo",
            search_text="corp",
        )

        # Deve retornar apenas clientes ativos com "corp"
        assert len(result) == 2
        ids = {row.id for row in result}
        assert ids == {"1", "3"}

    def test_no_matches_with_combined_filters(self, sample_clients):
        """Deve retornar lista vazia quando filtros combinados não têm matches."""
        result = compute_visible_clients(
            sample_clients,
            filter_label="Inativo",
            search_text="acme",
        )

        assert len(result) == 0

    def test_combined_filters_narrow_results(self, sample_clients):
        """Deve estreitar resultados com múltiplos filtros."""
        # Só status: 2 clientes
        result = compute_visible_clients(sample_clients, filter_label="Ativo")
        assert len(result) == 2

        # Status + busca: 1 cliente
        result = compute_visible_clients(
            sample_clients,
            filter_label="Ativo",
            search_text="gamma",
        )
        assert len(result) == 1
        assert result[0].id == "3"


# ============================================================================
# Testes de Ordenação
# ============================================================================


class TestControllerOrdering:
    """Testes para ordenação via controller."""

    def test_order_by_razao_social_asc(self, sample_clients):
        """Testa ordenação por Razão Social (A→Z)."""
        result = compute_visible_clients(
            sample_clients,
            order_label="Razão Social (A→Z)",
        )

        assert len(result) == 3
        assert result[0].razao_social == "ACME Corporation"
        assert result[1].razao_social == "Beta Industries"
        assert result[2].razao_social == "Gamma Corp"

    def test_order_by_nome_asc(self, sample_clients):
        """Testa ordenação por Nome (A→Z)."""
        result = compute_visible_clients(
            sample_clients,
            order_label="Nome (A→Z)",
        )

        assert len(result) == 3
        assert result[0].nome == "João Silva"
        assert result[1].nome == "Maria Santos"
        assert result[2].nome == "Pedro Costa"

    def test_order_by_id_asc(self, sample_clients):
        """Testa ordenação por ID (1→9)."""
        # Embaralhar clientes
        shuffled = [sample_clients[2], sample_clients[0], sample_clients[1]]

        result = compute_visible_clients(
            shuffled,
            order_label="ID (1→9)",
        )

        assert len(result) == 3
        assert result[0].id == "1"
        assert result[1].id == "2"
        assert result[2].id == "3"

    def test_order_by_id_desc(self, sample_clients):
        """Testa ordenação por ID (9→1)."""
        result = compute_visible_clients(
            sample_clients,
            order_label="ID (9→1)",
        )

        assert len(result) == 3
        assert result[0].id == "3"
        assert result[1].id == "2"
        assert result[2].id == "1"


# ============================================================================
# Testes de Ordenação + Filtros Combinados
# ============================================================================


class TestControllerOrderingWithFilters:
    """Testes para ordenação combinada com filtros."""

    def test_order_filtered_results(self, sample_clients):
        """Deve ordenar apenas os resultados filtrados."""
        result = compute_visible_clients(
            sample_clients,
            filter_label="Ativo",
            order_label="Razão Social (A→Z)",
        )

        assert len(result) == 2
        # Apenas os ativos, ordenados: ACME, Gamma
        assert result[0].razao_social == "ACME Corporation"
        assert result[1].razao_social == "Gamma Corp"

    def test_order_with_search_and_status(self, sample_clients):
        """Deve ordenar resultados de filtros combinados."""
        # Adicionar mais um cliente ativo com "corp"
        extra_client = make_client(
            id="4",
            razao_social="Alpha Corporation",
            status="Ativo",
            search_norm="4 alpha corporation ativo",
        )
        all_clients = sample_clients + [extra_client]

        result = compute_visible_clients(
            all_clients,
            filter_label="Ativo",
            search_text="corp",
            order_label="Razão Social (A→Z)",
        )

        # Deve filtrar por status "Ativo" + busca "corp" e ordenar
        assert len(result) == 3  # ACME, Alpha, Gamma
        assert result[0].razao_social == "ACME Corporation"
        assert result[1].razao_social == "Alpha Corporation"
        assert result[2].razao_social == "Gamma Corp"


# ============================================================================
# Testes de Casos Extremos
# ============================================================================


class TestControllerEdgeCases:
    """Testes de casos extremos."""

    def test_empty_client_list(self):
        """Deve funcionar com lista vazia."""
        result = compute_visible_clients(
            [],
            filter_label="Ativo",
            search_text="acme",
        )

        assert result == []

    def test_clients_with_unicode(self):
        """Deve funcionar com caracteres unicode."""
        clients = [
            make_client(
                id="1",
                razao_social="Farmácia São José",
                nome="João Ñoño",
                status="Ativo",
                search_norm="1 farmácia são josé joão ñoño ativo",
            )
        ]

        result = compute_visible_clients(clients, search_text="farmácia")
        assert len(result) == 1

    def test_large_client_list(self):
        """Deve funcionar com listas grandes."""
        clients = [
            make_client(
                id=str(i),
                razao_social=f"Cliente {i}",
                status="Ativo",
                search_norm=f"{i} cliente {i} ativo",
            )
            for i in range(100)
        ]

        result = compute_visible_clients(clients, filter_label="Ativo")
        assert len(result) == 100

    def test_clients_without_status(self):
        """Deve tratar clientes sem status."""
        clients = [
            make_client(id="1", razao_social="ACME", status=""),
            make_client(id="2", razao_social="Beta", status="Ativo"),
        ]

        # Filtrar por "Ativo" deve retornar apenas o segundo
        result = compute_visible_clients(clients, filter_label="Ativo")
        assert len(result) == 1
        assert result[0].id == "2"

        # Filtrar por "Todos" deve retornar ambos
        result = compute_visible_clients(clients, filter_label="Todos")
        assert len(result) == 2


# ============================================================================
# Testes de Integração Completa
# ============================================================================


class TestControllerIntegration:
    """Testes de integração completos simulando uso real."""

    def test_full_user_workflow(self, sample_clients):
        """Simula workflow completo de usuário filtrando clientes."""
        # 1. Lista inicial: 3 clientes
        result = compute_visible_clients(sample_clients)
        assert len(result) == 3

        # 2. Usuário escolhe status "Ativo"
        result = compute_visible_clients(sample_clients, filter_label="Ativo")
        assert len(result) == 2

        # 3. Usuário digita "gamma" na busca
        result = compute_visible_clients(
            sample_clients,
            filter_label="Ativo",
            search_text="gamma",
        )
        assert len(result) == 1
        assert result[0].razao_social == "Gamma Corp"

        # 4. Usuário limpa filtros
        result = compute_visible_clients(
            sample_clients,
            filter_label="Todos",
            search_text="",
        )
        assert len(result) == 3

    def test_sequential_filter_changes(self, sample_clients):
        """Simula mudanças sequenciais de filtros."""
        # Filtrar por "Ativo"
        result = compute_visible_clients(sample_clients, filter_label="Ativo")
        assert len(result) == 2

        # Mudar para busca "acme"
        result = compute_visible_clients(sample_clients, search_text="acme")
        assert len(result) == 1

        # Combinar ambos
        result = compute_visible_clients(
            sample_clients,
            filter_label="Ativo",
            search_text="acme",
        )
        assert len(result) == 1
        assert result[0].id == "1"

        # Limpar busca (mantém status)
        result = compute_visible_clients(
            sample_clients,
            filter_label="Ativo",
            search_text="",
        )
        assert len(result) == 2

    def test_order_changes_during_filtering(self, sample_clients):
        """Simula mudança de ordenação durante filtragem."""
        # Filtrar + ordenar por Razão Social
        result = compute_visible_clients(
            sample_clients,
            filter_label="Ativo",
            order_label="Razão Social (A→Z)",
        )
        assert result[0].razao_social == "ACME Corporation"
        assert result[1].razao_social == "Gamma Corp"

        # Mudar ordenação para Nome
        result = compute_visible_clients(
            sample_clients,
            filter_label="Ativo",
            order_label="Nome (A→Z)",
        )
        assert result[0].nome == "João Silva"
        assert result[1].nome == "Pedro Costa"

        # Mudar ordenação para ID desc
        result = compute_visible_clients(
            sample_clients,
            filter_label="Ativo",
            order_label="ID (9→1)",
        )
        assert result[0].id == "3"
        assert result[1].id == "1"
