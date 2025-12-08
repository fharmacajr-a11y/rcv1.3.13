# -*- coding: utf-8 -*-
"""Testes para o dashboard_service (Radar de riscos regulatórios).

Testa:
- Estrutura do radar com 3 quadrantes (ANVISA, SNGPC, SIFAP)
- Ausência de Farmácia Popular
- Mapeamento correto de kinds para quadrantes
- Cálculo de status (green/yellow/red)
- Contagem de pendentes e atrasados
"""

from __future__ import annotations

from datetime import date


class TestRiskRadarStructure:
    """Testes para a estrutura do radar de riscos."""

    def test_radar_has_three_quadrants(self):
        """Verifica que o radar possui exatamente 3 quadrantes."""
        from src.modules.hub.dashboard_service import _build_risk_radar

        obligations = []
        today = date(2025, 12, 15)

        radar = _build_risk_radar(obligations, today)

        assert len(radar) == 3

    def test_radar_quadrant_keys(self):
        """Verifica que os quadrantes são ANVISA, SNGPC e SIFAP."""
        from src.modules.hub.dashboard_service import _build_risk_radar

        obligations = []
        today = date(2025, 12, 15)

        radar = _build_risk_radar(obligations, today)

        assert set(radar.keys()) == {"ANVISA", "SNGPC", "SIFAP"}

    def test_no_farmacia_popular_quadrant(self):
        """Verifica que NÃO existe quadrante de Farmácia Popular."""
        from src.modules.hub.dashboard_service import _build_risk_radar

        obligations = []
        today = date(2025, 12, 15)

        radar = _build_risk_radar(obligations, today)

        assert "FARMACIA_POPULAR" not in radar

    def test_quadrant_structure(self):
        """Verifica que cada quadrante tem pending, overdue e status."""
        from src.modules.hub.dashboard_service import _build_risk_radar

        obligations = []
        today = date(2025, 12, 15)

        radar = _build_risk_radar(obligations, today)

        for quadrant_key in ["ANVISA", "SNGPC", "SIFAP"]:
            assert quadrant_key in radar
            quadrant = radar[quadrant_key]
            assert "pending" in quadrant
            assert "overdue" in quadrant
            assert "status" in quadrant


class TestRiskRadarMapping:
    """Testes para o mapeamento de kinds para quadrantes."""

    def test_sngpc_maps_to_sngpc_quadrant(self):
        """Verifica que obrigações SNGPC são mapeadas para o quadrante SNGPC."""
        from src.modules.hub.dashboard_service import _build_risk_radar

        obligations = [
            {"kind": "SNGPC", "status": "pending", "due_date": "2025-12-20"},
        ]
        today = date(2025, 12, 15)

        radar = _build_risk_radar(obligations, today)

        assert radar["SNGPC"]["pending"] == 1
        assert radar["ANVISA"]["pending"] == 0
        assert radar["SIFAP"]["pending"] == 0

    def test_sifap_maps_to_sifap_quadrant(self):
        """Verifica que obrigações SIFAP são mapeadas para o quadrante SIFAP."""
        from src.modules.hub.dashboard_service import _build_risk_radar

        obligations = [
            {"kind": "SIFAP", "status": "pending", "due_date": "2025-12-20"},
        ]
        today = date(2025, 12, 15)

        radar = _build_risk_radar(obligations, today)

        assert radar["SIFAP"]["pending"] == 1
        assert radar["ANVISA"]["pending"] == 0
        assert radar["SNGPC"]["pending"] == 0

    def test_licenca_sanitaria_maps_to_anvisa_quadrant(self):
        """Verifica que obrigações LICENCA_SANITARIA são mapeadas para ANVISA."""
        from src.modules.hub.dashboard_service import _build_risk_radar

        obligations = [
            {"kind": "LICENCA_SANITARIA", "status": "pending", "due_date": "2025-12-20"},
        ]
        today = date(2025, 12, 15)

        radar = _build_risk_radar(obligations, today)

        assert radar["ANVISA"]["pending"] == 1
        assert radar["SNGPC"]["pending"] == 0
        assert radar["SIFAP"]["pending"] == 0

    def test_farmacia_popular_not_in_radar(self):
        """Verifica que obrigações FARMACIA_POPULAR NÃO aparecem no radar."""
        from src.modules.hub.dashboard_service import _build_risk_radar

        obligations = [
            {"kind": "FARMACIA_POPULAR", "status": "pending", "due_date": "2025-12-20"},
        ]
        today = date(2025, 12, 15)

        radar = _build_risk_radar(obligations, today)

        # Nenhum quadrante deve ter contadores incrementados
        assert radar["ANVISA"]["pending"] == 0
        assert radar["SNGPC"]["pending"] == 0
        assert radar["SIFAP"]["pending"] == 0

    def test_unknown_kind_ignored(self):
        """Verifica que kinds desconhecidos são ignorados."""
        from src.modules.hub.dashboard_service import _build_risk_radar

        obligations = [
            {"kind": "UNKNOWN_KIND", "status": "pending", "due_date": "2025-12-20"},
        ]
        today = date(2025, 12, 15)

        radar = _build_risk_radar(obligations, today)

        # Nenhum quadrante deve ter contadores incrementados
        assert radar["ANVISA"]["pending"] == 0
        assert radar["SNGPC"]["pending"] == 0
        assert radar["SIFAP"]["pending"] == 0


