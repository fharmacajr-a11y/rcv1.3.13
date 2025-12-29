def test_clientes_views_modules_import_smoke():
    # Se algum import estiver errado, este teste quebra com ImportError
    import src.modules.clientes.views.main_screen_dataflow as _mod  # noqa: F401
