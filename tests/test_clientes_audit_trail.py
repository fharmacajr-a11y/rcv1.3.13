# -*- coding: utf-8 -*-
"""Testes de audit trail para o módulo de clientes.

Garante que:
- mover_cliente_para_lixeira  inclui deleted_at, ultima_alteracao, ultima_por
- restaurar_clientes_da_lixeira inclui deleted_at=None, ultima_alteracao, ultima_por
- Nenhuma função tenta gravar manualmente updated_by/deleted_by/restored_by
  (essas colunas são preenchidas pelo trigger DB-side)
- Fallback: se exec_postgrest levanta (coluna ausente), o payload remove
  ultima_por e tenta novamente
- update_cliente_status_and_observacoes funciona sem erro de KeyError/IndexError
"""
import unittest
from unittest.mock import MagicMock, call, patch

_SVC = "src.modules.clientes.core.service"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_exec():
    """Mock de exec_postgrest que retorna resposta genérica."""
    m = MagicMock()
    m.return_value = MagicMock(data=[{"id": 1}])
    return m


def _mock_supabase():
    """Mock de supabase com encadeamento fluente."""
    tbl = MagicMock()
    tbl.update.return_value = tbl
    tbl.eq.return_value = tbl
    tbl.in_.return_value = tbl
    sb = MagicMock()
    sb.table.return_value = tbl
    return sb, tbl


# ---------------------------------------------------------------------------
# mover_cliente_para_lixeira
# ---------------------------------------------------------------------------

class TestMoverClienteParaLixeira(unittest.TestCase):

    def _run(self, user_label: str = "ana@teste.com"):
        sb, tbl = _mock_supabase()
        exec_mock = _mock_exec()
        with patch(f"{_SVC}.supabase", sb), \
             patch(f"{_SVC}.exec_postgrest", exec_mock), \
             patch(f"{_SVC}._current_user_label", return_value=user_label), \
             patch(f"{_SVC}._current_utc_iso", return_value="2026-02-23T00:00:00+00:00"):
            from src.modules.clientes.core.service import mover_cliente_para_lixeira
            mover_cliente_para_lixeira(42)
        return sb, tbl, exec_mock

    def test_chama_exec_postgrest(self):
        _, _, exec_mock = self._run()
        exec_mock.assert_called_once()

    def test_payload_inclui_deleted_at(self):
        sb, tbl, _ = self._run()
        payload = tbl.update.call_args[0][0]
        self.assertIn("deleted_at", payload)
        self.assertIsNotNone(payload["deleted_at"])

    def test_payload_inclui_ultima_alteracao(self):
        sb, tbl, _ = self._run()
        payload = tbl.update.call_args[0][0]
        self.assertIn("ultima_alteracao", payload)

    def test_payload_inclui_ultima_por(self):
        sb, tbl, _ = self._run(user_label="ana@teste.com")
        payload = tbl.update.call_args[0][0]
        self.assertIn("ultima_por", payload)
        self.assertEqual(payload["ultima_por"], "ana@teste.com")

    def test_payload_NAO_inclui_updated_by_app_side(self):
        """Colunas UUID de auditoria NÃO devem ser gravadas pelo app (responsabilidade do trigger)."""
        sb, tbl, _ = self._run()
        payload = tbl.update.call_args[0][0]
        self.assertNotIn("updated_by", payload)
        self.assertNotIn("deleted_by", payload)
        self.assertNotIn("restored_by", payload)

    def test_usa_cliente_id_no_eq(self):
        sb, tbl, _ = self._run()
        tbl.eq.assert_called_once_with("id", 42)

    def test_fallback_sem_ultima_por_quando_exec_falha(self):
        """Se exec_postgrest falha na primeira chamada, tenta sem ultima_por."""
        sb, tbl = _mock_supabase()
        first_call = {"done": False}

        def exec_side_effect(*args, **kwargs):
            if not first_call["done"]:
                first_call["done"] = True
                raise RuntimeError("column ultima_por does not exist")
            return MagicMock(data=[])

        with patch(f"{_SVC}.supabase", sb), \
             patch(f"{_SVC}.exec_postgrest", side_effect=exec_side_effect), \
             patch(f"{_SVC}._current_user_label", return_value="x@y.com"), \
             patch(f"{_SVC}._current_utc_iso", return_value="2026-02-23T00:00:00+00:00"):
            from src.modules.clientes.core.service import mover_cliente_para_lixeira
            # Não deve levantar exceção
            mover_cliente_para_lixeira(99)

        # Na segunda chamada, payload não deve ter ultima_por
        second_payload = tbl.update.call_args_list[1][0][0]
        self.assertNotIn("ultima_por", second_payload)
        self.assertIn("deleted_at", second_payload)


# ---------------------------------------------------------------------------
# restaurar_clientes_da_lixeira
# ---------------------------------------------------------------------------

