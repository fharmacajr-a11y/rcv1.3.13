# -*- coding: utf-8 -*-
"""Testes headless para QuickActionsViewModel."""

from __future__ import annotations

import pytest

from src.modules.hub.viewmodels.quick_actions_vm import (
    QuickActionItemView,
    QuickActionsViewModel,
    QuickActionsViewState,
)


class TestQuickActionItemView:
    """Testes para QuickActionItemView."""

    def test_create_item(self):
        """Deve criar item de atalho com valores corretos."""
        item = QuickActionItemView(
            id="clientes",
            label="Clientes",
            description="Gerenciar clientes",
            bootstyle="info",
            is_enabled=True,
            order=10,
            category="cadastros",
        )

        assert item.id == "clientes"
        assert item.label == "Clientes"
        assert item.description == "Gerenciar clientes"
        assert item.bootstyle == "info"
        assert item.is_enabled is True
        assert item.order == 10
        assert item.category == "cadastros"

    def test_item_is_immutable(self):
        """QuickActionItemView deve ser imutável (frozen)."""
        item = QuickActionItemView(id="test", label="Test")

        with pytest.raises(Exception):  # dataclass frozen
            item.label = "Changed"  # type: ignore


class TestQuickActionsViewState:
    """Testes para QuickActionsViewState."""

    def test_default_state(self):
        """Deve criar estado vazio por padrão."""
        state = QuickActionsViewState()

        assert state.actions == []
        assert state.is_loading is False
        assert state.error_message is None

    def test_state_with_actions(self):
        """Deve criar estado com lista de ações."""
        actions = [
            QuickActionItemView(id="action1", label="Action 1", order=1),
            QuickActionItemView(id="action2", label="Action 2", order=2),
        ]

        state = QuickActionsViewState(actions=actions)

        assert len(state.actions) == 2
        assert state.actions[0].id == "action1"
        assert state.actions[1].id == "action2"

    def test_state_is_immutable(self):
        """QuickActionsViewState deve ser imutável (frozen)."""
        state = QuickActionsViewState()

        with pytest.raises(Exception):  # dataclass frozen
            state.is_loading = True  # type: ignore


class TestQuickActionsViewModel:
    """Testes para QuickActionsViewModel."""

    @pytest.fixture
    def vm(self):
        """ViewModel para testes."""
        return QuickActionsViewModel(features_service=None)

    def test_build_state_returns_all_actions(self, vm):
        """Deve retornar todos os atalhos padrão do HUB."""
        state = vm.build_state()

        assert isinstance(state, QuickActionsViewState)
        # Removidos farmacia_popular, sifap, senhas e auditoria (5 actions restantes)
        assert len(state.actions) == 5
        assert state.is_loading is False
        assert state.error_message is None

        # Verificar IDs dos atalhos essenciais
        action_ids = {a.id for a in state.actions}
        for expected_id in {"clientes", "fluxo_caixa", "anvisa", "sngpc", "sites"}:
            assert expected_id in action_ids

    def test_build_state_correct_labels(self, vm):
        """Deve ter labels corretos para cada atalho."""
        state = vm.build_state()

        actions_map = {a.id: a for a in state.actions}

        # Verificar labels das ações essenciais (sem farmacia_popular, sifap, senhas e auditoria)
        assert actions_map["clientes"].label == "Clientes"
        assert actions_map["fluxo_caixa"].label == "Fluxo de Caixa"
        assert actions_map["anvisa"].label == "Anvisa"
        assert actions_map["sngpc"].label == "Sngpc"
        assert actions_map["sites"].label == "Sites"

    def test_build_state_correct_categories(self, vm):
        """Deve agrupar atalhos nas categorias corretas."""
        state = vm.build_state()

        # Agrupar por categoria
        by_category = {}
        for action in state.actions:
            if action.category not in by_category:
                by_category[action.category] = []
            by_category[action.category].append(action.id)

        # Verificar categorias principais (sem farmacia_popular, sifap, senhas, auditoria)
        assert set(by_category["cadastros"]) == {"clientes"}
        assert set(by_category["gestao"]) == {"fluxo_caixa"}
        assert set(by_category["regulatorio"]) == {
            "anvisa",
            "sngpc",
        }
        # MF-39: sites em categoria "utilidades"
        assert "sites" in by_category["utilidades"]

    def test_build_state_sorted_by_order(self, vm):
        """Deve ordenar atalhos por campo order."""
        state = vm.build_state()

        # Verificar que está ordenado
        orders = [a.order for a in state.actions]
        assert orders == sorted(orders), "Ações devem estar ordenadas por 'order'"

        # Verificar ordem específica (MF-39: sites agora é o último, não sifap)
        action_ids = [a.id for a in state.actions]
        assert action_ids[0] == "clientes"  # order=10 (sempre primeiro)
        # senhas e auditoria removidos – segundo agora é fluxo_caixa
        assert action_ids[-1] == "sites"  # order=90 (sempre último)

    def test_build_state_all_enabled_by_default(self, vm):
        """Deve retornar todos atalhos habilitados por padrão."""
        state = vm.build_state()

        for action in state.actions:
            assert action.is_enabled is True

    def test_build_state_has_descriptions(self, vm):
        """Deve incluir descrições para cada atalho."""
        state = vm.build_state()

        for action in state.actions:
            assert action.description is not None
            assert len(action.description) > 0

    def test_build_state_has_metadata(self, vm):
        """Deve incluir metadata completa para cada atalho."""
        state = vm.build_state()

        # Verificar que actions têm campos obrigatórios
        for action in state.actions:
            assert action.id is not None
            assert action.label is not None
            assert action.category is not None
            # bootstyle é opcional (tag semântica apenas, não passado para widgets)

        # Verificar IDs específicos existem
        actions_map = {a.id: a for a in state.actions}
        assert "clientes" in actions_map
        assert "fluxo_caixa" in actions_map
        assert "anvisa" in actions_map
        # bootstyle não mais validado (tag semântica opcional)
