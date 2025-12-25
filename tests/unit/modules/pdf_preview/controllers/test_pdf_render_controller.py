# -*- coding: utf-8 -*-
"""Testes unitários para controllers/pdf_render_controller.py (lógica headless)."""

from src.modules.pdf_preview.controllers.pdf_render_controller import (
    PdfRenderController,
)


class TestPdfRenderControllerInit:
    """Testes de inicialização."""

    def test_default_init(self):
        """Inicialização padrão deve configurar gap correto."""
        ctrl = PdfRenderController()
        # Não há getter, mas podemos testar via comportamento
        layout = ctrl.calculate_page_layout([(800, 1000)], 1.0)
        assert layout.page_tops[0] == 16  # gap padrão

    def test_custom_gap(self):
        """Gap customizado deve ser respeitado."""
        ctrl = PdfRenderController(gap=32)
        layout = ctrl.calculate_page_layout([(800, 1000)], 1.0)
        assert layout.page_tops[0] == 32


class TestCalculatePageLayout:
    """Testes para cálculo de layout de páginas."""

    def test_single_page_zoom_1(self):
        """Uma página com zoom 1.0 deve ter layout correto."""
        ctrl = PdfRenderController(gap=16)
        layout = ctrl.calculate_page_layout([(800, 1000)], zoom=1.0)

        assert layout.page_tops == [16]
        assert layout.total_width == 832  # 800 + 2*16
        assert layout.total_height == 1032  # 16 + 1000 + 16

    def test_two_pages_zoom_1(self):
        """Duas páginas com zoom 1.0 devem ter layout correto."""
        ctrl = PdfRenderController(gap=16)
        layout = ctrl.calculate_page_layout([(800, 1000), (800, 1000)], zoom=1.0)

        assert layout.page_tops == [16, 1032]  # segunda página após primeira + gap
        assert layout.total_width == 832
        assert layout.total_height == 2048  # 16 + 1000 + 16 + 1000 + 16

    def test_zoom_2(self):
        """Zoom 2.0 deve dobrar dimensões."""
        ctrl = PdfRenderController(gap=16)
        layout = ctrl.calculate_page_layout([(800, 1000)], zoom=2.0)

        assert layout.page_tops == [16]
        assert layout.total_width == 1632  # (800*2) + 2*16
        assert layout.total_height == 2032  # 16 + (1000*2) + 16

    def test_zoom_0_5(self):
        """Zoom 0.5 deve reduzir dimensões pela metade."""
        ctrl = PdfRenderController(gap=16)
        layout = ctrl.calculate_page_layout([(800, 1000)], zoom=0.5)

        assert layout.page_tops == [16]
        assert layout.total_width == 432  # (800*0.5) + 2*16
        assert layout.total_height == 532  # 16 + (1000*0.5) + 16

    def test_empty_pages(self):
        """Lista vazia deve retornar layout vazio."""
        ctrl = PdfRenderController(gap=16)
        layout = ctrl.calculate_page_layout([], zoom=1.0)

        assert layout.page_tops == []
        assert layout.total_width == 0
        assert layout.total_height == 16  # apenas o gap inicial

    def test_different_page_widths(self):
        """Páginas com larguras diferentes devem usar a maior."""
        ctrl = PdfRenderController(gap=16)
        layout = ctrl.calculate_page_layout(
            [(600, 1000), (1000, 1000), (700, 1000)],
            zoom=1.0,
        )

        assert layout.total_width == 1032  # 1000 (maior) + 2*16

    def test_different_page_heights(self):
        """Páginas com alturas diferentes devem acumular corretamente."""
        ctrl = PdfRenderController(gap=16)
        layout = ctrl.calculate_page_layout(
            [(800, 1000), (800, 1500), (800, 800)],
            zoom=1.0,
        )

        # P1: y=16
        # P2: y = 16 + 1000 + 16 = 1032
        # P3: y = 1032 + 1500 + 16 = 2548
        assert layout.page_tops == [16, 1032, 2548]
        assert layout.total_height == 3364  # 2548 + 800 + 16


