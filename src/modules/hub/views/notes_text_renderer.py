# -*- coding: utf-8 -*-
"""Helper de renderização de notas em widget tk.Text com layout clean (estilo chat).

Este módulo centraliza a lógica de renderização de notas em widgets tk.Text,
fornecendo um layout limpo e organizado similar ao WhatsApp:
- Blocos separados por mensagem
- Timestamp e autor na linha superior (autor em negrito/cor)
- Corpo da mensagem com margem à esquerda
- Suporte para mensagens apagadas (soft delete: "__RC_DELETED__")
- Tags por nota para suportar menu de contexto e ações

Usado por:
- src/modules/hub/panels.py (_render_notes_to_text_widget)
- src/modules/hub/views/hub_notes_view.py (render_notes)
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)
log = logger  # alias para B110 tratados


def _configure_text_widget_tags(text_widget: Any) -> None:
    """Configura tags fixas no widget Text para renderização de notas.

    Tags configuradas:
    - note_ts: timestamp (fonte menor, cinza)
    - note_author: autor (negrito)
    - note_body: corpo da mensagem (wrap word, sem margem)
    - note_deleted: mensagem apagada (itálico, cinza)
    - note_block: espaçamento entre blocos

    Args:
        text_widget: Widget tk.Text onde as tags serão configuradas
    """
    try:
        # Timestamp: fonte menor, cinza claro
        text_widget.tag_configure("note_ts", foreground="#999999", font=("", 9))

        # Autor: negrito, fonte normal
        text_widget.tag_configure("note_author", font=("", 10, "bold"))

        # Corpo: wrap word, sem margem
        text_widget.tag_configure("note_body", wrap="word", lmargin1=0, lmargin2=0)

        # Mensagem apagada: itálico, cinza, sem margem
        text_widget.tag_configure("note_deleted", foreground="#999999", font=("", 10, "italic"), lmargin1=0, lmargin2=0)

        # Espaçamento entre blocos (respiro entre mensagens)
        text_widget.tag_configure("note_block", spacing3=12)
    except Exception as exc:
        logger.debug(f"Erro ao configurar tags do widget: {exc}")


def render_notes_text(
    text_widget: Any,
    notes: List[Dict[str, Any]],
    *,
    resolve_display_name: Optional[Callable[[str], str]] = None,
    author_tags_dict: Optional[Dict[str, str]] = None,
    ensure_author_tag_fn: Optional[Callable[[Any, str, Dict[str, str]], str]] = None,
) -> None:
    """Renderiza lista de notas em widget tk.Text com layout clean (2 linhas por nota).

    Layout por mensagem (2 linhas):
    - Linha 1 (cabeçalho): "{DD/MM HH:MM} - {NOME}:"
    - Linha 2 (corpo): mensagem com quebras originais preservadas
    - Linha em branco após cada mensagem

    Cria uma tag "noteid_<ID>" por mensagem para suportar menu de contexto.
    Armazena metadados em text_widget._note_meta[note_id] para ações (copiar, etc.).

    Args:
        text_widget: Widget tk.Text onde as notas serão renderizadas
        notes: Lista de dicionários/objetos com dados das notas
        resolve_display_name: Callback para resolver email -> nome de exibição
        author_tags_dict: Dicionário de tags de cores por autor (email → tag_name)
        ensure_author_tag_fn: Função para criar/obter tag de cor do autor
    """
    # Garantir que o widget existe
    try:
        if not text_widget.winfo_exists():
            return
    except Exception as winfo_exc:  # noqa: BLE001
        # Widget pode ter sido destruído: abort silencioso é intencional
        log.debug("Widget de notas não existe mais: %s", type(winfo_exc).__name__)
        return

    # Configurar tags fixas (primeira vez ou sempre, é idempotente)
    _configure_text_widget_tags(text_widget)

    # Habilitar edição, limpar conteúdo
    text_widget.configure(state="normal")
    text_widget.delete("1.0", "end")

    # Dicionário para armazenar metadados das notas (para copiar, etc.)
    if not hasattr(text_widget, "_note_meta"):
        text_widget._note_meta = {}
    text_widget._note_meta.clear()

    # Renderizar cada nota
    for note in notes:
        # Suportar tanto dicts quanto objetos (NoteItemView)
        if hasattr(note, "id"):  # É objeto
            note_id = str(note.id)
            author_email = (note.author_email or "").strip().lower()
            author_name = (note.author_name or "").strip()
            created_at = getattr(note, "created_at", "")
            body = (note.body or "").strip()
        else:  # É dict
            note_id = str(note.get("id", ""))
            author_email = (note.get("author_email") or "").strip().lower()
            author_name = (note.get("author_name") or "").strip()
            created_at = note.get("created_at", "")
            body = (note.get("body") or "").strip()

        if not note_id:
            continue  # Pular notas sem ID

        # Resolver nome de exibição
        if not author_name and resolve_display_name and author_email:
            author_name = resolve_display_name(author_email)
        if not author_name:
            author_name = author_email or "Usuário"

        # Formatar timestamp
        timestamp_str = _format_timestamp_simple(created_at)

        # Detectar soft delete
        is_deleted = body.startswith("__RC_DELETED__")

        # Normalizar corpo (apenas quebras de linha Windows)
        if is_deleted:
            body_text = "Mensagem apagada"
        else:
            # Normalizar apenas \r\n e \r para \n, manter quebras originais
            body_text = (body or "").replace("\r\n", "\n").replace("\r", "\n")

        # Armazenar metadados para ações (copiar, etc.)
        text_widget._note_meta[note_id] = {
            "id": note_id,
            "author_email": author_email,
            "author_name": author_name,
            "created_at": created_at,
            "body": body,
            "is_deleted": is_deleted,
        }

        # Tag única para esta nota (para identificar no menu de contexto)
        note_tag = f"noteid_{note_id}"

        # === Linha 1: Cabeçalho (TIMESTAMP - AUTOR:) ===

        # 1. Inserir timestamp com tag "note_ts"
        text_widget.insert("end", timestamp_str, ("note_ts", note_tag))

        # 2. Inserir " - " (separador)
        text_widget.insert("end", " - ", (note_tag,))

        # 3. Inserir autor com tag de cor (se disponível) + negrito
        author_color_tag = None
        if ensure_author_tag_fn and author_tags_dict is not None and author_email:
            try:
                author_color_tag = ensure_author_tag_fn(text_widget, author_email, author_tags_dict)
            except Exception as exc:
                logger.debug(f"Erro ao obter tag de autor: {exc}")

        if author_color_tag:
            text_widget.insert("end", author_name, (author_color_tag, "note_author", note_tag))
        else:
            text_widget.insert("end", author_name, ("note_author", note_tag))

        # 4. Inserir ":" + quebra de linha
        text_widget.insert("end", ":\n", (note_tag,))

        # === Linha 2: Corpo da mensagem ===
        if is_deleted:
            text_widget.insert("end", body_text, ("note_deleted", note_tag))
        else:
            text_widget.insert("end", body_text, ("note_body", note_tag))

        # === Separação entre mensagens (linha em branco) ===
        text_widget.insert("end", "\n\n", ("note_block", note_tag))

    # Desabilitar edição
    text_widget.configure(state="disabled")

    # Scrollar para o fim
    try:
        text_widget.see("end")
    except Exception as scroll_exc:  # noqa: BLE001
        # Widget pode ter sido destruído durante scroll: não crítico
        log.debug("Falha ao scrollar widget de notas: %s", type(scroll_exc).__name__)


def _format_timestamp_simple(timestamp: Any) -> str:
    """Formata timestamp para exibição simples.

    Args:
        timestamp: Timestamp (string ISO ou datetime)

    Returns:
        String formatada (ex: "21/12 14:30" ou "??")
    """
    if not timestamp:
        return "??"

    try:
        from datetime import datetime

        # Se já é string, tentar parsear
        if isinstance(timestamp, str):
            # Tentar formato ISO (com ou sem timezone)
            for fmt in [
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S",
            ]:
                try:
                    dt = datetime.strptime(timestamp.replace("+00:00", "Z"), fmt)
                    return dt.strftime("%d/%m %H:%M")
                except ValueError:
                    continue

            # Se não conseguiu parsear, retornar parte relevante da string
            return timestamp[:16] if len(timestamp) >= 16 else timestamp

        # Se é datetime
        if hasattr(timestamp, "strftime"):
            return timestamp.strftime("%d/%m %H:%M")

        return str(timestamp)[:16]

    except Exception as exc:
        logger.debug(f"Erro ao formatar timestamp: {exc}")
        return "??"
