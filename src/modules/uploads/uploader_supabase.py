# -*- coding: utf-8 -*-
"""Helpers para o fluxo de upload de documentos ao Supabase."""

from __future__ import annotations

import logging
import os
import queue
import threading
from pathlib import Path
from typing import Any, Callable, List, Optional, Sequence, Tuple, cast

import tkinter as tk
from tkinter import filedialog

from src.ui.dialogs.rc_dialogs import show_info, show_error, show_warning, ask_yes_no

from src.modules.uploads import service as uploads_service
from src.modules.uploads.components.helpers import _cnpj_only_digits
from src.modules.uploads.exceptions import (
    UploadDuplicateError,
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
from src.ui.ctk_config import ctk
from src.ui.files_browser.utils import format_file_size
from src.ui.ui_tokens import APP_BG, BUTTON_RADIUS, PRIMARY_BLUE, PRIMARY_BLUE_HOVER
from src.ui.window_utils import apply_window_icon

log = logging.getLogger(__name__)


def _show_msg(parent: tk.Misc, title: str, msg: str) -> None:
    """Exibe mensagem modal com ícone RC correto (substitui tkinter messagebox).

    Não usa prepare_hidden_window/show_centered_no_flash para evitar conflito
    com a inicialização assíncrona do CTkToplevel no Windows (titlebar color).
    """
    dlg = ctk.CTkToplevel(parent)
    # Auditoria Anti-Flash: withdraw imediato para construir UI sem flash
    dlg.withdraw()
    dlg.title(title)
    dlg.resizable(False, False)
    try:
        dlg.transient(parent)
    except tk.TclError:
        pass
    apply_window_icon(dlg)
    dlg.configure(fg_color=APP_BG)

    frame = ctk.CTkFrame(dlg, fg_color="transparent")
    frame.pack(fill="both", expand=True, padx=24, pady=20)
    ctk.CTkLabel(frame, text=msg, wraplength=360, justify="left", fg_color="transparent").pack(pady=(0, 16))
    ctk.CTkButton(
        frame,
        text="OK",
        width=90,
        command=dlg.destroy,
        corner_radius=BUTTON_RADIUS,
        fg_color=PRIMARY_BLUE,
        hover_color=PRIMARY_BLUE_HOVER,
    ).pack()

    dlg.update_idletasks()
    try:
        w = max(dlg.winfo_reqwidth(), 380)
        h = max(dlg.winfo_reqheight(), 130)
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        x = max(0, px + (pw - w) // 2)
        y = max(0, py + (ph - h) // 2)
        dlg.geometry(f"{w}x{h}+{x}+{y}")
    except tk.TclError:
        pass

    # Auditoria Anti-Flash: deiconify APÓS UI construída e posicionada
    try:
        dlg.deiconify()
    except tk.TclError:
        pass

    try:
        dlg.update()
    except tk.TclError:
        pass

    try:
        if dlg.winfo_exists():
            dlg.grab_set()
            dlg.focus_force()
    except tk.TclError:
        pass

    try:
        parent.wait_window(dlg)
    except tk.TclError:
        pass


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
        try:
            if self._dialog.winfo_exists():
                return self._dialog.after(delay, callback)
        except Exception:
            pass
        return None

    def update_idletasks(self) -> None:
        try:
            self._dialog.update_idletasks()
        except tk.TclError as exc:
            log.debug("Failed to update_idletasks on ProgressDialog: %s", exc)

    def update(self) -> None:
        try:
            self._dialog.update()
        except tk.TclError as exc:
            log.debug("Failed to update ProgressDialog: %s", exc)

    def advance(self, label: str) -> None:
        self._value = min(self._total, self._value + 1)
        detail = self._detail_text()
        try:
            self._dialog.set_message(label)
            self._dialog.set_detail(detail)
            self._dialog.set_progress(self._value / self._total)
        except tk.TclError as exc:
            log.debug("Failed to update progress bar: %s", exc)

    def close(self) -> None:
        try:
            self._dialog.close()
        except tk.TclError as exc:
            log.debug("Failed to destroy progress window: %s", exc)

    def wait_window(self) -> None:
        """Bloqueia até que o diálogo seja fechado (via close() ou janela destruída)."""
        try:
            self._dialog.wait_window()
        except tk.TclError as exc:
            log.debug("wait_window encerrado: %s", exc)

    def _detail_text(self) -> str:
        return f"{self._value}/{self._total} arquivo(s)"


def _select_files_dialog(parent: Optional[tk.Misc] = None) -> List[str]:
    """Abre diálogo de seleção múltipla de documentos e retorna os paths escolhidos."""
    paths = filedialog.askopenfilenames(
        title="Selecione um ou mais documentos",
        filetypes=[
            ("Documentos", "*.pdf *.doc *.docx *.xls *.xlsx *.csv *.jpg *.jpeg *.png"),
            ("Todos os arquivos", "*.*"),
        ],
        parent=parent,
    )
    return list(paths or [])


# Alias mantido por compatibilidade com chamadas legadas.
_select_pdfs_dialog = _select_files_dialog


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
    duplicate_errors: List[str] = []
    network_errors: List[str] = []
    server_errors: List[str] = []
    validation_msgs: List[str] = []
    other_errors: List[str] = []

    # Processar falhas de upload
    for item, exc in failed_items:
        filename = Path(getattr(item, "relative_path", str(item))).name
        typed_exc = classify_upload_exception(exc)

        # IMPORTANTE: checar DuplicateError ANTES de ServerError (herança)
        if isinstance(typed_exc, UploadDuplicateError):
            duplicate_errors.append(filename)
        elif isinstance(typed_exc, UploadNetworkError):
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
        if parent is not None:
            _show_msg(
                parent,
                "Envio concluído",
                f"Todos os {ok_count} arquivo(s) foram enviados com sucesso.",
            )
        else:
            show_info(
                parent,
                "Envio concluído",
                f"Todos os {ok_count} arquivo(s) foram enviados com sucesso.",
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

    if duplicate_errors:
        lines.append("↷ Arquivos já existentes (upload ignorado):")
        for name in duplicate_errors[:5]:
            lines.append(f"  • {name}")
        if len(duplicate_errors) > 5:
            lines.append(f"  ... e mais {len(duplicate_errors) - 5} arquivo(s)")
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
        if parent is not None:
            _show_msg(parent, "Envio concluído com falhas", message)
        else:
            show_warning(
                parent,
                "Envio concluído com falhas",
                message,
            )
    else:
        if parent is not None:
            _show_msg(parent, "Falha no envio", message)
        else:
            show_error(
                parent,
                "Falha no envio",
                message,
            )


def ensure_client_saved_or_abort(app: tk.Misc, client_id: int) -> bool:
    """Verifica se ha formulario de edicao com alteracoes pendentes."""
    handler = getattr(app, "ensure_client_saved_for_upload", None)
    if callable(handler):
        return bool(handler(client_id))
    return True


def ask_storage_subfolder(parent: tk.Misc, *, default: str = "") -> Optional[str]:
    """Abre dialogo para escolher subpasta de storage (pode retornar None se cancelado)."""
    from src.modules.clientes.forms.client_subfolder_prompt import SubpastaDialog

    dialog = SubpastaDialog(parent, default=default)
    parent.wait_window(dialog)
    return dialog.result


def _confirm_large_volume(parent: tk.Misc, total: int) -> bool:
    """Pergunta ao usuario se deve continuar quando o volume de arquivos excede o threshold."""
    if total <= VOLUME_CONFIRM_THRESHOLD:
        return True
    return ask_yes_no(
        parent,
        "Confirmar envio",
        f"Voce selecionou {total} arquivos.\n\nEsse volume pode levar algum tempo. Deseja continuar?",
    )


class _ProgressPump:
    """Polling não-bloqueante da fila de resultado do worker de upload.

    Testável sem Tk real: basta injetar ``after_fn`` e ``close_fn`` como
    callables (não há dependência direta de tkinter nesta classe).

    Protocolo de mensagens da ``result_queue``:
        ("success", ok: int, failures: list)   — worker concluiu com sucesso
        ("error",   exc: Exception)             — worker lançou exceção

    O ``done_event`` é obrigatoriamente setado no ``finally`` do worker,
    garantindo que o diálogo **nunca** feche apenas porque a fila está vazia.

    Fluxo de ``_tick``:
        1. Drena *todas* as mensagens disponíveis na fila (loop while/break).
        2. Se a fila ficou vazia E ``done_event`` ainda NÃO está setado
           → reagenda o próximo tick com ``after_fn``.
        3. Se a fila ficou vazia E ``done_event`` está setado
           → chama ``_finalize()`` (fecha diálogo uma única vez).
    """

    POLL_MS = 50

    def __init__(
        self,
        result_queue: "queue.Queue[tuple]",
        done_event: threading.Event,
        *,
        after_fn: Callable[[int, Callable[[], None]], Any],
        close_fn: Callable[[], None],
        after_cancel_fn: Optional[Callable[[Any], None]] = None,
        poll_ms: int = POLL_MS,
    ) -> None:
        self._queue = result_queue
        self._done_event = done_event
        self._after_fn = after_fn
        self._close_fn = close_fn
        self._after_cancel_fn = after_cancel_fn
        self._poll_ms = poll_ms
        self._finalized = False
        self._after_id: Any = None
        # Resultados preenchidos por _process_msg
        self.result: Optional[Tuple[int, list]] = None
        self.error: Optional[Exception] = None

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Agenda o primeiro tick no loop de eventos do Tk."""
        self._after_id = self._after_fn(self._poll_ms, self._tick)

    def cancel(self) -> None:
        """Cancela ticks futuros de forma idempotente (ex: diálogo fechado manualmente)."""
        self._finalized = True
        aid, self._after_id = self._after_id, None
        if aid is not None and self._after_cancel_fn is not None:
            try:
                self._after_cancel_fn(aid)
            except tk.TclError:
                pass

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _tick(self) -> None:
        """Drena a fila e decide se finaliza ou reagenda."""
        self._after_id = None
        if self._finalized:
            return

        # Passo 1: drenar TODAS as mensagens disponíveis neste ciclo.
        while True:
            try:
                msg = self._queue.get_nowait()
            except queue.Empty:
                break
            self._process_msg(msg)

        # Passo 2: decidir com base em done_event, nunca apenas na fila vazia.
        if self._done_event.is_set():
            self._finalize()
        elif not self._finalized:
            # Worker ainda vivo: reagenda próximo tick.
            self._after_id = self._after_fn(self._poll_ms, self._tick)

    def _process_msg(self, msg: tuple) -> None:
        kind = msg[0]
        if kind == "success":
            self.result = (msg[1], msg[2])
        elif kind == "error":
            self.error = msg[1]
        else:
            log.debug("_ProgressPump: mensagem desconhecida: %s", kind)

    def _finalize(self) -> None:
        """Fecha o diálogo exatamente uma vez, com segurança."""
        if self._finalized:
            return
        self._finalized = True
        try:
            self._close_fn()
        except (tk.TclError, RuntimeError) as exc:
            log.debug("_ProgressPump close_fn error: %s", exc)


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
    """Upload batch com threading + sinalização explícita via done_event.

    PERF-002 / Fase 6:
    - ``done_event`` é setado no ``finally`` do worker (sempre, mesmo em erro).
    - ``_ProgressPump`` drena a fila em loop antes de decidir fechar.
    - Diálogo nunca fecha enquanto ``done_event`` não estiver setado.
    """
    progress = UploadProgressDialog(parent, len(items))
    result_queue: queue.Queue[tuple] = queue.Queue()
    done_event = threading.Event()

    def _safe_after(delay: int, callback: Any) -> None:
        """Agenda callback no main thread de forma segura."""
        try:
            progress.after(delay, callback)
        except tk.TclError as e:
            log.debug("Failed to schedule callback: %s", e)

    def _progress(item: UploadItem) -> None:
        label = Path(item.relative_path).name
        try:
            item_path = Path(item.path)
            if item_path.exists():
                size_str = format_file_size(item_path.stat().st_size)
                _safe_after(0, lambda: progress.advance(f"Enviando {label} ({size_str})"))
            else:
                _safe_after(0, lambda: progress.advance(f"Enviando {label}"))
        except OSError:
            _safe_after(0, lambda: progress.advance(f"Enviando {label}"))

    def _upload_worker() -> None:
        """Executa upload em thread background; sinaliza done_event sempre."""
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
        finally:
            # Sinaliza SEMPRE — garante que o pump nunca fica preso esperando.
            done_event.set()

    pump = _ProgressPump(
        result_queue,
        done_event,
        after_fn=progress.after,
        close_fn=progress.close,
    )

    # Inicia upload em background thread
    worker = threading.Thread(target=_upload_worker, daemon=True)
    worker.start()

    # Inicia polling não-bloqueante (pump agenda o próprio after)
    pump.start()

    # Aguarda resultado bloqueando apenas esta janela, não a GUI principal.
    # wait_window() processa eventos Tk normalmente, sem busy-wait.
    progress.wait_window()

    # Cancela ticks pendentes (idempotente se pump já finalizou normalmente)
    pump.cancel()

    # Recupera resultado
    if pump.error is not None:
        raise pump.error
    if pump.result is not None:
        return pump.result
    # Janela foi fechada pelo usuário antes do término do worker.
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
        show_warning(
            target,
            "Envio",
            "Este cliente não possui CNPJ cadastrado. Salve antes de enviar.",
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
        show_error(
            target,
            "Erro no envio",
            typed_exc.message,
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
    except (ValueError, IndexError):
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
        show_info(target, "Envio", "Selecione um cliente primeiro.")
        return 0, 0

    client_id, row = resolved

    if not ensure_client_saved_or_abort(app, client_id):
        return 0, 0

    cnpj_value = row.get("CNPJ", "")

    files = _select_files_dialog(parent=target)
    if not files:
        show_info(target, "Envio", "Nenhum arquivo selecionado.")
        return 0, 0

    items = build_items_from_files(files)
    if not items:
        show_warning(
            target,
            "Envio",
            "Nenhum arquivo válido foi selecionado.",
        )
        return 0, 0

    # Pedir subpasta em GERAL
    sub = ask_storage_subfolder(target, default="")
    if sub is None:
        show_info(target, "Envio", "Envio cancelado.")
        return 0, 0
    sub = sub.strip()
    subpasta = sub or None

    cliente = {"cnpj": cnpj_value}
    return upload_files_to_supabase(
        app,
        cliente,
        items,
        subpasta=subpasta,
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
        _show_msg(target, "Envio", "Selecione um cliente primeiro.")
        return 0, 0

    client_id, row = resolved

    if not ensure_client_saved_or_abort(app, client_id):
        return 0, 0

    folder = filedialog.askdirectory(title="Selecione a pasta com os documentos", parent=target)
    if not folder:
        _show_msg(target, "Envio", "Nenhuma pasta selecionada.")
        return 0, 0

    base = Path(folder)
    if not base.is_dir():
        log.warning(
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
        log.warning("Nenhum arquivo coletado da pasta: %s (is_dir=%s)", folder, base.is_dir())
        _show_msg(
            target,
            "Nenhum arquivo encontrado",
            "Nenhum arquivo suportado foi encontrado na pasta selecionada.\n\n"
            "Se você navegou por 'Resultados da pesquisa' do Windows,\n"
            "isso pode causar esse problema.\n\n"
            "Clique OK para selecionar os arquivos individualmente.",
        )
        paths = filedialog.askopenfilenames(
            title="Selecione os documentos",
            parent=target,
            filetypes=[
                ("Documentos", "*.pdf *.doc *.docx *.xls *.xlsx *.csv *.jpg *.jpeg *.png"),
                ("Todos os arquivos", "*.*"),
            ],
        )
        if not paths:
            return 0, 0
        items = build_items_from_files(list(paths))
        if not items:
            return 0, 0

    # Pedir subpasta em GERAL (com nome da pasta como default)
    default_name = base.name
    sub = ask_storage_subfolder(target, default=default_name)
    if sub is None:
        _show_msg(target, "Envio", "Envio cancelado.")
        return 0, 0
    sub = sub.strip()
    subpasta = sub or None

    cliente = {"cnpj": row.get("CNPJ", "")}
    return upload_files_to_supabase(
        app,
        cliente,
        items,
        subpasta=subpasta,
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
