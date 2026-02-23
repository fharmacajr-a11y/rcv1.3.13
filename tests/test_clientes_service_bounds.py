# pyright: reportAttributeAccessIssue=false
# -*- coding: utf-8 -*-
"""
Testes unitários — Fase 10: acesso seguro a response.data[0] em service.py.

Cobre _resolve_current_org_id para garantir que:
  a) data = []        → RuntimeError (sem IndexError)
  b) data = None      → RuntimeError (sem IndexError)
  c) data = [row]     → retorna org_id corretamente
  d) row sem org_id   → RuntimeError
  e) exec_postgrest lança exceção → RuntimeError propagado
"""
from __future__ import annotations

import importlib
import importlib.util
import re
import sys
import types
import unittest
from typing import Any, cast
from unittest.mock import MagicMock, patch

_SVC_MOD_NAME = "src.modules.clientes.core.service"  # nome real → __package__ correto para imports relativos
_SVC_MOD_PATH = r"c:\Users\Pichau\Desktop\v1.5.73\src\modules\clientes\core\service.py"


# ---------------------------------------------------------------------------
# Stubs mínimos — retorna dict (NÃO modifica sys.modules)
# ---------------------------------------------------------------------------

def _build_stubs() -> dict:
    """Constrói stubs sem tocar em sys.modules (seguro em tempo de import)."""

    def _mk(name: str, **attrs) -> types.ModuleType:
        mod = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(mod, k, v)
        return mod

    class _FakeAdapter:
        def __init__(self, **kw): ...

    fake_storage_api = _mk(
        "src.adapters.storage.api",
        delete_file=MagicMock(),
        list_files=MagicMock(return_value=[]),
        using_storage_backend=MagicMock(),
    )
    fake_supa_storage = _mk("src.adapters.storage.supabase_storage",
                             SupabaseStorageAdapter=_FakeAdapter)
    fake_storage     = _mk("src.adapters.storage",
                            api=fake_storage_api, supabase_storage=fake_supa_storage)
    fake_adapters    = _mk("src.adapters", storage=fake_storage)
    fake_db_schemas  = _mk("src.infra.db_schemas", MEMBERSHIPS_SELECT_ORG_ID="org_id")
    fake_supa_client = _mk("src.infra.supabase_client",
                            supabase=MagicMock(), exec_postgrest=MagicMock())
    fake_infra       = _mk("src.infra", supabase_client=fake_supa_client,
                            db_schemas=fake_db_schemas)
    fake_cnpj        = _mk("src.core.cnpj_norm", normalize_cnpj=lambda x: x)
    fake_db_mgr      = _mk("src.core.db_manager",
                            find_cliente_by_cnpj_norm=MagicMock(return_value=None),
                            get_cliente_by_id=MagicMock(return_value=None),
                            list_clientes_deletados=MagicMock(return_value=[]))
    fake_cli_svc     = _mk("src.core.services.clientes_service",
                            count_clients=MagicMock(return_value=0),
                            checar_duplicatas_info=MagicMock(return_value={}),
                            salvar_cliente=MagicMock())
    fake_core_svcs   = _mk("src.core.services", clientes_service=fake_cli_svc)
    fake_constants   = _mk("src.modules.clientes.core.constants",
                            STATUS_PREFIX_RE=re.compile(r""))
    fake_cli_core    = _mk("src.modules.clientes.core", constants=fake_constants)
    fake_clientes    = _mk("src.modules.clientes", core=fake_cli_core)
    fake_modules     = _mk("src.modules", clientes=fake_clientes)

    return {
        "src.adapters.storage.api":              fake_storage_api,
        "src.adapters.storage.supabase_storage": fake_supa_storage,
        "src.adapters.storage":                  fake_storage,
        "src.adapters":                          fake_adapters,
        "src.infra.db_schemas":                  fake_db_schemas,
        "src.infra.supabase_client":             fake_supa_client,
        "src.infra":                             fake_infra,
        "src.core.cnpj_norm":                    fake_cnpj,
        "src.core.db_manager":                   fake_db_mgr,
        "src.core.services.clientes_service":    fake_cli_svc,
        "src.core.services":                     fake_core_svcs,
        "src.modules.clientes.core.constants":   fake_constants,
        "src.modules.clientes.core":             fake_cli_core,
        "src.modules.clientes":                  fake_clientes,
        "src.modules":                           fake_modules,
    }


# ---------------------------------------------------------------------------
# Módulo-alvo e patcher — inicializados em setUpModule, limpos em tearDownModule
# ---------------------------------------------------------------------------

_patcher: Any = None
svc: Any = None  # acessível pelos métodos de teste — definido em setUpModule


def setUpModule() -> None:  # noqa: N802
    global _patcher, svc
    _patcher = patch.dict(sys.modules, _build_stubs())
    _patcher.start()
    spec = importlib.util.spec_from_file_location(_SVC_MOD_NAME, _SVC_MOD_PATH)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules[_SVC_MOD_NAME] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    svc = cast(Any, mod)


def tearDownModule() -> None:  # noqa: N802
    global _patcher, svc
    svc = None
    sys.modules.pop(_SVC_MOD_NAME, None)
    if _patcher is not None:
        _patcher.stop()
    _patcher = None


# ---------------------------------------------------------------------------
# Helper para montar resposta fake do exec_postgrest
# ---------------------------------------------------------------------------

class _FakeResponse:
    def __init__(self, data):
        self.data = data


def _fake_user(uid: str = "uid-abc"):
    user = MagicMock()
    user.id = uid
    resp = MagicMock()
    resp.user = user
    return resp


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------

