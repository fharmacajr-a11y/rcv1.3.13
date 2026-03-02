import time
import json
import os
import threading
from datetime import datetime, timedelta
from typing import Any


class JsonCacheStore:
    """
    Cache simples baseado em JSON com TTL.
    Salva um dicionário: { cache_key: { "timestamp": "...", "expire": <epoch>, "payload": ... } }
    """

    def __init__(self, file_path: str = "runtime/cache.json", ttl_hours: int = 24) -> None:
        self.file_path = file_path
        self.ttl = timedelta(hours=ttl_hours)
        self._lock = threading.Lock()
        dir_name = os.path.dirname(self.file_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        if not os.path.exists(self.file_path):
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump({}, f)

    # ------------------------------------------------------------------
    # I/O interno — sem lock, para ser chamado dentro de seções críticas
    # ------------------------------------------------------------------

    def _load_unlocked(self) -> dict:
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_unlocked(self, data: dict) -> None:
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # Wrappers públicos preservados para retrocompatibilidade interna
    def _load(self) -> dict:
        with self._lock:
            return self._load_unlocked()

    def _save(self, data: dict) -> None:
        with self._lock:
            self._save_unlocked(data)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_expire(self, item: dict) -> float | None:
        """
        Retorna o epoch de expiração de uma entrada.
        - Se 'expire' estiver presente, usa diretamente.
        - Para entradas legadas (sem 'expire'), computa timestamp + ttl.
        - Retorna None se não for possível determinar.
        """
        if "expire" in item:
            return float(item["expire"])
        ts_str = item.get("timestamp")
        if ts_str:
            try:
                ts_dt = datetime.fromisoformat(str(ts_str))
                return ts_dt.timestamp() + self.ttl.total_seconds()
            except Exception:
                pass
        return None

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def get(self, key: str) -> Any:
        """Retorna o payload cacheado ou None se expirado/inexistente."""
        now = time.time()
        with self._lock:
            data = self._load_unlocked()
            dirty = False

            # Remove entradas expiradas ou malformadas (limpeza geral)
            to_remove = []
            for k, v in data.items():
                if not isinstance(v, dict):
                    to_remove.append(k)
                    continue
                expire = self._resolve_expire(v)
                if expire is None or expire < now:
                    to_remove.append(k)

            for k in to_remove:
                data.pop(k, None)
                dirty = True

            item = data.get(key)
            if item is None:
                if dirty:
                    self._save_unlocked(data)
                return None

            # Migra entradas legadas: adiciona 'expire' ao arquivo
            if "expire" not in item:
                expire = self._resolve_expire(item)
                if expire is not None:
                    item["expire"] = expire
                    dirty = True

            if dirty:
                self._save_unlocked(data)

            return item.get("payload")

    def get_entry(self, key: str) -> dict | None:
        """Retorna a entrada completa {timestamp, expire, payload} para debug/uso interno."""
        now = time.time()
        with self._lock:
            data = self._load_unlocked()
        item = data.get(key)
        if not isinstance(item, dict):
            return None
        expire = self._resolve_expire(item)
        if expire is None or expire < now:
            return None
        return item

    def set(self, key: str, payload: Any) -> None:
        """Grava o payload com TTL. Operação atômica (read-modify-write sob lock)."""
        now = time.time()
        with self._lock:
            data = self._load_unlocked()
            data[key] = {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "expire": now + self.ttl.total_seconds(),
                "payload": payload,
            }
            self._save_unlocked(data)

    def has_valid(self, key: str) -> bool:
        return self.get(key) is not None
