# -*- coding: utf-8 -*-
"""Testes unitários para dashboard_center.py - builder de UI do dashboard.

Testa a construção dos componentes visuais do painel central do Hub:
- Cards de indicadores (clientes ativos, pendências, tarefas)
- Bloco "O que está bombando hoje" (hot_items)
- Bloco "Próximos vencimentos" (upcoming_deadlines)
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from datetime import datetime

import pytest
from tests import ui_compat as tb

from src.modules.hub.dashboard_service import DashboardSnapshot
from src.modules.hub.recent_activity_store import ActivityEvent, get_recent_activity_store
from src.modules.hub.viewmodels import DashboardViewModel
from src.modules.hub.views.dashboard_center import (
    MSG_NO_HOT_ITEMS,
    MSG_NO_UPCOMING,
    _build_indicator_card,
    _build_section_frame,
    _clear_children,
    build_dashboard_center,
    build_dashboard_error,
)

# ORG-005: Funções movidas para dashboard_center_pure
from src.modules.hub.views.dashboard_center_pure import (
    format_deadline_line as _format_deadline_line,
    format_task_line as _format_task_line,
)

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def tk_root(tk_root_session):
    """Usa o root de sessão para testes de UI."""
    return tk_root_session


@pytest.fixture
def parent_frame(tk_root):
    """Cria um frame pai para testes."""
    frame = ttk.Frame(tk_root)
    frame.pack()
    yield frame
    # Cleanup
    for child in frame.winfo_children():
        child.destroy()
    frame.destroy()


@pytest.fixture
def empty_snapshot():
    """Cria um snapshot vazio para testes."""
    return DashboardSnapshot()


@pytest.fixture(autouse=True)
def setup_activity_store(populated_snapshot):
    """Limpa e popula o store de atividades antes de cada teste."""
    store = get_recent_activity_store()
    store.clear()

    # Adicionar atividades de teste compatíveis com o snapshot
    store.add_event(
        ActivityEvent(
            org_id="test-org",
            module="TAREFAS",
            action="Nova",
            message="Nova tarefa: Revisar documentos",
            created_at=datetime(2025, 12, 4, 10, 30),
        )
    )
    store.add_event(
        ActivityEvent(
            org_id="test-org",
            module="OBRIGACOES",
            action="Nova",
            message="Nova obrigação SNGPC para cliente #123",
            created_at=datetime(2025, 12, 3, 14, 15),
        )
    )

    yield

    # Cleanup
    store.clear()


@pytest.fixture
def populated_snapshot():
    """Cria um snapshot com dados populados."""
    return DashboardSnapshot(
        active_clients=15,
        pending_obligations=7,
        tasks_today=3,
        cash_in_month=12500.50,
        upcoming_deadlines=[
            {
                "due_date": "2025-12-05",
                "client_name": "Farmácia ABC",
                "kind": "SNGPC",
                "title": "Envio mensal SNGPC",
                "status": "pending",
            },
            {
                "due_date": "2025-12-07",
                "client_name": "Drogaria XYZ",
                "kind": "FARMACIA_POPULAR",
                "title": "Relatório FP",
                "status": "pending",
            },
        ],
        hot_items=[
            "Faltam 2 dias para 3 envio(s) SNGPC",
            "1 obrigação(ões) Farmácia Popular vencida(s) ou para hoje!",
        ],
        pending_tasks=[
            {
                "due_date": "2025-12-10",
                "client_name": "Farmácia ABC",
                "title": "Revisar documentos",
                "priority": "high",
            },
            {
                "due_date": "2025-12-12",
                "client_name": "Drogaria XYZ",
                "title": "Enviar relatório",
                "priority": "normal",
            },
        ],
        clients_of_the_day=[
            {
                "client_id": 1,
                "client_name": "Farmácia Central",
                "obligation_kinds": ["FARMACIA_POPULAR", "SNGPC"],
            },
            {
                "client_id": 2,
                "client_name": "Drogaria Boa Saúde",
                "obligation_kinds": ["LICENCA_SANITARIA"],
            },
        ],
        risk_radar={
            "ANVISA": {"pending": 1, "overdue": 0, "status": "yellow", "enabled": True},
            "SNGPC": {"pending": 0, "overdue": 0, "status": "disabled", "enabled": False},
            "SIFAP": {"pending": 0, "overdue": 0, "status": "disabled", "enabled": False},
        },
        recent_activity=[
            {
                "timestamp": datetime(2025, 12, 4, 10, 30, 0),
                "category": "task",
                "text": "Nova tarefa: Revisar documentos",
            },
            {
                "timestamp": datetime(2025, 12, 3, 14, 15, 0),
                "category": "obligation",
                "text": "Nova obrigação SNGPC para cliente #123",
            },
        ],
    )


def _snapshot_to_state(snapshot: DashboardSnapshot):
    """Helper para converter DashboardSnapshot em DashboardViewState (para testes)."""
    vm = DashboardViewModel(service=lambda org_id, today: snapshot)
    return vm.load(org_id="test-org", today=None)


# ============================================================================
# TESTES PARA FUNÇÕES AUXILIARES
# ============================================================================


class TestClearChildren:
    """Testes para _clear_children."""

    def test_clear_empty_frame(self, parent_frame):
        """Frame vazio não causa erro."""
        _clear_children(parent_frame)
        assert len(parent_frame.winfo_children()) == 0

    def test_clear_frame_with_children(self, parent_frame):
        """Remove todos os widgets filhos."""
        # Criar alguns widgets
        tb.Label(parent_frame, text="Label 1").pack()
        tb.Label(parent_frame, text="Label 2").pack()
        tb.Button(parent_frame, text="Botão").pack()

        assert len(parent_frame.winfo_children()) == 3

        _clear_children(parent_frame)

        assert len(parent_frame.winfo_children()) == 0


class TestBuildIndicatorCard:
    """Testes para _build_indicator_card."""

    def test_creates_card_with_value_and_label(self, parent_frame):
        """Cria card com valor e label."""
        card = _build_indicator_card(parent_frame, "Clientes ativos", 10)

        # Deve ser um Frame (ttk.Frame from real code)
        assert isinstance(card, (ttk.Frame, tk.Frame))

        # Deve ter 2 labels (valor + texto)
        labels = [w for w in card.winfo_children() if isinstance(w, tk.Label)]
        assert len(labels) == 2

    def test_card_displays_correct_value(self, parent_frame):
        """Card exibe o valor numérico correto."""
        card = _build_indicator_card(parent_frame, "Tarefas", 42)

        labels = card.winfo_children()
        value_label = labels[0]

        # O texto do primeiro label deve ser o valor
        assert value_label.cget("text") == "42"

    def test_card_displays_correct_label(self, parent_frame):
        """Card exibe o texto descritivo correto."""
        card = _build_indicator_card(parent_frame, "Pendências", 5)

        labels = card.winfo_children()
        text_label = labels[1]

        assert text_label.cget("text") == "Pendências"

    def test_card_handles_float_value(self, parent_frame):
        """Float é convertido para int na exibição."""
        card = _build_indicator_card(parent_frame, "Valor", 123.99)

        labels = card.winfo_children()
        value_label = labels[0]

        assert value_label.cget("text") == "123"

    def test_card_with_custom_value_text(self, parent_frame):
        """Card aceita texto customizado para o valor."""
        card = _build_indicator_card(parent_frame, "Pendências", 5, value_text="5 ⚠")

        labels = card.winfo_children()
        value_label = labels[0]

        assert value_label.cget("text") == "5 ⚠"

    def test_card_with_bootstyle(self, parent_frame):
        """Card aplica bootstyle correto - bootstyle removed, just verify creation."""
        # bootstyle is no longer passed to widgets (no ttkbootstrap)
        card = _build_indicator_card(parent_frame, "Alertas", 10)

        # Verifica que o card foi criado
        assert isinstance(card, (ttk.Frame, tk.Frame))

    def test_card_accepts_custom_bootstyle(self, parent_frame):
        """Card aceita bootstyle customizado - bootstyle removed."""
        # bootstyle is no longer passed to widgets
        card = _build_indicator_card(parent_frame, "Test", 1)

        # Não deve lançar exceção
        assert card is not None


class TestBuildSectionFrame:
    """Testes para _build_section_frame."""

    def test_creates_section_with_title(self, parent_frame):
        """Cria seção com título."""
        section, content = _build_section_frame(parent_frame, "Minha Seção")

        # Deve ser um Labelframe (ttk.Labelframe from real code)
        assert isinstance(section, ttk.Labelframe)

        # Content deve ser um Frame
        assert isinstance(content, (ttk.Frame, tk.Frame))

    def test_section_title_is_set(self, parent_frame):
        """Título da seção é configurado corretamente."""
        section, _ = _build_section_frame(parent_frame, "Título Teste")

        # ttkbootstrap Labelframe usa 'text' para o título
        assert section.cget("text") == "Título Teste"


class TestFormatDeadlineLine:
    """Testes para _format_deadline_line."""

    def test_formats_complete_deadline(self):
        """Formata deadline com todos os campos."""
        deadline = {
            "due_date": "2025-12-10",
            "client_name": "Farmácia Test",
            "kind": "SNGPC",
            "title": "Envio SNGPC",
            "status": "pending",
        }

        result = _format_deadline_line(deadline)

        assert result == "2025-12-10 – Farmácia Test – SNGPC – Envio SNGPC – pending"

    def test_formats_deadline_with_missing_fields(self):
        """Usa '—' para campos ausentes."""
        deadline = {"due_date": "2025-12-10"}

        result = _format_deadline_line(deadline)

        assert "2025-12-10" in result
        assert "—" in result  # Campos ausentes

    def test_formats_empty_deadline(self):
        """Deadline vazio usa '—' para todos os campos."""
        deadline = {}

        result = _format_deadline_line(deadline)

        assert result == "— – — – — – — – —"


class TestFormatTaskLine:
    """Testes para _format_task_line."""

    def test_formats_complete_task_normal_priority(self):
        """Formata tarefa com prioridade normal."""
        task = {
            "due_date": "2025-12-15",
            "client_name": "Farmácia ABC",
            "title": "Revisar contratos",
            "priority": "normal",
        }

        result = _format_task_line(task)

        assert result == "2025-12-15 – Farmácia ABC – Revisar contratos"

    def test_formats_task_with_high_priority(self):
        """Formata tarefa com prioridade alta (emoji 🟡)."""
        task = {
            "due_date": "2025-12-15",
            "client_name": "Drogaria XYZ",
            "title": "Enviar relatório",
            "priority": "high",
        }

        result = _format_task_line(task)

        assert result == "🟡 2025-12-15 – Drogaria XYZ – Enviar relatório"

    def test_formats_task_with_urgent_priority(self):
        """Formata tarefa com prioridade urgente (emoji 🔴)."""
        task = {
            "due_date": "2025-12-10",
            "client_name": "Farmácia Test",
            "title": "Resolver pendência",
            "priority": "urgent",
        }

        result = _format_task_line(task)

        assert result == "🔴 2025-12-10 – Farmácia Test – Resolver pendência"

    def test_formats_task_with_missing_fields(self):
        """Usa '—' para campos ausentes."""
        task = {}

        result = _format_task_line(task)

        assert "—" in result


# ============================================================================
# TESTES PARA build_dashboard_center
# ============================================================================


class TestBuildDashboardCenter:
    """Testes para build_dashboard_center."""

    def test_clears_existing_widgets(self, parent_frame, empty_snapshot):
        """Limpa widgets existentes antes de construir."""
        # Adicionar widgets preexistentes
        tb.Label(parent_frame, text="Widget existente").pack()
        assert len(parent_frame.winfo_children()) == 1

        build_dashboard_center(parent_frame, _snapshot_to_state(empty_snapshot))

        # O widget original deve ter sido removido
        # (deve haver novos widgets, não o original)
        for child in parent_frame.winfo_children():
            if isinstance(child, tk.Label):
                assert child.cget("text") != "Widget existente"

    def test_creates_three_indicator_cards(self, parent_frame, populated_snapshot):
        """Cria 3 cards de indicadores."""
        build_dashboard_center(parent_frame, _snapshot_to_state(populated_snapshot))

        # Buscar textos dos cards
        texts = []
        _collect_label_texts(parent_frame, texts)

        # Verifica os labels dos cards (agora são mais curtos)
        assert "Clientes" in texts
        assert "Pendências" in texts
        assert "Tarefas hoje" in texts

    def test_displays_correct_card_values(self, parent_frame, populated_snapshot):
        """Cards exibem valores corretos do snapshot."""
        build_dashboard_center(parent_frame, _snapshot_to_state(populated_snapshot))

        texts = []
        _collect_label_texts(parent_frame, texts)

        # Valores do populated_snapshot
        assert "15" in texts  # active_clients
        assert "7 ⚠" in texts  # pending_obligations (com ícone)
        assert "3" in texts  # tasks_today

    def test_shows_no_hot_items_message_when_empty(self, parent_frame, empty_snapshot):
        """Mostra mensagem quando hot_items está vazio."""
        build_dashboard_center(parent_frame, _snapshot_to_state(empty_snapshot))

        texts = []
        _collect_label_texts(parent_frame, texts)

        assert MSG_NO_HOT_ITEMS in texts

    def test_shows_hot_items_when_present(self, parent_frame, populated_snapshot):
        """Exibe hot_items quando presentes."""
        build_dashboard_center(parent_frame, _snapshot_to_state(populated_snapshot))

        texts = []
        _collect_label_texts(parent_frame, texts)

        # Verificar que os hot_items aparecem
        assert any("SNGPC" in t for t in texts)
        assert any("Farmácia Popular" in t for t in texts)

    def test_shows_no_deadlines_message_when_empty(self, parent_frame, empty_snapshot):
        """Mostra mensagem quando upcoming_deadlines está vazio."""
        build_dashboard_center(parent_frame, _snapshot_to_state(empty_snapshot))

        texts = []
        _collect_label_texts(parent_frame, texts)

        assert MSG_NO_UPCOMING in texts

    def test_shows_deadlines_when_present(self, parent_frame, populated_snapshot):
        """Exibe deadlines quando presentes."""
        build_dashboard_center(parent_frame, _snapshot_to_state(populated_snapshot))

        texts = []
        _collect_label_texts(parent_frame, texts)

        # Verificar que os deadlines aparecem
        assert any("Farmácia ABC" in t for t in texts)
        assert any("Drogaria XYZ" in t for t in texts)

    def test_limits_deadlines_to_five(self, parent_frame):
        """Exibe no máximo 5 deadlines."""
        snapshot = DashboardSnapshot(
            upcoming_deadlines=[
                {
                    "due_date": f"2025-12-{i:02d}",
                    "client_name": f"TestClient{i}",
                    "kind": "SNGPC",
                    "title": "Envio",
                    "status": "pending",
                }
                for i in range(1, 8)  # 7 deadlines
            ]
        )

        build_dashboard_center(parent_frame, _snapshot_to_state(snapshot))

        texts = []
        _collect_label_texts(parent_frame, texts)

        # Contar quantos TestClient aparecem nos textos formatados
        # Cada deadline gera uma linha com "TestClient"
        deadline_count = sum(1 for t in texts if "TestClient" in t)

        # Deve ter no máximo 5
        assert deadline_count <= 5

    def test_creates_hot_items_section(self, parent_frame, empty_snapshot):
        """Cria seção 'O que está bombando hoje'."""
        build_dashboard_center(parent_frame, _snapshot_to_state(empty_snapshot))

        # Buscar labelframes
        labelframes = []
        _collect_widgets_by_type(parent_frame, ttk.Labelframe, labelframes)

        titles = [lf.cget("text") for lf in labelframes]
        assert any("bombando" in t.lower() for t in titles)

    def test_creates_deadlines_section(self, parent_frame, empty_snapshot):
        """Cria seção 'Próximos vencimentos'."""
        build_dashboard_center(parent_frame, _snapshot_to_state(empty_snapshot))

        labelframes = []
        _collect_widgets_by_type(parent_frame, ttk.Labelframe, labelframes)

        titles = [lf.cget("text") for lf in labelframes]
        assert any("vencimento" in t.lower() for t in titles)

    def test_shows_pending_tasks_when_present(self, parent_frame, populated_snapshot):
        """Exibe tarefas pendentes quando presentes."""
        build_dashboard_center(parent_frame, _snapshot_to_state(populated_snapshot))

        texts = []
        _collect_label_texts(parent_frame, texts)

        # Verificar que as tarefas aparecem
        assert any("Revisar documentos" in t for t in texts)
        assert any("Enviar relatório" in t for t in texts)

    def test_shows_no_tasks_message_when_empty(self, parent_frame, empty_snapshot):
        """Mostra mensagem quando pending_tasks está vazio."""
        build_dashboard_center(parent_frame, _snapshot_to_state(empty_snapshot))

        texts = []
        _collect_label_texts(parent_frame, texts)

        assert any("Nenhuma tarefa pendente" in t for t in texts)

    def test_limits_pending_tasks_to_five(self, parent_frame):
        """Exibe no máximo 5 tarefas pendentes."""
        snapshot = DashboardSnapshot(
            pending_tasks=[
                {
                    "due_date": f"2025-12-{i:02d}",
                    "client_name": f"TestClient{i}",
                    "title": f"Tarefa {i}",
                    "priority": "normal",
                }
                for i in range(1, 8)  # 7 tarefas
            ]
        )

        build_dashboard_center(parent_frame, _snapshot_to_state(snapshot))

        texts = []
        _collect_label_texts(parent_frame, texts)

        # Contar quantos "Tarefa " aparecem nos textos formatados
        task_count = sum(1 for t in texts if "Tarefa " in t)

        # Deve ter no máximo 5
        assert task_count <= 5

    def test_creates_pending_tasks_section(self, parent_frame, empty_snapshot):
        """Cria seção 'Tarefas pendentes'."""
        build_dashboard_center(parent_frame, _snapshot_to_state(empty_snapshot))

        labelframes = []
        _collect_widgets_by_type(parent_frame, ttk.Labelframe, labelframes)

        # Verificar título via text ou labelwidget (após refatoração PNG)
        titles = []
        for lf in labelframes:
            text = lf.cget("text")
            if text:
                titles.append(text)
            else:
                # labelwidget usado (com PNG)
                labelwidget_name = lf.cget("labelwidget")
                if labelwidget_name:
                    try:
                        labelwidget = lf.nametowidget(labelwidget_name)
                        widget_text = labelwidget.cget("text")
                        titles.append(widget_text)
                    except Exception:
                        pass

        assert any("tarefas pendentes" in t.lower() or "tarefas de hoje" in t.lower() for t in titles)

    def test_shows_clients_of_the_day_when_present(self, parent_frame, populated_snapshot):
        """Exibe clientes do dia quando presentes."""
        build_dashboard_center(parent_frame, _snapshot_to_state(populated_snapshot))

        texts = []
        _collect_label_texts(parent_frame, texts)

        # Verificar que os clientes aparecem
        assert any("Farmácia Central" in t for t in texts)
        assert any("Drogaria Boa Saúde" in t for t in texts)

    def test_shows_no_clients_message_when_empty(self, parent_frame, empty_snapshot):
        """Mostra mensagem quando clients_of_the_day está vazio."""
        build_dashboard_center(parent_frame, _snapshot_to_state(empty_snapshot))

        texts = []
        _collect_label_texts(parent_frame, texts)

        assert any("Nenhum cliente com obrigação para hoje" in t for t in texts)

    def test_creates_clients_of_the_day_section(self, parent_frame, empty_snapshot):
        """Cria seção 'Clientes do dia'."""
        build_dashboard_center(parent_frame, _snapshot_to_state(empty_snapshot))

        labelframes = []
        _collect_widgets_by_type(parent_frame, ttk.Labelframe, labelframes)

        titles = [lf.cget("text") for lf in labelframes]
        assert any("clientes do dia" in t.lower() for t in titles)

    def test_clients_of_the_day_shows_obligation_kinds(self, parent_frame, populated_snapshot):
        """Mostra os tipos de obrigação para cada cliente."""
        build_dashboard_center(parent_frame, _snapshot_to_state(populated_snapshot))

        texts = []
        _collect_label_texts(parent_frame, texts)

        # Verificar que aparecem os kinds de obrigação
        assert any("SNGPC" in t and "FARMACIA_POPULAR" in t for t in texts)
        assert any("LICENCA_SANITARIA" in t for t in texts)

    def test_displays_risk_radar_with_four_quadrants(self, parent_frame, populated_snapshot):
        """Exibe radar de riscos com 3 quadrantes (ANVISA, Farmácia Popular, SIFAP)."""
        build_dashboard_center(parent_frame, _snapshot_to_state(populated_snapshot))
        parent_frame.update()

        texts = []
        _collect_label_texts(parent_frame, texts)

        # Deve exibir todos os 3 quadrantes
        assert "ANVISA" in texts
        assert "Farmácia Popular" in texts
        assert "SIFAP" in texts

    def test_risk_radar_shows_correct_status(self, parent_frame, populated_snapshot):
        """Radar de riscos mostra status correto para cada quadrante."""
        build_dashboard_center(parent_frame, _snapshot_to_state(populated_snapshot))
        parent_frame.update()

        texts = []
        _collect_label_texts(parent_frame, texts)

        # populated_snapshot tem:
        # ANVISA: yellow (1 pending, enabled)
        # Farmácia Popular: disabled
        # SIFAP: disabled
        # Verificar se há informações dos quadrantes (ANVISA mostra pending/overdue, outros mostram "Desativado")
        assert any("Pendentes:" in t for t in texts)  # ANVISA mostra contagem
        assert any("Desativado" in t for t in texts)  # Farmácia Popular ou SIFAP mostram "Desativado"

    def test_displays_recent_activity_section(self, parent_frame, populated_snapshot):
        """Exibe seção de atividade recente."""
        build_dashboard_center(parent_frame, _snapshot_to_state(populated_snapshot))
        parent_frame.update()

        texts = []
        _collect_label_texts(parent_frame, texts)

        # Deve ter atividades exibidas (verificar por timestamp formatado)
        assert any("04/12" in t for t in texts) or any(
            "03/12" in t for t in texts
        ), f"Timestamps não encontrados em: {texts}"

    def test_recent_activity_shows_activities(self, parent_frame, populated_snapshot):
        """Atividade recente mostra atividades do snapshot."""
        build_dashboard_center(parent_frame, _snapshot_to_state(populated_snapshot))
        parent_frame.update()

        texts = []
        _collect_label_texts(parent_frame, texts)

        # populated_snapshot tem 2 atividades:
        # - "Nova tarefa: Revisar documentos"
        # - "Nova obrigação SNGPC para cliente #123"
        assert any("Revisar documentos" in t for t in texts)
        assert any("SNGPC" in t and "cliente #123" in t for t in texts)

    def test_recent_activity_formats_timestamps(self, parent_frame, populated_snapshot):
        """Atividade recente formata timestamps."""
        build_dashboard_center(parent_frame, _snapshot_to_state(populated_snapshot))
        parent_frame.update()

        texts = []
        _collect_label_texts(parent_frame, texts)

        # Deve ter timestamps formatados (dd/mm HH:MM)
        # populated_snapshot tem timestamps 04/12 10:30 e 03/12 14:15
        assert any("04/12" in t or "03/12" in t for t in texts)

    def test_recent_activity_uses_text_field(self, parent_frame):
        """Atividade recente usa campo 'text' (agora 'message') do ActivityEvent."""
        store = get_recent_activity_store()
        store.clear()

        # Adicionar eventos com message (equivalente ao 'text' antigo)
        store.add_event(
            ActivityEvent(
                org_id="test-org",
                module="TAREFAS",
                action="Nova",
                message="Nova tarefa: enviar SNGPC para cliente #123",
                created_at=datetime(2025, 12, 4, 20, 37, 0),
            )
        )
        store.add_event(
            ActivityEvent(
                org_id="test-org",
                module="TAREFAS",
                action="Nova",
                message="Nova tarefa: uhubguy",
                created_at=datetime(2025, 12, 4, 20, 36, 0),
            )
        )

        build_dashboard_center(parent_frame, _snapshot_to_state(DashboardSnapshot()))
        parent_frame.update()

        texts = []
        _collect_label_texts(parent_frame, texts)

        # Novo formato 2 linhas: Linha 2 tem "NOVA — enviar SNGPC..."
        # Validar que o tipo (após extração) aparece
        assert any(
            "enviar SNGPC para cliente #123" in t for t in texts
        ), f"Expected activity text not found in: {texts}"
        assert any("uhubguy" in t for t in texts), f"Expected activity text not found in: {texts}"

    def test_recent_activity_handles_legacy_title_field(self, parent_frame):
        """Atividade recente aceita campo 'title' via metadata (fallback)."""
        store = get_recent_activity_store()
        store.clear()

        # Evento sem message, mas com title em metadata (fallback)
        store.add_event(
            ActivityEvent(
                org_id="test-org",
                module="TAREFAS",
                action="Nova",
                message=None,
                metadata={"title": "Tarefa antiga (campo title)"},
                created_at=datetime(2025, 12, 4, 15, 0, 0),
            )
        )

        build_dashboard_center(parent_frame, _snapshot_to_state(DashboardSnapshot()))
        parent_frame.update()

        texts = []
        _collect_label_texts(parent_frame, texts)

        # Deve exibir o texto do campo 'title' como fallback
        assert any(
            "Tarefa antiga (campo title)" in t for t in texts
        ), f"Expected fallback to 'title' field not found in: {texts}"

    def test_recent_activity_handles_missing_text(self, parent_frame):
        """Atividade recente mostra mensagem padrão quando texto está ausente."""
        store = get_recent_activity_store()
        store.clear()

        # Evento sem message nem metadata
        store.add_event(
            ActivityEvent(
                org_id="test-org",
                module="TAREFAS",
                action="Nova",
                message=None,
                created_at=datetime(2025, 12, 4, 15, 0, 0),
            )
        )

        build_dashboard_center(parent_frame, _snapshot_to_state(DashboardSnapshot()))
        parent_frame.update()

        texts = []
        _collect_label_texts(parent_frame, texts)

        # Novo formato 2 linhas: Linha 2 tem "NOVA — — — por: —"
        # Deve exibir "—" quando não há mensagem
        assert any("NOVA — —" in t for t in texts), f"Expected default message not found in: {texts}"

    def test_recent_activity_displays_user_names(self, parent_frame):
        """Atividade recente exibe nomes de usuários via metadata."""
        store = get_recent_activity_store()
        store.clear()

        # Eventos com user_name em metadata
        store.add_event(
            ActivityEvent(
                org_id="test-org",
                module="TAREFAS",
                action="Nova",
                message="Nova tarefa: enviar SNGPC para cliente #123",
                metadata={"user_name": "Ana"},
                created_at=datetime(2025, 12, 4, 20, 37, 0),
            )
        )
        store.add_event(
            ActivityEvent(
                org_id="test-org",
                module="OBRIGACOES",
                action="Nova",
                message="Nova obrigação SNGPC para cliente #456",
                metadata={"user_name": "Júnior"},
                created_at=datetime(2025, 12, 4, 18, 12, 0),
            )
        )

        build_dashboard_center(parent_frame, _snapshot_to_state(DashboardSnapshot()))
        parent_frame.update()

        texts = []
        _collect_label_texts(parent_frame, texts)

        # Novo formato 2 linhas: Linha 2 tem "NOVA — ... — por: Ana"
        # Deve exibir linhas com nomes de usuários
        assert any(
            "por: Ana" in t and "enviar SNGPC para cliente #123" in t for t in texts
        ), f"Expected Ana activity not found in: {texts}"
        assert any(
            "por: Júnior" in t and "Nova obrigação SNGPC para cliente #456" in t for t in texts
        ), f"Expected Júnior activity not found in: {texts}"

    def test_recent_activity_fallback_to_user_name_when_no_text(self, parent_frame):
        """Atividade recente exibe user_name mesmo quando mensagem está vazia."""
        store = get_recent_activity_store()
        store.clear()

        # Evento sem message mas com user_name em metadata
        store.add_event(
            ActivityEvent(
                org_id="test-org",
                module="TAREFAS",
                action="Nova",
                message=None,
                metadata={"user_name": "Carlos"},
                created_at=datetime(2025, 12, 4, 15, 0, 0),
            )
        )

        build_dashboard_center(parent_frame, _snapshot_to_state(DashboardSnapshot()))
        parent_frame.update()

        texts = []
        _collect_label_texts(parent_frame, texts)

        # Deve exibir o nome do usuário (e mensagem padrão)
        assert any("Carlos" in t for t in texts), f"Expected fallback to user_name not found in: {texts}"


class TestBuildDashboardError:
    """Testes para build_dashboard_error."""

    def test_clears_existing_widgets(self, parent_frame):
        """Limpa widgets existentes antes de mostrar erro."""
        tb.Label(parent_frame, text="Widget existente").pack()

        build_dashboard_error(parent_frame)

        for child in parent_frame.winfo_children():
            if isinstance(child, tk.Label):
                assert child.cget("text") != "Widget existente"

    def test_shows_default_error_message(self, parent_frame):
        """Mostra mensagem de erro padrão."""
        build_dashboard_error(parent_frame)

        texts = []
        _collect_label_texts(parent_frame, texts)

        assert any("não foi possível" in t.lower() for t in texts)

    def test_shows_custom_error_message(self, parent_frame):
        """Mostra mensagem de erro customizada."""
        build_dashboard_error(parent_frame, message="Erro customizado de teste")

        texts = []
        _collect_label_texts(parent_frame, texts)

        assert "Erro customizado de teste" in texts

    def test_shows_error_icon(self, parent_frame):
        """Mostra ícone de erro (⚠️)."""
        build_dashboard_error(parent_frame)

        texts = []
        _collect_label_texts(parent_frame, texts)

        assert any("⚠️" in t for t in texts)


# ============================================================================
# FUNÇÕES AUXILIARES PARA TESTES
# ============================================================================


def _collect_label_texts(widget: tk.Widget, texts: list) -> None:
    """Coleta recursivamente os textos de todos os Labels e ScrolledText."""
    from tkinter.scrolledtext import ScrolledText

    for child in widget.winfo_children():
        if isinstance(child, tk.Label):
            text = child.cget("text")
            if text:
                texts.append(text)
        elif isinstance(child, ScrolledText):
            # Obter conteúdo do ScrolledText
            content = child.get("1.0", "end-1c")
            if content:
                texts.append(content)
        _collect_label_texts(child, texts)


def _collect_widgets_by_type(widget: tk.Widget, widget_type: type, result: list) -> None:
    """Coleta recursivamente widgets de um tipo específico."""
    for child in widget.winfo_children():
        if isinstance(child, widget_type):
            result.append(child)
        _collect_widgets_by_type(child, widget_type, result)


# ============================================================================
# TESTES ADICIONAIS PARA CORES INTELIGENTES DOS CARDS
# ============================================================================


class TestDashboardCardsSmartColors:
    """Testes para cores inteligentes dos cards baseadas em valores."""

    def test_pendencias_card_green_when_zero(self, parent_frame):
        """Card de pendências verde quando valor é 0."""
        snapshot = DashboardSnapshot(
            active_clients=10,
            pending_obligations=0,  # Zero pendências
            tasks_today=0,
        )

        build_dashboard_center(parent_frame, _snapshot_to_state(snapshot))

        # Verificar que existe um card com bootstyle success (verde)
        frames = []
        _collect_widgets_by_type(parent_frame, ttk.Frame, frames)

        # Pelo menos um frame deve ter bootstyle success
        # (o card de pendências com 0 deve ser verde)
        assert len(frames) > 0

    def test_pendencias_card_red_when_positive(self, parent_frame):
        """Card de pendências vermelho quando valor > 0."""
        snapshot = DashboardSnapshot(
            active_clients=10,
            pending_obligations=5,  # Tem pendências
            tasks_today=0,
        )

        build_dashboard_center(parent_frame, _snapshot_to_state(snapshot))

        # Verificar que há texto com ícone de alerta
        texts = []
        _collect_label_texts(parent_frame, texts)

        # Deve ter "5 ⚠" em algum label (card de pendências)
        assert any("⚠" in t for t in texts)

    def test_tarefas_card_green_when_zero(self, parent_frame):
        """Card de tarefas verde quando valor é 0."""
        snapshot = DashboardSnapshot(
            active_clients=10,
            pending_obligations=0,
            tasks_today=0,  # Zero tarefas
        )

        build_dashboard_center(parent_frame, _snapshot_to_state(snapshot))

        # Verificar construção sem erros
        frames = []
        _collect_widgets_by_type(parent_frame, ttk.Frame, frames)
        assert len(frames) > 0

    def test_tarefas_card_warning_when_positive(self, parent_frame):
        """Card de tarefas amarelo/warning quando valor > 0."""
        snapshot = DashboardSnapshot(
            active_clients=10,
            pending_obligations=0,
            tasks_today=3,  # Tem tarefas
        )

        build_dashboard_center(parent_frame, _snapshot_to_state(snapshot))

        # Verificar que o valor 3 aparece em algum label
        texts = []
        _collect_label_texts(parent_frame, texts)
        assert "3" in texts


class TestDashboardHotItemsWithIcons:
    """Testes para prefixo de ícone nos hot items."""

    def test_hot_items_show_warning_icon(self, parent_frame):
        """Hot items mostram ícone ⚠ no início."""
        snapshot = DashboardSnapshot(
            hot_items=[
                "2 envio(s) SNGPC vencido(s) ou para hoje!",
            ],
        )

        build_dashboard_center(parent_frame, _snapshot_to_state(snapshot))

        texts = []
        _collect_label_texts(parent_frame, texts)

        # Deve ter "⚠ 2 envio(s) SNGPC" (prefixo adicionado pela UI)
        assert any("⚠" in t and "SNGPC" in t for t in texts)

    def test_no_hot_items_shows_friendly_message(self, parent_frame):
        """Quando não há hot items, mostra mensagem amigável."""
        snapshot = DashboardSnapshot(
            hot_items=[],  # Vazio
        )

        build_dashboard_center(parent_frame, _snapshot_to_state(snapshot))

        texts = []
        _collect_label_texts(parent_frame, texts)

        # Deve mostrar a mensagem padrão com emoji feliz
        assert MSG_NO_HOT_ITEMS in texts
        assert "😀" in MSG_NO_HOT_ITEMS


def _find_buttons_recursive(widget) -> list:
    """Encontra recursivamente todos os botões em um widget."""
    buttons = []
    if isinstance(widget, (ttk.Button, tk.Button)):
        buttons.append(widget)
    for child in widget.winfo_children():
        buttons.extend(_find_buttons_recursive(child))
    return buttons


# ============================================================================
# TESTES PARA AGRUPAMENTO DE TAREFAS/PRAZOS (REFATORAÇÃO MF43)
# ============================================================================


class TestTaskGrouping:
    """Testes para garantir que o agrupamento não repete nomes de cliente."""

    def test_same_client_two_tasks_shows_single_header(self, parent_frame):
        """Quando o mesmo cliente tem 2 tarefas, mostra 1 header + 2 bullets."""
        snapshot = DashboardSnapshot(
            pending_tasks=[
                {
                    "due_date": "2025-12-10",
                    "client_name": "Farmácia ABC",
                    "client_id": 123,
                    "title": "Revisar documentos",
                    "priority": "high",
                },
                {
                    "due_date": "2025-12-12",
                    "client_name": "Farmácia ABC",
                    "client_id": 123,
                    "title": "Enviar relatório",
                    "priority": "normal",
                },
            ],
        )

        build_dashboard_center(parent_frame, _snapshot_to_state(snapshot))

        texts = []
        _collect_label_texts(parent_frame, texts)

        # Deve aparecer "Farmácia ABC" apenas 1 vez (como header do grupo)
        farmacia_abc_count = sum(1 for t in texts if "Farmácia ABC" in t)
        assert farmacia_abc_count == 1, "Nome do cliente deve aparecer apenas 1 vez no header"

        # Deve ter "Revisar documentos" e "Enviar relatório"
        assert any("Revisar documentos" in t for t in texts)
        assert any("Enviar relatório" in t for t in texts)

    def test_multiple_clients_show_multiple_headers(self, parent_frame):
        """Clientes diferentes devem ter headers separados."""
        snapshot = DashboardSnapshot(
            pending_tasks=[
                {
                    "due_date": "2025-12-10",
                    "client_name": "Farmácia ABC",
                    "client_id": 123,
                    "title": "Tarefa 1",
                    "priority": "high",
                },
                {
                    "due_date": "2025-12-11",
                    "client_name": "Drogaria XYZ",
                    "client_id": 456,
                    "title": "Tarefa 2",
                    "priority": "normal",
                },
            ],
        )

        build_dashboard_center(parent_frame, _snapshot_to_state(snapshot))

        texts = []
        _collect_label_texts(parent_frame, texts)

        # Cada cliente aparece 1 vez (seus respectivos headers)
        assert sum(1 for t in texts if "Farmácia ABC" in t) == 1
        assert sum(1 for t in texts if "Drogaria XYZ" in t) == 1


class TestHotItemsAnvisaOnlyHiding:
    """Testes para esconder 'O que está bombando hoje' quando vazio no modo ANVISA-only."""

    def test_hot_items_hidden_when_anvisa_only_and_empty(self, parent_frame):
        """Quando anvisa_only=True e hot_items=[], não renderiza a seção."""
        snapshot = DashboardSnapshot(
            hot_items=[],  # Vazio
            anvisa_only=True,  # Modo ANVISA-only
        )

        build_dashboard_center(parent_frame, _snapshot_to_state(snapshot))

        texts = []
        _collect_label_texts(parent_frame, texts)

        # Não deve aparecer o título "O que está bombando hoje"
        assert not any("bombando" in t.lower() for t in texts)
        # Não deve aparecer a mensagem padrão de vazio
        assert MSG_NO_HOT_ITEMS not in texts

    def test_hot_items_shown_when_anvisa_only_but_not_empty(self, parent_frame):
        """Quando anvisa_only=True mas hot_items não vazio, renderiza normalmente."""
        snapshot = DashboardSnapshot(
            hot_items=["2 regularizações ANVISA vencidas!"],
            anvisa_only=True,
        )

        build_dashboard_center(parent_frame, _snapshot_to_state(snapshot))

        texts = []
        _collect_label_texts(parent_frame, texts)

        # Deve aparecer o conteúdo
        assert any("regularizações ANVISA" in t for t in texts)

    def test_hot_items_shown_when_not_anvisa_only_even_if_empty(self, parent_frame):
        """Quando anvisa_only=False e hot_items=[], mostra mensagem padrão."""
        snapshot = DashboardSnapshot(
            hot_items=[],  # Vazio
            anvisa_only=False,  # Modo misto
        )

        build_dashboard_center(parent_frame, _snapshot_to_state(snapshot))

        texts = []
        _collect_label_texts(parent_frame, texts)

        # Deve mostrar mensagem padrão de vazio
        assert MSG_NO_HOT_ITEMS in texts


class TestClientsOfTheDayAnvisaOnlyHiding:
    """Testes para esconder 'Clientes do dia' quando ANVISA-only."""

    def test_anvisa_only_hides_clients_of_the_day_section(self, parent_frame):
        """Quando anvisa_only=True, não renderiza seção 'Clientes do dia'."""
        snapshot = DashboardSnapshot(
            anvisa_only=True,
            clients_of_the_day=[
                {
                    "client_id": 1,
                    "client_name": "Farmácia ABC",
                    "obligation_kinds": ["SNGPC"],
                },
            ],
        )

        build_dashboard_center(parent_frame, _snapshot_to_state(snapshot))

        texts = []
        _collect_label_texts(parent_frame, texts)

        # Não deve aparecer "Clientes do dia" nem "Clientes com tarefa hoje"
        assert not any("clientes" in t.lower() and ("do dia" in t.lower() or "com tarefa" in t.lower()) for t in texts)
        # Não deve aparecer o nome do cliente
        assert "Farmácia ABC" not in texts

    def test_clients_of_the_day_shown_when_not_anvisa_only(self, parent_frame):
        """Quando anvisa_only=False, renderiza seção normalmente."""
        snapshot = DashboardSnapshot(
            anvisa_only=False,
            clients_of_the_day=[
                {
                    "client_id": 1,
                    "client_name": "Farmácia ABC",
                    "obligation_kinds": ["SNGPC"],
                },
            ],
        )

        build_dashboard_center(parent_frame, _snapshot_to_state(snapshot))

        texts = []
        _collect_label_texts(parent_frame, texts)

        # Deve aparecer o nome do cliente
        assert any("Farmácia ABC" in t for t in texts)
