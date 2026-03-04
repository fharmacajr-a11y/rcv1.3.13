# -*- coding: utf-8 -*-
"""Testes para escrita atômica e leitura resiliente em prefs.py (PR17)."""

from __future__ import annotations

import json
import os
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# _atomic_write_json
# ---------------------------------------------------------------------------


class TestAtomicWriteJson:
    """Garante atomicidade: temp → fsync → os.replace."""

    def test_basic_write(self, tmp_path: pytest.TempPathFactory) -> None:
        """Escrita básica cria arquivo com conteúdo correto."""
        from src.utils.prefs import _atomic_write_json

        path = str(tmp_path / "test.json")
        _atomic_write_json(path, {"a": 1})

        with open(path, encoding="utf-8") as f:
            assert json.load(f) == {"a": 1}

    def test_os_replace_is_called(self, tmp_path: pytest.TempPathFactory) -> None:
        """os.replace é chamado durante a escrita atômica."""
        from src.utils.prefs import _atomic_write_json

        path = str(tmp_path / "test.json")
        with patch("src.utils.prefs.os.replace", wraps=os.replace) as mock_replace:
            _atomic_write_json(path, {"ok": True})

        mock_replace.assert_called_once()
        # Primeiro arg é o temp, segundo é o path final
        _, final = mock_replace.call_args[0]
        assert final == path

    def test_crash_before_replace_preserves_original(self, tmp_path: pytest.TempPathFactory) -> None:
        """Se json.dump falhar, o arquivo original permanece intacto."""
        from src.utils.prefs import _atomic_write_json

        path = str(tmp_path / "prefs.json")
        # Escrever arquivo original válido
        original_data = {"user": "original"}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(original_data, f)

        # Forçar json.dump a falhar (simula crash antes do os.replace)
        with (
            patch("src.utils.prefs.json.dump", side_effect=OSError("disk full")),
            pytest.raises(OSError, match="disk full"),
        ):
            _atomic_write_json(path, {"user": "new"})

        # Arquivo original deve estar intacto
        with open(path, encoding="utf-8") as f:
            assert json.load(f) == original_data

    def test_no_leftover_temp_on_failure(self, tmp_path: pytest.TempPathFactory) -> None:
        """Temp files são removidos em caso de falha."""
        from src.utils.prefs import _atomic_write_json

        path = str(tmp_path / "prefs.json")
        with (
            patch("src.utils.prefs.json.dump", side_effect=OSError("disk full")),
            pytest.raises(OSError),
        ):
            _atomic_write_json(path, {"x": 1})

        # Nenhum .tmp restante no diretório
        remaining = [f for f in os.listdir(tmp_path) if f.endswith(".tmp")]
        assert remaining == []


# ---------------------------------------------------------------------------
# _resilient_load_json
# ---------------------------------------------------------------------------


class TestResilientLoadJson:
    """Garante quarentena de arquivo corrompido."""

    def test_valid_json_loads_normally(self, tmp_path: pytest.TempPathFactory) -> None:
        from src.utils.prefs import _resilient_load_json

        path = str(tmp_path / "ok.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"key": "val"}, f)

        assert _resilient_load_json(path) == {"key": "val"}

    def test_corrupt_json_quarantined(self, tmp_path: pytest.TempPathFactory, caplog) -> None:
        """Arquivo com JSON inválido é renomeado para .corrupt.<ts> e retorna None."""
        from src.utils.prefs import _resilient_load_json
        import logging

        path = str(tmp_path / "broken.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write("{invalid json!!")

        with caplog.at_level(logging.WARNING):
            result = _resilient_load_json(path)

        # Retorna None (caller usará defaults)
        assert result is None
        # Arquivo original não existe mais
        assert not os.path.exists(path)
        # Arquivo .corrupt.* foi criado
        corrupt_files = [f for f in os.listdir(tmp_path) if ".corrupt." in f]
        assert len(corrupt_files) == 1
        # Warning emitido
        assert any("corrompido" in r.message for r in caplog.records)

    def test_missing_file_returns_none(self, tmp_path: pytest.TempPathFactory) -> None:
        from src.utils.prefs import _resilient_load_json

        path = str(tmp_path / "nope.json")
        assert _resilient_load_json(path) is None

    def test_quarantine_warning_has_no_file_content(self, tmp_path: pytest.TempPathFactory, caplog) -> None:
        """Warning de quarentena NÃO vaza conteúdo do arquivo."""
        from src.utils.prefs import _resilient_load_json
        import logging

        path = str(tmp_path / "secret.json")
        secret = "SUPER-SECRET-PREFS-DATA-XYZ"
        with open(path, "w", encoding="utf-8") as f:
            f.write(secret)

        with caplog.at_level(logging.WARNING):
            _resilient_load_json(path)

        for record in caplog.records:
            assert secret not in record.message


# ---------------------------------------------------------------------------
# Integration: save/load com arquivo real
# ---------------------------------------------------------------------------


class TestPrefsIntegration:
    """Testes integrados para save/load de preferências via helpers atômicos."""

    def test_save_load_columns_visibility(
        self, tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """save_columns_visibility + load_columns_visibility round-trip."""
        from src.utils import prefs

        monkeypatch.setattr(prefs, "_get_base_dir", lambda: str(tmp_path))

        prefs.save_columns_visibility("u1", {"colA": True, "colB": False})
        result = prefs.load_columns_visibility("u1")
        assert result == {"colA": True, "colB": False}

    def test_load_corrupt_columns_returns_empty(
        self, tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Arquivo corrompido de columns_visibility → retorna {} e quarentina."""
        from src.utils import prefs

        monkeypatch.setattr(prefs, "_get_base_dir", lambda: str(tmp_path))
        path = os.path.join(str(tmp_path), prefs.PREFS_FILENAME)
        with open(path, "w", encoding="utf-8") as f:
            f.write("NOT JSON")

        result = prefs.load_columns_visibility("u1")
        assert result == {}
        assert not os.path.exists(path)

    def test_no_direct_open_w_in_prefs(self) -> None:
        """Nenhum 'open(path, \"w\")' direto no arquivo de prefs (exceto _atomic_write_json helper)."""
        import inspect
        from src.utils import prefs

        source = inspect.getsource(prefs)
        # _atomic_write_json usa os.fdopen, não open(path, "w")
        # Todas as demais funções não devem ter open(..., "w")
        # Excluir o helper e verificar o restante
        helper_start = source.index("def _atomic_write_json")
        helper_end = source.index("\ndef _resilient_load_json")
        source_without_helper = source[:helper_start] + source[helper_end:]

        import re

        # Procurar open(qualquer_coisa, "w") ou open(qualquer_coisa, 'w')
        matches = re.findall(r'open\([^)]*["\']w["\'][^)]*\)', source_without_helper)
        assert matches == [], f"open(..., 'w') direto encontrado fora do helper: {matches}"
