"""Testes para open_pdf_viewer_from_download_result."""

from __future__ import annotations

from unittest.mock import Mock, patch


from src.modules.pdf_preview.view import open_pdf_viewer_from_download_result


class TestOpenPdfViewerFromDownloadResult:
    """Testes para helper de integração com mode='internal'."""

    @patch("src.modules.pdf_preview.view.open_pdf_viewer")
    def test_opens_viewer_with_valid_internal_result(self, mock_open: Mock):
        """Deve abrir viewer quando resultado é válido e mode=internal."""
        # Arrange
        download_result = {
            "ok": True,
            "mode": "internal",
            "temp_path": "/tmp/rc_gestor_uploads/documento.pdf",
            "display_name": "documento.pdf",
            "message": "Arquivo baixado com sucesso (modo interno)",
        }
        master = Mock()

        # Act
        result = open_pdf_viewer_from_download_result(master, download_result)

        # Assert
        mock_open.assert_called_once_with(
            master,
            pdf_path="/tmp/rc_gestor_uploads/documento.pdf",
            display_name="documento.pdf",
        )
        assert result is not None

    @patch("src.modules.pdf_preview.view.open_pdf_viewer")
    def test_returns_none_when_result_not_ok(self, mock_open: Mock):
        """Não deve abrir viewer se download falhou."""
        # Arrange
        download_result = {
            "ok": False,
            "message": "Erro no download",
            "error": "Arquivo não encontrado",
        }
        master = Mock()

        # Act
        result = open_pdf_viewer_from_download_result(master, download_result)

        # Assert
        mock_open.assert_not_called()
        assert result is None

    @patch("src.modules.pdf_preview.view.open_pdf_viewer")
    def test_returns_none_when_mode_is_not_internal(self, mock_open: Mock):
        """Não deve abrir viewer se mode não é 'internal'."""
        # Arrange
        download_result = {
            "ok": True,
            "mode": "external",
            "temp_path": "/tmp/rc_gestor_uploads/documento.pdf",
            "message": "Arquivo aberto com sucesso",
        }
        master = Mock()

        # Act
        result = open_pdf_viewer_from_download_result(master, download_result)

        # Assert
        mock_open.assert_not_called()
        assert result is None

    @patch("src.modules.pdf_preview.view.open_pdf_viewer")
    def test_returns_none_when_temp_path_missing(self, mock_open: Mock):
        """Não deve abrir viewer se temp_path ausente."""
        # Arrange
        download_result = {
            "ok": True,
            "mode": "internal",
            "message": "Erro ao criar temporário",
        }
        master = Mock()

        # Act
        result = open_pdf_viewer_from_download_result(master, download_result)

        # Assert
        mock_open.assert_not_called()
        assert result is None

    @patch("src.modules.pdf_preview.view.open_pdf_viewer")
    def test_works_without_display_name(self, mock_open: Mock):
        """Deve funcionar mesmo sem display_name."""
        # Arrange
        download_result = {
            "ok": True,
            "mode": "internal",
            "temp_path": "/tmp/rc_gestor_uploads/file.pdf",
        }
        master = Mock()

        # Act
        open_pdf_viewer_from_download_result(master, download_result)

        # Assert
        mock_open.assert_called_once_with(
            master,
            pdf_path="/tmp/rc_gestor_uploads/file.pdf",
            display_name=None,
        )
