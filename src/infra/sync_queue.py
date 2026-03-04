import json
import logging
import os
import tempfile
import uuid
import threading
from datetime import datetime

log = logging.getLogger(__name__)


class SyncQueue:
    """
    Fila local persistente para operações que dependem de API.
    Cada item: { "id": "...", "type": "nome_da_acao", "payload": {...}, "timestamp": "..." }

    Escrita atômica (temp + os.replace) e leitura resiliente (arquivo
    corrompido é renomeado para *.corrupt.<timestamp>).
    """

    def __init__(self, file_path="runtime/sync_queue.json"):
        self.file_path = file_path
        self._lock = threading.Lock()
        dir_name = os.path.dirname(self.file_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        if not os.path.exists(self.file_path):
            self._atomic_write_json([])

    # ------------------------------------------------------------------
    # I/O interno — sem lock, para ser chamado dentro de seções críticas
    # ------------------------------------------------------------------

    def _atomic_write_json(self, data):
        """Grava *data* em JSON de forma atômica (temp → os.replace)."""
        dir_name = os.path.dirname(self.file_path) or "."
        fd, tmp_path = tempfile.mkstemp(
            dir=dir_name,
            prefix=".syncq_",
            suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, self.file_path)
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def _load_unlocked(self):
        """Carrega a fila do disco.  Se o JSON for inválido, renomeia o
        arquivo corrompido e retorna lista vazia."""
        if not os.path.exists(self.file_path):
            return []
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
            log.warning("sync_queue: conteúdo não é uma lista, recriando fila vazia")
            return []
        except json.JSONDecodeError:
            self._quarantine_corrupt_file()
            return []
        except Exception:
            return []

    def _quarantine_corrupt_file(self):
        """Renomeia arquivo corrompido para *.corrupt.<timestamp>."""
        try:
            ts = datetime.now().strftime("%Y%m%d%H%M%S")
            corrupt_path = f"{self.file_path}.corrupt.{ts}"
            os.replace(self.file_path, corrupt_path)
            log.warning(
                "sync_queue: arquivo JSON corrompido renomeado para %s",
                os.path.basename(corrupt_path),
            )
        except OSError as exc:
            log.warning("sync_queue: falha ao renomear arquivo corrompido: %s", exc)

    def _save_unlocked(self, items):
        self._atomic_write_json(items)

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