class TestResolveCurrentOrgIdEmptyData(unittest.TestCase):
    """data = [] → não deve levantar IndexError; deve levantar RuntimeError."""

    def test_empty_list_raises_runtime_not_index(self):
        with patch.object(svc, "supabase") as mock_supa, \
             patch.object(svc, "exec_postgrest") as mock_exec:
            mock_supa.auth.get_user.return_value = _fake_user("uid-1")
            mock_exec.return_value = _FakeResponse(data=[])

            with self.assertRaises(RuntimeError) as ctx:
                svc._resolve_current_org_id()

            self.assertNotIsInstance(ctx.exception.__cause__, IndexError,
                                     "causa não deve ser IndexError")
            self.assertIn("encontrada", str(ctx.exception).lower())

    def test_data_none_raises_runtime_not_index(self):
        """Quando .data é None (não lista) → RuntimeError sem IndexError."""
        with patch.object(svc, "supabase") as mock_supa, \
             patch.object(svc, "exec_postgrest") as mock_exec:
            mock_supa.auth.get_user.return_value = _fake_user("uid-2")
            mock_exec.return_value = _FakeResponse(data=None)

            with self.assertRaises(RuntimeError):
                svc._resolve_current_org_id()

    def test_exec_raises_wrapped_in_runtime(self):
        """exec_postgrest levantando exceção → RuntimeError propagado."""
        with patch.object(svc, "supabase") as mock_supa, \
             patch.object(svc, "exec_postgrest") as mock_exec:
            mock_supa.auth.get_user.return_value = _fake_user("uid-3")
            mock_exec.side_effect = ConnectionError("db indisponível")

            with self.assertRaises(RuntimeError) as ctx:
                svc._resolve_current_org_id()

            self.assertIn("db indisponível", str(ctx.exception))


class TestResolveCurrentOrgIdHappyPath(unittest.TestCase):
    """data = [{"org_id": "org-xyz"}] → retorna "org-xyz"."""

    def test_returns_org_id_string(self):
        with patch.object(svc, "supabase") as mock_supa, \
             patch.object(svc, "exec_postgrest") as mock_exec:
            mock_supa.auth.get_user.return_value = _fake_user("uid-ok")
            mock_exec.return_value = _FakeResponse(data=[{"org_id": "org-xyz"}])

            result = svc._resolve_current_org_id()

        self.assertEqual(result, "org-xyz")

    def test_returns_string_type(self):
        """org_id é sempre retornado como str."""
        with patch.object(svc, "supabase") as mock_supa, \
             patch.object(svc, "exec_postgrest") as mock_exec:
            mock_supa.auth.get_user.return_value = _fake_user("uid-ok2")
            mock_exec.return_value = _FakeResponse(data=[{"org_id": 42}])

            result = svc._resolve_current_org_id()

        self.assertIsInstance(result, str)
        self.assertEqual(result, "42")

    def test_extra_columns_ignored(self):
        """Colunas extras no row não causam erro."""
        with patch.object(svc, "supabase") as mock_supa, \
             patch.object(svc, "exec_postgrest") as mock_exec:
            mock_supa.auth.get_user.return_value = _fake_user("uid-ok3")
            mock_exec.return_value = _FakeResponse(data=[{"org_id": "org-a", "role": "admin"}])

            result = svc._resolve_current_org_id()

        self.assertEqual(result, "org-a")

    def test_uses_first_row_only(self):
        """Havendo múltiplos rows, o primeiro é usado (limit=1 no caller)."""
        with patch.object(svc, "supabase") as mock_supa, \
             patch.object(svc, "exec_postgrest") as mock_exec:
            mock_supa.auth.get_user.return_value = _fake_user("uid-multi")
            mock_exec.return_value = _FakeResponse(data=[
                {"org_id": "org-first"},
                {"org_id": "org-second"},
            ])

            result = svc._resolve_current_org_id()

        self.assertEqual(result, "org-first")


class TestResolveCurrentOrgIdMissingOrgId(unittest.TestCase):
    """Row presente mas org_id ausente/None → RuntimeError."""

    def test_row_without_org_id_key(self):
        with patch.object(svc, "supabase") as mock_supa, \
             patch.object(svc, "exec_postgrest") as mock_exec:
            mock_supa.auth.get_user.return_value = _fake_user("uid-noorg")
            mock_exec.return_value = _FakeResponse(data=[{"user_id": "uid-noorg"}])

            with self.assertRaises(RuntimeError):
                svc._resolve_current_org_id()

    def test_row_with_org_id_none(self):
        with patch.object(svc, "supabase") as mock_supa, \
             patch.object(svc, "exec_postgrest") as mock_exec:
            mock_supa.auth.get_user.return_value = _fake_user("uid-nullorg")
            mock_exec.return_value = _FakeResponse(data=[{"org_id": None}])

            with self.assertRaises(RuntimeError):
                svc._resolve_current_org_id()

    def test_row_with_org_id_empty_string(self):
        with patch.object(svc, "supabase") as mock_supa, \
             patch.object(svc, "exec_postgrest") as mock_exec:
            mock_supa.auth.get_user.return_value = _fake_user("uid-emptyorg")
            mock_exec.return_value = _FakeResponse(data=[{"org_id": ""}])

            with self.assertRaises(RuntimeError):
                svc._resolve_current_org_id()


class TestResolveCurrentOrgIdNoUser(unittest.TestCase):
    """Usuário não autenticado → RuntimeError."""

    def test_uid_none_raises(self):
        with patch.object(svc, "supabase") as mock_supa:
            resp = MagicMock()
            resp.user = MagicMock()
            resp.user.id = None
            # Como dict não
            mock_supa.auth.get_user.return_value = resp

            with self.assertRaises(RuntimeError) as ctx:
                svc._resolve_current_org_id()

            self.assertIn("autenticado", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()
