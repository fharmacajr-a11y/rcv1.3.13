from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Iterable, Optional, Tuple


class FileList(ttk.Frame):
    """Treeview que exibe arquivos em estrutura hierárquica e delega acoes para callbacks."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        on_download: Optional[Callable[[], None]] = None,
        on_delete: Optional[Callable[[], None]] = None,
        on_open_file: Optional[Callable[[str, str, str], None]] = None,
        on_expand_folder: Optional[Callable[[str], list[dict]]] = None,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self._on_download = on_download
        self._on_delete = on_delete
        self._on_open_file = on_open_file
        self._on_expand_folder = on_expand_folder
        self._base_prefix = ""
        self._status_cache: dict[str, str] = {}
        self._item_data: dict[str, dict] = {}  # iid -> dados do item
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Estrutura de colunas para árvore hierárquica
        self.tree = ttk.Treeview(
            self, columns=("type", "size", "modified", "status"), show="tree headings", selectmode="browse"
        )

        # Configuração dos headings
        self.tree.heading("#0", text="Nome do arquivo/pasta", anchor="w")
        self.tree.heading("type", text="Tipo", anchor="center")
        self.tree.heading("size", text="Tamanho", anchor="e")
        self.tree.heading("modified", text="Modificado", anchor="center")
        self.tree.heading("status", text="Status", anchor="center")

        # Configuração das colunas
        self.tree.column("#0", width=400, anchor="w", stretch=True)
        self.tree.column("type", width=100, anchor="center", stretch=False)
        self.tree.column("size", width=100, anchor="e", stretch=False)
        self.tree.column("modified", width=160, anchor="center", stretch=False)
        self.tree.column("status", width=80, anchor="center", stretch=False)

        # Garantir que todas as colunas sejam visíveis
        self.tree["displaycolumns"] = ("type", "size", "modified", "status")

        self.tree.grid(row=0, column=0, sticky="nsew")

        # Scrollbars vertical e horizontal
        scroll_y = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        scroll_y.grid(row=0, column=1, sticky="ns")

        scroll_x = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        scroll_x.grid(row=1, column=0, sticky="ew")

        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.tree.bind("<Delete>", lambda _event: self._handle_delete())
        self.tree.bind("<BackSpace>", lambda _event: self._handle_delete())
        self.tree.bind("<Return>", lambda _event: self._handle_download())
        self.tree.bind("<Double-Button-1>", self._on_double_click)
        self.tree.bind("<<TreeviewOpen>>", lambda _event: self._on_tree_open())

    def populate_tree_hierarchical(self, items: Iterable[dict], base_prefix: str, status_cache: dict[str, str]) -> None:
        """Popula a treeview com primeiro nível (lazy loading).

        Args:
            items: Lista de itens do storage (com 'name', 'is_folder', 'size', etc.)
            base_prefix: Prefixo base do cliente (para construir paths relativos)
            status_cache: Cache de status de pastas
        """
        self.tree.delete(*self.tree.get_children(""))
        self._base_prefix = base_prefix
        self._status_cache = status_cache
        self._item_data = {}

        for entry in items:
            name = entry.get("name") or ""
            if not name:
                continue

            # Nome para exibição (última parte do path)
            display_name = name.rsplit("/", 1)[-1] if "/" in name else name
            is_folder = bool(entry.get("is_folder", False))

            # Tipo
            tipo = "Pasta" if is_folder else "Arquivo"

            # Tamanho (apenas para arquivos)
            size_display = ""
            if not is_folder:
                size_raw = entry.get("size") or entry.get("Size") or 0
                size_display = self._format_size(size_raw)

            # Data de modificação
            modified = ""
            if not is_folder:
                modified = entry.get("updated_at") or entry.get("LastModified") or ""

            # Status (para pastas)
            status = ""
            if is_folder:
                # Construir full path para buscar status
                full_path = entry.get("full_path") or name
                status = status_cache.get(full_path, "")

            # Inserir o item na raiz
            iid = self.tree.insert(
                "", "end", text=display_name, values=(tipo, size_display, modified, status), open=False
            )

            # Guardar dados do item (full path, tipo)
            full_path = entry.get("full_path") or name
            self._item_data[iid] = {
                "name": display_name,
                "full_path": full_path,
                "is_folder": is_folder,
                "populated": False,  # Controla se já carregou filhos
            }

            # Para pastas, inserir placeholder para mostrar o "+"
            if is_folder:
                self.tree.insert(iid, "end", text="", values=("", "", "", ""), tags=("placeholder",))

    def _format_size(self, size_bytes) -> str:
        """Formata o tamanho do arquivo de forma legível."""
        try:
            size = int(size_bytes or 0)
        except (ValueError, TypeError):
            return ""

        if size == 0:
            return ""
        elif size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.2f} GB"

    def _on_tree_open(self) -> None:
        """Evento disparado ao expandir pasta - carrega filhos sob demanda."""
        focused = self.tree.focus()
        if focused:
            self._populate_folder(focused)

    def _populate_folder(self, folder_iid: str) -> None:
        """Popula os filhos de uma pasta se ainda não foram carregados."""
        # Verificar se é pasta e se ainda não foi populada
        item_info = self._item_data.get(folder_iid)
        if not item_info or not item_info["is_folder"] or item_info["populated"]:
            return

        # Remover placeholder
        children = self.tree.get_children(folder_iid)
        for child in children:
            if "placeholder" in self.tree.item(child, "tags"):
                self.tree.delete(child)

        # Chamar callback para buscar filhos
        if not self._on_expand_folder:
            return

        full_path = item_info["full_path"]
        child_items = self._on_expand_folder(full_path)

        # Inserir filhos
        for entry in child_items:
            name = entry.get("name") or ""
            if not name:
                continue

            display_name = name.rsplit("/", 1)[-1] if "/" in name else name
            is_folder = bool(entry.get("is_folder", False))

            tipo = "Pasta" if is_folder else "Arquivo"

            size_display = ""
            if not is_folder:
                size_raw = entry.get("size") or entry.get("Size") or 0
                size_display = self._format_size(size_raw)

            modified = ""
            if not is_folder:
                modified = entry.get("updated_at") or entry.get("LastModified") or ""

            status = ""
            if is_folder:
                child_full_path = entry.get("full_path") or name
                status = self._status_cache.get(child_full_path, "")

            # Inserir filho
            child_iid = self.tree.insert(
                folder_iid, "end", text=display_name, values=(tipo, size_display, modified, status), open=False
            )

            # Guardar dados
            child_full_path = entry.get("full_path") or name
            self._item_data[child_iid] = {
                "name": display_name,
                "full_path": child_full_path,
                "is_folder": is_folder,
                "populated": False,
            }

            # Adicionar placeholder em subpastas
            if is_folder:
                self.tree.insert(child_iid, "end", text="", values=("", "", "", ""), tags=("placeholder",))

        # Marcar como populado
        item_info["populated"] = True

    def selected_item(self) -> Optional[str]:
        """Retorna o nome do item selecionado."""
        selection = self.tree.selection()
        if not selection:
            return None
        return self.tree.item(selection[0], "text")

    def get_selected_info(self) -> Optional[Tuple[str, str, str]]:
        """Retorna (nome, tipo, full_path) do item selecionado."""
        selection = self.tree.selection()
        if not selection:
            return None

        iid = selection[0]
        # Buscar dados salvos
        saved_data = self._item_data.get(iid)
        if saved_data:
            name = saved_data["name"]
            tipo = "Pasta" if saved_data["is_folder"] else "Arquivo"
            full_path = saved_data["full_path"]
        else:
            # Fallback: extrair da tree
            item_data = self.tree.item(iid)
            name = item_data.get("text", "")
            values = item_data.get("values", [])
            tipo = values[0] if values else ""
            full_path = name

        return (name, tipo, full_path)

    def _on_double_click(self, event) -> str:
        """Handler de duplo clique que retorna 'break' para impedir comportamento padrão."""
        self.handle_double_click()
        return "break"

    def handle_double_click(self) -> None:
        """Duplo clique: pasta => expandir/fechar, arquivo => callback de abrir."""
        info = self.get_selected_info()
        if not info:
            return

        name, item_type, full_path = info
        item_id = self.tree.focus()
        if not item_id:
            return

        # Pasta => abre/fecha e carrega filhos se necessário
        if item_type.lower() == "pasta":
            is_open = bool(self.tree.item(item_id, "open"))

            # Se estava fechado e vai abrir, garantir que carrega filhos
            if not is_open:
                # Verificar se precisa popular
                item_info = self._item_data.get(item_id)
                if item_info and not item_info["populated"]:
                    # Carregar filhos antes de abrir
                    self._populate_folder(item_id)

            # Alternar estado aberto/fechado
            self.tree.item(item_id, open=not is_open)
            return

        # Arquivo => dispara callback (viewer) se existir
        if self._on_open_file is not None:
            self._on_open_file(name, item_type, full_path)

    def clear(self) -> None:
        self.tree.delete(*self.tree.get_children(""))

    def _handle_download(self) -> None:
        if self._on_download:
            self._on_download()

    def _handle_delete(self) -> None:
        if self._on_delete:
            self._on_delete()
