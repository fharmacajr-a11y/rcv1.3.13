from inspect import signature
from importlib import import_module


def test_splash_signature_has_root_param():
    splash = import_module("src.ui.splash")
    func = getattr(splash, "show_splash", None)
    assert callable(func), "show_splash não encontrado"
    assert "root" in str(signature(func)), "show_splash deve aceitar parâmetro 'root'"
