# -*- coding: utf-8 -*-
"""Testes de consistência storage × banco para deleção de clientes.

Garante que a remoção do registro no banco NUNCA ocorre quando a
remoção de arquivos no storage falha, prevenindo arquivos órfãos.
"""

import unittest
from unittest.mock import MagicMock, patch

from src.modules.clientes.core.service import (
    ClienteStorageRemovalError,
    excluir_clientes_definitivamente,
)

# Caminho do módulo a ser patcheado
_MOD = "src.modules.clientes.core.service"


def _make_ctx_mock() -> MagicMock:
    """Cria mock de context manager (usando_storage_backend)."""
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=None)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx


class TestExcluirClientesStorageConsistency(unittest.TestCase):
    """Verifica que storage × banco são exclusões atômicas (storage primeiro)."""

    def _patches(self, storage_side_effect=None, storage_return=None):
        """Retorna dict com todos os patches necessários."""
        return {
            "org": patch(f"{_MOD}._resolve_current_org_id", return_value="org-test-123"),
            "adapter": patch(f"{_MOD}.SupabaseStorageAdapter"),
            "ctx": patch(f"{_MOD}.using_storage_backend"),
            "storage": patch(
                f"{_MOD}._remove_cliente_storage",
                side_effect=storage_side_effect,
                return_value=storage_return,
            ),
            "exec_pg": patch(f"{_MOD}.exec_postgrest"),
        }

    # ------------------------------------------------------------------
    # Cenário 1: storage falha → banco NÃO deve ser chamado
    # ------------------------------------------------------------------

    def test_banco_nao_chamado_quando_storage_falha(self):
        """Se _remove_cliente_storage levanta, exec_postgrest NÃO deve ser invocado."""
        patches = self._patches(storage_side_effect=ClienteStorageRemovalError("erro simulado"))
        with (
            patches["org"],
            patches["adapter"],
            patches["ctx"] as mock_ctx,
            patches["storage"] as mock_storage,
            patches["exec_pg"] as mock_exec,
        ):
            mock_ctx.return_value = _make_ctx_mock()

            ok, errs = excluir_clientes_definitivamente([42])

        mock_storage.assert_called_once_with("rc-docs", "org-test-123", 42)
        mock_exec.assert_not_called()
        self.assertEqual(ok, 0)
        self.assertEqual(len(errs), 1)
        self.assertEqual(errs[0][0], 42)
        self.assertIn("exclusao cancelada", errs[0][1].lower())

    def test_banco_nao_chamado_para_cada_id_com_falha_de_storage(self):
        """Cada ID com storage falhando não deve gerar deleção no banco."""
        patches = self._patches(storage_side_effect=ClienteStorageRemovalError("falha"))
        with (
            patches["org"],
            patches["adapter"],
            patches["ctx"] as mock_ctx,
            patches["storage"],
            patches["exec_pg"] as mock_exec,
        ):
            mock_ctx.return_value = _make_ctx_mock()

            ok, errs = excluir_clientes_definitivamente([1, 2, 3])

        mock_exec.assert_not_called()
        self.assertEqual(ok, 0)
        self.assertEqual(len(errs), 3)

    # ------------------------------------------------------------------
    # Cenário 2: storage ok → banco DEVE ser chamado
    # ------------------------------------------------------------------

    def test_banco_chamado_quando_storage_ok(self):
        """Se _remove_cliente_storage é bem-sucedido, exec_postgrest deve ser invocado."""
        patches = self._patches(storage_return=None)
        with (
            patches["org"],
            patches["adapter"],
            patches["ctx"] as mock_ctx,
            patches["storage"] as mock_storage,
            patches["exec_pg"] as mock_exec,
        ):
            mock_ctx.return_value = _make_ctx_mock()
            mock_exec.return_value = MagicMock()

            ok, errs = excluir_clientes_definitivamente([99])

        mock_storage.assert_called_once_with("rc-docs", "org-test-123", 99)
        mock_exec.assert_called_once()
        self.assertEqual(ok, 1)
        self.assertEqual(errs, [])

    def test_banco_chamado_para_cada_id_com_storage_ok(self):
        """Múltiplos IDs com storage ok devem gerar uma deleção no banco cada."""
        patches = self._patches(storage_return=None)
        with (
            patches["org"],
            patches["adapter"],
            patches["ctx"] as mock_ctx,
            patches["storage"],
            patches["exec_pg"] as mock_exec,
        ):
            mock_ctx.return_value = _make_ctx_mock()
            mock_exec.return_value = MagicMock()

            ok, errs = excluir_clientes_definitivamente([10, 20, 30])

        self.assertEqual(mock_exec.call_count, 3)
        self.assertEqual(ok, 3)
        self.assertEqual(errs, [])

    def test_lista_vazia_nao_chama_nada(self):
        """Lista vazia de IDs não deve chamar storage nem banco."""
        patches = self._patches()
        with (
            patches["org"],
            patches["adapter"],
            patches["ctx"] as mock_ctx,
            patches["storage"] as mock_storage,
            patches["exec_pg"] as mock_exec,
        ):
            mock_ctx.return_value = _make_ctx_mock()

            ok, errs = excluir_clientes_definitivamente([])

        mock_storage.assert_not_called()
        mock_exec.assert_not_called()
        self.assertEqual(ok, 0)
        self.assertEqual(errs, [])

    # ------------------------------------------------------------------
    # Cenário 3: mix — alguns storage ok, outros falham
    # ------------------------------------------------------------------

    def test_mix_storage_ok_e_falha(self):
        """IDs com storage ok → banco chamado; IDs com falha → banco não chamado."""
        # IDs 1 e 3 ok, ID 2 falha
        call_count = {"n": 0}

        def storage_side_effect(bucket, org_id, cid_int):
            call_count["n"] += 1
            if cid_int == 2:
                raise ClienteStorageRemovalError("falha no cliente 2")

        patches = self._patches()
        with (
            patches["org"],
            patches["adapter"],
            patches["ctx"] as mock_ctx,
            patch(f"{_MOD}._remove_cliente_storage", side_effect=storage_side_effect),
            patches["exec_pg"] as mock_exec,
        ):
            mock_ctx.return_value = _make_ctx_mock()
            mock_exec.return_value = MagicMock()

            ok, errs = excluir_clientes_definitivamente([1, 2, 3])

        # banco chamado 2 vezes (IDs 1 e 3) e não para o 2
        self.assertEqual(mock_exec.call_count, 2)
        self.assertEqual(ok, 2)
        self.assertEqual(len(errs), 1)
        self.assertEqual(errs[0][0], 2)

    # ------------------------------------------------------------------
    # Cenário 4: storage ok mas banco falha
    # ------------------------------------------------------------------

    def test_banco_falha_contabilizado_no_errs(self):
        """Falha no banco (após storage ok) deve ser registrada em errs."""
        patches = self._patches(storage_return=None)
        with (
            patches["org"],
            patches["adapter"],
            patches["ctx"] as mock_ctx,
            patches["storage"],
            patches["exec_pg"] as mock_exec,
        ):
            mock_ctx.return_value = _make_ctx_mock()
            mock_exec.side_effect = RuntimeError("DB timeout")

            ok, errs = excluir_clientes_definitivamente([55])

        self.assertEqual(ok, 0)
        self.assertEqual(len(errs), 1)
        self.assertEqual(errs[0][0], 55)

    # ------------------------------------------------------------------
    # Cenário 5: callback de progresso é chamado mesmo na falha de storage
    # ------------------------------------------------------------------

    def test_progress_cb_chamado_em_falha_storage(self):
        """Callback de progresso deve ser invocado mesmo quando storage falha."""
        patches = self._patches(storage_side_effect=ClienteStorageRemovalError("err"))
        calls = []
        with patches["org"], patches["adapter"], patches["ctx"] as mock_ctx, patches["storage"], patches["exec_pg"]:
            mock_ctx.return_value = _make_ctx_mock()

            excluir_clientes_definitivamente([7], progress_cb=lambda idx, total, cid: calls.append((idx, total, cid)))

        self.assertEqual(calls, [(1, 1, 7)])


if __name__ == "__main__":
    unittest.main()
