# -*- coding: utf-8 -*-
"""Testes de upload para ClientesV2 - FASE 3.3.

Testa funcionalidade de upload de arquivos para cliente.
"""

from __future__ import annotations

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path


@pytest.fixture
def mock_upload_service():
    """Mock do serviço de upload."""
    with patch("src.modules.uploads.service.build_items_from_files") as mock:
        yield mock


@pytest.fixture
def mock_storage_api():
    """Mock da API de storage."""
    with (
        patch("src.adapters.storage.api.upload_file") as mock_upload,
        patch("src.adapters.storage.api.using_storage_backend") as mock_context,
    ):
        # Fazer o context manager funcionar
        mock_context.return_value.__enter__ = Mock()
        mock_context.return_value.__exit__ = Mock(return_value=False)
        yield {"upload": mock_upload, "context": mock_context}


def test_upload_dialog_opens_with_client_info(tk_root):
    """Test que dialog abre com informações do cliente."""
    from src.modules.clientes_v2.views.upload_dialog import ClientUploadDialog

    dialog = ClientUploadDialog(tk_root, client_id=123, client_name="Empresa Teste Ltda")

    # Verificar que dialog foi criado
    assert dialog.winfo_exists(), "Dialog deve existir"
    assert dialog.client_id == 123, "Client ID deve estar correto"
    assert dialog.client_name == "Empresa Teste Ltda", "Nome deve estar correto"

    # Verificar que botão upload está desabilitado inicialmente
    assert dialog.upload_btn.cget("state") == "disabled", "Botão upload deve estar desabilitado"

    dialog.destroy()


def test_upload_single_file_success(tk_root, mock_upload_service, mock_storage_api):
    """Test upload único bem-sucedido."""
    from src.modules.clientes_v2.views.upload_dialog import ClientUploadDialog

    # Mock do filedialog
    test_file = "C:/temp/documento.pdf"
    mock_filedialog = MagicMock(return_value=(test_file,))

    # Mock do build_items_from_files
    mock_upload_service.return_value = [
        {"local_path": test_file, "storage_key": "123/documento.pdf", "content_type": "application/pdf"}
    ]

    # Mock dos messageboxes
    mock_askyesno = MagicMock(return_value=True)  # Usuário confirma
    mock_showinfo = MagicMock()

    # Mock do ProgressDialog
    mock_progress = MagicMock()
    mock_progress_class = MagicMock(return_value=mock_progress)

    with (
        patch("tkinter.filedialog.askopenfilenames", mock_filedialog),
        patch("tkinter.messagebox.askyesno", mock_askyesno),
        patch("tkinter.messagebox.showinfo", mock_showinfo),
        patch("src.ui.components.progress_dialog.ProgressDialog", mock_progress_class),
    ):
        dialog = ClientUploadDialog(tk_root, client_id=123, client_name="Teste")

        # Simular seleção de arquivo
        dialog._select_files()

        # Verificar que arquivo foi selecionado
        assert len(dialog.selected_files) == 1, "Deve ter 1 arquivo selecionado"
        assert dialog.upload_btn.cget("state") == "normal", "Botão deve estar habilitado"

        # Simular upload
        dialog._do_upload()

        # Verificar que confirmação foi mostrada
        assert mock_askyesno.called, "Deve mostrar confirmação"

        # Verificar que upload foi chamado
        assert mock_storage_api["upload"].called, "Deve chamar upload_file"
        call_args = mock_storage_api["upload"].call_args[0]
        assert call_args[0] == test_file, "Deve fazer upload do arquivo correto"

        # Verificar que sucesso foi mostrado
        assert mock_showinfo.called, "Deve mostrar mensagem de sucesso"

        dialog.destroy()


def test_upload_multiple_files_success(tk_root, mock_upload_service, mock_storage_api):
    """Test upload múltiplo bem-sucedido."""
    from src.modules.clientes_v2.views.upload_dialog import ClientUploadDialog

    # Mock de múltiplos arquivos
    test_files = ["C:/temp/doc1.pdf", "C:/temp/doc2.pdf", "C:/temp/image.png"]
    mock_filedialog = MagicMock(return_value=test_files)

    # Mock do build_items_from_files
    mock_upload_service.return_value = [
        {"local_path": f, "storage_key": f"123/{Path(f).name}", "content_type": "application/pdf"} for f in test_files
    ]

    # Mock dos messageboxes
    mock_askyesno = MagicMock(return_value=True)
    mock_showinfo = MagicMock()

    # Mock do ProgressDialog
    mock_progress = MagicMock()
    mock_progress_class = MagicMock(return_value=mock_progress)

    with (
        patch("tkinter.filedialog.askopenfilenames", mock_filedialog),
        patch("tkinter.messagebox.askyesno", mock_askyesno),
        patch("tkinter.messagebox.showinfo", mock_showinfo),
        patch("src.ui.components.progress_dialog.ProgressDialog", mock_progress_class),
    ):
        dialog = ClientUploadDialog(tk_root, client_id=123)

        # Simular seleção de arquivos
        dialog._select_files()

        # Verificar que arquivos foram selecionados
        assert len(dialog.selected_files) == 3, "Deve ter 3 arquivos selecionados"

        # Simular upload
        dialog._do_upload()

        # Verificar que upload foi chamado 3 vezes
        assert mock_storage_api["upload"].call_count == 3, "Deve fazer 3 uploads"

        # Verificar que sucesso foi mostrado
        assert mock_showinfo.called, "Deve mostrar mensagem de sucesso"
        success_msg = mock_showinfo.call_args[0][1]
        assert "3" in success_msg, "Mensagem deve mencionar 3 arquivos"

        dialog.destroy()


