# -*- coding: utf-8 -*-
"""Testes para PR9 — Escrita atômica da SyncQueue."""

from __future__ import annotations

import json
import os
from unittest import mock

import pytest

from src.infra.sync_queue import SyncQueue


# ═══════════════════════════════════════════════════════════════════════════
# Escrita atômica
# ═══════════════════════════════════════════════════════════════════════════


class TestAtomicWrite:
    """Verifica que a escrita usa temp + os.replace."""

    def test_save_calls_os_replace(self, tmp_path: object) -> None:
        path = str(tmp_path / "q.json")  # type: ignore[operator]
        q = SyncQueue(file_path=path)

        with mock.patch("src.infra.sync_queue.os.replace", wraps=os.replace) as m:
            q.enqueue("test_action", {"key": "val"})
        m.assert_called_once()
        # O segundo argumento deve ser o caminho final
        assert m.call_args[0][1] == path

    def test_no_leftover_temp_on_success(self, tmp_path: object) -> None:
        dir_ = str(tmp_path)  # type: ignore[arg-type]
        path = os.path.join(dir_, "q.json")
        q = SyncQueue(file_path=path)
        q.enqueue("a", {"x": 1})

        files = os.listdir(dir_)
        # Só deve existir o arquivo final
        assert files == ["q.json"]

    def test_original_survives_when_dump_fails(self, tmp_path: object) -> None:
        """Se json.dump falhar, o arquivo original deve permanecer intacto."""
        path = str(tmp_path / "q.json")  # type: ignore[operator]
        q = SyncQueue(file_path=path)
        q.enqueue("original", {"seq": 1})

        # Ler conteúdo original
        with open(path, "r", encoding="utf-8") as f:
            original = json.load(f)
        assert len(original) == 1

        # Falhar o dump
        with mock.patch("src.infra.sync_queue.json.dump", side_effect=OSError("disk full")):
            with pytest.raises(OSError, match="disk full"):
                q.enqueue("should_not_persist", {"seq": 2})

        # Arquivo original intacto
        with open(path, "r", encoding="utf-8") as f:
            after = json.load(f)
        assert after == original

    def test_no_temp_leftover_on_failure(self, tmp_path: object) -> None:
        """Arquivos temporários devem ser removidos em caso de erro."""
        dir_ = str(tmp_path)  # type: ignore[arg-type]
        path = os.path.join(dir_, "q.json")
        q = SyncQueue(file_path=path)

        with mock.patch("src.infra.sync_queue.json.dump", side_effect=OSError("boom")):
            with pytest.raises(OSError):
                q.enqueue("x", {})

        temps = [f for f in os.listdir(dir_) if f.startswith(".syncq_")]
        assert temps == []


# ═══════════════════════════════════════════════════════════════════════════
# Leitura resiliente — arquivo corrompido
# ═══════════════════════════════════════════════════════════════════════════


class TestCorruptFileRecovery:
    """Verifica que JSON inválido é renomeado e fila inicia vazia."""

    def test_corrupt_file_is_quarantined(self, tmp_path: object) -> None:
        dir_ = str(tmp_path)  # type: ignore[arg-type]
        path = os.path.join(dir_, "q.json")

        # Criar arquivo corrompido
        with open(path, "w") as f:
            f.write("{{{invalid json!!!")

        q = SyncQueue(file_path=path)
        items = q.list()

        # Fila deve estar vazia
        assert items == []
        # Arquivo corrompido deve ter sido renomeado
        corrupt_files = [f for f in os.listdir(dir_) if ".corrupt." in f]
        assert len(corrupt_files) == 1

    def test_corrupt_backup_preserves_content(self, tmp_path: object) -> None:
        dir_ = str(tmp_path)  # type: ignore[arg-type]
        path = os.path.join(dir_, "q.json")
        garbage = "not valid json 12345"

        with open(path, "w") as f:
            f.write(garbage)

        q = SyncQueue(file_path=path)
        # Trigger load (constructor não lê; list() sim)
        q.list()

        corrupt_files = [f for f in os.listdir(dir_) if ".corrupt." in f]
        assert len(corrupt_files) == 1
        with open(os.path.join(dir_, corrupt_files[0]), "r") as f:
            assert f.read() == garbage

    def test_new_file_created_after_corrupt_recovery(self, tmp_path: object) -> None:
        path = str(tmp_path / "q.json")  # type: ignore[operator]
        with open(path, "w") as f:
            f.write("GARBAGE")

        q = SyncQueue(file_path=path)
        # Enqueue deve funcionar normalmente após recuperação
        q.enqueue("recovered", {"ok": True})
        items = q.list()
        assert len(items) == 1
        assert items[0]["type"] == "recovered"


# ═══════════════════════════════════════════════════════════════════════════
# Lock de concorrência
# ═══════════════════════════════════════════════════════════════════════════


class TestConcurrencyLock:
    """Verifica que operações críticas usam o lock."""

    def test_enqueue_acquires_lock(self, tmp_path: object) -> None:
        path = str(tmp_path / "q.json")  # type: ignore[operator]
        q = SyncQueue(file_path=path)

        # Substituir o lock inteiro por um mock que registra chamadas
        real_lock = q._lock
        mock_lock = mock.MagicMock(wraps=real_lock)
        q._lock = mock_lock

        q.enqueue("t", {})

        mock_lock.__enter__.assert_called()
        q._lock = real_lock

    def test_list_acquires_lock(self, tmp_path: object) -> None:
        path = str(tmp_path / "q.json")  # type: ignore[operator]
        q = SyncQueue(file_path=path)

        real_lock = q._lock
        mock_lock = mock.MagicMock(wraps=real_lock)
        q._lock = mock_lock

        q.list()

        mock_lock.__enter__.assert_called()
        q._lock = real_lock


# ═══════════════════════════════════════════════════════════════════════════
# Roundtrip funcional
# ═══════════════════════════════════════════════════════════════════════════


class TestFunctionalRoundtrip:
    """Testes de integração básicos: enqueue → list → process."""

    def test_enqueue_and_list(self, tmp_path: object) -> None:
        path = str(tmp_path / "q.json")  # type: ignore[operator]
        q = SyncQueue(file_path=path)
        q.enqueue("action_a", {"val": 1})
        q.enqueue("action_b", {"val": 2})

        items = q.list()
        assert len(items) == 2
        assert items[0]["type"] == "action_a"
        assert items[1]["type"] == "action_b"

    def test_process_removes_successful(self, tmp_path: object) -> None:
        path = str(tmp_path / "q.json")  # type: ignore[operator]
        q = SyncQueue(file_path=path)
        q.enqueue("ok", {})
        q.enqueue("fail", {})

        processed, remaining = q.process(lambda item: item["type"] == "ok")
        assert processed == 1
        assert remaining == 1
        assert q.list()[0]["type"] == "fail"

    def test_survives_restart(self, tmp_path: object) -> None:
        """Simula reinício: cria SyncQueue, enqueue, cria nova instância, dados persistem."""
        path = str(tmp_path / "q.json")  # type: ignore[operator]
        q1 = SyncQueue(file_path=path)
        q1.enqueue("persist_me", {"data": 42})

        # "Reiniciar" — nova instância
        q2 = SyncQueue(file_path=path)
        items = q2.list()
        assert len(items) == 1
        assert items[0]["type"] == "persist_me"
        assert items[0]["payload"]["data"] == 42
