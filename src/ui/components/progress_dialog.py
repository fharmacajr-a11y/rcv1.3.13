"""Componentes de diálogo de progresso reutilizáveis."""

from __future__ import annotations

import logging
import tkinter as tk
from typing import Callable

import ttkbootstrap as tb

from src.ui.theme_toggle import is_dark_theme
from src.ui.win_titlebar import set_immersive_dark_mode
from src.ui.window_utils import show_centered
from src.utils.resource_path import resource_path

logger = logging.getLogger(__name__)


class BusyDialog(tk.Toplevel):
    """Progress dialog clássico com suporte a modo indeterminado/determinado."""

    def __init__(self, parent: tk.Misc, text: str = "Processando..."):
        super().__init__(parent)
        self.withdraw()
        self.title("Aguarde...")
        self.resizable(False, False)
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", lambda: None)  # não fecha
        try:
            self.iconbitmap(resource_path("rc.ico"))
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao aplicar iconbitmap no BusyDialog: %s", exc)

        body = tb.Frame(self, padding=12)
        body.pack(fill="both", expand=True)

        self._lbl = tb.Label(body, text=text, anchor="center", justify="center")
        self._lbl.pack(pady=(0, 8), fill="x")

        self._pb = tb.Progressbar(body, mode="indeterminate", length=280, maximum=100)
        self._pb.pack(fill="x")

        try:
            self.update_idletasks()
            show_centered(self)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao centralizar BusyDialog: %s", exc)

        # Aplicar titlebar dark/light conforme tema
        try:
            theme = tb.Style().theme_use()
            set_immersive_dark_mode(self, enabled=is_dark_theme(theme))
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao aplicar titlebar no BusyDialog: %s", exc)

        self._pb.start(12)
        self.lift()
        try:
            self.attributes("-topmost", True)
            self.after(50, lambda: self.attributes("-topmost", False))
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao ajustar topmost do BusyDialog: %s", exc)
        self.update()

        self._det_total = None
        self._det_value = 0

    def set_text(self, txt: str) -> None:
        try:
            self._lbl.configure(text=txt)
            self.update_idletasks()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao atualizar mensagem do BusyDialog: %s", exc)

    def set_total(self, total: int) -> None:
        """Troca para modo determinado com 'total' passos."""
        try:
            self._det_total = max(int(total), 1)
            self._det_value = 0
            self._pb.stop()
            self._pb.configure(mode="determinate", maximum=self._det_total, value=0)
            self.update_idletasks()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao configurar progresso determinado: %s", exc)

    def step(self, inc: int = 1) -> None:
        try:
            if self._det_total:
                self._det_value = min(self._det_total, self._det_value + inc)
                self._pb.configure(value=self._det_value)
            self.update_idletasks()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao avancar BusyDialog: %s", exc)

    def close(self) -> None:
        try:
            self._pb.stop()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao parar progress bar do BusyDialog: %s", exc)
        try:
            self.destroy()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao destruir BusyDialog: %s", exc)