class TestRiskRadarCounting:
    """Testes para contagem de pendentes e atrasados."""

    def test_pending_count(self):
        """Verifica contagem de obrigações pendentes."""
        from src.modules.hub.dashboard_service import _build_risk_radar

        obligations = [
            {"kind": "SNGPC", "status": "pending", "due_date": "2025-12-20"},
            {"kind": "SNGPC", "status": "pending", "due_date": "2025-12-21"},
            {"kind": "LICENCA_SANITARIA", "status": "pending", "due_date": "2025-12-22"},
        ]
        today = date(2025, 12, 15)

        radar = _build_risk_radar(obligations, today)

        assert radar["SNGPC"]["pending"] == 2
        assert radar["ANVISA"]["pending"] == 1
        assert radar["SIFAP"]["pending"] == 0

    def test_overdue_count_explicit_status(self):
        """Verifica contagem de obrigações atrasadas (status='overdue')."""
        from src.modules.hub.dashboard_service import _build_risk_radar

        obligations = [
            {"kind": "SNGPC", "status": "overdue", "due_date": "2025-12-10"},
            {"kind": "SNGPC", "status": "overdue", "due_date": "2025-12-11"},
        ]
        today = date(2025, 12, 15)

        radar = _build_risk_radar(obligations, today)

        assert radar["SNGPC"]["overdue"] == 2
        assert radar["SNGPC"]["pending"] == 0

    def test_overdue_count_past_due_date(self):
        """Verifica que pendentes com due_date passado são contados como overdue."""
        from src.modules.hub.dashboard_service import _build_risk_radar

        obligations = [
            {"kind": "SIFAP", "status": "pending", "due_date": "2025-12-10"},  # Passado
            {"kind": "SIFAP", "status": "pending", "due_date": "2025-12-20"},  # Futuro
        ]
        today = date(2025, 12, 15)

        radar = _build_risk_radar(obligations, today)

        assert radar["SIFAP"]["overdue"] == 1
        assert radar["SIFAP"]["pending"] == 1

    def test_mixed_counts(self):
        """Verifica contagem com mix de pendentes e atrasados."""
        from src.modules.hub.dashboard_service import _build_risk_radar

        obligations = [
            {"kind": "LICENCA_SANITARIA", "status": "pending", "due_date": "2025-12-20"},
            {"kind": "LICENCA_SANITARIA", "status": "pending", "due_date": "2025-12-21"},
            {"kind": "LICENCA_SANITARIA", "status": "overdue", "due_date": "2025-12-10"},
            {"kind": "SNGPC", "status": "pending", "due_date": "2025-12-08"},  # Passado
            {"kind": "SIFAP", "status": "pending", "due_date": "2025-12-25"},
        ]
        today = date(2025, 12, 15)

        radar = _build_risk_radar(obligations, today)

        assert radar["ANVISA"]["pending"] == 2
        assert radar["ANVISA"]["overdue"] == 1
        assert radar["SNGPC"]["pending"] == 0
        assert radar["SNGPC"]["overdue"] == 1
        assert radar["SIFAP"]["pending"] == 1
        assert radar["SIFAP"]["overdue"] == 0


class TestRiskRadarStatus:
    """Testes para o cálculo do status (green/yellow/red)."""

    def test_status_green_no_obligations(self):
        """Verifica que quadrante sem obrigações tem status 'green'."""
        from src.modules.hub.dashboard_service import _build_risk_radar

        obligations = []
        today = date(2025, 12, 15)

        radar = _build_risk_radar(obligations, today)

        assert radar["ANVISA"]["status"] == "green"
        assert radar["SNGPC"]["status"] == "green"
        assert radar["SIFAP"]["status"] == "green"

    def test_status_yellow_only_pending(self):
        """Verifica que quadrante com apenas pendentes tem status 'yellow'."""
        from src.modules.hub.dashboard_service import _build_risk_radar

        obligations = [
            {"kind": "SNGPC", "status": "pending", "due_date": "2025-12-20"},
        ]
        today = date(2025, 12, 15)

        radar = _build_risk_radar(obligations, today)

        assert radar["SNGPC"]["status"] == "yellow"

    def test_status_red_with_overdue(self):
        """Verifica que quadrante com atrasados tem status 'red'."""
        from src.modules.hub.dashboard_service import _build_risk_radar

        obligations = [
            {"kind": "LICENCA_SANITARIA", "status": "overdue", "due_date": "2025-12-10"},
        ]
        today = date(2025, 12, 15)

        radar = _build_risk_radar(obligations, today)

        assert radar["ANVISA"]["status"] == "red"

    def test_status_red_with_pending_and_overdue(self):
        """Verifica que quadrante com pendentes e atrasados tem status 'red'."""
        from src.modules.hub.dashboard_service import _build_risk_radar

        obligations = [
            {"kind": "SIFAP", "status": "pending", "due_date": "2025-12-20"},
            {"kind": "SIFAP", "status": "overdue", "due_date": "2025-12-10"},
        ]
        today = date(2025, 12, 15)

        radar = _build_risk_radar(obligations, today)

        assert radar["SIFAP"]["status"] == "red"

    def test_status_all_quadrants_different(self):
        """Verifica que cada quadrante pode ter status diferente."""
        from src.modules.hub.dashboard_service import _build_risk_radar

        obligations = [
            {"kind": "LICENCA_SANITARIA", "status": "pending", "due_date": "2025-12-20"},  # Yellow
            {"kind": "SNGPC", "status": "overdue", "due_date": "2025-12-10"},  # Red
            # SIFAP sem obrigações - Green
        ]
        today = date(2025, 12, 15)

        radar = _build_risk_radar(obligations, today)

        assert radar["ANVISA"]["status"] == "yellow"
        assert radar["SNGPC"]["status"] == "red"
        assert radar["SIFAP"]["status"] == "green"
