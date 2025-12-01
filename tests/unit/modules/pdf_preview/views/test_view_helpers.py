"""Testes unitários para view_helpers do PDF Preview.

REFACTOR-UI-001 - Fase 01
"""

from __future__ import annotations


from src.modules.pdf_preview.views.view_helpers import (
    calculate_button_states,
    detect_file_type,
    find_first_visible_page,
    format_page_label,
    is_pdf_or_image,
)


class TestIsPdfOrImage:
    """Testes para detecção de tipo de arquivo."""

    def test_pdf_by_extension(self):
        """Deve detectar PDF pela extensão .pdf."""
        is_pdf, is_image = is_pdf_or_image("documento.pdf")
        assert is_pdf is True
        assert is_image is False

    def test_pdf_uppercase_extension(self):
        """Deve detectar PDF com extensão maiúscula."""
        is_pdf, is_image = is_pdf_or_image("DOCUMENTO.PDF")
        assert is_pdf is True
        assert is_image is False

    def test_image_jpg(self):
        """Deve detectar imagem JPEG."""
        is_pdf, is_image = is_pdf_or_image("foto.jpg")
        assert is_pdf is False
        assert is_image is True

    def test_image_png(self):
        """Deve detectar imagem PNG."""
        is_pdf, is_image = is_pdf_or_image("screenshot.png")
        assert is_pdf is False
        assert is_image is True

    def test_none_input(self):
        """Deve retornar False para ambos quando input é None."""
        is_pdf, is_image = is_pdf_or_image(None)
        assert is_pdf is False
        assert is_image is False

    def test_empty_string(self):
        """Deve retornar False para ambos quando input é string vazia."""
        is_pdf, is_image = is_pdf_or_image("")
        assert is_pdf is False
        assert is_image is False

    def test_unknown_extension(self):
        """Deve retornar False para ambos com extensão desconhecida."""
        is_pdf, is_image = is_pdf_or_image("arquivo.xyz")
        assert is_pdf is False
        assert is_image is False

    def test_detect_file_type_alias(self):
        """Deve funcionar com alias detect_file_type."""
        result1 = detect_file_type("doc.pdf")
        result2 = is_pdf_or_image("doc.pdf")
        assert result1 == result2


class TestFormatPageLabel:
    """Testes para formatação de labels de página e zoom."""

    def test_first_page_basic(self):
        """Deve formatar primeira página corretamente."""
        page_label, zoom_label = format_page_label(0, 5, 100)
        assert page_label == "Página 1/5"
        assert zoom_label == "100%"

    def test_middle_page(self):
        """Deve formatar página intermediária corretamente."""
        page_label, zoom_label = format_page_label(4, 10, 150)
        assert page_label == "Página 5/10"
        assert zoom_label == "150%"

    def test_last_page(self):
        """Deve formatar última página corretamente."""
        page_label, zoom_label = format_page_label(9, 10, 75)
        assert page_label == "Página 10/10"
        assert zoom_label == "75%"

    def test_with_suffix(self):
        """Deve adicionar sufixo quando fornecido."""
        page_label, zoom_label = format_page_label(2, 5, 100, suffix="• OCR: OK")
        assert page_label == "Página 3/5  • OCR: OK"
        assert zoom_label == "100%"

    def test_custom_prefix(self):
        """Deve usar prefixo customizado."""
        page_label, zoom_label = format_page_label(0, 3, 100, page_prefix="Page")
        assert page_label == "Page 1/3"
        assert zoom_label == "100%"

    def test_zero_total_pages_clamping(self):
        """Deve tratar total_pages zero como 1 (evita divisão por zero)."""
        page_label, zoom_label = format_page_label(0, 0, 100)
        assert page_label == "Página 1/1"
        assert zoom_label == "100%"

    def test_negative_current_page_clamping(self):
        """Deve clampar current_page negativo para 0."""
        page_label, zoom_label = format_page_label(-5, 10, 100)
        assert page_label == "Página 1/10"
        assert zoom_label == "100%"

    def test_current_page_exceeds_total_clamping(self):
        """Deve clampar current_page que excede total."""
        page_label, zoom_label = format_page_label(999, 5, 100)
        assert page_label == "Página 5/5"
        assert zoom_label == "100%"

    def test_zoom_variations(self):
        """Deve formatar diferentes valores de zoom corretamente."""
        _, zoom_label_50 = format_page_label(0, 1, 50)
        _, zoom_label_200 = format_page_label(0, 1, 200)
        _, zoom_label_33 = format_page_label(0, 1, 33)

        assert zoom_label_50 == "50%"
        assert zoom_label_200 == "200%"
        assert zoom_label_33 == "33%"


