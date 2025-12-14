"""Testes unitários para src.ui.files_browser.constants.

Módulo testado: constantes e configurações do File Browser.
Cobertura esperada: 100% (apenas constantes, sem lógica).
"""

from src.ui.files_browser.constants import (
    UI_GAP,
    UI_PADX,
    UI_PADY,
    FOLDER_STATUS_NEUTRAL,
    FOLDER_STATUS_READY,
    FOLDER_STATUS_NOTREADY,
    STATUS_GLYPHS,
    PLACEHOLDER_TAG,
    EMPTY_TAG,
    DEFAULT_PAGE_SIZE,
)


class TestUIConstants:
    """Testes de constantes de UI."""

    def test_ui_gap_is_positive_integer(self):
        """UI_GAP é inteiro positivo."""
        assert isinstance(UI_GAP, int)
        assert UI_GAP > 0
        assert UI_GAP == 6

    def test_ui_padx_is_positive_integer(self):
        """UI_PADX é inteiro positivo."""
        assert isinstance(UI_PADX, int)
        assert UI_PADX > 0
        assert UI_PADX == 8

    def test_ui_pady_is_positive_integer(self):
        """UI_PADY é inteiro positivo."""
        assert isinstance(UI_PADY, int)
        assert UI_PADY > 0
        assert UI_PADY == 6


class TestFolderStatus:
    """Testes de constantes de status de pastas."""

    def test_folder_status_values_are_strings(self):
        """Status de pastas são strings."""
        assert isinstance(FOLDER_STATUS_NEUTRAL, str)
        assert isinstance(FOLDER_STATUS_READY, str)
        assert isinstance(FOLDER_STATUS_NOTREADY, str)

    def test_folder_status_values(self):
        """Valores específicos dos status."""
        assert FOLDER_STATUS_NEUTRAL == "neutral"
        assert FOLDER_STATUS_READY == "ready"
        assert FOLDER_STATUS_NOTREADY == "notready"

    def test_folder_status_values_are_unique(self):
        """Cada status tem valor único."""
        statuses = {FOLDER_STATUS_NEUTRAL, FOLDER_STATUS_READY, FOLDER_STATUS_NOTREADY}
        assert len(statuses) == 3


class TestStatusGlyphs:
    """Testes de mapeamento de status para glyphs."""

    def test_status_glyphs_is_dict(self):
        """STATUS_GLYPHS é dicionário."""
        assert isinstance(STATUS_GLYPHS, dict)

    def test_status_glyphs_has_all_statuses(self):
        """STATUS_GLYPHS tem entrada para cada status."""
        assert FOLDER_STATUS_NEUTRAL in STATUS_GLYPHS
        assert FOLDER_STATUS_READY in STATUS_GLYPHS
        assert FOLDER_STATUS_NOTREADY in STATUS_GLYPHS

    def test_status_glyphs_values(self):
        """Glyphs têm valores específicos."""
        assert STATUS_GLYPHS[FOLDER_STATUS_NEUTRAL] == "•"
        assert STATUS_GLYPHS[FOLDER_STATUS_READY] == "✓"
        assert STATUS_GLYPHS[FOLDER_STATUS_NOTREADY] == "✗"

    def test_status_glyphs_values_are_strings(self):
        """Todos os glyphs são strings."""
        for glyph in STATUS_GLYPHS.values():
            assert isinstance(glyph, str)
            assert len(glyph) > 0

    def test_status_glyphs_count(self):
        """STATUS_GLYPHS tem exatamente 3 entradas."""
        assert len(STATUS_GLYPHS) == 3


class TestTreeviewTags:
    """Testes de tags da Treeview."""

    def test_placeholder_tag_is_string(self):
        """PLACEHOLDER_TAG é string."""
        assert isinstance(PLACEHOLDER_TAG, str)
        assert len(PLACEHOLDER_TAG) > 0

    def test_empty_tag_is_string(self):
        """EMPTY_TAG é string."""
        assert isinstance(EMPTY_TAG, str)
        assert len(EMPTY_TAG) > 0

    def test_placeholder_tag_value(self):
        """PLACEHOLDER_TAG tem valor específico."""
        assert PLACEHOLDER_TAG == "async-placeholder"

    def test_empty_tag_value(self):
        """EMPTY_TAG tem valor específico."""
        assert EMPTY_TAG == "async-empty"

    def test_tags_are_unique(self):
        """Tags são únicas."""
        assert PLACEHOLDER_TAG != EMPTY_TAG


class TestPaginationConstants:
    """Testes de constantes de paginação."""

    def test_default_page_size_is_positive_integer(self):
        """DEFAULT_PAGE_SIZE é inteiro positivo."""
        assert isinstance(DEFAULT_PAGE_SIZE, int)
        assert DEFAULT_PAGE_SIZE > 0

    def test_default_page_size_value(self):
        """DEFAULT_PAGE_SIZE tem valor específico."""
        assert DEFAULT_PAGE_SIZE == 200

    def test_default_page_size_is_reasonable(self):
        """DEFAULT_PAGE_SIZE está em range razoável."""
        assert 50 <= DEFAULT_PAGE_SIZE <= 1000


class TestConstantsIntegration:
    """Testes de integração entre constantes."""

    def test_all_imports_work(self):
        """Todas as constantes podem ser importadas."""
        # Reimporta para garantir
        from src.ui.files_browser import constants

        assert hasattr(constants, "UI_GAP")
        assert hasattr(constants, "UI_PADX")
        assert hasattr(constants, "UI_PADY")
        assert hasattr(constants, "FOLDER_STATUS_NEUTRAL")
        assert hasattr(constants, "FOLDER_STATUS_READY")
        assert hasattr(constants, "FOLDER_STATUS_NOTREADY")
        assert hasattr(constants, "STATUS_GLYPHS")
        assert hasattr(constants, "PLACEHOLDER_TAG")
        assert hasattr(constants, "EMPTY_TAG")
        assert hasattr(constants, "DEFAULT_PAGE_SIZE")

    def test_ui_spacing_coherence(self):
        """Valores de spacing são coerentes entre si."""
        # PAD geralmente >= GAP
        assert UI_PADX >= UI_GAP or UI_PADX >= 0
        assert UI_PADY >= 0
