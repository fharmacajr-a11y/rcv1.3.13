"""Testes de cobertura parcial para main_window.py - ZUI-TEST-001.

Esta suite complementa a cobertura com testes de código público e paths não cobertos.
Não tenta criar instâncias Tk devido à complexidade.
"""

from __future__ import annotations


def test_import_app_class():
    """Testa que conseguimos importar a classe App."""
    from src.modules.main_window.views.main_window import App

    assert App is not None
    assert hasattr(App, "show_hub_screen")
    assert hasattr(App, "show_main_screen")
    assert hasattr(App, "novo_cliente")


def test_app_methods_exist():
    """Testa que App tem todos os métodos públicos esperados."""
    from src.modules.main_window.views.main_window import App

    # Navegação
    assert callable(getattr(App, "show_hub_screen", None))
    assert callable(getattr(App, "show_main_screen", None))
    assert callable(getattr(App, "show_passwords_screen", None))
    assert callable(getattr(App, "show_cashflow_screen", None))
    assert callable(getattr(App, "show_placeholder_screen", None))

    # Ações
    assert callable(getattr(App, "novo_cliente", None))
    assert callable(getattr(App, "editar_cliente", None))
    assert callable(getattr(App, "ver_subpastas", None))
    assert callable(getattr(App, "abrir_lixeira", None))
    assert callable(getattr(App, "enviar_para_supabase", None))

    # Cache
    assert callable(getattr(App, "_get_user_cached", None))
    assert callable(getattr(App, "_get_role_cached", None))
    assert callable(getattr(App, "_get_org_id_cached", None))


def test_constants_exist():
    """Testa que as constantes do módulo existem."""
    from src.modules.main_window.views import constants

    assert hasattr(constants, "APP_TITLE")
    assert hasattr(constants, "APP_VERSION")
    assert hasattr(constants, "APP_ICON_PATH")


def test_app_navegacao_metodos_delegacao():
    """Testa que métodos de navegação delegam corretamente (via inspect)."""
    from src.modules.main_window.views.main_window import App
    import inspect

    # Verificar código-fonte dos métodos de navegação
    source_hub = inspect.getsource(App.show_hub_screen)
    source_main = inspect.getsource(App.show_main_screen)

    # Devem chamar navigate_to ou nav.show_*
    assert "navigate_to" in source_hub or "nav.show_" in source_hub
    assert "navigate_to" in source_main or "nav.show_" in source_main


def test_app_acoes_metodos_delegacao():
    """Testa que métodos de ações delegam para AppActions (via inspect)."""
    from src.modules.main_window.views.main_window import App
    import inspect

    source_novo = inspect.getsource(App.novo_cliente)
    source_editar = inspect.getsource(App.editar_cliente)

    # Devem chamar self._actions.*
    assert "_actions" in source_novo
    assert "_actions" in source_editar


def test_app_cache_metodos_usam_session():
    """Testa que métodos de cache usam session_cache (via inspect)."""
    from src.modules.main_window.views.main_window import App
    import inspect

    source_user = inspect.getsource(App._get_user_cached)

    # Deve usar self._session ou self.session_cache
    assert "_session" in source_user or "session_cache" in source_user
