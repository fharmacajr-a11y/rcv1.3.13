# -*- coding: utf-8 -*-
"""
Módulo headless para helpers de upload do formulário de clientes.

Extrai a lógica de execução de upload (seleção, validação, envio) do client_form.py,
permitindo reutilização e testabilidade independente de UI.
"""

from __future__ import annotations

import logging
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any

from src.modules.uploads.components.helpers import _cnpj_only_digits, get_clients_bucket, get_current_org_id
from src.modules.uploads.file_validator import validate_upload_files
from src.modules.uploads.service import build_items_from_files, upload_items_for_client
from src.modules.uploads.upload_retry import classify_upload_exception
from src.modules.uploads.views import UploadDialog, UploadDialogContext, UploadDialogResult

logger = logging.getLogger(__name__)


def _format_validation_errors(results: list[Any] | None) -> list[str]:
    """
    Formata erros de validação de arquivos para exibição ao usuário.

    Args:
        results: Lista de resultados de validação com path e error (ou None)

    Returns:
        Lista de mensagens formatadas
    """
    messages: list[str] = []
    for res in results or []:
        try:
            path = getattr(res, "path", None)
            name = Path(path).name if path else "Arquivo"
            error_text = getattr(res, "error", "") or "arquivo invalido"
            messages.append(f"{name}: {error_text}")
        except Exception:
            continue
    return messages


def execute_upload_flow(
    parent_widget: Any,
    ents: dict[str, Any],
    client_id: int | None,
    host: Any,
) -> None:
    """
    Executa o fluxo completo de upload de documentos para um cliente.

    Este é o fluxo principal:
    1. Solicita seleção de arquivos PDF
    2. Valida arquivos selecionados
    3. Verifica CNPJ do cliente
    4. Executa upload com dialog de progresso
    5. Exibe resultado ao usuário

    Args:
        parent_widget: Widget pai para dialogs
        ents: Dicionário de campos do formulário
        client_id: ID do cliente (deve existir)
        host: Referência ao host (para supabase client)

    Raises:
        Exception: Se houver erro durante upload
    """
    # 1. Selecionar arquivos
    files = filedialog.askopenfilenames(
        parent=parent_widget,
        title="Selecione um ou mais PDFs",
        filetypes=[("PDF", "*.pdf")],
    )
    if not files:
        messagebox.showinfo("Envio", "Nenhum arquivo selecionado.", parent=parent_widget)
        return

    # 2. Validar arquivos
    valid_results, invalid_results = validate_upload_files(list(files))
    if not valid_results:
        body = "\n".join(_format_validation_errors(invalid_results)) or "Nenhum arquivo valido para envio."
        messagebox.showwarning("Envio", body, parent=parent_widget)
        return

    # 3. Construir items de upload
    items = build_items_from_files([str(res.path) for res in valid_results])
    if not items:
        messagebox.showwarning("Envio", "Nenhum PDF valido foi selecionado.", parent=parent_widget)
        return

    # 4. Verificar CNPJ
    cnpj_widget = ents.get("CNPJ")
    cnpj_value = ""
    try:
        cnpj_value = cnpj_widget.get().strip() if cnpj_widget else ""
    except Exception:
        pass

    cnpj_digits = _cnpj_only_digits(cnpj_value)
    if not cnpj_digits:
        messagebox.showwarning("Envio", "Informe o CNPJ antes de enviar.", parent=parent_widget)
        return

    # 5. Resolver org_id
    supabase_client = getattr(host, "supabase", None)
    org_id_val = ""
    try:
        if supabase_client:
            org_id_val = get_current_org_id(supabase_client)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Falha ao resolver org_id para upload: %s", exc)

    items_total = len(items)

    # 6. Definir callable de upload (executado em thread)
    def _upload_callable(ctx: UploadDialogContext) -> dict[str, Any]:
        ctx.set_total(items_total)

        def _progress(item: Any) -> None:
            ctx.raise_if_cancelled()
            label = Path(getattr(item, "relative_path", getattr(item, "path", "arquivo"))).name
            ctx.advance(label=f"Enviando {label}")

        ok_count, failures = upload_items_for_client(
            items,
            cnpj_digits=cnpj_digits,
            bucket=get_clients_bucket(),
            supabase_client=supabase_client,
            subfolder=None,
            progress_callback=_progress,
            client_id=client_id,
            org_id=org_id_val or None,
        )
        return {
            "ok_count": ok_count,
            "failed": failures,
            "validation_errors": invalid_results,
            "total": items_total,
        }

    # 7. Definir callback de conclusão
    def _on_upload_complete(outcome: UploadDialogResult) -> None:
        if outcome.error:
            title = "Envio cancelado" if "cancelado" in outcome.error.message.lower() else "Erro no upload"
            handler = messagebox.showinfo if title.startswith("Envio cancelado") else messagebox.showerror
            handler(title, outcome.error.message, parent=parent_widget)
            return

        payload = outcome.result or {}
        ok_count = int(payload.get("ok_count", 0) or 0)
        failures = list(payload.get("failed") or [])
        validation_errors = list(payload.get("validation_errors") or [])

        failure_msgs: list[str] = []
        for item, exc in failures:
            typed_exc = classify_upload_exception(exc)
            label = Path(getattr(item, "relative_path", getattr(item, "path", "arquivo"))).name
            failure_msgs.append(f"{label}: {typed_exc.message}")

        failure_msgs.extend(_format_validation_errors(validation_errors))

        total_failed = len(failure_msgs)
        total_sent = payload.get("total") or items_total

        if total_failed == 0:
            messagebox.showinfo(
                "Envio concluído",
                f"{ok_count} arquivo(s) enviados com sucesso.",
                parent=parent_widget,
            )
            return

        summary = "\n".join(failure_msgs[:6])
        if len(failure_msgs) > 6:
            summary += f"\n... e mais {len(failure_msgs) - 6} arquivo(s)"

        if ok_count > 0:
            messagebox.showwarning(
                "Envio concluído com avisos",
                f"{ok_count} enviado(s), {total_failed} falha(s) de {total_sent}.\n\n{summary}",
                parent=parent_widget,
            )
        else:
            messagebox.showerror(
                "Falha no envio",
                f"Não foi possível enviar os arquivos selecionados.\n\n{summary}",
                parent=parent_widget,
            )

    # 8. Executar dialog de upload
    dialog = UploadDialog(
        parent_widget,
        _upload_callable,
        title="Enviando arquivos...",
        message="Preparando envio...",
        total_items=items_total,
        on_complete=_on_upload_complete,
    )
    dialog.start()


__all__ = [
    "execute_upload_flow",
]
