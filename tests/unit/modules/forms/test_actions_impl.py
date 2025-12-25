# -*- coding: utf-8 -*-
"""Testes unitários para actions_impl (lógica de formulários).

Cobertura:
- list_storage_objects: sucesso, erro bucket_not_found, outros erros
- download_file: chamada normal e compacta
- preencher_via_pasta: sucesso, cancelamento, dados ausentes
- salvar_e_enviar_para_supabase: sucesso, Exception durante service
"""

from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch


from src.modules.forms.actions_impl import (
    download_file,
    list_storage_objects,
    preencher_via_pasta,
    salvar_e_enviar_para_supabase,
)


class TestListStorageObjects:
    """Testes para list_storage_objects() - listagem de arquivos do Storage."""

    @patch("src.modules.forms.actions_impl.list_storage_objects_service")
    def test_success_returns_objects_list(self, mock_service):
        """list_storage_objects: quando service retorna ok=True, deve retornar lista."""
        # ARRANGE
        expected_objects = [{"name": "file1.pdf"}, {"name": "file2.pdf"}]
        mock_service.return_value = {
            "ok": True,
            "objects": expected_objects,
        }

        # ACT
        result = list_storage_objects("test-bucket", "client123/")

        # ASSERT
        assert result == expected_objects
        mock_service.assert_called_once_with(
            {
                "bucket_name": "test-bucket",
                "prefix": "client123/",
            }
        )

    @patch("src.modules.forms.actions_impl.messagebox")
    @patch("src.modules.forms.actions_impl.list_storage_objects_service")
    def test_bucket_not_found_shows_error_returns_empty_list(self, mock_service, mock_messagebox):
        """list_storage_objects: quando bucket não existe, deve mostrar erro e retornar []."""
        # ARRANGE
        mock_service.return_value = {
            "ok": False,
            "error_type": "bucket_not_found",
            "objects": [],
        }

        # ACT
        result = list_storage_objects("inexistent-bucket", "")

        # ASSERT
        assert result == []
        mock_messagebox.showerror.assert_called_once()
        args = mock_messagebox.showerror.call_args[0]
        assert "Erro ao listar arquivos" in args[0]
        assert "bucket" in args[1].lower()

    @patch("src.modules.forms.actions_impl.messagebox")
    @patch("src.modules.forms.actions_impl.list_storage_objects_service")
    def test_other_error_no_messagebox_returns_empty_list(self, mock_service, mock_messagebox):
        """list_storage_objects: outros erros não mostram messagebox (só log no service)."""
        # ARRANGE
        mock_service.return_value = {
            "ok": False,
            "error_type": "network_error",
            "objects": [],
        }

        # ACT
        result = list_storage_objects("bucket", "prefix/")

        # ASSERT
        assert result == []
        mock_messagebox.showerror.assert_not_called()


class TestDownloadFile:
    """Testes para download_file() - download de arquivos do Storage."""

    @patch("src.modules.forms.actions_impl.download_file_service")
    def test_normal_call_with_all_parameters(self, mock_service):
        """download_file: chamada normal com todos os parâmetros."""
        # ARRANGE
        mock_service.return_value = {
            "ok": True,
            "local_path": "/tmp/downloaded.pdf",
        }

        # ACT
        result = download_file("bucket", "remote/file.pdf", "/tmp/downloaded.pdf")

        # ASSERT
        mock_service.assert_called_once_with(
            {
                "bucket_name": "bucket",
                "file_path": "remote/file.pdf",
                "local_path": "/tmp/downloaded.pdf",
                "compact_call": False,
            }
        )
        assert result["ok"] is True

    @patch("src.modules.forms.actions_impl.download_file_service")
    def test_compact_call_without_local_path(self, mock_service):
        """download_file: chamada compacta (sem local_path) deve marcar compact_call=True."""
        # ARRANGE
        mock_service.return_value = {"ok": True}

        # ACT
        result = download_file("bucket", "remote/file.pdf")

        # ASSERT
        mock_service.assert_called_once_with(
            {
                "bucket_name": "bucket",
                "file_path": "remote/file.pdf",
                "local_path": None,
                "compact_call": True,
            }
        )
        assert result["ok"] is True


