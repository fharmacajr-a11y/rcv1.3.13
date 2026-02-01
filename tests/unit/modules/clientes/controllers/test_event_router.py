"""
Testes unitários para event_router.py (MS-22 Event Routing).

Este módulo testa EventRouter de forma headless, sem dependências do Tkinter.
Segue o padrão estabelecido nas microfases anteriores.

Objetivo: Elevar a cobertura de ~60.0% para ≥85%.
Linhas não cobertas alvo: 43-44, 48-50, 54-56.
"""

import pytest

from src.modules.clientes.controllers.event_router import (
    EventAction,
    EventContext,
    EventRouter,
    EventRoutingResult,
)
from src.modules.clientes.controllers.pick_mode_manager import PickModeSnapshot
from src.modules.clientes.controllers.selection_manager import SelectionSnapshot
from src.modules.clientes.core.viewmodel import ClienteRow


# ────────────────────────────────────────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def sample_cliente_rows() -> list[ClienteRow]:
    """Lista de ClienteRow para testes."""
    return [
        ClienteRow(
            id="1",
            razao_social="Empresa Um LTDA",
            cnpj="11.111.111/0001-11",
            nome="Cliente Um",
            whatsapp="11-11111-1111",
            observacoes="",
            status="Ativo",
            ultima_alteracao="2024-01-01",
        ),
        ClienteRow(
            id="2",
            razao_social="Empresa Dois LTDA",
            cnpj="22.222.222/0002-22",
            nome="Cliente Dois",
            whatsapp="22-22222-2222",
            observacoes="",
            status="Ativo",
            ultima_alteracao="2024-01-02",
        ),
    ]


@pytest.fixture
def empty_selection(sample_cliente_rows: list[ClienteRow]) -> SelectionSnapshot:
    """SelectionSnapshot sem seleção."""
    return SelectionSnapshot(
        selected_ids=frozenset(),
        all_clients=sample_cliente_rows,
    )


@pytest.fixture
def single_selection(sample_cliente_rows: list[ClienteRow]) -> SelectionSnapshot:
    """SelectionSnapshot com um cliente selecionado."""
    return SelectionSnapshot(
        selected_ids=frozenset(["1"]),
        all_clients=sample_cliente_rows,
    )


@pytest.fixture
def multiple_selection(sample_cliente_rows: list[ClienteRow]) -> SelectionSnapshot:
    """SelectionSnapshot com múltiplos clientes selecionados."""
    return SelectionSnapshot(
        selected_ids=frozenset(["1", "2"]),
        all_clients=sample_cliente_rows,
    )


@pytest.fixture
def pick_mode_inactive() -> PickModeSnapshot:
    """PickModeSnapshot com pick mode desativado."""
    return PickModeSnapshot(
        is_pick_mode_active=False,
        should_disable_trash_button=False,
        should_disable_topbar_menus=False,
        should_show_pick_banner=False,
        should_disable_crud_buttons=False,
    )


@pytest.fixture
def pick_mode_active() -> PickModeSnapshot:
    """PickModeSnapshot com pick mode ativo."""
    return PickModeSnapshot(
        is_pick_mode_active=True,
        should_disable_trash_button=True,
        should_disable_topbar_menus=True,
        should_show_pick_banner=True,
        should_disable_crud_buttons=True,
    )


# ────────────────────────────────────────────────────────────────────────────────
# Tests: EventContext
# ────────────────────────────────────────────────────────────────────────────────


class TestEventContext:
    """Testes do dataclass EventContext."""

    def test_event_context_creation_without_pick_mode(
        self,
        empty_selection: SelectionSnapshot,
    ):
        """Testa criação de EventContext sem PickModeSnapshot."""
        ctx = EventContext(selection=empty_selection)
        assert ctx.selection == empty_selection
        assert ctx.pick_mode is None

    def test_event_context_creation_with_pick_mode(
        self,
        empty_selection: SelectionSnapshot,
        pick_mode_active: PickModeSnapshot,
    ):
        """Testa criação de EventContext com PickModeSnapshot."""
        ctx = EventContext(selection=empty_selection, pick_mode=pick_mode_active)
        assert ctx.selection == empty_selection
        assert ctx.pick_mode == pick_mode_active

    def test_event_context_immutability(
        self,
        empty_selection: SelectionSnapshot,
    ):
        """Testa imutabilidade do dataclass frozen."""
        ctx = EventContext(selection=empty_selection)
        with pytest.raises(AttributeError):
            ctx.selection = empty_selection  # type: ignore


