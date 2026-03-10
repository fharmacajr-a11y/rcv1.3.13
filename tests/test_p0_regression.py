# pyright: reportAttributeAccessIssue=false
# -*- coding: utf-8 -*-
"""
Testes de regressão — P0 fixes (FASE 1 estabilização clientes).

P0-1: app_core.novo_cliente / editar_cliente devem usar ClientEditorDialog,
      não form_cliente (que levanta NotImplementedError).
P0-2: service.checar_duplicatas_para_form deve reconhecer a chave
      "Razão Social" (com ã) — antes havia "Raz?o Social" (encoding bug).
"""

from __future__ import annotations

import importlib
import importlib.util
import re
import sys
import types
import unittest
from pathlib import Path
from typing import Any, cast
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Paths dos módulos-alvo
# ---------------------------------------------------------------------------

_ROOT = Path(__file__).resolve().parent.parent
_SVC_MOD_NAME = "src.modules.clientes.core.service"
_SVC_MOD_PATH = str(_ROOT / "src" / "modules" / "clientes" / "core" / "service.py")
_APP_CORE_MOD_NAME = "src.core.app_core"
_APP_CORE_MOD_PATH = str(_ROOT / "src" / "core" / "app_core.py")


# ---------------------------------------------------------------------------
# Stubs mínimos para carregar service.py sem Tk/CTk
# ---------------------------------------------------------------------------


def _mk(name: str, **attrs: Any) -> types.ModuleType:
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


class _FakeAdapter:
    def __init__(self, **kw: Any) -> None: ...


def _build_service_stubs() -> dict[str, types.ModuleType]:
    fake_storage_api = _mk(
        "src.adapters.storage.api",
        delete_file=MagicMock(),
        list_files=MagicMock(return_value=[]),
        using_storage_backend=MagicMock(),
    )
    fake_supa_storage = _mk("src.adapters.storage.supabase_storage", SupabaseStorageAdapter=_FakeAdapter)
    fake_storage = _mk("src.adapters.storage", api=fake_storage_api, supabase_storage=fake_supa_storage)
    fake_adapters = _mk("src.adapters", storage=fake_storage)
    fake_db_schemas = _mk(
        "src.infra.db_schemas",
        MEMBERSHIPS_SELECT_ORG_ID="org_id",
        MEMBERSHIPS_SELECT_ORG_ROLE="org_id, role",
    )
    fake_supa_client = _mk("src.infra.supabase_client", supabase=MagicMock(), exec_postgrest=MagicMock())
    fake_infra = _mk("src.infra", supabase_client=fake_supa_client, db_schemas=fake_db_schemas)
    fake_cnpj = _mk("src.core.cnpj_norm", normalize_cnpj=lambda x: x)
    fake_session_mod = _mk(
        "src.core.session.session",
        get_current_user=MagicMock(return_value=None),
        CurrentUser=MagicMock(),
    )
    fake_session_pkg = _mk("src.core.session", session=fake_session_mod)
    fake_db_mgr = _mk(
        "src.core.db_manager",
        find_cliente_by_cnpj_norm=MagicMock(return_value=None),
        get_cliente_by_id=MagicMock(return_value=None),
        list_clientes_deletados=MagicMock(return_value=[]),
        update_status_only=MagicMock(),
    )
    fake_cli_svc = _mk(
        "src.core.services.clientes_service",
        count_clients=MagicMock(return_value=0),
        checar_duplicatas_info=MagicMock(return_value={}),
        salvar_cliente=MagicMock(),
    )
    fake_core_svcs = _mk("src.core.services", clientes_service=fake_cli_svc)
    fake_constants = _mk("src.modules.clientes.core.constants", STATUS_PREFIX_RE=re.compile(r""))
    fake_cli_core = _mk("src.modules.clientes.core", constants=fake_constants)
    fake_clientes = _mk("src.modules.clientes", core=fake_cli_core)
    fake_modules = _mk("src.modules", clientes=fake_clientes)

    return {
        "src.adapters.storage.api": fake_storage_api,
        "src.adapters.storage.supabase_storage": fake_supa_storage,
        "src.adapters.storage": fake_storage,
        "src.adapters": fake_adapters,
        "src.infra.db_schemas": fake_db_schemas,
        "src.infra.supabase_client": fake_supa_client,
        "src.infra": fake_infra,
        "src.core.cnpj_norm": fake_cnpj,
        "src.core.db_manager": fake_db_mgr,
        "src.core.session.session": fake_session_mod,
        "src.core.session": fake_session_pkg,
        "src.core.services.clientes_service": fake_cli_svc,
        "src.core.services": fake_core_svcs,
        "src.modules.clientes.core.constants": fake_constants,
        "src.modules.clientes.core": fake_cli_core,
        "src.modules.clientes": fake_clientes,
        "src.modules": fake_modules,
    }


