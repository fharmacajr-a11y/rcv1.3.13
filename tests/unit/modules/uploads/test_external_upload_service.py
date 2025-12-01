"""Testes unitários para src/modules/uploads/external_upload_service.py (esqueleto)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


from src.modules.uploads.external_upload_service import salvar_e_enviar_para_supabase_service


class TestSalvarEEnviarParaSupabaseService:
    """Testes para salvar_e_enviar_para_supabase_service."""

    @patch("src.modules.uploads.external_upload_service.is_really_online")
    @patch("src.modules.uploads.external_upload_service.get_supabase_state")
    def test_validates_online_connection(self, mock_get_state, mock_is_online):
        """Testa que o service valida se está online antes de processar."""
        mock_is_online.return_value = False
        mock_get_state.return_value = ("offline", "No network connection")

        ctx = {"files": ["file1.pdf"], "self": MagicMock()}
        result = salvar_e_enviar_para_supabase_service(ctx)

        assert result["ok"] is False
        assert result["should_show_ui"] is True
        assert result["ui_message_type"] == "warning"
        assert "Offline" in result["ui_message_title"]

    @patch("src.modules.uploads.external_upload_service.is_really_online")
    def test_validates_files_selected(self, mock_is_online):
        """Testa que o service valida se há arquivos selecionados."""
        mock_is_online.return_value = True

        ctx = {"files": [], "self": MagicMock()}
        result = salvar_e_enviar_para_supabase_service(ctx)

        assert result["ok"] is False
        assert result["should_show_ui"] is True
        assert result["ui_message_type"] == "info"
        assert "Nenhum arquivo selecionado" in result["ui_message_body"]

    @patch("src.modules.uploads.external_upload_service.is_really_online")
    @patch("src.modules.uploads.external_upload_service.build_items_from_files")
    def test_builds_upload_items_from_files(self, mock_build_items, mock_is_online):
        """Testa que o service constrói items de upload a partir dos arquivos."""
        mock_is_online.return_value = True
        mock_build_items.return_value = []  # Nenhum PDF válido

        ctx = {"files": ["file1.txt"], "self": MagicMock(), "ents": {}}
        result = salvar_e_enviar_para_supabase_service(ctx)

        mock_build_items.assert_called_once_with(["file1.txt"])
        assert result["ok"] is False
        assert "Nenhum PDF valido" in result["ui_message_body"]

    @patch("src.modules.uploads.external_upload_service.is_really_online")
    @patch("src.modules.uploads.external_upload_service.build_items_from_files")
    @patch("src.modules.uploads.external_upload_service.upload_files_to_supabase")
    def test_extracts_cnpj_from_cliente(self, mock_upload, mock_build_items, mock_is_online):
        """Testa que o service extrai CNPJ do cliente corretamente."""
        mock_is_online.return_value = True
        mock_build_items.return_value = [{"path": "file1.pdf"}]
        mock_upload.return_value = (1, 0)

        # Mock de widget CNPJ
        mock_widget = MagicMock()
        mock_widget.get.return_value = "12.345.678/0001-99"

        ctx = {"files": ["file1.pdf"], "self": MagicMock(), "ents": {"CNPJ": mock_widget}, "row": None}
        salvar_e_enviar_para_supabase_service(ctx)

        # Verifica que upload foi chamado com CNPJ correto
        assert mock_upload.called
        call_args = mock_upload.call_args
        cliente = call_args[0][1]  # Segundo argumento
        assert cliente["cnpj"] == "12.345.678/0001-99"

    @patch("src.modules.uploads.external_upload_service.is_really_online")
    @patch("src.modules.uploads.external_upload_service.build_items_from_files")
    @patch("src.modules.uploads.external_upload_service.upload_files_to_supabase")
    def test_uploads_via_upload_files_to_supabase(self, mock_upload, mock_build_items, mock_is_online):
        """Testa que o service delega upload para upload_files_to_supabase."""
        mock_is_online.return_value = True
        mock_build_items.return_value = [{"path": "file1.pdf"}, {"path": "file2.pdf"}]
        mock_upload.return_value = (2, 0)

        ctx = {"files": ["file1.pdf", "file2.pdf"], "self": MagicMock(), "ents": {}, "row": None}
        result = salvar_e_enviar_para_supabase_service(ctx)

        assert mock_upload.called
        assert result["ok"] is True
        assert result["result"] == (2, 0)

    @patch("src.modules.uploads.external_upload_service.is_really_online")
    @patch("src.modules.uploads.external_upload_service.get_supabase_state")
    def test_returns_error_when_offline(self, mock_get_state, mock_is_online):
        """Testa que o service retorna erro se a conexão estiver offline."""
        mock_is_online.return_value = False
        mock_get_state.return_value = ("unstable", "Intermittent connection")

        ctx = {"files": ["file1.pdf"], "self": MagicMock()}
        result = salvar_e_enviar_para_supabase_service(ctx)

        assert result["ok"] is False
        assert "Conexão Instável" in result["ui_message_title"]
        assert "instável" in result["ui_message_body"]

    @patch("src.modules.uploads.external_upload_service.is_really_online")
    @patch("src.modules.uploads.external_upload_service.build_items_from_files")
    @patch("src.modules.uploads.external_upload_service.upload_files_to_supabase")
    def test_returns_upload_counts(self, mock_upload, mock_build_items, mock_is_online):
        """Testa que o service retorna (ok_count, failed_count) no result."""
        mock_is_online.return_value = True
        mock_build_items.return_value = [{"path": "file1.pdf"}]
        mock_upload.return_value = (1, 0)

        ctx = {
            "files": ["file1.pdf"],
            "self": MagicMock(),
            "ents": {},
        }
        result = salvar_e_enviar_para_supabase_service(ctx)

        assert result["ok"] is True
        assert result["result"] == (1, 0)
        assert "1 sucesso(s), 0 falha(s)" in result["message"]

    @patch("src.modules.uploads.external_upload_service.is_really_online")
    def test_sets_should_show_ui_flag(self, mock_is_online):
        """Testa que o service define flag should_show_ui corretamente."""
        mock_is_online.return_value = True

        # Caso 1: Sem arquivos (deve mostrar UI)
        ctx = {"files": [], "self": MagicMock()}
        result = salvar_e_enviar_para_supabase_service(ctx)
        assert result["should_show_ui"] is True

        # Caso 2: Offline (deve mostrar UI)
        mock_is_online.return_value = False
        ctx = {"files": ["file1.pdf"], "self": MagicMock()}
        result = salvar_e_enviar_para_supabase_service(ctx)
        assert result["should_show_ui"] is True

    @patch("src.modules.uploads.external_upload_service.is_really_online")
    @patch("src.modules.uploads.external_upload_service.build_items_from_files")
    def test_sets_ui_message_type(self, mock_build_items, mock_is_online):
        """Testa que o service define ui_message_type (warning/error/info)."""
        mock_is_online.return_value = True

        # Caso 1: Sem arquivos (info)
        ctx = {"files": [], "self": MagicMock()}
        result = salvar_e_enviar_para_supabase_service(ctx)
        assert result["ui_message_type"] == "info"

        # Caso 2: Sem PDFs válidos (warning)
        mock_build_items.return_value = []
        ctx = {"files": ["file1.txt"], "self": MagicMock(), "ents": {}}
        result = salvar_e_enviar_para_supabase_service(ctx)
        assert result["ui_message_type"] == "warning"