def test_upload_validates_file_extension(tk_root):
    """Test que valida extensão de arquivo."""
    from src.modules.clientes_v2.views.upload_dialog import ClientUploadDialog

    dialog = ClientUploadDialog(tk_root, client_id=123)

    # Testar extensões válidas
    assert dialog._validate_file("doc.pdf"), "PDF deve ser válido"
    assert dialog._validate_file("image.png"), "PNG deve ser válido"
    assert dialog._validate_file("sheet.xlsx"), "XLSX deve ser válido"
    assert dialog._validate_file("archive.zip"), "ZIP deve ser válido"

    # Testar extensões inválidas
    assert not dialog._validate_file("script.exe"), "EXE não deve ser válido"
    assert not dialog._validate_file("code.py"), "PY não deve ser válido"
    assert not dialog._validate_file("video.mp4"), "MP4 não deve ser válido"

    dialog.destroy()


def test_upload_blocks_invalid_file_types(tk_root):
    """Test que bloqueia tipos de arquivo inválidos."""
    from src.modules.clientes_v2.views.upload_dialog import ClientUploadDialog

    # Mock de arquivos com um inválido
    test_files = [
        "C:/temp/doc.pdf",
        "C:/temp/malware.exe",  # Inválido
        "C:/temp/image.png",
    ]
    mock_filedialog = MagicMock(return_value=test_files)

    # Mock do warning
    mock_showwarning = MagicMock()

    with (
        patch("tkinter.filedialog.askopenfilenames", mock_filedialog),
        patch("tkinter.messagebox.showwarning", mock_showwarning),
    ):
        dialog = ClientUploadDialog(tk_root, client_id=123)

        # Simular seleção
        dialog._select_files()

        # Verificar que apenas arquivos válidos foram selecionados
        assert len(dialog.selected_files) == 2, "Deve ter apenas 2 arquivos válidos"
        assert "malware.exe" not in str(dialog.selected_files), "EXE não deve estar na lista"

        # Verificar que aviso foi mostrado
        assert mock_showwarning.called, "Deve mostrar aviso de arquivo inválido"
        warning_msg = mock_showwarning.call_args[0][1]
        assert "malware.exe" in warning_msg, "Aviso deve mencionar arquivo inválido"

        dialog.destroy()


def test_upload_handles_network_error(tk_root, mock_upload_service, mock_storage_api):
    """Test que trata erro de rede durante upload."""
    from src.modules.clientes_v2.views.upload_dialog import ClientUploadDialog

    # Mock do filedialog
    test_file = "C:/temp/documento.pdf"
    mock_filedialog = MagicMock(return_value=(test_file,))

    # Mock do build_items_from_files
    mock_upload_service.return_value = [
        {"local_path": test_file, "storage_key": "123/documento.pdf", "content_type": "application/pdf"}
    ]

    # Mock de erro de rede no upload
    mock_storage_api["upload"].side_effect = Exception("Network error: Connection timeout")

    # Mock dos messageboxes
    mock_askyesno = MagicMock(return_value=True)
    mock_showwarning = MagicMock()

    # Mock do ProgressDialog
    mock_progress = MagicMock()
    mock_progress_class = MagicMock(return_value=mock_progress)

    with (
        patch("tkinter.filedialog.askopenfilenames", mock_filedialog),
        patch("tkinter.messagebox.askyesno", mock_askyesno),
        patch("tkinter.messagebox.showwarning", mock_showwarning),
        patch("src.ui.components.progress_dialog.ProgressDialog", mock_progress_class),
    ):
        dialog = ClientUploadDialog(tk_root, client_id=123)

        # Simular seleção e upload
        dialog._select_files()
        dialog._do_upload()

        # Verificar que aviso foi mostrado (upload parcial/falha)
        assert mock_showwarning.called, "Deve mostrar aviso de falha"
        warning_msg = mock_showwarning.call_args[0][1]
        assert "0 de 1" in warning_msg, "Deve indicar que nenhum arquivo foi enviado"

        dialog.destroy()


