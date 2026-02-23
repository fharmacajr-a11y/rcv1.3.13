# pyright: reportAttributeAccessIssue=false
# -*- coding: utf-8 -*-
"""Testes unitários para src/infra/cache_store.py (JsonCacheStore)."""

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from src.infra.cache_store import JsonCacheStore

_MODULE = "src.infra.cache_store.time.time"


def _make_store(path: str, ttl_hours: int = 1) -> JsonCacheStore:
    return JsonCacheStore(file_path=path, ttl_hours=ttl_hours)


class TestSetGet(unittest.TestCase):
    """set/get com TTL controlado via mock."""

    def test_get_before_expiry_returns_payload(self):
        with tempfile.TemporaryDirectory() as d:
            store = _make_store(os.path.join(d, "cache.json"))
            t0 = 1_000_000.0

            with patch(_MODULE, return_value=t0):
                store.set("k", {"x": 1})

            with patch(_MODULE, return_value=t0 + 10):
                result = store.get("k")

            self.assertEqual(result, {"x": 1})

    def test_get_after_expiry_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "cache.json")
            store = _make_store(path, ttl_hours=1)
            t0 = 1_000_000.0

            with patch(_MODULE, return_value=t0):
                store.set("k", "dados")

            with patch(_MODULE, return_value=t0 + 3601.0):
                result = store.get("k")

            self.assertIsNone(result)

    def test_expired_entry_removed_from_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "cache.json")
            store = _make_store(path, ttl_hours=1)
            t0 = 1_000_000.0

            with patch(_MODULE, return_value=t0):
                store.set("k", "dados")

            with patch(_MODULE, return_value=t0 + 3601.0):
                store.get("k")

            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            self.assertNotIn("k", data)

    def test_expire_field_persisted(self):
        """set() deve gravar 'expire' no arquivo JSON."""
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "cache.json")
            store = _make_store(path, ttl_hours=1)
            t0 = 1_000_000.0

            with patch(_MODULE, return_value=t0):
                store.set("k", [1, 2])

            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            entry = data.get("k", {})
            self.assertIn("expire", entry)
            self.assertAlmostEqual(entry["expire"], t0 + 3600.0, places=1)

    def test_get_returns_only_payload_not_wrapper(self):
        """get() deve retornar o payload, não o dict {timestamp, expire, payload}."""
        with tempfile.TemporaryDirectory() as d:
            store = _make_store(os.path.join(d, "cache.json"))
            t0 = 1_000_000.0

            with patch(_MODULE, return_value=t0):
                store.set("k", {"nome": "teste"})

            with patch(_MODULE, return_value=t0 + 1):
                result = store.get("k")

            self.assertIsInstance(result, dict)
            self.assertEqual(result, {"nome": "teste"})
            self.assertNotIn("expire", result)
            self.assertNotIn("timestamp", result)


class TestLegacyEntries(unittest.TestCase):
    """Compatibilidade com entradas legadas (sem campo 'expire')."""

    def _write_legacy(self, path: str, key: str, ts: str, payload) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({key: {"timestamp": ts, "payload": payload}}, f)

    def test_legacy_recent_entry_accepted(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "cache.json")
            ts = datetime.now().isoformat(timespec="seconds")
            self._write_legacy(path, "leg", ts, "valor")

            store = _make_store(path, ttl_hours=1)
            self.assertEqual(store.get("leg"), "valor")

    def test_legacy_old_entry_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "cache.json")
            old_ts = (datetime.now() - timedelta(hours=2)).isoformat(timespec="seconds")
            self._write_legacy(path, "leg", old_ts, "stale")

            store = _make_store(path, ttl_hours=1)
            self.assertIsNone(store.get("leg"))

    def test_legacy_entry_gets_migrated(self):
        """Ao ler entrada legada válida, 'expire' deve ser adicionado no arquivo."""
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "cache.json")
            ts = datetime.now().isoformat(timespec="seconds")
            self._write_legacy(path, "leg", ts, "val")

            store = _make_store(path, ttl_hours=1)
            store.get("leg")  # deve migrar automaticamente

            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            self.assertIn("expire", data.get("leg", {}))

    def test_legacy_invalid_timestamp_treated_as_expired(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "cache.json")
            self._write_legacy(path, "leg", "nao-e-uma-data", "x")

            store = _make_store(path, ttl_hours=1)
            self.assertIsNone(store.get("leg"))


class TestHasValid(unittest.TestCase):
    def test_has_valid_true_before_expiry(self):
        with tempfile.TemporaryDirectory() as d:
            store = _make_store(os.path.join(d, "cache.json"))
            t0 = 1_000_000.0

            with patch(_MODULE, return_value=t0):
                store.set("k", "y")

            with patch(_MODULE, return_value=t0 + 10):
                self.assertTrue(store.has_valid("k"))

    def test_has_valid_false_after_expiry(self):
        with tempfile.TemporaryDirectory() as d:
            store = _make_store(os.path.join(d, "cache.json"))
            t0 = 1_000_000.0

            with patch(_MODULE, return_value=t0):
                store.set("k", "y")

            with patch(_MODULE, return_value=t0 + 3601.0):
                self.assertFalse(store.has_valid("k"))


class TestGetEntry(unittest.TestCase):
    def test_get_entry_returns_full_dict(self):
        with tempfile.TemporaryDirectory() as d:
            store = _make_store(os.path.join(d, "cache.json"))
            t0 = 1_000_000.0

            with patch(_MODULE, return_value=t0):
                store.set("k", {"a": 1})

            with patch(_MODULE, return_value=t0 + 1):
                entry = store.get_entry("k")

            self.assertIsNotNone(entry)
            self.assertIn("expire", entry)
            self.assertIn("timestamp", entry)
            self.assertIn("payload", entry)
            self.assertEqual(entry["payload"], {"a": 1})

    def test_get_entry_returns_none_when_expired(self):
        with tempfile.TemporaryDirectory() as d:
            store = _make_store(os.path.join(d, "cache.json"))
            t0 = 1_000_000.0

            with patch(_MODULE, return_value=t0):
                store.set("k", "z")

            with patch(_MODULE, return_value=t0 + 3601.0):
                self.assertIsNone(store.get_entry("k"))


if __name__ == "__main__":
    unittest.main()
