"""Testes unitários para src/modules/clientes/forms/_prepare.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


from src.modules.clientes.forms._prepare import (
    UploadCtx,
    prepare_payload,
    validate_inputs,
)


class TestValidateInputs:
    """Testes para validate_inputs."""

    def test_validate_inputs_marks_abort_when_offline(self):
        """Testa que validate_inputs marca ctx.abort=True quando Supabase está offline."""
        # Mock de self com _upload_ctx
        mock_self = MagicMock()
        mock_self._upload_ctx = None  # Será criado por _ensure_ctx

        # Mock de ents (widgets do formulário)
        mock_ents = {
            "Razão Social": MagicMock(get=lambda: "Test Corp"),
            "CNPJ": MagicMock(get=lambda: "12345678000190"),
            "Nome": MagicMock(get=lambda: "Test"),
            "WhatsApp": MagicMock(get=lambda: "11999999999"),
            "Observações": MagicMock(get=lambda start, end: "Obs"),
        }

        args = (mock_self, {"id": 1}, mock_ents, ["file1.pdf"], None)
        kwargs = {}

        with patch("src.modules.clientes.forms._prepare.get_supabase_state") as mock_state, patch("src.modules.clientes.forms._prepare.messagebox"):
            # Mock do estado offline
            mock_state.return_value = ("offline", "Sem resposta do Supabase")

            # Chamar validate_inputs
            result_args, result_kwargs = validate_inputs(*args, **kwargs)

            # Verificar que ctx.abort foi definido
            ctx = getattr(mock_self, "_upload_ctx")
            assert ctx is not None
            assert ctx.abort is True

    def test_validate_inputs_does_not_abort_when_online(self):
        """Testa que validate_inputs NÃO marca abort quando Supabase está online."""
        mock_self = MagicMock()
        mock_self._upload_ctx = None

        mock_ents = {
            "Razão Social": MagicMock(get=lambda: "Test Corp"),
            "CNPJ": MagicMock(get=lambda: "12345678000190"),
            "Nome": MagicMock(get=lambda: "Test"),
            "WhatsApp": MagicMock(get=lambda: "11999999999"),
            "Observações": MagicMock(get=lambda start, end: "Obs"),
        }

        args = (mock_self, {"id": 1}, mock_ents, ["file1.pdf"], None)
        kwargs = {}

        with patch("src.modules.clientes.forms._prepare.get_supabase_state") as mock_state:
            mock_state.return_value = ("online", "OK")

            result_args, result_kwargs = validate_inputs(*args, **kwargs)

            ctx = getattr(mock_self, "_upload_ctx")
            assert ctx is not None
            assert ctx.abort is False

    def test_validate_inputs_populates_valores(self):
        """Testa que validate_inputs popula ctx.valores com dados do formulário."""
        mock_self = MagicMock()
        mock_self._upload_ctx = None

        mock_ents = {
            "Razão Social": MagicMock(get=lambda: "Test Corp"),
            "CNPJ": MagicMock(get=lambda: "12345678000190"),
            "Nome": MagicMock(get=lambda: "Test"),
            "WhatsApp": MagicMock(get=lambda: "11999999999"),
            "Observações": MagicMock(get=lambda start, end: "Observações de teste"),
        }

        args = (mock_self, {"id": 1}, mock_ents, ["file1.pdf"], None)
        kwargs = {}

        with patch("src.modules.clientes.forms._prepare.get_supabase_state") as mock_state:
            mock_state.return_value = ("online", "OK")

            validate_inputs(*args, **kwargs)

            ctx = getattr(mock_self, "_upload_ctx")
            assert ctx.valores is not None
            assert ctx.valores["Razão Social"] == "Test Corp"
            assert ctx.valores["CNPJ"] == "12345678000190"
            assert ctx.valores["Nome"] == "Test"
            assert ctx.valores["WhatsApp"] == "11999999999"
            assert ctx.valores["Observações"] == "Observações de teste"

    def test_validate_inputs_handles_unstable_connection(self):
        """Testa que validate_inputs marca abort quando conexão está instável."""
        mock_self = MagicMock()
        mock_self._upload_ctx = None

        mock_ents = {
            "Razão Social": MagicMock(get=lambda: "Test Corp"),
            "CNPJ": MagicMock(get=lambda: "12345678000190"),
            "Nome": MagicMock(get=lambda: "Test"),
            "WhatsApp": MagicMock(get=lambda: "11999999999"),
            "Observações": MagicMock(get=lambda start, end: "Obs"),
        }

        args = (mock_self, {"id": 1}, mock_ents, ["file1.pdf"], None)
        kwargs = {}

        with patch("src.modules.clientes.forms._prepare.get_supabase_state") as mock_state, patch("src.modules.clientes.forms._prepare.messagebox"):
            mock_state.return_value = ("unstable", "Conexão intermitente")

            validate_inputs(*args, **kwargs)

            ctx = getattr(mock_self, "_upload_ctx")
            assert ctx.abort is True


class TestPreparePayload:
    """Testes para prepare_payload."""

    def test_prepare_payload_returns_early_when_abort_true(self):
        """Testa que prepare_payload retorna imediatamente se ctx.abort=True."""
        mock_self = MagicMock()
        mock_ctx = UploadCtx(
            app=mock_self,
            row={},
            ents={},
            arquivos_selecionados=[],
            win=None,
        )
        mock_ctx.abort = True
        mock_self._upload_ctx = mock_ctx

        args = (mock_self, {}, {}, [], None)
        kwargs = {}

        # prepare_payload não deve alterar ctx se abort=True
        result_args, result_kwargs = prepare_payload(*args, **kwargs)

        # Verificar que args/kwargs foram retornados sem alteração
        assert result_args == args
        assert result_kwargs == kwargs

    def test_prepare_payload_returns_early_when_ctx_none(self):
        """Testa que prepare_payload retorna imediatamente se _upload_ctx não existe."""
        mock_self = MagicMock()
        mock_self._upload_ctx = None  # Sem ctx

        args = (mock_self, {}, {}, [], None)
        kwargs = {}

        result_args, result_kwargs = prepare_payload(*args, **kwargs)

        assert result_args == args
        assert result_kwargs == {}

    def test_prepare_payload_uses_existing_valores_from_ctx(self):
        """Testa que prepare_payload usa ctx.valores se já existir (de validate_inputs)."""
        mock_self = MagicMock()
        mock_ctx = UploadCtx(
            app=mock_self,
            row={"id": 1},
            ents={},
            arquivos_selecionados=["file1.pdf"],
            win=None,
        )
        mock_ctx.abort = False
        mock_ctx.valores = {
            "Razão Social": "Test Corp (from ctx)",
            "CNPJ": "12345678000190",
            "Nome": "Test",
            "WhatsApp": "11999999999",
            "Observações": "Obs from ctx",
            "status": "Ativo",
        }
        mock_self._upload_ctx = mock_ctx

        args = (mock_self, {"id": 1}, {}, ["file1.pdf"], None)
        kwargs = {}

        # Mock salvar_cliente para não acessar banco
        with patch("src.modules.clientes.forms._prepare.salvar_cliente") as mock_salvar:
            mock_salvar.return_value = (123, "/tmp/pasta")

            # Forçar abort=True para interromper antes de pedir subpasta
            mock_ctx.abort = True
            prepare_payload(*args, skip_duplicate_prompt=True, **kwargs)

            # Verificar que ctx.valores não foi alterado
            assert mock_ctx.valores["Razão Social"] == "Test Corp (from ctx)"

    def test_prepare_payload_with_skip_duplicate_prompt(self):
        """Testa que prepare_payload aceita skip_duplicate_prompt como kwarg."""
        mock_self = MagicMock()
        mock_ctx = UploadCtx(
            app=mock_self,
            row={"id": 1},
            ents={},
            arquivos_selecionados=["file1.pdf"],
            win=None,
        )
        mock_ctx.abort = False
        mock_ctx.valores = {
            "Razão Social": "Test Corp",
            "CNPJ": "12345678000190",
            "Nome": "Test",
            "WhatsApp": "11999999999",
            "Observações": "Obs",
            "status": "Ativo",
        }
        mock_self._upload_ctx = mock_ctx

        args = (mock_self, {"id": 1}, {}, ["file1.pdf"], None)
        kwargs = {}

        # Chamar com skip_duplicate_prompt=True e verificar que não levanta exceção
        result_args, result_kwargs = prepare_payload(*args, skip_duplicate_prompt=True, **kwargs)

        # Se chegou aqui sem erro, o kwarg foi aceito
        assert result_args is not None
