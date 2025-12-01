"""Testes unitários para view_helpers do PDF Preview - FASE 02.

REFACTOR-UI-005 - Fase 02: Zoom calculations
Cobertura: calculate_zoom_step, calculate_zoom_fit_width,
           calculate_zoom_anchor, should_apply_zoom_change
"""

from __future__ import annotations

from src.modules.pdf_preview.views.view_helpers import (
    calculate_zoom_anchor,
    calculate_zoom_fit_width,
    calculate_zoom_step,
    should_apply_zoom_change,
)


class TestCalculateZoomStep:
    """Testes para cálculo de zoom por steps (wheel/scroll)."""

    def test_zoom_in_single_step(self):
        """Deve aumentar zoom em 0.1 com 1 step positivo."""
        result = calculate_zoom_step(1.0, 1)
        assert result == 1.1

    def test_zoom_out_single_step(self):
        """Deve diminuir zoom em 0.1 com 1 step negativo."""
        result = calculate_zoom_step(1.0, -1)
        assert result == 0.9

    def test_zoom_in_multiple_steps(self):
        """Deve aumentar zoom proporcionalmente com múltiplos steps."""
        result = calculate_zoom_step(1.0, 3)
        assert result == 1.3

    def test_zoom_out_multiple_steps(self):
        """Deve diminuir zoom proporcionalmente com múltiplos steps."""
        result = calculate_zoom_step(1.0, -2)
        assert result == 0.8

    def test_clamp_at_max_zoom(self):
        """Deve clampar no máximo (6.0) quando exceder."""
        result = calculate_zoom_step(5.9, 5)
        assert result == 6.0

    def test_clamp_at_min_zoom(self):
        """Deve clampar no mínimo (0.2) quando ficar abaixo."""
        result = calculate_zoom_step(0.3, -5)
        assert result == 0.2

    def test_custom_min_max_zoom(self):
        """Deve respeitar limites customizados."""
        # 0.5 + 10*0.1 = 1.5, clamp [0.1, 2.0] -> 1.5
        result = calculate_zoom_step(0.5, 10, min_zoom=0.1, max_zoom=2.0)
        assert result == 1.5

    def test_custom_step_size(self):
        """Deve usar step customizado."""
        result = calculate_zoom_step(1.0, 2, step=0.05)
        assert result == 1.1

    def test_fractional_steps(self):
        """Deve lidar com steps fracionários."""
        result = calculate_zoom_step(1.0, 1.5)
        assert result == 1.15

    def test_zero_steps_no_change(self):
        """Deve retornar zoom atual quando steps = 0."""
        result = calculate_zoom_step(1.5, 0)
        assert result == 1.5

    def test_rounding_precision(self):
        """Deve arredondar para 2 casas decimais."""
        # 1.0 + 0.123456789 * 1.0 = 1.123456789 -> round(1.12, 2) = 1.12
        result = calculate_zoom_step(1.0, 0.123456789, step=1.0)
        assert result == 1.12


