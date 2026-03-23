# -*- coding: utf-8 -*-
"""
Módulo headless para helpers de upload do formulário de clientes.

Extrai a lógica de execução de upload (seleção, validação, envio) do client_form.py,
permitindo reutilização e testabilidade independente de UI.
"""

from __future__ import annotations

import logging
from pathlib import Path
from tkinter import filedialog
from typing import Any

from src.modules.clientes.forms.client_subfolder_prompt import SubpastaDialog
from src.modules.uploads.components.helpers import _cnpj_only_digits, get_clients_bucket, get_current_org_id
from src.modules.uploads.file_validator import validate_upload_files
from src.modules.uploads import repository as _uploads_repo
from src.modules.uploads.service import build_items_from_files, collect_pdfs_from_folder, upload_items_for_client
from src.modules.uploads.upload_retry import classify_upload_exception
from src.modules.uploads.views import UploadDialog, UploadDialogContext, UploadDialogResult
from src.ui.dialogs.rc_dialogs import show_info
from src.ui.files_browser.utils import format_file_size

logger = logging.getLogger(__name__)


def _show_msg(parent: Any, title: str, msg: str) -> None:
    """Exibe mensagem modal com ícone RC (via rc_dialogs padronizado)."""
    show_info(parent, title, msg)


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
            logger.debug("Erro ao formatar mensagem de validação de arquivo", exc_info=True)
            continue
    return messages


