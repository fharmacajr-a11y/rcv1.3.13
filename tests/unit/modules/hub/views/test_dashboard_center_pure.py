# -*- coding: utf-8 -*-
"""Testes para dashboard_center_pure.py - funções puras sem UI."""

from datetime import date, timedelta

from src.modules.hub.views.dashboard_center_pure import (
    _norm_key_client,
    _priority_rank,
    format_day_label,
    format_deadline_line,
    format_task_line,
    group_deadlines_for_display,
    group_tasks_for_display,
)


def test_format_deadline_line_complete():
    """Testa formatação com todos os campos."""
    deadline = {
        "due_date": "31/12/2025",
        "client_name": "ACME Corp",
        "kind": "AFE",
        "title": "Renovação",
        "status": "Pendente",
    }
    result = format_deadline_line(deadline)
    assert result == "31/12/2025 – ACME Corp – AFE – Renovação – Pendente"


def test_format_deadline_line_missing_fields():
    """Testa formatação com campos faltantes (usa '—')."""
    deadline = {"due_date": "01/01/2026"}
    result = format_deadline_line(deadline)
    assert result == "01/01/2026 – — – — – — – —"


def test_format_task_line_urgent():
    """Testa formatação de tarefa urgente (emoji 🔴)."""
    task = {
        "due_date": "28/12/2025",
        "client_name": "Cliente A",
        "title": "Tarefa crítica",
        "priority": "urgent",
    }
    result = format_task_line(task)
    assert result == "🔴 28/12/2025 – Cliente A – Tarefa crítica"


def test_format_task_line_high():
    """Testa formatação de tarefa alta (emoji 🟡)."""
    task = {
        "due_date": "29/12/2025",
        "client_name": "Cliente B",
        "title": "Tarefa importante",
        "priority": "high",
    }
    result = format_task_line(task)
    assert result == "🟡 29/12/2025 – Cliente B – Tarefa importante"


def test_format_task_line_normal():
    """Testa formatação de tarefa normal (sem emoji)."""
    task = {
        "due_date": "30/12/2025",
        "client_name": "Cliente C",
        "title": "Tarefa rotineira",
        "priority": "normal",
    }
    result = format_task_line(task)
    assert result == "30/12/2025 – Cliente C – Tarefa rotineira"


def test_format_day_label_hoje():
    """Testa label 'Hoje' quando day == today."""
    today = date(2025, 12, 28)
    result = format_day_label(today, today)
    assert result == "Hoje"


def test_format_day_label_ontem():
    """Testa label 'Ontem' quando day == today - 1."""
    today = date(2025, 12, 28)
    ontem = today - timedelta(days=1)
    result = format_day_label(ontem, today)
    assert result == "Ontem"


def test_format_day_label_other_day():
    """Testa formato 'dd/MM' para outras datas."""
    today = date(2025, 12, 28)
    other = date(2025, 12, 25)
    result = format_day_label(other, today)
    assert result == "25/12"


# --- Testes para funções de agrupamento (linhas 100-252) ---


def test_norm_key_client_with_id():
    """Testa normalização com client_id."""
    task = {"client_id": "123", "client_name": "ACME"}
    result = _norm_key_client(task)
    assert result == "id:123"


def test_norm_key_client_without_id():
    """Testa normalização sem client_id (usa client_name)."""
    task = {"client_name": "  ACME Corp  "}
    result = _norm_key_client(task)
    assert result == "name:acme corp"


def test_norm_key_client_missing_both():
    """Testa normalização sem client_id nem client_name."""
    task = {}
    result = _norm_key_client(task)
    assert result == "name:—"


def test_priority_rank_urgent():
    """Testa ranking de prioridade urgente."""
    assert _priority_rank("urgent") == 0


def test_priority_rank_high():
    """Testa ranking de prioridade alta."""
    assert _priority_rank("high") == 1


def test_priority_rank_normal():
    """Testa ranking de prioridade normal."""
    assert _priority_rank("normal") == 2


def test_priority_rank_low():
    """Testa ranking de prioridade baixa."""
    assert _priority_rank("low") == 3


def test_priority_rank_unknown():
    """Testa ranking de prioridade desconhecida (default normal)."""
    assert _priority_rank("unknown") == 2
    assert _priority_rank("URGENT") == 0  # case insensitive


