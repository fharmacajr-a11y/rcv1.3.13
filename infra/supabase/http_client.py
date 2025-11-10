import httpx
from httpx import Timeout

# Timeout para operações leves (health, auth, RPC simples)
HTTPX_TIMEOUT_LIGHT = Timeout(connect=10.0, read=30.0, write=30.0, pool=None)

# Timeout para operações pesadas (upload/download de arquivos)
HTTPX_TIMEOUT_HEAVY = Timeout(connect=10.0, read=60.0, write=60.0, pool=None)

# --- Compatibilidade: alias para código legado ---
# Mantém o nome antigo apontando para LIGHT (semântica original)
HTTPX_TIMEOUT = HTTPX_TIMEOUT_LIGHT

# Cliente padrão usa timeout leve (a maioria das operações)
HTTPX_CLIENT = httpx.Client(
    http2=False,  # manter compat com PR-H1
    timeout=HTTPX_TIMEOUT_LIGHT,
)

# Exportação pública explícita
__all__ = [
    "HTTPX_CLIENT",
    "HTTPX_TIMEOUT",        # alias compatível (legado)
    "HTTPX_TIMEOUT_LIGHT",  # novo (30s)
    "HTTPX_TIMEOUT_HEAVY",  # novo (60s)
    "Timeout",
]
