import time
import json
import os
import threading
from datetime import datetime, timedelta


class JsonCacheStore:
    """
    Cache simples baseado em JSON com TTL.
    Salva um dicionário: { cache_key: { "timestamp": "...", "payload": ... } }
    """

    def __init__(self, file_path="runtime/cache.json", ttl_hours=24):
        self.file_path = file_path
        self.ttl = timedelta(hours=ttl_hours)
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        if not os.path.exists(self.file_path):
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump({}, f)

    def _load(self):
        with self._lock:
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}

    def _save(self, data):
        with self._lock:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    def get(self, key):
        data = self._load()
        now = time.time()
        expired = [k for k, v in list(data.items()) if isinstance(v, dict) and v.get("expire", 0) < now]
        if expired:
            for k in expired:
                data.pop(k, None)
            self._save(data)
        item = data.get(key)
        if isinstance(item, dict) and item.get("expire", 0) < now:
            return None
        return item

    def set(self, key, payload):
        data = self._load()
        data[key] = {"timestamp": datetime.now().isoformat(timespec="seconds"), "payload": payload}
        self._save(data)

    def has_valid(self, key):
        return self.get(key) is not None