def test_group_tasks_for_display_empty():
    """Testa agrupamento com lista vazia."""
    result = group_tasks_for_display([])
    assert result == []


def test_group_tasks_for_display_single_client():
    """Testa agrupamento com um único cliente."""
    tasks = [
        {"client_id": "1", "client_name": "ACME", "due_date": "31/12", "title": "Tarefa 1", "priority": "normal"},
    ]
    result = group_tasks_for_display(tasks)
    assert len(result) == 1
    assert "ACME" in result[0]
    assert "31/12" in result[0]


def test_group_tasks_for_display_multiple_clients():
    """Testa agrupamento com múltiplos clientes (max_clients=2)."""
    tasks = [
        {"client_id": "1", "client_name": "ACME", "due_date": "31/12", "title": "Tarefa A", "priority": "urgent"},
        {"client_id": "2", "client_name": "Beta", "due_date": "30/12", "title": "Tarefa B", "priority": "normal"},
        {"client_id": "3", "client_name": "Gamma", "due_date": "29/12", "title": "Tarefa C", "priority": "low"},
    ]
    result = group_tasks_for_display(tasks, max_clients=2)
    # Deve retornar apenas 2 clientes (ordenado por prioridade)
    assert len(result) == 2
    # ACME tem urgent (prioridade 0), deve vir primeiro
    assert "ACME" in result[0]


def test_group_tasks_for_display_remaining_count():
    """Testa indicação de '+X outras' quando há mais tarefas que o limite."""
    tasks = [
        {"client_id": "1", "client_name": "ACME", "due_date": "31/12", "title": "Tarefa 1", "priority": "normal"},
        {"client_id": "1", "client_name": "ACME", "due_date": "30/12", "title": "Tarefa 2", "priority": "normal"},
        {"client_id": "1", "client_name": "ACME", "due_date": "29/12", "title": "Tarefa 3", "priority": "normal"},
    ]
    result = group_tasks_for_display(tasks, max_items_per_client=2)
    assert len(result) == 1
    # Deve ter indicação de mais tarefas
    assert "+1 outra" in result[0]


def test_group_deadlines_for_display_empty():
    """Testa agrupamento de deadlines com lista vazia."""
    result = group_deadlines_for_display([])
    assert result == []


def test_group_deadlines_for_display_single_client():
    """Testa agrupamento de deadlines com um cliente."""
    deadlines = [
        {
            "client_id": "1",
            "client_name": "ACME",
            "due_date": "31/12",
            "kind": "AFE",
            "title": "Renovação",
            "status": "Pendente",
        },
    ]
    result = group_deadlines_for_display(deadlines)
    assert len(result) == 1
    assert "📅 ACME" in result[0]
    assert "31/12" in result[0]


def test_group_deadlines_for_display_hide_kind():
    """Testa agrupamento de deadlines com hide_kind=True (modo ANVISA-only)."""
    deadlines = [
        {
            "client_id": "1",
            "client_name": "ACME",
            "due_date": "31/12",
            "kind": "AFE",
            "title": "Renovação",
            "status": "Pendente",
        },
    ]
    result = group_deadlines_for_display(deadlines, hide_kind=True)
    assert len(result) == 1
    # Com hide_kind=True, não deve ter "AFE" no meio
    assert "AFE" not in result[0] or "– AFE –" not in result[0]


def test_group_deadlines_for_display_remaining_count():
    """Testa indicação de '+X outras' em deadlines."""
    deadlines = [
        {
            "client_id": "1",
            "client_name": "ACME",
            "due_date": "31/12",
            "kind": "AFE",
            "title": "Item 1",
            "status": "Pendente",
        },
        {
            "client_id": "1",
            "client_name": "ACME",
            "due_date": "30/12",
            "kind": "AUT",
            "title": "Item 2",
            "status": "Pendente",
        },
        {
            "client_id": "1",
            "client_name": "ACME",
            "due_date": "29/12",
            "kind": "LIC",
            "title": "Item 3",
            "status": "Pendente",
        },
    ]
    result = group_deadlines_for_display(deadlines, max_items_per_client=2)
    assert len(result) == 1
    assert "+1 outra" in result[0]