# ────────────────────────────────────────────────────────────────────────────────
# Tests: EventRoutingResult
# ────────────────────────────────────────────────────────────────────────────────


class TestEventRoutingResult:
    """Testes do dataclass EventRoutingResult."""

    def test_routing_result_noop(self):
        """Testa criação de resultado com ação noop."""
        result = EventRoutingResult(action="noop")
        assert result.action == "noop"

    def test_routing_result_open_editor(self):
        """Testa criação de resultado com ação open_editor."""
        result = EventRoutingResult(action="open_editor")
        assert result.action == "open_editor"

    def test_routing_result_confirm_pick(self):
        """Testa criação de resultado com ação confirm_pick."""
        result = EventRoutingResult(action="confirm_pick")
        assert result.action == "confirm_pick"

    def test_routing_result_delete_selection(self):
        """Testa criação de resultado com ação delete_selection."""
        result = EventRoutingResult(action="delete_selection")
        assert result.action == "delete_selection"

    def test_routing_result_immutability(self):
        """Testa imutabilidade do dataclass frozen."""
        result = EventRoutingResult(action="noop")
        with pytest.raises(AttributeError):
            result.action = "open_editor"  # type: ignore


# ────────────────────────────────────────────────────────────────────────────────
# Tests: EventRouter._is_pick_mode_active (private helper)
# ────────────────────────────────────────────────────────────────────────────────


class TestIsPickModeActive:
    """Testes do método privado _is_pick_mode_active (linhas 43-44)."""

    def test_is_pick_mode_active_when_none(
        self,
        empty_selection: SelectionSnapshot,
    ):
        """Testa _is_pick_mode_active quando pick_mode é None (linha 44)."""
        router = EventRouter()
        ctx = EventContext(selection=empty_selection, pick_mode=None)
        assert router._is_pick_mode_active(ctx) is False  # type: ignore

    def test_is_pick_mode_active_when_inactive(
        self,
        empty_selection: SelectionSnapshot,
        pick_mode_inactive: PickModeSnapshot,
    ):
        """Testa _is_pick_mode_active quando pick mode está desativado (linha 44)."""
        router = EventRouter()
        ctx = EventContext(selection=empty_selection, pick_mode=pick_mode_inactive)
        assert router._is_pick_mode_active(ctx) is False  # type: ignore

    def test_is_pick_mode_active_when_active(
        self,
        empty_selection: SelectionSnapshot,
        pick_mode_active: PickModeSnapshot,
    ):
        """Testa _is_pick_mode_active quando pick mode está ativo (linha 44)."""
        router = EventRouter()
        ctx = EventContext(selection=empty_selection, pick_mode=pick_mode_active)
        assert router._is_pick_mode_active(ctx) is True  # type: ignore


# ────────────────────────────────────────────────────────────────────────────────
# Tests: EventRouter.route_double_click
# ────────────────────────────────────────────────────────────────────────────────


