# -*- coding: utf-8 -*-
"""CTkTableView - Wrapper para CTkTable com API compatível com Treeview.

MICROFASE 27/28: Substitui Treeview legado por CustomTkinter (via CTkTable).
Fornece API completa para migração plug-in sem quebrar código existente.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

# CustomTkinter: fonte única centralizada (SSoT)
from src.ui.ctk_config import ctk

log = logging.getLogger(__name__)

# Import condicional de CTkTable
try:
    from CTkTable import CTkTable  # type: ignore[import-untyped]
except ImportError:
    class _CTkTableStub:
        """Stub que levanta erro quando CTkTable não está disponível."""
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise ImportError(
                "CTkTable não está instalado. Instale com: pip install CTkTable"
            )
    
    CTkTable = _CTkTableStub  # type: ignore[assignment, misc]


class CTkTableView(ctk.CTkFrame):
    """Tabela customizada usando CTkTable, compatível com API Treeview."""

    def __init__(
        self,
        master: Any,
        columns: Optional[list[str]] = None,
        show: str = "headings",
        height: int = 10,
        zebra: bool = False,
        zebra_colors: Optional[tuple[str, str]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, **kwargs)
        
        self._columns: list[str] = columns or []
        self._headers: list[str] = []
        self._rows: list[list[Any]] = []
        self._selected_row_idx: Optional[int] = None
        self._row_select_callback: Optional[Callable[[int], None]] = None
        self._double_click_callback: Optional[Callable[..., Any]] = None
        self._table: CTkTable | None = None
        self._height = height
        self._zebra = zebra
        self._zebra_colors = zebra_colors or ("#ffffff", "#f0f0f0")
        self._iid_to_index: dict[str, int] = {}
        self._next_iid = 0
        
        self._create_table()

    def _create_table(self) -> None:
        if self._table is not None:
            self._table.destroy()
        
        data = [self._headers] + self._rows if self._headers else [[]]
        
        try:
            # Configurar parâmetros base da tabela
            table_params = {
                "master": self,
                "values": data if data and data != [[]] else [["Sem dados"]],
                "row": len(data) if data and data != [[]] else 1,
                "column": len(self._headers) if self._headers else 1,
                "hover": True,
                "command": self._on_cell_click,
            }
            
            # Adicionar cores apenas se zebra estiver ativo e houver dados
            if self._zebra and len(data) > 1:
                zebra_colors = [self._zebra_colors[0], self._zebra_colors[1]] * ((len(data) // 2) + 1)
                zebra_colors = zebra_colors[:len(data)]
                table_params["colors"] = zebra_colors
            
            self._table = CTkTable(**table_params)
            self._table.pack(fill="both", expand=True)
        except Exception as e:
            log.error(f"Falha ao criar CTkTable: {e}")
            self._table = None

    def _on_cell_click(self, cell: dict[str, Any]) -> None:
        if not cell:
            return
        
        row_idx = cell.get("row", 0)
        if row_idx == 0:
            return
        
        data_idx = row_idx - 1
        if 0 <= data_idx < len(self._rows):
            self._selected_row_idx = data_idx
            if self._row_select_callback:
                try:
                    self._row_select_callback(data_idx)
                except Exception as e:
                    log.error(f"Erro em callback: {e}")

    def set_columns(self, headers: list[str]) -> None:
        self._headers = headers
        self._create_table()

    def set_rows(self, rows: list[list[Any]]) -> None:
        self._rows = rows
        self._selected_row_idx = None
        self._iid_to_index.clear()
        self._next_iid = 0
        self._create_table()

    def add_row(self, row: list[Any]) -> None:
        self._rows.append(row)
        self._create_table()

    def get_selected_row(self) -> Optional[list[Any]]:
        if self._selected_row_idx is None:
            return None
        if 0 <= self._selected_row_idx < len(self._rows):
            return self._rows[self._selected_row_idx]
        return None

    def get_selected_row_index(self) -> Optional[int]:
        return self._selected_row_idx

    def bind_row_select(self, callback: Callable[[int], None]) -> None:
        self._row_select_callback = callback

    def clear(self) -> None:
        self._rows = []
        self._selected_row_idx = None
        self._iid_to_index.clear()
        self._next_iid = 0
        self._create_table()

    def get_all_rows(self) -> list[list[Any]]:
        return self._rows.copy()

    def heading(self, column: str, text: str = "", **kwargs: Any) -> None:
        try:
            col_idx = self._columns.index(column)
            if col_idx < len(self._headers):
                self._headers[col_idx] = text
                self._create_table()
        except (ValueError, IndexError):
            log.debug(f"Coluna não encontrada: {column}")

    def column(self, column: str, width: int = 100, **kwargs: Any) -> None:
        pass

    def insert(
        self,
        parent: str,
        index: str | int,
        iid: Optional[str] = None,
        text: str = "",
        values: tuple[Any, ...] = (),
        tags: tuple[str, ...] = (),
        **kwargs: Any,
    ) -> str:
        if values:
            row = list(values)
            self._rows.append(row)
            
            if iid is None:
                iid = f"I{self._next_iid:03d}"
                self._next_iid += 1
            
            row_idx = len(self._rows) - 1
            self._iid_to_index[iid] = row_idx
            
            self._create_table()
            return iid
        return ""

    def delete(self, *items: str) -> None:
        if not items:
            return
        
        if "all" in items:
            self.clear()
            return
        
        indices_to_remove = set()
        for iid in items:
            if iid in self._iid_to_index:
                indices_to_remove.add(self._iid_to_index[iid])
        
        if indices_to_remove:
            for idx in sorted(indices_to_remove, reverse=True):
                if 0 <= idx < len(self._rows):
                    del self._rows[idx]
            self._iid_to_index.clear()
            self._next_iid = 0
            self._create_table()

    def selection(self) -> tuple[str, ...]:
        if self._selected_row_idx is not None:
            for iid, idx in self._iid_to_index.items():
                if idx == self._selected_row_idx:
                    return (iid,)
        return ()

    def item(self, item: str, option: Optional[str] = None, **kwargs: Any) -> dict[str, Any]:
        idx = self._iid_to_index.get(item)
        
        if idx is None:
            try:
                idx = int(item)
            except (ValueError, TypeError):
                return {"values": ()}
        
        if idx is not None and 0 <= idx < len(self._rows):
            return {"values": tuple(self._rows[idx])}
        
        return {"values": ()}

    def get_children(self, item: str = "") -> tuple[str, ...]:
        return tuple(self._iid_to_index.keys())

    def bind(self, sequence: str, callback: Callable[..., Any]) -> None:
        if sequence in ("<Double-Button-1>", "<Double-1>"):
            self._double_click_callback = callback
        elif sequence == "<<TreeviewSelect>>":
            self.bind_row_select(lambda idx: callback(None))

    def selection_set(self, iid: str) -> None:
        """Seleciona uma linha pelo iid."""
        idx = self._iid_to_index.get(iid)
        if idx is not None:
            self._selected_row_idx = idx

    def get_selected_iid(self) -> Optional[str]:
        """Retorna o iid da linha selecionada."""
        if self._selected_row_idx is not None:
            for iid, idx in self._iid_to_index.items():
                if idx == self._selected_row_idx:
                    return iid
        return None

    def yview(self, *args: Any) -> None:
        """Compatibilidade com scrollbar (no-op por enquanto)."""
        pass

    def xview(self, *args: Any) -> None:
        """Compatibilidade com scrollbar (no-op por enquanto)."""
        pass

    def set(self, item: str, column: str, value: Any) -> None:
        """Atualiza valor de uma célula específica."""
        idx = self._iid_to_index.get(item)
        if idx is not None and 0 <= idx < len(self._rows):
            try:
                col_idx = self._columns.index(column) if column in self._columns else int(column)
                if 0 <= col_idx < len(self._rows[idx]):
                    self._rows[idx][col_idx] = value
                    self._create_table()
            except (ValueError, IndexError):
                pass

    def index(self, item: str) -> int:
        """Retorna o índice de um item."""
        return self._iid_to_index.get(item, -1)

    def exists(self, item: str) -> bool:
        """Verifica se um iid existe."""
        return item in self._iid_to_index

    def focus(self, item: Optional[str] = None) -> str:
        """Define ou retorna o item com foco."""
        if item is not None:
            self.selection_set(item)
            return item
        iid = self.get_selected_iid()
        return iid if iid else ""

    def tag_configure(self, tagname: str, **kwargs: Any) -> None:
        """Compatibilidade com tags (no-op por enquanto)."""
        pass

    def tag_has(self, tagname: str, item: Optional[str] = None) -> bool | tuple[str, ...]:
        """Compatibilidade com tags."""
        if item is None:
            return ()
        return False


__all__ = ["CTkTableView"]
