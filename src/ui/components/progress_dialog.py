"""Componentes de diálogo de progresso reutilizáveis."""

from __future__ import annotations

import logging
import tkinter as tk
from typing import Callable

from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk
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

        if HAS_CUSTOMTKINTER and ctk is not None:
            body = ctk.CTkFrame(self)
        else:
            body = tk.Frame(self, padx=12, pady=12)
        body.pack(fill="both", expand=True)

        if HAS_CUSTOMTKINTER and ctk is not None:
            self._lbl = ctk.CTkLabel(body, text=text, anchor="center", justify="center")
        else:
            self._lbl = tk.Label(body, text=text, anchor="center", justify="center")
        self._lbl.pack(pady=(0, 8), fill="x")

        if HAS_CUSTOMTKINTER and ctk is not None:
            self._pb = ctk.CTkProgressBar(body, width=280, mode="indeterminate")
            self._pb.set(0)
            self._pb.start()  # CTk requer start() para indeterminate
        else:
            # Fallback tk puro (sem CTk)
            self._pb = tk.Canvas(body, width=280, height=22, bg="#e0e0e0", highlightthickness=0)
            self._pb.pack(fill="x")
            self._pb_anim = 0  # type: ignore[attr-defined]

        try:
            self.update_idletasks()
            show_centered(self)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao centralizar BusyDialog: %s", exc)

        # Aplicar titlebar dark/light conforme tema
        try:
            if HAS_CUSTOMTKINTER:
                # CustomTkinter já gerencia tema automaticamente
                pass
            else:
                # Sem CTk, tema light padrão
                set_immersive_dark_mode(self, enabled=False)
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
            if hasattr(self._pb, 'stop'):
                self._pb.stop()
            if HAS_CUSTOMTKINTER and ctk is not None and hasattr(self._pb, 'set'):
                self._pb.configure(mode="determinate")
                self._pb.set(0)
            else:
                self._pb.configure(mode="determinate", maximum=self._det_total, value=0)
            self.update_idletasks()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao configurar progresso determinado: %s", exc)

    def step(self, inc: int = 1) -> None:
        try:
            if self._det_total:
                self._det_value = min(self._det_total, self._det_value + inc)
                if HAS_CUSTOMTKINTER and ctk is not None and hasattr(self._pb, 'set'):
                    # CTkProgressBar usa valores 0.0 a 1.0
                    progress_fraction = self._det_value / self._det_total
                    self._pb.set(progress_fraction)
                else:
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