class TestFindVisiblePageIndices:
    """Testes para encontrar páginas visíveis (viewport)."""

    def test_all_pages_visible(self):
        """Canvas grande deve ver todas as páginas."""
        ctrl = PdfRenderController(gap=16)

        # Setup: 2 páginas, cada 1000px de altura
        page_tops = [16, 1032]
        page_sizes = [(800, 1000), (800, 1000)]

        # Canvas mostra de y=0 até y=3000 (todas visíveis)
        visible = ctrl.find_visible_page_indices(
            page_tops, page_sizes, zoom=1.0, canvas_y0=0, canvas_height=3000, margin=0
        )

        assert visible == [0, 1]

    def test_only_first_page_visible(self):
        """Canvas pequeno deve ver apenas primeira página."""
        ctrl = PdfRenderController(gap=16)

        page_tops = [16, 1032]
        page_sizes = [(800, 1000), (800, 1000)]

        # Canvas mostra de y=0 até y=500 (só primeira)
        visible = ctrl.find_visible_page_indices(
            page_tops, page_sizes, zoom=1.0, canvas_y0=0, canvas_height=500, margin=0
        )

        assert visible == [0]

    def test_only_second_page_visible(self):
        """Canvas scrollado deve ver apenas segunda página."""
        ctrl = PdfRenderController(gap=16)

        page_tops = [16, 1032]
        page_sizes = [(800, 1000), (800, 1000)]

        # Canvas mostra de y=1100 até y=1600 (só segunda)
        visible = ctrl.find_visible_page_indices(
            page_tops, page_sizes, zoom=1.0, canvas_y0=1100, canvas_height=500, margin=0
        )

        assert visible == [1]

    def test_no_pages_visible(self):
        """Canvas scrollado muito longe não deve ver nenhuma página."""
        ctrl = PdfRenderController(gap=16)

        page_tops = [16, 1032]
        page_sizes = [(800, 1000), (800, 1000)]

        # Canvas mostra de y=5000 até y=5500 (fora de todas)
        visible = ctrl.find_visible_page_indices(
            page_tops, page_sizes, zoom=1.0, canvas_y0=5000, canvas_height=500, margin=0
        )

        assert visible == []

    def test_with_margin(self):
        """Margem deve incluir páginas próximas (pré-render)."""
        ctrl = PdfRenderController(gap=16)

        # Três páginas: tops em 16, 1032, 2048 (cada 1000px de altura)
        page_tops = [16, 1032, 2048]
        page_sizes = [(800, 1000), (800, 1000), (800, 1000)]

        # Canvas mostra y=1032 até y=1532 (exatamente a segunda página)
        # Sem margem: só página 1
        visible_no_margin = ctrl.find_visible_page_indices(
            page_tops, page_sizes, zoom=1.0, canvas_y0=1032, canvas_height=500, margin=0
        )
        assert visible_no_margin == [1]

        # Com margem=1000: deve incluir primeira (bottom=1016 > 1032-1000=32)
        # e terceira (top=2048 < 1532+1000=2532)
        visible_with_margin = ctrl.find_visible_page_indices(
            page_tops, page_sizes, zoom=1.0, canvas_y0=1032, canvas_height=500, margin=1000
        )
        assert visible_with_margin == [0, 1, 2]

    def test_zoomed_pages(self):
        """Zoom deve afetar cálculo de visibilidade."""
        ctrl = PdfRenderController(gap=16)

        page_tops = [16, 2032]  # com zoom 2.0
        page_sizes = [(800, 1000), (800, 1000)]

        # Canvas mostra y=0 até y=1500
        visible = ctrl.find_visible_page_indices(
            page_tops, page_sizes, zoom=2.0, canvas_y0=0, canvas_height=1500, margin=0
        )

        # Primeira página: top=16, height=2000 (1000*2) → bottom=2016
        # Segunda página: top=2032 → não visível até 1500
        assert visible == [0]

    def test_empty_pages(self):
        """Lista vazia de páginas deve retornar lista vazia."""
        ctrl = PdfRenderController(gap=16)

        visible = ctrl.find_visible_page_indices([], [], zoom=1.0, canvas_y0=0, canvas_height=1000, margin=0)

        assert visible == []

    def test_partially_visible_top(self):
        """Página parcialmente visível no topo deve ser incluída."""
        ctrl = PdfRenderController(gap=16)

        page_tops = [16]
        page_sizes = [(800, 1000)]

        # Canvas mostra y=900 até y=1400 (só pegando fim da primeira)
        visible = ctrl.find_visible_page_indices(
            page_tops, page_sizes, zoom=1.0, canvas_y0=900, canvas_height=500, margin=0
        )

        assert visible == [0]

    def test_partially_visible_bottom(self):
        """Página parcialmente visível no bottom deve ser incluída."""
        ctrl = PdfRenderController(gap=16)

        page_tops = [16, 1032]
        page_sizes = [(800, 1000), (800, 1000)]

        # Canvas mostra y=900 até y=1100 (pegando fim da primeira e início da segunda)
        visible = ctrl.find_visible_page_indices(
            page_tops, page_sizes, zoom=1.0, canvas_y0=900, canvas_height=200, margin=0
        )

        assert visible == [0, 1]