class TestPreencherViaPasta:
    """Testes para preencher_via_pasta() - preenchimento via Cartão CNPJ."""

    @patch("src.modules.forms.actions_impl.filedialog")
    def test_user_cancels_directory_selection_does_nothing(self, mock_filedialog):
        """preencher_via_pasta: usuário cancela seleção de pasta -> não preenche nada."""
        # ARRANGE
        mock_filedialog.askdirectory.return_value = ""  # Cancelado
        ents = {"Razão Social": Mock(), "CNPJ": Mock()}

        # ACT
        preencher_via_pasta(ents)

        # ASSERT
        ents["Razão Social"].delete.assert_not_called()
        ents["CNPJ"].delete.assert_not_called()

    @patch("src.modules.forms.actions_impl.messagebox")
    @patch("src.modules.forms.actions_impl.extrair_dados_cartao_cnpj_em_pasta")
    @patch("src.modules.forms.actions_impl.filedialog")
    def test_no_cnpj_found_shows_warning_does_not_fill(self, mock_filedialog, mock_extrair, mock_messagebox):
        """preencher_via_pasta: sem CNPJ/razão encontrado -> aviso, não preenche."""
        # ARRANGE
        mock_filedialog.askdirectory.return_value = "/path/to/folder"
        mock_extrair.return_value = {"cnpj": None, "razao_social": None}
        ents = {"Razão Social": Mock(), "CNPJ": Mock()}

        # ACT
        preencher_via_pasta(ents)

        # ASSERT
        mock_messagebox.showwarning.assert_called_once()
        args = mock_messagebox.showwarning.call_args[0]
        assert "Nenhum Cartão CNPJ" in args[1]
        ents["Razão Social"].delete.assert_not_called()
        ents["CNPJ"].delete.assert_not_called()

    @patch("src.modules.forms.actions_impl.only_digits")
    @patch("src.modules.forms.actions_impl.extrair_dados_cartao_cnpj_em_pasta")
    @patch("src.modules.forms.actions_impl.filedialog")
    def test_success_fills_razao_and_cnpj_fields(self, mock_filedialog, mock_extrair, mock_only_digits):
        """preencher_via_pasta: dados encontrados -> preenche Razão Social e CNPJ."""
        # ARRANGE
        mock_filedialog.askdirectory.return_value = "/path/to/folder"
        mock_extrair.return_value = {
            "cnpj": "12.345.678/0001-90",
            "razao_social": "Empresa Teste LTDA",
        }
        mock_only_digits.return_value = "12345678000190"

        razao_entry = Mock()
        cnpj_entry = Mock()
        ents = {"Razão Social": razao_entry, "CNPJ": cnpj_entry}

        # ACT
        preencher_via_pasta(ents)

        # ASSERT
        razao_entry.delete.assert_called_once_with(0, "end")
        razao_entry.insert.assert_called_once_with(0, "Empresa Teste LTDA")

        cnpj_entry.delete.assert_called_once_with(0, "end")
        cnpj_entry.insert.assert_called_once_with(0, "12345678000190")
        mock_only_digits.assert_called_once_with("12.345.678/0001-90")

    @patch("src.modules.forms.actions_impl.only_digits")
    @patch("src.modules.forms.actions_impl.extrair_dados_cartao_cnpj_em_pasta")
    @patch("src.modules.forms.actions_impl.filedialog")
    def test_only_razao_found_fills_only_razao(self, mock_filedialog, mock_extrair, mock_only_digits):
        """preencher_via_pasta: só razão encontrada -> preenche só Razão Social."""
        # ARRANGE
        mock_filedialog.askdirectory.return_value = "/path/to/folder"
        mock_extrair.return_value = {
            "cnpj": None,
            "razao_social": "Empresa Teste",
        }

        razao_entry = Mock()
        cnpj_entry = Mock()
        ents = {"Razão Social": razao_entry, "CNPJ": cnpj_entry}

        # ACT
        preencher_via_pasta(ents)

        # ASSERT
        razao_entry.delete.assert_called_once()
        razao_entry.insert.assert_called_once_with(0, "Empresa Teste")

        # CNPJ não deve ser preenchido (não houve insert, só delete)
        cnpj_entry.delete.assert_called_once()
        cnpj_entry.insert.assert_not_called()


