from __future__ import annotations

import tkinter as tk
from typing import Any, Mapping, Sequence, Tuple

from src.ui.feedback import get_ui_feedback

__all__ = ["build_upload_message_info", "show_upload_result_message"]


def _normalize_errors(errors: Any) -> list[str]:
    if not errors:
        return []

    if isinstance(errors, str):
        return [errors]

    if isinstance(errors, Sequence) and not isinstance(errors, (str, bytes)):
        normalized: list[str] = []
        for item in errors:
            if item:
                normalized.append(str(item))
        return normalized

    return [str(errors)]


def _coerce_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def build_upload_message_info(result: Mapping[str, Any] | None) -> Tuple[bool, str, str, str]:
    """Prepara dados para exibição de feedback de upload.

    Returns:
        Tuple (should_show_ui, message_type, title, body).
    """
    if not isinstance(result, Mapping):
        return True, "info", "Upload", "O serviço de upload não retornou informações."

    should_show_ui = bool(result.get("should_show_ui", True))
    message_type = str(result.get("ui_message_type") or ("info" if result.get("ok") else "warning")).lower()
    title = str(result.get("ui_message_title") or ("Upload concluído" if result.get("ok") else "Upload"))

    raw_body = result.get("ui_message_body")
    body = str(raw_body).strip() if isinstance(raw_body, str) else ""

    if not body and raw_body and not isinstance(raw_body, str):
        body = str(raw_body)

    if not body:
        errors = _normalize_errors(result.get("errors"))
        if errors:
            body = "\n".join(errors)

    stats = result.get("stats")
    summary_lines: list[str] = []
    if isinstance(stats, Mapping):
        total_selected = _coerce_int(stats.get("total_selected"))
        total_validated = _coerce_int(stats.get("total_validated"))
        total_invalid = _coerce_int(stats.get("total_invalid"))
        total_skipped = _coerce_int(stats.get("total_skipped_by_limit"))

        if total_selected is not None:
            summary_lines.append(f"Arquivos selecionados: {total_selected}")
        if total_validated is not None:
            summary_lines.append(f"Arquivos enviados: {total_validated}")
        if total_invalid:
            summary_lines.append(f"Arquivos recusados na validação: {total_invalid}")
        if total_skipped:
            summary_lines.append(f"Arquivos ignorados pelo limite de lote: {total_skipped}")

    if summary_lines:
        summary_block = "\n".join(summary_lines)
        body = f"{body}\n\n{summary_block}".strip() if body else summary_block

    if not body:
        body = "Nenhuma mensagem foi retornada pelo serviço de upload."

    return should_show_ui, message_type, title, body


def show_upload_result_message(parent: tk.Misc | None, result: Mapping[str, Any] | None) -> None:
    """Exibe messagebox com base no resultado do upload."""
    should_show_ui, message_type, title, body = build_upload_message_info(result)
    if not should_show_ui:
        return

    feedback = get_ui_feedback(parent)

    if message_type == "error":
        feedback.error(title, body)
    elif message_type == "warning":
        feedback.warning(title, body)
    else:
        feedback.info(title, body)
