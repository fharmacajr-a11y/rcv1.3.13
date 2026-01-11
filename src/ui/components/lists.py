# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import tkinter as tk
import tkinter.font as tkfont
from typing import Any, Callable

import ttkbootstrap as tb

from src.config.constants import COL_STATUS_WIDTH  # <-- adicionar
from src.config.constants import (
    COL_CNPJ_WIDTH,
    COL_ID_WIDTH,
    COL_NOME_WIDTH,
    COL_OBS_WIDTH,
    COL_RAZAO_WIDTH,
    COL_ULTIMA_WIDTH,
    COL_WHATSAPP_WIDTH,
    # Novas constantes de modernização
    TREEVIEW_ROW_HEIGHT,
    TREEVIEW_FONT_FAMILY,
    TREEVIEW_FONT_SIZE,
    TREEVIEW_HEADER_FONT_SIZE,
    # Cores de status
    STATUS_NOVO_CLIENTE_BG,
    STATUS_NOVO_CLIENTE_FG,
    STATUS_SEM_RESPOSTA_BG,
    STATUS_SEM_RESPOSTA_FG,
    STATUS_ANALISE_BG,
    STATUS_ANALISE_FG,
    STATUS_AGUARDANDO_BG,
    STATUS_AGUARDANDO_FG,
    STATUS_FINALIZADO_BG,
    STATUS_FINALIZADO_FG,
    STATUS_FOLLOWUP_BG,
    STATUS_FOLLOWUP_FG,
    # Zebra striping
    ZEBRA_EVEN_BG,
    ZEBRA_ODD_BG,
)

OBS_FG = "#0d6efd"

logger = logging.getLogger(__name__)
log = logger

__all__ = ["create_clients_treeview", "configure_status_tags", "apply_zebra_striping"]


def _get_modern_font() -> tkfont.Font:
    """Retorna uma fonte moderna para a Treeview.

    Tenta usar Segoe UI (Windows) ou Roboto, com fallback para a fonte padrão.
    """
    try:
        # Tenta criar fonte com Segoe UI (disponível no Windows 7+)
        font = tkfont.Font(family=TREEVIEW_FONT_FAMILY, size=TREEVIEW_FONT_SIZE)
        # Verifica se a fonte está disponível
        if font.actual()["family"].lower() != TREEVIEW_FONT_FAMILY.lower():
            # Fallback para Roboto ou Arial
            for fallback in ("Roboto", "Arial", "Helvetica"):
                try:
                    font = tkfont.Font(family=fallback, size=TREEVIEW_FONT_SIZE)
                    if font.actual()["family"].lower() == fallback.lower():
                        break
                except Exception:
                    continue
        return font
    except Exception:
        # Fallback final para fonte padrão
        return tkfont.nametofont("TkDefaultFont")


def _get_header_font() -> tkfont.Font:
    """Retorna uma fonte para os cabeçalhos da Treeview."""
    try:
        font = tkfont.Font(family=TREEVIEW_FONT_FAMILY, size=TREEVIEW_HEADER_FONT_SIZE, weight="bold")
        return font
    except Exception:
        default = tkfont.nametofont("TkDefaultFont")
        return default.copy()


def configure_status_tags(tree: tb.Treeview) -> None:
    """Configura tags de status com cores dinâmicas para a Treeview.

    Tags disponíveis:
    - status_novo_cliente: Verde (Novo Cliente)
    - status_sem_resposta: Laranja/Amarelo (Sem resposta)
    - status_analise: Azul (Análise da Caixa, Análise do Ministério)
    - status_aguardando: Cinza (Aguardando documento/pagamento)
    - status_finalizado: Verde (Finalizado)
    - status_followup: Roxo (Follow-up hoje/amanhã)
    - zebra_even: Linha par (branco)
    - zebra_odd: Linha ímpar (cinza claro)
    """
    try:
        modern_font = _get_modern_font()
        bold_font = modern_font.copy()
        bold_font.configure(weight="bold")

        # Tags de status com cores visuais (badges dinâmicos)
        tree.tag_configure(
            "status_novo_cliente",
            background=STATUS_NOVO_CLIENTE_BG,
            foreground=STATUS_NOVO_CLIENTE_FG,
            font=bold_font,
        )

        tree.tag_configure(
            "status_sem_resposta",
            background=STATUS_SEM_RESPOSTA_BG,
            foreground=STATUS_SEM_RESPOSTA_FG,
        )

        tree.tag_configure(
            "status_analise",
            background=STATUS_ANALISE_BG,
            foreground=STATUS_ANALISE_FG,
        )

        tree.tag_configure(
            "status_aguardando",
            background=STATUS_AGUARDANDO_BG,
            foreground=STATUS_AGUARDANDO_FG,
        )

        tree.tag_configure(
            "status_finalizado",
            background=STATUS_FINALIZADO_BG,
            foreground=STATUS_FINALIZADO_FG,
        )

        tree.tag_configure(
            "status_followup",
            background=STATUS_FOLLOWUP_BG,
            foreground=STATUS_FOLLOWUP_FG,
            font=bold_font,
        )

        # Zebra striping para melhor legibilidade em linhas longas
        tree.tag_configure("zebra_even", background=ZEBRA_EVEN_BG)
        tree.tag_configure("zebra_odd", background=ZEBRA_ODD_BG)

        log.debug("Tags de status configuradas com sucesso")

    except Exception as exc:
        log.debug("Falha ao configurar tags de status: %s", exc)


