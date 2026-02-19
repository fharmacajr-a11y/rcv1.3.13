# -*- coding: utf-8 -*-
"""CTkAutocompleteEntry - Entry com autocomplete 100% CustomTkinter.

MICROFASE 28: Substitui AutocompleteEntry (que herdava de ctk.CTkEntry).
Sem dependências de widgets legados, usa apenas CustomTkinter.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional, cast

# CustomTkinter: fonte única centralizada (SSoT)
from src.ui.ctk_config import ctk
from src.ui.typing_utils import TkInfoMixin, TkToplevelMixin

log = logging.getLogger(__name__)


class CTkAutocompleteEntry(ctk.CTkFrame):
    """Entry com autocomplete dropdown (100% CustomTkinter).

    API:
        entry.get() - Retorna texto do entry
        entry.set(text) - Define texto do entry
        entry.set_suggester(fn) - Define função de sugestões: fn(text) -> list[dict]
        entry.on_pick - Callback quando item é selecionado
        entry.bind(event, fn) - Bind de eventos no entry interno
        entry.focus() - Foca no entry

    Uso:
        entry = CTkAutocompleteEntry(parent)
        entry.set_suggester(lambda text: [{"label": "Item", "data": {...}}])
        entry.on_pick = lambda item: print(f"Selecionado: {item}")
    """

    def __init__(
        self,
        master: Any,
        placeholder: str = "",
        width: int = 200,
        **kwargs: Any,
    ) -> None:
        """Inicializa CTkAutocompleteEntry.

        Args:
            master: Widget pai
            placeholder: Texto placeholder
            width: Largura do entry
            **kwargs: Argumentos para CTkFrame
        """
        super().__init__(master, **kwargs)

        # Estado interno
        self._suggester: Optional[Callable[[str], list[dict[str, Any]]]] = None
        self._suggestions: list[dict[str, Any]] = []
        self._dropdown: Optional[ctk.CTkToplevel] = None
        self._dropdown_frame: Optional[ctk.CTkScrollableFrame] = None
        self._selected_index: int = -1
        self._debounce_id: Optional[str] = None
        self._debounce_ms: int = 300
        self.on_pick: Optional[Callable[[dict[str, Any]], None]] = None

        # Entry principal
        self.entry = ctk.CTkEntry(
            self,
            placeholder_text=placeholder,
            width=width,
        )
        self.entry.pack(fill="x", expand=True)

        # Binds
        self.entry.bind("<KeyRelease>", self._on_key_release)
        self.entry.bind("<Down>", self._on_down)
        self.entry.bind("<Up>", self._on_up)
        self.entry.bind("<Return>", self._on_return)
        self.entry.bind("<Escape>", self._on_escape)
        self.entry.bind("<FocusOut>", self._on_focus_out)

    def get(self) -> str:
        """Retorna texto do entry."""
        return self.entry.get()

    def set(self, text: str) -> None:
        """Define texto do entry."""
        self.entry.delete(0, "end")
        self.entry.insert(0, text)

    def insert(self, index: int | str, text: str) -> None:
        """Insere texto no entry (compatibilidade)."""
        self.entry.insert(index, text)

    def delete(self, first: int | str, last: Optional[int | str] = None) -> None:
        """Deleta texto do entry (compatibilidade)."""
        if last is None:
            self.entry.delete(first)
        else:
            self.entry.delete(first, last)

    def bind(self, event: str, func: Callable, add: str = "") -> str:
        """Bind evento no entry interno."""
        return self.entry.bind(event, func, add)

    def focus(self) -> None:
        """Foca no entry."""
        self.entry.focus()

    def focus_set(self) -> None:
        """Foca no entry (compatibilidade)."""
        self.entry.focus_set()

    def set_suggester(self, fn: Callable[[str], list[dict[str, Any]]]) -> None:
        """Define função que retorna sugestões.

        Args:
            fn: Função que recebe texto e retorna lista de dicts com 'label' e 'data'
        """
        self._suggester = fn

    def _on_key_release(self, event: Any) -> None:
        """Callback de tecla liberada (debounced)."""
        # Ignorar teclas de navegação
        if event.keysym in ("Down", "Up", "Return", "Escape", "Left", "Right", "Home", "End"):
            return

        # Cancelar debounce anterior
        if self._debounce_id:
            self.after_cancel(self._debounce_id)

        # Agendar busca
        self._debounce_id = self.after(self._debounce_ms, self._fetch_suggestions)

    def _fetch_suggestions(self) -> None:
        """Busca sugestões e exibe dropdown."""
        text = self.get().strip()

        # Menos de 2 caracteres: fechar
        if len(text) < 2:
            self._close_dropdown()
            return

        # Sem suggester
        if not self._suggester:
            return

        # Buscar
        try:
            self._suggestions = self._suggester(text)
        except Exception as e:
            log.error(f"Erro ao buscar sugestões: {e}")
            self._suggestions = []

        # Sem sugestões: fechar
        if not self._suggestions:
            self._close_dropdown()
            return

        # Exibir
        self._show_dropdown()

    def _show_dropdown(self) -> None:
        """Cria/atualiza dropdown com sugestões."""
        # Criar dropdown se não existir
        if not self._dropdown:
            self._create_dropdown()

        # Limpar frame
        if self._dropdown_frame:
            for widget in cast(TkInfoMixin, self._dropdown_frame).winfo_children():
                cast(Any, widget).destroy()  # destroy disponível em runtime para todos widgets Tk

        # Adicionar sugestões
        for idx, item in enumerate(self._suggestions):
            label = item.get("label", "")
            btn = ctk.CTkButton(
                self._dropdown_frame,
                text=label,
                command=lambda i=idx: self._select_suggestion(i),
                anchor="w",
                fg_color="transparent",
                hover_color=("gray85", "gray25"),
            )
            btn.pack(fill="x", padx=2, pady=1)

        # Posicionar e mostrar
        self._position_dropdown()
        if self._dropdown:
            cast(TkToplevelMixin, self._dropdown).deiconify()

    def _create_dropdown(self) -> None:
        """Cria dropdown toplevel."""
        self._dropdown = ctk.CTkToplevel(self)
        cast(TkToplevelMixin, self._dropdown).withdraw()
        cast(TkToplevelMixin, self._dropdown).overrideredirect(True)

        # Frame scrollável
        self._dropdown_frame = ctk.CTkScrollableFrame(
            self._dropdown,
            width=cast(TkInfoMixin, self.entry).winfo_reqwidth() - 4,
            height=200,
        )
        self._dropdown_frame.pack(fill="both", expand=True)

    def _position_dropdown(self) -> None:
        """Posiciona dropdown abaixo do entry."""
        if not self._dropdown:
            return

        # Atualizar geometria
        self.update_idletasks()

        # Posição do entry
        entry_info = cast(TkInfoMixin, self.entry)
        x = entry_info.winfo_rootx()
        y = entry_info.winfo_rooty() + entry_info.winfo_height()
        w = self.entry.winfo_width()

        # Posicionar dropdown
        self._dropdown.geometry(f"{w}x200+{x}+{y}")

    def _close_dropdown(self) -> None:
        """Fecha dropdown."""
        if self._dropdown:
            cast(TkToplevelMixin, self._dropdown).withdraw()
        self._selected_index = -1

    def _select_suggestion(self, index: int) -> None:
        """Seleciona sugestão por índice."""
        if 0 <= index < len(self._suggestions):
            item = self._suggestions[index]

            # Atualizar entry
            self.set(item.get("label", ""))

            # Chamar callback
            if self.on_pick:
                try:
                    self.on_pick(item)
                except Exception as e:
                    log.error(f"Erro em on_pick: {e}")

            # Fechar dropdown
            self._close_dropdown()

    def _on_down(self, event: Any) -> Optional[str]:
        """Navega para baixo no dropdown."""
        if self._suggestions and self._dropdown and cast(TkToplevelMixin, self._dropdown).winfo_viewable():
            self._selected_index = min(self._selected_index + 1, len(self._suggestions) - 1)
            # TODO: highlight visual
        return "break"

    def _on_up(self, event: Any) -> Optional[str]:
        """Navega para cima no dropdown."""
        if self._suggestions and self._dropdown and cast(TkToplevelMixin, self._dropdown).winfo_viewable():
            self._selected_index = max(self._selected_index - 1, 0)
            # TODO: highlight visual
        return "break"

    def _on_return(self, event: Any) -> Optional[str]:
        """Seleciona item atual ou fecha."""
        if self._dropdown and cast(TkToplevelMixin, self._dropdown).winfo_viewable():
            if 0 <= self._selected_index < len(self._suggestions):
                self._select_suggestion(self._selected_index)
            else:
                # Selecionar primeiro se nenhum destacado
                if self._suggestions:
                    self._select_suggestion(0)
            return "break"
        return None

    def _on_escape(self, event: Any) -> Optional[str]:
        """Fecha dropdown."""
        self._close_dropdown()
        return "break"

    def _on_focus_out(self, event: Any) -> None:
        """Fecha dropdown após perder foco (com delay)."""
        # Delay para permitir clique no botão
        self.after(200, self._close_dropdown)

    def destroy(self) -> None:
        """Cleanup ao destruir."""
        # Cancelar debounce
        if self._debounce_id:
            self.after_cancel(self._debounce_id)

        # Destruir dropdown
        if self._dropdown:
            try:
                self._dropdown.destroy()
            except Exception:
                pass

        # Destruir frame pai
        super().destroy()


__all__ = ["CTkAutocompleteEntry"]