class TestRouteDoubleClick:
    """Testes do método route_double_click (linhas 48-50)."""

    def test_route_double_click_normal_mode(
        self,
        single_selection: SelectionSnapshot,
        pick_mode_inactive: PickModeSnapshot,
    ):
        """Testa duplo clique em modo normal → open_editor (linha 50)."""
        router = EventRouter()
        ctx = EventContext(selection=single_selection, pick_mode=pick_mode_inactive)
        result = router.route_double_click(ctx)
        assert result.action == "open_editor"

    def test_route_double_click_normal_mode_without_pick_snapshot(
        self,
        single_selection: SelectionSnapshot,
    ):
        """Testa duplo clique em modo normal sem PickModeSnapshot → open_editor."""
        router = EventRouter()
        ctx = EventContext(selection=single_selection, pick_mode=None)
        result = router.route_double_click(ctx)
        assert result.action == "open_editor"

    def test_route_double_click_pick_mode_active(
        self,
        single_selection: SelectionSnapshot,
        pick_mode_active: PickModeSnapshot,
    ):
        """Testa duplo clique em pick mode → confirm_pick (linha 49)."""
        router = EventRouter()
        ctx = EventContext(selection=single_selection, pick_mode=pick_mode_active)
        result = router.route_double_click(ctx)
        assert result.action == "confirm_pick"

    def test_route_double_click_empty_selection_normal_mode(
        self,
        empty_selection: SelectionSnapshot,
        pick_mode_inactive: PickModeSnapshot,
    ):
        """Testa duplo clique sem seleção em modo normal → open_editor."""
        router = EventRouter()
        ctx = EventContext(selection=empty_selection, pick_mode=pick_mode_inactive)
        result = router.route_double_click(ctx)
        assert result.action == "open_editor"

    def test_route_double_click_empty_selection_pick_mode(
        self,
        empty_selection: SelectionSnapshot,
        pick_mode_active: PickModeSnapshot,
    ):
        """Testa duplo clique sem seleção em pick mode → confirm_pick."""
        router = EventRouter()
        ctx = EventContext(selection=empty_selection, pick_mode=pick_mode_active)
        result = router.route_double_click(ctx)
        assert result.action == "confirm_pick"

    def test_route_double_click_multiple_selection_normal_mode(
        self,
        multiple_selection: SelectionSnapshot,
        pick_mode_inactive: PickModeSnapshot,
    ):
        """Testa duplo clique com múltipla seleção em modo normal → open_editor."""
        router = EventRouter()
        ctx = EventContext(selection=multiple_selection, pick_mode=pick_mode_inactive)
        result = router.route_double_click(ctx)
        assert result.action == "open_editor"

    def test_route_double_click_multiple_selection_pick_mode(
        self,
        multiple_selection: SelectionSnapshot,
        pick_mode_active: PickModeSnapshot,
    ):
        """Testa duplo clique com múltipla seleção em pick mode → confirm_pick."""
        router = EventRouter()
        ctx = EventContext(selection=multiple_selection, pick_mode=pick_mode_active)
        result = router.route_double_click(ctx)
        assert result.action == "confirm_pick"


# ────────────────────────────────────────────────────────────────────────────────
# Tests: EventRouter.route_delete_key
# ────────────────────────────────────────────────────────────────────────────────


class TestRouteDeleteKey:
    """Testes do método route_delete_key (linhas 54-56)."""

    def test_route_delete_key_normal_mode(
        self,
        single_selection: SelectionSnapshot,
        pick_mode_inactive: PickModeSnapshot,
    ):
        """Testa tecla Delete em modo normal → delete_selection (linha 56)."""
        router = EventRouter()
        ctx = EventContext(selection=single_selection, pick_mode=pick_mode_inactive)
        result = router.route_delete_key(ctx)
        assert result.action == "delete_selection"

    def test_route_delete_key_normal_mode_without_pick_snapshot(
        self,
        single_selection: SelectionSnapshot,
    ):
        """Testa tecla Delete em modo normal sem PickModeSnapshot → delete_selection."""
        router = EventRouter()
        ctx = EventContext(selection=single_selection, pick_mode=None)
        result = router.route_delete_key(ctx)
        assert result.action == "delete_selection"

    def test_route_delete_key_pick_mode_active(
        self,
        single_selection: SelectionSnapshot,
        pick_mode_active: PickModeSnapshot,
    ):
        """Testa tecla Delete em pick mode → noop (linha 55)."""
        router = EventRouter()
        ctx = EventContext(selection=single_selection, pick_mode=pick_mode_active)
        result = router.route_delete_key(ctx)
        assert result.action == "noop"

    def test_route_delete_key_empty_selection_normal_mode(
        self,
        empty_selection: SelectionSnapshot,
        pick_mode_inactive: PickModeSnapshot,
    ):
        """Testa tecla Delete sem seleção em modo normal → delete_selection."""
        router = EventRouter()
        ctx = EventContext(selection=empty_selection, pick_mode=pick_mode_inactive)
        result = router.route_delete_key(ctx)
        assert result.action == "delete_selection"

    def test_route_delete_key_empty_selection_pick_mode(
        self,
        empty_selection: SelectionSnapshot,
        pick_mode_active: PickModeSnapshot,
    ):
        """Testa tecla Delete sem seleção em pick mode → noop."""
        router = EventRouter()
        ctx = EventContext(selection=empty_selection, pick_mode=pick_mode_active)
        result = router.route_delete_key(ctx)
        assert result.action == "noop"

    def test_route_delete_key_multiple_selection_normal_mode(
        self,
        multiple_selection: SelectionSnapshot,
        pick_mode_inactive: PickModeSnapshot,
    ):
        """Testa tecla Delete com múltipla seleção em modo normal → delete_selection."""
        router = EventRouter()
        ctx = EventContext(selection=multiple_selection, pick_mode=pick_mode_inactive)
        result = router.route_delete_key(ctx)
        assert result.action == "delete_selection"

    def test_route_delete_key_multiple_selection_pick_mode(
        self,
        multiple_selection: SelectionSnapshot,
        pick_mode_active: PickModeSnapshot,
    ):
        """Testa tecla Delete com múltipla seleção em pick mode → noop."""
        router = EventRouter()
        ctx = EventContext(selection=multiple_selection, pick_mode=pick_mode_active)
        result = router.route_delete_key(ctx)
        assert result.action == "noop"


