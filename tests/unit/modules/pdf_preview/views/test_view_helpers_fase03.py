"""Testes unitários para view_helpers do PDF Preview - FASE 03.

REFACTOR-UI-006 - Fase 03: Page navigation logic
Cobertura: clamp_page_index, get_next_page_index, get_prev_page_index,
           get_first_page_index, get_last_page_index
"""

from __future__ import annotations

from src.modules.pdf_preview.views.view_helpers import (
    clamp_page_index,
    get_first_page_index,
    get_last_page_index,
    get_next_page_index,
    get_prev_page_index,
)


class TestClampPageIndex:
    """Testes para clamp de índice de página."""

    def test_index_within_range(self):
        """Deve retornar índice quando está dentro do range válido."""
        result = clamp_page_index(5, 10)
        assert result == 5

    def test_index_at_start(self):
        """Deve retornar 0 quando índice está no início."""
        result = clamp_page_index(0, 10)
        assert result == 0

    def test_index_at_end(self):
        """Deve retornar total_pages-1 quando índice está no fim."""
        result = clamp_page_index(9, 10)
        assert result == 9

    def test_negative_index_clamps_to_zero(self):
        """Deve clampar índice negativo para 0."""
        result = clamp_page_index(-3, 10)
        assert result == 0

    def test_index_exceeds_total_pages(self):
        """Deve clampar índice que excede total_pages para total_pages-1."""
        result = clamp_page_index(15, 10)
        assert result == 9

    def test_zero_total_pages(self):
        """Deve retornar 0 quando total_pages = 0."""
        result = clamp_page_index(5, 0)
        assert result == 0

    def test_negative_total_pages(self):
        """Deve retornar 0 quando total_pages negativo."""
        result = clamp_page_index(5, -3)
        assert result == 0

    def test_single_page_document(self):
        """Deve funcionar corretamente com documento de 1 página."""
        assert clamp_page_index(0, 1) == 0
        assert clamp_page_index(1, 1) == 0
        assert clamp_page_index(-1, 1) == 0

    def test_large_negative_index(self):
        """Deve clampar índices muito negativos para 0."""
        result = clamp_page_index(-999, 10)
        assert result == 0

    def test_large_index_overflow(self):
        """Deve clampar índices muito grandes para total_pages-1."""
        result = clamp_page_index(999, 10)
        assert result == 9


class TestGetNextPageIndex:
    """Testes para obter índice da próxima página."""

    def test_next_from_middle_page(self):
        """Deve retornar próxima página quando no meio do documento."""
        result = get_next_page_index(3, 10)
        assert result == 4

    def test_next_from_first_page(self):
        """Deve ir para segunda página quando na primeira."""
        result = get_next_page_index(0, 10)
        assert result == 1

    def test_next_from_last_page(self):
        """Deve permanecer na última página quando já estiver nela."""
        result = get_next_page_index(9, 10)
        assert result == 9

    def test_next_from_penultimate_page(self):
        """Deve ir para última página quando na penúltima."""
        result = get_next_page_index(8, 10)
        assert result == 9

    def test_next_with_zero_pages(self):
        """Deve retornar 0 quando total_pages = 0."""
        result = get_next_page_index(0, 0)
        assert result == 0

    def test_next_with_negative_current(self):
        """Deve clampar índice negativo e ir para próxima."""
        result = get_next_page_index(-5, 10)
        # -5 + 1 = -4, clamp -> 0
        assert result == 0

    def test_next_with_single_page(self):
        """Deve permanecer em 0 com documento de 1 página."""
        result = get_next_page_index(0, 1)
        assert result == 0

    def test_next_beyond_last_page(self):
        """Deve clampar quando current_index já excede total_pages."""
        result = get_next_page_index(15, 10)
        # 15 + 1 = 16, clamp -> 9
        assert result == 9


