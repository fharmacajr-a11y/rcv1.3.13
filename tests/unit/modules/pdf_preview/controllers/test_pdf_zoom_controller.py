# -*- coding: utf-8 -*-
"""Testes unitários para controllers/pdf_zoom_controller.py (lógica headless)."""

from src.modules.pdf_preview.controllers.pdf_zoom_controller import PdfZoomController


class TestPdfZoomControllerInit:
    """Testes de inicialização do controller."""

    def test_default_init(self):
        """Inicialização padrão deve configurar limites corretos."""
        ctrl = PdfZoomController()
        assert ctrl.current_zoom == 1.0
        assert ctrl.img_zoom == 1.0
        assert ctrl.is_fit_mode is False

    def test_custom_limits(self):
        """Limites customizados devem ser aceitos."""
        ctrl = PdfZoomController(min_zoom=0.5, max_zoom=10.0, zoom_step=0.2)
        # Testa clamp para min ao tentar ir abaixo
        result = ctrl.calculate_zoom_by_delta(0.6, wheel_steps=-1)
        assert result == 0.5  # 0.6 - 0.2 = 0.4, clamped to 0.5


class TestCalculateZoomByDelta:
    """Testes para cálculo de zoom por delta (wheel steps)."""

    def test_zoom_in_from_1(self):
        """Zoom in de 1.0 com +1 step deve aumentar 0.1."""
        ctrl = PdfZoomController()
        result = ctrl.calculate_zoom_by_delta(1.0, wheel_steps=1)
        assert result == 1.1

    def test_zoom_out_from_1(self):
        """Zoom out de 1.0 com -1 step deve diminuir 0.1."""
        ctrl = PdfZoomController()
        result = ctrl.calculate_zoom_by_delta(1.0, wheel_steps=-1)
        assert result == 0.9

    def test_multiple_steps_in(self):
        """Múltiplos steps devem acumular corretamente."""
        ctrl = PdfZoomController()
        result = ctrl.calculate_zoom_by_delta(1.0, wheel_steps=5)
        assert result == 1.5

    def test_multiple_steps_out(self):
        """Múltiplos steps negativos devem diminuir corretamente."""
        ctrl = PdfZoomController()
        result = ctrl.calculate_zoom_by_delta(1.0, wheel_steps=-3)
        assert result == 0.7

    def test_clamp_at_min_pdf(self):
        """Zoom abaixo do mínimo (PDF) deve ser clamped para 0.2."""
        ctrl = PdfZoomController(min_zoom=0.2)
        result = ctrl.calculate_zoom_by_delta(0.3, wheel_steps=-5)
        assert result == 0.2

    def test_clamp_at_max_pdf(self):
        """Zoom acima do máximo (PDF) deve ser clamped para 6.0."""
        ctrl = PdfZoomController(max_zoom=6.0)
        result = ctrl.calculate_zoom_by_delta(5.8, wheel_steps=5)
        assert result == 6.0

    def test_image_mode_different_limits(self):
        """Modo imagem deve usar limites 0.1-5.0."""
        ctrl = PdfZoomController()
        result = ctrl.calculate_zoom_by_delta(0.2, wheel_steps=-5, is_image=True)
        assert result == 0.1  # min para imagem

    def test_fractional_steps(self):
        """Steps fracionários devem funcionar."""
        ctrl = PdfZoomController()
        result = ctrl.calculate_zoom_by_delta(1.0, wheel_steps=0.5)
        assert result == 1.05

    def test_zero_steps(self):
        """Zero steps deve manter zoom atual."""
        ctrl = PdfZoomController()
        result = ctrl.calculate_zoom_by_delta(1.5, wheel_steps=0)
        assert result == 1.5


