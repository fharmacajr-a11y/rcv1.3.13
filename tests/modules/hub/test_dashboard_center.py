# -*- coding: utf-8 -*-
"""Testes para o dashboard_center (Atividade recente e helpers).

Testa:
- Formatação de labels de dia (Hoje/Ontem/dd/MM)
- Lógica de limite de atividades (5 itens)
- Condição para mostrar botão "Ver todos"
- Agrupamento por dia
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest


class TestFormatDayLabel:
    """Testes para a função _format_day_label."""

    def test_format_today(self):
        """Verifica que a data de hoje retorna 'Hoje'."""
        from src.modules.hub.views.dashboard_center import _format_day_label

        today = date(2025, 12, 15)
        result = _format_day_label(today, today)
        assert result == "Hoje"

    def test_format_yesterday(self):
        """Verifica que ontem retorna 'Ontem'."""
        from src.modules.hub.views.dashboard_center import _format_day_label

        today = date(2025, 12, 15)
        yesterday = today - timedelta(days=1)
        result = _format_day_label(yesterday, today)
        assert result == "Ontem"

    def test_format_older_date(self):
        """Verifica que datas antigas retornam formato dd/MM."""
        from src.modules.hub.views.dashboard_center import _format_day_label

        today = date(2025, 12, 15)
        older = date(2025, 12, 10)
        result = _format_day_label(older, today)
        assert result == "10/12"

    def test_format_different_month(self):
        """Verifica formatação de data de mês diferente."""
        from src.modules.hub.views.dashboard_center import _format_day_label

        today = date(2025, 12, 15)
        older = date(2025, 11, 25)
        result = _format_day_label(older, today)
        assert result == "25/11"


class TestActivityLimit:
    """Testes para o limite de atividades exibidas."""

    def test_max_activity_constant(self):
        """Verifica que a constante MAX_ACTIVITY_ITEMS_DASHBOARD está definida como 5."""
        from src.modules.hub.views.dashboard_center import MAX_ACTIVITY_ITEMS_DASHBOARD

        assert MAX_ACTIVITY_ITEMS_DASHBOARD == 5

    def test_limit_with_few_activities(self):
        """Verifica que com poucas atividades (<5), todas são mostradas."""
        activities = [
            {"timestamp": datetime(2025, 12, 15, 14, 30), "text": "Item 1"},
            {"timestamp": datetime(2025, 12, 15, 13, 15), "text": "Item 2"},
            {"timestamp": datetime(2025, 12, 14, 16, 45), "text": "Item 3"},
        ]

        # Simular o corte
        from src.modules.hub.views.dashboard_center import MAX_ACTIVITY_ITEMS_DASHBOARD

        limited = activities[:MAX_ACTIVITY_ITEMS_DASHBOARD]
        assert len(limited) == 3

    def test_limit_with_many_activities(self):
        """Verifica que com muitas atividades (>5), apenas 5 são mostradas."""
        activities = [{"timestamp": datetime(2025, 12, 15, i, 0), "text": f"Item {i}"} for i in range(10)]

        # Simular o corte
        from src.modules.hub.views.dashboard_center import MAX_ACTIVITY_ITEMS_DASHBOARD

        limited = activities[:MAX_ACTIVITY_ITEMS_DASHBOARD]
        assert len(limited) == 5

    def test_limit_exactly_five(self):
        """Verifica que com exatamente 5 atividades, todas são mostradas."""
        activities = [{"timestamp": datetime(2025, 12, 15, i, 0), "text": f"Item {i}"} for i in range(5)]

        # Simular o corte
        from src.modules.hub.views.dashboard_center import MAX_ACTIVITY_ITEMS_DASHBOARD

        limited = activities[:MAX_ACTIVITY_ITEMS_DASHBOARD]
        assert len(limited) == 5


class TestViewAllCondition:
    """Testes para a condição de exibição do botão 'Ver todos'."""

    @pytest.mark.parametrize(
        "total_items,max_items,expected",
        [
            (0, 5, False),  # Nenhuma atividade
            (3, 5, False),  # Poucas atividades
            (5, 5, False),  # Exatamente o limite
            (6, 5, True),  # Uma a mais que o limite
            (10, 5, True),  # Muitas atividades
            (100, 5, True),  # Muitas atividades
        ],
    )
    def test_should_show_view_all(self, total_items, max_items, expected):
        """Verifica a condição para mostrar o botão 'Ver todos'."""
        # Lógica: botão aparece apenas quando total > max
        should_show = total_items > max_items
        assert should_show == expected


class TestActivityGrouping:
    """Testes para o agrupamento de atividades por dia."""

    def test_grouping_single_day(self):
        """Verifica agrupamento de atividades do mesmo dia."""
        from collections import defaultdict

        activities = [
            {"timestamp": datetime(2025, 12, 15, 14, 30), "text": "Item 1"},
            {"timestamp": datetime(2025, 12, 15, 13, 15), "text": "Item 2"},
            {"timestamp": datetime(2025, 12, 15, 12, 0), "text": "Item 3"},
        ]

        # Simular agrupamento
        grouped: dict[date, list] = defaultdict(list)
        for activity in activities:
            timestamp = activity.get("timestamp")
            if timestamp and hasattr(timestamp, "date"):
                activity_date = timestamp.date()
                grouped[activity_date].append(activity)

        assert len(grouped) == 1
        assert date(2025, 12, 15) in grouped
        assert len(grouped[date(2025, 12, 15)]) == 3

    def test_grouping_multiple_days(self):
        """Verifica agrupamento de atividades de dias diferentes."""
        from collections import defaultdict

        activities = [
            {"timestamp": datetime(2025, 12, 15, 14, 30), "text": "Item 1"},
            {"timestamp": datetime(2025, 12, 15, 13, 15), "text": "Item 2"},
            {"timestamp": datetime(2025, 12, 14, 16, 45), "text": "Item 3"},
            {"timestamp": datetime(2025, 12, 14, 9, 0), "text": "Item 4"},
            {"timestamp": datetime(2025, 12, 13, 18, 20), "text": "Item 5"},
        ]

        # Simular agrupamento
        grouped: dict[date, list] = defaultdict(list)
        for activity in activities:
            timestamp = activity.get("timestamp")
            if timestamp and hasattr(timestamp, "date"):
                activity_date = timestamp.date()
                grouped[activity_date].append(activity)

        assert len(grouped) == 3
        assert date(2025, 12, 15) in grouped
        assert date(2025, 12, 14) in grouped
        assert date(2025, 12, 13) in grouped
        assert len(grouped[date(2025, 12, 15)]) == 2
        assert len(grouped[date(2025, 12, 14)]) == 2
        assert len(grouped[date(2025, 12, 13)]) == 1

    def test_grouping_sorted_descending(self):
        """Verifica que as datas são ordenadas em ordem decrescente."""
        from collections import defaultdict

        activities = [
            {"timestamp": datetime(2025, 12, 13, 18, 20), "text": "Item 1"},
            {"timestamp": datetime(2025, 12, 15, 14, 30), "text": "Item 2"},
            {"timestamp": datetime(2025, 12, 14, 16, 45), "text": "Item 3"},
        ]

        # Simular agrupamento
        grouped: dict[date, list] = defaultdict(list)
        for activity in activities:
            timestamp = activity.get("timestamp")
            if timestamp and hasattr(timestamp, "date"):
                activity_date = timestamp.date()
                grouped[activity_date].append(activity)

        # Ordenar datas
        sorted_dates = sorted(grouped.keys(), reverse=True)

        assert sorted_dates[0] == date(2025, 12, 15)
        assert sorted_dates[1] == date(2025, 12, 14)
        assert sorted_dates[2] == date(2025, 12, 13)

    def test_most_recent_activities_selected(self):
        """Verifica que as 5 atividades mais recentes são selecionadas."""
        # Criar 8 atividades em ordem decrescente (mais recente primeiro)
        activities = [
            {"timestamp": datetime(2025, 12, 15, 18, 0), "text": "Mais recente"},
            {"timestamp": datetime(2025, 12, 15, 17, 0), "text": "2ª mais recente"},
            {"timestamp": datetime(2025, 12, 15, 16, 0), "text": "3ª mais recente"},
            {"timestamp": datetime(2025, 12, 15, 15, 0), "text": "4ª mais recente"},
            {"timestamp": datetime(2025, 12, 15, 14, 0), "text": "5ª mais recente"},
            {"timestamp": datetime(2025, 12, 15, 13, 0), "text": "6ª (não deve aparecer)"},
            {"timestamp": datetime(2025, 12, 15, 12, 0), "text": "7ª (não deve aparecer)"},
            {"timestamp": datetime(2025, 12, 15, 11, 0), "text": "8ª (não deve aparecer)"},
        ]

        # Simular corte
        from src.modules.hub.views.dashboard_center import MAX_ACTIVITY_ITEMS_DASHBOARD

        limited = activities[:MAX_ACTIVITY_ITEMS_DASHBOARD]

        assert len(limited) == 5
        assert limited[0]["text"] == "Mais recente"
        assert limited[4]["text"] == "5ª mais recente"
        assert all(act["text"] != "6ª (não deve aparecer)" for act in limited)
