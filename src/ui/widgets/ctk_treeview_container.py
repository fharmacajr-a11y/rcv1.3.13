# -*- coding: utf-8 -*-
"""CTkTreeviewContainer - Widget reutilizável CTk+ttk para tabelas.

FASE 3: Widget que combina CTkFrame com ttk.Treeview real + scrollbars.
Integrado com GlobalThemeManager para atualização automática de cores.

Uso:
    container = CTkTreeviewContainer(parent, columns=("col1", "col2"), rowheight=28)
    tree = container.get_treeview()
    tree.insert("", "end", values=("A", "B"))
"""

from __future__ import annotations

import logging
from tkinter import ttk
from typing import Any, Optional

from src.ui.ctk_config import ctk
from src.ui.ttk_treeview_theme import TreeColors, apply_treeview_theme, apply_zebra

log = logging.getLogger(__name__)

# Nome do style próprio para não afetar outros Treeviews
STYLE_NAME = "CTk.Treeview"


class CTkTreeviewContainer(ctk.CTkFrame):
    """Container CTkFrame que encapsula ttk.Treeview + scrollbars.

    Fornece um Treeview real com tema integrado ao sistema CTk.
    O style é isolado ("CTk.Treeview") para não afetar outros Treeviews.
    """

    def __init__(
        self,
        master: Any,
        columns: tuple[str, ...] = (),
        show: str = "headings",
        selectmode: str = "browse",
        height: int = 10,
        rowheight: int = 24,
        zebra: bool = True,
        style_name: str = STYLE_NAME,
        show_hscroll: bool = True,
        **kwargs: Any,
    ):
        """Inicializa o container com Treeview e scrollbars.

        Args:
            master: Widget pai
            columns: Tupla de nomes de colunas
            show: O que mostrar ("tree", "headings", "tree headings")
            selectmode: Modo de seleção ("browse", "extended", "none")
            height: Número de linhas visíveis
            rowheight: Altura de cada linha em pixels
            zebra: Se True, aplica zebra striping
            style_name: Nome base do style (default: "CTk.Treeview")
            show_hscroll: Se True, mostra scrollbar horizontal (default: True)
            **kwargs: Argumentos adicionais para CTkFrame
        """
        super().__init__(master, **kwargs)

        self._columns = columns
        self._show = show
        self._selectmode = selectmode
        self._height = height
        self._rowheight = rowheight
        self._zebra = zebra
        self._style_name = style_name
        self._show_hscroll = show_hscroll
        self._colors: Optional[TreeColors] = None

        # Aplicar tema inicial
        self._apply_initial_theme()

        # Criar Treeview
        self._tree = ttk.Treeview(
            self,
            columns=columns,
            show=show,
            selectmode=selectmode,
            height=height,
            style=f"{self._style_name}.Treeview",
        )

        # Scrollbar vertical usando CTkScrollbar (aparência consistente dark/light)
        self._vsb = ctk.CTkScrollbar(
            self,
            orientation="vertical",
            command=self._tree.yview,  # type: ignore[attr-defined]
        )
        self._tree.configure(yscrollcommand=self._vsb.set)

        # Scrollbar horizontal (opcional, baseado em show_hscroll)
        self._hsb: Optional[ctk.CTkScrollbar] = None
        if self._show_hscroll:
            self._hsb = ctk.CTkScrollbar(
                self,
                orientation="horizontal",
                command=self._tree.xview,  # type: ignore[attr-defined]
            )
            self._tree.configure(xscrollcommand=self._hsb.set)

        # Layout usando grid
        self._tree.grid(row=0, column=0, sticky="nsew")  # type: ignore[attr-defined]
        self._vsb.grid(row=0, column=1, sticky="ns")
        if self._hsb:
            self._hsb.grid(row=1, column=0, sticky="ew")

        # Configurar pesos do grid (métodos herdados de CTkFrame)
        self.grid_rowconfigure(0, weight=1)  # type: ignore[attr-defined]
        self.grid_columnconfigure(0, weight=1)  # type: ignore[attr-defined]

        # Registrar no TtkTreeviewManager para updates automáticos
        self._register_with_manager()

        # Desregistrar do manager quando o widget for destruído
        self._tree.bind("<Destroy>", self._on_tree_destroy)

        log.debug(f"[CTkTreeviewContainer] Criado: columns={columns}, rowheight={rowheight}")

    def _apply_initial_theme(self) -> None:
        """Aplica tema inicial baseado no modo atual do CTk."""
        try:
            mode = ctk.get_appearance_mode()
        except Exception:
            mode = "Light"

        self._apply_theme(mode)

    def _apply_theme(self, mode: str) -> None:
        """Aplica tema ttk.Style para o Treeview.

        Args:
            mode: "Light" ou "Dark"
        """
        try:
            full_style, colors = apply_treeview_theme(mode, self, self._style_name)
            self._colors = colors

            # Configurar rowheight customizado
            style = ttk.Style(self)  # type: ignore[attr-defined]
            style.configure(full_style, rowheight=self._rowheight)

            log.debug(f"[CTkTreeviewContainer] Tema aplicado: {mode}, rowheight={self._rowheight}")

        except Exception as exc:
            log.exception(f"[CTkTreeviewContainer] Erro ao aplicar tema: {exc}")

    def _register_with_manager(self) -> None:
        """Registra este Treeview no TtkTreeviewManager para updates automáticos."""
        try:
            from src.ui.ttk_treeview_manager import get_treeview_manager

            manager = get_treeview_manager()
            manager.register(
                tree=self._tree,
                master=self,
                style_name=self._style_name,
                zebra=self._zebra,
            )
            log.debug("[CTkTreeviewContainer] Registrado no TtkTreeviewManager")

        except Exception as exc:
            log.warning(f"[CTkTreeviewContainer] Não foi possível registrar no manager: {exc}")

    def _on_tree_destroy(self, event: Any = None) -> None:
        """Callback ao destruir o Treeview — remove do registry do manager."""
        try:
            from src.ui.ttk_treeview_manager import get_treeview_manager

            manager = get_treeview_manager()
            manager.unregister(self._tree)
            log.debug("[CTkTreeviewContainer] Desregistrado do TtkTreeviewManager")
        except Exception:
            pass  # Widget já destruído, silenciar

    def get_treeview(self) -> ttk.Treeview:
        """Retorna o ttk.Treeview encapsulado.

        Returns:
            Instância do ttk.Treeview interno
        """
        return self._tree

    def get_colors(self) -> Optional[TreeColors]:
        """Retorna as cores atuais do tema.

        Returns:
            TreeColors ou None se não aplicado
        """
        return self._colors

    def apply_zebra(self, parent_iid: str = "") -> None:
        """Aplica/reaplica zebra striping nas linhas.

        Chamar após inserir ou reordenar itens.

        Args:
            parent_iid: ID do item pai (vazio = raiz)
        """
        if self._colors is not None:
            apply_zebra(self._tree, self._colors, parent_iid)

    def configure_columns(
        self,
        column_widths: dict[str, int],
        column_anchors: Optional[dict[str, str]] = None,
        column_headings: Optional[dict[str, str]] = None,
    ) -> None:
        """Configura colunas do Treeview de forma conveniente.

        Args:
            column_widths: Dict {coluna: largura}
            column_anchors: Dict {coluna: anchor} (default: "w")
            column_headings: Dict {coluna: texto_heading}
        """
        column_anchors = column_anchors or {}
        column_headings = column_headings or {}

        for col in self._columns:
            width = column_widths.get(col, 100)
            anchor = column_anchors.get(col, "w")
            heading = column_headings.get(col, col)

            self._tree.column(col, width=width, anchor=anchor)
            self._tree.heading(col, text=heading, anchor=anchor)

    def clear(self) -> None:
        """Remove todos os itens do Treeview."""
        for item in self._tree.get_children():
            self._tree.delete(item)

    def insert(
        self,
        parent: str = "",
        index: str | int = "end",
        iid: Optional[str] = None,
        text: str = "",
        values: tuple[Any, ...] = (),
        open: bool = False,
        tags: tuple[str, ...] = (),
    ) -> str:
        """Wrapper para inserir item no Treeview.

        Args:
            parent: ID do item pai (vazio = raiz)
            index: Posição ("end", 0, etc.)
            iid: ID do item (opcional)
            text: Texto do item
            values: Valores das colunas
            open: Se True, expande item
            tags: Tags do item

        Returns:
            ID do item inserido
        """
        kwargs: dict[str, Any] = {
            "parent": parent,
            "index": index,
            "text": text,
            "values": values,
            "open": open,
            "tags": tags,
        }
        if iid is not None:
            kwargs["iid"] = iid

        item_id = self._tree.insert(**kwargs)

        # Reaplicar zebra se ativo
        if self._zebra and self._colors:
            apply_zebra(self._tree, self._colors, parent)

        return item_id


__all__ = ["CTkTreeviewContainer", "STYLE_NAME"]