# ---------------------------------------------------------------------------
# Módulo service — carregado em setUpModule
# ---------------------------------------------------------------------------

_svc_patcher: Any = None
svc: Any = None


def setUpModule() -> None:  # noqa: N802
    global _svc_patcher, svc
    _svc_patcher = patch.dict(sys.modules, _build_service_stubs())
    _svc_patcher.start()
    spec = importlib.util.spec_from_file_location(_SVC_MOD_NAME, _SVC_MOD_PATH)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules[_SVC_MOD_NAME] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    svc = cast(Any, mod)


def tearDownModule() -> None:  # noqa: N802
    global _svc_patcher, svc
    svc = None
    sys.modules.pop(_SVC_MOD_NAME, None)
    if _svc_patcher is not None:
        _svc_patcher.stop()
    _svc_patcher = None


# ===========================================================================
# P0-2: checar_duplicatas_para_form — encoding key "Razão Social"
# ===========================================================================


class TestP02RazaoSocialKeyEncoding(unittest.TestCase):
    """A chave 'Razão Social' (com ã) deve ser reconhecida corretamente."""

    def _call(self, valores: dict) -> str:
        """Extrai o valor de razao_val que seria passado a checar_duplicatas_info."""
        captured: dict[str, Any] = {}

        def _capture(**kw: Any) -> dict:
            captured.update(kw)
            return {}

        with patch.object(svc, "checar_duplicatas_info", side_effect=_capture):
            try:
                svc.checar_duplicatas_para_form(valores)
            except Exception:
                pass
        return captured.get("razao", "")

    def test_razao_social_com_til(self):
        """Chave com acento correto 'Razão Social' → deve ser capturada."""
        resultado = self._call({"Razão Social": "Acme Ltda", "CNPJ": ""})
        self.assertEqual(resultado, "Acme Ltda")

    def test_razao_social_sem_acento(self):
        """Fallback 'Razao Social' → deve funcionar."""
        resultado = self._call({"Razao Social": "Beta Corp", "CNPJ": ""})
        self.assertEqual(resultado, "Beta Corp")

    def test_razao_social_snake_case(self):
        """Fallback 'razao_social' → deve funcionar."""
        resultado = self._call({"razao_social": "Gama SA", "CNPJ": ""})
        self.assertEqual(resultado, "Gama SA")

    def test_razao_social_vazia_retorna_string_vazia(self):
        """Nenhuma chave presente → razao = ''."""
        resultado = self._call({"CNPJ": "12345678000100"})
        self.assertEqual(resultado, "")

    def test_razao_social_prioridade_acento_sobre_fallback(self):
        """Quando ambas as chaves existem, 'Razão Social' tem prioridade."""
        resultado = self._call(
            {
                "Razão Social": "Prioridade",
                "razao_social": "Fallback",
                "CNPJ": "",
            }
        )
        self.assertEqual(resultado, "Prioridade")


# ===========================================================================
# P0-1: app_core.novo_cliente / editar_cliente — usa ClientEditorDialog
# ===========================================================================


