"""
Testes para config/paths.py - CLOUD_ONLY flag
"""

import sys


def test_cloud_only_true(monkeypatch):
    """RC_NO_LOCAL_FS=1 deve ativar CLOUD_ONLY"""
    monkeypatch.setenv("RC_NO_LOCAL_FS", "1")

    # Remove do cache se já foi importado
    if "config.paths" in sys.modules:
        del sys.modules["config.paths"]

    import config.paths as paths

    assert paths.CLOUD_ONLY is True


def test_cloud_only_false(monkeypatch):
    """RC_NO_LOCAL_FS=0 deve desativar CLOUD_ONLY"""
    monkeypatch.setenv("RC_NO_LOCAL_FS", "0")

    # Remove do cache se já foi importado
    if "config.paths" in sys.modules:
        del sys.modules["config.paths"]

    import config.paths as paths

    assert paths.CLOUD_ONLY is False


def test_cloud_only_default(monkeypatch):
    """Sem RC_NO_LOCAL_FS explícito, verifica comportamento padrão"""
    # O valor padrão depende da configuração atual do ambiente
    # Este teste apenas verifica que CLOUD_ONLY é um booleano válido
    monkeypatch.delenv("RC_NO_LOCAL_FS", raising=False)

    # Remove do cache se já foi importado
    if "config.paths" in sys.modules:
        del sys.modules["config.paths"]

    import config.paths as paths

    # Verifica que é um booleano (True ou False são válidos)
    assert isinstance(paths.CLOUD_ONLY, bool)
