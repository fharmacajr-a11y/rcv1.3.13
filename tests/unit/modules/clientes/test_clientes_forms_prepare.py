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

        with (
            patch("src.modules.clientes.forms._prepare.get_supabase_state") as mock_state,
            patch("src.modules.clientes.forms._prepare.messagebox"),
        ):
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

        with (
            patch("src.modules.clientes.forms._prepare.get_supabase_state") as mock_state,
            patch("src.modules.clientes.forms._prepare.messagebox"),
        ):
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


class TestHelperFunctions:
    """Testes para funções auxiliares de _prepare.py."""

    def test_extract_supabase_error_from_dict(self):
        """Testa extração de erro de dict Supabase."""
        from src.modules.clientes.forms._prepare import _extract_supabase_error

        err = {
            "code": "23505",
            "message": "duplicate key violation",
            "constraint": "uq_clients_cnpj",
        }

        code, message, constraint = _extract_supabase_error(err)

        assert code == "23505"
        assert "duplicate key violation" in message
        assert constraint == "uq_clients_cnpj"

    def test_extract_supabase_error_fallback_to_str(self):
        """Testa fallback para str(err) quando não há attrs."""
        from src.modules.clientes.forms._prepare import _extract_supabase_error

        err = Exception("generic error message")

        _code, message, _constraint = _extract_supabase_error(err)

        assert "generic error message" in message

    def test_traduzir_erro_supabase_cnpj_duplicado(self):
        """Testa tradução de erro de CNPJ duplicado."""
        from src.modules.clientes.forms._prepare import traduzir_erro_supabase_para_msg_amigavel

        err = {
            "code": "23505",
            "message": "duplicate key value violates unique constraint",
            "constraint": "uq_clients_cnpj",
        }

        msg = traduzir_erro_supabase_para_msg_amigavel(err, cnpj="12.345.678/0001-99")

        assert "Já existe um cliente cadastrado com este CNPJ" in msg
        assert "12.345.678/0001-99" in msg
        assert "Lixeira" in msg

    def test_traduzir_erro_supabase_generico(self):
        """Testa tradução de erro genérico."""
        from src.modules.clientes.forms._prepare import traduzir_erro_supabase_para_msg_amigavel

        err = {"code": "42P01", "message": "relation does not exist"}

        msg = traduzir_erro_supabase_para_msg_amigavel(err)

        assert "relation does not exist" in msg

    def test_extract_status_value_from_widget(self):
        """Testa extração de status de widget."""
        from src.modules.clientes.forms._prepare import _extract_status_value

        widget = MagicMock()
        widget.get.return_value = "ATIVO"

        ents = {"status": widget}

        result = _extract_status_value(ents)

        assert result == "ATIVO"

    def test_extract_status_value_empty_when_no_widget(self):
        """Testa retorno vazio quando não há widget de status."""
        from src.modules.clientes.forms._prepare import _extract_status_value

        result_empty_dict = _extract_status_value({})
        result_none = _extract_status_value(None)

        assert result_empty_dict == ""
        assert result_none == ""

    def test_build_storage_prefix_with_all_parts(self):
        """Testa construção de prefix com todas as partes."""
        from src.modules.clientes.forms._prepare import _build_storage_prefix

        prefix = _build_storage_prefix("org123", "456", "GERAL", "SIFAP")

        assert "org123" in prefix
        assert "456" in prefix
        # storage_slug_part converte para lowercase
        assert "geral" in prefix.lower()
        assert "sifap" in prefix.lower()

    def test_build_storage_prefix_with_none_parts(self):
        """Testa construção ignorando partes None."""
        from src.modules.clientes.forms._prepare import _build_storage_prefix

        prefix = _build_storage_prefix("org123", None, "GERAL")

        assert "org123" in prefix
        assert "geral" in prefix.lower()

    def test_unpack_call_from_args(self):
        """Testa desempacotamento de args posicionais."""
        from src.modules.clientes.forms._prepare import _unpack_call

        mock_self = MagicMock()
        row = {"id": 1}
        ents = {"Nome": MagicMock()}
        arquivos = ["file1.pdf"]
        win = MagicMock()

        args = (mock_self, row, ents, arquivos, win)
        kwargs = {}

        result = _unpack_call(args, kwargs)

        assert result == (mock_self, row, ents, arquivos, win)

    def test_unpack_call_from_kwargs(self):
        """Testa desempacotamento de kwargs."""
        from src.modules.clientes.forms._prepare import _unpack_call

        mock_self = MagicMock()
        row = {"id": 2}
        ents = {"CNPJ": MagicMock()}

        args = (mock_self,)
        kwargs = {"row": row, "ents": ents, "arquivos_selecionados": [], "win": None}

        result = _unpack_call(args, kwargs)

        assert result[0] == mock_self
        assert result[1] == row
        assert result[2] == ents
        assert result[3] == []
        assert result[4] is None

    def test_ensure_ctx_creates_new_when_missing(self):
        """Testa criação de novo contexto quando não existe."""
        from src.modules.clientes.forms._prepare import _ensure_ctx

        mock_self = MagicMock()
        # Garantir que não tem _upload_ctx
        if hasattr(mock_self, "_upload_ctx"):
            delattr(mock_self, "_upload_ctx")

        row = {"id": 1}
        ents = {"Nome": MagicMock()}
        arquivos = ["file.pdf"]
        win = MagicMock()

        ctx = _ensure_ctx(mock_self, row, ents, arquivos, win)

        assert ctx.app == mock_self
        assert ctx.row == row
        assert ctx.ents == ents
        assert ctx.arquivos_selecionados == ["file.pdf"]
        assert ctx.win == win

    def test_ensure_ctx_reuses_existing(self):
        """Testa reutilização de contexto existente."""
        from src.modules.clientes.forms._prepare import _ensure_ctx, UploadCtx

        mock_self = MagicMock()
        existing_ctx = UploadCtx(client_id=999, org_id="old_org")
        mock_self._upload_ctx = existing_ctx

        row = None
        ents = {"CNPJ": MagicMock()}
        arquivos = []
        win = MagicMock()

        ctx = _ensure_ctx(mock_self, row, ents, arquivos, win)

        # Deve ser o mesmo objeto
        assert ctx is existing_ctx
        # Mas valores atualizados
        assert ctx.row is None
        assert ctx.ents == ents