class TestCalculateZoomFitWidth:
    """Testes para cálculo de zoom fit-width."""

    def test_exact_fit_no_gap(self):
        """Deve retornar 1.0 quando canvas e página têm mesma largura (sem gap)."""
        result = calculate_zoom_fit_width(800, 800, gap=0)
        assert result == 1.0

    def test_fit_with_default_gap(self):
        """Deve considerar gap padrão de 16px."""
        result = calculate_zoom_fit_width(800, 600)
        # (800 - 16) / 600 = 784 / 600 = 1.306... -> 1.31
        assert result == 1.31

    def test_zoom_out_large_page(self):
        """Deve reduzir zoom quando página é maior que canvas."""
        result = calculate_zoom_fit_width(400, 1000)
        # (400 - 16) / 1000 = 384 / 1000 = 0.384 -> 0.38
        assert result == 0.38

    def test_zoom_in_small_page(self):
        """Deve aumentar zoom quando página é menor que canvas."""
        result = calculate_zoom_fit_width(1000, 400)
        # (1000 - 16) / 400 = 984 / 400 = 2.46
        assert result == 2.46

    def test_clamp_at_min_zoom(self):
        """Deve clampar no mínimo quando cálculo resulta abaixo."""
        result = calculate_zoom_fit_width(100, 800, gap=20)
        # (100 - 20) / 800 = 80 / 800 = 0.1 -> clamp para 0.2
        assert result == 0.2

    def test_clamp_at_max_zoom(self):
        """Deve clampar no máximo quando cálculo excede."""
        result = calculate_zoom_fit_width(3000, 400)
        # (3000 - 16) / 400 = 7.46 -> clamp para 6.0
        assert result == 6.0

    def test_custom_min_max(self):
        """Deve respeitar limites customizados."""
        result = calculate_zoom_fit_width(800, 400, min_zoom=0.5, max_zoom=1.5)
        # (800 - 16) / 400 = 1.96 -> clamp para 1.5
        assert result == 1.5

    def test_custom_gap(self):
        """Deve usar gap customizado."""
        result = calculate_zoom_fit_width(800, 600, gap=100)
        # (800 - 100) / 600 = 700 / 600 = 1.166... -> 1.17
        assert result == 1.17

    def test_zero_page_width_returns_min(self):
        """Deve retornar min_zoom quando page_width = 0 (evita divisão por zero)."""
        result = calculate_zoom_fit_width(800, 0)
        assert result == 0.2

    def test_negative_page_width_returns_min(self):
        """Deve retornar min_zoom quando page_width negativo."""
        result = calculate_zoom_fit_width(800, -100)
        assert result == 0.2

    def test_small_canvas_width(self):
        """Deve lidar com canvas muito pequeno."""
        result = calculate_zoom_fit_width(10, 100, gap=5)
        # (10 - 5) / 100 = 0.05 -> clamp para 0.2
        assert result == 0.2

    def test_gap_larger_than_canvas(self):
        """Deve garantir largura efetiva >= 1 quando gap > canvas_width."""
        result = calculate_zoom_fit_width(10, 100, gap=50)
        # max(1, 10 - 50) = 1, então 1 / 100 = 0.01 -> clamp para 0.2
        assert result == 0.2


class TestCalculateZoomAnchor:
    """Testes para cálculo de ancoragem de zoom no cursor."""

    def test_center_of_canvas(self):
        """Deve retornar (0.5, 0.5) para cursor no centro."""
        fx, fy = calculate_zoom_anchor(400, 300, (0, 0, 800, 600))
        assert fx == 0.5
        assert fy == 0.5

    def test_top_left_corner(self):
        """Deve retornar (0.0, 0.0) para cursor no canto superior esquerdo."""
        fx, fy = calculate_zoom_anchor(0, 0, (0, 0, 800, 600))
        assert fx == 0.0
        assert fy == 0.0

    def test_bottom_right_corner(self):
        """Deve retornar (1.0, 1.0) para cursor no canto inferior direito."""
        fx, fy = calculate_zoom_anchor(800, 600, (0, 0, 800, 600))
        assert fx == 1.0
        assert fy == 1.0

    def test_offset_bbox(self):
        """Deve calcular corretamente com bbox que não começa em (0,0)."""
        fx, fy = calculate_zoom_anchor(600, 400, (100, 100, 900, 700))
        # fx = (600 - 100) / (900 - 100) = 500 / 800 = 0.625
        # fy = (400 - 100) / (700 - 100) = 300 / 600 = 0.5
        assert fx == 0.625
        assert fy == 0.5

    def test_degenerate_bbox_zero_width(self):
        """Deve retornar (0.0, fy) quando largura do bbox = 0."""
        fx, fy = calculate_zoom_anchor(100, 200, (100, 100, 100, 300))
        assert fx == 0.0
        # fy = (200 - 100) / (300 - 100) = 100 / 200 = 0.5
        assert fy == 0.5

    def test_degenerate_bbox_zero_height(self):
        """Deve retornar (fx, 0.0) quando altura do bbox = 0."""
        fx, fy = calculate_zoom_anchor(200, 100, (100, 100, 300, 100))
        # fx = (200 - 100) / (300 - 100) = 100 / 200 = 0.5
        assert fx == 0.5
        assert fy == 0.0

    def test_degenerate_bbox_point(self):
        """Deve retornar (0.0, 0.0) quando bbox é um ponto (largura e altura = 0)."""
        fx, fy = calculate_zoom_anchor(100, 200, (100, 100, 100, 100))
        assert fx == 0.0
        assert fy == 0.0

    def test_cursor_before_bbox(self):
        """Deve clampar fx/fy para 0.0 quando cursor está antes do bbox."""
        fx, fy = calculate_zoom_anchor(-100, -50, (0, 0, 800, 600))
        # fx = (-100 - 0) / 800 = -0.125 -> clamp para 0.0
        # fy = (-50 - 0) / 600 = -0.083 -> clamp para 0.0
        assert fx == 0.0
        assert fy == 0.0

    def test_cursor_after_bbox(self):
        """Deve clampar fx/fy para 1.0 quando cursor está além do bbox."""
        fx, fy = calculate_zoom_anchor(1000, 800, (0, 0, 800, 600))
        # fx = 1000 / 800 = 1.25 -> clamp para 1.0
        # fy = 800 / 600 = 1.333 -> clamp para 1.0
        assert fx == 1.0
        assert fy == 1.0

    def test_fractional_position(self):
        """Deve calcular frações corretas para posições arbitrárias."""
        fx, fy = calculate_zoom_anchor(100, 200, (0, 0, 800, 600))
        # fx = 100 / 800 = 0.125
        # fy = 200 / 600 = 0.333...
        assert fx == 0.125
        assert abs(fy - 0.3333333333333333) < 1e-9

    def test_negative_bbox_coordinates(self):
        """Deve lidar com bbox que tem coordenadas negativas (scroll)."""
        fx, fy = calculate_zoom_anchor(100, 50, (-200, -100, 600, 500))
        # fx = (100 - (-200)) / (600 - (-200)) = 300 / 800 = 0.375
        # fy = (50 - (-100)) / (500 - (-100)) = 150 / 600 = 0.25
        assert fx == 0.375
        assert fy == 0.25


