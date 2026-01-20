"""Protocolo unificado de feedback para UI.

Provê interface única para:
- Notificações modais (info/warning/error/success)
- Toasts não-bloqueantes (via ttkbootstrap quando disponível)
- Diálogos de ocupado (BusyDialog) e progresso (ProgressDialog)

Uso típico:
    feedback = get_ui_feedback(parent)
    feedback.info("Título", "Mensagem")
    feedback.warning("Atenção", "Algo aconteceu")
    with feedback.busy("Processando...") as h:
        h.set_text("Etapa 2...")
"""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import messagebox
from typing import TYPE_CHECKING, Any, Callable, Literal, Protocol, runtime_checkable

if TYPE_CHECKING:
    from src.ui.components.progress_dialog import BusyDialog as _BusyDialogType
    from src.ui.components.progress_dialog import ProgressDialog as _ProgressDialogType

__all__ = [
    "FeedbackKind",
    "BusyHandle",
    "ProgressHandle",
    "UIFeedback",
    "NullFeedback",
    "TkFeedback",
    "get_ui_feedback",
]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tipos e Protocolos
# ---------------------------------------------------------------------------

FeedbackKind = Literal["info", "warning", "error", "success"]


@runtime_checkable
class BusyHandle(Protocol):
    """Handle para controlar diálogo de ocupado."""

    def set_text(self, text: str) -> None:
        """Atualiza o texto exibido."""
        ...

    def step(self, inc: int = 1) -> None:
        """Avança o progresso (se em modo determinado)."""
        ...

    def close(self) -> None:
        """Fecha o diálogo."""
        ...


@runtime_checkable
class ProgressHandle(Protocol):
    """Handle para controlar diálogo de progresso."""

    def set_message(self, text: str) -> None:
        """Define a mensagem principal."""
        ...

    def set_detail(self, text: str) -> None:
        """Define o texto de detalhe/status."""
        ...

    def set_percent(self, value: float) -> None:
        """Define o percentual (0-100 ou 0.0-1.0)."""
        ...

    def close(self) -> None:
        """Fecha o diálogo."""
        ...


@runtime_checkable
class UIFeedback(Protocol):
    """Protocolo de feedback de UI."""

    def notify(
        self,
        kind: FeedbackKind,
        title: str,
        message: str,
        *,
        toast: bool = False,
        duration_ms: int = 3000,
        bootstyle: str | None = None,
    ) -> None:
        """Exibe notificação (modal ou toast)."""
        ...

    def info(self, title: str, message: str) -> None:
        """Exibe mensagem informativa."""
        ...

    def warning(self, title: str, message: str) -> None:
        """Exibe mensagem de aviso."""
        ...

    def error(self, title: str, message: str) -> None:
        """Exibe mensagem de erro."""
        ...

    def confirm(self, title: str, message: str) -> bool:
        """Exibe diálogo de confirmação. Retorna True se confirmado."""
        ...

    def busy(self, text: str = "Processando...") -> BusyHandle:
        """Abre diálogo de ocupado e retorna handle para controle."""
        ...

    def progress(
        self,
        title: str = "Aguarde...",
        message: str = "",
        detail: str = "",
        can_cancel: bool = False,
        on_cancel: Callable[[], None] | None = None,
    ) -> ProgressHandle:
        """Abre diálogo de progresso e retorna handle para controle."""
        ...


# ---------------------------------------------------------------------------
# Implementação: NullFeedback (no-op, apenas logs)
# ---------------------------------------------------------------------------


class _NullBusyHandle:
    """Handle no-op para busy dialog."""

    def set_text(self, text: str) -> None:
        logger.debug("NullBusyHandle.set_text: %s", text)

    def step(self, inc: int = 1) -> None:
        logger.debug("NullBusyHandle.step: %d", inc)

    def close(self) -> None:
        logger.debug("NullBusyHandle.close")


class _NullProgressHandle:
    """Handle no-op para progress dialog."""

    def set_message(self, text: str) -> None:
        logger.debug("NullProgressHandle.set_message: %s", text)

    def set_detail(self, text: str) -> None:
        logger.debug("NullProgressHandle.set_detail: %s", text)

    def set_percent(self, value: float) -> None:
        logger.debug("NullProgressHandle.set_percent: %.1f", value)

    def close(self) -> None:
        logger.debug("NullProgressHandle.close")


