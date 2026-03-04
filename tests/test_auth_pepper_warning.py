"""Testes para o warning de pepper vazio em auth.py (PR13)."""

from __future__ import annotations

import logging
import os


def _get_auth_mod():
    """Obtém referência ao módulo auth e reseta flag _pepper_warned."""
    import src.core.auth.auth as auth_mod

    auth_mod._pepper_warned = False
    return auth_mod


def _clear_pepper(monkeypatch):
    """Remove AUTH_PEPPER de todas as fontes (env + config file)."""
    monkeypatch.setenv("AUTH_PEPPER", "")
    monkeypatch.setenv("RC_AUTH_PEPPER", "")
    # Impede fallback via config.yml/config.yaml
    _original_isfile = os.path.isfile

    def _isfile_no_config(p):
        base = os.path.basename(str(p))
        if base in ("config.yml", "config.yaml"):
            return False
        return _original_isfile(p)

    monkeypatch.setattr(os.path, "isfile", _isfile_no_config)


class TestPepperWarning:
    """Testes do warning SEC-006 quando pepper está vazio."""

    def test_empty_pepper_emits_warning(self, monkeypatch, caplog):
        """Pepper vazio deve emitir warning SEC-006."""
        _clear_pepper(monkeypatch)
        auth_mod = _get_auth_mod()

        with caplog.at_level(logging.WARNING, logger="core.auth"):
            result = auth_mod._get_auth_pepper()

        assert result == ""
        sec006 = [r for r in caplog.records if "SEC-006" in r.message]
        assert len(sec006) == 1
        assert "AUTH_PEPPER" in sec006[0].message

    def test_set_pepper_no_warning(self, monkeypatch, caplog):
        """Pepper configurado não deve emitir warning."""
        monkeypatch.setenv("AUTH_PEPPER", "a-secure-pepper-value-1234")
        auth_mod = _get_auth_mod()

        with caplog.at_level(logging.WARNING, logger="core.auth"):
            result = auth_mod._get_auth_pepper()

        assert result == "a-secure-pepper-value-1234"
        sec006 = [r for r in caplog.records if "SEC-006" in r.message]
        assert len(sec006) == 0

    def test_rc_pepper_env_no_warning(self, monkeypatch, caplog):
        """RC_AUTH_PEPPER configurado não deve emitir warning."""
        monkeypatch.setenv("AUTH_PEPPER", "")
        monkeypatch.setenv("RC_AUTH_PEPPER", "another-pepper-value-5678")
        auth_mod = _get_auth_mod()

        with caplog.at_level(logging.WARNING, logger="core.auth"):
            result = auth_mod._get_auth_pepper()

        assert result == "another-pepper-value-5678"
        sec006 = [r for r in caplog.records if "SEC-006" in r.message]
        assert len(sec006) == 0

    def test_warning_emitted_only_once(self, monkeypatch, caplog):
        """Warning deve ser emitido apenas 1 vez por execução (once-only)."""
        _clear_pepper(monkeypatch)
        auth_mod = _get_auth_mod()

        with caplog.at_level(logging.WARNING, logger="core.auth"):
            auth_mod._get_auth_pepper()
            auth_mod._get_auth_pepper()
            auth_mod._get_auth_pepper()

        sec006 = [r for r in caplog.records if "SEC-006" in r.message]
        assert len(sec006) == 1, f"Esperava 1 warning, obteve {len(sec006)}"

    def test_whitespace_pepper_treated_as_set(self, monkeypatch, caplog):
        """Pepper com whitespace '   ' é truthy — retorna sem warning."""
        monkeypatch.setenv("AUTH_PEPPER", "   ")
        auth_mod = _get_auth_mod()

        with caplog.at_level(logging.WARNING, logger="core.auth"):
            result = auth_mod._get_auth_pepper()

        # "   " é truthy para os.getenv, retorna sem warning
        assert result == "   "
        sec006 = [r for r in caplog.records if "SEC-006" in r.message]
        assert len(sec006) == 0

    def test_warning_never_logs_pepper_value(self, monkeypatch, caplog):
        """Mensagem de warning nunca deve conter o valor do pepper."""
        _clear_pepper(monkeypatch)
        auth_mod = _get_auth_mod()

        with caplog.at_level(logging.WARNING, logger="core.auth"):
            auth_mod._get_auth_pepper()

        for record in caplog.records:
            assert "pepper-value" not in record.message.lower()
            assert "secure-pepper" not in record.message.lower()
