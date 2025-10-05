from __future__ import annotations

import os
import time
from typing import Optional, Any, cast

import requests
from urllib.parse import urlparse
import yaml

from .cache_store import JsonCacheStore

DEFAULT_CONFIG: dict[str, Any] = {
    "timeouts": {"connect_seconds": 3, "read_seconds": 5},
    "retries": {"attempts": 3, "backoff_seconds": [1, 2, 5]},
}


class Circuit:
    def __init__(self) -> None:
        self._fails = 0
        self._next_try = 0.0  # epoch seconds

    def allow(self) -> bool:
        return time.time() >= self._next_try

    def report(self, ok: bool) -> None:
        if ok:
            self._fails = 0
            self._next_try = 0.0
        else:
            self._fails += 1
            if self._fails >= 5:
                self._next_try = time.time() + 300  # 5 minutos


class HttpClient:
    def __init__(
        self,
        cache_store: Optional[JsonCacheStore] = None,
        config_path: str = "config.yml",
    ) -> None:
        self.cache: Optional[JsonCacheStore] = cache_store
        self.config: dict[str, Any] = DEFAULT_CONFIG.copy()

        # load config se existir
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    loaded = yaml.safe_load(f) or {}
                if isinstance(loaded, dict):
                    user_cfg: dict[str, Any] = cast(dict[str, Any], loaded)
                    # shallow-merge
                    for k, v in user_cfg.items():
                        self.config[k] = v
            except Exception:
                pass

        self.circuits: dict[str, Circuit] = {}

    def _circuit_for(self, url: str) -> Circuit:
        host = urlparse(url).netloc
        c = self.circuits.get(host)
        if c is None:
            c = Circuit()
            self.circuits[host] = c
        return c

    def _req(
        self,
        method: str,
        url: str,
        *,
        json: Any = None,
        params: dict[str, Any] | None = None,
        cache_key: str | None = None,
    ) -> dict[str, Any]:
        attempts = int(self.config.get("retries", {}).get("attempts", 3))
        backoffs: list[int] = self.config.get("retries", {}).get("backoff_seconds", [1, 2, 5])
        timeout_tuple = (
            self.config.get("timeouts", {}).get("connect_seconds", 3),
            self.config.get("timeouts", {}).get("read_seconds", 5),
        )

        circuit = self._circuit_for(url)
        last_exc: Exception | None = None

        if not circuit.allow():
            # Circuit fechado → tenta cache
            if cache_key and self.cache:
                cached = self.cache.get(cache_key)
                if cached is not None:
                    return {"data": cached, "from_cache": True}
            raise RuntimeError("Circuit breaker ativo; aguarde alguns minutos.")

        for i in range(attempts):
            try:
                r = requests.request(method, url, json=json, params=params, timeout=timeout_tuple)
                if 200 <= r.status_code < 300:
                    content_type = r.headers.get("Content-Type") or ""
                    data: Any = r.json() if "application/json" in content_type else r.text
                    circuit.report(ok=True)
                    if cache_key and self.cache:
                        self.cache.set(cache_key, data)
                    return {"data": data, "from_cache": False}
                else:
                    last_exc = RuntimeError(f"HTTP {r.status_code}")
            except Exception as e:
                last_exc = e

            # backoff progressivo
            time.sleep(backoffs[min(i, len(backoffs) - 1)])

        circuit.report(ok=False)

        # tenta cache
        if cache_key and self.cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return {"data": cached, "from_cache": True}

        # sem cache → propaga erro
        if last_exc:
            raise last_exc
        raise RuntimeError("Falha na requisição")

    def get(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        cache_key: str | None = None,
    ) -> dict[str, Any]:
        return self._req("GET", url, params=params, cache_key=cache_key)

    def post(
        self,
        url: str,
        *,
        json: Any = None,
        cache_key: str | None = None,
    ) -> dict[str, Any]:
        return self._req("POST", url, json=json, cache_key=cache_key)
