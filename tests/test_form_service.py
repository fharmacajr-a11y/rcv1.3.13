"""Testes unitários para src/modules/uploads/form_service.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


from src.modules.uploads.form_service import salvar_e_upload_docs_service


class TestSalvarEUploadDocsService:
    """Testes para salvar_e_upload_docs_service."""

    def test_returns_correct_result_structure(self):
        """Testa que o service retorna dict com ok, result, errors."""
        # Criar mock de self com _upload_ctx
        mock_self = MagicMock()
        mock_ctx_obj = MagicMock()
        mock_ctx_obj.abort = False
        mock_self._upload_ctx = mock_ctx_obj

        ctx = {
            "self": mock_self,
            "row": {"id": 1},
            "ents": {
                "Razão Social": MagicMock(get=lambda: "Test Corp"),
                "CNPJ": MagicMock(get=lambda: "12345678000190"),
                "Nome": MagicMock(get=lambda: "Test"),
                "WhatsApp": MagicMock(get=lambda: "11999999999"),
                "Observações": MagicMock(get=lambda start, end: "Obs"),
            },
            "arquivos_selecionados": ["file1.pdf"],
            "win": None,
            "kwargs": {},
        }

        with (
            patch("src.modules.uploads.form_service.validate_inputs") as mock_validate,
            patch("src.modules.uploads.form_service.prepare_payload") as mock_prepare,
            patch("src.modules.uploads.form_service.perform_uploads"),
            patch("src.modules.uploads.form_service.finalize_state"),
            patch("src.modules.clientes.forms._prepare.get_supabase_state") as mock_state,
        ):
            # Mock do estado online
            mock_state.return_value = ("online", "OK")

            # Mock do pipeline (retorna args + kwargs)
            mock_validate.return_value = ((mock_self, {"id": 1}, ctx["ents"], ["file1.pdf"], None), {})
            mock_prepare.return_value = ((mock_self, {"id": 1}, ctx["ents"], ["file1.pdf"], None), {})

            result = salvar_e_upload_docs_service(ctx)

            # Verificar estrutura do retorno
            assert "ok" in result
            assert "result" in result
            assert "errors" in result
            assert "message" in result
            assert isinstance(result["errors"], list)

    def test_handles_exception_gracefully(self):
        """Testa que o service captura exceções e retorna estrutura consistente."""
        mock_self = MagicMock()
        mock_self._upload_ctx = None  # Simula erro no _execute_impl_logic

        ctx = {"self": mock_self, "row": {}, "ents": {}, "arquivos_selecionados": [], "win": None, "kwargs": {}}

        with patch("src.modules.uploads.form_service.validate_inputs") as mock_validate:
            # Mock que levanta exceção
            mock_validate.side_effect = ValueError("CNPJ inválido")

            result = salvar_e_upload_docs_service(ctx)

            assert result["ok"] is False
            assert len(result["errors"]) > 0
            assert "CNPJ inválido" in result["errors"][0]

    def test_calls_pipeline_in_correct_order(self):
        """Testa que o service chama o pipeline na ordem correta."""
        mock_self = MagicMock()
        mock_ctx_obj = MagicMock()
        mock_ctx_obj.abort = False
        mock_self._upload_ctx = mock_ctx_obj

        ctx = {
            "self": mock_self,
            "row": {"id": 1},
            "ents": {
                "Razão Social": MagicMock(get=lambda: "Test Corp"),
                "CNPJ": MagicMock(get=lambda: "12345678000190"),
                "Nome": MagicMock(get=lambda: "Test"),
                "WhatsApp": MagicMock(get=lambda: "11999999999"),
                "Observações": MagicMock(get=lambda start, end: "Obs"),
            },
            "arquivos_selecionados": ["file1.pdf"],
            "win": None,
            "kwargs": {},
        }

        with (
            patch("src.modules.uploads.form_service.validate_inputs") as mock_validate,
            patch("src.modules.uploads.form_service.prepare_payload") as mock_prepare,
            patch("src.modules.uploads.form_service.perform_uploads") as mock_perform,
            patch("src.modules.uploads.form_service.finalize_state") as mock_finalize,
            patch("src.modules.clientes.forms._prepare.get_supabase_state") as mock_state,
        ):
            mock_state.return_value = ("online", "OK")

            # Mock do pipeline
            mock_validate.return_value = ((mock_self, {"id": 1}, ctx["ents"], ["file1.pdf"], None), {})
            mock_prepare.return_value = ((mock_self, {"id": 1}, ctx["ents"], ["file1.pdf"], None), {})

            result = salvar_e_upload_docs_service(ctx)

            # Verificar ordem de chamadas (validate → prepare → upload → finalize)
            assert result["ok"] is True
            assert mock_validate.called
            assert mock_prepare.called
            assert mock_perform.called
            assert mock_finalize.called

    def test_passes_skip_duplicate_prompt_to_prepare(self):
        """Testa que skip_duplicate_prompt é passado para prepare_payload."""
        mock_self = MagicMock()
        mock_ctx_obj = MagicMock()
        mock_ctx_obj.abort = False
        mock_self._upload_ctx = mock_ctx_obj

        ctx = {
            "self": mock_self,
            "row": {"id": 1},
            "ents": {
                "Razão Social": MagicMock(get=lambda: "Test Corp"),
                "CNPJ": MagicMock(get=lambda: "12345678000190"),
                "Nome": MagicMock(get=lambda: "Test"),
                "WhatsApp": MagicMock(get=lambda: "11999999999"),
                "Observações": MagicMock(get=lambda start, end: "Obs"),
            },
            "arquivos_selecionados": ["file1.pdf"],
            "win": None,
            "kwargs": {},
            "skip_duplicate_prompt": True,  # Flag no contexto
        }

        with (
            patch("src.modules.uploads.form_service.validate_inputs") as mock_validate,
            patch("src.modules.uploads.form_service.prepare_payload") as mock_prepare,
            patch("src.modules.uploads.form_service.perform_uploads"),
            patch("src.modules.uploads.form_service.finalize_state"),
            patch("src.modules.clientes.forms._prepare.get_supabase_state") as mock_state,
        ):
            mock_state.return_value = ("online", "OK")

            mock_validate.return_value = ((mock_self, {"id": 1}, ctx["ents"], ["file1.pdf"], None), {})
            mock_prepare.return_value = ((mock_self, {"id": 1}, ctx["ents"], ["file1.pdf"], None), {})

            result = salvar_e_upload_docs_service(ctx)

            # Verificar que prepare_payload foi chamado com skip_duplicate_prompt=True
            assert result["ok"] is True
            mock_prepare.assert_called_once()
            call_args = mock_prepare.call_args
            assert call_args[1]["skip_duplicate_prompt"] is True

    def test_handles_abort_from_validate_inputs(self):
        """Testa comportamento quando validate_inputs define ctx.abort=True."""
        mock_self = MagicMock()
        mock_ctx_obj = MagicMock()
        mock_ctx_obj.abort = True  # Simula abort após validate
        mock_self._upload_ctx = mock_ctx_obj

        ctx = {"self": mock_self, "row": {}, "ents": {}, "arquivos_selecionados": [], "win": None, "kwargs": {}}

        with (
            patch("src.modules.uploads.form_service.validate_inputs") as mock_validate,
            patch("src.modules.uploads.form_service.prepare_payload") as mock_prepare,
        ):
            # validate_inputs retorna args/kwargs, mas ctx.abort já é True
            mock_validate.return_value = ((mock_self, {}, {}, [], None), {})
            # prepare_payload retorna imediatamente se ctx.abort=True
            mock_prepare.return_value = ((mock_self, {}, {}, [], None), {})

            result = salvar_e_upload_docs_service(ctx)

            # Service completa, mas _execute_impl_logic detecta abort
            assert result["ok"] is True  # Sem exceção
            assert result["message"] == "Upload concluído com sucesso"

    def test_logs_warning_when_ctx_not_found(self):
        """Testa que _execute_impl_logic loga warning quando _upload_ctx é None."""
        mock_self = MagicMock()
        mock_self._upload_ctx = None  # Simula _upload_ctx ausente

        ctx = {"self": mock_self, "row": {}, "ents": {}, "arquivos_selecionados": [], "win": None, "kwargs": {}}

        with (
            patch("src.modules.uploads.form_service.validate_inputs") as mock_validate,
            patch("src.modules.uploads.form_service.prepare_payload") as mock_prepare,
            patch("src.modules.uploads.form_service.perform_uploads"),
            patch("src.modules.uploads.form_service.finalize_state"),
            patch("src.modules.uploads.form_service.log") as mock_log,
        ):
            mock_validate.return_value = ((mock_self, {}, {}, [], None), {})
            mock_prepare.return_value = ((mock_self, {}, {}, [], None), {})

            salvar_e_upload_docs_service(ctx)

            # Verificar que warning foi logado
            mock_log.warning.assert_called()
            warning_calls = [str(call) for call in mock_log.warning.call_args_list]
            assert any("_upload_ctx não encontrado" in str(call) for call in warning_calls)

    def test_extracts_context_parameters_correctly(self):
        """Testa que o service extrai corretamente os parâmetros do ctx."""
        mock_self = MagicMock()
        mock_ctx_obj = MagicMock()
        mock_ctx_obj.abort = False
        mock_self._upload_ctx = mock_ctx_obj

        test_row = {"id": 999}
        test_ents = {"test": "value"}
        test_arquivos = ["file1.pdf", "file2.pdf"]
        test_win = MagicMock()
        test_kwargs = {"custom_param": "test"}

        ctx = {"self": mock_self, "row": test_row, "ents": test_ents, "arquivos_selecionados": test_arquivos, "win": test_win, "kwargs": test_kwargs}

        with (
            patch("src.modules.uploads.form_service.validate_inputs") as mock_validate,
            patch("src.modules.uploads.form_service.prepare_payload") as mock_prepare,
            patch("src.modules.uploads.form_service.perform_uploads"),
            patch("src.modules.uploads.form_service.finalize_state"),
        ):
            mock_validate.return_value = ((mock_self, test_row, test_ents, test_arquivos, test_win), test_kwargs)
            mock_prepare.return_value = ((mock_self, test_row, test_ents, test_arquivos, test_win), test_kwargs)

            salvar_e_upload_docs_service(ctx)

            # Verificar que validate_inputs foi chamado com os parâmetros corretos
            mock_validate.assert_called_once_with(mock_self, test_row, test_ents, test_arquivos, test_win, custom_param="test")