# ────────────────────────────────────────────────────────────────────────────────
# Tests: Integration Scenarios
# ────────────────────────────────────────────────────────────────────────────────


class TestEventRouterIntegration:
    """Testes de cenários completos de uso do EventRouter."""

    def test_full_workflow_normal_mode(
        self,
        single_selection: SelectionSnapshot,
        pick_mode_inactive: PickModeSnapshot,
    ):
        """Testa fluxo completo em modo normal: duplo clique e Delete."""
        router = EventRouter()
        ctx = EventContext(selection=single_selection, pick_mode=pick_mode_inactive)

        # Duplo clique deve abrir editor
        double_click_result = router.route_double_click(ctx)
        assert double_click_result.action == "open_editor"

        # Delete deve excluir seleção
        delete_result = router.route_delete_key(ctx)
        assert delete_result.action == "delete_selection"

    def test_full_workflow_pick_mode(
        self,
        single_selection: SelectionSnapshot,
        pick_mode_active: PickModeSnapshot,
    ):
        """Testa fluxo completo em pick mode: duplo clique e Delete."""
        router = EventRouter()
        ctx = EventContext(selection=single_selection, pick_mode=pick_mode_active)

        # Duplo clique deve confirmar pick
        double_click_result = router.route_double_click(ctx)
        assert double_click_result.action == "confirm_pick"

        # Delete deve fazer nada (noop)
        delete_result = router.route_delete_key(ctx)
        assert delete_result.action == "noop"

    def test_mode_transition_scenario(
        self,
        single_selection: SelectionSnapshot,
        pick_mode_inactive: PickModeSnapshot,
        pick_mode_active: PickModeSnapshot,
    ):
        """Testa transição entre modo normal e pick mode."""
        router = EventRouter()

        # Contexto em modo normal
        ctx_normal = EventContext(selection=single_selection, pick_mode=pick_mode_inactive)
        assert router.route_double_click(ctx_normal).action == "open_editor"
        assert router.route_delete_key(ctx_normal).action == "delete_selection"

        # Contexto em pick mode (simula transição)
        ctx_pick = EventContext(selection=single_selection, pick_mode=pick_mode_active)
        assert router.route_double_click(ctx_pick).action == "confirm_pick"
        assert router.route_delete_key(ctx_pick).action == "noop"

    def test_router_is_stateless(
        self,
        single_selection: SelectionSnapshot,
        pick_mode_active: PickModeSnapshot,
        pick_mode_inactive: PickModeSnapshot,
    ):
        """Testa que EventRouter é stateless (sem estado interno)."""
        router = EventRouter()

        # Primeira chamada com pick mode ativo
        ctx1 = EventContext(selection=single_selection, pick_mode=pick_mode_active)
        result1 = router.route_double_click(ctx1)
        assert result1.action == "confirm_pick"

        # Segunda chamada com pick mode inativo (não deve ser influenciada pela primeira)
        ctx2 = EventContext(selection=single_selection, pick_mode=pick_mode_inactive)
        result2 = router.route_double_click(ctx2)
        assert result2.action == "open_editor"


