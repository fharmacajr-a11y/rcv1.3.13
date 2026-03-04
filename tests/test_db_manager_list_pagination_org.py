# -*- coding: utf-8 -*-
"""Testes para paginação e filtro org_id em list_clientes / list_clientes_deletados (PR18).

Garante que:
- _current_org_id() resolve uid → memberships → org_id
- _current_org_id() retorna None em caso de falha/ausência
- list_clientes aplica .eq("org_id", …) quando disponível
- list_clientes aplica .range(offset, offset+limit-1) quando limit != None
- list_clientes sem limit emite warning e não aplica .range()
- list_clientes aplica .order() estável (col + tiebreaker "id")
- list_clientes_deletados: mesmas garantias acima
- list_clientes_by_org: agora aceita limit/offset e aplica .range()
- DEFAULT_PAGE_LIMIT exportado com valor 200
"""

from __future__ import annotations

import importlib
import logging
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MOD_PATH = "src.core.db_manager.db_manager"


def _get_mod():
    return importlib.import_module(_MOD_PATH)


def _fake_row(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": 1,
        "numero": "001",
        "nome": "Acme",
        "razao_social": "Acme Ltda",
        "cnpj": "11222333000181",
        "cnpj_norm": "11222333000181",
        "ultima_alteracao": "2025-01-01T00:00:00Z",
        "obs": "",
        "ultima_por": "user@example.com",
        "created_at": "2025-01-01T00:00:00Z",
    }
    base.update(overrides)
    return base


def _chain_mock(data: list[dict[str, Any]] | None = None) -> MagicMock:
    """Retorna um mock encadeável que imita a query-builder do Supabase.

    Cada chamada de método retorna o mesmo mock, exceto exec_postgrest
    que é patcheado separadamente.
    """
    chain = MagicMock()
    chain.select.return_value = chain
    chain.is_.return_value = chain
    chain.not_.is_.return_value = chain
    chain.eq.return_value = chain
    chain.order.return_value = chain
    chain.range.return_value = chain
    chain.limit.return_value = chain
    return chain


# ---------------------------------------------------------------------------
# _current_org_id
# ---------------------------------------------------------------------------


class TestCurrentOrgId:
    """Testes unitários para o helper _current_org_id."""

    def test_returns_org_id_on_success(self) -> None:
        mod = _get_mod()
        fake_user = SimpleNamespace(user=SimpleNamespace(id="uid-123"))
        fake_membership = MagicMock(data=[{"org_id": "org-abc"}])

        with (
            patch.object(mod, "supabase") as sb,
            patch.object(mod, "exec_postgrest", return_value=fake_membership),
        ):
            sb.auth.get_user.return_value = fake_user
            sb.table.return_value = _chain_mock()
            result = mod._current_org_id()

        assert result == "org-abc"

    def test_returns_none_when_no_user(self) -> None:
        mod = _get_mod()
        fake_user = SimpleNamespace(user=SimpleNamespace(id=None))

        with patch.object(mod, "supabase") as sb:
            sb.auth.get_user.return_value = fake_user
            result = mod._current_org_id()

        assert result is None

    def test_returns_none_when_no_memberships(self) -> None:
        mod = _get_mod()
        fake_user = SimpleNamespace(user=SimpleNamespace(id="uid-123"))
        empty_resp = MagicMock(data=[])

        with (
            patch.object(mod, "supabase") as sb,
            patch.object(mod, "exec_postgrest", return_value=empty_resp),
        ):
            sb.auth.get_user.return_value = fake_user
            sb.table.return_value = _chain_mock()
            result = mod._current_org_id()

        assert result is None

    def test_returns_none_on_exception(self) -> None:
        mod = _get_mod()

        with patch.object(mod, "supabase") as sb:
            sb.auth.get_user.side_effect = RuntimeError("network")
            result = mod._current_org_id()

        assert result is None

    def test_dict_response_fallback(self) -> None:
        """Cobre branch quando get_user retorna dict (API v1 compat)."""
        mod = _get_mod()
        fake_membership = MagicMock(data=[{"org_id": "org-dict"}])

        with (
            patch.object(mod, "supabase") as sb,
            patch.object(mod, "exec_postgrest", return_value=fake_membership),
        ):
            sb.auth.get_user.return_value = {"user": {"id": "uid-dict"}}
            sb.table.return_value = _chain_mock()
            result = mod._current_org_id()

        assert result == "org-dict"


# ---------------------------------------------------------------------------
# list_clientes — org_id + paginação
# ---------------------------------------------------------------------------


