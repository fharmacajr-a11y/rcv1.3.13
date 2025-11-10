# gui/widgets/autocomplete_entry.py
# -*- coding: utf-8 -*-
"""Entry com autocomplete (dropdown com sugestões)."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Dict, List, Literal, Optional


class AutocompleteEntry(ttk.Entry):
    """
    Entry com autocomplete dropdown.

    Uso:
        entry = AutocompleteEntry(parent)
        entry.set_suggester(lambda text: [...])  # retorna List[Dict] com 'label' e 'data'

        def _on_pick(item):
            logging.debug('autocomplete pick: %s', item)
            # Callback de validação de entrada (opcional)

        entry.on_pick = _on_pick
    """

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self._suggester: Optional[Callable[[str], List[Dict[str, Any]]]] = None
        self.on_pick: Optional[Callable[[Dict[str, Any]], None]] = None

        self._dropdown: Optional[tk.Toplevel] = None
        self._listbox: Optional[tk.Listbox] = None
        self._suggestions: List[Dict[str, Any]] = []
        self._debounce_id: Optional[str] = None
        self._debounce_ms = 300

        # Bind para detectar digitação
        self.bind("<KeyRelease>", self._on_key_release)
        self.bind("<FocusOut>", self._on_focus_out)

    def set_suggester(self, fn: Callable[[str], List[Dict[str, Any]]]) -> None:
        """Define a função que retorna sugestões baseadas no texto digitado."""
        self._suggester = fn

    def _on_key_release(self, event) -> Optional[Literal["break"]]:
        """Chamado ao soltar tecla (digitação)."""
        key = event.keysym

        # Teclas especiais: navegar/confirmar/cancelar
        if key == "Down":
            self._navigate_dropdown(1)
            return "break"
        elif key == "Up":
            self._navigate_dropdown(-1)
            return "break"
        elif key == "Return":
            self._confirm_selection()
            return "break"
        elif key == "Escape":
            self._close_dropdown()
            return "break"

        # Teclas de navegação/modificação: não fazer nada
        if key in (
            "Left",
            "Right",
            "Home",
            "End",
            "Shift_L",
            "Shift_R",
            "Control_L",
            "Control_R",
            "Alt_L",
            "Alt_R",
        ):
            return None

        # Debounce: cancelar timer anterior
        if self._debounce_id:
            self.after_cancel(self._debounce_id)

        # Agendar busca após delay
        self._debounce_id = self.after(self._debounce_ms, self._fetch_suggestions)
        return None

    def _fetch_suggestions(self) -> None:
        """Busca sugestões e exibe dropdown."""
        text = self.get().strip()

        # Menos de 2 caracteres: fechar dropdown
        if len(text) < 2:
            self._close_dropdown()
            return

        # Sem suggester configurado
        if not self._suggester:
            return

        # Buscar sugestões
        try:
            self._suggestions = self._suggester(text)
        except Exception:
            self._suggestions = []

        # Nenhuma sugestão: fechar dropdown
        if not self._suggestions:
            self._close_dropdown()
            return

        # Exibir dropdown
        self._show_dropdown()

    def _show_dropdown(self) -> None:
        """Cria/atualiza o dropdown com sugestões."""
        # Criar dropdown se não existir
        if not self._dropdown:
            self._create_dropdown()

        # Limpar listbox
        if self._listbox:
            self._listbox.delete(0, tk.END)

            # Adicionar sugestões
            for item in self._suggestions:
                label = item.get("label", "")
                self._listbox.insert(tk.END, label)

            # Selecionar primeiro item
            if self._suggestions:
                self._listbox.selection_set(0)
                self._listbox.activate(0)

        # Posicionar dropdown abaixo do Entry
        if self._dropdown:
            self._position_dropdown()
            self._dropdown.deiconify()

    def _create_dropdown(self) -> None:
        """Cria o Toplevel com Listbox."""
        self._dropdown = tk.Toplevel(self)
        self._dropdown.withdraw()
        self._dropdown.overrideredirect(True)

        # Listbox com scrollbar
        frame = ttk.Frame(self._dropdown)
        frame.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(frame, orient="vertical")
        self._listbox = tk.Listbox(
            frame,
            height=10,
            yscrollcommand=scrollbar.set,
            exportselection=False,
        )
        scrollbar.config(command=self._listbox.yview)

        self._listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Bind: clique duplo ou Enter para selecionar
        self._listbox.bind("<Double-Button-1>", lambda e: self._confirm_selection())
        self._listbox.bind("<Return>", lambda e: self._confirm_selection())
        self._listbox.bind("<Escape>", lambda e: self._close_dropdown())

    def _position_dropdown(self) -> None:
        """Posiciona dropdown abaixo do Entry."""
        if not self._dropdown:
            return

        # Atualizar geometria
        self.update_idletasks()

        # Posição do Entry
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        width = self.winfo_width()

        # Definir geometria do dropdown
        self._dropdown.geometry(f"{width}x200+{x}+{y}")

    def _navigate_dropdown(self, direction: int) -> None:
        """Navega no dropdown (↑/↓)."""
        if not self._listbox or not self._suggestions:
            return

        # Índice atual
        try:
            current = self._listbox.curselection()[0]
        except (IndexError, tk.TclError):
            current = 0

        # Novo índice
        new_index = current + direction
        if 0 <= new_index < len(self._suggestions):
            self._listbox.selection_clear(0, tk.END)
            self._listbox.selection_set(new_index)
            self._listbox.activate(new_index)
            self._listbox.see(new_index)

    def _confirm_selection(self) -> None:
        """Confirma seleção do item no dropdown."""
        if not self._listbox or not self._suggestions:
            return

        # Obter item selecionado
        try:
            index = self._listbox.curselection()[0]
            item = self._suggestions[index]
        except (IndexError, tk.TclError):
            return

        # Preencher Entry com label
        label = item.get("label", "")
        self.delete(0, tk.END)
        self.insert(0, label)

        # Callback
        if self.on_pick:
            try:
                self.on_pick(item)
            except Exception:
                pass

        # Fechar dropdown
        self._close_dropdown()

    def _close_dropdown(self) -> None:
        """Fecha o dropdown."""
        if self._dropdown:
            self._dropdown.withdraw()

    def _on_focus_out(self, event) -> None:
        """Fecha dropdown ao perder foco (com delay para permitir clique)."""
        # Delay para permitir clique no dropdown
        self.after(200, self._close_dropdown)

    def set(self, text: str) -> None:
        """Define o texto do Entry."""
        self.delete(0, tk.END)
        self.insert(0, text)