class TestCalculateFitToWidthZoom:
    """Testes para cálculo de zoom fit-to-width."""

    def test_fit_exact(self):
        """Canvas e página com mesma largura devem dar zoom ~1.0."""
        ctrl = PdfZoomController()
        # Canvas 1000px, página 800px, gap 2*16=32 → disponível 968px
        result = ctrl.calculate_fit_to_width_zoom(1000, 800, gap=16)
        assert result == 1.21  # 968/800 = 1.21

    def test_fit_narrow_canvas(self):
        """Canvas menor que página deve dar zoom < 1.0."""
        ctrl = PdfZoomController()
        result = ctrl.calculate_fit_to_width_zoom(500, 800, gap=16)
        assert result == 0.58  # (500-32)/800 = 0.585 → arredondado para 0.58

    def test_fit_wide_canvas(self):
        """Canvas maior que página deve dar zoom > 1.0."""
        ctrl = PdfZoomController()
        result = ctrl.calculate_fit_to_width_zoom(2000, 800, gap=16)
        assert result == 2.46  # (2000-32)/800 = 2.46

    def test_clamp_at_min(self):
        """Zoom fit abaixo do mínimo deve ser clamped."""
        ctrl = PdfZoomController()
        result = ctrl.calculate_fit_to_width_zoom(50, 1000, gap=16)
        assert result == 0.1  # mínimo

    def test_clamp_at_max(self):
        """Zoom fit acima do máximo deve ser clamped."""
        ctrl = PdfZoomController()
        result = ctrl.calculate_fit_to_width_zoom(10000, 800, gap=16)
        assert result == 6.0  # máximo para PDF

    def test_custom_gap(self):
        """Gap customizado deve ser respeitado."""
        ctrl = PdfZoomController()
        result = ctrl.calculate_fit_to_width_zoom(1000, 800, gap=50)
        assert result == 1.12  # (1000-100)/800 = 1.125

    def test_image_mode_limits(self):
        """Modo imagem deve ter max 5.0."""
        ctrl = PdfZoomController()
        result = ctrl.calculate_fit_to_width_zoom(10000, 800, gap=16, is_image=True)
        assert result == 5.0  # max para imagem

    def test_zero_width_canvas(self):
        """Canvas com width zero deve usar 1 como fallback."""
        ctrl = PdfZoomController()
        result = ctrl.calculate_fit_to_width_zoom(0, 800, gap=16)
        # available_width = max(1, 0-32) = 1
        # 1/800 = 0.00125 → clamped to 0.1
        assert result == 0.1

    def test_zero_width_page(self):
        """Página com width zero deve usar 1 como fallback."""
        ctrl = PdfZoomController()
        result = ctrl.calculate_fit_to_width_zoom(1000, 0, gap=16)
        # 968/1 = 968 → clamped to 6.0
        assert result == 6.0


class TestApplyZoomToImage:
    """Testes para aplicação de zoom em imagem."""

    def test_zoom_in_image(self):
        """Zoom in em imagem deve atualizar img_zoom."""
        ctrl = PdfZoomController()
        new_zoom = ctrl.apply_zoom_to_image(wheel_steps=2)
        assert new_zoom == 1.2
        assert ctrl.img_zoom == 1.2

    def test_zoom_out_image(self):
        """Zoom out em imagem deve atualizar img_zoom."""
        ctrl = PdfZoomController()
        new_zoom = ctrl.apply_zoom_to_image(wheel_steps=-3)
        assert new_zoom == 0.7
        assert ctrl.img_zoom == 0.7

    def test_clamp_image_min(self):
        """Zoom de imagem não deve ir abaixo de 0.1."""
        ctrl = PdfZoomController()
        new_zoom = ctrl.apply_zoom_to_image(wheel_steps=-20)
        assert new_zoom == 0.1
        assert ctrl.img_zoom == 0.1

    def test_clamp_image_max(self):
        """Zoom de imagem não deve ir acima de 5.0."""
        ctrl = PdfZoomController()
        new_zoom = ctrl.apply_zoom_to_image(wheel_steps=50)
        assert new_zoom == 5.0
        assert ctrl.img_zoom == 5.0


