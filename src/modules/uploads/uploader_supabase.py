# -*- coding: utf-8 -*-
"""Helpers para o fluxo de upload de documentos ao Supabase."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, List, Optional, Sequence, Tuple, cast

import tkinter as tk
from tkinter import filedialog, messagebox

from src.modules.uploads import service as uploads_service
from src.modules.uploads.components.helpers import _cnpj_only_digits
from src.modules.uploads.exceptions import (
    UploadNetworkError,
    UploadServerError,
    UploadValidationError,
)
from src.modules.uploads.upload_retry import classify_upload_exception
from src.modules.uploads.file_validator import (
    validate_upload_files,
    FileValidationResult,
)
from src.ui.components.progress_dialog import ProgressDialog
from src.ui.window_utils import show_centered

log = logging.getLogger(__name__)


def center_window(window: tk.Misc, *args: object, **kwargs: object) -> None:
    """Wrapper de compatibilidade para centralizar janelas de upload."""

    # Mantido para testes e codigo legado que ainda chamam center_window.
    # Hoje delega para src.ui.window_utils.show_centered.
    show_centered(window)


CLIENTS_BUCKET = (os.getenv("SUPABASE_CLIENTS_BUCKET") or "clientes").strip() or "clientes"
VOLUME_CONFIRM_THRESHOLD = int(os.getenv("RC_UPLOAD_CONFIRM_THRESHOLD") or "200")


UploadItem = uploads_service.UploadItem
collect_pdfs_from_folder = uploads_service.collect_pdfs_from_folder
build_items_from_files = uploads_service.build_items_from_files


class UploadProgressDialog:
    """Wrapper fino que reutiliza ProgressDialog."""

    def __init__(self, parent: tk.Misc, total: int) -> None:
        self._total = max(int(total), 1)
        self._value = 0
        self._dialog = ProgressDialog(
            parent,
            title="Enviando arquivos",
            message="Preparando...",
            detail=self._detail_text(),
        )
        self._dialog.set_progress(0.0)

    def after(self, delay: int, callback: Any) -> Any:
        return self._dialog.after(delay, callback)

    def update_idletasks(self) -> None:
        try:
            self._dialog.update_idletasks()
        except Exception as exc:  # noqa: BLE001
            log.debug("Failed to update_idletasks on ProgressDialog: %s", exc)

    def update(self) -> None:
        try:
            self._dialog.update()
        except Exception as exc:  # noqa: BLE001
            log.debug("Failed to update ProgressDialog: %s", exc)

    def advance(self, label: str) -> None:
        self._value = min(self._total, self._value + 1)
        detail = self._detail_text()
        try:
            self._dialog.set_message(label)
            self._dialog.set_detail(detail)
            self._dialog.set_progress(self._value / self._total)
        except Exception as exc:  # noqa: BLE001
            log.debug("Failed to update progress bar: %s", exc)

    def close(self) -> None:
        try:
            self._dialog.close()
        except Exception as exc:  # noqa: BLE001
            log.debug("Failed to destroy progress window: %s", exc)

    def wait_window(self) -> None:
        """Bloqueia até que o diálogo seja fechado (via close() ou janela destruída)."""
        try:
            self._dialog.wait_window()
        except Exception as exc:  # noqa: BLE001
            log.debug("wait_window encerrado: %s", exc)

    def _detail_text(self) -> str:
        return f"{self._value}/{self._total} arquivo(s)"


def _select_pdfs_dialog(parent: Optional[tk.Misc] = None) -> List[str]:
    """Abre diálogo de seleção múltipla de PDFs e retorna os paths escolhidos."""
    paths = filedialog.askopenfilenames(
        title="Selecione um ou mais PDFs",
        filetypes=[("PDF", "*.pdf")],
        parent=parent,
    )
    return list(paths or [])


def _show_upload_summary(
    ok_count: int,
    failed_items: List[Tuple[Any, Exception]],
    *,
    parent: Optional[tk.Misc] = None,
    validation_errors: List[FileValidationResult] | None = None,
) -> None:
    """Exibe resumo de sucesso/falha dos uploads com mensagens específicas.

    FASE 7: Mensagens de erro melhoradas baseadas no tipo de exceção.
    """
    # Coletar mensagens de erro por categoria
    network_errors: List[str] = []
    server_errors: List[str] = []
    validation_msgs: List[str] = []
    other_errors: List[str] = []

    # Processar falhas de upload
    for item, exc in failed_items:
        filename = Path(getattr(item, "relative_path", str(item))).name
        typed_exc = classify_upload_exception(exc)

        if isinstance(typed_exc, UploadNetworkError):
            network_errors.append(filename)
        elif isinstance(typed_exc, UploadServerError):
            server_errors.append(filename)
        elif isinstance(typed_exc, UploadValidationError):
            validation_msgs.append(f"{filename}: {typed_exc.message}")
        else:
            other_errors.append(f"{filename}: {typed_exc.message}")

    # Processar erros de validação prévia
    if validation_errors:
        for result in validation_errors:
            validation_msgs.append(f"{result.path.name}: {result.error}")

    # Montar mensagem
    total_failed = len(failed_items) + (len(validation_errors) if validation_errors else 0)

    if total_failed == 0:
        messagebox.showinfo(
            "Envio concluído",
            f"Todos os {ok_count} arquivo(s) foram enviados com sucesso.",
            parent=parent,
        )
        return

    # Construir mensagem detalhada
    lines: List[str] = []

    if ok_count > 0:
        lines.append(f"✓ {ok_count} arquivo(s) enviado(s) com sucesso.\n")

    if validation_msgs:
        lines.append("⚠ Arquivos inválidos:")
        for msg in validation_msgs[:5]:  # Limitar a 5 para não poluir
            lines.append(f"  • {msg}")
        if len(validation_msgs) > 5:
            lines.append(f"  ... e mais {len(validation_msgs) - 5} arquivo(s)")
        lines.append("")

    if network_errors:
        lines.append("⚠ Falha de conexão (verifique sua internet):")
        for name in network_errors[:3]:
            lines.append(f"  • {name}")
        if len(network_errors) > 3:
            lines.append(f"  ... e mais {len(network_errors) - 3} arquivo(s)")
        lines.append("")

    if server_errors:
        lines.append("⚠ Erro no servidor (tente novamente mais tarde):")
        for name in server_errors[:3]:
            lines.append(f"  • {name}")
        if len(server_errors) > 3:
            lines.append(f"  ... e mais {len(server_errors) - 3} arquivo(s)")
        lines.append("")

    if other_errors:
        lines.append("⚠ Outros erros:")
        for msg in other_errors[:3]:
            lines.append(f"  • {msg}")
        if len(other_errors) > 3:
            lines.append(f"  ... e mais {len(other_errors) - 3} arquivo(s)")

    message = "\n".join(lines).strip()

    if ok_count > 0:
        messagebox.showwarning(
            "Envio concluído com falhas",
            message,
            parent=parent,
        )
    else:
        messagebox.showerror(
            "Falha no envio",
            message,
            parent=parent,
        )


def ensure_client_saved_or_abort(app: tk.Misc, client_id: int) -> bool:
    """Verifica se ha formulario de edicao com alteracoes pendentes."""
    handler = getattr(app, "ensure_client_saved_for_upload", None)
    if callable(handler):
        return bool(handler(client_id))
    return True


def ask_storage_subfolder(parent: tk.Misc) -> Optional[str]:
    """Abre dialogo para escolher subpasta de storage (pode retornar None se cancelado)."""
    from src.modules.clientes.forms.client_subfolder_prompt import SubpastaDialog

    dialog = SubpastaDialog(parent, default="")
    parent.wait_window(dialog)
    return dialog.result


def _confirm_large_volume(parent: tk.Misc, total: int) -> bool:
    """Pergunta ao usuario se deve continuar quando o volume de arquivos excede o threshold."""
    if total <= VOLUME_CONFIRM_THRESHOLD:
        return True
    return messagebox.askyesno(
        "Confirmar envio",
        (f"Voce selecionou {total} arquivos.\n\nEsse volume pode levar algum tempo. Deseja continuar?"),
        parent=parent,
    )


def _upload_batch(
    app: tk.Misc,
    items: Sequence[UploadItem],
    cnpj_digits: str,
    subfolder: Optional[str],
    parent: tk.Misc,
    *,
    bucket: Optional[str] = None,
    client_id: Optional[int] = None,
    org_id: Optional[str] = None,
) -> Tuple[int, List[Tuple[UploadItem, Exception]]]:
    """
    Upload batch with threading support.

    PERF-002: Movido I/O de rede para thread background para evitar
    travamento da GUI durante uploads. A janela de progresso é atualizada
    via widget.after() chamado da thread de I/O.
    """
    import threading
    import queue

    progress = UploadProgressDialog(parent, len(items))
    result_queue: queue.Queue = queue.Queue()

    def _safe_after(delay: int, callback: Any) -> None:
        """Schedule callback on main thread safely."""
        try:
            progress.after(delay, callback)
        except Exception as e:
            log.debug("Failed to schedule callback: %s", e)

    def _progress(item: UploadItem) -> None:
        label = Path(item.relative_path).name
        # Atualiza progresso via main thread
        _safe_after(0, lambda: progress.advance(f"Enviando {label}"))

    def _upload_worker() -> None:
        """Execute upload em thread background."""
        try:
            ok, failures = uploads_service.upload_items_for_client(
                items,
                cnpj_digits=cnpj_digits,
                bucket=bucket or CLIENTS_BUCKET,
                supabase_client=getattr(app, "supabase", None),
                subfolder=subfolder,
                progress_callback=_progress,
                client_id=client_id,
                org_id=org_id,
            )
            result_queue.put(("success", ok, failures))
        except Exception as exc:
            log.error("Upload batch error: %s", exc, exc_info=True)
            result_queue.put(("error", exc))

    # Estado compartilhado para polling não-bloqueante
    state = {"worker": None, "polling": False}

    def _tick() -> None:
        """Polling não-bloqueante: verifica se thread worker terminou."""
        worker = state["worker"]
        if worker is None:
            return

        if worker.is_alive():
            # Thread ainda rodando: agenda próximo tick
            state["polling"] = True
            _safe_after(50, _tick)
        else:
            # Thread terminou: recupera resultado e fecha progresso
            state["polling"] = False
            try:
                result = result_queue.get_nowait()
                progress.close()

                if result[0] == "success":
                    # Armazena resultado no state para wait_window retornar
                    state["result"] = (result[1], result[2])
                else:
                    # Se houve erro, armazena exceção
                    state["error"] = result[1]
            except queue.Empty:
                progress.close()
                state["error"] = RuntimeError("Upload thread finished without result")

    # Inicia upload em background thread
    worker = threading.Thread(target=_upload_worker, daemon=True)
    state["worker"] = worker
    worker.start()

    # Inicia polling não-bloqueante
    _tick()

    # Aguarda resultado bloqueando apenas esta janela, não a GUI principal
    # wait_window() processa eventos Tk normalmente, sem busy-wait
    progress.wait_window()

    # Recupera resultado do state
    if "error" in state:
        raise state["error"]
    elif "result" in state:
        return state["result"]
    else:
        # Janela foi fechada antes do término (usuário fechou manualmente)
        raise RuntimeError("Upload dialog closed before completion")


def upload_files_to_supabase(
    app: tk.Misc,
    cliente: dict,
    items: Sequence[UploadItem],
    subpasta: Optional[str],
    *,
    parent: Optional[tk.Misc] = None,
    bucket: Optional[str] = None,
    client_id: Optional[int] = None,
    skip_validation: bool = False,
) -> Tuple[int, int]:
    """Executa o upload para <bucket>/<org_id>/<client_id>/GERAL/<arquivo>.

    FASE 7: Inclui validação prévia de arquivos e mensagens de erro específicas.

    Args:
        app: Referência ao app principal.
        cliente: Dict com dados do cliente (deve ter 'cnpj').
        items: Sequência de UploadItem para enviar.
        subpasta: Subpasta no storage (opcional).
        parent: Widget pai para diálogos.
        bucket: Nome do bucket (opcional, usa padrão).
        client_id: ID do cliente (opcional).
        skip_validation: Se True, pula validação de arquivos.

    Returns:
        Tupla (sucesso, falhas).
    """
    if not items:
        return 0, 0

    target = parent or app
    if not _confirm_large_volume(target, len(items)):
        return 0, 0

    cnpj_raw = cliente.get("cnpj")
    cnpj_digits = _cnpj_only_digits(cnpj_raw) if cnpj_raw else ""
    if not cnpj_digits:
        messagebox.showwarning(
            "Envio",
            "Este cliente não possui CNPJ cadastrado. Salve antes de enviar.",
            parent=target,
        )
        return 0, len(items)

    # FASE 7: Validar arquivos antes de iniciar upload
    validation_errors: List[FileValidationResult] = []
    valid_items: List[UploadItem] = list(items)

    if not skip_validation:
        paths = [str(item.path) for item in items]
        valid_results, invalid_results = validate_upload_files(paths)
        validation_errors = invalid_results

        if invalid_results:
            # Filtrar apenas os itens válidos
            valid_paths = {str(r.path) for r in valid_results}
            valid_items = [item for item in items if str(item.path) in valid_paths]

            log.info(
                "Validação: %d válidos, %d inválidos de %d total",
                len(valid_items),
                len(invalid_results),
                len(items),
            )

            # Se todos inválidos, mostrar erro e sair
            if not valid_items:
                _show_upload_summary(
                    ok_count=0,
                    failed_items=[],
                    parent=target,
                    validation_errors=validation_errors,
                )
                return 0, len(items)

    # Obtem org_id do usuario logado
    org_id: Optional[str] = None
    if client_id is not None:
        try:
            from src.modules.uploads.components.helpers import get_current_org_id

            sb = getattr(app, "supabase", None)
            if sb:
                org_id = get_current_org_id(sb)
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao resolver org_id para upload: %s", exc)

    # Executar upload dos itens válidos
    try:
        ok, failures = _upload_batch(
            app,
            valid_items,
            cnpj_digits,
            subpasta,
            target,
            bucket=bucket,
            client_id=client_id,
            org_id=org_id,
        )
    except Exception as exc:
        # Erro geral (ex: sem autenticação)
        log.error("Erro crítico no upload: %s", exc, exc_info=True)
        typed_exc = classify_upload_exception(exc)
        messagebox.showerror(
            "Erro no envio",
            typed_exc.message,
            parent=target,
        )
        return 0, len(items)

    # Mostrar resumo com erros de validação incluídos
    _show_upload_summary(
        ok_count=ok,
        failed_items=failures,
        parent=target,
        validation_errors=validation_errors,
    )

    total_failed = len(failures) + len(validation_errors)
    return ok, total_failed


def _resolve_selected_cliente(app: tk.Misc) -> Optional[Tuple[int, dict[str, str]]]:
    """Obt�m o cliente selecionado na UI, retornando id e mapping de colunas ou None."""
    resolver = getattr(app, "_selected_main_values", None)
    if not callable(resolver):
        return None

    values = resolver()
    if not values:
        return None

    frame_getter = getattr(app, "_main_screen_frame", None)
    frame = frame_getter() if callable(frame_getter) else None
    columns = tuple(getattr(frame, "_col_order", ()))

    # Cast para Sequence para garantir que suporta len() e indexa��o
    values_seq = cast(Sequence, values)
    columns_seq = cast(Sequence, columns)

    mapping: dict[str, str] = {}
    if columns_seq and len(columns_seq) == len(values_seq):
        mapping = {str(columns_seq[idx]): str(values_seq[idx]) for idx in range(len(columns_seq))}
    else:
        mapping = {str(idx): str(values_seq[idx]) for idx in range(len(values_seq))}

    try:
        client_id_raw = mapping.get("ID", str(values_seq[0]))
        client_id = int(str(client_id_raw).strip())
    except Exception:
        return None

    return client_id, mapping


def send_to_supabase_interactive(
    app: tk.Misc,
    *,
    default_bucket: Optional[str] = None,
    base_prefix: Optional[str] = None,  # mantido por compatibilidade
    default_subprefix: Optional[str] = None,
    parent: Optional[tk.Misc] = None,
) -> Tuple[int, int]:
    """Fluxo interativo: seleciona cliente, coleta PDFs e envia ao Supabase."""
    del base_prefix, default_subprefix  # parametros legados nao utilizados

    target = parent or app

    resolved = _resolve_selected_cliente(app)
    if not resolved:
        messagebox.showinfo("Envio", "Selecione um cliente primeiro.", parent=target)
        return 0, 0

    client_id, row = resolved

    if not ensure_client_saved_or_abort(app, client_id):
        return 0, 0

    cnpj_value = row.get("CNPJ", "")

    files = _select_pdfs_dialog(parent=target)
    if not files:
        messagebox.showinfo("Envio", "Nenhum arquivo selecionado.", parent=target)
        return 0, 0

    items = build_items_from_files(files)
    if not items:
        messagebox.showwarning(
            "Envio",
            "Nenhum PDF valido foi selecionado.",
            parent=target,
        )
        return 0, 0

    cliente = {"cnpj": cnpj_value}
    return upload_files_to_supabase(
        app,
        cliente,
        items,
        subpasta=None,
        parent=target,
        bucket=default_bucket,
        client_id=client_id,
    )


def send_folder_to_supabase(
    app: tk.Misc,
    *,
    default_bucket: Optional[str] = None,
    parent: Optional[tk.Misc] = None,
) -> Tuple[int, int]:
    """Fluxo interativo: seleciona cliente e pasta local, envia todos os PDFs."""
    target = parent or app

    resolved = _resolve_selected_cliente(app)
    if not resolved:
        messagebox.showinfo("Envio", "Selecione um cliente primeiro.", parent=target)
        return 0, 0

    client_id, row = resolved

    if not ensure_client_saved_or_abort(app, client_id):
        return 0, 0

    folder = filedialog.askdirectory(title="Selecione a pasta com os PDFs", parent=target)
    if not folder:
        messagebox.showinfo("Envio", "Nenhuma pasta selecionada.", parent=target)
        return 0, 0

    # Captura o nome da pasta selecionada para usar como subfolder no Storage
    from pathlib import Path as _Path

    folder_name = _Path(folder).name

    items = collect_pdfs_from_folder(folder)
    if not items:
        messagebox.showinfo(
            "Envio",
            "Nenhum PDF encontrado nessa pasta.",
            parent=target,
        )
        return 0, 0

    cliente = {"cnpj": row.get("CNPJ", "")}
    return upload_files_to_supabase(
        app,
        cliente,
        items,
        subpasta=folder_name,  # Passa o nome da pasta como subfolder
        parent=target,
        bucket=default_bucket,
        client_id=client_id,
    )


__all__ = [
    "UploadItem",
    "collect_pdfs_from_folder",
    "build_items_from_files",
    "ensure_client_saved_or_abort",
    "ask_storage_subfolder",
    "upload_files_to_supabase",
    "send_to_supabase_interactive",
    "send_folder_to_supabase",
]
