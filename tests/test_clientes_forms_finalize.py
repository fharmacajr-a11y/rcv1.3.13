"""Testes unitários para src/modules/clientes/forms/_finalize.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


from src.modules.clientes.forms._finalize import finalize_state
from src.modules.clientes.forms._prepare import UploadCtx


class TestFinalizeState:
    """Testes para finalize_state."""

    def test_finalize_state_returns_early_when_ctx_none(self):
        """Testa que finalize_state retorna imediatamente se _upload_ctx não existe."""
        mock_self = MagicMock()
        mock_self._upload_ctx = None

        args = (mock_self, {}, {}, [], None)
        kwargs = {}

        result_args, result_kwargs = finalize_state(*args, **kwargs)

        assert result_args == args
        assert result_kwargs == kwargs

    def test_finalize_state_returns_early_when_abort_true_and_not_finalize_ready(self):
        """Testa que finalize_state retorna imediatamente se ctx.abort=True e finalize_ready=False."""
        mock_self = MagicMock()
        mock_ctx = UploadCtx(
            app=mock_self,
            row={},
            ents={},
            arquivos_selecionados=[],
            win=None,
        )
        mock_ctx.abort = True
        mock_ctx.finalize_ready = False
        mock_self._upload_ctx = mock_ctx

        args = (mock_self, {}, {}, [], None)
        kwargs = {}

        result_args, result_kwargs = finalize_state(*args, **kwargs)

        assert result_args == args
        assert result_kwargs == kwargs

    def test_finalize_state_proceeds_when_abort_true_but_finalize_ready(self):
        """Testa que finalize_state processa se ctx.abort=True mas finalize_ready=True."""
        mock_self = MagicMock()
        mock_self.carregar = MagicMock()

        mock_win = MagicMock()
        mock_busy_dialog = MagicMock()

        mock_ctx = UploadCtx(
            app=mock_self,
            row={},
            ents={},
            arquivos_selecionados=[],
            win=mock_win,
        )
        mock_ctx.abort = True
        mock_ctx.finalize_ready = True
        mock_ctx.busy_dialog = mock_busy_dialog
        mock_ctx.falhas = 0
        mock_self._upload_ctx = mock_ctx

        args = (mock_self, {}, {}, [], mock_win)
        kwargs = {}

        with patch("src.modules.clientes.forms._finalize.messagebox.showinfo") as mock_showinfo:
            result_args, result_kwargs = finalize_state(*args, **kwargs)

            # Verificar que busy_dialog foi fechado
            mock_busy_dialog.close.assert_called_once()

            # Verificar que messagebox foi chamado
            mock_showinfo.assert_called_once()

            # Verificar que janela foi destruída
            mock_win.destroy.assert_called_once()

            # Verificar que carregar foi chamado
            mock_self.carregar.assert_called_once()

    def test_finalize_state_shows_success_message_when_no_failures(self):
        """Testa que finalize_state mostra mensagem de sucesso quando falhas=0."""
        mock_self = MagicMock()
        mock_self.carregar = MagicMock()

        mock_win = MagicMock()
        mock_busy_dialog = MagicMock()

        mock_ctx = UploadCtx(
            app=mock_self,
            row={},
            ents={},
            arquivos_selecionados=[],
            win=mock_win,
        )
        mock_ctx.abort = False
        mock_ctx.finalize_ready = True
        mock_ctx.busy_dialog = mock_busy_dialog
        mock_ctx.parent_win = None  # Para usar showinfo sem parent
        mock_ctx.falhas = 0
        mock_ctx.misc = {}
        mock_self._upload_ctx = mock_ctx

        args = (mock_self, {}, {}, [], mock_win)
        kwargs = {}

        with patch("src.modules.clientes.forms._finalize.messagebox.showinfo") as mock_showinfo:
            finalize_state(*args, **kwargs)

            # Verificar que mensagem contém "sucesso"
            mock_showinfo.assert_called_once()
            call_args = mock_showinfo.call_args
            assert "sucesso" in call_args[0][1].lower()

    def test_finalize_state_shows_failure_message_when_has_failures(self):
        """Testa que finalize_state mostra mensagem de falha quando falhas>0."""
        mock_self = MagicMock()
        mock_self.carregar = MagicMock()

        mock_win = MagicMock()
        mock_busy_dialog = MagicMock()

        mock_ctx = UploadCtx(
            app=mock_self,
            row={},
            ents={},
            arquivos_selecionados=[],
            win=mock_win,
        )
        mock_ctx.abort = False
        mock_ctx.finalize_ready = True
        mock_ctx.busy_dialog = mock_busy_dialog
        mock_ctx.parent_win = None  # Para usar showinfo sem parent
        mock_ctx.falhas = 2
        mock_ctx.misc = {}
        mock_self._upload_ctx = mock_ctx

        args = (mock_self, {}, {}, [], mock_win)
        kwargs = {}

        with patch("src.modules.clientes.forms._finalize.messagebox.showinfo") as mock_showinfo:
            finalize_state(*args, **kwargs)

            # Verificar que mensagem contém número de falhas
            mock_showinfo.assert_called_once()
            call_args = mock_showinfo.call_args
            message = call_args[0][1]
            assert "2" in message
            assert "falha" in message.lower()

    def test_finalize_state_closes_busy_dialog(self):
        """Testa que finalize_state fecha o busy_dialog."""
        mock_self = MagicMock()
        mock_self.carregar = MagicMock()

        mock_win = MagicMock()
        mock_busy_dialog = MagicMock()

        mock_ctx = UploadCtx(
            app=mock_self,
            row={},
            ents={},
            arquivos_selecionados=[],
            win=mock_win,
        )
        mock_ctx.abort = False
        mock_ctx.finalize_ready = True
        mock_ctx.busy_dialog = mock_busy_dialog
        mock_ctx.falhas = 0
        mock_ctx.misc = {}
        mock_self._upload_ctx = mock_ctx

        args = (mock_self, {}, {}, [], mock_win)
        kwargs = {}

        with patch("src.modules.clientes.forms._finalize.messagebox.showinfo"):
            finalize_state(*args, **kwargs)

            # Verificar que busy_dialog.close foi chamado
            mock_busy_dialog.close.assert_called_once()

    def test_finalize_state_destroys_window(self):
        """Testa que finalize_state destrói a janela ctx.win."""
        mock_self = MagicMock()
        mock_self.carregar = MagicMock()

        mock_win = MagicMock()
        mock_busy_dialog = MagicMock()

        mock_ctx = UploadCtx(
            app=mock_self,
            row={},
            ents={},
            arquivos_selecionados=[],
            win=mock_win,
        )
        mock_ctx.abort = False
        mock_ctx.finalize_ready = True
        mock_ctx.busy_dialog = mock_busy_dialog
        mock_ctx.falhas = 0
        mock_ctx.misc = {}
        mock_self._upload_ctx = mock_ctx

        args = (mock_self, {}, {}, [], mock_win)
        kwargs = {}

        with patch("src.modules.clientes.forms._finalize.messagebox.showinfo"):
            finalize_state(*args, **kwargs)

            # Verificar que window.destroy foi chamado
            mock_win.destroy.assert_called_once()

    def test_finalize_state_calls_carregar(self):
        """Testa que finalize_state chama self.carregar() para atualizar a UI."""
        mock_self = MagicMock()
        mock_self.carregar = MagicMock()

        mock_win = MagicMock()
        mock_busy_dialog = MagicMock()

        mock_ctx = UploadCtx(
            app=mock_self,
            row={},
            ents={},
            arquivos_selecionados=[],
            win=mock_win,
        )
        mock_ctx.abort = False
        mock_ctx.finalize_ready = True
        mock_ctx.busy_dialog = mock_busy_dialog
        mock_ctx.falhas = 0
        mock_ctx.misc = {}
        mock_self._upload_ctx = mock_ctx

        args = (mock_self, {}, {}, [], mock_win)
        kwargs = {}

        with patch("src.modules.clientes.forms._finalize.messagebox.showinfo"):
            finalize_state(*args, **kwargs)

            # Verificar que carregar foi chamado
            mock_self.carregar.assert_called_once()

    def test_finalize_state_cleans_up_ctx(self):
        """Testa que finalize_state deleta _upload_ctx de self."""
        mock_self = MagicMock()
        mock_self.carregar = MagicMock()

        mock_win = MagicMock()
        mock_busy_dialog = MagicMock()

        mock_ctx = UploadCtx(
            app=mock_self,
            row={},
            ents={},
            arquivos_selecionados=[],
            win=mock_win,
        )
        mock_ctx.abort = False
        mock_ctx.finalize_ready = True
        mock_ctx.busy_dialog = mock_busy_dialog
        mock_ctx.falhas = 0
        mock_ctx.misc = {}
        mock_self._upload_ctx = mock_ctx

        args = (mock_self, {}, {}, [], mock_win)
        kwargs = {}

        with patch("src.modules.clientes.forms._finalize.messagebox.showinfo"):
            finalize_state(*args, **kwargs)

            # Verificar que _upload_ctx foi deletado
            assert not hasattr(mock_self, "_upload_ctx")

    def test_finalize_state_with_ctx_override(self):
        """Testa que finalize_state aceita ctx_override em kwargs."""
        mock_self = MagicMock()
        mock_self.carregar = MagicMock()
        mock_self._upload_ctx = None  # Ctx original None

        mock_win = MagicMock()
        mock_busy_dialog = MagicMock()

        # Ctx override
        mock_ctx_override = UploadCtx(
            app=mock_self,
            row={},
            ents={},
            arquivos_selecionados=[],
            win=mock_win,
        )
        mock_ctx_override.abort = False
        mock_ctx_override.finalize_ready = True
        mock_ctx_override.busy_dialog = mock_busy_dialog
        mock_ctx_override.falhas = 0
        mock_ctx_override.misc = {}

        args = (mock_self, {}, {}, [], mock_win)
        kwargs = {"ctx_override": mock_ctx_override}

        with patch("src.modules.clientes.forms._finalize.messagebox.showinfo"):
            finalize_state(*args, **kwargs)

            # Verificar que funções foram chamadas (usando ctx_override)
            mock_busy_dialog.close.assert_called_once()
            mock_win.destroy.assert_called_once()
            mock_self.carregar.assert_called_once()