class TestSetExactZoom:
    """Testes para definição de zoom exato."""

    def test_set_zoom_1_5(self):
        """Definir zoom 1.5 deve atualizar estado."""
        ctrl = PdfZoomController()
        result = ctrl.set_exact_zoom(1.5)
        assert result == 1.5
        assert ctrl.current_zoom == 1.5
        assert ctrl.is_fit_mode is False

    def test_set_zoom_with_fit_mode(self):
        """Definir zoom com fit_mode deve atualizar flag."""
        ctrl = PdfZoomController()
        result = ctrl.set_exact_zoom(1.2, fit_mode=True)
        assert result == 1.2
        assert ctrl.is_fit_mode is True

    def test_clamp_below_min(self):
        """Zoom exato abaixo do mínimo deve ser clamped."""
        ctrl = PdfZoomController(min_zoom=0.2)
        result = ctrl.set_exact_zoom(0.1)
        assert result == 0.2
        assert ctrl.current_zoom == 0.2

    def test_clamp_above_max(self):
        """Zoom exato acima do máximo deve ser clamped."""
        ctrl = PdfZoomController(max_zoom=6.0)
        result = ctrl.set_exact_zoom(10.0)
        assert result == 6.0
        assert ctrl.current_zoom == 6.0

    def test_set_zoom_with_pdf_controller_mock(self):
        """Com PdfPreviewController, deve delegar para ele."""
        ctrl = PdfZoomController()

        # Mock simples: objeto com set_zoom e state.zoom
        class MockPdfController:
            class State:
                zoom = 1.5

            def __init__(self):
                self.state = self.State()
                self.last_zoom = None
                self.last_mode = None

            def set_zoom(self, zoom, fit_mode):
                self.last_zoom = zoom
                self.last_mode = fit_mode
                self.state.zoom = zoom * 1.1  # simula ajuste interno

        mock = MockPdfController()
        result = ctrl.set_exact_zoom(2.0, pdf_controller=mock)

        assert mock.last_zoom == 2.0
        assert mock.last_mode == "custom"
        assert result == 2.2  # zoom ajustado pelo mock
        assert ctrl.current_zoom == 2.2


class TestToggleFit100:
    """Testes para toggle entre fit e 100%."""

    def test_toggle_from_custom_to_fit(self):
        """De custom → fit deve calcular fit-to-width."""
        ctrl = PdfZoomController()
        ctrl._fit_mode = False

        new_zoom, now_fit = ctrl.toggle_fit_100(1000, 800)
        assert now_fit is True
        assert new_zoom == 1.21  # (1000-32)/800
        assert ctrl.is_fit_mode is True

    def test_toggle_from_fit_to_100(self):
        """De fit → custom deve voltar para 1.0."""
        ctrl = PdfZoomController()
        ctrl._fit_mode = True

        new_zoom, now_fit = ctrl.toggle_fit_100(1000, 800)
        assert now_fit is False
        assert new_zoom == 1.0
        assert ctrl.is_fit_mode is False

    def test_toggle_with_pdf_controller(self):
        """Toggle com PdfPreviewController deve delegar."""
        ctrl = PdfZoomController()

        class MockPdfController:
            class State:
                zoom = 1.0

            def __init__(self):
                self.state = self.State()

            def set_zoom(self, zoom, fit_mode):
                self.state.zoom = zoom

        mock = MockPdfController()
        ctrl._fit_mode = False

        new_zoom, now_fit = ctrl.toggle_fit_100(1000, 800, pdf_controller=mock)
        assert now_fit is True
        # Deve ter calculado e aplicado fit
        assert new_zoom == 1.21


class TestApplyZoomToPdf:
    """Testes para aplicação de zoom em PDF."""

    def test_apply_without_controller(self):
        """Sem controller, deve usar cálculo interno."""
        ctrl = PdfZoomController()
        new_zoom = ctrl.apply_zoom_to_pdf(wheel_steps=2, pdf_controller=None)
        assert new_zoom == 1.2
        assert ctrl.current_zoom == 1.2
        assert ctrl.is_fit_mode is False

    def test_apply_with_controller(self):
        """Com controller, deve delegar para ele."""
        ctrl = PdfZoomController()

        class MockPdfController:
            def apply_zoom_delta(self, steps):
                return 1.0 + steps * 0.15  # step diferente para testar

        mock = MockPdfController()
        new_zoom = ctrl.apply_zoom_to_pdf(wheel_steps=2, pdf_controller=mock)

        assert new_zoom == 1.3  # 1.0 + 2*0.15
        assert ctrl.current_zoom == 1.3
        assert ctrl.is_fit_mode is False