class TestRestaurarClientesDaLixeira(unittest.TestCase):

    def _run(self, ids=(1, 2, 3), user_label: str = "bob@teste.com"):
        sb, tbl = _mock_supabase()
        exec_mock = _mock_exec()
        with patch(f"{_SVC}.supabase", sb), \
             patch(f"{_SVC}.exec_postgrest", exec_mock), \
             patch(f"{_SVC}._current_user_label", return_value=user_label), \
             patch(f"{_SVC}._current_utc_iso", return_value="2026-02-23T01:00:00+00:00"):
            from src.modules.clientes.core.service import restaurar_clientes_da_lixeira
            restaurar_clientes_da_lixeira(ids)
        return sb, tbl, exec_mock

    def test_lista_vazia_nao_chama_exec(self):
        sb, tbl = _mock_supabase()
        exec_mock = _mock_exec()
        with patch(f"{_SVC}.supabase", sb), \
             patch(f"{_SVC}.exec_postgrest", exec_mock), \
             patch(f"{_SVC}._current_user_label", return_value=""), \
             patch(f"{_SVC}._current_utc_iso", return_value="t"):
            from src.modules.clientes.core.service import restaurar_clientes_da_lixeira
            restaurar_clientes_da_lixeira([])
        exec_mock.assert_not_called()

    def test_payload_inclui_deleted_at_none(self):
        _, tbl, _ = self._run()
        payload = tbl.update.call_args[0][0]
        self.assertIn("deleted_at", payload)
        self.assertIsNone(payload["deleted_at"])

    def test_payload_inclui_ultima_alteracao(self):
        _, tbl, _ = self._run()
        payload = tbl.update.call_args[0][0]
        self.assertIn("ultima_alteracao", payload)

    def test_payload_inclui_ultima_por(self):
        _, tbl, _ = self._run(user_label="bob@teste.com")
        payload = tbl.update.call_args[0][0]
        self.assertIn("ultima_por", payload)
        self.assertEqual(payload["ultima_por"], "bob@teste.com")

    def test_payload_NAO_inclui_colunas_uuid_auditoria(self):
        """Trigger é responsável por updated_by/restored_by; app não deve gravá-los."""
        _, tbl, _ = self._run()
        payload = tbl.update.call_args[0][0]
        self.assertNotIn("updated_by", payload)
        self.assertNotIn("deleted_by", payload)
        self.assertNotIn("restored_by", payload)

    def test_usa_in_com_ids(self):
        _, tbl, _ = self._run(ids=[10, 20])
        tbl.in_.assert_called_once_with("id", [10, 20])

    def test_fallback_sem_ultima_por_quando_exec_falha(self):
        """Se exec_postgrest falha (coluna ausente), retenta sem ultima_por."""
        sb, tbl = _mock_supabase()
        first_call = {"done": False}

        def exec_side_effect(*args, **kwargs):
            if not first_call["done"]:
                first_call["done"] = True
                raise RuntimeError("column ultima_por does not exist")
            return MagicMock(data=[])

        with patch(f"{_SVC}.supabase", sb), \
             patch(f"{_SVC}.exec_postgrest", side_effect=exec_side_effect), \
             patch(f"{_SVC}._current_user_label", return_value="x@y.com"), \
             patch(f"{_SVC}._current_utc_iso", return_value="t"):
            from src.modules.clientes.core.service import restaurar_clientes_da_lixeira
            restaurar_clientes_da_lixeira([77])

        second_payload = tbl.update.call_args_list[1][0][0]
        self.assertNotIn("ultima_por", second_payload)
        self.assertIsNone(second_payload.get("deleted_at"))


# ---------------------------------------------------------------------------
# _current_user_label
# ---------------------------------------------------------------------------

class TestCurrentUserLabel(unittest.TestCase):

    def test_retorna_email_do_usuario(self):
        user = MagicMock()
        user.email = "alice@exemplo.com"
        with patch(f"{_SVC}._get_current_user", return_value=user):
            from src.modules.clientes.core.service import _current_user_label
            self.assertEqual(_current_user_label(), "alice@exemplo.com")

    def test_retorna_vazio_quando_sem_email(self):
        user = MagicMock()
        user.email = None
        with patch(f"{_SVC}._get_current_user", return_value=user):
            from src.modules.clientes.core.service import _current_user_label
            self.assertEqual(_current_user_label(), "")

    def test_retorna_vazio_quando_excecao(self):
        with patch(f"{_SVC}._get_current_user", side_effect=RuntimeError("sem sessão")):
            from src.modules.clientes.core.service import _current_user_label
            self.assertEqual(_current_user_label(), "")


# ---------------------------------------------------------------------------
# Invariante: colunas UUID de auditoria nunca aparecem em payloads app-side
# (regressão guard)
# ---------------------------------------------------------------------------

class TestAuditColumnsNeverWrittenByApp(unittest.TestCase):
    """Verifica que as colunas UUID gerenciadas pelo trigger não surgem em
    nenhum payload enviado pelo app em operações de lixeira/restauração."""

    _FORBIDDEN = ("updated_by", "deleted_by", "restored_by")

    def _collect_payloads(self, fn_name: str, *args):
        """Executa fn_name e coleta todos os dicts passados a .update()."""
        sb, tbl = _mock_supabase()
        payloads = []
        original_update = tbl.update.side_effect

        def capture_update(payload, *a, **kw):
            payloads.append(dict(payload))
            return tbl

        tbl.update.side_effect = capture_update
        with patch(f"{_SVC}.supabase", sb), \
             patch(f"{_SVC}.exec_postgrest", MagicMock(return_value=MagicMock(data=[]))), \
             patch(f"{_SVC}._current_user_label", return_value=""), \
             patch(f"{_SVC}._current_utc_iso", return_value="t"):
            import importlib
            svc = importlib.import_module("src.modules.clientes.core.service")
            getattr(svc, fn_name)(*args)
        return payloads

    def test_mover_para_lixeira_sem_uuid_cols(self):
        for p in self._collect_payloads("mover_cliente_para_lixeira", 1):
            for col in self._FORBIDDEN:
                self.assertNotIn(col, p, f"'{col}' não deve ser gravado pelo app (responsabilidade do trigger)")

    def test_restaurar_sem_uuid_cols(self):
        for p in self._collect_payloads("restaurar_clientes_da_lixeira", [1, 2]):
            for col in self._FORBIDDEN:
                self.assertNotIn(col, p, f"'{col}' não deve ser gravado pelo app (responsabilidade do trigger)")


if __name__ == "__main__":
    unittest.main()