class NullFeedback:
    """Implementação no-op que apenas loga as chamadas."""

    def notify(
        self,
        kind: FeedbackKind,
        title: str,
        message: str,
        *,
        toast: bool = False,
        duration_ms: int = 3000,
        bootstyle: str | None = None,
    ) -> None:
        logger.debug("NullFeedback.notify(%s): %s - %s", kind, title, message)

    def info(self, title: str, message: str) -> None:
        self.notify("info", title, message)

    def warning(self, title: str, message: str) -> None:
        self.notify("warning", title, message)

    def error(self, title: str, message: str) -> None:
        self.notify("error", title, message)

    def confirm(self, title: str, message: str) -> bool:
        logger.debug("NullFeedback.confirm: %s - %s (returning False)", title, message)
        return False

    def busy(self, text: str = "Processando...") -> BusyHandle:
        logger.debug("NullFeedback.busy: %s", text)
        return _NullBusyHandle()

    def progress(
        self,
        title: str = "Aguarde...",
        message: str = "",
        detail: str = "",
        can_cancel: bool = False,
        on_cancel: Callable[[], None] | None = None,
    ) -> ProgressHandle:
        logger.debug("NullFeedback.progress: %s", title)
        return _NullProgressHandle()


# ---------------------------------------------------------------------------
# Implementação: TkFeedback (Tkinter + ttkbootstrap)
# ---------------------------------------------------------------------------


class _TkBusyHandle:
    """Wrapper de BusyDialog como BusyHandle."""

    def __init__(self, dialog: _BusyDialogType) -> None:
        self._dialog = dialog

    def set_text(self, text: str) -> None:
        self._dialog.set_text(text)

    def step(self, inc: int = 1) -> None:
        self._dialog.step(inc)

    def close(self) -> None:
        self._dialog.close()


class _TkProgressHandle:
    """Wrapper de ProgressDialog como ProgressHandle."""

    def __init__(self, dialog: _ProgressDialogType) -> None:
        self._dialog = dialog

    def set_message(self, text: str) -> None:
        self._dialog.set_message(text)

    def set_detail(self, text: str) -> None:
        self._dialog.set_detail(text)

    def set_percent(self, value: float) -> None:
        self._dialog.set_progress(value)

    def close(self) -> None:
        self._dialog.close()


