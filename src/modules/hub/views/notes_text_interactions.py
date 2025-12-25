# -*- coding: utf-8 -*-
"""Interações (menu de contexto) para widget de notas.

Este módulo fornece menu de contexto (clique direito) no widget de notas,
permitindo ações por mensagem:
- Copiar mensagem (apenas corpo)
- Copiar tudo (timestamp + autor + corpo)
- Apagar mensagem (soft delete)

O menu identifica a nota clicada pela tag "noteid_<ID>" e usa metadados
armazenados em text_widget._note_meta para obter dados da nota.
"""

from __future__ import annotations

import logging
import sys
import tkinter as tk
from typing import Any, Callable, Optional

log = logging.getLogger(__name__)

logger = logging.getLogger(__name__)


def install_notes_context_menu(
    text_widget: Any,
    *,
    on_delete_note_click: Optional[Callable[[str], None]] = None,
    current_user_email: Optional[str] = None,
) -> None:
    """Instala menu de contexto (clique direito) no widget de notas.

    Menu oferece:
    - Copiar mensagem: copia apenas o corpo da nota
    - Copiar tudo: copia timestamp + autor + corpo
    - Apagar mensagem: chama callback on_delete_note_click(note_id) ou mostra aviso se sem permissão

    O menu identifica a nota pela tag "noteid_<ID>" presente no índice clicado.
    Se não houver nota no local clicado, mostra menu reduzido (copiar seleção).

    Args:
        text_widget: Widget tk.Text onde o menu será instalado
        on_delete_note_click: Callback para apagar nota (recebe note_id)
        current_user_email: Email do usuário atual (para validar permissão)
    """
    # Criar menu de contexto
    context_menu = tk.Menu(text_widget, tearoff=0)

    # Estado: note_id da nota clicada (preenchido no evento de clique)
    menu_state = {"note_id": None, "click_x": 0, "click_y": 0}

    def _get_note_id_at_click(x: int, y: int) -> Optional[str]:
        """Identifica note_id pela tag no índice clicado.

        Args:
            x, y: Coordenadas do clique

        Returns:
            note_id (string) ou None se não encontrado
        """
        try:
            index = text_widget.index(f"@{x},{y}")
            tags = text_widget.tag_names(index)

            # Buscar tag "noteid_<ID>"
            for tag in tags:
                if tag.startswith("noteid_"):
                    return tag.replace("noteid_", "")

            return None
        except Exception as exc:
            logger.debug(f"Erro ao identificar nota no clique: {exc}")
            return None

    def _copy_text_to_clipboard(text: str) -> None:
        """Copia texto para área de transferência.

        Args:
            text: Texto a ser copiado
        """
        try:
            # Usar clipboard do widget (mais confiável que widget.clipboard_*)
            text_widget.clipboard_clear()
            text_widget.clipboard_append(text)
            # Atualizar clipboard (necessário em alguns sistemas)
            text_widget.update()
        except Exception as exc:
            logger.warning(f"Erro ao copiar para clipboard: {exc}")

    def _on_copy_message() -> None:
        """Copia apenas o corpo da mensagem."""
        note_id = menu_state.get("note_id")
        if not note_id:
            return

        meta = getattr(text_widget, "_note_meta", {}).get(note_id)
        if not meta:
            return

        # Se deletada, copiar "Mensagem apagada"
        if meta.get("is_deleted"):
            _copy_text_to_clipboard("Mensagem apagada")
        else:
            body = meta.get("body", "")
            _copy_text_to_clipboard(body)

    def _on_copy_all() -> None:
        """Copia timestamp + autor + corpo."""
        note_id = menu_state.get("note_id")
        if not note_id:
            return

        meta = getattr(text_widget, "_note_meta", {}).get(note_id)
        if not meta:
            return

        # Formatar: [timestamp] Autor: corpo
        from src.modules.hub.views.notes_text_renderer import _format_timestamp_simple

        ts = _format_timestamp_simple(meta.get("created_at", ""))
        author = meta.get("author_name", "Usuário")
        body = "Mensagem apagada" if meta.get("is_deleted") else meta.get("body", "")

        full_text = f"[{ts}] {author}: {body}"
        _copy_text_to_clipboard(full_text)

    def _on_delete_message() -> None:
        """Apaga mensagem (soft delete)."""
        note_id = menu_state.get("note_id")
        if not note_id:
            return

        # Validar permissão se current_user_email disponível
        if current_user_email:
            meta = getattr(text_widget, "_note_meta", {}).get(note_id)
            if meta:
                note_author_email = meta.get("author_email", "").strip().lower()
                if note_author_email and current_user_email.strip().lower() != note_author_email:
                    # Mostrar aviso usando messagebox
                    try:
                        from tkinter import messagebox

                        messagebox.showinfo("Permissão negada", "Você só pode apagar mensagens enviadas por você.")
                    except Exception as msg_exc:  # noqa: BLE001
                        # UI defensiva: messagebox pode falhar se widget foi destruído
                        log.debug("Falha ao exibir messagebox de permissão: %s", type(msg_exc).__name__)
                    return

        # Chamar callback de deleção
        if on_delete_note_click:
            on_delete_note_click(note_id)

    def _on_copy_selection() -> None:
        """Copia seleção atual do widget."""
        try:
            selected_text = text_widget.selection_get()
            _copy_text_to_clipboard(selected_text)
        except tk.TclError:
            # Sem seleção
            pass

    def _show_context_menu(event) -> str:
        """Mostra menu de contexto no clique direito.

        Args:
            event: Evento de clique

        Returns:
            "break" para prevenir propagação do evento
        """
        # Identificar nota clicada
        note_id = _get_note_id_at_click(event.x, event.y)
        menu_state["note_id"] = note_id
        menu_state["click_x"] = event.x
        menu_state["click_y"] = event.y

        # Limpar menu atual
        context_menu.delete(0, "end")

        if note_id:
            # Menu completo: com ações da nota
            meta = getattr(text_widget, "_note_meta", {}).get(note_id)
            is_deleted = meta.get("is_deleted", False) if meta else False

            context_menu.add_command(label="Copiar mensagem", command=_on_copy_message)
            context_menu.add_command(label="Copiar tudo", command=_on_copy_all)
            context_menu.add_separator()

            # Só mostrar "Apagar" se não estiver já apagada
            if not is_deleted and on_delete_note_click:
                context_menu.add_command(label="Apagar mensagem", command=_on_delete_message)
        else:
            # Menu reduzido: apenas copiar seleção (se houver)
            try:
                text_widget.selection_get()
                context_menu.add_command(label="Copiar seleção", command=_on_copy_selection)
            except tk.TclError:
                # Sem seleção: menu vazio (ou mensagem)
                context_menu.add_command(label="(Nenhuma ação disponível)", state="disabled")

        # Mostrar menu
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()

        return "break"

    # Bind do menu de contexto
    # Windows/Linux: Button-3 (botão direito)
    text_widget.bind("<Button-3>", _show_context_menu)

    # macOS: Button-2 (Control+Click ou botão direito)
    if sys.platform == "darwin":
        text_widget.bind("<Button-2>", _show_context_menu)
