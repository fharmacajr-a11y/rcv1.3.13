import httpx
from httpx import Timeout

# Timeout para operações leves (health, auth, RPC simples)
HTTPX_TIMEOUT_LIGHT = Timeout(connect=10.0, read=30.0, write=30.0, pool=None)

# Timeout para operações pesadas (upload/download de arquivos)
HTTPX_TIMEOUT_HEAVY = Timeout(connect=10.0, read=60.0, write=60.0, pool=None)

# Cliente padrão usa timeout leve (a maioria das operações)
HTTPX_CLIENT = httpx.Client(
    http2=False,  # manter compat com PR-H1
    timeout=HTTPX_TIMEOUT_LIGHT,
)