# ────────────────────────────────────────────────────────────────────────────────
# Tests: Edge Cases
# ────────────────────────────────────────────────────────────────────────────────


class TestEdgeCases:
    """Testes de casos extremos e edge cases."""

    def test_event_context_with_empty_all_clients(self):
        """Testa EventContext com lista de clientes vazia."""
        empty_snapshot = SelectionSnapshot(
            selected_ids=frozenset(),
            all_clients=[],
        )
        ctx = EventContext(selection=empty_snapshot, pick_mode=None)
        router = EventRouter()

        # Não deve lançar exceção
        result_double_click = router.route_double_click(ctx)
        assert result_double_click.action == "open_editor"

        result_delete = router.route_delete_key(ctx)
        assert result_delete.action == "delete_selection"

    def test_multiple_router_instances(
        self,
        single_selection: SelectionSnapshot,
        pick_mode_active: PickModeSnapshot,
    ):
        """Testa que múltiplas instâncias de EventRouter se comportam identicamente."""
        router1 = EventRouter()
        router2 = EventRouter()

        ctx = EventContext(selection=single_selection, pick_mode=pick_mode_active)

        result1 = router1.route_double_click(ctx)
        result2 = router2.route_double_click(ctx)

        assert result1.action == result2.action == "confirm_pick"

    def test_result_immutability_across_calls(
        self,
        single_selection: SelectionSnapshot,
        pick_mode_inactive: PickModeSnapshot,
    ):
        """Testa que resultados anteriores não são afetados por novas chamadas."""
        router = EventRouter()
        ctx = EventContext(selection=single_selection, pick_mode=pick_mode_inactive)

        result1 = router.route_double_click(ctx)
        assert result1.action == "open_editor"

        # Criar novo contexto com pick mode ativo
        pick_mode_active = PickModeSnapshot(
            is_pick_mode_active=True,
            should_disable_trash_button=True,
            should_disable_topbar_menus=True,
            should_show_pick_banner=True,
            should_disable_crud_buttons=True,
        )
        ctx2 = EventContext(selection=single_selection, pick_mode=pick_mode_active)
        result2 = router.route_double_click(ctx2)

        # result1 deve permanecer inalterado (imutável)
        assert result1.action == "open_editor"
        assert result2.action == "confirm_pick"

    def test_all_action_types_covered(self):
        """Testa que todas as 4 ações possíveis podem ser retornadas."""
        router = EventRouter()
        empty_snapshot = SelectionSnapshot(
            selected_ids=frozenset(),
            all_clients=[],
        )

        pick_inactive = PickModeSnapshot(
            is_pick_mode_active=False,
            should_disable_trash_button=False,
            should_disable_topbar_menus=False,
            should_show_pick_banner=False,
            should_disable_crud_buttons=False,
        )

        pick_active = PickModeSnapshot(
            is_pick_mode_active=True,
            should_disable_trash_button=True,
            should_disable_topbar_menus=True,
            should_show_pick_banner=True,
            should_disable_crud_buttons=True,
        )

        # Coletar todas as ações possíveis
        actions_collected: set[EventAction] = set()

        # open_editor: duplo clique em modo normal
        ctx1 = EventContext(selection=empty_snapshot, pick_mode=pick_inactive)
        actions_collected.add(router.route_double_click(ctx1).action)

        # confirm_pick: duplo clique em pick mode
        ctx2 = EventContext(selection=empty_snapshot, pick_mode=pick_active)
        actions_collected.add(router.route_double_click(ctx2).action)

        # delete_selection: Delete em modo normal
        ctx3 = EventContext(selection=empty_snapshot, pick_mode=pick_inactive)
        actions_collected.add(router.route_delete_key(ctx3).action)

        # noop: Delete em pick mode
        ctx4 = EventContext(selection=empty_snapshot, pick_mode=pick_active)
        actions_collected.add(router.route_delete_key(ctx4).action)

        # Verificar que todas as 4 ações foram cobertas
        assert actions_collected == {"noop", "open_editor", "confirm_pick", "delete_selection"}
