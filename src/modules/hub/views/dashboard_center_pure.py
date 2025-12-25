# -*- coding: utf-8 -*-
"""Funções puras (sem UI) para o dashboard center.

ORG-005: Extraído de dashboard_center.py para reduzir complexidade.
Contém funções de formatação e transformação de dados sem dependências de tkinter.
"""

from __future__ import annotations

from datetime import date, timedelta


def format_deadline_line(deadline: dict) -> str:
    """Formata uma linha de vencimento.

    Args:
        deadline: Dict com due_date, client_name, kind, title, status.

    Returns:
        String formatada com os dados do vencimento.
    """
    due_date = deadline.get("due_date", "—")
    client_name = deadline.get("client_name", "—")
    kind = deadline.get("kind", "—")
    title = deadline.get("title", "—")
    status = deadline.get("status", "—")

    return f"{due_date} – {client_name} – {kind} – {title} – {status}"


def format_task_line(task: dict) -> str:
    """Formata uma linha de tarefa pendente.

    Args:
        task: Dict com due_date, client_name, title, priority.

    Returns:
        String formatada com os dados da tarefa.
    """
    due_date = task.get("due_date", "—")
    client_name = task.get("client_name", "—")
    title = task.get("title", "—")
    priority = task.get("priority", "normal")

    # Adiciona emoji de prioridade
    priority_emoji = ""
    if priority == "urgent":
        priority_emoji = "🔴 "
    elif priority == "high":
        priority_emoji = "🟡 "

    return f"{priority_emoji}{due_date} – {client_name} – {title}"


def format_day_label(day: date, today: date) -> str:
    """Formata o label do dia para exibição.

    Args:
        day: Data a ser formatada.
        today: Data de hoje para comparação.

    Returns:
        String formatada: "Hoje", "Ontem" ou "dd/MM".
    """
    if day == today:
        return "Hoje"
    elif day == today - timedelta(days=1):
        return "Ontem"
    else:
        return day.strftime("%d/%m")