class TestShouldApplyZoomChange:
    """Testes para determinação se mudança de zoom é significativa."""

    def test_significant_change_positive(self):
        """Deve retornar True para mudança significativa positiva."""
        result = should_apply_zoom_change(1.0, 1.1)
        assert result is True

    def test_significant_change_negative(self):
        """Deve retornar True para mudança significativa negativa."""
        result = should_apply_zoom_change(1.0, 0.9)
        assert result is True

    def test_insignificant_change_very_small(self):
        """Deve retornar False para mudança muito pequena (< threshold)."""
        result = should_apply_zoom_change(1.0, 1.0000000001)
        assert result is False

    def test_no_change(self):
        """Deve retornar False quando zoom não muda."""
        result = should_apply_zoom_change(1.5, 1.5)
        assert result is False

    def test_custom_threshold_pass(self):
        """Deve retornar True quando diferença >= threshold customizado."""
        result = should_apply_zoom_change(0.5, 0.6, threshold=0.05)
        assert result is True

    def test_custom_threshold_fail(self):
        """Deve retornar False quando diferença < threshold customizado."""
        result = should_apply_zoom_change(0.5, 0.52, threshold=0.05)
        assert result is False

    def test_boundary_exactly_threshold(self):
        """Deve retornar True quando diferença = threshold exato."""
        result = should_apply_zoom_change(1.0, 1.1, threshold=0.1)
        assert result is True

    def test_negative_to_positive_change(self):
        """Deve calcular diferença absoluta corretamente."""
        result = should_apply_zoom_change(0.8, 1.2)
        assert result is True

    def test_large_zoom_values(self):
        """Deve funcionar com valores grandes de zoom."""
        result = should_apply_zoom_change(5.0, 5.5)
        assert result is True

    def test_small_zoom_values(self):
        """Deve funcionar com valores pequenos de zoom."""
        result = should_apply_zoom_change(0.2, 0.3)
        assert result is True


# Testes de integração


