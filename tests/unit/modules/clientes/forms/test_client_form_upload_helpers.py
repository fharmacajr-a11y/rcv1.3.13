# -*- coding: utf-8 -*-
"""
Testes para client_form_upload_helpers.py

Valida a lógica headless de upload de documentos extraída do client_form.py.
"""

from __future__ import annotations

from unittest.mock import Mock, PropertyMock, patch

import pytest

from src.modules.clientes.forms.client_form_upload_helpers import (
    _format_validation_errors,
    execute_upload_flow,
)


class TestFormatValidationErrors:
    """Testes para _format_validation_errors()."""

    def test_formats_validation_errors_with_path_and_error(self):
        """Deve formatar erros com path e mensagem."""
        results = [
            Mock(path="/path/to/file1.pdf", error="arquivo muito grande"),
            Mock(path="/path/to/file2.pdf", error="formato inválido"),
        ]

        messages = _format_validation_errors(results)

        assert len(messages) == 2
        assert "file1.pdf: arquivo muito grande" in messages
        assert "file2.pdf: formato inválido" in messages

    def test_formats_validation_errors_without_error(self):
        """Deve usar mensagem padrão quando error está vazio."""
        results = [Mock(path="/path/to/file.pdf", error="")]

        messages = _format_validation_errors(results)

        assert len(messages) == 1
        assert "file.pdf: arquivo invalido" in messages[0]

    def test_formats_validation_errors_without_path(self):
        """Deve usar 'Arquivo' quando path está ausente."""
        results = [Mock(spec=[], error="erro genérico")]

        messages = _format_validation_errors(results)

        assert len(messages) == 1
        assert "Arquivo: erro genérico" in messages[0]

    def test_handles_exception_in_formatting(self):
        """Deve ignorar silenciosamente erros ao formatar."""
        # Objeto que lança exceção ao acessar atributos
        bad_result = Mock()
        bad_result.path = PropertyMock(side_effect=Exception("boom"))

        results = [bad_result]

        messages = _format_validation_errors(results)

        assert messages == []

    def test_returns_empty_list_for_none(self):
        """Deve retornar lista vazia quando results é None."""
        messages = _format_validation_errors(None)

        assert messages == []

    def test_returns_empty_list_for_empty_list(self):
        """Deve retornar lista vazia quando results é lista vazia."""
        messages = _format_validation_errors([])

        assert messages == []


