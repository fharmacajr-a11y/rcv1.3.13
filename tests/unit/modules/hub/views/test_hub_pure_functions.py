# -*- coding: utf-8 -*-
"""Testes unitários para funções puras extraídas nas ORG-004, ORG-005 e ORG-006.

Este arquivo testa as funções extraídas dos módulos *_pure.py do hub/views,
garantindo que elas são realmente testáveis isoladamente sem dependências de UI.
"""

from __future__ import annotations

from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest


# ═══════════════════════════════════════════════════════════════════════
# ORG-004: hub_screen_pure.py
# ═══════════════════════════════════════════════════════════════════════


def test_get_local_timezone_returns_tzinfo_or_fallback():
    """Testa que get_local_timezone retorna um tzinfo válido sem exceções.

    ORG-004: Função extraída de hub_screen.py.
    Deve retornar um tzinfo (tzlocal, system timezone ou UTC fallback).
    """
    from src.modules.hub.views.hub_screen_pure import get_local_timezone

    # Executar função
    tz = get_local_timezone()

    # Validações
    assert tz is not None, "get_local_timezone não deve retornar None"

    # Verificar que é um tzinfo válido (pode ser usado para criar datetime)
    now = datetime.now(tz=tz)
    assert now.tzinfo is not None, "Timezone retornado deve ser utilizável"

    # Verificar que tem nome (tzlocal, UTC, etc.)
    tz_name = str(tz)
    assert tz_name, "Timezone deve ter representação string"


# ═══════════════════════════════════════════════════════════════════════
# ORG-005: dashboard_center_pure.py
# ═══════════════════════════════════════════════════════════════════════


def test_format_deadline_line_smoke():
    """Testa formatação básica de linha de vencimento.

    ORG-005: Função extraída de dashboard_center.py.
    Formato esperado: "due_date – Cliente – Tipo – Título – Status"
    Nota: A função não formata a data, apenas concatena os campos.
    """
    from src.modules.hub.views.dashboard_center_pure import format_deadline_line

    # Caso típico
    deadline = {
        "due_date": "2025-12-31",
        "client_name": "Farmácia Teste",
        "kind": "RDC",
        "title": "Relatório Mensal",
        "status": "Pendente",
    }

    result = format_deadline_line(deadline)

    # Validações
    assert isinstance(result, str), "Deve retornar string"
    assert "2025-12-31" in result, "Deve conter data (formato ISO conforme input)"
    assert "Farmácia Teste" in result, "Deve conter nome do cliente"
    assert "RDC" in result, "Deve conter tipo"
    assert "Relatório Mensal" in result, "Deve conter título"
    assert "Pendente" in result, "Deve conter status"
    assert "–" in result, "Deve conter separador"


def test_format_deadline_line_missing_fields():
    """Testa formatação com campos faltando (edge case).

    Deve lidar com dicts incompletos sem explodir.
    """
    from src.modules.hub.views.dashboard_center_pure import format_deadline_line

    # Dict vazio
    result = format_deadline_line({})
    assert isinstance(result, str), "Deve retornar string mesmo com dict vazio"

    # Dict com apenas alguns campos
    partial = {"client_name": "Cliente X", "title": "Tarefa"}
    result = format_deadline_line(partial)
    assert isinstance(result, str), "Deve retornar string com dict parcial"
    assert "Cliente X" in result, "Deve conter campos presentes"
    assert "Tarefa" in result, "Deve conter título"


def test_format_task_line_smoke():
    """Testa formatação básica de linha de tarefa.

    ORG-005: Função extraída de dashboard_center.py.
    Formato esperado: "[emoji] due_date – Cliente – Título"
    Nota: A função não formata a data, apenas concatena os campos.
    """
    from src.modules.hub.views.dashboard_center_pure import format_task_line

    # Caso com prioridade urgent (emoji 🔴)
    task_urgent = {
        "due_date": "2025-12-25",
        "client_name": "Farmácia Urgente",
        "title": "Compra de Medicamentos",
        "priority": "urgent",
    }

    result = format_task_line(task_urgent)

    # Validações
    assert isinstance(result, str), "Deve retornar string"
    assert "🔴" in result, "Deve conter emoji de prioridade urgent"
    assert "2025-12-25" in result, "Deve conter data (formato ISO conforme input)"
    assert "Farmácia Urgente" in result, "Deve conter nome do cliente"
    assert "Compra de Medicamentos" in result, "Deve conter título"

    # Caso com prioridade high (emoji 🟡)
    task_high = {
        "due_date": "2025-12-26",
        "client_name": "Cliente ABC",
        "title": "Relatório",
        "priority": "high",
    }

    result = format_task_line(task_high)
    assert "🟡" in result, "Deve conter emoji de prioridade high"

    # Caso sem prioridade especial (sem emoji)
    task_normal = {
        "due_date": "2025-12-27",
        "client_name": "Cliente XYZ",
        "title": "Revisão",
        "priority": "normal",
    }

    result = format_task_line(task_normal)
    assert "🔴" not in result and "🟡" not in result, "Não deve conter emoji para prioridade normal"