class ProgressDialog(tk.Toplevel):
    """Diálogo canônico de progresso com mensagens, ETA e botão Cancelar opcional."""

    DIALOG_MIN_WIDTH = 460
    WRAP_LEN = 420

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
        self._cancel_button: tk.Button | None = None  # Pode ser tk.Button ou ctk.CTkButton

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

        # Grid layout limpo e compacto
        self.rowconfigure(0, weight=0)
        self.columnconfigure(0, weight=1)

        if HAS_CUSTOMTKINTER and ctk is not None:
            body = ctk.CTkFrame(self)
        else:
            body = tk.Frame(self, padx=16, pady=12)
        body.grid(row=0, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=0)

        self._message_var = tk.StringVar(value=message)
        self._detail_var = tk.StringVar(value=detail)
        self._eta_var = tk.StringVar(value="")

        # Linha 1: Mensagem principal em negrito
        if HAS_CUSTOMTKINTER and ctk is not None:
            msg_label = ctk.CTkLabel(
                body,
                textvariable=self._message_var,
                anchor="w",
                justify="left",
                wraplength=self.WRAP_LEN,
            )
        else:
            msg_label = tk.Label(
                body,
                textvariable=self._message_var,
                anchor="w",
                justify="left",
                wraplength=self.WRAP_LEN,
                font=("Segoe UI", 10),
            )
        msg_label.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))

        # Linha 2: Status (esquerda: x/y %) (direita: Tempo/ETA)
        if HAS_CUSTOMTKINTER and ctk is not None:
            detail_label = ctk.CTkLabel(
                body,
                textvariable=self._detail_var,
                anchor="w",
                justify="left",
                wraplength=280,
            )
        else:
            detail_label = tk.Label(
                body,
                textvariable=self._detail_var,
                anchor="w",
                justify="left",
                wraplength=280,
                foreground="#6c757d",
            )
        detail_label.grid(row=1, column=0, sticky="w", pady=(0, 4))

        if HAS_CUSTOMTKINTER and ctk is not None:
            eta_label = ctk.CTkLabel(
                body,
                textvariable=self._eta_var,
                anchor="e",
                justify="right",
                wraplength=140,
            )
        else:
            eta_label = tk.Label(
                body,
                textvariable=self._eta_var,
                anchor="e",
                justify="right",
                wraplength=140,
                foreground="#6c757d",
            )
        eta_label.grid(row=1, column=1, sticky="e", pady=(0, 4))

        # Linha 3: Barra de progresso azul clara
        if HAS_CUSTOMTKINTER and ctk is not None:
            self._progress = ctk.CTkProgressBar(body, width=420, mode="determinate")
            self._progress.set(0)
        else:
            # Fallback tk puro (Canvas simples para visualizar progresso)
            self._progress = tk.Canvas(body, width=420, height=20, bg="#e0e0e0", highlightthickness=0)
            self._progress._progress_value = 0.0  # type: ignore[attr-defined]
        self._progress.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        # Botão Cancelar: canto direito, vermelho
        if can_cancel:
            if HAS_CUSTOMTKINTER and ctk is not None:
                self._cancel_button = ctk.CTkButton(body, text="Cancelar", command=self._handle_cancel, fg_color="#dc3545", hover_color="#c82333")
            else:
                self._cancel_button = tk.Button(body, text="Cancelar", command=self._handle_cancel, bg="#dc3545", fg="white")
            self._cancel_button.grid(row=3, column=1, sticky="e", pady=(8, 0))

        # Forçar altura exata para evitar espaço branco extra
        try:
            self.update_idletasks()
            req_w = max(self.DIALOG_MIN_WIDTH, self.winfo_reqwidth())
            req_h = self.winfo_reqheight()
            self.geometry(f"{req_w}x{req_h}")
            self.minsize(req_w, req_h)
            show_centered(self)

            # Reaplicar tamanho mantendo posição para evitar expansão
            self.update_idletasks()
            x, y = self.winfo_x(), self.winfo_y()
            w = self.winfo_width()
            h = self.winfo_reqheight()
            self.geometry(f"{w}x{h}+{x}+{y}")
            self.minsize(w, h)

            self.grab_set()
            self.focus_force()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao exibir ProgressDialog: %s", exc)

        # Aplicar titlebar dark/light conforme tema
        try:
            if HAS_CUSTOMTKINTER:
                # CustomTkinter já gerencia tema automaticamente
                pass
            else:
                # Sem CTk, tema light padrão
                set_immersive_dark_mode(self, enabled=False)
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
            if HAS_CUSTOMTKINTER and ctk is not None and hasattr(self._progress, 'set'):
                # CTkProgressBar
                if fraction is None:
                    if not self._indeterminate:
                        self._indeterminate = True
                        self._progress.configure(mode="indeterminate")
                        self._progress.start()
                else:
                    if self._indeterminate:
                        self._indeterminate = False
                        self._progress.stop()
                        self._progress.configure(mode="determinate")
                    percent = self._clamp_percent(fraction)
                    self._progress.set(percent / 100.0)  # CTk usa 0.0-1.0
            else:
                # Fallback Canvas (desenhar retângulo de progresso)
                if fraction is not None:
                    self._indeterminate = False
                    percent = self._clamp_percent(fraction)
                    self._progress._progress_value = percent / 100.0  # type: ignore[attr-defined]
                    # Desenhar retângulo proporcional
                    w = 420
                    h = 20
                    fill_w = int(w * self._progress._progress_value)  # type: ignore[attr-defined]
                    self._progress.delete("all")
                    self._progress.create_rectangle(0, 0, fill_w, h, fill="#007bff", outline="")
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
            if self._indeterminate and HAS_CUSTOMTKINTER and ctk is not None:
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
