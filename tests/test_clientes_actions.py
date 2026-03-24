# -*- coding: utf-8 -*-
"""Testes diretos para src/modules/clientes/ui/actions.py.

Cobre as funções de fluxo de ação (execute_soft_delete, execute_hard_delete,
execute_restore) sem dependência de Tkinter real — todos os colaboradores
são injetados via parâmetros (design "testável por construção").

C2 — complemento da fase de refatoração do módulo clientes.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from src.modules.clientes.ui.actions import (
    execute_hard_delete,
    execute_restore,
    execute_soft_delete,
)


# ---------------------------------------------------------------------------
# Helpers reutilizáveis
# ---------------------------------------------------------------------------


def _make_service():
    """Stub mínimo de ClintesService."""
    svc = MagicMock()
    svc.excluir_clientes_definitivamente.return_value = (True, [])  # (ok, erros)
    return svc


def _ask_confirm(top, title, msg, **kw):
    """ask_fn que sempre confirma."""
    return True


def _ask_cancel(top, title, msg, **kw):
    """ask_fn que sempre cancela."""
    return False


# ---------------------------------------------------------------------------
# execute_soft_delete
# ---------------------------------------------------------------------------


class TestExecuteSoftDelete:
    """Testes para execute_soft_delete."""

    def _base_kwargs(self, *, confirm=True, service=None):
        """Monta kwargs padrão para execute_soft_delete."""
        return dict(
            client_id=42,
            label_cli="Empresa XYZ (ID 42)",
            top=MagicMock(),
            service=service or _make_service(),
            refresh_lixeira=MagicMock(),
            on_success=MagicMock(),
            ask_fn=_ask_confirm if confirm else _ask_cancel,
            show_info_fn=MagicMock(),
            show_error_fn=MagicMock(),
        )

    def test_user_cancels_returns_false(self):
        """Se o usuário cancelar o diálogo, retorna False e NÃO chama o serviço."""
        kw = self._base_kwargs(confirm=False)
        result = execute_soft_delete(**kw)
        assert result is False
        kw["service"].mover_cliente_para_lixeira.assert_not_called()
        kw["on_success"].assert_not_called()

    def test_user_confirms_calls_service(self):
        """Se o usuário confirmar, chama mover_cliente_para_lixeira com o ID correto."""
        kw = self._base_kwargs()
        execute_soft_delete(**kw)
        kw["service"].mover_cliente_para_lixeira.assert_called_once_with(42)

    def test_user_confirms_returns_true(self):
        """Se o usuário confirmar, retorna True independente de sucesso do serviço."""
        kw = self._base_kwargs()
        result = execute_soft_delete(**kw)
        assert result is True

    def test_success_calls_refresh_and_on_success(self):
        """Após sucesso do serviço, chama refresh_lixeira e on_success."""
        kw = self._base_kwargs()
        execute_soft_delete(**kw)
        kw["refresh_lixeira"].assert_called_once()
        kw["on_success"].assert_called_once()

    def test_success_shows_info(self):
        """Após sucesso, exibe mensagem informativa."""
        kw = self._base_kwargs()
        execute_soft_delete(**kw)
        kw["show_info_fn"].assert_called_once()
        # Confirma que o título contém "Lixeira"
        info_title = kw["show_info_fn"].call_args[0][1]
        assert "Lixeira" in info_title

    def test_service_error_shows_error_not_raises(self):
        """Exceção do serviço é capturada e exibe erro; não propaga exceção."""
        svc = _make_service()
        svc.mover_cliente_para_lixeira.side_effect = RuntimeError("DB offline")
        kw = self._base_kwargs(service=svc)
        result = execute_soft_delete(**kw)
        # Ainda retorna True (confirmou), mas mostra erro
        assert result is True
        kw["show_error_fn"].assert_called_once()
        kw["on_success"].assert_not_called()
        kw["refresh_lixeira"].assert_not_called()

    def test_service_error_does_not_call_on_success(self):
        """Falha no serviço não deve acionar on_success."""
        svc = _make_service()
        svc.mover_cliente_para_lixeira.side_effect = ValueError("erro inexperado")
        kw = self._base_kwargs(service=svc)
        execute_soft_delete(**kw)
        kw["on_success"].assert_not_called()


# ---------------------------------------------------------------------------
# execute_hard_delete
# ---------------------------------------------------------------------------


class TestExecuteHardDelete:
    """Testes para execute_hard_delete."""

    def _base_kwargs(self, *, confirm=True, service=None):
        return dict(
            client_id=99,
            label_cli="Cliente Raro (ID 99)",
            top=MagicMock(),
            service=service or _make_service(),
            on_success=MagicMock(),
            ask_danger_fn=_ask_confirm if confirm else _ask_cancel,
            show_info_fn=MagicMock(),
            show_error_fn=MagicMock(),
        )

    def test_user_cancels_returns_false(self):
        """Cancelamento retorna False e não chama serviço."""
        kw = self._base_kwargs(confirm=False)
        result = execute_hard_delete(**kw)
        assert result is False
        kw["service"].excluir_clientes_definitivamente.assert_not_called()

    def test_user_confirms_calls_service_with_list(self):
        """Confirmação chama excluir_clientes_definitivamente com [client_id]."""
        kw = self._base_kwargs()
        execute_hard_delete(**kw)
        kw["service"].excluir_clientes_definitivamente.assert_called_once_with([99])

    def test_success_returns_true(self):
        """Sucesso retorna True."""
        kw = self._base_kwargs()
        result = execute_hard_delete(**kw)
        assert result is True

    def test_success_calls_on_success(self):
        """Sucesso chama on_success."""
        kw = self._base_kwargs()
        execute_hard_delete(**kw)
        kw["on_success"].assert_called_once()

    def test_success_shows_info(self):
        """Sucesso exibe mensagem informativa."""
        kw = self._base_kwargs()
        execute_hard_delete(**kw)
        kw["show_info_fn"].assert_called_once()

    def test_service_returns_errors_shows_error(self):
        """Se o serviço retornar erros parciais, exibe mensagem de erro."""
        svc = _make_service()
        svc.excluir_clientes_definitivamente.return_value = (False, [(99, "FK constraint")])
        kw = self._base_kwargs(service=svc)
        result = execute_hard_delete(**kw)
        # Retorna True (confirmou), mas mostrou erro
        assert result is True
        kw["show_error_fn"].assert_called_once()
        kw["on_success"].assert_not_called()

    def test_service_exception_shows_error_not_raises(self):
        """Exceção do serviço é capturada; não propaga."""
        svc = _make_service()
        svc.excluir_clientes_definitivamente.side_effect = ConnectionError("timeout")
        kw = self._base_kwargs(service=svc)
        result = execute_hard_delete(**kw)
        assert result is True
        kw["show_error_fn"].assert_called_once()
        kw["on_success"].assert_not_called()

    def test_no_errors_does_not_call_show_error(self):
        """Caminho feliz não chama show_error_fn."""
        kw = self._base_kwargs()
        execute_hard_delete(**kw)
        kw["show_error_fn"].assert_not_called()


# ---------------------------------------------------------------------------
# execute_restore
# ---------------------------------------------------------------------------


class TestExecuteRestore:
    """Testes para execute_restore."""

    def _base_kwargs(self, *, confirm=True, service=None):
        return dict(
            client_id=7,
            label_cli="Cliente Restaurado (ID 7)",
            top=MagicMock(),
            service=service or _make_service(),
            on_success=MagicMock(),
            ask_fn=_ask_confirm if confirm else _ask_cancel,
            show_info_fn=MagicMock(),
            show_error_fn=MagicMock(),
        )

    def test_user_cancels_returns_false(self):
        """Cancelamento retorna False e não chama serviço."""
        kw = self._base_kwargs(confirm=False)
        result = execute_restore(**kw)
        assert result is False
        kw["service"].restaurar_clientes_da_lixeira.assert_not_called()

    def test_user_confirms_calls_service_with_list(self):
        """Confirmação chama restaurar_clientes_da_lixeira com [client_id]."""
        kw = self._base_kwargs()
        execute_restore(**kw)
        kw["service"].restaurar_clientes_da_lixeira.assert_called_once_with([7])

    def test_success_returns_true(self):
        """Sucesso retorna True."""
        kw = self._base_kwargs()
        result = execute_restore(**kw)
        assert result is True

    def test_success_calls_on_success(self):
        """Sucesso chama on_success."""
        kw = self._base_kwargs()
        execute_restore(**kw)
        kw["on_success"].assert_called_once()

    def test_success_shows_info(self):
        """Sucesso exibe mensagem informativa."""
        kw = self._base_kwargs()
        execute_restore(**kw)
        kw["show_info_fn"].assert_called_once()
        title = kw["show_info_fn"].call_args[0][1]
        assert "Restaurado" in title

    def test_service_exception_shows_error_not_raises(self):
        """Exceção do serviço capturada; não propaga."""
        svc = _make_service()
        svc.restaurar_clientes_da_lixeira.side_effect = RuntimeError("erro DB")
        kw = self._base_kwargs(service=svc)
        result = execute_restore(**kw)
        assert result is True
        kw["show_error_fn"].assert_called_once()
        kw["on_success"].assert_not_called()

    def test_service_exception_does_not_call_on_success(self):
        """Falha no serviço não aciona on_success."""
        svc = _make_service()
        svc.restaurar_clientes_da_lixeira.side_effect = ValueError("forbidden")
        kw = self._base_kwargs(service=svc)
        execute_restore(**kw)
        kw["on_success"].assert_not_called()