class TestListClientesPaginationOrg:
    """Testes para list_clientes com org_id e paginação (PR18)."""

    def _call(self, mod, chain, org_id="org-1", **kwargs):
        resp = MagicMock(data=[_fake_row()])
        with (
            patch.object(mod, "supabase") as sb,
            patch.object(mod, "_current_org_id", return_value=org_id),
            patch.object(mod, "exec_postgrest", return_value=resp),
        ):
            sb.table.return_value = chain
            result = mod.list_clientes(**kwargs)
        return result, chain

    def test_applies_org_id_filter(self) -> None:
        mod = _get_mod()
        chain = _chain_mock()
        self._call(mod, chain, org_id="org-xyz")
        chain.eq.assert_called_once_with("org_id", "org-xyz")

    def test_no_org_id_skips_eq_and_warns(self, caplog: pytest.LogCaptureFixture) -> None:
        mod = _get_mod()
        chain = _chain_mock()
        with caplog.at_level(logging.WARNING):
            self._call(mod, chain, org_id=None)
        chain.eq.assert_not_called()
        assert "org_id indisponível" in caplog.text

    def test_default_limit_applies_range(self) -> None:
        mod = _get_mod()
        chain = _chain_mock()
        self._call(mod, chain)
        chain.range.assert_called_once_with(0, 199)

    def test_custom_limit_and_offset(self) -> None:
        mod = _get_mod()
        chain = _chain_mock()
        self._call(mod, chain, limit=50, offset=100)
        chain.range.assert_called_once_with(100, 149)

    def test_limit_none_skips_range_and_warns(self, caplog: pytest.LogCaptureFixture) -> None:
        mod = _get_mod()
        chain = _chain_mock()
        with caplog.at_level(logging.WARNING):
            self._call(mod, chain, limit=None)
        chain.range.assert_not_called()
        assert "fetch_all" in caplog.text

    def test_returns_cliente_objects(self) -> None:
        mod = _get_mod()
        chain = _chain_mock()
        result, _ = self._call(mod, chain)
        assert len(result) == 1
        assert result[0].razao_social == "Acme Ltda"

    def test_stable_order_tiebreaker(self) -> None:
        mod = _get_mod()
        chain = _chain_mock()
        self._call(mod, chain)
        # Deve chamar .order() duas vezes: col principal + tiebreaker "id"
        assert chain.order.call_count == 2
        second_call = chain.order.call_args_list[1]
        assert second_call == call("id", desc=True)


# ---------------------------------------------------------------------------
# list_clientes_deletados — org_id + paginação
# ---------------------------------------------------------------------------


class TestListClientesDeletadosPaginationOrg:
    """Testes para list_clientes_deletados com org_id e paginação."""

    def _call(self, mod, chain, org_id="org-1", **kwargs):
        resp = MagicMock(data=[_fake_row()])
        with (
            patch.object(mod, "supabase") as sb,
            patch.object(mod, "_current_org_id", return_value=org_id),
            patch.object(mod, "exec_postgrest", return_value=resp),
        ):
            sb.table.return_value = chain
            result = mod.list_clientes_deletados(**kwargs)
        return result, chain

    def test_applies_org_id_filter(self) -> None:
        mod = _get_mod()
        chain = _chain_mock()
        self._call(mod, chain, org_id="org-trash")
        chain.eq.assert_called_once_with("org_id", "org-trash")

    def test_no_org_id_skips_eq_and_warns(self, caplog: pytest.LogCaptureFixture) -> None:
        mod = _get_mod()
        chain = _chain_mock()
        with caplog.at_level(logging.WARNING):
            self._call(mod, chain, org_id=None)
        chain.eq.assert_not_called()
        assert "org_id indisponível" in caplog.text

    def test_default_limit_applies_range(self) -> None:
        mod = _get_mod()
        chain = _chain_mock()
        self._call(mod, chain)
        chain.range.assert_called_once_with(0, 199)

    def test_limit_none_skips_range(self) -> None:
        mod = _get_mod()
        chain = _chain_mock()
        self._call(mod, chain, limit=None)
        chain.range.assert_not_called()

    def test_stable_order_tiebreaker(self) -> None:
        mod = _get_mod()
        chain = _chain_mock()
        self._call(mod, chain)
        assert chain.order.call_count == 2
        second_call = chain.order.call_args_list[1]
        assert second_call == call("id", desc=True)


# ---------------------------------------------------------------------------
# list_clientes_by_org — paginação (org_id já era obrigatório)
# ---------------------------------------------------------------------------


class TestListClientesByOrgPagination:
    """Testes para paginação adicionada a list_clientes_by_org."""

    def _call(self, mod, chain, org_id="org-1", **kwargs):
        resp = MagicMock(data=[_fake_row()])
        with (
            patch.object(mod, "supabase") as sb,
            patch.object(mod, "exec_postgrest", return_value=resp),
        ):
            sb.table.return_value = chain
            result = mod.list_clientes_by_org(org_id=org_id, **kwargs)
        return result, chain

    def test_default_limit_applies_range(self) -> None:
        mod = _get_mod()
        chain = _chain_mock()
        self._call(mod, chain)
        chain.range.assert_called_once_with(0, 199)

    def test_custom_offset(self) -> None:
        mod = _get_mod()
        chain = _chain_mock()
        self._call(mod, chain, limit=50, offset=200)
        chain.range.assert_called_once_with(200, 249)

    def test_limit_none_no_range(self) -> None:
        mod = _get_mod()
        chain = _chain_mock()
        self._call(mod, chain, limit=None)
        chain.range.assert_not_called()

    def test_stable_order_tiebreaker(self) -> None:
        mod = _get_mod()
        chain = _chain_mock()
        self._call(mod, chain)
        assert chain.order.call_count == 2


# ---------------------------------------------------------------------------
# DEFAULT_PAGE_LIMIT — exportação
# ---------------------------------------------------------------------------


class TestDefaultPageLimit:
    """Verifica que a constante está exportada e tem valor esperado."""

    def test_value(self) -> None:
        mod = _get_mod()
        assert mod.DEFAULT_PAGE_LIMIT == 200

    def test_exported_from_init(self) -> None:
        init = importlib.import_module("src.core.db_manager")
        assert hasattr(init, "DEFAULT_PAGE_LIMIT")
        assert init.DEFAULT_PAGE_LIMIT == 200