def execute_upload_flow(
    parent_widget: Any,
    ents: dict[str, Any],
    client_id: int | None,
    host: Any,
    on_mutation: Callable[[], None] | None = None,
) -> None:
    """
    Executa o fluxo completo de upload de documentos para um cliente.

    Este é o fluxo principal:
    1. Solicita seleção de PASTA (não arquivos individuais)
    2. Coleta todos os PDFs da pasta selecionada
    3. Solicita subpasta em GERAL (ex.: SIFAP)
    4. Valida arquivos selecionados
    5. Verifica CNPJ do cliente
    6. Executa upload com dialog de progresso
    7. Exibe resultado ao usuário

    Args:
        parent_widget: Widget pai para dialogs
        ents: Dicionário de campos do formulário
        client_id: ID do cliente (deve existir)
        host: Referência ao host (para supabase client)

    Raises:
        Exception: Se houver erro durante upload
    """
    logger.info("[EnviarDocs] execute_upload_flow iniciado para cliente_id=%s", client_id)

    # 1. Selecionar pasta
    folder = filedialog.askdirectory(title="Selecione a pasta com os documentos", parent=parent_widget)
    if not folder:
        _show_msg(parent_widget, "Envio", "Nenhuma pasta selecionada.")
        return

    # 2. Coletar PDFs da pasta
    base = Path(folder)
    if not base.is_dir():
        # Caminho virtual (ex.: "Resultados da pesquisa" do Windows) — não é um diretório real
        logger.warning(
            "Pasta selecionada não é um diretório válido: %s | exists=%s is_dir=%s",
            folder,
            base.exists(),
            base.is_dir(),
        )
        items = []
    else:
        items = collect_pdfs_from_folder(folder)

    if not items:
        # Pasta vazia, virtual ou resultados de pesquisa do Windows que
        # passam no is_dir() mas o glob não consegue listar os arquivos.
        logger.warning("Nenhum arquivo coletado da pasta: %s (is_dir=%s)", folder, base.is_dir())
        _show_msg(
            parent_widget,
            "Nenhum arquivo suportado encontrado",
            "Nenhum arquivo suportado foi encontrado na pasta selecionada.\n\n"
            "Se você navegou por 'Resultados da pesquisa' do Windows,\n"
            "isso pode causar esse problema.\n\n"
            "Clique OK para selecionar os arquivos individualmente.",
        )
        paths = filedialog.askopenfilenames(
            title="Selecione os documentos",
            parent=parent_widget,
            filetypes=[
                ("Documentos", "*.pdf *.doc *.docx *.xls *.xlsx *.csv *.jpg *.jpeg *.png"),
                ("Todos os arquivos", "*.*"),
            ],
        )
        if not paths:
            return
        items = build_items_from_files(list(paths))
        if not items:
            return

    # 3. Pedir nome da SUBPASTA em GERAL
    dlg = SubpastaDialog(parent_widget, default="")
    parent_widget.wait_window(dlg)
    subfolder = dlg.result  # None se cancelado, "" se vazio
    if subfolder is None:
        _show_msg(parent_widget, "Envio", "Envio cancelado.")
        return
    subfolder_upload = subfolder or None

    # 4. Validar arquivos
    valid_results, invalid_results = validate_upload_files([item.path for item in items])
    if not valid_results:
        body = "\n".join(_format_validation_errors(invalid_results)) or "Nenhum arquivo valido para envio."
        _show_msg(parent_widget, "Envio", body)
        return

    # Filtrar items para manter somente os válidos (preservando relative_path)
    valid_set = {str(res.path) for res in valid_results}
    items = [it for it in items if str(it.path) in valid_set]
    if not items:
        _show_msg(parent_widget, "Envio", "Nenhum arquivo válido foi selecionado.")
        return

    # 5. Verificar client_id
    if client_id is None:
        _show_msg(parent_widget, "Envio", "Salve o cadastro do cliente antes de enviar documentos.")
        return

    # 6. Verificar CNPJ
    cnpj_widget = ents.get("CNPJ")
    cnpj_value = ""
    try:
        cnpj_value = cnpj_widget.get().strip() if cnpj_widget else ""
    except Exception:
        logger.debug("Erro ao obter valor do CNPJ do widget", exc_info=True)
        pass

    cnpj_digits = _cnpj_only_digits(cnpj_value)
    if not cnpj_digits:
        _show_msg(parent_widget, "Envio", "Informe o CNPJ antes de enviar.")
        return

    # 7. Resolver supabase_client e org_id
    # Sempre garante um client válido (fallback para singleton global)
    from src.infra.supabase_client import supabase as _global_supabase

    supabase_client = getattr(host, "supabase", None) or _global_supabase

    org_id_val = ""
    try:
        org_id_val = get_current_org_id(supabase_client)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Falha ao resolver org_id via get_current_org_id: %s", exc)

    if not org_id_val:
        # Fallback via memberships do usuário autenticado
        try:
            org_id_val = _uploads_repo.resolve_org_id()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao resolver org_id via resolve_org_id: %s", exc)

    logger.info(
        "UPLOAD prefix: org_id=%s client_id=%s (esperado: %s/%s/GERAL)",
        org_id_val,
        client_id,
        org_id_val,
        client_id,
    )

    items_total = len(items)

    # 8. Definir callable de upload (executado em thread)
    def _upload_callable(ctx: UploadDialogContext) -> dict[str, Any]:
        ctx.set_total(items_total)

        def _progress(item: Any) -> None:
            ctx.raise_if_cancelled()
            label = Path(getattr(item, "relative_path", getattr(item, "path", "arquivo"))).name
            try:
                item_path = Path(getattr(item, "path", ""))
                if item_path.exists():
                    size_str = format_file_size(item_path.stat().st_size)
                    ctx.advance(label=f"Enviando {label} ({size_str})")
                else:
                    ctx.advance(label=f"Enviando {label}")
            except Exception:  # noqa: BLE001
                ctx.advance(label=f"Enviando {label}")

        ok_count, failures = upload_items_for_client(
            items,
            cnpj_digits=cnpj_digits,
            bucket=get_clients_bucket(),
            supabase_client=supabase_client,
            subfolder=subfolder_upload,
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

    # 9. Definir callback de conclusão
    def _on_upload_complete(outcome: UploadDialogResult) -> None:
        if outcome.error:
            title = "Envio cancelado" if "cancelado" in outcome.error.message.lower() else "Erro no upload"
            _show_msg(parent_widget, title, outcome.error.message)
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
            logger.info("[EnviarDocs] upload bem-sucedido: ok_count=%s para cliente_id=%s", ok_count, client_id)
            _show_msg(
                parent_widget,
                "Envio concluído",
                f"{ok_count} arquivo(s) enviados com sucesso.",
            )
            if ok_count > 0 and on_mutation is not None:
                try:
                    on_mutation()
                except Exception:  # noqa: BLE001
                    logger.debug("[EnviarDocs] on_mutation callback falhou", exc_info=True)
            return

        summary = "\n".join(failure_msgs[:6])
        if len(failure_msgs) > 6:
            summary += f"\n... e mais {len(failure_msgs) - 6} arquivo(s)"

        if ok_count > 0:
            logger.info(
                "[EnviarDocs] upload parcial: ok_count=%s failed=%s para cliente_id=%s",
                ok_count,
                total_failed,
                client_id,
            )
            _show_msg(
                parent_widget,
                "Envio concluído com avisos",
                f"{ok_count} enviado(s), {total_failed} falha(s) de {total_sent}.\n\n{summary}",
            )
            if on_mutation is not None:
                try:
                    on_mutation()
                except Exception:  # noqa: BLE001
                    logger.debug("[EnviarDocs] on_mutation callback falhou", exc_info=True)
        else:
            _show_msg(
                parent_widget,
                "Falha no envio",
                f"Não foi possível enviar os arquivos selecionados.\n\n{summary}",
            )

    # 10. Executar dialog de upload
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