class TkFeedback:
    """Implementação Tkinter do protocolo UIFeedback."""

    def __init__(self, parent: tk.Misc | None = None, *, allow_toast: bool = True) -> None:
        self._parent = parent
        self._allow_toast = allow_toast

    def _resolve_parent(self) -> tk.Misc | None:
        """Resolve o widget parent para uso em diálogos."""
        if isinstance(self._parent, tk.Misc):
            return self._parent
        root = getattr(tk, "_default_root", None)
        if isinstance(root, tk.Misc):
            return root
        return None

    def notify(
        self,
        kind: FeedbackKind,
        title: str,
        message: str,
        *,
        toast: bool = False,
        duration_ms: int = 3000,
        bootstyle: str | None = None,
    ) -> None:
        """Exibe notificação modal ou toast."""
        if toast and self._allow_toast:
            if self._try_show_toast(kind, title, message, duration_ms, bootstyle):
                return
        # Fallback para modal
        self._show_modal(kind, title, message)

    def _try_show_toast(
        self,
        kind: FeedbackKind,
        title: str,
        message: str,
        duration_ms: int,
        bootstyle: str | None,
    ) -> bool:
        """Tenta exibir toast nativo CTk/tk. Retorna True se sucesso."""
        try:
            from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk

            parent = self._resolve_parent()
            if parent is None:
                return False

            # Criar toplevel para o toast
            if HAS_CUSTOMTKINTER and ctk is not None:
                toast = ctk.CTkToplevel(parent)
            else:
                toast = tk.Toplevel(parent)

            toast.withdraw()
            toast.overrideredirect(True)
            toast.attributes("-topmost", True)

            # Container com padding
            if HAS_CUSTOMTKINTER and ctk is not None:
                frame = ctk.CTkFrame(toast)
                frame.pack(fill="both", expand=True, padx=10, pady=10)
                label = ctk.CTkLabel(
                    frame,
                    text=f"{title}\n{message}",
                    justify="left",
                    anchor="w",
                )
            else:
                frame = tk.Frame(toast, bg="#333333", padx=10, pady=10)
                frame.pack(fill="both", expand=True)
                label = tk.Label(
                    frame,
                    text=f"{title}\n{message}",
                    justify="left",
                    anchor="w",
                    bg="#333333",
                    fg="white",
                )
            label.pack()

            # Posicionar no canto inferior direito
            toast.update_idletasks()
            sw = toast.winfo_screenwidth()
            sh = toast.winfo_screenheight()
            w = toast.winfo_width()
            h = toast.winfo_height()
            x = sw - w - 20
            y = sh - h - 60
            toast.geometry(f"{w}x{h}+{x}+{y}")
            toast.deiconify()

            # Auto-fechar após duration
            toast.after(duration_ms, toast.destroy)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao exibir toast: %s", exc)
            return False

    def _show_modal(self, kind: FeedbackKind, title: str, message: str) -> None:
        """Exibe mensagem modal via messagebox."""
        parent = self._resolve_parent()
        if kind == "error":
            messagebox.showerror(title, message, parent=parent)
        elif kind == "warning":
            messagebox.showwarning(title, message, parent=parent)
        else:
            # info ou success
            messagebox.showinfo(title, message, parent=parent)

    @staticmethod
    def _kind_to_bootstyle(kind: FeedbackKind) -> str:
        """Converte FeedbackKind para bootstyle do ttkbootstrap."""
        mapping = {
            "info": "info",
            "warning": "warning",
            "error": "danger",
            "success": "success",
        }
        return mapping.get(kind, "info")

    def info(self, title: str, message: str) -> None:
        self.notify("info", title, message, toast=False)

    def warning(self, title: str, message: str) -> None:
        self.notify("warning", title, message, toast=False)

    def error(self, title: str, message: str) -> None:
        self.notify("error", title, message, toast=False)

    def confirm(self, title: str, message: str) -> bool:
        parent = self._resolve_parent()
        return bool(messagebox.askokcancel(title, message, parent=parent))

    def busy(self, text: str = "Processando...") -> BusyHandle:
        parent = self._resolve_parent()
        if parent is None:
            logger.warning("TkFeedback.busy chamado sem parent válido, retornando NullBusyHandle")
            return _NullBusyHandle()
        try:
            from src.ui.components.progress_dialog import BusyDialog

            dialog = BusyDialog(parent, text=text)
            return _TkBusyHandle(dialog)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Falha ao criar BusyDialog: %s", exc)
            return _NullBusyHandle()

    def progress(
        self,
        title: str = "Aguarde...",
        message: str = "",
        detail: str = "",
        can_cancel: bool = False,
        on_cancel: Callable[[], None] | None = None,
    ) -> ProgressHandle:
        parent = self._resolve_parent()
        if parent is None:
            logger.warning("TkFeedback.progress chamado sem parent válido, retornando NullProgressHandle")
            return _NullProgressHandle()
        try:
            from src.ui.components.progress_dialog import ProgressDialog

            dialog = ProgressDialog(
                parent,
                title=title,
                message=message,
                detail=detail,
                can_cancel=can_cancel,
                on_cancel=on_cancel,
            )
            return _TkProgressHandle(dialog)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Falha ao criar ProgressDialog: %s", exc)
            return _NullProgressHandle()


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def get_ui_feedback(parent: tk.Misc | None = None, *, allow_toast: bool = True) -> UIFeedback:
    """Retorna implementação apropriada de UIFeedback.

    Args:
        parent: Widget Tk parent para diálogos.
        allow_toast: Se True, tenta usar toasts quando disponível.

    Returns:
        TkFeedback se ambiente GUI disponível, NullFeedback caso contrário.
    """
    return TkFeedback(parent, allow_toast=allow_toast)
