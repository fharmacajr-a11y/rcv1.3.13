# ui/widgets/busy.py
"""BusyOverlay - Overlay de carregamento (MICROFASE 28: 100% CustomTkinter)."""

from __future__ import annotations

import logging
import tkinter as tk

# CustomTkinter: fonte única centralizada (SSoT)
from src.ui.ctk_config import ctk

_log = logging.getLogger(__name__)


class BusyOverlay:
    """
    Overlay de carregamento com barra de progresso indeterminada.
    Útil para operações de rede ou processamento que bloqueiam a UI.

    Uso:
        overlay = BusyOverlay(parent_window, "Carregando...")
        overlay.show()
        # ... realizar operação ...
        overlay.hide()
    """

    def __init__(self, parent: tk.Tk | tk.Toplevel, text: str = "Carregando..."):
        """
        Cria um overlay de carregamento.

        Args:
            parent: Janela pai (Tk ou Toplevel)
            text: Texto a exibir acima da barra de progresso
        """
        self.parent = parent
        self.top = tk.Toplevel(parent)
        self.top.withdraw()
        self.top.overrideredirect(True)
        self.top.transient(parent)

        # Aguarda parent estar visível para obter geometria correta
        parent.update_idletasks()

        # Cobre a janela inteira
        pw = parent.winfo_width() or 400
        ph = parent.winfo_height() or 300
        px = parent.winfo_rootx() or 0
        py = parent.winfo_rooty() or 0

        self.top.geometry(f"{pw}x{ph}+{px}+{py}")
        self.top.configure(bg="#000000")

        try:
            self.top.attributes("-alpha", 0.25)  # leve escurecido
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao configurar alpha em BusyOverlay: %s", exc)

        # Container central (CTk)
        frame = ctk.CTkFrame(self.top, fg_color="transparent")
        frame.place(relx=0.5, rely=0.5, anchor="center")

        self.label = ctk.CTkLabel(frame, text=text, font=("Segoe UI", 11))
        self.label.pack(pady=(0, 10))

        self.pb = ctk.CTkProgressBar(frame, mode="indeterminate", width=220)
        self.pb.pack()

    def show(self):
        """Exibe o overlay e inicia a animação da barra de progresso."""
        self.top.deiconify()
        self.top.lift(self.parent)
        self.top.grab_set()
        try:
            self.pb.start(10)  # indeterminate
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao iniciar progressbar em BusyOverlay: %s", exc)
        self.top.update_idletasks()

    def hide(self):
        """Oculta o overlay e para a animação."""
        try:
            self.pb.stop()
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao parar progressbar em BusyOverlay: %s", exc)
        try:
            self.top.grab_release()
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao liberar grab em BusyOverlay: %s", exc)
        self.top.destroy()

    def update_text(self, text: str):
        """
        Atualiza o texto do overlay enquanto está visível.

        Args:
            text: Novo texto a exibir
        """
        self.label.configure(text=text)
        self.top.update_idletasks()