def test_format_day_label_smoke():
    """Testa formatação de label de dia.

    ORG-005: Função extraída de dashboard_center.py.
    Formato esperado: "Hoje", "Ontem" ou "DD/MM"
    """
    from src.modules.hub.views.dashboard_center_pure import format_day_label

    today = date(2025, 12, 25)

    # Caso: hoje
    result = format_day_label(today, today)
    assert result == "Hoje", "Deve retornar 'Hoje' para data atual"

    # Caso: ontem
    yesterday = date(2025, 12, 24)
    result = format_day_label(yesterday, today)
    assert result == "Ontem", "Deve retornar 'Ontem' para dia anterior"

    # Caso: outro dia
    other_day = date(2025, 12, 20)
    result = format_day_label(other_day, today)
    assert result == "20/12", "Deve retornar 'DD/MM' para outros dias"
    assert "/" in result, "Formato deve conter barra"


# ═══════════════════════════════════════════════════════════════════════
# ORG-006: hub_screen_view_pure.py
# ═══════════════════════════════════════════════════════════════════════


def test_extract_time_from_timestamp_iso_format():
    """Testa extração de hora de timestamp ISO 8601.

    ORG-006: Função extraída de hub_screen_view.py.
    """
    from src.modules.hub.views.hub_screen_view_pure import extract_time_from_timestamp

    # Caso: timestamp ISO 8601 completo com Z
    result = extract_time_from_timestamp("2025-12-25T14:30:00Z")
    assert result == "14:30", "Deve extrair HH:MM de timestamp ISO com Z"

    # Caso: timestamp ISO 8601 com timezone
    result = extract_time_from_timestamp("2025-12-25T09:15:30+00:00")
    assert result == "09:15", "Deve extrair HH:MM de timestamp ISO com timezone"


def test_extract_time_from_timestamp_direct_time():
    """Testa extração de hora quando já é string de hora."""
    from src.modules.hub.views.hub_screen_view_pure import extract_time_from_timestamp

    # Caso: já é hora (HH:MM)
    result = extract_time_from_timestamp("14:30")
    assert result == "14:30", "Deve retornar hora direta"

    # Caso: hora com segundos
    result = extract_time_from_timestamp("14:30:45")
    assert result == "14:30", "Deve retornar primeiros 5 caracteres"


def test_extract_time_from_timestamp_invalid():
    """Testa extração de hora com inputs inválidos."""
    from src.modules.hub.views.hub_screen_view_pure import extract_time_from_timestamp

    # Caso: string vazia
    result = extract_time_from_timestamp("")
    assert result == "", "Deve retornar string vazia para input vazio"

    # Caso: string inválida
    result = extract_time_from_timestamp("invalid-timestamp")
    assert isinstance(result, str), "Deve retornar string mesmo para input inválido"
    # Pode retornar "" ou primeiros 5 chars, dependendo da lógica

    # Caso: string muito curta
    result = extract_time_from_timestamp("12")
    assert isinstance(result, str), "Deve retornar string sem explodir"


def test_format_note_line_complete():
    """Testa formatação de linha de nota com todos os campos.

    ORG-006: Função extraída de hub_screen_view.py.
    Formato esperado: "[HH:MM] email: texto\n"
    """
    from src.modules.hub.views.hub_screen_view_pure import format_note_line

    note = {
        "created_at": "2025-12-25T14:30:00Z",
        "author_email": "user@example.com",
        "body": "Lembrar de revisar documento",
    }

    result = format_note_line(note)

    # Validações
    assert isinstance(result, str), "Deve retornar string"
    assert "[14:30]" in result, "Deve conter hora entre colchetes"
    assert "user@example.com" in result, "Deve conter email do autor"
    assert "Lembrar de revisar documento" in result, "Deve conter corpo da nota"
    assert result.endswith("\n"), "Deve terminar com newline"
    assert ":" in result, "Deve conter separador ':'"


def test_format_note_line_missing_fields():
    """Testa formatação de nota com campos faltando."""
    from src.modules.hub.views.hub_screen_view_pure import format_note_line

    # Dict vazio
    result = format_note_line({})
    assert isinstance(result, str), "Deve retornar string mesmo com dict vazio"
    assert result.endswith("\n"), "Deve terminar com newline"

    # Apenas body
    note_partial = {"body": "Texto de teste"}
    result = format_note_line(note_partial)
    assert "Texto de teste" in result, "Deve conter body mesmo sem outros campos"


def test_make_module_button_with_mock():
    """Testa criação de botão de módulo (mockando ttkbootstrap).

    ORG-006: Função extraída de hub_screen_view.py.
    O import de ttkbootstrap é feito dentro da função, então patchamos o módulo ttkbootstrap.
    """
    from src.modules.hub.views.hub_screen_view_pure import make_module_button

    # Patch do ttkbootstrap.Button (onde é importado dentro da função)
    with patch("ttkbootstrap.Button") as mock_button_class:
        mock_button_instance = MagicMock()
        mock_button_class.return_value = mock_button_instance

        # Mock do parent
        mock_parent = MagicMock()

        # Mock do command
        mock_command = MagicMock()

        # Chamar função
        result = make_module_button(
            parent=mock_parent,
            text="Clientes",
            command=mock_command,
            bootstyle="primary",
        )

        # Validações
        assert result == mock_button_instance, "Deve retornar instância do botão"

        # Verificar que Button foi chamado com args corretos
        mock_button_class.assert_called_once_with(
            mock_parent,
            text="Clientes",
            command=mock_command,
            bootstyle="primary",
        )


# ═══════════════════════════════════════════════════════════════════════
# Execução dos testes
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