def apply_zebra_striping(tree: tb.Treeview) -> None:
    """Aplica zebra striping (linhas alternadas) à Treeview.

    Deve ser chamado após inserir/remover itens da tabela.
    Preserva tags de status existentes.
    """
    try:
        children = tree.get_children()
        for idx, item in enumerate(children):
            current_tags = list(tree.item(item, "tags") or ())

            # Remove tags de zebra anteriores
            current_tags = [t for t in current_tags if t not in ("zebra_even", "zebra_odd")]

            # Adiciona tag de zebra baseado no índice
            zebra_tag = "zebra_even" if idx % 2 == 0 else "zebra_odd"

            # Tags de status têm prioridade sobre zebra (não adicionar zebra se tem status)
            has_status_tag = any(t.startswith("status_") for t in current_tags)
            if not has_status_tag:
                current_tags.append(zebra_tag)

            tree.item(item, tags=tuple(current_tags))

    except Exception as exc:
        log.debug("Falha ao aplicar zebra striping: %s", exc)


def get_status_tag(status_text: str | None) -> str | None:
    """Retorna a tag de status apropriada baseado no texto do status.

    Args:
        status_text: Texto do status do cliente

    Returns:
        Nome da tag de status ou None se não houver match
    """
    if not status_text:
        return None

    status_lower = status_text.lower().strip()

    # Mapeamento de status para tags
    if "novo cliente" in status_lower:
        return "status_novo_cliente"
    elif "sem resposta" in status_lower:
        return "status_sem_resposta"
    elif "análise" in status_lower or "analise" in status_lower:
        return "status_analise"
    elif "aguardando" in status_lower:
        return "status_aguardando"
    elif "finalizado" in status_lower:
        return "status_finalizado"
    elif "follow-up" in status_lower or "follow up" in status_lower:
        return "status_followup"

    return None


def create_clients_treeview(
    parent: tk.Misc,
    *,
    on_double_click: Callable[[Any], Any] | None,
    on_select: Callable[[Any], Any] | None,
    on_delete: Callable[[Any], Any] | None,
    on_click: Callable[[Any], Any] | None,
) -> tb.Treeview:
    """Create the main clients Treeview configured with column widths and bindings.

    Melhorias de UI v1.5.41:
    - Altura de linha aumentada (32px) para melhor legibilidade
    - Fonte moderna (Segoe UI 10pt)
    - Tags de status com cores dinâmicas
    - Suporte a zebra striping
    """
    columns = (
        ("ID", "ID", COL_ID_WIDTH, False),
        ("Razao Social", "Razão Social", COL_RAZAO_WIDTH, True),  # só esta estica
        ("CNPJ", "CNPJ", COL_CNPJ_WIDTH, False),
        ("Nome", "Nome", COL_NOME_WIDTH, False),
        ("WhatsApp", "WhatsApp", COL_WHATSAPP_WIDTH, False),  # col #5
        ("Observacoes", "Observações", COL_OBS_WIDTH, True),  # col #6
        ("Status", "Status", COL_STATUS_WIDTH, False),  # col #7 (NOVA)
        ("Ultima Alteracao", "Última Alteração", COL_ULTIMA_WIDTH, False),
    )

    tree = tb.Treeview(parent, columns=[c[0] for c in columns], show="headings")

    # =========================================================================
    # MODERNIZAÇÃO: Configurar altura de linha e fonte
    # =========================================================================
    try:
        style = tb.Style()
        modern_font = _get_modern_font()
        header_font = _get_header_font()

        # Configura estilo personalizado para a Treeview
        style.configure(
            "Treeview",
            rowheight=TREEVIEW_ROW_HEIGHT,
            font=modern_font,
        )

        # Configura estilo do cabeçalho
        style.configure(
            "Treeview.Heading",
            font=header_font,
        )

        log.debug(
            "Treeview modernizada: rowheight=%d, font=%s %d",
            TREEVIEW_ROW_HEIGHT,
            modern_font.actual()["family"],
            modern_font.actual()["size"],
        )

    except Exception as exc:
        log.debug("Falha ao configurar estilo moderno da Treeview: %s", exc)

    for key, heading, _, _ in columns:
        tree.heading(key, text=heading, anchor="center")

    for key, _, width, can_stretch in columns:
        tree.column(key, width=width, minwidth=width, anchor="center", stretch=can_stretch)

    def _block_header_resize(event: Any) -> str | None:
        if tree.identify_region(event.x, event.y) == "separator":
            return "break"
        return None

    tree.bind("<Button-1>", _block_header_resize, add="+")

    # =========================================================================
    # MODERNIZAÇÃO: Configurar tags de status e observações
    # =========================================================================
    try:
        modern_font = _get_modern_font()
        bold_font = modern_font.copy()
        bold_font.configure(weight="bold")
        tree.tag_configure("has_obs", font=bold_font, foreground=OBS_FG)
    except Exception as exc:
        log.debug("Falha ao configurar fonte em negrito: %s", exc)

    # Configurar tags de status dinâmico
    configure_status_tags(tree)

    if on_double_click:
        tree.bind("<Double-1>", on_double_click, add="+")
    if on_select:
        tree.bind("<<TreeviewSelect>>", on_select, add="+")
    if on_delete:
        tree.bind("<Delete>", on_delete, add="+")
    if on_click:
        tree.bind("<ButtonRelease-1>", on_click, add="+")

    def _on_motion_hand_cursor(event: Any) -> None:
        try:
            col = tree.identify_column(event.x)
            tree.configure(cursor="hand2" if col in ("#5",) else "")
        except Exception:
            tree.configure(cursor="")

    tree.bind("<Motion>", _on_motion_hand_cursor, add="+")
    tree.bind("<Leave>", lambda _e: tree.configure(cursor=""), add="+")

    return tree