class TestGetPrevPageIndex:
    """Testes para obter índice da página anterior."""

    def test_prev_from_middle_page(self):
        """Deve retornar página anterior quando no meio do documento."""
        result = get_prev_page_index(5, 10)
        assert result == 4

    def test_prev_from_last_page(self):
        """Deve ir para penúltima página quando na última."""
        result = get_prev_page_index(9, 10)
        assert result == 8

    def test_prev_from_first_page(self):
        """Deve permanecer na primeira página quando já estiver nela."""
        result = get_prev_page_index(0, 10)
        assert result == 0

    def test_prev_from_second_page(self):
        """Deve ir para primeira página quando na segunda."""
        result = get_prev_page_index(1, 10)
        assert result == 0

    def test_prev_with_zero_pages(self):
        """Deve retornar 0 quando total_pages = 0."""
        result = get_prev_page_index(3, 0)
        assert result == 0

    def test_prev_with_negative_current(self):
        """Deve clampar índice negativo e permanecer em 0."""
        result = get_prev_page_index(-3, 10)
        # -3 - 1 = -4, clamp -> 0
        assert result == 0

    def test_prev_with_single_page(self):
        """Deve permanecer em 0 com documento de 1 página."""
        result = get_prev_page_index(0, 1)
        assert result == 0

    def test_prev_from_large_index(self):
        """Deve clampar quando current_index excede total_pages."""
        result = get_prev_page_index(15, 10)
        # 15 - 1 = 14, clamp -> 9
        assert result == 9


class TestGetFirstPageIndex:
    """Testes para obter índice da primeira página."""

    def test_first_page_normal_document(self):
        """Deve retornar 0 para documento com múltiplas páginas."""
        result = get_first_page_index(10)
        assert result == 0

    def test_first_page_single_page(self):
        """Deve retornar 0 para documento de 1 página."""
        result = get_first_page_index(1)
        assert result == 0

    def test_first_page_zero_pages(self):
        """Deve retornar 0 quando total_pages = 0."""
        result = get_first_page_index(0)
        assert result == 0

    def test_first_page_negative_pages(self):
        """Deve retornar 0 quando total_pages negativo."""
        result = get_first_page_index(-5)
        assert result == 0

    def test_first_page_large_document(self):
        """Deve retornar 0 para documentos grandes."""
        result = get_first_page_index(1000)
        assert result == 0


class TestGetLastPageIndex:
    """Testes para obter índice da última página."""

    def test_last_page_normal_document(self):
        """Deve retornar total_pages-1 para documento com múltiplas páginas."""
        result = get_last_page_index(10)
        assert result == 9

    def test_last_page_single_page(self):
        """Deve retornar 0 para documento de 1 página."""
        result = get_last_page_index(1)
        assert result == 0

    def test_last_page_zero_pages(self):
        """Deve retornar 0 quando total_pages = 0."""
        result = get_last_page_index(0)
        assert result == 0

    def test_last_page_negative_pages(self):
        """Deve retornar 0 quando total_pages negativo."""
        result = get_last_page_index(-3)
        assert result == 0

    def test_last_page_large_document(self):
        """Deve retornar total_pages-1 para documentos grandes."""
        result = get_last_page_index(1000)
        assert result == 999

    def test_last_page_two_pages(self):
        """Deve retornar 1 para documento de 2 páginas."""
        result = get_last_page_index(2)
        assert result == 1


# Testes de integração


