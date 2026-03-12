# pyright: reportAttributeAccessIssue=false
# -*- coding: utf-8 -*-
"""
Testes de regressão — P1 fixes (FASE 2 estabilização clientes).

P1-1: numero_conflicts em checar_duplicatas_info deve ser populado quando há match.
P1-2: _validate_fields aceita razao-only ou cnpj-only (não exige ambos).
P1-3: falha parcial em contatos/bloco_notas gera _save_warnings.
P1-4: app_core.py não importa get_cliente_by_id no top-level.
"""

from __future__ import annotations

import ast
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
# Paths
# ---------------------------------------------------------------------------

_ROOT = Path(__file__).resolve().parent.parent
_CORE_SVC_MOD_NAME = "src.core.services.clientes_service"
_CORE_SVC_MOD_PATH = str(_ROOT / "src" / "core" / "services" / "clientes_service.py")
_APP_CORE_MOD_PATH = str(_ROOT / "src" / "core" / "app_core.py")
_EDITOR_MIXIN_PATH = str(_ROOT / "src" / "modules" / "clientes" / "ui" / "views" / "_editor_data_mixin.py")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mk(name: str, **attrs: Any) -> types.ModuleType:
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


# ---------------------------------------------------------------------------
# Stubs para carregar clientes_service.py (core) sem Tk/Supabase reais
# ---------------------------------------------------------------------------


def _build_core_svc_stubs(
    *,
    cloud_only: bool = False,
    list_clientes_data: list[Any] | None = None,
) -> dict[str, types.ModuleType]:
    """Stubs para src.core.services.clientes_service com funções puras reais."""

    # Funções puras reais (sem dependências externas)
    def _normalize_text(s: Any) -> str:
        return (s or "").strip()

    def _only_phone_digits(v: Any) -> str:
        if not v:
            return ""
        return re.sub(r"\D", "", str(v))

    def _only_digits(v: Any) -> str:
        if not v:
            return ""
        return re.sub(r"\D", "", str(v))

    def _normalize_cnpj(v: Any) -> str:
        if not v:
            return ""
        return re.sub(r"\D", "", str(v))

    mock_list_clientes = MagicMock(return_value=list_clientes_data or [])

    return {
        "src": _mk("src"),
        "src.infra": _mk("src.infra"),
        "src.infra.supabase_client": _mk(
            "src.infra.supabase_client",
            exec_postgrest=MagicMock(),
            supabase=MagicMock(),
        ),
        "src.core": _mk("src.core"),
        "src.core.services": _mk("src.core.services"),
        "src.core.app_utils": _mk("src.core.app_utils", safe_base_from_fields=MagicMock()),
        "src.config": _mk("src.config"),
        "src.config.paths": _mk("src.config.paths", CLOUD_ONLY=cloud_only, DOCS_DIR="/tmp"),
        "src.core.db_manager": _mk(
            "src.core.db_manager",
            find_cliente_by_cnpj_norm=MagicMock(return_value=None),
            list_clientes=mock_list_clientes,
            insert_cliente=MagicMock(return_value=1),
            update_cliente=MagicMock(),
        ),
        "src.core.logs": _mk("src.core.logs"),
        "src.core.logs.audit": _mk("src.core.logs.audit", log_client_action=MagicMock()),
        "src.core.session": _mk("src.core.session"),
        "src.core.session.session": _mk(
            "src.core.session.session",
            get_current_user=MagicMock(return_value=None),
        ),
        "src.utils": _mk("src.utils"),
        "src.utils.file_utils": _mk("src.utils.file_utils"),
        "src.utils.validators": _mk("src.utils.validators", normalize_text=_normalize_text),
        "src.utils.formatters": _mk("src.utils.formatters", format_cnpj=lambda v: v or ""),
        "src.utils.phone_utils": _mk(
            "src.utils.phone_utils",
            format_phone_br=lambda v: v or "",
            only_phone_digits=_only_phone_digits,
        ),
        "src.core.cnpj_norm": _mk(
            "src.core.cnpj_norm",
            normalize_cnpj=_normalize_cnpj,
        ),
        "src.core.string_utils": _mk("src.core.string_utils", only_digits=_only_digits),
    }


