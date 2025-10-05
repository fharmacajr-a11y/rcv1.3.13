from enum import Enum
import requests

class Status(str, Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    LOCAL = "LOCAL"

def probe(url: str = "", timeout: int = 2) -> Status:
    """
    Se url não for fornecida → retorna LOCAL (não há teste).
    Se url for fornecida → faz um HEAD; se responder → ONLINE; senão → OFFLINE.
    """
    if not url:
        return Status.LOCAL
    try:
        r = requests.head(url, timeout=timeout)
        if 200 <= r.status_code < 500:
            # Considera online se o host responde (mesmo 404)
            return Status.ONLINE
        return Status.OFFLINE
    except Exception:
        return Status.OFFLINE
