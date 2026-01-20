"""CTkTreeView - Treeview hierárquico usando CustomTkinter.

MICROFASE 29: Widget personalizado para substituir Treeview legado em casos hierárquicos.
"""

from __future__ import annotations

import tkinter as tk
from typing import Any, Callable, Optional

from src.ui.ctk_config import ctk


class CTkTreeView(ctk.CTkScrollableFrame):
    """TreeView hierárquico usando CustomTkinter.
    
    API compatível com Treeview para casos básicos de hierarquia.
    """

    def __init__(
        self,
        master: Any,
        columns: tuple = (),
        show: str = "tree headings",
        selectmode: str = "browse",
        height: int = 10,
        **kwargs: Any,
    ):
        super().__init__(master, **kwargs)
        
        self._columns = columns
        self._show = show
        self._selectmode = selectmode
        self._height = height
        
        # Dados internos
        self._items: dict[str, dict] = {}  # iid -> item data
        self._children: dict[str, list[str]] = {"": []}  # parent_iid -> [child_iids]
        self._selection: list[str] = []
        self._headings: dict[str, str] = {}
        self._column_widths: dict[str, int] = {}
        
        # Callbacks
        self._select_callback: Optional[Callable] = None
        self._expand_callback: Optional[Callable] = None
        
        # Frame para headers
        if "headings" in self._show:
            self._header_frame = ctk.CTkFrame(self)
            self._header_frame.pack(fill="x", padx=5, pady=(5, 0))
        
    def heading(self, column: str, text: str = "", anchor: str = "w", command: Optional[Callable] = None) -> None:
        """Define cabeçalho de coluna."""
        self._headings[column] = text
        
    def column(self, column: str, width: int = 100, anchor: str = "w", stretch: bool = True, **kwargs: Any) -> None:
        """Define propriedades da coluna."""
        self._column_widths[column] = width
        
    def insert(
        self,
        parent: str,
        index: str | int,
        iid: Optional[str] = None,
        text: str = "",
        values: list | tuple = (),
        open: bool = False,
        tags: tuple = (),
    ) -> str:
        """Insere item na árvore."""
        if iid is None:
            iid = f"I{len(self._items):03d}"
            
        self._items[iid] = {
            "text": text,
            "values": list(values) if values else [],
            "open": open,
            "tags": tags,
            "parent": parent,
        }
        
        if parent not in self._children:
            self._children[parent] = []
        self._children[parent].append(iid)
        
        return iid
    
    def delete(self, *items: str) -> None:
        """Remove itens da árvore."""
        for iid in items:
            if iid in self._items:
                # Remover filhos recursivamente
                if iid in self._children:
                    for child in self._children[iid][:]:
                        self.delete(child)
                    del self._children[iid]
                
                # Remover da lista de filhos do pai
                parent = self._items[iid]["parent"]
                if parent in self._children and iid in self._children[parent]:
                    self._children[parent].remove(iid)
                
                del self._items[iid]
    
    def clear(self) -> None:
        """Limpa todos os itens."""
        self._items.clear()
        self._children = {"": []}
        self._selection.clear()
        
    def get_children(self, iid: str = "") -> tuple:
        """Retorna filhos de um item."""
        return tuple(self._children.get(iid, []))
    
    def item(self, iid: str, option: Optional[str] = None, **kwargs: Any) -> Any:
        """Get/set propriedades do item."""
        if iid not in self._items:
            return {}
            
        if option:
            return self._items[iid].get(option)
        if kwargs:
            self._items[iid].update(kwargs)
            return None
        return self._items[iid]
    
    def selection(self) -> tuple:
        """Retorna itens selecionados."""
        return tuple(self._selection)
    
    def selection_set(self, iid: str | list) -> None:
        """Define seleção."""
        if isinstance(iid, str):
            iid = [iid]
        self._selection = list(iid)
        if self._select_callback:
            self._select_callback()
    
    def get_selected_iid(self) -> Optional[str]:
        """Retorna primeiro item selecionado ou None."""
        return self._selection[0] if self._selection else None
    
    def focus(self, iid: Optional[str] = None) -> Optional[str]:
        """Get/set item com foco."""
        if iid is not None:
            self.selection_set(iid)
            return iid
        return self._selection[0] if self._selection else None
    
    def see(self, iid: str) -> None:
        """Scrolla para tornar item visível."""
        pass  # CTkScrollableFrame cuida automaticamente
    
    def exists(self, iid: str) -> bool:
        """Verifica se item existe."""
        return iid in self._items
    
    def bind(self, sequence: str, func: Callable, add: Optional[str] = None) -> None:
        """Bind de eventos."""
        if sequence == "<<TreeviewSelect>>":
            self._select_callback = lambda: func(None)
        else:
            super().bind(sequence, func, add)
    
    def unbind(self, sequence: str) -> None:
        """Remove bind."""
        if sequence == "<<TreeviewSelect>>":
            self._select_callback = None
        else:
            super().unbind(sequence)


__all__ = ["CTkTreeView"]