class TestZoomIntegrationScenarios:
    """Testes de integração simulando workflows reais de zoom."""

    def test_wheel_zoom_in_workflow(self):
        """Simula zoom in com mouse wheel."""
        # 1. Usuário rola wheel (3 steps)
        old_zoom = 1.0
        new_zoom = calculate_zoom_step(old_zoom, 3)
        assert new_zoom == 1.3

        # 2. Verifica se deve aplicar
        should_apply = should_apply_zoom_change(old_zoom, new_zoom)
        assert should_apply is True

        # 3. Calcula ancoragem no cursor
        fx, fy = calculate_zoom_anchor(400, 300, (0, 0, 800, 600))
        assert fx == 0.5
        assert fy == 0.5

    def test_wheel_zoom_out_workflow(self):
        """Simula zoom out com mouse wheel."""
        old_zoom = 1.5
        new_zoom = calculate_zoom_step(old_zoom, -5)
        assert new_zoom == 1.0

        should_apply = should_apply_zoom_change(old_zoom, new_zoom)
        assert should_apply is True

    def test_fit_width_workflow(self):
        """Simula ação de fit-to-width."""
        # 1. Calcula zoom para caber na largura
        canvas_width = 1000
        page_width = 612  # típico A4 em pontos
        zoom = calculate_zoom_fit_width(canvas_width, page_width)
        # (1000 - 16) / 612 = 1.608... -> 1.61
        assert zoom == 1.61

        # 2. Verifica se deve aplicar mudança
        old_zoom = 1.0
        should_apply = should_apply_zoom_change(old_zoom, zoom)
        assert should_apply is True

    def test_zoom_limit_clamping_workflow(self):
        """Simula tentativa de zoom além dos limites."""
        # Tentativa de zoom muito alto
        old_zoom = 5.8
        new_zoom = calculate_zoom_step(old_zoom, 10)
        assert new_zoom == 6.0  # clamped

        # Tentativa de zoom muito baixo
        old_zoom = 0.3
        new_zoom = calculate_zoom_step(old_zoom, -10)
        assert new_zoom == 0.2  # clamped

    def test_negligible_zoom_change_workflow(self):
        """Simula mudança negligenciável que não deve ser aplicada."""
        old_zoom = 1.0
        # Pequena variação numérica (ex: floating point error)
        new_zoom = 1.0 + 1e-10

        should_apply = should_apply_zoom_change(old_zoom, new_zoom)
        assert should_apply is False

    def test_resize_window_fit_width_workflow(self):
        """Simula redimensionamento de janela com fit-width ativo."""
        page_width = 600

        # Janela inicial
        zoom1 = calculate_zoom_fit_width(800, page_width)
        # (800 - 16) / 600 = 1.31
        assert zoom1 == 1.31

        # Usuário redimensiona janela (mais estreita)
        zoom2 = calculate_zoom_fit_width(500, page_width)
        # (500 - 16) / 600 = 0.81
        assert zoom2 == 0.81

        # Usuário redimensiona janela (mais larga)
        zoom3 = calculate_zoom_fit_width(1200, page_width)
        # (1200 - 16) / 600 = 1.97
        assert zoom3 == 1.97

    def test_anchor_at_edge_workflow(self):
        """Simula zoom com cursor nos cantos (edge cases)."""
        # Zoom com cursor no canto superior esquerdo
        fx1, fy1 = calculate_zoom_anchor(0, 0, (0, 0, 800, 600))
        assert fx1 == 0.0
        assert fy1 == 0.0

        # Zoom com cursor no canto inferior direito
        fx2, fy2 = calculate_zoom_anchor(800, 600, (0, 0, 800, 600))
        assert fx2 == 1.0
        assert fy2 == 1.0

    def test_multi_step_zoom_sequence(self):
        """Simula sequência de múltiplos zooms."""
        zoom = 1.0

        # Zoom in 3x
        zoom = calculate_zoom_step(zoom, 1)
        assert zoom == 1.1
        zoom = calculate_zoom_step(zoom, 1)
        assert zoom == 1.2
        zoom = calculate_zoom_step(zoom, 1)
        assert zoom == 1.3

        # Zoom out 2x
        zoom = calculate_zoom_step(zoom, -1)
        assert zoom == 1.2
        zoom = calculate_zoom_step(zoom, -1)
        assert zoom == 1.1
