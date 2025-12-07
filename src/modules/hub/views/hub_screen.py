"""HubScreen - Tela de notas e histórico do Hub."""

from __future__ import annotations

import tkinter as tk
from typing import Any


class HubScreen(tk.Frame):
    """Tela principal do Hub com histórico de notas."""

    def __init__(self, parent: tk.Widget, **kwargs: Any) -> None:
        """Inicializa a tela do Hub.

        Args:
            parent: Widget pai
            **kwargs: Argumentos adicionais para o Frame
        """
        super().__init__(parent, **kwargs)
        self.notes_history: tk.Text | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Configura a interface do usuário."""
        # TODO: Implementar UI completa
        # Por enquanto, apenas cria o widget de histórico de notas
        self.notes_history = tk.Text(self)
        if self.notes_history:
            self.notes_history.pack(fill=tk.BOTH, expand=True)

    def render_notes(self, notes: list[tuple[Any, ...]]) -> None:
        """Renderiza notas no histórico.

        Implementa defensive checks para evitar TclError quando o widget
        foi destruído.

        Args:
            notes: Lista de tuplas contendo dados das notas
        """
        # Defensive check: verifica se o widget ainda existe
        if not self._guard_widgets():
            return

        # Limpa o conteúdo atual
        if self.notes_history:
            self.notes_history.delete("1.0", tk.END)

            # Renderiza cada nota
            for note in notes:
                # TODO: Implementar formatação adequada das notas
                # Por enquanto, apenas converte para string
                note_text = str(note) + "\n"
                self.notes_history.insert(tk.END, note_text)

    def _guard_widgets(self) -> bool:
        """Evita TclError se janela/widget foram destruídos.

        Returns:
            True se os widgets existem e são válidos, False caso contrário
        """
        try:
            return self.winfo_exists() and self.notes_history is not None and self.notes_history.winfo_exists()
        except Exception:
            return False
