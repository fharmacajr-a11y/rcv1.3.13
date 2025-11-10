"""
Teste de compatibilidade do alias HTTPX_TIMEOUT.
Garante que código legado continua funcionando após refatoração.
"""


def test_httpx_timeout_alias_import():
    """
    Verifica que HTTPX_TIMEOUT existe e aponta para HTTPX_TIMEOUT_LIGHT.
    Compatibilidade retroativa após introdução de LIGHT/HEAVY variants.
    """
    from infra.supabase.http_client import HTTPX_TIMEOUT, HTTPX_TIMEOUT_LIGHT
    
    # Deve existir e ser o mesmo objeto (alias, não cópia)
    assert HTTPX_TIMEOUT is HTTPX_TIMEOUT_LIGHT, \
        "HTTPX_TIMEOUT deve ser alias de HTTPX_TIMEOUT_LIGHT"


def test_httpx_timeout_alias_config():
    """
    Verifica configuração do timeout (30s read/write).
    """
    from infra.supabase.http_client import HTTPX_TIMEOUT
    
    assert HTTPX_TIMEOUT.connect == 10.0
    assert HTTPX_TIMEOUT.read == 30.0
    assert HTTPX_TIMEOUT.write == 30.0
    assert HTTPX_TIMEOUT.pool is None


def test_httpx_all_exports():
    """
    Verifica que __all__ exporta os 3 timeout variants.
    """
    from infra.supabase import http_client
    
    assert "HTTPX_TIMEOUT" in http_client.__all__
    assert "HTTPX_TIMEOUT_LIGHT" in http_client.__all__
    assert "HTTPX_TIMEOUT_HEAVY" in http_client.__all__