def _load_core_svc(**stubs_kwargs: Any) -> Any:
    """Carrega clientes_service.py com stubs e retorna o módulo.

    Mantém stubs registrados em sys.modules (necessário para @dataclass resolver __module__).
    O teste deve limpar depois se necessário.
    """
    stubs = _build_core_svc_stubs(**stubs_kwargs)
    patcher = patch.dict(sys.modules, stubs)
    patcher.start()

    spec = importlib.util.spec_from_file_location(_CORE_SVC_MOD_NAME, _CORE_SVC_MOD_PATH)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules[_CORE_SVC_MOD_NAME] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]

    # Parar patcher após carregar mas manter o módulo alvo
    patcher.stop()
    return cast(Any, mod)


# ===========================================================================
# P1-1: numero_conflicts deve ser populado quando há match por telefone
# ===========================================================================


class TestP11NumeroConflicts(unittest.TestCase):
    """checar_duplicatas_info deve retornar numero_conflicts quando telefones batem."""

    def _make_fake_client(self, cid: int, numero: str, razao: str = "", cnpj: str = "") -> Any:
        ns = types.SimpleNamespace(
            id=cid,
            razao_social=razao,
            cnpj=cnpj,
            cnpj_norm=re.sub(r"\D", "", cnpj) if cnpj else "",
            numero=numero,
            nome="",
            obs="",
            ultima_alteracao="",
        )
        return ns

    def test_matching_phone_returns_conflict(self):
        """Telefone idêntico (digits-only) deve gerar numero_conflicts."""
        existing = self._make_fake_client(10, "+55 11 98765-4321", "Acme Ltda")
        svc = _load_core_svc(cloud_only=False, list_clientes_data=[existing])

        result = svc.checar_duplicatas_info(
            numero="11987654321",
            cnpj="",
            nome="",
            razao="",
        )
        conflicts = result.get("numero_conflicts", [])
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].id, 10)

    def test_different_phone_returns_empty(self):
        """Telefone diferente não gera conflito."""
        existing = self._make_fake_client(10, "+55 11 98765-4321")
        svc = _load_core_svc(cloud_only=False, list_clientes_data=[existing])

        result = svc.checar_duplicatas_info(
            numero="21999999999",
            cnpj="",
            nome="",
            razao="",
        )
        conflicts = result.get("numero_conflicts", [])
        self.assertEqual(len(conflicts), 0)

    def test_empty_numero_returns_empty(self):
        """Telefone vazio não dispara busca."""
        existing = self._make_fake_client(10, "+55 11 98765-4321")
        svc = _load_core_svc(cloud_only=False, list_clientes_data=[existing])

        result = svc.checar_duplicatas_info(
            numero="",
            cnpj="",
            nome="",
            razao="",
        )
        conflicts = result.get("numero_conflicts", [])
        self.assertEqual(len(conflicts), 0)

    def test_short_numero_skipped(self):
        """Telefone com menos de 10 dígitos não dispara busca."""
        existing = self._make_fake_client(10, "12345")
        svc = _load_core_svc(cloud_only=False, list_clientes_data=[existing])

        result = svc.checar_duplicatas_info(
            numero="12345",
            cnpj="",
            nome="",
            razao="",
        )
        conflicts = result.get("numero_conflicts", [])
        self.assertEqual(len(conflicts), 0)

    def test_exclude_id_skips_self(self):
        """exclude_id deve excluir o próprio cliente do resultado."""
        existing = self._make_fake_client(10, "+55 11 98765-4321")
        svc = _load_core_svc(cloud_only=False, list_clientes_data=[existing])

        result = svc.checar_duplicatas_info(
            numero="11987654321",
            cnpj="",
            nome="",
            razao="",
            exclude_id=10,
        )
        conflicts = result.get("numero_conflicts", [])
        self.assertEqual(len(conflicts), 0)


# ===========================================================================
# P1-2: _validate_fields aceita razão-only ou cnpj-only
# ===========================================================================


