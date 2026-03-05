# -*- coding: utf-8 -*-
"""Testes para fallback de 'ultima_por' no db_manager (PR16).

Garante que:
- Erro de coluna inexistente (42703) → fallback (retry sem 'ultima_por')
- Qualquer outro erro (rede, RLS, permissão) → exceção propagada, sem fallback
"""

from __future__ import annotations

import importlib
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_api_error(code: str, message: str = "") -> Exception:
    """Cria instância de postgrest.exceptions.APIError (ou fallback)."""
    try:
        from postgrest.exceptions import APIError
    except Exception:
        # Fallback mínimo para CI sem postgrest
        class APIError(Exception):
            def __init__(self, error: dict) -> None:
                self.code = error.get("code")
                self.message = error.get("message")
                self.details = error.get("details")
                self.hint = error.get("hint")
                super().__init__(str(error))

    return APIError({"code": code, "message": message, "details": message})


def _get_mod():
    return importlib.import_module("src.core.db_manager.db_manager")


# ---------------------------------------------------------------------------
# _is_unknown_column_error
# ---------------------------------------------------------------------------


class TestIsUnknownColumnError:
    """Testes unitários para o helper _is_unknown_column_error."""

    def test_code_42703_returns_true(self) -> None:
        mod = _get_mod()
        exc = _make_api_error("42703", "some message")
        assert mod._is_unknown_column_error(exc) is True

    def test_code_pgrst204_returns_true(self) -> None:
        mod = _get_mod()
        exc = _make_api_error("PGRST204", "some message")
        assert mod._is_unknown_column_error(exc) is True

    def test_message_unknown_column_returns_true(self) -> None:
        mod = _get_mod()
        exc = _make_api_error("", "Could not find: unknown column in table")
        assert mod._is_unknown_column_error(exc) is True

    def test_unrelated_error_returns_false(self) -> None:
        mod = _get_mod()
        exc = _make_api_error("42501", "permission denied for table clients")
        assert mod._is_unknown_column_error(exc) is False

    def test_timeout_error_returns_false(self) -> None:
        mod = _get_mod()
        exc = _make_api_error("57014", "canceling statement due to statement timeout")
        assert mod._is_unknown_column_error(exc) is False

    def test_plain_exception_returns_false(self) -> None:
        """Exception genérica sem .code/.message → False."""
        mod = _get_mod()
        assert mod._is_unknown_column_error(RuntimeError("boom")) is False


# ---------------------------------------------------------------------------
# insert_cliente – fallback vs propagação
# ---------------------------------------------------------------------------


class TestInsertClienteFallback:
    """Garante que insert_cliente aplica fallback apenas para coluna inexistente."""

    @patch("src.core.db_manager.db_manager._current_org_id", return_value="org-test-123")
    @patch("src.core.db_manager.db_manager._current_user_email", return_value="u@test.com")
    @patch("src.core.db_manager.db_manager.supabase")
    @patch("src.core.db_manager.db_manager.exec_postgrest")
    def test_unknown_column_triggers_fallback(
        self, mock_exec: MagicMock, mock_supa: MagicMock, _mock_user: MagicMock, _mock_org: MagicMock
    ) -> None:
        """Erro 42703 na 1ª tentativa → retry sem 'ultima_por'."""
        # 1ª chamada: levanta 42703; 2ª: sucesso
        ok_resp = MagicMock(data=[{"id": 99}])
        mock_exec.side_effect = [
            _make_api_error("42703", 'column "ultima_por" of relation "clients" does not exist'),
            ok_resp,
        ]

        mod = _get_mod()
        result = mod.insert_cliente("001", "Teste", "Razão", "00000000000100", "obs")

        assert result == 99
        assert mock_exec.call_count == 2

        # O payload foi passado via supabase.table().insert(payload) – verificamos
        # que o insert mock recebeu payload sem 'ultima_por'
        insert_calls = mock_supa.table.return_value.insert.call_args_list
        assert len(insert_calls) == 2
        second_payload = insert_calls[1][0][0]  # primeiro arg posicional
        assert "ultima_por" not in second_payload

    @patch("src.core.db_manager.db_manager._current_org_id", return_value="org-test-123")
    @patch("src.core.db_manager.db_manager._current_user_email", return_value="u@test.com")
    @patch("src.core.db_manager.db_manager.supabase")
    @patch("src.core.db_manager.db_manager.exec_postgrest")
    def test_permission_error_propagates(
        self, mock_exec: MagicMock, mock_supa: MagicMock, _mock_user: MagicMock, _mock_org: MagicMock
    ) -> None:
        """Erro de permissão (42501) NÃO faz fallback – exceção propaga."""
        mock_exec.side_effect = _make_api_error("42501", "permission denied for table clients")

        mod = _get_mod()
        with pytest.raises(Exception, match="permission denied"):
            mod.insert_cliente("001", "Teste", "Razão", "00000000000100", "obs")

        # Apenas 1 chamada (sem retry)
        assert mock_exec.call_count == 1


# ---------------------------------------------------------------------------
# update_cliente – fallback vs propagação
# ---------------------------------------------------------------------------


class TestUpdateClienteFallback:
    """Garante que update_cliente aplica fallback apenas para coluna inexistente."""

    @patch("src.core.db_manager.db_manager._current_user_email", return_value="u@test.com")
    @patch("src.core.db_manager.db_manager.supabase")
    @patch("src.core.db_manager.db_manager.exec_postgrest")
    def test_unknown_column_triggers_fallback(
        self, mock_exec: MagicMock, mock_supa: MagicMock, _mock_user: MagicMock
    ) -> None:
        ok_resp = MagicMock(data=[{"id": 1}], count=None)
        mock_exec.side_effect = [
            _make_api_error("42703", 'column "ultima_por" does not exist'),
            ok_resp,
        ]

        mod = _get_mod()
        mod.update_cliente(1, "001", "Teste", "Razão", "00000000000100", "obs")

        assert mock_exec.call_count == 2

        update_calls = mock_supa.table.return_value.update.call_args_list
        assert len(update_calls) == 2
        second_payload = update_calls[1][0][0]
        assert "ultima_por" not in second_payload

    @patch("src.core.db_manager.db_manager._current_user_email", return_value="u@test.com")
    @patch("src.core.db_manager.db_manager.supabase")
    @patch("src.core.db_manager.db_manager.exec_postgrest")
    def test_timeout_error_propagates(self, mock_exec: MagicMock, mock_supa: MagicMock, _mock_user: MagicMock) -> None:
        mock_exec.side_effect = _make_api_error("57014", "statement timeout")

        mod = _get_mod()
        with pytest.raises(Exception, match="timeout"):
            mod.update_cliente(1, "001", "Teste", "Razão", "00000000000100", "obs")

        assert mock_exec.call_count == 1
