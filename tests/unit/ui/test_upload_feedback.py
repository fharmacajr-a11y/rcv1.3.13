from __future__ import annotations

from unittest.mock import patch

from src.ui.components.upload_feedback import (
    build_upload_message_info,
    show_upload_result_message,
)


def test_build_upload_message_info_includes_stats_summary() -> None:
    """Resumo deve incluir contadores quando stats disponíveis."""
    result = {
        "ok": True,
        "should_show_ui": True,
        "ui_message_type": "info",
        "ui_message_title": "Envio concluído",
        "ui_message_body": "Arquivos enviados com sucesso.",
        "stats": {
            "total_selected": 5,
            "total_validated": 3,
            "total_invalid": 1,
            "total_skipped_by_limit": 1,
        },
    }

    should_show, message_type, title, body = build_upload_message_info(result)

    assert should_show is True
    assert message_type == "info"
    assert title == "Envio concluído"
    assert "Arquivos selecionados: 5" in body
    assert "Arquivos enviados: 3" in body
    assert "Arquivos recusados na validação: 1" in body
    assert "Arquivos ignorados pelo limite de lote: 1" in body


@patch("src.ui.components.upload_feedback.messagebox.showinfo")
@patch("src.ui.components.upload_feedback.messagebox.showerror")
@patch("src.ui.components.upload_feedback.messagebox.showwarning")
def test_show_upload_result_message_uses_message_type(mock_warning, mock_error, mock_info) -> None:
    """Deve acionar o tipo correto de messagebox."""
    result = {
        "should_show_ui": True,
        "ui_message_type": "warning",
        "ui_message_title": "Atenção",
        "ui_message_body": "Alguns arquivos foram ignorados.",
    }

    show_upload_result_message(None, result)

    mock_warning.assert_called_once()
    mock_error.assert_not_called()
    mock_info.assert_not_called()


@patch("src.ui.components.upload_feedback.messagebox.showinfo")
@patch("src.ui.components.upload_feedback.messagebox.showerror")
@patch("src.ui.components.upload_feedback.messagebox.showwarning")
def test_show_upload_result_message_respects_flag(mock_warning, mock_error, mock_info) -> None:
    """Quando should_show_ui for falso, nenhuma messagebox deve ser exibida."""
    result = {
        "should_show_ui": False,
        "ui_message_type": "info",
        "ui_message_title": "Envio",
        "ui_message_body": "Mensagem teste",
    }

    show_upload_result_message(None, result)

    mock_warning.assert_not_called()
    mock_error.assert_not_called()
    mock_info.assert_not_called()
