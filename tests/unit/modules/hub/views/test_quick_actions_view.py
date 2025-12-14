# -*- coding: utf-8 -*-
"""Testes headless/mock para a view de atalhos rápidos."""

from __future__ import annotations


from src.modules.hub.viewmodels.quick_actions_vm import (
    QuickActionItemView,
    QuickActionsViewState,
)


class TestQuickActionsViewState:
    """Testes para garantir que QuickActionsViewState é usável pela view."""

    def test_can_create_state_with_few_actions(self):
        """Deve criar estado com poucos atalhos para teste."""
        actions = [
            QuickActionItemView(
                id="clientes",
                label="Clientes",
                description="Gerenciar clientes",
                bootstyle="info",
                order=10,
                category="cadastros",
            ),
            QuickActionItemView(
                id="anvisa",
                label="Anvisa",
                description="Regulatório Anvisa",
                bootstyle="secondary",
                order=50,
                category="regulatorio",
            ),
        ]

        state = QuickActionsViewState(actions=actions)

        assert len(state.actions) == 2
        assert state.actions[0].id == "clientes"
        assert state.actions[1].id == "anvisa"

    def test_can_iterate_actions(self):
        """Deve permitir iteração sobre as ações."""
        actions = [QuickActionItemView(id=f"action{i}", label=f"Action {i}", order=i) for i in range(3)]

        state = QuickActionsViewState(actions=actions)

        action_ids = []
        for action in state.actions:
            action_ids.append(action.id)

        assert action_ids == ["action0", "action1", "action2"]

    def test_can_group_by_category(self):
        """Deve permitir agrupamento por categoria."""
        actions = [
            QuickActionItemView(id="a1", label="A1", category="cat1", order=1),
            QuickActionItemView(id="a2", label="A2", category="cat1", order=2),
            QuickActionItemView(id="b1", label="B1", category="cat2", order=3),
        ]

        state = QuickActionsViewState(actions=actions)

        # Agrupar manualmente (como a view faria)
        by_category = {}
        for action in state.actions:
            if action.category not in by_category:
                by_category[action.category] = []
            by_category[action.category].append(action)

        assert len(by_category["cat1"]) == 2
        assert len(by_category["cat2"]) == 1
        assert by_category["cat1"][0].id == "a1"
        assert by_category["cat1"][1].id == "a2"
        assert by_category["cat2"][0].id == "b1"

    def test_disabled_action_has_flag(self):
        """Deve identificar ações desabilitadas."""
        actions = [
            QuickActionItemView(id="enabled", label="Enabled", is_enabled=True),
            QuickActionItemView(id="disabled", label="Disabled", is_enabled=False),
        ]

        state = QuickActionsViewState(actions=actions)

        enabled_action = [a for a in state.actions if a.id == "enabled"][0]
        disabled_action = [a for a in state.actions if a.id == "disabled"][0]

        assert enabled_action.is_enabled is True
        assert disabled_action.is_enabled is False

    def test_error_state(self):
        """Deve suportar estado de erro."""
        state = QuickActionsViewState(
            actions=[],
            is_loading=False,
            error_message="Erro ao carregar atalhos",
        )

        assert state.error_message is not None
        assert "Erro" in state.error_message
        assert len(state.actions) == 0

    def test_loading_state(self):
        """Deve suportar estado de loading."""
        state = QuickActionsViewState(
            actions=[],
            is_loading=True,
        )

        assert state.is_loading is True
        assert state.error_message is None

    def test_action_has_all_display_properties(self):
        """Ação deve ter todas as propriedades para renderização."""
        action = QuickActionItemView(
            id="test",
            label="Test Action",
            description="Test description",
            bootstyle="primary",
            is_enabled=True,
            order=100,
            category="test_category",
        )

        # Verificar que todas as propriedades estão acessíveis
        assert action.id == "test"
        assert action.label == "Test Action"
        assert action.description == "Test description"
        assert action.bootstyle == "primary"
        assert action.is_enabled is True
        assert action.order == 100
        assert action.category == "test_category"

    def test_can_sort_actions_by_order(self):
        """Deve permitir ordenação por campo order."""
        actions = [
            QuickActionItemView(id="c", label="C", order=30),
            QuickActionItemView(id="a", label="A", order=10),
            QuickActionItemView(id="b", label="B", order=20),
        ]

        state = QuickActionsViewState(actions=actions)

        # Ordenar (como a view faria se necessário)
        sorted_actions = sorted(state.actions, key=lambda a: a.order)

        assert sorted_actions[0].id == "a"
        assert sorted_actions[1].id == "b"
        assert sorted_actions[2].id == "c"
