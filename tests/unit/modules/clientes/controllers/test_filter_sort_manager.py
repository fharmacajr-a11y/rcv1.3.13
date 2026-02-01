# -*- coding: utf-8 -*-
"""Testes unitários para FilterSortManager.

Este módulo testa o gerenciador de filtros, ordenação e busca de forma headless,
sem depender de Tkinter real, usando mocks para as funções auxiliares.

Cobertura esperada: >= 90% do arquivo filter_sort_manager.py
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.modules.clientes.controllers.filter_sort_manager import (
    FilterSortInput,
    FilterSortManager,
    FilterSortResult,
)
from src.modules.clientes.core.viewmodel import ClienteRow
from src.modules.clientes.views.main_screen_controller import (
    MainScreenComputed,
    MainScreenState,
)


@pytest.fixture
def sample_clients() -> list[ClienteRow]:
    """Lista de clientes de exemplo para testes."""
    return [
        ClienteRow(
            id="1",
            razao_social="Empresa Alpha LTDA",
            cnpj="11.111.111/0001-11",
            nome="Alpha",
            whatsapp="11-11111-1111",
            observacoes="Cliente ativo",
            status="Ativo",
            ultima_alteracao="2024-01-15",
        ),
        ClienteRow(
            id="2",
            razao_social="Empresa Beta SA",
            cnpj="22.222.222/0002-22",
            nome="Beta",
            whatsapp="22-22222-2222",
            observacoes="Empresa grande",
            status="Ativo",
            ultima_alteracao="2024-02-20",
        ),
        ClienteRow(
            id="3",
            razao_social="Empresa Gamma ME",
            cnpj="33.333.333/0003-33",
            nome="Gamma",
            whatsapp="33-33333-3333",
            observacoes="Microempresa",
            status="Inativo",
            ultima_alteracao="2024-03-10",
        ),
        ClienteRow(
            id="4",
            razao_social="Delta Comercio LTDA",
            cnpj="44.444.444/0004-44",
            nome="Delta",
            whatsapp="44-44444-4444",
            observacoes="",
            status="Ativo",
            ultima_alteracao="2024-01-05",
        ),
    ]


@pytest.fixture
def mock_state() -> MainScreenState:
    """Mock de MainScreenState."""
    return MainScreenState(
        clients=[],
        order_label="Razão Social (A→Z)",
        filter_label="Todos",
        search_text="",
        selected_ids=frozenset(),
        is_trash_screen=False,
    )


@pytest.fixture
def mock_computed() -> MainScreenComputed:
    """Mock de MainScreenComputed."""
    return MainScreenComputed(
        visible_clients=[],
        can_batch_delete=False,
        can_batch_restore=False,
        can_batch_export=False,
        selection_count=0,
        has_selection=False,
    )


@pytest.fixture
def manager() -> FilterSortManager:
    """Cria uma instância do FilterSortManager."""
    return FilterSortManager()


# ============================================================================
# TESTES DE DATA STRUCTURES
# ============================================================================


class TestFilterSortInput:
    """Testes da estrutura FilterSortInput."""

    def test_filter_sort_input_criacao(self, sample_clients: list[ClienteRow]) -> None:
        """FilterSortInput deve ser criado com todos os parâmetros."""
        inp = FilterSortInput(
            clients=sample_clients,
            raw_order_label="Razão Social (A→Z)",
            raw_filter_label="Todos",
            raw_search_text="empresa",
            selected_ids={"1", "2"},
            is_trash_screen=False,
        )

        assert inp.clients == sample_clients
        assert inp.raw_order_label == "Razão Social (A→Z)"
        assert inp.raw_filter_label == "Todos"
        assert inp.raw_search_text == "empresa"
        assert inp.selected_ids == {"1", "2"}
        assert inp.is_trash_screen is False

    def test_filter_sort_input_frozen(self, sample_clients: list[ClienteRow]) -> None:
        """FilterSortInput deve ser imutável (frozen dataclass)."""
        inp = FilterSortInput(
            clients=sample_clients,
            raw_order_label="CNPJ (A→Z)",
            raw_filter_label="Ativo",
            raw_search_text="",
            selected_ids=set(),
            is_trash_screen=False,
        )

        with pytest.raises(AttributeError):
            inp.raw_search_text = "novo"  # type: ignore


class TestFilterSortResult:
    """Testes da estrutura FilterSortResult."""

    def test_filter_sort_result_criacao(
        self,
        mock_state: MainScreenState,
        mock_computed: MainScreenComputed,
    ) -> None:
        """FilterSortResult deve ser criado com state e computed."""
        result = FilterSortResult(state=mock_state, computed=mock_computed)

        assert result.state == mock_state
        assert result.computed == mock_computed

    def test_filter_sort_result_frozen(
        self,
        mock_state: MainScreenState,
        mock_computed: MainScreenComputed,
    ) -> None:
        """FilterSortResult deve ser imutável (frozen dataclass)."""
        result = FilterSortResult(state=mock_state, computed=mock_computed)

        with pytest.raises(AttributeError):
            result.state = MagicMock()  # type: ignore


# ============================================================================
# TESTES DE INICIALIZAÇÃO
# ============================================================================


class TestFilterSortManagerInit:
    """Testes de inicialização do FilterSortManager."""

    def test_manager_criado_sem_estado(self) -> None:
        """FilterSortManager deve ser criado sem estado interno."""
        manager = FilterSortManager()
        # Manager é stateless, apenas verificamos que foi criado
        assert manager is not None


# ============================================================================
# TESTES DO MÉTODO COMPUTE
# ============================================================================


class TestFilterSortManagerCompute:
    """Testes do método compute()."""

    @patch("src.modules.clientes.controllers.filter_sort_manager.compute_main_screen_state")
    @patch("src.modules.clientes.controllers.filter_sort_manager.build_main_screen_state")
    def test_compute_chama_build_e_compute_state(
        self,
        mock_build: MagicMock,
        mock_compute: MagicMock,
        manager: FilterSortManager,
        sample_clients: list[ClienteRow],
        mock_state: MainScreenState,
        mock_computed: MainScreenComputed,
    ) -> None:
        """compute deve chamar build_main_screen_state e compute_main_screen_state."""
        mock_build.return_value = mock_state
        mock_compute.return_value = mock_computed

        inp = FilterSortInput(
            clients=sample_clients,
            raw_order_label="Razão Social (A→Z)",
            raw_filter_label="Todos",
            raw_search_text="",
            selected_ids=set(),
            is_trash_screen=False,
        )

        result = manager.compute(inp)

        # Verifica que build foi chamado com parâmetros corretos
        mock_build.assert_called_once_with(
            clients=sample_clients,
            raw_order_label="Razão Social (A→Z)",
            raw_filter_label="Todos",
            raw_search_text="",
            selected_ids=set(),
            is_trash_screen=False,
        )

        # Verifica que compute foi chamado com o state construído
        mock_compute.assert_called_once_with(mock_state)

        # Verifica o resultado
        assert result.state == mock_state
        assert result.computed == mock_computed

    @patch("src.modules.clientes.controllers.filter_sort_manager.compute_main_screen_state")
    @patch("src.modules.clientes.controllers.filter_sort_manager.build_main_screen_state")
    def test_compute_com_filtro_ativo(
        self,
        mock_build: MagicMock,
        mock_compute: MagicMock,
        manager: FilterSortManager,
        sample_clients: list[ClienteRow],
        mock_state: MainScreenState,
        mock_computed: MainScreenComputed,
    ) -> None:
        """compute deve processar corretamente filtro de status."""
        mock_build.return_value = mock_state
        mock_compute.return_value = mock_computed

        inp = FilterSortInput(
            clients=sample_clients,
            raw_order_label="CNPJ (A→Z)",
            raw_filter_label="Ativo",
            raw_search_text="",
            selected_ids=set(),
            is_trash_screen=False,
        )

        result = manager.compute(inp)

        mock_build.assert_called_once_with(
            clients=sample_clients,
            raw_order_label="CNPJ (A→Z)",
            raw_filter_label="Ativo",
            raw_search_text="",
            selected_ids=set(),
            is_trash_screen=False,
        )

        assert result.state == mock_state
        assert result.computed == mock_computed

    @patch("src.modules.clientes.controllers.filter_sort_manager.compute_main_screen_state")
    @patch("src.modules.clientes.controllers.filter_sort_manager.build_main_screen_state")
    def test_compute_com_busca(
        self,
        mock_build: MagicMock,
        mock_compute: MagicMock,
        manager: FilterSortManager,
        sample_clients: list[ClienteRow],
        mock_state: MainScreenState,
        mock_computed: MainScreenComputed,
    ) -> None:
        """compute deve processar corretamente texto de busca."""
        mock_build.return_value = mock_state
        mock_compute.return_value = mock_computed

        inp = FilterSortInput(
            clients=sample_clients,
            raw_order_label="Nome (A→Z)",
            raw_filter_label="Todos",
            raw_search_text="alpha",
            selected_ids=set(),
            is_trash_screen=False,
        )

        result = manager.compute(inp)

        mock_build.assert_called_once_with(
            clients=sample_clients,
            raw_order_label="Nome (A→Z)",
            raw_filter_label="Todos",
            raw_search_text="alpha",
            selected_ids=set(),
            is_trash_screen=False,
        )

        assert result.state == mock_state

    @patch("src.modules.clientes.controllers.filter_sort_manager.compute_main_screen_state")
    @patch("src.modules.clientes.controllers.filter_sort_manager.build_main_screen_state")
    def test_compute_com_selecao(
        self,
        mock_build: MagicMock,
        mock_compute: MagicMock,
        manager: FilterSortManager,
        sample_clients: list[ClienteRow],
        mock_state: MainScreenState,
        mock_computed: MainScreenComputed,
    ) -> None:
        """compute deve processar corretamente IDs selecionados."""
        mock_build.return_value = mock_state
        mock_compute.return_value = mock_computed

        selected = {"1", "2", "3"}
        inp = FilterSortInput(
            clients=sample_clients,
            raw_order_label="ID (1→9)",
            raw_filter_label="Todos",
            raw_search_text="",
            selected_ids=selected,
            is_trash_screen=False,
        )

        result = manager.compute(inp)

        mock_build.assert_called_once_with(
            clients=sample_clients,
            raw_order_label="ID (1→9)",
            raw_filter_label="Todos",
            raw_search_text="",
            selected_ids=selected,
            is_trash_screen=False,
        )

        assert result.computed == mock_computed

    @patch("src.modules.clientes.controllers.filter_sort_manager.compute_main_screen_state")
    @patch("src.modules.clientes.controllers.filter_sort_manager.build_main_screen_state")
    def test_compute_em_tela_lixeira(
        self,
        mock_build: MagicMock,
        mock_compute: MagicMock,
        manager: FilterSortManager,
        sample_clients: list[ClienteRow],
        mock_state: MainScreenState,
        mock_computed: MainScreenComputed,
    ) -> None:
        """compute deve processar corretamente flag is_trash_screen."""
        mock_build.return_value = mock_state
        mock_compute.return_value = mock_computed

        inp = FilterSortInput(
            clients=sample_clients,
            raw_order_label="Razão Social (A→Z)",
            raw_filter_label="Todos",
            raw_search_text="",
            selected_ids=set(),
            is_trash_screen=True,
        )

        result = manager.compute(inp)

        mock_build.assert_called_once_with(
            clients=sample_clients,
            raw_order_label="Razão Social (A→Z)",
            raw_filter_label="Todos",
            raw_search_text="",
            selected_ids=set(),
            is_trash_screen=True,
        )

        assert result.state == mock_state

    @patch("src.modules.clientes.controllers.filter_sort_manager.compute_main_screen_state")
    @patch("src.modules.clientes.controllers.filter_sort_manager.build_main_screen_state")
    def test_compute_com_parametros_nulos(
        self,
        mock_build: MagicMock,
        mock_compute: MagicMock,
        manager: FilterSortManager,
        sample_clients: list[ClienteRow],
        mock_state: MainScreenState,
        mock_computed: MainScreenComputed,
    ) -> None:
        """compute deve lidar com parâmetros None."""
        mock_build.return_value = mock_state
        mock_compute.return_value = mock_computed

        inp = FilterSortInput(
            clients=sample_clients,
            raw_order_label=None,
            raw_filter_label=None,
            raw_search_text=None,
            selected_ids=set(),
            is_trash_screen=False,
        )

        result = manager.compute(inp)

        mock_build.assert_called_once_with(
            clients=sample_clients,
            raw_order_label=None,
            raw_filter_label=None,
            raw_search_text=None,
            selected_ids=set(),
            is_trash_screen=False,
        )

        assert result.state == mock_state
        assert result.computed == mock_computed

    @patch("src.modules.clientes.controllers.filter_sort_manager.compute_main_screen_state")
    @patch("src.modules.clientes.controllers.filter_sort_manager.build_main_screen_state")
    def test_compute_com_lista_vazia(
        self,
        mock_build: MagicMock,
        mock_compute: MagicMock,
        manager: FilterSortManager,
        mock_state: MainScreenState,
        mock_computed: MainScreenComputed,
    ) -> None:
        """compute deve processar lista vazia de clientes."""
        mock_build.return_value = mock_state
        mock_compute.return_value = mock_computed

        inp = FilterSortInput(
            clients=[],
            raw_order_label="Razão Social (A→Z)",
            raw_filter_label="Todos",
            raw_search_text="",
            selected_ids=set(),
            is_trash_screen=False,
        )

        result = manager.compute(inp)

        mock_build.assert_called_once_with(
            clients=[],
            raw_order_label="Razão Social (A→Z)",
            raw_filter_label="Todos",
            raw_search_text="",
            selected_ids=set(),
            is_trash_screen=False,
        )

        assert result.state == mock_state

    @patch("src.modules.clientes.controllers.filter_sort_manager.compute_main_screen_state")
    @patch("src.modules.clientes.controllers.filter_sort_manager.build_main_screen_state")
    def test_compute_combinacao_multiplos_filtros(
        self,
        mock_build: MagicMock,
        mock_compute: MagicMock,
        manager: FilterSortManager,
        sample_clients: list[ClienteRow],
        mock_state: MainScreenState,
        mock_computed: MainScreenComputed,
    ) -> None:
        """compute deve processar combinação de filtro + busca + seleção."""
        mock_build.return_value = mock_state
        mock_compute.return_value = mock_computed

        inp = FilterSortInput(
            clients=sample_clients,
            raw_order_label="Última Alteração (mais recente)",
            raw_filter_label="Ativo",
            raw_search_text="empresa",
            selected_ids={"1", "2"},
            is_trash_screen=False,
        )

        result = manager.compute(inp)

        mock_build.assert_called_once_with(
            clients=sample_clients,
            raw_order_label="Última Alteração (mais recente)",
            raw_filter_label="Ativo",
            raw_search_text="empresa",
            selected_ids={"1", "2"},
            is_trash_screen=False,
        )

        assert result.state == mock_state
        assert result.computed == mock_computed


# ============================================================================
# TESTES DO MÉTODO COMPUTE_FOR_SELECTION_CHANGE
# ============================================================================


class TestFilterSortManagerComputeForSelectionChange:
    """Testes do método compute_for_selection_change()."""

    @patch("src.modules.clientes.controllers.filter_sort_manager.compute_main_screen_state")
    @patch("src.modules.clientes.controllers.filter_sort_manager.build_main_screen_state")
    def test_compute_for_selection_change_usa_visible_clients(
        self,
        mock_build: MagicMock,
        mock_compute: MagicMock,
        manager: FilterSortManager,
        sample_clients: list[ClienteRow],
        mock_state: MainScreenState,
        mock_computed: MainScreenComputed,
    ) -> None:
        """compute_for_selection_change deve usar current_visible_clients ao invés de inp.clients."""
        mock_build.return_value = mock_state
        mock_compute.return_value = mock_computed

        # Simula clientes visíveis após filtro (subset)
        visible_clients = sample_clients[:2]

        inp = FilterSortInput(
            clients=sample_clients,  # Lista completa (ignorada neste método)
            raw_order_label="Razão Social (A→Z)",
            raw_filter_label="Ativo",
            raw_search_text="",
            selected_ids={"1"},
            is_trash_screen=False,
        )

        result = manager.compute_for_selection_change(visible_clients, inp)

        # Deve usar visible_clients ao invés de inp.clients
        mock_build.assert_called_once_with(
            clients=visible_clients,  # Não sample_clients!
            raw_order_label="Razão Social (A→Z)",
            raw_filter_label="Ativo",
            raw_search_text="",
            selected_ids={"1"},
            is_trash_screen=False,
        )

        mock_compute.assert_called_once_with(mock_state)
        assert result.state == mock_state
        assert result.computed == mock_computed

    @patch("src.modules.clientes.controllers.filter_sort_manager.compute_main_screen_state")
    @patch("src.modules.clientes.controllers.filter_sort_manager.build_main_screen_state")
    def test_compute_for_selection_change_atualiza_batch_flags(
        self,
        mock_build: MagicMock,
        mock_compute: MagicMock,
        manager: FilterSortManager,
        sample_clients: list[ClienteRow],
        mock_state: MainScreenState,
        mock_computed: MainScreenComputed,
    ) -> None:
        """compute_for_selection_change deve recomputar flags de batch com nova seleção."""
        mock_build.return_value = mock_state
        mock_compute.return_value = mock_computed

        visible_clients = sample_clients[:3]

        # Primeira chamada: sem seleção
        inp1 = FilterSortInput(
            clients=sample_clients,
            raw_order_label="CNPJ (A→Z)",
            raw_filter_label="Todos",
            raw_search_text="",
            selected_ids=set(),
            is_trash_screen=False,
        )

        _ = manager.compute_for_selection_change(visible_clients, inp1)

        # Segunda chamada: com seleção
        inp2 = FilterSortInput(
            clients=sample_clients,
            raw_order_label="CNPJ (A→Z)",
            raw_filter_label="Todos",
            raw_search_text="",
            selected_ids={"1", "2"},
            is_trash_screen=False,
        )

        _ = manager.compute_for_selection_change(visible_clients, inp2)

        # Deve ter chamado build duas vezes com seleções diferentes
        assert mock_build.call_count == 2
        assert mock_compute.call_count == 2

        # Verificar que selected_ids mudou entre as chamadas
        call1 = mock_build.call_args_list[0][1]
        call2 = mock_build.call_args_list[1][1]

        assert call1["selected_ids"] == set()
        assert call2["selected_ids"] == {"1", "2"}

    @patch("src.modules.clientes.controllers.filter_sort_manager.compute_main_screen_state")
    @patch("src.modules.clientes.controllers.filter_sort_manager.build_main_screen_state")
    def test_compute_for_selection_change_com_lista_vazia(
        self,
        mock_build: MagicMock,
        mock_compute: MagicMock,
        manager: FilterSortManager,
        sample_clients: list[ClienteRow],
        mock_state: MainScreenState,
        mock_computed: MainScreenComputed,
    ) -> None:
        """compute_for_selection_change deve funcionar com lista vazia de visíveis."""
        mock_build.return_value = mock_state
        mock_compute.return_value = mock_computed

        inp = FilterSortInput(
            clients=sample_clients,
            raw_order_label="Nome (A→Z)",
            raw_filter_label="Inativo",
            raw_search_text="xyz",
            selected_ids=set(),
            is_trash_screen=False,
        )

        # Lista vazia (filtro não encontrou nada)
        result = manager.compute_for_selection_change([], inp)

        mock_build.assert_called_once_with(
            clients=[],
            raw_order_label="Nome (A→Z)",
            raw_filter_label="Inativo",
            raw_search_text="xyz",
            selected_ids=set(),
            is_trash_screen=False,
        )

        assert result.state == mock_state

    @patch("src.modules.clientes.controllers.filter_sort_manager.compute_main_screen_state")
    @patch("src.modules.clientes.controllers.filter_sort_manager.build_main_screen_state")
    def test_compute_for_selection_change_preserva_outros_parametros(
        self,
        mock_build: MagicMock,
        mock_compute: MagicMock,
        manager: FilterSortManager,
        sample_clients: list[ClienteRow],
        mock_state: MainScreenState,
        mock_computed: MainScreenComputed,
    ) -> None:
        """compute_for_selection_change deve preservar filtro/ordem/busca."""
        mock_build.return_value = mock_state
        mock_compute.return_value = mock_computed

        visible_clients = sample_clients[1:3]

        inp = FilterSortInput(
            clients=sample_clients,
            raw_order_label="ID (9→1)",
            raw_filter_label="Ativo",
            raw_search_text="beta",
            selected_ids={"2"},
            is_trash_screen=True,
        )

        result = manager.compute_for_selection_change(visible_clients, inp)

        mock_build.assert_called_once_with(
            clients=visible_clients,
            raw_order_label="ID (9→1)",
            raw_filter_label="Ativo",
            raw_search_text="beta",
            selected_ids={"2"},
            is_trash_screen=True,
        )

        assert result.computed == mock_computed