class TestFindFirstVisiblePage:
    """Testes para encontrar primeira página visível."""

    def test_first_page_at_top(self):
        """Deve retornar índice 0 quando viewport está no topo."""
        page_tops = [16, 1116, 2216]
        page_heights = [1100, 1100, 1100]
        result = find_first_visible_page(0, page_tops, page_heights)
        assert result == 0

    def test_second_page_visible(self):
        """Deve retornar índice 1 quando segunda página está visível."""
        page_tops = [16, 1116, 2216]
        page_heights = [1100, 1100, 1100]
        result = find_first_visible_page(1200, page_tops, page_heights)
        assert result == 1

    def test_last_page_visible(self):
        """Deve retornar última página quando scroll está no fim."""
        page_tops = [16, 1116, 2216]
        page_heights = [1100, 1100, 1100]
        result = find_first_visible_page(9999, page_tops, page_heights)
        assert result == 2

    def test_empty_page_tops(self):
        """Deve retornar 0 quando não há páginas."""
        result = find_first_visible_page(100, [], [])
        assert result == 0

    def test_boundary_between_pages(self):
        """Deve retornar primeira página quando viewport está na fronteira."""
        page_tops = [0, 100, 200]
        page_heights = [100, 100, 100]
        # Viewport em Y=99 ainda está na primeira página
        result = find_first_visible_page(99, page_tops, page_heights)
        assert result == 0

        # Viewport em Y=100 já está na segunda página
        result = find_first_visible_page(100, page_tops, page_heights)
        assert result == 1

    def test_mismatched_heights_length(self):
        """Deve lidar com page_heights mais curto que page_tops."""
        page_tops = [0, 100, 200]
        page_heights = [100]  # Apenas uma altura
        # Deve usar altura 0 para páginas sem altura definida
        result = find_first_visible_page(150, page_tops, page_heights)
        # Esperado: página 2, pois páginas 1 e 2 têm altura 0 (não definida)
        # então 150 >= 100 + 0 = 100 (página 1 termina em 100)
        # e 150 < 200 + 0 = 200 (página 2 começa em 200)
        # mas como Y=150 está entre 100 e 200, retorna a página que "contém" esse Y
        # Como páginas sem altura definida têm altura 0, Y=150 está "após" página 1
        assert result == 2

    def test_single_page(self):
        """Deve funcionar com documento de página única."""
        page_tops = [16]
        page_heights = [1100]
        result = find_first_visible_page(500, page_tops, page_heights)
        assert result == 0


class TestCalculateButtonStates:
    """Testes para cálculo de estados de botões de download."""

    def test_pdf_only(self):
        """Deve habilitar apenas botão PDF quando é PDF."""
        pdf_enabled, img_enabled = calculate_button_states(is_pdf=True, is_image=False)
        assert pdf_enabled is True
        assert img_enabled is False

    def test_image_only(self):
        """Deve habilitar apenas botão de imagem quando é imagem."""
        pdf_enabled, img_enabled = calculate_button_states(is_pdf=False, is_image=True)
        assert pdf_enabled is False
        assert img_enabled is True

    def test_neither_pdf_nor_image(self):
        """Deve desabilitar ambos quando não é nem PDF nem imagem."""
        pdf_enabled, img_enabled = calculate_button_states(is_pdf=False, is_image=False)
        assert pdf_enabled is False
        assert img_enabled is False

    def test_both_pdf_and_image(self):
        """Deve habilitar ambos quando flags são True (caso improvável mas válido)."""
        pdf_enabled, img_enabled = calculate_button_states(is_pdf=True, is_image=True)
        assert pdf_enabled is True
        assert img_enabled is True


# Testes de integração entre funções


class TestIntegrationScenarios:
    """Testes de integração simulando fluxos reais."""

    def test_pdf_workflow(self):
        """Simula workflow completo de abertura de PDF."""
        # 1. Detecta tipo
        is_pdf, is_image = is_pdf_or_image("relatorio.pdf")
        assert is_pdf is True

        # 2. Calcula estados dos botões
        pdf_btn, img_btn = calculate_button_states(is_pdf=is_pdf, is_image=is_image)
        assert pdf_btn is True
        assert img_btn is False

        # 3. Formata label inicial
        page_label, zoom_label = format_page_label(0, 15, 100)
        assert "1/15" in page_label
        assert zoom_label == "100%"

    def test_image_workflow(self):
        """Simula workflow completo de abertura de imagem."""
        # 1. Detecta tipo
        is_pdf, is_image = is_pdf_or_image("foto.png")
        assert is_image is True

        # 2. Calcula estados dos botões
        pdf_btn, img_btn = calculate_button_states(is_pdf=is_pdf, is_image=is_image)
        assert pdf_btn is False
        assert img_btn is True

        # 3. Formata label (imagem = 1 página)
        page_label, zoom_label = format_page_label(0, 1, 150)
        assert "1/1" in page_label
        assert zoom_label == "150%"

    def test_scroll_navigation_workflow(self):
        """Simula navegação com scroll em documento multi-página."""
        page_tops = [16, 516, 1016]
        page_heights = [500, 500, 500]

        # Início do documento
        visible = find_first_visible_page(0, page_tops, page_heights)
        label, _ = format_page_label(visible, 3, 100)
        assert visible == 0
        assert "1/3" in label

        # Meio do documento
        visible = find_first_visible_page(600, page_tops, page_heights)
        label, _ = format_page_label(visible, 3, 100)
        assert visible == 1
        assert "2/3" in label

        # Fim do documento
        visible = find_first_visible_page(1200, page_tops, page_heights)
        label, _ = format_page_label(visible, 3, 100)
        assert visible == 2
        assert "3/3" in label
