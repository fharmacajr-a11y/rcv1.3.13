import httpx
from httpx import Timeout

HTTPX_TIMEOUT = Timeout(connect=10.0, read=60.0, write=60.0, pool=None)

HTTPX_CLIENT = httpx.Client(
    http2=False,  # manter compat com PR-H1
    timeout=HTTPX_TIMEOUT,
)
