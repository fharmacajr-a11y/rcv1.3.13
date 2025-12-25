# -*- coding: utf-8 -*-
"""Testes unitários para helpers/pdf_viewer_helpers.py (funções puras)."""

from src.modules.pdf_preview.helpers.pdf_viewer_helpers import (
    calculate_page_tops,
    update_button_states_from_doc,
    validate_zoom_value,
)


class TestCalculatePageTops:
    """Testes para calculate_page_tops (layout de páginas)."""

    def test_single_page_zoom_1(self):
        """Uma página com zoom 1.0 deve começar em GAP."""
        page_sizes = [(800, 1100)]
        result = calculate_page_tops(page_sizes, zoom=1.0, gap=16)
        assert result == [16]

    def test_two_pages_zoom_1(self):
        """Duas páginas com zoom 1.0 devem ter tops corretos."""
        page_sizes = [(800, 1100), (800, 1100)]
        result = calculate_page_tops(page_sizes, zoom=1.0, gap=16)
        # Primeira página: y=16
        # Segunda página: y = 16 + 1100 + 16 = 1132
        assert result == [16, 1132]

    def test_two_pages_zoom_2(self):
        """Duas páginas com zoom 2.0 devem ter espaçamento maior."""
        page_sizes = [(800, 1100), (800, 1100)]
        result = calculate_page_tops(page_sizes, zoom=2.0, gap=16)
        # Primeira página: y=16
        # Segunda página: y = 16 + (1100*2) + 16 = 2232
        assert result == [16, 2232]

    def test_empty_pages(self):
        """Lista vazia deve retornar lista vazia."""
        result = calculate_page_tops([], zoom=1.0, gap=16)
        assert result == []

    def test_different_page_sizes(self):
        """Páginas de tamanhos diferentes devem calcular tops corretamente."""
        page_sizes = [(800, 1000), (600, 1200), (900, 800)]
        result = calculate_page_tops(page_sizes, zoom=1.0, gap=16)
        # P1: y=16
        # P2: y = 16 + 1000 + 16 = 1032
        # P3: y = 1032 + 1200 + 16 = 2248
        assert result == [16, 1032, 2248]

    def test_custom_gap(self):
        """Gap customizado deve ser respeitado."""
        page_sizes = [(800, 1100)]
        result = calculate_page_tops(page_sizes, zoom=1.0, gap=32)
        assert result == [32]

    def test_fractional_zoom(self):
        """Zoom fracionário deve aplicar corretamente."""
        page_sizes = [(800, 1000), (800, 1000)]
        result = calculate_page_tops(page_sizes, zoom=0.5, gap=16)
        # P1: y=16
        # P2: y = 16 + (1000*0.5) + 16 = 532
        assert result == [16, 532]

    def test_zoom_zero(self):
        """Zoom zero deve resultar em todas páginas com mesma posição."""
        page_sizes = [(800, 1000), (800, 1000)]
        result = calculate_page_tops(page_sizes, zoom=0.0, gap=16)
        # P1: y=16
        # P2: y = 16 + (1000*0) + 16 = 32
        assert result == [16, 32]


class TestUpdateButtonStatesFromDoc:
    """Testes para update_button_states_from_doc (lógica de botões)."""

    def test_pdf_only(self):
        """Documento PDF deve habilitar apenas botão de PDF."""
        pdf_enabled, img_enabled = update_button_states_from_doc(True, False)
        assert pdf_enabled is True
        assert img_enabled is False

    def test_image_only(self):
        """Documento imagem deve habilitar apenas botão de imagem."""
        pdf_enabled, img_enabled = update_button_states_from_doc(False, True)
        assert pdf_enabled is False
        assert img_enabled is True

    def test_neither(self):
        """Sem documento deve desabilitar ambos."""
        pdf_enabled, img_enabled = update_button_states_from_doc(False, False)
        assert pdf_enabled is False
        assert img_enabled is False

    def test_both_true_edge_case(self):
        """Ambos True (caso raro) deve retornar ambos habilitados."""
        pdf_enabled, img_enabled = update_button_states_from_doc(True, True)
        assert pdf_enabled is True
        assert img_enabled is True


class TestValidateZoomValue:
    """Testes para validate_zoom_value (clamp de zoom)."""

    def test_value_within_range(self):
        """Valor dentro do range deve ser retornado inalterado."""
        assert validate_zoom_value(1.5) == 1.5
        assert validate_zoom_value(0.5) == 0.5
        assert validate_zoom_value(3.0) == 3.0

    def test_value_below_min(self):
        """Valor abaixo do mínimo deve ser clamped para min_zoom."""
        assert validate_zoom_value(0.01) == 0.1
        assert validate_zoom_value(-1.0) == 0.1
        assert validate_zoom_value(0.0) == 0.1

    def test_value_above_max(self):
        """Valor acima do máximo deve ser clamped para max_zoom."""
        assert validate_zoom_value(10.0) == 5.0
        assert validate_zoom_value(100.0) == 5.0
        assert validate_zoom_value(6.0) == 5.0

    def test_exactly_min(self):
        """Valor exatamente no mínimo deve ser aceito."""
        assert validate_zoom_value(0.1) == 0.1

    def test_exactly_max(self):
        """Valor exatamente no máximo deve ser aceito."""
        assert validate_zoom_value(5.0) == 5.0

    def test_custom_range(self):
        """Range customizado deve ser respeitado."""
        assert validate_zoom_value(15.0, min_zoom=10.0, max_zoom=20.0) == 15.0
        assert validate_zoom_value(5.0, min_zoom=10.0, max_zoom=20.0) == 10.0
        assert validate_zoom_value(25.0, min_zoom=10.0, max_zoom=20.0) == 20.0

    def test_negative_zoom(self):
        """Zoom negativo deve ser clamped para min."""
        assert validate_zoom_value(-5.0) == 0.1

    def test_edge_case_min_equals_max(self):
        """Min igual a max deve retornar esse valor."""
        assert validate_zoom_value(1.0, min_zoom=2.0, max_zoom=2.0) == 2.0
        assert validate_zoom_value(5.0, min_zoom=2.0, max_zoom=2.0) == 2.0
