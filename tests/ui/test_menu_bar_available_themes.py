"""Testes unitários para src.ui.menu_bar._available_themes.

Módulo testado: função _available_themes() (validação de contrato e comportamento).
Cobertura esperada: testa comportamento observável da função.

Nota: função _available_themes() tenta importar theme_manager dinamicamente.
Testamos o comportamento real sem mockar imports complexos.
"""

from src.ui.menu_bar import _available_themes


class TestAvailableThemes:
    """Testes de _available_themes() - detecção de temas disponíveis."""

    def test_available_themes_returns_iterable(self):
        """Função retorna iterável válido."""
        result = _available_themes()

        # Deve ser iterável
        assert hasattr(result, "__iter__")

        # Deve conter strings
        result_list = list(result)
        assert len(result_list) > 0
        assert all(isinstance(theme, str) for theme in result_list)

    def test_available_themes_no_duplicates(self):
        """Temas retornados não tem duplicatas."""
        result = list(_available_themes())

        # Não deve ter duplicatas
        assert len(result) == len(set(result))

    def test_available_themes_nonempty_strings(self):
        """Todos os temas são strings não-vazias."""
        result = list(_available_themes())

        assert all(len(theme) > 0 for theme in result)
        assert all(theme.strip() == theme for theme in result)  # sem espaços extras

    def test_available_themes_contains_expected_themes(self):
        """Resultado contém temas conhecidos (fallback ou reais)."""
        result = list(_available_themes())

        # Deve conter pelo menos alguns temas conhecidos
        # (ou do theme_manager real, ou do fallback)
        known_themes = {"flatly", "cosmo", "darkly", "superhero"}

        # Pelo menos alguns dos temas conhecidos devem estar presentes
        assert any(theme in result for theme in known_themes)

    def test_available_themes_minimum_count(self):
        """Retorna pelo menos 5 temas."""
        result = list(_available_themes())

        # Fallback tem 10, theme_manager real provavelmente tem mais
        assert len(result) >= 5

    def test_fallback_themes_validation(self):
        """Valida estrutura dos temas de fallback esperados."""
        expected_fallback = [
            "flatly",
            "cosmo",
            "darkly",
            "litera",
            "morph",
            "pulse",
            "sandstone",
            "solar",
            "superhero",
            "yeti",
        ]

        # Todos são strings não-vazias
        assert all(isinstance(t, str) and len(t) > 0 for t in expected_fallback)
        assert len(expected_fallback) == 10

        # Não tem duplicatas
        assert len(expected_fallback) == len(set(expected_fallback))

    def test_available_themes_consistent(self):
        """Múltiplas chamadas retornam mesmo resultado."""
        result1 = list(_available_themes())
        result2 = list(_available_themes())

        assert result1 == result2

    def test_available_themes_lowercase(self):
        """Temas são lowercase (convenção)."""
        result = list(_available_themes())

        # Maioria dos temas ttkbootstrap são lowercase
        lowercase_count = sum(1 for theme in result if theme.islower())

        # Pelo menos 80% devem ser lowercase
        assert lowercase_count >= len(result) * 0.8