class ProgressDialog(tb.Toplevel):
    """Diálogo canônico de progresso com mensagens, ETA e botão Cancelar opcional."""

    def __init__(
        self,
        parent: tk.Misc,
        title: str = "Enviando arquivos...",
        *,
        message: str = "",
        detail: str = "",
        can_cancel: bool = False,
        on_cancel: Callable[[], None] | None = None,
    ):
        super().__init__(parent)
        self.withdraw()
        self._cancel_callback = on_cancel
        self._indeterminate = False
        self._can_cancel = bool(can_cancel)
        self._cancel_button: tb.Button | None = None

        try:
            owner = parent.winfo_toplevel()
        except Exception:  # noqa: BLE001
            owner = parent

        try:
            self.iconbitmap(resource_path("rc.ico"))
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao aplicar iconbitmap no ProgressDialog: %s", exc)

        self.title(title)
        self.resizable(False, False)
        self.transient(owner)
        self.protocol("WM_DELETE_WINDOW", self._handle_wm_delete)

        body = tb.Frame(self, padding=16)
        body.pack(fill="both", expand=True)

        wrap_len = 360
        self._message_var = tk.StringVar(value=message)
        self._detail_var = tk.StringVar(value=detail)
        self._eta_var = tk.StringVar(value="")

        tb.Label(body, textvariable=self._message_var, anchor="w", justify="left", wraplength=wrap_len).pack(
            fill="x", pady=(0, 6)
        )
        tb.Label(body, textvariable=self._detail_var, anchor="w", justify="left", wraplength=wrap_len).pack(
            fill="x", pady=(0, 6)
        )

        self._progress = tb.Progressbar(body, mode="determinate", maximum=100, length=wrap_len)
        self._progress.pack(fill="x", pady=(0, 4))

        self._eta_label = tb.Label(body, textvariable=self._eta_var, anchor="w", justify="left", wraplength=wrap_len)
        self._eta_label.pack(fill="x", pady=(0, 10))

        if can_cancel:
            self._cancel_button = tb.Button(body, text="Cancelar", command=self._handle_cancel)
            self._cancel_button.pack(pady=(0, 4))

        try:
            self.update_idletasks()
            show_centered(self)
            self.deiconify()
            self.grab_set()
            self.focus_force()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao exibir ProgressDialog: %s", exc)

        # Aplicar titlebar dark/light conforme tema
        try:
            theme = tb.Style().theme_use()
            set_immersive_dark_mode(self, enabled=is_dark_theme(theme))
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao aplicar titlebar no ProgressDialog: %s", exc)

    def set_message(self, text: str) -> None:
        try:
            self._message_var.set(text)
            self.update_idletasks()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao atualizar mensagem do ProgressDialog: %s", exc)

    def set_detail(self, text: str) -> None:
        try:
            self._detail_var.set(text)
            self.update_idletasks()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao atualizar detalhe do ProgressDialog: %s", exc)

    def set_progress(self, fraction: float | None) -> None:
        """Atualiza a barra de progresso. Use None para modo indeterminado."""
        try:
            if fraction is None:
                if not self._indeterminate:
                    self._indeterminate = True
                    self._progress.configure(mode="indeterminate")
                    self._progress.start(12)
            else:
                if self._indeterminate:
                    self._indeterminate = False
                    self._progress.stop()
                    self._progress.configure(mode="determinate")
                percent = self._clamp_percent(fraction)
                self._progress.configure(value=percent)
            self.update_idletasks()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao atualizar progresso do ProgressDialog: %s", exc)

    def set_eta(self, seconds: float | None) -> None:
        """Atualiza o texto de ETA com base em segundos restantes."""
        if seconds is None or seconds < 0:
            self.set_eta_text("")
            return
        humanized = self._format_eta(seconds)
        self.set_eta_text(f"ETA: {humanized}")

    def set_eta_text(self, text: str | None) -> None:
        try:
            self._eta_var.set(text or "")
            self.update_idletasks()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao atualizar ETA do ProgressDialog: %s", exc)

    def close(self) -> None:
        try:
            if self._indeterminate:
                self._progress.stop()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao parar progresso do ProgressDialog: %s", exc)
        try:
            self.grab_release()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao liberar grab do ProgressDialog: %s", exc)
        try:
            self.destroy()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao destruir ProgressDialog: %s", exc)

    def _handle_wm_delete(self) -> None:
        if self._can_cancel:
            self._handle_cancel()

    def _handle_cancel(self) -> None:
        if self._cancel_button and str(self._cancel_button["state"]) == "disabled":
            return
        if self._cancel_button:
            self._cancel_button.configure(state="disabled", text="Cancelando...")
        if self._cancel_callback:
            try:
                self._cancel_callback()
            except Exception as exc:  # noqa: BLE001
                logger.debug("Falha ao executar callback de cancelamento: %s", exc)

    @staticmethod
    def _clamp_percent(value: float) -> float:
        if value is None:
            return 0.0
        if value > 1:
            return max(0.0, min(100.0, float(value)))
        return max(0.0, min(100.0, float(value) * 100.0))

    @staticmethod
    def _format_eta(seconds: float) -> str:
        secs = int(max(0, seconds))
        hours, remainder = divmod(secs, 3600)
        minutes, secs = divmod(remainder, 60)
        if hours:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"


__all__ = ["BusyDialog", "ProgressDialog"]