def test_upload_handles_service_error(tk_root, mock_upload_service):
    """Test que trata erro do serviço de upload."""
    from src.modules.clientes_v2.views.upload_dialog import ClientUploadDialog

    # Mock do filedialog
    test_file = "C:/temp/documento.pdf"
    mock_filedialog = MagicMock(return_value=(test_file,))

    # Mock de erro no build_items_from_files
    mock_upload_service.side_effect = Exception("Service error: Invalid client ID")

    # Mock dos messageboxes
    mock_showerror = MagicMock()

    with (
        patch("tkinter.filedialog.askopenfilenames", mock_filedialog),
        patch("tkinter.messagebox.showerror", mock_showerror),
    ):
        dialog = ClientUploadDialog(tk_root, client_id=123)

        # Simular seleção
        dialog._select_files()

        # Simular upload (deve falhar)
        dialog._do_upload()

        # Verificar que erro foi mostrado
        assert mock_showerror.called, "Deve mostrar erro"
        error_msg = mock_showerror.call_args[0][1]
        assert "erro" in error_msg.lower(), "Deve mencionar erro"

        dialog.destroy()


def test_upload_user_cancels_confirmation(tk_root, mock_upload_service, mock_storage_api):
    """Test que respeita cancelamento do usuário na confirmação."""
    from src.modules.clientes_v2.views.upload_dialog import ClientUploadDialog

    # Mock do filedialog
    test_file = "C:/temp/documento.pdf"
    mock_filedialog = MagicMock(return_value=(test_file,))

    # Mock do build_items_from_files
    mock_upload_service.return_value = [
        {"local_path": test_file, "storage_key": "123/documento.pdf", "content_type": "application/pdf"}
    ]

    # Mock do messagebox retornando False (usuário cancelou)
    mock_askyesno = MagicMock(return_value=False)

    with (
        patch("tkinter.filedialog.askopenfilenames", mock_filedialog),
        patch("tkinter.messagebox.askyesno", mock_askyesno),
    ):
        dialog = ClientUploadDialog(tk_root, client_id=123)

        # Simular seleção e tentativa de upload
        dialog._select_files()
        dialog._do_upload()

        # Verificar que confirmação foi mostrada
        assert mock_askyesno.called, "Deve mostrar confirmação"

        # Verificar que upload NÃO foi chamado (usuário cancelou)
        assert not mock_storage_api["upload"].called, "Não deve fazer upload se cancelado"

        dialog.destroy()


def test_upload_callback_called_on_success(tk_root, mock_upload_service, mock_storage_api):
    """Test que callback é chamado após upload bem-sucedido."""
    from src.modules.clientes_v2.views.upload_dialog import ClientUploadDialog

    # Mock do callback
    mock_callback = MagicMock()

    # Mock do filedialog
    test_file = "C:/temp/documento.pdf"
    mock_filedialog = MagicMock(return_value=(test_file,))

    # Mock do build_items_from_files
    mock_upload_service.return_value = [
        {"local_path": test_file, "storage_key": "123/documento.pdf", "content_type": "application/pdf"}
    ]

    # Mock dos messageboxes
    mock_askyesno = MagicMock(return_value=True)
    mock_showinfo = MagicMock()

    # Mock do ProgressDialog
    mock_progress = MagicMock()
    mock_progress_class = MagicMock(return_value=mock_progress)

    with (
        patch("tkinter.filedialog.askopenfilenames", mock_filedialog),
        patch("tkinter.messagebox.askyesno", mock_askyesno),
        patch("tkinter.messagebox.showinfo", mock_showinfo),
        patch("src.ui.components.progress_dialog.ProgressDialog", mock_progress_class),
    ):
        dialog = ClientUploadDialog(tk_root, client_id=123, on_complete=mock_callback)

        # Simular seleção e upload
        dialog._select_files()
        dialog._do_upload()

        # Verificar que callback foi chamado
        assert mock_callback.called, "Callback deve ser chamado após sucesso"


def test_upload_format_size_helper(tk_root):
    """Test helper de formatação de tamanho."""
    from src.modules.clientes_v2.views.upload_dialog import ClientUploadDialog

    dialog = ClientUploadDialog(tk_root, client_id=123)

    # Testar diferentes tamanhos
    assert "500.0 B" in dialog._format_size(500)
    assert "KB" in dialog._format_size(2048)
    assert "MB" in dialog._format_size(5 * 1024 * 1024)
    assert "GB" in dialog._format_size(2 * 1024 * 1024 * 1024)

    dialog.destroy()
