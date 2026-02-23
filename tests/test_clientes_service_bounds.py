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

import sys
import types
import unittest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Stubs mínimos para importar service.py sem dependências pesadas
# ---------------------------------------------------------------------------

def _install_stubs() -> None:
    """Injeta módulos stub em sys.modules antes de importar o alvo."""

    def _stub(name: str, **attrs) -> types.ModuleType:
        mod = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(mod, k, v)
        sys.modules.setdefault(name, mod)
        return mod

    # src.adapters.storage.api
    _stub(
        "src.adapters.storage.api",
        delete_file=MagicMock(),
        list_files=MagicMock(return_value=[]),
        using_storage_backend=MagicMock(),
    )

    # src.adapters.storage.supabase_storage
    class _FakeAdapter:
        def __init__(self, **kw): ...
    _stub("src.adapters.storage.supabase_storage", SupabaseStorageAdapter=_FakeAdapter)
    _stub("src.adapters.storage", supabase_storage=sys.modules["src.adapters.storage.supabase_storage"])
    _stub("src.adapters", storage=sys.modules.get("src.adapters.storage"))

    # src.infra.db_schemas
    _stub("src.infra.db_schemas", MEMBERSHIPS_SELECT_ORG_ID="org_id")

    # supabase_client fake — supabase e exec_postgrest patcháveis depois
    _fake_supabase = MagicMock()
    _stub("src.infra.supabase_client", supabase=_fake_supabase, exec_postgrest=MagicMock())
    _stub("src.infra", supabase_client=sys.modules["src.infra.supabase_client"])

    # src.core.cnpj_norm
    _stub("src.core.cnpj_norm", normalize_cnpj=lambda x: x)

    # src.core.db_manager
    _stub(
        "src.core.db_manager",
        find_cliente_by_cnpj_norm=MagicMock(return_value=None),
        get_cliente_by_id=MagicMock(return_value=None),
        list_clientes_deletados=MagicMock(return_value=[]),
    )

    # src.core.services.clientes_service
    _fake_legacy = MagicMock()
    _fake_legacy.count_clients = MagicMock(return_value=0)
    _fake_legacy.checar_duplicatas_info = MagicMock(return_value={})
    _fake_legacy.salvar_cliente = MagicMock()
    _stub("src.core.services.clientes_service", **{
        "count_clients": _fake_legacy.count_clients,
        "checar_duplicatas_info": _fake_legacy.checar_duplicatas_info,
        "salvar_cliente": _fake_legacy.salvar_cliente,
    })
    _fake_core_services = types.ModuleType("src.core.services")
    _fake_core_services.clientes_service = sys.modules["src.core.services.clientes_service"]
    sys.modules.setdefault("src.core.services", _fake_core_services)

    # src.modules.clientes.core.constants
    import re
    _stub("src.modules.clientes.core.constants", STATUS_PREFIX_RE=re.compile(r""))
    _stub("src.modules.clientes.core", constants=sys.modules["src.modules.clientes.core.constants"])
    _stub("src.modules.clientes", core=sys.modules.get("src.modules.clientes.core"))
    _stub("src.modules", clientes=sys.modules.get("src.modules.clientes"))
    _stub("src", modules=sys.modules.get("src.modules"),
          core=sys.modules.get("src.core"),
          infra=sys.modules.get("src.infra"),
          adapters=sys.modules.get("src.adapters"),
    )


_install_stubs()

# Após stubs, importa o módulo alvo
import importlib
import importlib.util

_spec = importlib.util.spec_from_file_location(
    "src.modules.clientes.core.service",
    r"c:\Users\Pichau\Desktop\v1.5.73\src\modules\clientes\core\service.py",
)
_svc_mod = importlib.util.module_from_spec(_spec)
sys.modules["src.modules.clientes.core.service"] = _svc_mod
_spec.loader.exec_module(_svc_mod)  # type: ignore[union-attr]

from typing import Any, cast
svc = cast(Any, _svc_mod)


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
