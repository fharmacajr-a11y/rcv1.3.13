"""Testes unitários para src.ui.wheel_windows.

Módulo testado: função pura wheel_steps() que normaliza evento de scroll no Windows.
Cobertura esperada: 100% (8 linhas, sem dependências externas).
"""

from unittest.mock import Mock
import pytest
from src.ui.wheel_windows import wheel_steps


class TestWheelSteps:
    """Testes para wheel_steps() - normalização de eventos de scroll."""

    def test_delta_zero_returns_zero(self):
        """Delta 0 retorna 0 steps."""
        event = Mock(delta=0)
        assert wheel_steps(event) == 0

    def test_delta_missing_returns_zero(self):
        """Evento sem atributo 'delta' retorna 0."""
        event = Mock(spec=[])
        assert wheel_steps(event) == 0

    def test_delta_120_returns_one_step(self):
        """Delta 120 (scroll up padrão Windows) retorna 1 step."""
        event = Mock(delta=120)
        assert wheel_steps(event) == 1

    def test_delta_minus_120_returns_minus_one_step(self):
        """Delta -120 (scroll down padrão Windows) retorna -1 step."""
        event = Mock(delta=-120)
        assert wheel_steps(event) == -1

    def test_delta_240_returns_two_steps(self):
        """Delta 240 (scroll rápido) retorna 2 steps."""
        event = Mock(delta=240)
        assert wheel_steps(event) == 2

    def test_delta_minus_240_returns_minus_two_steps(self):
        """Delta -240 (scroll rápido negativo) retorna -2 steps."""
        event = Mock(delta=-240)
        assert wheel_steps(event) == -2

    def test_delta_60_positive_small_returns_one(self):
        """Delta positivo < 120 retorna 1 (fallback para pequenos valores)."""
        event = Mock(delta=60)
        result = wheel_steps(event)
        # step = 60 // 120 = 0, mas o código faz fallback: 1 if d > 0 else -1
        assert result == 1

    def test_delta_minus_60_negative_small_returns_minus_one(self):
        """Delta negativo > -120 retorna -1 (fallback para pequenos valores)."""
        event = Mock(delta=-60)
        result = wheel_steps(event)
        # step = -60 // 120 = -1, mas o código faz fallback se step == 0
        # Na verdade -60 // 120 = -1 (divisão inteira em Python), então retorna -1 diretamente
        assert result == -1

    def test_delta_1_returns_one(self):
        """Delta 1 (mínimo positivo) retorna 1 via fallback."""
        event = Mock(delta=1)
        result = wheel_steps(event)
        # step = 1 // 120 = 0, então fallback: 1 if d > 0 else -1
        assert result == 1

    def test_delta_minus_1_returns_minus_one(self):
        """Delta -1 (mínimo negativo) retorna -1 via fallback."""
        event = Mock(delta=-1)
        result = wheel_steps(event)
        # step = -1 // 120 = -1 em Python (floor division)
        assert result == -1

    def test_delta_360_returns_three_steps(self):
        """Delta 360 (3x scroll padrão) retorna 3 steps."""
        event = Mock(delta=360)
        assert wheel_steps(event) == 3

    def test_delta_minus_480_returns_minus_four_steps(self):
        """Delta -480 (4x scroll padrão negativo) retorna -4 steps."""
        event = Mock(delta=-480)
        assert wheel_steps(event) == -4

    @pytest.mark.parametrize(
        "delta,expected",
        [
            (0, 0),
            (120, 1),
            (-120, -1),
            (240, 2),
            (-240, -2),
            (119, 1),  # fallback positivo
            (-119, -1),  # fallback negativo
            (121, 1),
            (-121, -2),  # -121 // 120 = -2
            (600, 5),
            (-600, -5),
        ],
    )
    def test_various_deltas(self, delta, expected):
        """Testa diversos valores de delta (parameterized)."""
        event = Mock(delta=delta)
        assert wheel_steps(event) == expected
