"""Testes adicionales da FASE 8 para external_upload_service."""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import src.modules.uploads.external_upload_service as external_service_module
import src.modules.uploads.file_validator as file_validator_module
from src.modules.uploads.external_upload_service import salvar_e_enviar_para_supabase_service
from src.modules.uploads.file_validator import PDF_MAGIC


@pytest.fixture
def valid_pdf(tmp_path: Path) -> Path:
    """Cria um PDF válido."""
    pdf = tmp_path / "valid.pdf"
    pdf.write_bytes(PDF_MAGIC + b"data")
    return pdf


@pytest.fixture
def invalid_txt(tmp_path: Path) -> Path:
    """Cria um arquivo TXT inválido para upload."""
    txt = tmp_path / "invalid.txt"
    txt.write_text("conteudo")
    return txt


class TestExternalUploadValidation:
    """Cobertura para validação OWASP e rate limit."""

    @patch("src.modules.uploads.external_upload_service.is_really_online", return_value=True)
    @patch("src.modules.uploads.external_upload_service.upload_files_to_supabase", return_value=(1, 0))
    @patch("src.modules.uploads.external_upload_service.build_items_from_files")
    def test_only_valid_files_are_processed(
        self,
        mock_build_items,
        mock_upload,
        _mock_is_online,
        valid_pdf: Path,
        invalid_txt: Path,
    ) -> None:
        """Garante que PDFs válidos seguem e inválidos populam errors."""
        mock_build_items.return_value = [{"path": str(valid_pdf)}]
        ctx = {
            "files": [str(valid_pdf), str(invalid_txt)],
            "self": MagicMock(),
            "ents": {},
            "row": None,
        }
        real_validate = file_validator_module.validate_upload_file

        with patch(
            "src.modules.uploads.external_upload_service.validate_upload_file",
            side_effect=lambda path: real_validate(path),
        ) as mock_validate:
            result = salvar_e_enviar_para_supabase_service(ctx)

        assert mock_validate.call_count == 2
        mock_build_items.assert_called_once_with([str(valid_pdf)])
        mock_upload.assert_called_once()
        assert result["ok"] is True
        assert any("txt" in err.lower() or "extens" in err.lower() for err in result["errors"])
        stats = result.get("stats") or {}
        assert stats.get("total_selected") == 2
        assert stats.get("total_validated") == 1
        assert stats.get("total_invalid") == 1

    @patch("src.modules.uploads.external_upload_service.is_really_online", return_value=True)
    @patch("src.modules.uploads.external_upload_service.upload_files_to_supabase")
    @patch("src.modules.uploads.external_upload_service.build_items_from_files")
    def test_all_invalid_files_stop_flow(
        self,
        mock_build_items,
        mock_upload,
        _mock_is_online,
        invalid_txt: Path,
        tmp_path: Path,
    ) -> None:
        """Nenhum arquivo válido deve impedir chamadas ao adapter."""
        extra_txt = tmp_path / "second.txt"
        extra_txt.write_text("foo")
        ctx = {
            "files": [str(invalid_txt), str(extra_txt)],
            "self": MagicMock(),
            "ents": {},
        }
        real_validate = file_validator_module.validate_upload_file

        with patch(
            "src.modules.uploads.external_upload_service.validate_upload_file",
            side_effect=lambda path: real_validate(path),
        ):
            result = salvar_e_enviar_para_supabase_service(ctx)

        mock_build_items.assert_not_called()
        mock_upload.assert_not_called()
        assert result["ok"] is False
        assert result["should_show_ui"] is True
        assert result["ui_message_type"] == "warning"
        assert "válido" in result["ui_message_title"].lower()
        stats = result.get("stats") or {}
        assert stats.get("total_selected") == 2
        assert stats.get("total_validated") == 0
        assert stats.get("total_invalid") == 2
        assert result["errors"]

    @patch("src.modules.uploads.external_upload_service.is_really_online", return_value=True)
    @patch("src.modules.uploads.external_upload_service.upload_files_to_supabase", return_value=(3, 0))
    @patch("src.modules.uploads.external_upload_service.build_items_from_files")
    def test_without_batch_limit_all_files_are_used(
        self,
        mock_build_items,
        mock_upload,
        _mock_is_online,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """MAX_FILES_PER_BATCH=0 deve processar todos os arquivos."""
        monkeypatch.setattr(external_service_module, "MAX_FILES_PER_BATCH", 0)
        files = []
        for idx in range(3):
            pdf = tmp_path / f"doc{idx}.pdf"
            pdf.write_bytes(PDF_MAGIC + b"payload")
            files.append(pdf)

        mock_build_items.return_value = [{"path": str(p)} for p in files]
        real_validate = file_validator_module.validate_upload_file

        with patch(
            "src.modules.uploads.external_upload_service.validate_upload_file",
            side_effect=lambda path: real_validate(path),
        ) as mock_validate:
            result = salvar_e_enviar_para_supabase_service(
                {"files": [str(p) for p in files], "self": MagicMock(), "ents": {}}
            )

        assert mock_validate.call_count == 3
        mock_build_items.assert_called_once()
        mock_upload.assert_called_once()
        assert mock_build_items.call_args[0][0] == [str(p) for p in files]
        assert "limitado" not in " ".join(result["errors"]).lower()
        assert result["ok"] is True
        stats = result.get("stats") or {}
        assert stats.get("total_selected") == 3
        assert stats.get("total_validated") == 3
        assert stats.get("total_skipped_by_limit") == 0

    @patch("src.modules.uploads.external_upload_service.is_really_online", return_value=True)
    @patch("src.modules.uploads.external_upload_service.upload_files_to_supabase", return_value=(1, 0))
    @patch("src.modules.uploads.external_upload_service.build_items_from_files")
    def test_batch_limit_truncates_file_list(
        self,
        mock_build_items,
        mock_upload,
        _mock_is_online,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Aplica limite de arquivos por lote e registra warning estruturado."""
        monkeypatch.setattr(external_service_module, "MAX_FILES_PER_BATCH", 1)
        files = []
        for idx in range(3):
            pdf = tmp_path / f"item{idx}.pdf"
            pdf.write_bytes(PDF_MAGIC + b"dados")
            files.append(pdf)

        mock_build_items.return_value = [{"path": str(files[0])}]
        real_validate = file_validator_module.validate_upload_file

        caplog.set_level(logging.WARNING)
        with patch(
            "src.modules.uploads.external_upload_service.validate_upload_file",
            side_effect=lambda path: real_validate(path),
        ) as mock_validate:
            result = salvar_e_enviar_para_supabase_service(
                {"files": [str(p) for p in files], "self": MagicMock(), "ents": {}}
            )

        assert mock_validate.call_count == 1
        mock_build_items.assert_called_once_with([str(files[0])])
        mock_upload.assert_called_once()
        assert any("limite" in err.lower() for err in result["errors"])

        stats = result.get("stats") or {}
        assert stats.get("total_selected") == 3
        assert stats.get("total_validated") == 1
        assert stats.get("total_skipped_by_limit") == 2

        warning_records = [record for record in caplog.records if record.levelname == "WARNING"]
        assert any(getattr(record, "skipped", None) == 2 for record in warning_records)