class TestP12ValidationAlignment(unittest.TestCase):
    """Editor deve exigir ao menos Razão Social OU CNPJ (não ambos)."""

    def test_validate_fields_source_accepts_razao_only(self):
        """Inspeção AST: _validate_fields NÃO deve ter 'Razão Social é obrigatória'."""
        source = Path(_EDITOR_MIXIN_PATH).read_text(encoding="utf-8")
        self.assertNotIn(
            "Razão Social é obrigatória",
            source,
            "Regra antiga 'Razão Social é obrigatória' não deve existir mais",
        )

    def test_validate_fields_source_accepts_cnpj_only(self):
        """Inspeção AST: _validate_fields NÃO deve ter 'CNPJ é obrigatório'."""
        source = Path(_EDITOR_MIXIN_PATH).read_text(encoding="utf-8")
        self.assertNotIn(
            "CNPJ é obrigatório",
            source,
            "Regra antiga 'CNPJ é obrigatório' não deve existir mais",
        )

    def test_validate_fields_requires_at_least_one(self):
        """Inspeção: _validate_fields deve exigir ao menos razão ou cnpj."""
        source = Path(_EDITOR_MIXIN_PATH).read_text(encoding="utf-8")
        self.assertIn(
            "ao menos",
            source,
            "Deve haver mensagem 'ao menos Razão Social ou CNPJ'",
        )


# ===========================================================================
# P1-3: falha parcial em contatos/bloco_notas gera _save_warnings
# ===========================================================================


class TestP13PartialSaveWarning(unittest.TestCase):
    """Erros em contatos/bloco_notas devem ser registrados em _save_warnings."""

    def test_save_contatos_error_appends_warning(self):
        """Inspeção: _on_error em _save_contatos_to_db deve usar _save_warnings."""
        source = Path(_EDITOR_MIXIN_PATH).read_text(encoding="utf-8")
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_save_contatos_to_db":
                body_src = ast.get_source_segment(source, node)
                assert body_src is not None
                self.assertIn("_save_warnings", body_src, "_save_contatos_to_db deve registrar falha em _save_warnings")
                return
        self.fail("Função _save_contatos_to_db não encontrada")

    def test_save_bloco_notas_error_appends_warning(self):
        """Inspeção: _on_error em _save_bloco_notas_to_db deve usar _save_warnings."""
        source = Path(_EDITOR_MIXIN_PATH).read_text(encoding="utf-8")
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_save_bloco_notas_to_db":
                body_src = ast.get_source_segment(source, node)
                assert body_src is not None
                self.assertIn(
                    "_save_warnings", body_src, "_save_bloco_notas_to_db deve registrar falha em _save_warnings"
                )
                return
        self.fail("Função _save_bloco_notas_to_db não encontrada")

    def test_finish_save_checks_warnings(self):
        """Inspeção: _on_save_clicked deve checar _save_warnings antes de fechar."""
        source = Path(_EDITOR_MIXIN_PATH).read_text(encoding="utf-8")
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_on_save_clicked":
                body_src = ast.get_source_segment(source, node)
                assert body_src is not None
                self.assertIn("_save_warnings", body_src, "_on_save_clicked deve inicializar e checar _save_warnings")
                self.assertIn(
                    "Salvo com ressalvas",
                    body_src,
                    "_on_save_clicked deve mostrar 'Salvo com ressalvas' quando há avisos",
                )
                return
        self.fail("Função _on_save_clicked não encontrada")


# ===========================================================================
# P1-4: app_core.py não importa get_cliente_by_id no top-level
# ===========================================================================


class TestP14NoTopLevelGetClienteImport(unittest.TestCase):
    """app_core.py não deve ter import top-level de get_cliente_by_id."""

    def test_no_top_level_import_get_cliente_by_id(self):
        """Imports top-level não devem incluir get_cliente_by_id."""
        source = Path(_APP_CORE_MOD_PATH).read_text(encoding="utf-8")
        tree = ast.parse(source)

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    name = alias.name
                    self.assertNotEqual(
                        name,
                        "get_cliente_by_id",
                        f"Import top-level de get_cliente_by_id encontrado na linha {node.lineno}. "
                        "Deve ser import local dentro da função que usa.",
                    )

    def test_resolve_cliente_row_removed(self):
        """_resolve_cliente_row (dead code) deve ter sido removido em P3."""
        source = Path(_APP_CORE_MOD_PATH).read_text(encoding="utf-8")
        self.assertNotIn(
            "def _resolve_cliente_row", source, "_resolve_cliente_row deveria ter sido removido (sem callers)"
        )


if __name__ == "__main__":
    unittest.main()
