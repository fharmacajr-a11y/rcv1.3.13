from __future__ import annotations

import logging
import tkinter as tk
from typing import Callable, Optional

try:
    import ttkbootstrap as tb
except Exception:
    from tkinter import ttk as tb  # fallback

from src.ui.components import create_footer_buttons

logger = logging.getLogger(__name__)


class ClientesFooter(tb.Frame):  # type: ignore[misc]
    """Barra inferior com botões de ações da tela de Clientes."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        on_novo: Callable[[], None],
        on_editar: Callable[[], None],
        on_subpastas: Callable[[], None],
        on_enviar_supabase: Callable[[], None],
        on_enviar_pasta: Callable[[], None],
        on_excluir: Optional[Callable[[], None]] = None,
        # on_obrigacoes removido - funcionalidade movida para Hub
        on_batch_delete: Callable[[], None],
        on_batch_restore: Callable[[], None],
        on_batch_export: Callable[[], None],
    ) -> None:
        super().__init__(master)

        buttons = create_footer_buttons(
            self,
            on_novo=on_novo,
            on_editar=on_editar,
            on_subpastas=on_subpastas,
            on_enviar=on_enviar_supabase,
            on_enviar_pasta=on_enviar_pasta,
            on_excluir=on_excluir,
            on_obrigacoes=None,  # Sempre None - funcionalidade removida
            # Batch desabilitado na UI principal de clientes
            on_batch_delete=None,
            on_batch_restore=None,
            on_batch_export=None,
        )
        buttons.frame.pack(fill="x", padx=0, pady=0)

        self.btn_novo = buttons.novo
        self.btn_editar = buttons.editar
        self.btn_subpastas = buttons.subpastas
        self.btn_enviar = buttons.enviar
        self.btn_excluir = buttons.excluir
        self.btn_obrigacoes = buttons.obrigacoes
        self.enviar_menu = buttons.enviar_menu
        self.btn_batch_delete = buttons.batch_delete
        self.btn_batch_restore = buttons.batch_restore
        self.btn_batch_export = buttons.batch_export

        self._uploading_busy = False
        self._send_button_prev_text: Optional[str] = None
        self._pick_prev_states: dict[tk.Widget, str] = {}  # Estado dos botões antes do pick mode

        # Alias para compatibilidade
        self.frame = buttons.frame

    def set_uploading(self, uploading: bool) -> None:
        """Desabilita/ajusta textos durante upload em andamento."""
        uploading = bool(uploading)
        if uploading == self._uploading_busy:
            return

        self._uploading_busy = uploading

        if uploading:
            try:
                if self.btn_enviar:
                    self._send_button_prev_text = self.btn_enviar.cget("text")
                    self.btn_enviar.configure(text="Enviando…")
            except Exception as exc:  # noqa: BLE001
                logger.debug("Falha ao ajustar texto de envio durante upload: %s", exc)
        else:
            try:
                if self.btn_enviar and self._send_button_prev_text is not None:
                    self.btn_enviar.configure(text=self._send_button_prev_text)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Falha ao restaurar texto do botao de envio: %s", exc)
            self._send_button_prev_text = None

    def _iter_pick_buttons(self) -> list[tk.Widget]:
        """Lista exatamente os botões do rodapé que devem ser controlados em pick mode."""
        buttons = []
        # Adiciona apenas os botões que existem e não são None
        # Nota: btn_obrigacoes removido - funcionalidade movida para toolbar superior
        for btn in [self.btn_novo, self.btn_editar, self.btn_subpastas, self.btn_enviar]:
            if btn is not None:
                buttons.append(btn)
        return buttons

    def enter_pick_mode(self) -> None:
        """Desabilita botões do rodapé em modo seleção de clientes (FIX-CLIENTES-007)."""
        logger.debug("FIX-007: ClientesFooter.enter_pick_mode()")

        # Salva estado original e desabilita
        for btn in self._iter_pick_buttons():
            try:
                if btn not in self._pick_prev_states:
                    current_state = str(btn["state"])
                    self._pick_prev_states[btn] = current_state
                btn.configure(state="disabled")
            except (tk.TclError, KeyError, AttributeError) as exc:
                logger.debug(
                    "Ignorando falha ao desabilitar botão %r em pick mode: %s",
                    btn,
                    exc,
                )

    def leave_pick_mode(self) -> None:
        """Restaura estados dos botões do rodapé após sair do modo seleção (FIX-CLIENTES-007)."""
        logger.debug("FIX-007: ClientesFooter.leave_pick_mode()")

        # Restaura estados originais
        for btn in self._iter_pick_buttons():
            try:
                prev = self._pick_prev_states.get(btn)
                if prev is not None:
                    btn.configure(state=prev)
            except (tk.TclError, KeyError, AttributeError) as exc:
                logger.debug(
                    "Ignorando falha ao restaurar botão %r após pick mode: %s",
                    btn,
                    exc,
                )

        self._pick_prev_states.clear()


__all__ = ["ClientesFooter"]
