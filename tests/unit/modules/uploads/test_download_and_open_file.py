"""Testes headless para download_and_open_file (service.py)."""

from __future__ import annotations

import sys
from unittest.mock import Mock, patch

import pytest

from src.modules.uploads.service import download_and_open_file


class TestDownloadAndOpenFile:
    """Testes para download_and_open_file()."""

    @patch("src.modules.uploads.service.create_temp_file")
    @patch("src.modules.uploads.service.download_file")
    @patch("src.modules.uploads.service.get_clients_bucket")
    @patch("os.startfile" if sys.platform.startswith("win") else "subprocess.Popen")
    def test_downloads_and_opens_file_successfully_windows(
        self,
        mock_opener: Mock,
        mock_get_bucket: Mock,
        mock_download: Mock,
        mock_create_temp: Mock,
    ):
        """Deve baixar arquivo e abrir no viewer (Windows)."""
        if not sys.platform.startswith("win"):
            pytest.skip("Teste específico para Windows")

        # Arrange
        mock_get_bucket.return_value = "bucket-clientes"
        mock_create_temp.return_value = Mock(
            path="C:\\Temp\\rc_gestor_uploads\\documento.pdf",
            directory="C:\\Temp\\rc_gestor_uploads",
            filename="documento.pdf",
        )
        mock_download.return_value = {"ok": True}

        # Act
        result = download_and_open_file("clientes/123/documento.pdf")

        # Assert
        assert result["ok"] is True
        assert result["message"] == "Arquivo aberto com sucesso"
        assert "temp_path" in result

        mock_create_temp.assert_called_once_with("documento.pdf")
        mock_download.assert_called_once_with(
            "bucket-clientes",
            "clientes/123/documento.pdf",
            "C:\\Temp\\rc_gestor_uploads\\documento.pdf",
        )
        mock_opener.assert_called_once_with("C:\\Temp\\rc_gestor_uploads\\documento.pdf")

    @patch("src.modules.uploads.service.create_temp_file")
    @patch("src.modules.uploads.service.download_file")
    @patch("src.modules.uploads.service.get_clients_bucket")
    @patch("subprocess.Popen")
    def test_downloads_and_opens_file_successfully_linux(
        self,
        mock_popen: Mock,
        mock_get_bucket: Mock,
        mock_download: Mock,
        mock_create_temp: Mock,
    ):
        """Deve baixar arquivo e abrir no viewer (Linux)."""
        if sys.platform.startswith("win") or sys.platform == "darwin":
            pytest.skip("Teste específico para Linux")

        # Arrange
        mock_get_bucket.return_value = "bucket-clientes"
        mock_create_temp.return_value = Mock(
            path="/tmp/rc_gestor_uploads/documento.pdf",
            directory="/tmp/rc_gestor_uploads",
            filename="documento.pdf",
        )
        mock_download.return_value = {"ok": True}

        # Act
        result = download_and_open_file("clientes/123/documento.pdf")

        # Assert
        assert result["ok"] is True
        mock_popen.assert_called_once_with(["xdg-open", "/tmp/rc_gestor_uploads/documento.pdf"])

    @patch("src.modules.uploads.service.create_temp_file")
    @patch("src.modules.uploads.service.download_file")
    @patch("src.modules.uploads.service.get_clients_bucket")
    def test_handles_download_failure(
        self,
        mock_get_bucket: Mock,
        mock_download: Mock,
        mock_create_temp: Mock,
    ):
        """Se download falhar, deve retornar erro."""
        # Arrange
        mock_get_bucket.return_value = "bucket-clientes"
        mock_create_temp.return_value = Mock(
            path="/tmp/rc_gestor_uploads/documento.pdf",
            directory="/tmp/rc_gestor_uploads",
            filename="documento.pdf",
        )
        mock_download.return_value = {
            "ok": False,
            "message": "Erro de rede ao baixar arquivo",
        }

        # Act
        result = download_and_open_file("clientes/123/documento.pdf")

        # Assert
        assert result["ok"] is False
        assert "Erro de rede" in result["message"]
        assert "error" in result

    @patch("src.modules.uploads.service.create_temp_file")
    @patch("src.modules.uploads.service.get_clients_bucket")
    def test_handles_temp_file_creation_error(
        self,
        mock_get_bucket: Mock,
        mock_create_temp: Mock,
    ):
        """Se criar arquivo temporário falhar, deve retornar erro."""
        # Arrange
        mock_get_bucket.return_value = "bucket-clientes"
        mock_create_temp.side_effect = OSError("Disco cheio")

        # Act
        result = download_and_open_file("clientes/123/documento.pdf")

        # Assert
        assert result["ok"] is False
        assert "Erro ao preparar arquivo temporário" in result["message"]
        assert result["error"] == "Disco cheio"

    @patch("src.modules.uploads.service.create_temp_file")
    @patch("src.modules.uploads.service.download_file")
    @patch("src.modules.uploads.service.get_clients_bucket")
    @patch("os.startfile" if sys.platform.startswith("win") else "subprocess.Popen")
    def test_handles_viewer_open_error(
        self,
        mock_opener: Mock,
        mock_get_bucket: Mock,
        mock_download: Mock,
        mock_create_temp: Mock,
    ):
        """Se abrir viewer falhar, deve retornar erro mas manter temp_path."""
        # Arrange
        mock_get_bucket.return_value = "bucket-clientes"
        mock_create_temp.return_value = Mock(
            path="/tmp/rc_gestor_uploads/documento.pdf",
            directory="/tmp/rc_gestor_uploads",
            filename="documento.pdf",
        )
        mock_download.return_value = {"ok": True}
        mock_opener.side_effect = OSError("Nenhum aplicativo associado")

        # Act
        result = download_and_open_file("clientes/123/documento.pdf")

        # Assert
        assert result["ok"] is False
        assert "não foi possível abri-lo" in result["message"]
        assert "temp_path" in result  # Path está disponível
        assert result["error"] == "Nenhum aplicativo associado"

    @patch("src.modules.uploads.service.create_temp_file")
    @patch("src.modules.uploads.service.get_clients_bucket")
    def test_uses_custom_bucket_when_provided(
        self,
        mock_get_bucket: Mock,
        mock_create_temp: Mock,
    ):
        """Deve usar bucket customizado se fornecido."""
        # Arrange
        mock_create_temp.return_value = Mock(
            path="/tmp/rc_gestor_uploads/documento.pdf",
            directory="/tmp/rc_gestor_uploads",
            filename="documento.pdf",
        )

        with patch("src.modules.uploads.service.download_file") as mock_download:
            mock_download.return_value = {"ok": False, "message": "erro"}

            # Act
            download_and_open_file("docs/relatorio.pdf", bucket="bucket-custom")

            # Assert
            mock_get_bucket.assert_not_called()
            mock_download.assert_called_once()
            assert mock_download.call_args[0][0] == "bucket-custom"

    def test_rejects_invalid_mode(self):
        """Deve levantar ValueError se mode for inválido."""
        with pytest.raises(ValueError, match="Modo inválido"):
            download_and_open_file("file.pdf", mode="invalid")

    @patch("src.modules.uploads.service.create_temp_file")
    @patch("src.modules.uploads.service.get_clients_bucket")
    def test_internal_mode_returns_not_implemented(
        self,
        mock_get_bucket: Mock,
        mock_create_temp: Mock,
    ):
        """Mode 'internal' deve baixar arquivo e retornar path para caller."""
        # Arrange
        mock_get_bucket.return_value = "bucket-clientes"
        mock_create_temp.return_value = Mock(
            path="/tmp/rc_gestor_uploads/documento.pdf",
            directory="/tmp/rc_gestor_uploads",
            filename="documento.pdf",
        )

        with patch("src.modules.uploads.service.download_file") as mock_download:
            mock_download.return_value = {"ok": True}

            # Act
            result = download_and_open_file("clientes/123/documento.pdf", mode="internal")

            # Assert
            assert result["ok"] is True
            assert result["mode"] == "internal"
            assert result["temp_path"] == "/tmp/rc_gestor_uploads/documento.pdf"
            assert result["display_name"] == "documento.pdf"
            assert "Arquivo baixado com sucesso (modo interno)" in result["message"]

    @patch("src.modules.uploads.service.create_temp_file")
    @patch("src.modules.uploads.service.download_file")
    @patch("src.modules.uploads.service.get_clients_bucket")
    @patch("os.path.getsize")
    @patch("os.startfile" if sys.platform.startswith("win") else "subprocess.Popen")
    def test_logs_file_size_and_download_time(
        self,
        mock_opener: Mock,
        mock_getsize: Mock,
        mock_get_bucket: Mock,
        mock_download: Mock,
        mock_create_temp: Mock,
    ):
        """Deve logar tamanho do arquivo e tempo de download."""
        # Arrange
        mock_get_bucket.return_value = "bucket-clientes"
        mock_create_temp.return_value = Mock(
            path="/tmp/rc_gestor_uploads/documento.pdf",
            directory="/tmp/rc_gestor_uploads",
            filename="documento.pdf",
        )
        mock_download.return_value = {"ok": True}
        mock_getsize.return_value = 102400  # 100 KB

        # Act
        result = download_and_open_file("clientes/123/documento.pdf")

        # Assert
        assert result["ok"] is True
        mock_getsize.assert_called_once()
