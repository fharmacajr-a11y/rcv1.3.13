from __future__ import annotations

import logging
import tkinter as tk
from typing import Optional

from src.ui.ctk_config import ctk
from src.ui.widgets.button_factory import make_btn

log = logging.getLogger(__name__)

CLOUD_COLORS = {
    "ONLINE": "#22c55e",
    "OFFLINE": "#ef4444",
    "UNKNOWN": "#a3a3a3",
}


class StatusFooter(ctk.CTkFrame):
    def __init__(
        self,
        master,
        on_lixeira_click=None,
        show_trash=False,
        user_var: tk.StringVar | None = None,
        cloud_var: tk.StringVar | None = None,
    ):
        super().__init__(master)
        # CTkFrame não suporta padding - usar grid/pack configurações
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=0)

        # Separador horizontal no topo
        self.separator = ctk.CTkFrame(self, height=2, corner_radius=0, fg_color=("#cccccc", "#444444"))
        self.separator.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(0, 2),
        )

        self._lbl_count = ctk.CTkLabel(self, text="")
        self._lbl_count.grid(row=1, column=0, sticky="w", padx=(6, 0), pady=3)

        right = ctk.CTkFrame(self)
        right.grid(row=1, column=1, sticky="e", padx=6, pady=2)

        # Usar StringVars se fornecidas (suporte a updates antes do widget existir)
        self._cloud_var = cloud_var or tk.StringVar(value="Nuvem: Desconhecido")
        self._user_var = user_var or tk.StringVar(value="Usuário: -")

        self._dot = tk.Canvas(right, width=14, height=14, highlightthickness=0, bd=0)
        self._dot_oval_id = self._dot.create_oval(2, 2, 12, 12, fill=CLOUD_COLORS["UNKNOWN"], outline="")

        self._lbl_cloud = ctk.CTkLabel(right, textvariable=self._cloud_var)
        sep = ctk.CTkLabel(right, text="  •  ")
        self._lbl_user = ctk.CTkLabel(right, textvariable=self._user_var)

        self._dot.grid(row=0, column=0, sticky="e")
        self._lbl_cloud.grid(row=0, column=1, sticky="e", padx=(6, 0))
        sep.grid(row=0, column=2, sticky="e")
        self._lbl_user.grid(row=0, column=3, sticky="e", padx=(0, 6))

        # Botão Lixeira opcional (apenas se show_trash=True)
        self._btn_lixeira = None
        if show_trash and on_lixeira_click:
            self._btn_lixeira = make_btn(right, text="Lixeira", command=on_lixeira_click)
            self._btn_lixeira.grid(row=0, column=4, sticky="e")

        self._cloud_state = "UNKNOWN"
        self._user_email = None
        self._count_text = "0 clientes | Hoje: 0 | Mês: 0"

    def set_count(self, total: int | str):
        # Compatibilidade: delega para set_clients_summary com Hoje/Mês = 0
        if isinstance(total, int):
            self.set_clients_summary(total, 0, 0)
        else:
            self._count_text = str(total)
            self._lbl_count.configure(text=self._count_text)

    def set_clients_summary(self, total: int, novos_hoje: int, novos_mes: int) -> None:
        """
        Atualiza o resumo global de clientes na status bar.

        Formato: 'N clientes | Hoje: X | Mês: Y'.
        """
        texto = f"{total} clientes | Hoje: {novos_hoje} | Mês: {novos_mes}"
        self._count_text = texto
        self._lbl_count.configure(text=self._count_text)

    def set_user(self, email: str | None):
        self._user_email = email or "-"
        self._user_var.set(f"Usuário: {self._user_email}")
        log.debug(f"StatusFooter: user atualizado -> {self._user_email}")

    def set_cloud(self, state: Optional[str]) -> None:
        state = (state or "UNKNOWN").upper()
        if state not in CLOUD_COLORS:
            state = "UNKNOWN"

        # Sempre atualizar estado (não return cedo para idempotência)
        self._cloud_state = state
        color = CLOUD_COLORS[state]

        # Atualizar dot com retry se TclError
        if hasattr(self, "_dot") and self._dot and hasattr(self, "_dot_oval_id"):
            try:
                self._dot.itemconfig(self._dot_oval_id, fill=color)
            except tk.TclError:
                # Retry via after(0) se widget ainda não pronto
                try:
                    self.after(0, lambda: self._dot.itemconfig(self._dot_oval_id, fill=color))
                except Exception:
                    pass  # Ignorar se after também falhar

        label = {"ONLINE": "Online", "OFFLINE": "Offline", "UNKNOWN": "Desconhecido"}[state]
        self._cloud_var.set(f"Nuvem: {label}")
        log.debug(f"StatusFooter: cloud atualizado -> {state}")
