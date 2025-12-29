# -*- coding: utf-8 -*-
"""Teste de regressão para lazy imports - garantir que importar mixins não puxa Supabase."""

import sys


def test_import_handlers_mixin_does_not_pull_supabase():
    """Importar _anvisa_handlers_mixin não deve carregar supabase, storage3, pyiceberg."""
    # Limpar módulos ANVISA do cache (simular import fresh)
    anvisa_modules = [k for k in sys.modules if k.startswith("src.modules.anvisa")]
    for mod in anvisa_modules:
        del sys.modules[mod]

    # Capturar módulos antes do import
    modules_before = set(sys.modules.keys())

    # Importar mixin
    from src.modules.anvisa.views import _anvisa_handlers_mixin  # noqa: F401

    # Capturar módulos depois do import
    modules_after = set(sys.modules.keys())
    new_modules = modules_after - modules_before

    # Validar: Supabase/PyIceberg/Pydantic NÃO foram carregados
    heavy_deps = {"supabase", "storage3", "pyiceberg", "pydantic"}
    loaded_heavy = {mod for mod in new_modules if any(dep in mod for dep in heavy_deps)}

    assert not loaded_heavy, f"Heavy dependencies foram carregados: {loaded_heavy}"


def test_import_history_popup_mixin_does_not_pull_supabase():
    """Importar _anvisa_history_popup_mixin não deve carregar supabase, storage3, pyiceberg."""
    # Limpar módulos ANVISA do cache
    anvisa_modules = [k for k in sys.modules if k.startswith("src.modules.anvisa")]
    for mod in anvisa_modules:
        del sys.modules[mod]

    modules_before = set(sys.modules.keys())

    from src.modules.anvisa.views import _anvisa_history_popup_mixin  # noqa: F401

    modules_after = set(sys.modules.keys())
    new_modules = modules_after - modules_before

    heavy_deps = {"supabase", "storage3", "pyiceberg", "pydantic"}
    loaded_heavy = {mod for mod in new_modules if any(dep in mod for dep in heavy_deps)}

    assert not loaded_heavy, f"Heavy dependencies foram carregados: {loaded_heavy}"


def test_anvisa_screen_lazy_import_still_works():
    """from src.modules.anvisa import AnvisaScreen deve funcionar com lazy import."""
    # Limpar cache
    anvisa_modules = [k for k in sys.modules if k.startswith("src.modules.anvisa")]
    for mod in anvisa_modules:
        del sys.modules[mod]

    # Importar via lazy import
    from src.modules.anvisa import AnvisaScreen

    # Validar que é a classe correta
    assert AnvisaScreen.__name__ == "AnvisaScreen"
    assert "anvisa_screen" in AnvisaScreen.__module__


def test_views_dir_exposes_public_api():
    """dir(src.modules.anvisa.views) deve expor AnvisaScreen sem importar o módulo pesado."""
    # Limpar cache
    anvisa_modules = [k for k in sys.modules if k.startswith("src.modules.anvisa")]
    for mod in anvisa_modules:
        del sys.modules[mod]

    # Importar apenas o pacote views
    import src.modules.anvisa.views as m

    # Validar: __dir__ retorna AnvisaScreen
    assert "AnvisaScreen" in dir(m)

    # Validar: AnvisaScreen ainda NÃO foi importado (lazy)
    assert "src.modules.anvisa.views.anvisa_screen" not in sys.modules


def test_views_getattr_unknown_raises_attribute_error():
    """__getattr__ deve lançar AttributeError para atributos desconhecidos."""
    # Limpar cache
    anvisa_modules = [k for k in sys.modules if k.startswith("src.modules.anvisa")]
    for mod in anvisa_modules:
        del sys.modules[mod]

    import src.modules.anvisa.views as m

    # Tentar acessar atributo inexistente
    try:
        m.__getattr__("DoesNotExist")
        assert False, "Deveria ter lançado AttributeError"
    except AttributeError as e:
        # Validar mensagem de erro
        assert "DoesNotExist" in str(e)
