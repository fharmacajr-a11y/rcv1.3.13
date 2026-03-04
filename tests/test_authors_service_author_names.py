# -*- coding: utf-8 -*-
"""Testes para load_env_author_names (PR14 — remoção de PII hardcoded)."""

from __future__ import annotations

import importlib
import json
import logging

import pytest


def _get_mod():
    """Importa e retorna o módulo authors_service."""
    return importlib.import_module("src.modules.hub.services.authors_service")


# ── helpers ──────────────────────────────────────────────────────────────────


class TestLoadEnvAuthorNames:
    """Testes para load_env_author_names()."""

    def test_valid_json_returns_map(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Env var com JSON válido deve retornar dict correto."""
        payload = {"user@example.com": "Alice", "admin@corp.io": "Bob"}
        monkeypatch.setenv("RC_INITIALS_MAP", json.dumps(payload))
        mod = _get_mod()
        result = mod.load_env_author_names()
        assert result == {"user@example.com": "Alice", "admin@corp.io": "Bob"}

    def test_invalid_json_returns_empty(self, monkeypatch: pytest.MonkeyPatch, caplog) -> None:
        """Env var com JSON inválido deve retornar {} e emitir warning."""
        monkeypatch.setenv("RC_INITIALS_MAP", "{not valid json!!")
        mod = _get_mod()
        with caplog.at_level(logging.WARNING):
            result = mod.load_env_author_names()
        assert result == {}
        assert any("SEC-014" in r.message for r in caplog.records)

    def test_absent_env_returns_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Sem env var definida, deve retornar {}."""
        monkeypatch.setenv("RC_INITIALS_MAP", "")
        mod = _get_mod()
        result = mod.load_env_author_names()
        assert result == {}

    def test_emails_normalized_to_lowercase(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Emails devem ser normalizados para lowercase."""
        payload = {"User@Example.COM": "Alice"}
        monkeypatch.setenv("RC_INITIALS_MAP", json.dumps(payload))
        mod = _get_mod()
        result = mod.load_env_author_names()
        assert "user@example.com" in result
        assert result["user@example.com"] == "Alice"

    def test_hardcoded_author_names_is_empty(self) -> None:
        """AUTHOR_NAMES não deve conter emails hardcoded (PR14)."""
        mod = _get_mod()
        assert mod.AUTHOR_NAMES == {}

    def test_warning_does_not_log_json_content(self, monkeypatch: pytest.MonkeyPatch, caplog) -> None:
        """Warning de JSON inválido NÃO deve incluir o conteúdo da env var."""
        secret_payload = "secret-invalid-json-content-12345"
        monkeypatch.setenv("RC_INITIALS_MAP", secret_payload)
        mod = _get_mod()
        with caplog.at_level(logging.WARNING):
            mod.load_env_author_names()
        for record in caplog.records:
            assert secret_payload not in record.message