class TestExecuteUploadFlow:
    """Testes para execute_upload_flow()."""

    @patch("src.modules.clientes.forms.client_form_upload_helpers.filedialog")
    @patch("src.modules.clientes.forms.client_form_upload_helpers.messagebox")
    def test_shows_info_when_no_folder_selected(self, mock_messagebox, mock_filedialog):
        """Deve exibir info quando usuário cancela seleção."""
        mock_filedialog.askdirectory.return_value = ""
        parent = Mock()
        ents = {"CNPJ": Mock()}
        host = Mock()

        execute_upload_flow(parent, ents, client_id=1, host=host)

        mock_messagebox.showinfo.assert_called_once_with(
            "Envio",
            "Nenhuma pasta selecionada.",
            parent=parent,
        )

    @patch("src.modules.clientes.forms.client_form_upload_helpers.filedialog")
    @patch("src.modules.clientes.forms.client_form_upload_helpers.messagebox")
    @patch("src.modules.clientes.forms.client_form_upload_helpers.collect_pdfs_from_folder")
    def test_shows_info_when_no_pdfs_found(self, mock_collect, mock_messagebox, mock_filedialog):
        """Deve exibir info quando pasta não contém PDFs."""
        mock_filedialog.askdirectory.return_value = "/pasta"
        mock_collect.return_value = []

        parent = Mock()
        ents = {"CNPJ": Mock()}
        host = Mock()

        execute_upload_flow(parent, ents, client_id=1, host=host)

        mock_messagebox.showinfo.assert_called_once_with(
            "Envio",
            "Nenhum PDF encontrado nessa pasta.",
            parent=parent,
        )

    @patch("src.modules.clientes.forms.client_form_upload_helpers.filedialog")
    @patch("src.modules.clientes.forms.client_form_upload_helpers.messagebox")
    @patch("src.modules.clientes.forms.client_form_upload_helpers.collect_pdfs_from_folder")
    @patch("src.modules.clientes.forms.client_form_upload_helpers.validate_upload_files")
    @patch("src.modules.clientes.forms.client_form_upload_helpers.SubpastaDialog")
    def test_shows_warning_when_no_valid_files(
        self, mock_dialog_class, mock_validate, mock_collect, mock_messagebox, mock_filedialog
    ):
        """Deve exibir aviso quando não há arquivos válidos."""
        mock_filedialog.askdirectory.return_value = "/pasta"
        mock_collect.return_value = [Mock(path="/path/file.pdf", relative_path="file.pdf")]
        mock_validate.return_value = ([], [Mock(path="/path/file.pdf", error="corrompido")])

        # Mock dialog de subpasta
        mock_dialog = Mock()
        mock_dialog.result = "SIFAP"
        mock_dialog_class.return_value = mock_dialog

        parent = Mock()
        ents = {"CNPJ": Mock()}
        host = Mock()

        execute_upload_flow(parent, ents, client_id=1, host=host)

        mock_messagebox.showwarning.assert_called_once()
        args = mock_messagebox.showwarning.call_args[0]
        assert args[0] == "Envio"
        assert "file.pdf: corrompido" in args[1]

    @patch("src.modules.clientes.forms.client_form_upload_helpers.filedialog")
    @patch("src.modules.clientes.forms.client_form_upload_helpers.messagebox")
    @patch("src.modules.clientes.forms.client_form_upload_helpers.collect_pdfs_from_folder")
    @patch("src.modules.clientes.forms.client_form_upload_helpers.SubpastaDialog")
    def test_cancels_when_subfolder_dialog_cancelled(
        self, mock_dialog_class, mock_collect, mock_messagebox, mock_filedialog
    ):
        """Deve cancelar quando usuário cancela dialog de subpasta."""
        mock_filedialog.askdirectory.return_value = "/pasta"
        mock_collect.return_value = [Mock(path="/path/file.pdf", relative_path="file.pdf")]

        # Mock dialog de subpasta retornando None (cancelado)
        mock_dialog = Mock()
        mock_dialog.result = None
        mock_dialog_class.return_value = mock_dialog

        parent = Mock()
        ents = {"CNPJ": Mock()}
        host = Mock()

        execute_upload_flow(parent, ents, client_id=1, host=host)

        mock_messagebox.showinfo.assert_called_once_with(
            "Envio",
            "Envio cancelado.",
            parent=parent,
        )

    @patch("src.modules.clientes.forms.client_form_upload_helpers.filedialog")
    @patch("src.modules.clientes.forms.client_form_upload_helpers.messagebox")
    @patch("src.modules.clientes.forms.client_form_upload_helpers.collect_pdfs_from_folder")
    @patch("src.modules.clientes.forms.client_form_upload_helpers.validate_upload_files")
    @patch("src.modules.clientes.forms.client_form_upload_helpers.SubpastaDialog")
    def test_shows_warning_when_cnpj_missing(
        self, mock_dialog_class, mock_validate, mock_collect, mock_messagebox, mock_filedialog
    ):
        """Deve exibir aviso quando CNPJ está vazio."""
        mock_filedialog.askdirectory.return_value = "/pasta"
        mock_collect.return_value = [Mock(path="/path/file.pdf", relative_path="file.pdf")]
        mock_validate.return_value = ([Mock(path="/path/file.pdf")], [])

        # Mock dialog de subpasta
        mock_dialog = Mock()
        mock_dialog.result = "SIFAP"
        mock_dialog_class.return_value = mock_dialog

        parent = Mock()
        cnpj_entry = Mock()
        cnpj_entry.get.return_value = ""
        ents = {"CNPJ": cnpj_entry}
        host = Mock()

        execute_upload_flow(parent, ents, client_id=1, host=host)

        mock_messagebox.showwarning.assert_called_once_with(
            "Envio",
            "Informe o CNPJ antes de enviar.",
            parent=parent,
        )

    @patch("src.modules.clientes.forms.client_form_upload_helpers.filedialog")
    @patch("src.modules.clientes.forms.client_form_upload_helpers.messagebox")
    @patch("src.modules.clientes.forms.client_form_upload_helpers.collect_pdfs_from_folder")
    @patch("src.modules.clientes.forms.client_form_upload_helpers.validate_upload_files")
    @patch("src.modules.clientes.forms.client_form_upload_helpers.SubpastaDialog")
    @patch("src.modules.clientes.forms.client_form_upload_helpers.UploadDialog")
    @patch("src.modules.clientes.forms.client_form_upload_helpers.get_current_org_id")
    def test_executes_upload_dialog_with_valid_input(
        self,
        mock_get_org_id,
        mock_dialog_class,
        mock_subfolder_dialog_class,
        mock_validate,
        mock_collect,
        mock_messagebox,
        mock_filedialog,
    ):
        """Deve executar dialog de upload quando tudo está OK."""
        mock_filedialog.askdirectory.return_value = "/pasta"
        mock_collect.return_value = [Mock(path="/path/file.pdf", relative_path="file.pdf")]
        mock_validate.return_value = ([Mock(path="/path/file.pdf")], [])
        mock_get_org_id.return_value = "org123"

        # Mock dialog de subpasta
        mock_subfolder_dialog = Mock()
        mock_subfolder_dialog.result = "SIFAP"
        mock_subfolder_dialog_class.return_value = mock_subfolder_dialog

        parent = Mock()
        cnpj_entry = Mock()
        cnpj_entry.get.return_value = "12.345.678/0001-90"
        ents = {"CNPJ": cnpj_entry}
        host = Mock(supabase=Mock())

        execute_upload_flow(parent, ents, client_id=42, host=host)

        # Verifica que dialog foi criado e iniciado
        mock_dialog_class.assert_called_once()
        dialog_instance = mock_dialog_class.return_value
        dialog_instance.start.assert_called_once()

    @patch("src.modules.clientes.forms.client_form_upload_helpers.filedialog")
    @patch("src.modules.clientes.forms.client_form_upload_helpers.messagebox")
    @patch("src.modules.clientes.forms.client_form_upload_helpers.collect_pdfs_from_folder")
    @patch("src.modules.clientes.forms.client_form_upload_helpers.validate_upload_files")
    @patch("src.modules.clientes.forms.client_form_upload_helpers.SubpastaDialog")
    @patch("src.modules.clientes.forms.client_form_upload_helpers.get_current_org_id")
    def test_handles_exception_getting_org_id_gracefully(
        self,
        mock_get_org_id,
        mock_subfolder_dialog_class,
        mock_validate,
        mock_collect,
        mock_messagebox,
        mock_filedialog,
    ):
        """Deve continuar mesmo se get_current_org_id lançar exceção."""
        mock_filedialog.askdirectory.return_value = "/pasta"
        mock_collect.return_value = [Mock(path="/path/file.pdf", relative_path="file.pdf")]
        mock_validate.return_value = ([Mock(path="/path/file.pdf")], [])
        mock_get_org_id.side_effect = Exception("Org ID error")

        # Mock dialog de subpasta
        mock_subfolder_dialog = Mock()
        mock_subfolder_dialog.result = ""
        mock_subfolder_dialog_class.return_value = mock_subfolder_dialog

        parent = Mock()
        cnpj_entry = Mock()
        cnpj_entry.get.return_value = "12345678000190"
        ents = {"CNPJ": cnpj_entry}
        host = Mock(supabase=Mock())

        # Não deve lançar exceção
        with patch("src.modules.clientes.forms.client_form_upload_helpers.UploadDialog") as mock_dialog:
            mock_dialog.return_value.start = Mock()
            execute_upload_flow(parent, ents, client_id=1, host=host)

            # Dialog deve ser criado mesmo com erro no org_id
            mock_dialog.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
