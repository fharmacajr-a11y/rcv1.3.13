# -*- coding: utf-8 -*-
"""Testes unitários para cards clicáveis em dashboard_center.py - FASE HUB-UX-01.

Valida que os cards de indicadores (Clientes, Pendências, Tarefas) são clicáveis
e executam os callbacks apropriados quando fornecidos.

NOTA HUB-TEST-TK-01:
- Alguns testes dependem de Tkinter funcional (tk.Tk()).
- Em ambientes com Tcl/Tk mal configurado, esses testes são automaticamente
  marcados como skip com mensagem clara.
- Erro típico: "couldn't read file .../tcl8.6/auto.tcl" ou "Can't find a usable tk.tcl".
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
import ttkbootstrap as tb

from src.modules.hub.dashboard_service import DashboardSnapshot
from src.modules.hub.viewmodels import DashboardViewModel
from src.modules.hub.views.dashboard_center import (
    _build_indicator_card,
    build_dashboard_center,
)

if TYPE_CHECKING:
    pass


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def test_frame(tk_root):
    """Cria frame de teste dentro do root."""
    frame = tb.Frame(tk_root)
    frame.pack()
    return frame


@pytest.fixture
def empty_snapshot():
    """DashboardSnapshot vazio para testes."""
    return DashboardSnapshot(
        active_clients=0,
        pending_obligations=0,
        tasks_today=0,
        cash_in_month=0.0,
        upcoming_deadlines=[],
        hot_items=[],
        pending_tasks=[],
        clients_of_the_day=[],
        risk_radar={},
        recent_activity=[],
    )


@pytest.fixture
def populated_snapshot():
    """DashboardSnapshot com dados para testes."""
    return DashboardSnapshot(
        active_clients=42,
        pending_obligations=5,
        tasks_today=3,
        cash_in_month=15000.0,
        upcoming_deadlines=[],
        hot_items=["Envio SNGPC urgente"],
        pending_tasks=[],
        clients_of_the_day=[],
        risk_radar={
            "ANVISA": {"pending": 0, "overdue": 0, "status": "green"},
            "SNGPC": {"pending": 2, "overdue": 1, "status": "red"},
            "SIFAP": {"pending": 1, "overdue": 0, "status": "yellow"},
        },
        recent_activity=[],
    )


def _snapshot_to_state(snapshot: DashboardSnapshot):
    """Helper para converter DashboardSnapshot em DashboardViewState (para testes)."""
    vm = DashboardViewModel(service=lambda org_id, today: snapshot)
    return vm.load(org_id="test-org", today=None)


# ============================================================================
# TESTES PARA _build_indicator_card COM on_click
# ============================================================================


class TestBuildIndicatorCardClickable:
    """Testes para _build_indicator_card com callback on_click."""

    def test_card_without_callback_has_no_cursor(self, test_frame):
        """Card sem callback não deve ter cursor hand2."""
        card = _build_indicator_card(
            test_frame,
            label="Test Card",
            value=10,
            bootstyle="primary",
            on_click=None,
        )

        # Cursor padrão não é "hand2"
        cursor_str = str(card.cget("cursor"))
        assert "hand2" not in cursor_str

    def test_card_with_callback_has_hand_cursor(self, test_frame):
        """Card com callback deve ter cursor hand2."""
        mock_callback = MagicMock()
        card = _build_indicator_card(
            test_frame,
            label="Clickable Card",
            value=42,
            bootstyle="info",
            on_click=mock_callback,
        )

        # Cursor deve ser "hand2"
        cursor_str = str(card.cget("cursor"))
        assert "hand2" in cursor_str

    def test_card_click_triggers_callback(self, test_frame):
        """Clicar no card deve chamar o callback fornecido."""
        mock_callback = MagicMock()
        card = _build_indicator_card(
            test_frame,
            label="Clickable Card",
            value=100,
            bootstyle="success",
            on_click=mock_callback,
        )

        # Simular clique no frame principal
        card.event_generate("<Button-1>", x=5, y=5)
        card.update()

        # Callback deve ter sido chamado
        assert mock_callback.call_count >= 1

    def test_card_labels_propagate_click(self, test_frame):
        """Clicar em labels internos do card deve chamar o callback."""
        mock_callback = MagicMock()
        card = _build_indicator_card(
            test_frame,
            label="Card com Labels",
            value=99,
            bootstyle="warning",
            on_click=mock_callback,
        )

        # Pegar labels internos (value_label e text_label)
        labels = [child for child in card.winfo_children() if isinstance(child, tb.Label)]
        assert len(labels) >= 2  # Deve ter pelo menos 2 labels

        # Simular clique no primeiro label
        labels[0].event_generate("<Button-1>", x=2, y=2)
        labels[0].update()

        # Callback deve ter sido chamado
        assert mock_callback.call_count >= 1


# ============================================================================
# TESTES PARA build_dashboard_center COM CALLBACKS DE CARDS
# ============================================================================


class TestBuildDashboardCenterWithCardCallbacks:
    """Testes para build_dashboard_center com callbacks de cards clicáveis."""

    def test_dashboard_accepts_card_callbacks(self, test_frame, empty_snapshot):
        """Dashboard deve aceitar callbacks opcionais para cards sem erro."""
        mock_clients = MagicMock()
        mock_pendencias = MagicMock()
        mock_tarefas = MagicMock()

        # Não deve lançar exceção
        build_dashboard_center(
            test_frame,
            _snapshot_to_state(empty_snapshot),
            on_card_clients_click=mock_clients,
            on_card_pendencias_click=mock_pendencias,
            on_card_tarefas_click=mock_tarefas,
        )

        # Callbacks não devem ter sido chamados ainda (só após clique)
        mock_clients.assert_not_called()
        mock_pendencias.assert_not_called()
        mock_tarefas.assert_not_called()

    def test_dashboard_without_card_callbacks_still_works(self, test_frame, populated_snapshot):
        """Dashboard sem callbacks de cards (retrocompatibilidade) deve funcionar."""
        # Não deve lançar exceção (chamadas antigas sem os novos parâmetros)
        build_dashboard_center(
            test_frame,
            _snapshot_to_state(populated_snapshot),
            on_new_task=None,
            on_new_obligation=None,
        )

        # Dashboard deve ter sido criado normalmente
        assert len(test_frame.winfo_children()) > 0

    def test_dashboard_cards_have_hand_cursor_when_callbacks_provided(self, test_frame, populated_snapshot):
        """Cards devem ter cursor hand2 quando callbacks são fornecidos."""
        build_dashboard_center(
            test_frame,
            _snapshot_to_state(populated_snapshot),
            on_card_clients_click=lambda state: None,
            on_card_pendencias_click=lambda state: None,
            on_card_tarefas_click=lambda state: None,
        )

        # Buscar frames de cards (provavelmente dentro de um container)
        # A estrutura é: main_container -> cards_frame -> cards individuais
        main_container = test_frame.winfo_children()[0]
        cards_frame = main_container.winfo_children()[0]  # Primeiro filho é cards_frame

        # Pegar frames de cards (devem ter cursor="hand2")
        card_frames = [child for child in cards_frame.winfo_children() if isinstance(child, tb.Frame)]

        # Deve ter pelo menos 3 cards (Clientes, Pendências, Tarefas)
        assert len(card_frames) >= 3

        # Todos os cards devem ter cursor hand2
        for card in card_frames[:3]:  # Primeiros 3 cards
            cursor_str = str(card.cget("cursor"))
            assert "hand2" in cursor_str

    def test_dashboard_cards_without_callbacks_have_no_hand_cursor(self, test_frame, populated_snapshot):
        """Cards sem callbacks não devem ter cursor hand2."""
        build_dashboard_center(
            test_frame,
            _snapshot_to_state(populated_snapshot),
            # Sem passar callbacks de cards
        )

        # Buscar cards
        main_container = test_frame.winfo_children()[0]
        cards_frame = main_container.winfo_children()[0]
        card_frames = [child for child in cards_frame.winfo_children() if isinstance(child, tb.Frame)]
        # Cards sem callbacks não devem ter cursor hand2
        for card in card_frames[:3]:
            cursor_str = str(card.cget("cursor"))
            assert "hand2" not in cursor_str
            assert card.cget("cursor") != "hand2"


# ============================================================================
# TESTES DE INTEGRAÇÃO LEVE
# ============================================================================


class TestCardClickableIntegration:
    """Testes de integração para validar fluxo completo de clique em cards."""

    def test_full_workflow_clients_card_click(self, test_frame, populated_snapshot):
        """Fluxo completo: criar dashboard, clicar em card Clientes, callback executado."""
        click_count = {"value": 0}

        def on_clients_click(state):
            click_count["value"] += 1

        # Criar dashboard com callback
        build_dashboard_center(
            test_frame,
            _snapshot_to_state(populated_snapshot),
            on_card_clients_click=on_clients_click,
        )

        # Encontrar card de Clientes (primeiro card)
        main_container = test_frame.winfo_children()[0]
        cards_frame = main_container.winfo_children()[0]
        clients_card = cards_frame.winfo_children()[0]

        # Simular clique
        clients_card.event_generate("<Button-1>", x=10, y=10)
        clients_card.update()

        # Callback deve ter sido chamado
        assert click_count["value"] >= 1

    def test_multiple_clicks_on_different_cards(self, test_frame, populated_snapshot):
        """Clicar em múltiplos cards deve chamar callbacks distintos."""
        clicks = {"clients": 0, "pendencias": 0, "tarefas": 0}

        def on_clients(state):
            clicks["clients"] += 1

        def on_pendencias(state):
            clicks["pendencias"] += 1

        def on_tarefas(state):
            clicks["tarefas"] += 1

        # Criar dashboard
        build_dashboard_center(
            test_frame,
            _snapshot_to_state(populated_snapshot),
            on_card_clients_click=on_clients,
            on_card_pendencias_click=on_pendencias,
            on_card_tarefas_click=on_tarefas,
        )

        # Encontrar cards
        main_container = test_frame.winfo_children()[0]
        cards_frame = main_container.winfo_children()[0]
        card_frames = [child for child in cards_frame.winfo_children() if isinstance(child, tb.Frame)]

        # Clicar em cada card
        for card in card_frames[:3]:
            card.event_generate("<Button-1>", x=5, y=5)
            card.update()

        # Cada callback deve ter sido chamado pelo menos uma vez
        assert clicks["clients"] >= 1
        assert clicks["pendencias"] >= 1
        assert clicks["tarefas"] >= 1


# ============================================================================
# TESTES DE EDGE CASES
# ============================================================================


class TestCardClickableEdgeCases:
    """Testes de casos extremos para cards clicáveis."""

    def test_card_with_zero_value_is_still_clickable(self, test_frame):
        """Card com valor 0 deve permanecer clicável se callback fornecido."""
        mock_callback = MagicMock()
        card = _build_indicator_card(
            test_frame,
            label="Zero Value",
            value=0,
            bootstyle="success",
            on_click=mock_callback,
        )

        cursor_str = str(card.cget("cursor"))
        assert "hand2" in cursor_str

        card.event_generate("<Button-1>", x=3, y=3)
        card.update()

        assert mock_callback.call_count >= 1

    def test_card_with_custom_value_text_is_clickable(self, test_frame):
        """Card com value_text customizado deve permanecer clicável."""
        mock_callback = MagicMock()
        card = _build_indicator_card(
            test_frame,
            label="Custom Text",
            value=100,
            bootstyle="danger",
            value_text="100 ⚠",
            on_click=mock_callback,
        )

        cursor_str = str(card.cget("cursor"))
        assert "hand2" in cursor_str

        card.event_generate("<Button-1>", x=4, y=4)
        card.update()

        assert mock_callback.call_count >= 1

    def test_none_callback_does_not_crash(self, test_frame):
        """Passar on_click=None explicitamente não deve causar erro."""
        # Não deve lançar exceção
        card = _build_indicator_card(
            test_frame,
            label="Explicit None",
            value=50,
            bootstyle="primary",
            on_click=None,
        )

        # Tentar clicar não deve causar erro (mesmo sem callback)
        card.event_generate("<Button-1>", x=1, y=1)
        card.update()

        # Não deve ter erro (sem callback para chamar)
        assert True  # Se chegou aqui, passou
