import json
import os
import uuid
import threading
from datetime import datetime


class SyncQueue:
    """
    Fila local persistente para operações que dependem de API.
    Cada item: { "id": "...", "type": "nome_da_acao", "payload": {...}, "timestamp": "..." }
    """

    def __init__(self, file_path="runtime/sync_queue.json"):
        self.file_path = file_path
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        if not os.path.exists(self.file_path):
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump([], f)

    # ------------------------------------------------------------------
    # I/O interno — sem lock, para ser chamado dentro de seções críticas
    # ------------------------------------------------------------------

    def _load_unlocked(self):
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save_unlocked(self, items):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)

    # Wrappers públicos preservados para retrocompatibilidade
    def _load(self):
        with self._lock:
            return self._load_unlocked()

    def _save(self, items):
        with self._lock:
            self._save_unlocked(items)

    def enqueue(self, action_type: str, payload: dict):
        """Enfileira operação de forma atômica (read-modify-write sob lock)."""
        with self._lock:
            items = self._load_unlocked()
            item = {
                "id": str(uuid.uuid4()),
                "type": action_type,
                "payload": payload,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            }
            items.append(item)
            self._save_unlocked(items)
            return item["id"]

    def list(self):
        return self._load()

    def process(self, processor_fn, max_items=None):
        """
        processor_fn: função que recebe (item) e retorna True (sucesso) ou False (falha).
        Remove apenas os itens que retornarem True.
        Operação atômica (read-modify-write sob lock).
        """
        with self._lock:
            items = self._load_unlocked()
            processed = 0
            remaining = []
            for idx, item in enumerate(items):
                if max_items is not None and processed >= max_items:
                    remaining.extend(items[idx:])
                    break
                try:
                    ok = bool(processor_fn(item))
                except Exception:
                    ok = False
                if ok:
                    processed += 1
                else:
                    remaining.append(item)
            self._save_unlocked(remaining)
            return processed, len(remaining)
