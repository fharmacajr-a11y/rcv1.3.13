# infra/net_status.py
from __future__ import annotations

import logging
import os
import socket
from enum import Enum

import httpx

log = logging.getLogger(__name__)


class Status(Enum):
    ONLINE = 1
    OFFLINE = 2
    LOCAL = 3


def _can_resolve(host: str) -> bool:
    try:
        socket.gethostbyname(host)
        return True
    except Exception as exc:
        log.debug("Falha ao resolver host %s", host, exc_info=exc)
        return False


def _pick_base(url_hint: str | None) -> str:
    if url_hint:
        u = url_hint.strip()
        if u and not u.startswith("http"):
            u = "https://" + u
        return u.rstrip("/")

    env_url = (os.getenv("SUPABASE_URL") or "").strip()
    if env_url:
        if not env_url.startswith("http"):
            env_url = "https://" + env_url
        return env_url.rstrip("/")

    try:
        from infra.supabase_client import supabase  # type: ignore

        for attr in ("_supabase_url", "supabase_url", "url"):
            if hasattr(supabase, attr):
                val = getattr(supabase, attr)
                if isinstance(val, str) and val:
                    if not val.startswith("http"):
                        val = "https://" + val
                    return val.rstrip("/")
    except Exception as exc:
        log.debug("Falha ao obter URL base do Supabase", exc_info=exc)

    # fallback leve para conectividade geral
    return "https://www.google.com/generate_204"


def _ok(code: int) -> bool:
    return code == 204 or 200 <= code < 400


def probe(url: str = "", timeout: float = 2.0) -> Status:
    base = _pick_base(url)

    # DNS rápido
    try:
        host = base.split("//", 1)[1].split("/", 1)[0]
        if not _can_resolve(host):
            return Status.OFFLINE
    except Exception as exc:
        log.debug("Falha ao resolver host de %s", base, exc_info=exc)

    headers_no_key = {"User-Agent": "rc-net-probe"}
    anon = (os.getenv("SUPABASE_ANON_KEY") or "").strip()
    headers_with_key = {"User-Agent": "rc-net-probe", "apikey": anon} if anon else headers_no_key

    # monta a lista de alvos conforme existência de apikey
    targets: list[tuple[str, dict[str, str]]] = []
    if "supabase.co" in base:
        if anon:
            # se tem anon key, já começa com ela (evita 401 no console)
            targets.append((f"{base}/auth/v1/health", headers_with_key))
            targets.append((f"{base}/rest/v1", headers_with_key))
        else:
            # sem anon key, tenta health sem chave (alguns projetos permitem)
            targets.append((f"{base}/auth/v1/health", headers_no_key))

    # fallback universal
    targets.append(("https://www.google.com/generate_204", headers_no_key))

    try:
        with httpx.Client(http2=True, timeout=timeout, verify=True, follow_redirects=True) as c:
            for u, h in targets:
                try:
                    r = c.get(u, headers=h)
                    if _ok(r.status_code):
                        return Status.ONLINE
                except Exception as exc:
                    log.debug("Falha ao consultar %s", u, exc_info=exc)
                    continue
    except Exception as exc:
        log.warning("Falha ao sondar conectividade", exc_info=exc)

    return Status.OFFLINE