def _build_app_core_stubs(mock_dialog: Any) -> dict[str, Any]:
    """Stubs para carregar app_core.py sem Tk/CTk e com ClientEditorDialog mockado."""
    fake_editor_mod = _mk(
        "src.modules.clientes.ui.views.client_editor_dialog",
        ClientEditorDialog=mock_dialog,
    )
    fake_views = _mk("src.modules.clientes.ui.views", client_editor_dialog=fake_editor_mod)
    fake_ui = _mk("src.modules.clientes.ui", views=fake_views)
    fake_cli_core_svc = _mk(
        "src.modules.clientes.core.service",
        get_cliente_by_id=MagicMock(),
        mover_cliente_para_lixeira=MagicMock(),
    )
    fake_cli_core = _mk("src.modules.clientes.core", service=fake_cli_core_svc)
    fake_clientes = _mk("src.modules.clientes", core=fake_cli_core, ui=fake_ui)
    fake_modules = _mk("src.modules", clientes=fake_clientes)

    return {
        "src.config.paths": _mk("src.config.paths", CLOUD_ONLY=False, DOCS_DIR="/tmp"),
        "src.modules": fake_modules,
        "src.modules.clientes": fake_clientes,
        "src.modules.clientes.core": fake_cli_core,
        "src.modules.clientes.core.service": fake_cli_core_svc,
        "src.modules.clientes.ui": fake_ui,
        "src.modules.clientes.ui.views": fake_views,
        "src.modules.clientes.ui.views.client_editor_dialog": fake_editor_mod,
        "src.modules.lixeira": _mk(
            "src.modules.lixeira",
            abrir_lixeira=MagicMock(),
            refresh_if_open=MagicMock(),
        ),
    }


class TestP01AppCoreUsesEditorDialog(unittest.TestCase):
    """
    novo_cliente() e editar_cliente() devem importar ClientEditorDialog
    e NÃO chamar form_cliente (que levanta NotImplementedError).
    """

    def test_novo_cliente_imports_editor_dialog(self):
        """Verifica via inspeção de código que novo_cliente importa ClientEditorDialog."""
        import ast

        source = Path(_APP_CORE_MOD_PATH).read_text(encoding="utf-8")
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "novo_cliente":
                body_src = ast.get_source_segment(source, node)
                assert body_src is not None
                self.assertIn("ClientEditorDialog", body_src, "novo_cliente deve usar ClientEditorDialog")
                self.assertNotIn("form_cliente", body_src, "novo_cliente NÃO deve chamar form_cliente")
                return
        self.fail("Função novo_cliente não encontrada em app_core.py")

    def test_editar_cliente_imports_editor_dialog(self):
        """Verifica via inspeção de código que editar_cliente importa ClientEditorDialog."""
        import ast

        source = Path(_APP_CORE_MOD_PATH).read_text(encoding="utf-8")
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "editar_cliente":
                body_src = ast.get_source_segment(source, node)
                assert body_src is not None
                self.assertIn("ClientEditorDialog", body_src, "editar_cliente deve usar ClientEditorDialog")
                self.assertNotIn("form_cliente", body_src, "editar_cliente NÃO deve chamar form_cliente")
                return
        self.fail("Função editar_cliente não encontrada em app_core.py")

    def test_novo_cliente_does_not_raise_not_implemented(self):
        """Chamar novo_cliente com mock não deve levantar NotImplementedError."""
        mock_app = MagicMock()
        mock_dialog = MagicMock()

        stubs = _build_app_core_stubs(mock_dialog)

        with patch.dict(sys.modules, stubs):
            spec = importlib.util.spec_from_file_location(_APP_CORE_MOD_NAME, _APP_CORE_MOD_PATH)
            mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
            spec.loader.exec_module(mod)  # type: ignore[union-attr]

            # NÃO deve levantar NotImplementedError
            mod.novo_cliente(mock_app)

        mock_dialog.assert_called_once()
        _, kwargs = mock_dialog.call_args
        self.assertIsNone(kwargs.get("client_id"), "novo_cliente deve passar client_id=None")

    def test_editar_cliente_does_not_raise_not_implemented(self):
        """Chamar editar_cliente com mock não deve levantar NotImplementedError."""
        mock_app = MagicMock()
        mock_dialog = MagicMock()

        stubs = _build_app_core_stubs(mock_dialog)

        with patch.dict(sys.modules, stubs):
            spec = importlib.util.spec_from_file_location(_APP_CORE_MOD_NAME, _APP_CORE_MOD_PATH)
            mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
            spec.loader.exec_module(mod)  # type: ignore[union-attr]

            mod.editar_cliente(mock_app, 42)

        mock_dialog.assert_called_once()
        _, kwargs = mock_dialog.call_args
        self.assertEqual(kwargs.get("client_id"), 42, "editar_cliente deve passar client_id=pk")


if __name__ == "__main__":
    unittest.main()
