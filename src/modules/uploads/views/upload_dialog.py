"""Upload dialog unificado para fluxos de envio de arquivos.

Este componente oferece:
- execuÇõÇœo de upload em executor (injeÇõÇœo para testes);
- barra de progresso baseada em ProgressDialog;
- suporte a cancelamento (Evento + exceÇõÇœo UploadError);
- callbacks de conclusÇœo para UI/UX customizada.
"""

from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable

import tkinter as tk
from tkinter import messagebox

from src.modules.uploads.exceptions import UploadError
from src.modules.uploads.upload_retry import classify_upload_exception
from src.ui.components.progress_dialog import ProgressDialog

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class UploadDialogResult:
    """Resultado bruto da execuÇõÇœo do UploadDialog."""

    result: Any = None
    error: UploadError | None = None


class UploadDialogContext:
    """Contexto passado para o callable de upload para reportar progresso e cancelamento."""

    def __init__(self, dialog: "UploadDialog", total: int | None) -> None:
        self._dialog = dialog
        self._cancel_event = threading.Event()
        self._total = max(int(total or 0), 0)
        self._completed = 0
        self._started_at = time.monotonic()

    # ---- Cancelamento --------------------------------------------------
    @property
    def cancel_event(self) -> threading.Event:
        return self._cancel_event

    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def raise_if_cancelled(self) -> None:
        if self._cancel_event.is_set():
            raise UploadError("Upload cancelado pelo usuário.")

    # ---- Progresso -----------------------------------------------------
    def set_total(self, total: int) -> None:
        self._total = max(int(total or 0), 0)
        if self._total == 0:
            self._completed = 0
        else:
            self._completed = min(self._completed, self._total)
        self._dialog._update_progress(detail=self._detail_text(), fraction=self._fraction())  # noqa: SLF001

    def advance(self, label: str | None = None) -> None:
        """Incrementa progresso em 1 passo."""
        if self._total:
            self._completed = min(self._total, self._completed + 1)
        self._dialog._update_progress(  # noqa: SLF001
            label=label,
            detail=self._detail_text(),
            fraction=self._fraction(),
            eta_text=self._eta_text(),
        )

    def report(
        self,
        *,
        label: str | None = None,
        detail: str | None = None,
        completed: int | None = None,
        total: int | None = None,
        fraction: float | None = None,
    ) -> None:
        """Atualiza estado de progresso com flexibilidade."""
        if total is not None:
            self._total = max(int(total or 0), 0)
        if completed is not None:
            self._completed = max(0, int(completed))
        self._dialog._update_progress(  # noqa: SLF001
            label=label,
            detail=detail or self._detail_text(),
            fraction=fraction if fraction is not None else self._fraction(),
        )

    # ---- Helpers internos ----------------------------------------------
    def _detail_text(self) -> str:
        if self._total > 0:
            pct = round((self._completed / self._total) * 100)
            return f"{self._completed}/{self._total} arquivo(s) ({pct}%)"
        return "Preparando upload..."

    def _fraction(self) -> float | None:
        if self._total > 0:
            return max(0.0, min(1.0, self._completed / self._total))
        return None

    def _eta_text(self) -> str:
        """Calcula tempo decorrido e ETA."""
        elapsed = time.monotonic() - self._started_at
        elapsed_str = self._format_time(elapsed)

        if self._total > 0 and self._completed > 0:
            eta_seconds = (elapsed / self._completed) * (self._total - self._completed)
            eta_str = self._format_time(eta_seconds)
            return f"Tempo: {elapsed_str} | ETA: {eta_str}"
        return f"Tempo: {elapsed_str}"

    @staticmethod
    def _format_time(seconds: float) -> str:
        """Formata segundos em HH:MM:SS ou MM:SS."""
        secs = int(max(0, seconds))
        hours, remainder = divmod(secs, 3600)
        minutes, secs = divmod(remainder, 60)
        if hours:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    def cancel(self) -> None:
        self._cancel_event.set()


class UploadDialog:
    """Janela fina de progresso para uploads baseada em ProgressDialog."""

    def __init__(
        self,
        parent: tk.Misc,
        upload_callable: Callable[[UploadDialogContext], Any],
        *,
        title: str = "Enviando arquivos...",
        message: str = "Preparando upload...",
        total_items: int | None = None,
        executor: Any | None = None,
        on_complete: Callable[[UploadDialogResult], None] | None = None,
    ) -> None:
        self._parent = parent
        self._upload_callable = upload_callable
        self._executor = executor or ThreadPoolExecutor(max_workers=1)
        self._on_complete = on_complete
        self._context = UploadDialogContext(self, total_items)
        self._dialog = ProgressDialog(
            parent,
            title=title,
            message=message,
            detail=self._context._detail_text(),  # noqa: SLF001
            can_cancel=True,
            on_cancel=self.cancel,
        )
        self._dialog.set_progress(self._context._fraction())

    # ---- API principal --------------------------------------------------
    def start(self) -> Future:
        future = self._executor.submit(self._run_upload)
        future.add_done_callback(lambda fut: self._post(lambda: self._finalize(fut)))
        return future

    def cancel(self) -> None:
        self._context.cancel()
        self._update_progress(label="Cancelando...", fraction=None)

    # ---- ExecuÇõÇœo interna ---------------------------------------------
    def _run_upload(self) -> UploadDialogResult:
        try:
            result = self._upload_callable(self._context)
            return UploadDialogResult(result=result, error=None)
        except UploadError as exc:
            return UploadDialogResult(result=None, error=exc)
        except Exception as exc:  # noqa: BLE001
            logger.debug("UploadDialog capturou exceÇõÇœo genÇ¸rica: %s", exc)
            return UploadDialogResult(result=None, error=classify_upload_exception(exc))

    def _finalize(self, future: Future) -> None:
        try:
            outcome: UploadDialogResult = future.result()
        except Exception as exc:  # noqa: BLE001
            outcome = UploadDialogResult(result=None, error=classify_upload_exception(exc))
        try:
            self._dialog.close()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao fechar ProgressDialog: %s", exc)

        if self._on_complete:
            try:
                self._on_complete(outcome)
                return
            except Exception as exc:  # noqa: BLE001
                logger.exception("Callback on_complete falhou: %s", exc)

        # Fallback de UX se nenhum callback for fornecido
        if outcome.error:
            parent = self._parent if isinstance(self._parent, tk.Misc) else None
            messagebox.showerror("Erro no upload", outcome.error.message, parent=parent)

    # ---- AtualizaÇõÇœes de UI -------------------------------------------
    def _update_progress(
        self,
        *,
        label: str | None = None,
        detail: str | None = None,
        fraction: float | None = None,
        eta_text: str | None = None,
    ) -> None:
        def _apply() -> None:
            try:
                if label is not None:
                    self._dialog.set_message(label)
                if detail is not None:
                    self._dialog.set_detail(detail)
                self._dialog.set_progress(fraction)
                if eta_text is not None:
                    self._dialog.set_eta_text(eta_text)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Falha ao atualizar ProgressDialog: %s", exc)

        self._post(_apply)

    def _post(self, callback: Callable[[], None]) -> None:
        try:
            if hasattr(self._parent, "after"):
                self._parent.after(0, callback)
                return
        except Exception as exc:  # noqa: BLE001
            logger.debug("after() falhou, executando callback diretamente: %s", exc)
        try:
            callback()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Callback de UI falhou: %s", exc)


__all__ = [
    "UploadDialog",
    "UploadDialogContext",
    "UploadDialogResult",
]