class TestSalvarEEnviarParaSupabase:
    """Testes para salvar_e_enviar_para_supabase() - upload de documentos."""

    @patch("src.modules.forms.actions_impl.show_upload_result_message")
    @patch("src.modules.forms.actions_impl.salvar_e_enviar_para_supabase_service")
    @patch("src.modules.forms.actions_impl._select_pdfs_dialog")
    def test_success_calls_service_and_shows_result(self, mock_select_pdfs, mock_service, mock_show_result):
        """salvar_e_enviar_para_supabase: fluxo de sucesso completo."""
        # ARRANGE
        mock_select_pdfs.return_value = ["/path/file1.pdf", "/path/file2.pdf"]
        mock_service.return_value = {
            "result": "success",
            "uploaded_count": 2,
        }

        self_mock = MagicMock()
        row = {"id": "123"}
        ents = {"field1": "value1"}
        win = None

        # ACT
        result = salvar_e_enviar_para_supabase(self_mock, row, ents, win)

        # ASSERT
        mock_select_pdfs.assert_called_once()
        mock_service.assert_called_once()
        ctx = mock_service.call_args[0][0]
        assert ctx["row"] == row
        assert ctx["ents"] == ents
        assert ctx["files"] == ["/path/file1.pdf", "/path/file2.pdf"]

        mock_show_result.assert_called_once()
        assert result == "success"

    @patch("src.modules.forms.actions_impl.messagebox")
    @patch("src.modules.forms.actions_impl.salvar_e_enviar_para_supabase_service")
    @patch("src.modules.forms.actions_impl._select_pdfs_dialog")
    def test_service_exception_shows_error_returns_none(self, mock_select_pdfs, mock_service, mock_messagebox):
        """salvar_e_enviar_para_supabase: Exception no service -> erro exibido, retorna None."""
        # ARRANGE
        mock_select_pdfs.return_value = ["/path/file.pdf"]
        mock_service.side_effect = Exception("Network error")

        self_mock = MagicMock()
        row = {"id": "456"}
        ents = {}
        win = None

        # ACT
        result = salvar_e_enviar_para_supabase(self_mock, row, ents, win)

        # ASSERT
        mock_messagebox.showerror.assert_called_once()
        args = mock_messagebox.showerror.call_args[0]
        assert "erro inesperado" in args[1].lower()
        assert result is None

    @patch("src.modules.forms.actions_impl.show_upload_result_message")
    @patch("src.modules.forms.actions_impl.salvar_e_enviar_para_supabase_service")
    @patch("src.modules.forms.actions_impl._select_pdfs_dialog")
    def test_with_win_parameter_passes_to_service(self, mock_select_pdfs, mock_service, mock_show_result):
        """salvar_e_enviar_para_supabase: parâmetro win é passado ao contexto."""
        # ARRANGE
        mock_select_pdfs.return_value = []
        mock_service.return_value = {"result": "no_files"}

        self_mock = MagicMock()
        win_mock = MagicMock()
        row = {}
        ents = {}

        # ACT
        salvar_e_enviar_para_supabase(self_mock, row, ents, win_mock)

        # ASSERT
        ctx = mock_service.call_args[0][0]
        assert ctx["win"] is win_mock
