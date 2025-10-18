"""
Smoke test - Verificação de import do entrypoint
"""


def test_import_app_gui():
    """app_gui deve importar sem erros"""
    import app_gui  # noqa: F401

    # Import bem-sucedido é suficiente
    assert True


def test_import_app_core():
    """app_core deve importar sem erros"""
    import app_core  # noqa: F401

    assert True


def test_import_gui_main_window():
    """gui.main_window deve importar sem erros"""
    from gui.main_window import App  # noqa: F401

    assert True
