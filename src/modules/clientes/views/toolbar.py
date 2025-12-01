from __future__ import annotations

import tkinter as tk
from typing import Callable, Iterable, Optional

try:
    import ttkbootstrap as tb
except Exception:
    from tkinter import ttk as tb  # fallback

from src.ui.components import create_search_controls


class ClientesToolbar(tb.Frame):  # type: ignore[misc]
    """Barra superior da tela de Clientes (busca, ordenação e status)."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        order_choices: Iterable[str],
        default_order: str,
        status_choices: Iterable[str],
        on_search_changed: Callable[[str], None],
        on_clear_search: Callable[[], None],
        on_order_changed: Callable[[str], None],
        on_status_changed: Callable[[Optional[str]], None],
        on_open_trash: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(master)

        controls = create_search_controls(
            self,
            order_choices=list(order_choices),
            default_order=default_order,
            on_search=lambda _event=None: on_search_changed(self.var_busca.get()),
            on_clear=lambda: on_clear_search(),
            on_order_change=lambda: on_order_changed(self.var_ordem.get()),
            on_status_change=lambda _event=None: on_status_changed(self.var_status.get()),
            on_lixeira=on_open_trash,
            status_choices=status_choices,
        )
        controls.frame.pack(fill="x", padx=0, pady=0)

        # Expor variáveis e widgets usados pelo frame principal
        self.var_busca = controls.search_var
        self.var_ordem = controls.order_var
        self.var_status = controls.status_var
        self.entry_busca = controls.entry
        self.order_combobox = controls.order_combobox
        self.status_combobox = controls.status_combobox
        self.lixeira_button = controls.lixeira_button

        # Aliases para compatibilidade com o código existente
        self.frame = controls.frame


__all__ = ["ClientesToolbar"]
