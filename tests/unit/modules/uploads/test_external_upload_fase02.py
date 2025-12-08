# -*- coding: utf-8 -*-
"""Testes adicionais para src/modules/uploads/external_upload_service.py - Coverage Pack 02.

Foco em branches não cobertas:
- Exceções de rede e timeout
- Tratamento de CNPJ inválido/vazio
- Erros no build_items_from_files
- Erros no upload_files_to_supabase
- Estados instáveis de conexão
- Exceções genéricas
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.modules.uploads.external_upload_service import salvar_e_enviar_para_supabase_service
from src.modules.uploads.file_validator import FileValidationResult


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def base_context():
    """Contexto base para testes."""
    return {
        "files": ["file1.pdf"],
        "self": MagicMock(),
        "ents": {},
        "row": None,
        "win": None,
    }


@pytest.fixture(autouse=True)
def _stub_validate_upload_file(monkeypatch: pytest.MonkeyPatch):
    """Permite que os testes usem caminhos fake sem tocar no disco."""

    def _fake_validate(path, **kwargs):
        file_path = Path(path)
        ext = file_path.suffix.lower() or ".pdf"
        return FileValidationResult(valid=True, path=file_path, size_bytes=1, extension=ext)

    monkeypatch.setattr(
        "src.modules.uploads.external_upload_service.validate_upload_file",
        _fake_validate,
    )


# ============================================================================
# TESTES - Exceções genéricas
# ============================================================================


@patch("src.modules.uploads.external_upload_service.is_really_online")
def test_service_handles_generic_exception(mock_is_online, base_context):
    """Testa que service captura exceção genérica e retorna erro."""
    mock_is_online.side_effect = Exception("Unexpected error")

    result = salvar_e_enviar_para_supabase_service(base_context)

    assert result["ok"] is False
    assert "Erro inesperado" in result["message"]
    assert len(result["errors"]) > 0


@patch("src.modules.uploads.external_upload_service.is_really_online")
@patch("src.modules.uploads.external_upload_service.build_items_from_files")
def test_service_handles_exception_in_build_items(mock_build, mock_is_online, base_context):
    """Testa que service trata exceção em build_items_from_files."""
    mock_is_online.return_value = True
    mock_build.side_effect = Exception("Failed to build items")

    result = salvar_e_enviar_para_supabase_service(base_context)

    assert result["ok"] is False
    assert "Erro inesperado" in result["message"]


@patch("src.modules.uploads.external_upload_service.is_really_online")
@patch("src.modules.uploads.external_upload_service.build_items_from_files")
@patch("src.modules.uploads.external_upload_service.upload_files_to_supabase")
def test_service_handles_exception_in_upload(mock_upload, mock_build, mock_is_online, base_context):
    """Testa que service trata exceção em upload_files_to_supabase."""
    mock_is_online.return_value = True
    mock_build.return_value = [{"path": "file1.pdf"}]
    mock_upload.side_effect = Exception("Upload failed")

    result = salvar_e_enviar_para_supabase_service(base_context)

    assert result["ok"] is False
    assert "Erro inesperado" in result["message"]


# ============================================================================
# TESTES - Estados de conexão
# ============================================================================


@patch("src.modules.uploads.external_upload_service.is_really_online")
@patch("src.modules.uploads.external_upload_service.get_supabase_state")
def test_service_handles_unstable_connection(mock_get_state, mock_is_online, base_context):
    """Testa que service detecta conexão instável."""
    mock_is_online.return_value = False
    mock_get_state.return_value = ("unstable", "Network fluctuation detected")

    result = salvar_e_enviar_para_supabase_service(base_context)

    assert result["ok"] is False
    assert result["should_show_ui"] is True
    assert result["ui_message_type"] == "warning"
    assert "Conexão Instável" in result["ui_message_title"]
    assert "instável" in result["ui_message_body"]


@patch("src.modules.uploads.external_upload_service.is_really_online")
@patch("src.modules.uploads.external_upload_service.get_supabase_state")
def test_service_handles_offline_state(mock_get_state, mock_is_online, base_context):
    """Testa que service detecta sistema offline."""
    mock_is_online.return_value = False
    mock_get_state.return_value = ("offline", "No network detected")

    result = salvar_e_enviar_para_supabase_service(base_context)

    assert result["ok"] is False
    assert result["should_show_ui"] is True
    assert "Offline" in result["ui_message_title"]


# ============================================================================
# TESTES - Validação de arquivos
# ============================================================================


@patch("src.modules.uploads.external_upload_service.is_really_online")
def test_service_validates_empty_files_list(mock_is_online):
    """Testa validação quando lista de arquivos está vazia."""
    mock_is_online.return_value = True

    ctx = {"files": [], "self": MagicMock()}
    result = salvar_e_enviar_para_supabase_service(ctx)

    assert result["ok"] is False
    assert result["should_show_ui"] is True
    assert result["ui_message_type"] == "info"
    assert "Nenhum arquivo selecionado" in result["ui_message_body"]


@patch("src.modules.uploads.external_upload_service.is_really_online")
def test_service_validates_none_files(mock_is_online):
    """Testa validação quando files é None."""
    mock_is_online.return_value = True

    ctx = {"self": MagicMock()}  # files não presente
    result = salvar_e_enviar_para_supabase_service(ctx)

    assert result["ok"] is False
    assert "Nenhum arquivo selecionado" in result["ui_message_body"]


@patch("src.modules.uploads.external_upload_service.is_really_online")
@patch("src.modules.uploads.external_upload_service.build_items_from_files")
def test_service_validates_no_valid_pdfs(mock_build, mock_is_online, base_context):
    """Testa validação quando não há PDFs válidos."""
    mock_is_online.return_value = True
    mock_build.return_value = []  # Nenhum item válido

    result = salvar_e_enviar_para_supabase_service(base_context)

    assert result["ok"] is False
    assert result["should_show_ui"] is True
    assert result["ui_message_type"] == "warning"
    assert "Nenhum PDF valido" in result["ui_message_body"]


# ============================================================================
# TESTES - Extração de CNPJ
# ============================================================================


@patch("src.modules.uploads.external_upload_service.is_really_online")
@patch("src.modules.uploads.external_upload_service.build_items_from_files")
@patch("src.modules.uploads.external_upload_service.upload_files_to_supabase")
def test_service_extracts_cnpj_from_widget(mock_upload, mock_build, mock_is_online):
    """Testa extração de CNPJ do widget."""
    mock_is_online.return_value = True
    mock_build.return_value = [{"path": "file1.pdf"}]
    mock_upload.return_value = (1, 0)

    mock_widget = MagicMock()
    mock_widget.get.return_value = "  12.345.678/0001-99  "

    ctx = {
        "files": ["file1.pdf"],
        "self": MagicMock(),
        "ents": {"CNPJ": mock_widget},
        "row": None,
    }

    salvar_e_enviar_para_supabase_service(ctx)

    # Verifica que CNPJ foi extraído e trimmed
    call_args = mock_upload.call_args
    cliente = call_args[0][1]
    assert cliente["cnpj"] == "12.345.678/0001-99"


@patch("src.modules.uploads.external_upload_service.is_really_online")
@patch("src.modules.uploads.external_upload_service.build_items_from_files")
@patch("src.modules.uploads.external_upload_service.upload_files_to_supabase")
def test_service_handles_cnpj_widget_exception(mock_upload, mock_build, mock_is_online):
    """Testa que service trata exceção ao obter CNPJ do widget."""
    mock_is_online.return_value = True
    mock_build.return_value = [{"path": "file1.pdf"}]
    mock_upload.return_value = (1, 0)

    mock_widget = MagicMock()
    mock_widget.get.side_effect = Exception("Widget error")

    ctx = {
        "files": ["file1.pdf"],
        "self": MagicMock(),
        "ents": {"CNPJ": mock_widget},
        "row": None,
    }

    result = salvar_e_enviar_para_supabase_service(ctx)

    # Deve continuar com CNPJ vazio
    assert result["ok"] is True
    call_args = mock_upload.call_args
    cliente = call_args[0][1]
    assert cliente["cnpj"] == ""


@patch("src.modules.uploads.external_upload_service.is_really_online")
@patch("src.modules.uploads.external_upload_service.build_items_from_files")
@patch("src.modules.uploads.external_upload_service.upload_files_to_supabase")
def test_service_extracts_cnpj_from_row(mock_upload, mock_build, mock_is_online):
    """Testa extração de CNPJ da row quando widget não disponível."""
    mock_is_online.return_value = True
    mock_build.return_value = [{"path": "file1.pdf"}]
    mock_upload.return_value = (1, 0)

    ctx = {
        "files": ["file1.pdf"],
        "self": MagicMock(),
        "ents": {},  # Sem widget CNPJ
        "row": [1, "ACME Corp", "  98.765.432/0001-11  "],
    }

    salvar_e_enviar_para_supabase_service(ctx)

    # Verifica que CNPJ foi extraído da row
    call_args = mock_upload.call_args
    cliente = call_args[0][1]
    assert cliente["cnpj"] == "98.765.432/0001-11"


@patch("src.modules.uploads.external_upload_service.is_really_online")
@patch("src.modules.uploads.external_upload_service.build_items_from_files")
@patch("src.modules.uploads.external_upload_service.upload_files_to_supabase")
def test_service_handles_row_exception(mock_upload, mock_build, mock_is_online):
    """Testa que service trata exceção ao obter CNPJ da row."""
    mock_is_online.return_value = True
    mock_build.return_value = [{"path": "file1.pdf"}]
    mock_upload.return_value = (1, 0)

    ctx = {
        "files": ["file1.pdf"],
        "self": MagicMock(),
        "ents": {},
        "row": ["invalid"],  # Row sem CNPJ no index 2
    }

    result = salvar_e_enviar_para_supabase_service(ctx)

    # Deve continuar com CNPJ vazio
    assert result["ok"] is True


@patch("src.modules.uploads.external_upload_service.is_really_online")
@patch("src.modules.uploads.external_upload_service.build_items_from_files")
@patch("src.modules.uploads.external_upload_service.upload_files_to_supabase")
def test_service_handles_empty_cnpj(mock_upload, mock_build, mock_is_online):
    """Testa que service aceita CNPJ vazio."""
    mock_is_online.return_value = True
    mock_build.return_value = [{"path": "file1.pdf"}]
    mock_upload.return_value = (1, 0)

    ctx = {
        "files": ["file1.pdf"],
        "self": MagicMock(),
        "ents": {},
        "row": None,
    }

    result = salvar_e_enviar_para_supabase_service(ctx)

    assert result["ok"] is True
    call_args = mock_upload.call_args
    cliente = call_args[0][1]
    assert cliente["cnpj"] == ""


# ============================================================================
# TESTES - Contexto e referências
# ============================================================================


@patch("src.modules.uploads.external_upload_service.is_really_online")
@patch("src.modules.uploads.external_upload_service.build_items_from_files")
def test_service_validates_self_reference(mock_build, mock_is_online):
    """Testa que service valida presença de self no contexto."""
    mock_is_online.return_value = True
    mock_build.return_value = [{"path": "file1.pdf"}]

    ctx = {
        "files": ["file1.pdf"],
        "self": None,  # self ausente
        "ents": {},
    }

    result = salvar_e_enviar_para_supabase_service(ctx)

    assert result["ok"] is False
    assert any("Referência ao app (self)" in err for err in result["errors"])
    assert "contexto inválido" in result["message"]


@patch("src.modules.uploads.external_upload_service.is_really_online")
@patch("src.modules.uploads.external_upload_service.build_items_from_files")
@patch("src.modules.uploads.external_upload_service.upload_files_to_supabase")
def test_service_uses_win_as_parent(mock_upload, mock_build, mock_is_online):
    """Testa que service usa win como parent quando disponível."""
    mock_is_online.return_value = True
    mock_build.return_value = [{"path": "file1.pdf"}]
    mock_upload.return_value = (1, 0)

    mock_win = MagicMock()
    ctx = {
        "files": ["file1.pdf"],
        "self": MagicMock(),
        "ents": {},
        "win": mock_win,
    }

    salvar_e_enviar_para_supabase_service(ctx)

    # Verifica que parent é win
    call_args = mock_upload.call_args
    parent = call_args[1]["parent"]
    assert parent is mock_win


@patch("src.modules.uploads.external_upload_service.is_really_online")
@patch("src.modules.uploads.external_upload_service.build_items_from_files")
@patch("src.modules.uploads.external_upload_service.upload_files_to_supabase")
def test_service_uses_self_as_parent_when_no_win(mock_upload, mock_build, mock_is_online):
    """Testa que service usa self como parent quando win não disponível."""
    mock_is_online.return_value = True
    mock_build.return_value = [{"path": "file1.pdf"}]
    mock_upload.return_value = (1, 0)

    mock_self = MagicMock()
    ctx = {
        "files": ["file1.pdf"],
        "self": mock_self,
        "ents": {},
        "win": None,
    }

    salvar_e_enviar_para_supabase_service(ctx)

    # Verifica que parent é self
    call_args = mock_upload.call_args
    parent = call_args[1]["parent"]
    assert parent is mock_self


# ============================================================================
# TESTES - Resultados de upload
# ============================================================================


@patch("src.modules.uploads.external_upload_service.is_really_online")
@patch("src.modules.uploads.external_upload_service.build_items_from_files")
@patch("src.modules.uploads.external_upload_service.upload_files_to_supabase")
def test_service_returns_success_with_counts(mock_upload, mock_build, mock_is_online, base_context):
    """Testa que service retorna sucesso com contadores corretos."""
    mock_is_online.return_value = True
    mock_build.return_value = [{"path": f"file{i}.pdf"} for i in range(5)]
    mock_upload.return_value = (5, 0)

    result = salvar_e_enviar_para_supabase_service(base_context)

    assert result["ok"] is True
    assert result["result"] == (5, 0)
    assert "5 sucesso(s), 0 falha(s)" in result["message"]


@patch("src.modules.uploads.external_upload_service.is_really_online")
@patch("src.modules.uploads.external_upload_service.build_items_from_files")
@patch("src.modules.uploads.external_upload_service.upload_files_to_supabase")
def test_service_returns_partial_success(mock_upload, mock_build, mock_is_online, base_context):
    """Testa que service retorna sucesso parcial quando há falhas."""
    mock_is_online.return_value = True
    mock_build.return_value = [{"path": f"file{i}.pdf"} for i in range(3)]
    mock_upload.return_value = (2, 1)  # 2 ok, 1 failed

    result = salvar_e_enviar_para_supabase_service(base_context)

    assert result["ok"] is True
    assert result["result"] == (2, 1)
    assert "2 sucesso(s), 1 falha(s)" in result["message"]


@patch("src.modules.uploads.external_upload_service.is_really_online")
@patch("src.modules.uploads.external_upload_service.build_items_from_files")
@patch("src.modules.uploads.external_upload_service.upload_files_to_supabase")
def test_service_returns_all_failures(mock_upload, mock_build, mock_is_online, base_context):
    """Testa que service retorna quando todos uploads falham."""
    mock_is_online.return_value = True
    mock_build.return_value = [{"path": f"file{i}.pdf"} for i in range(3)]
    mock_upload.return_value = (0, 3)  # Todos falharam

    result = salvar_e_enviar_para_supabase_service(base_context)

    assert result["ok"] is True  # Service executa com sucesso
    assert result["result"] == (0, 3)
    assert "0 sucesso(s), 3 falha(s)" in result["message"]


# ============================================================================
# TESTES - Logging
# ============================================================================


@patch("src.modules.uploads.external_upload_service.is_really_online")
@patch("src.modules.uploads.external_upload_service.build_items_from_files")
@patch("src.modules.uploads.external_upload_service.upload_files_to_supabase")
def test_service_logs_upload_execution(mock_upload, mock_build, mock_is_online, base_context):
    """Testa que service faz log da execução do upload."""
    mock_is_online.return_value = True
    mock_build.return_value = [{"path": "file1.pdf"}, {"path": "file2.pdf"}]
    mock_upload.return_value = (2, 0)

    with patch("src.modules.uploads.external_upload_service.log") as mock_log:
        salvar_e_enviar_para_supabase_service(base_context)

        # Verifica que log.info foi chamado
        assert any("Executando upload_files_to_supabase" in str(call) for call in mock_log.info.call_args_list)
        assert any("Upload concluído" in str(call) for call in mock_log.info.call_args_list)


@patch("src.modules.uploads.external_upload_service.is_really_online")
@patch("src.modules.uploads.external_upload_service.get_supabase_state")
def test_service_logs_offline_warning(mock_get_state, mock_is_online, base_context):
    """Testa que service faz log de warning quando offline."""
    mock_is_online.return_value = False
    mock_get_state.return_value = ("offline", "No connection")

    with patch("src.modules.uploads.external_upload_service.log") as mock_log:
        salvar_e_enviar_para_supabase_service(base_context)

        # Verifica que log.warning foi chamado
        assert mock_log.warning.called


@patch("src.modules.uploads.external_upload_service.is_really_online")
@patch("src.modules.uploads.external_upload_service.build_items_from_files")
@patch("src.modules.uploads.external_upload_service.upload_files_to_supabase")
def test_service_logs_errors(mock_upload, mock_build, mock_is_online, base_context):
    """Testa que service faz log de erros."""
    mock_is_online.return_value = True
    mock_build.return_value = [{"path": "file1.pdf"}]
    mock_upload.side_effect = Exception("Critical error")

    with patch("src.modules.uploads.external_upload_service.log") as mock_log:
        salvar_e_enviar_para_supabase_service(base_context)

        # Verifica que log.error foi chamado
        assert mock_log.error.called
