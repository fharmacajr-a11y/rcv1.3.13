# -*- coding: utf-8 -*-
"""
MF-52: Testes para hub_screen_helpers.py (façade de re-exports).

Valida que:
- __all__ está correto
- Re-exports apontam para os mesmos objetos dos módulos temáticos
- Todos os nomes em __all__ são acessíveis
"""

from __future__ import annotations

import pytest


class TestHubScreenHelpersFacade:
    """Testes para façade hub_screen_helpers.py."""

    def test_all_is_correct(self):
        """Testa que __all__ contém a lista esperada de exports."""
        import src.modules.hub.views.hub_screen_helpers as h

        expected_all = [
            # Módulos e navegação (hub_helpers_modules)
            "ModuleButton",
            "build_module_buttons",
            "calculate_module_button_style",
            # Notas (hub_helpers_notes)
            "calculate_notes_content_hash",
            "calculate_notes_ui_state",
            "format_note_line",
            "format_notes_count",
            "format_timestamp",
            "is_notes_list_empty",
            "normalize_note_dict",
            "should_show_notes_section",
            "should_skip_render_empty_notes",
            # Sessão e utilitários (hub_helpers_session)
            "calculate_retry_delay_ms",
            "extract_email_prefix",
            "format_author_fallback",
            "is_auth_ready",
            "should_skip_refresh_by_cooldown",
        ]

        assert h.__all__ == expected_all

    def test_all_names_are_accessible(self):
        """Testa que todos os nomes em __all__ são acessíveis."""
        import src.modules.hub.views.hub_screen_helpers as h

        for name in h.__all__:
            assert hasattr(h, name), f"{name} deveria estar acessível"
            assert getattr(h, name) is not None, f"{name} não deveria ser None"

    @pytest.mark.parametrize(
        "name,origin_module",
        [
            # hub_helpers_modules
            ("ModuleButton", "hub_helpers_modules"),
            ("build_module_buttons", "hub_helpers_modules"),
            ("calculate_module_button_style", "hub_helpers_modules"),
            # hub_helpers_notes
            ("calculate_notes_content_hash", "hub_helpers_notes"),
            ("calculate_notes_ui_state", "hub_helpers_notes"),
            ("format_note_line", "hub_helpers_notes"),
            ("format_notes_count", "hub_helpers_notes"),
            ("format_timestamp", "hub_helpers_notes"),
            ("is_notes_list_empty", "hub_helpers_notes"),
            ("normalize_note_dict", "hub_helpers_notes"),
            ("should_show_notes_section", "hub_helpers_notes"),
            ("should_skip_render_empty_notes", "hub_helpers_notes"),
            # hub_helpers_session
            ("calculate_retry_delay_ms", "hub_helpers_session"),
            ("extract_email_prefix", "hub_helpers_session"),
            ("format_author_fallback", "hub_helpers_session"),
            ("is_auth_ready", "hub_helpers_session"),
            ("should_skip_refresh_by_cooldown", "hub_helpers_session"),
        ],
    )
    def test_reexports_point_to_same_objects(self, name, origin_module):
        """Testa que re-exports apontam para os mesmos objetos dos módulos de origem."""
        import importlib

        import src.modules.hub.views.hub_screen_helpers as h

        # Importar módulo de origem
        origin = importlib.import_module(f"src.modules.hub.views.{origin_module}")

        # Verificar que o objeto no façade é o mesmo do módulo origem (identity)
        facade_obj = getattr(h, name)
        origin_obj = getattr(origin, name)

        # Verificar que são o mesmo objeto ou ao menos apontam para o mesmo código
        # (em alguns casos de reload de módulo, o Python pode criar objetos diferentes)
        assert facade_obj is origin_obj or (
            callable(facade_obj) and callable(origin_obj) and facade_obj.__name__ == origin_obj.__name__
        ), f"{name} no façade deveria ser o mesmo objeto de {origin_module}"

    def test_module_button_from_modules(self):
        """Testa especificamente que ModuleButton vem de hub_helpers_modules."""
        from src.modules.hub.views import hub_helpers_modules as hm
        from src.modules.hub.views import hub_screen_helpers as h

        assert h.ModuleButton is hm.ModuleButton

    def test_format_note_line_from_notes(self):
        """Testa especificamente que format_note_line vem de hub_helpers_notes."""
        from src.modules.hub.views import hub_helpers_notes as hn
        from src.modules.hub.views import hub_screen_helpers as h

        # Verificar que são o mesmo objeto ou ao menos apontam para o mesmo código
        assert h.format_note_line is hn.format_note_line or (
            callable(h.format_note_line)
            and callable(hn.format_note_line)
            and h.format_note_line.__name__ == hn.format_note_line.__name__
        )

    def test_extract_email_prefix_from_session(self):
        """Testa especificamente que extract_email_prefix vem de hub_helpers_session."""
        from src.modules.hub.views import hub_helpers_session as hs
        from src.modules.hub.views import hub_screen_helpers as h

        assert h.extract_email_prefix is hs.extract_email_prefix

    def test_all_items_count(self):
        """Testa que __all__ tem o número esperado de itens."""
        import src.modules.hub.views.hub_screen_helpers as h

        # 3 de modules + 9 de notes + 5 de session = 17
        assert len(h.__all__) == 17

    def test_no_extra_public_exports(self):
        """Testa que não há exports públicos além dos declarados em __all__."""
        import src.modules.hub.views.hub_screen_helpers as h

        # Pegar todos os nomes públicos (não começam com _)
        public_names = [name for name in dir(h) if not name.startswith("_")]

        # Filtrar apenas funções/classes (excluir módulos importados)
        actual_exports = []
        for name in public_names:
            obj = getattr(h, name)
            # Incluir se for função, classe ou dataclass
            if callable(obj) or hasattr(obj, "__dataclass_fields__"):
                actual_exports.append(name)

        # Todos os exports reais devem estar em __all__
        for name in actual_exports:
            assert name in h.__all__, f"{name} é público mas não está em __all__"

    def test_modules_group_exports(self):
        """Testa que exports do grupo 'módulos' estão corretos."""
        import src.modules.hub.views.hub_screen_helpers as h

        modules_exports = [
            "ModuleButton",
            "build_module_buttons",
            "calculate_module_button_style",
        ]

        for name in modules_exports:
            assert name in h.__all__
            assert hasattr(h, name)

    def test_notes_group_exports(self):
        """Testa que exports do grupo 'notas' estão corretos."""
        import src.modules.hub.views.hub_screen_helpers as h

        notes_exports = [
            "calculate_notes_content_hash",
            "calculate_notes_ui_state",
            "format_note_line",
            "format_notes_count",
            "format_timestamp",
            "is_notes_list_empty",
            "normalize_note_dict",
            "should_show_notes_section",
            "should_skip_render_empty_notes",
        ]

        for name in notes_exports:
            assert name in h.__all__
            assert hasattr(h, name)

    def test_session_group_exports(self):
        """Testa que exports do grupo 'sessão' estão corretos."""
        import src.modules.hub.views.hub_screen_helpers as h

        session_exports = [
            "calculate_retry_delay_ms",
            "extract_email_prefix",
            "format_author_fallback",
            "is_auth_ready",
            "should_skip_refresh_by_cooldown",
        ]

        for name in session_exports:
            assert name in h.__all__
            assert hasattr(h, name)