class TestNavigationWorkflows:
    """Testes de workflows completos de navegação."""

    def test_sequential_next_navigation(self):
        """Simula navegação sequencial para frente."""
        total_pages = 5
        current = get_first_page_index(total_pages)
        assert current == 0

        # Next 4x
        current = get_next_page_index(current, total_pages)
        assert current == 1
        current = get_next_page_index(current, total_pages)
        assert current == 2
        current = get_next_page_index(current, total_pages)
        assert current == 3
        current = get_next_page_index(current, total_pages)
        assert current == 4

        # Tentativa de ir além (deve permanecer em 4)
        current = get_next_page_index(current, total_pages)
        assert current == 4

    def test_sequential_prev_navigation(self):
        """Simula navegação sequencial para trás."""
        total_pages = 5
        current = get_last_page_index(total_pages)
        assert current == 4

        # Prev 4x
        current = get_prev_page_index(current, total_pages)
        assert current == 3
        current = get_prev_page_index(current, total_pages)
        assert current == 2
        current = get_prev_page_index(current, total_pages)
        assert current == 1
        current = get_prev_page_index(current, total_pages)
        assert current == 0

        # Tentativa de ir antes (deve permanecer em 0)
        current = get_prev_page_index(current, total_pages)
        assert current == 0

    def test_jump_to_ends_workflow(self):
        """Simula saltos entre primeira e última página."""
        total_pages = 10

        # Começa no meio
        current = 5

        # Jump to first
        current = get_first_page_index(total_pages)
        assert current == 0

        # Jump to last
        current = get_last_page_index(total_pages)
        assert current == 9

        # Jump to first again
        current = get_first_page_index(total_pages)
        assert current == 0

    def test_mixed_navigation_workflow(self):
        """Simula navegação mista (next/prev/jump)."""
        total_pages = 10

        # Start -> Next -> Next -> Prev -> End -> Home
        current = get_first_page_index(total_pages)
        assert current == 0

        current = get_next_page_index(current, total_pages)
        assert current == 1

        current = get_next_page_index(current, total_pages)
        assert current == 2

        current = get_prev_page_index(current, total_pages)
        assert current == 1

        current = get_last_page_index(total_pages)
        assert current == 9

        current = get_first_page_index(total_pages)
        assert current == 0

    def test_clamp_navigation_workflow(self):
        """Simula navegação com índices inválidos que precisam de clamp."""
        total_pages = 5

        # Índice negativo clamped
        current = clamp_page_index(-10, total_pages)
        assert current == 0

        # Next a partir de clamped
        current = get_next_page_index(current, total_pages)
        assert current == 1

        # Índice muito grande clamped
        current = clamp_page_index(100, total_pages)
        assert current == 4

        # Prev a partir de clamped
        current = get_prev_page_index(current, total_pages)
        assert current == 3

    def test_single_page_document_workflow(self):
        """Simula navegação em documento de página única."""
        total_pages = 1

        current = get_first_page_index(total_pages)
        assert current == 0

        # Tentativa de next (deve permanecer)
        current = get_next_page_index(current, total_pages)
        assert current == 0

        # Tentativa de prev (deve permanecer)
        current = get_prev_page_index(current, total_pages)
        assert current == 0

        # Last também deve ser 0
        current = get_last_page_index(total_pages)
        assert current == 0

    def test_empty_document_workflow(self):
        """Simula navegação em documento vazio (0 páginas)."""
        total_pages = 0

        # Todas as operações devem retornar 0
        assert get_first_page_index(total_pages) == 0
        assert get_last_page_index(total_pages) == 0
        assert get_next_page_index(0, total_pages) == 0
        assert get_prev_page_index(0, total_pages) == 0
        assert clamp_page_index(5, total_pages) == 0

    def test_boundary_navigation_workflow(self):
        """Simula navegação nos limites (primeira/última página)."""
        total_pages = 10

        # Navegação na primeira página
        current = 0
        # Prev não deve ir abaixo de 0
        current = get_prev_page_index(current, total_pages)
        assert current == 0
        # Next deve ir para 1
        current = get_next_page_index(current, total_pages)
        assert current == 1

        # Navegação na última página
        current = 9
        # Next não deve ir além de 9
        current = get_next_page_index(current, total_pages)
        assert current == 9
        # Prev deve ir para 8
        current = get_prev_page_index(current, total_pages)
        assert current == 8


class TestNavigationEdgeCases:
    """Testes de casos extremos de navegação."""

    def test_all_functions_consistent_with_zero_pages(self):
        """Garante que todas as funções retornam 0 para total_pages=0."""
        total_pages = 0
        assert clamp_page_index(0, total_pages) == 0
        assert clamp_page_index(5, total_pages) == 0
        assert clamp_page_index(-5, total_pages) == 0
        assert get_next_page_index(0, total_pages) == 0
        assert get_prev_page_index(0, total_pages) == 0
        assert get_first_page_index(total_pages) == 0
        assert get_last_page_index(total_pages) == 0

    def test_all_functions_consistent_with_single_page(self):
        """Garante comportamento consistente para documento de 1 página."""
        total_pages = 1
        assert clamp_page_index(0, total_pages) == 0
        assert clamp_page_index(1, total_pages) == 0
        assert get_next_page_index(0, total_pages) == 0
        assert get_prev_page_index(0, total_pages) == 0
        assert get_first_page_index(total_pages) == 0
        assert get_last_page_index(total_pages) == 0

    def test_negative_total_pages_handling(self):
        """Garante que total_pages negativo é tratado como 0."""
        total_pages = -10
        assert clamp_page_index(5, total_pages) == 0
        assert get_next_page_index(3, total_pages) == 0
        assert get_prev_page_index(3, total_pages) == 0
        assert get_first_page_index(total_pages) == 0
        assert get_last_page_index(total_pages) == 0

    def test_very_large_document(self):
        """Testa navegação em documentos muito grandes."""
        total_pages = 10000

        assert get_first_page_index(total_pages) == 0
        assert get_last_page_index(total_pages) == 9999
        assert get_next_page_index(5000, total_pages) == 5001
        assert get_prev_page_index(5000, total_pages) == 4999
        assert clamp_page_index(15000, total_pages) == 9999
        assert clamp_page_index(-100, total_pages) == 0
