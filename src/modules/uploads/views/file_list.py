from __future__ import annotations

import tkinter as tk
from tkinter import ttk as _ttk
from typing import Callable, Iterable, Optional, Tuple, Any

# CustomTkinter (fonte centralizada)
from src.ui.ctk_config import ctk

# CTkTreeview para hierarquia de arquivos (vendorizado - MICROFASE 32)
from src.third_party.ctktreeview import CTkTreeview


class FileList(ctk.CTkFrame):  # type: ignore[misc]
    """Treeview que exibe arquivos em estrutura hierárquica e delega acoes para callbacks (CustomTkinter)."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        on_download: Optional[Callable[[], None]] = None,
        on_delete: Optional[Callable[[], None]] = None,
        on_open_file: Optional[Callable[[str, str, str], None]] = None,
        on_expand_folder: Optional[Callable[[str], list[dict]]] = None,
        on_download_folder: Optional[Callable[[], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self._on_download = on_download
        self._on_delete = on_delete
        self._on_open_file = on_open_file
        self._on_expand_folder = on_expand_folder
        self._on_download_folder = on_download_folder
        self._base_prefix = ""
        self._status_cache: dict[str, str] = {}
        self._item_data: dict[str, dict] = {}  # iid -> dados do item
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Estrutura de colunas para árvore hierárquica (CTkTreeview)
        # fg_color="transparent": frame interno herda SURFACE_DARK do wrapper pai
        self.tree = CTkTreeview(
            self, columns=("type",), show="tree headings", fg_color="transparent"
        )  # selectmode browse default

        # Headings
        self.tree.heading("#0", text="Nome do arquivo/pasta", anchor="w")
        self.tree.heading("type", text="Tipo", anchor="center")

        # Colunas
        self.tree.column("#0", minwidth=200, anchor="w", stretch=True)
        self.tree.column("type", width=90, minwidth=80, anchor="center", stretch=False)

        # Expandir frame interna do CTkTreeview: elimina área vazia à direita.
        # CTkTreeview cria self.frame = CTkFrame(master) sem configurar pesos,
        # o que impede o ttk.Treeview interno de esticar no eixo X.
        self.tree.frame.rowconfigure(0, weight=1)
        self.tree.frame.columnconfigure(0, weight=1)

        self.tree.grid(row=0, column=0, sticky="nsew")  # type: ignore[attr-defined]

        # SEM scrollbars redundantes: CTkTreeview já fornece barra vertical interna.
        # SEM scrollbar horizontal.

        # Estilo visual local — rowheight, fonte, cores, zebra
        self._apply_local_tree_style()

        # Ícones PIL de documento
        self._img_pdf, self._img_file = self._build_item_icons()

        self.tree.bind("<Delete>", lambda _event: self._handle_delete())
        self.tree.bind("<BackSpace>", lambda _event: self._handle_delete())
        self.tree.bind("<Return>", lambda _event: self._handle_download())
        self.tree.bind("<Double-Button-1>", self._on_double_click)
        self.tree.bind("<<TreeviewOpen>>", lambda _event: self._on_tree_open())

        # Travar redimensionamento de colunas
        self._lock_treeview_columns(self.tree)

        # Menu de contexto (clique direito)
        self._context_menu = tk.Menu(self, tearoff=0)
        self.tree.bind("<Button-3>", self._on_right_click)

    def _apply_local_tree_style(self) -> None:
        """Aplica estilo visual local na Treeview (rowheight, fonte, cores, zebra)."""
        try:
            mode = ctk.get_appearance_mode()
        except Exception:
            mode = "Light"

        try:
            from src.ui.ttk_treeview_theme import get_tree_colors

            colors = get_tree_colors(mode)
        except Exception:
            return

        _style = "V2Files.Treeview"
        style = _ttk.Style(self)
        # NÃO chamar style.theme_use() — o processo já está em "clam"
        style.configure(
            _style,
            background=colors.bg,
            fieldbackground=colors.field_bg,
            foreground=colors.fg,
            font=("Segoe UI", 10),
            rowheight=28,
            borderwidth=0,
            relief="flat",
        )
        style.configure(
            f"{_style}.Heading",
            background=colors.heading_bg,
            foreground=colors.heading_fg,
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            borderwidth=0,
            padding=(8, 4),
        )
        style.map(
            f"{_style}.Heading",
            background=[("active", colors.heading_bg), ("pressed", colors.heading_bg)],
            foreground=[("active", colors.heading_fg), ("pressed", colors.heading_fg)],
        )
        style.map(
            _style,
            background=[("selected", colors.sel_bg)],
            foreground=[("selected", colors.sel_fg)],
        )
        # Atribuir estilo ao ttk.Treeview via super().configure (bypassa CTkTreeview)
        _ttk.Treeview.configure(self.tree, style=_style)

        # Tags zebra
        self.tree.tag_configure("even", background=colors.even_bg, foreground=colors.fg)
        self.tree.tag_configure("odd", background=colors.odd_bg, foreground=colors.fg)

    def _build_item_icons(self):
        """Constrói ícones PIL para tipos de documento (PDF vermelho, genérico cinza)."""
        try:
            from PIL import Image, ImageDraw
            from PIL.ImageTk import PhotoImage as _ItkPhoto

            def _doc_icon(page_rgba, border_rgba):
                w, h, fold = 14, 16, 4
                img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
                d = ImageDraw.Draw(img)
                body = [(0, 0), (w - 1 - fold, 0), (w - 1, fold), (w - 1, h - 1), (0, h - 1)]
                d.polygon(body, fill=page_rgba, outline=border_rgba)
                d.polygon([(w - 1 - fold, 0), (w - 1, fold), (w - 1 - fold, fold)], fill=border_rgba)
                return _ItkPhoto(img)

            img_pdf = _doc_icon((220, 53, 69, 255), (150, 20, 40, 255))  # vermelho — PDF
            img_file = _doc_icon((180, 180, 190, 255), (110, 110, 120, 255))  # cinza — arquivo
            return img_pdf, img_file

        except Exception:  # noqa: BLE001
            # Fallback: pixel transparente para não quebrar o kwarg image=
            img_pdf = tk.PhotoImage(width=1, height=1)
            img_file = tk.PhotoImage(width=1, height=1)
            return img_pdf, img_file

    @staticmethod
    def _lock_treeview_columns(tree: Any) -> None:
        """Trava redimensionamento e arrasto de colunas da Treeview.

        Args:
            tree: CTkTreeview para travar colunas
        """

        # Bloquear resize manual via separator
        def block_separator(event: Any) -> str:
            if tree.identify_region(event.x, event.y) == "separator":
                return "break"
            return ""

        # Bloquear cursor de resize
        def block_resize_cursor(event: Any) -> str:
            if tree.identify_region(event.x, event.y) == "separator":
                tree.config(cursor="arrow")
                return "break"
            tree.config(cursor="")
            return ""

        tree.bind("<Button-1>", block_separator)
        tree.bind("<B1-Motion>", block_separator)
        tree.bind("<Motion>", block_resize_cursor)

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

        for idx, entry in enumerate(items):
            name = entry.get("name") or ""
            if not name:
                continue

            # Nome para exibição (last component do path)
            display_name = name.rsplit("/", 1)[-1] if "/" in name else name

            # Ocultar arquivos de marcação (.keep)
            if display_name == ".keep":
                continue

            is_folder = bool(entry.get("is_folder", False))

            # Tipo (Pasta, PDF, Imagem, Word, Excel, Arquivo)
            if is_folder:
                tipo = "Pasta"
            elif display_name.lower().endswith(".pdf"):
                tipo = "PDF"
            elif display_name.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp")):
                tipo = "Imagem"
            elif display_name.lower().endswith((".doc", ".docx")):
                tipo = "Word"
            elif display_name.lower().endswith((".xls", ".xlsx", ".csv")):
                tipo = "Excel"
            else:
                tipo = "Arquivo"

            # Zebra
            tag = "even" if idx % 2 == 0 else "odd"

            # Inserir o item na raiz
            if is_folder:
                iid = self.tree.insert("", "end", text=f"📁 {display_name}", values=(tipo,), open=False, tags=(tag,))
            else:
                _img = self._img_pdf if tipo == "PDF" else self._img_file
                iid = self.tree.insert(
                    "", "end", text=f"  {display_name}", image=_img, values=(tipo,), open=False, tags=(tag,)
                )

            # Guardar dados do item (full path, tipo)
            full_path = entry.get("full_path") or name
            self._item_data[iid] = {
                "name": display_name,
                "full_path": full_path,
                "is_folder": is_folder,
                "tipo": tipo,
                "populated": False,  # Controla se já carregou filhos
            }

            # Para pastas, inserir placeholder para mostrar o "+"
            if is_folder:
                self.tree.insert(iid, "end", text="", values=("",), tags=("placeholder",))

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
        focused = self.tree.focus()  # type: ignore[attr-defined]
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
        for idx, entry in enumerate(child_items):
            name = entry.get("name") or ""
            if not name:
                continue

            display_name = name.rsplit("/", 1)[-1] if "/" in name else name

            # Ocultar arquivos de marcação (.keep)
            if display_name == ".keep":
                continue

            is_folder = bool(entry.get("is_folder", False))

            # Tipo (Pasta, PDF, Imagem, Word, Excel, Arquivo)
            if is_folder:
                tipo = "Pasta"
            elif display_name.lower().endswith(".pdf"):
                tipo = "PDF"
            elif display_name.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp")):
                tipo = "Imagem"
            elif display_name.lower().endswith((".doc", ".docx")):
                tipo = "Word"
            elif display_name.lower().endswith((".xls", ".xlsx", ".csv")):
                tipo = "Excel"
            else:
                tipo = "Arquivo"

            # Zebra
            tag = "even" if idx % 2 == 0 else "odd"

            # Inserir filho
            if is_folder:
                child_iid = self.tree.insert(
                    folder_iid, "end", text=f"📁 {display_name}", values=(tipo,), open=False, tags=(tag,)
                )
            else:
                _img = self._img_pdf if tipo == "PDF" else self._img_file
                child_iid = self.tree.insert(
                    folder_iid, "end", text=f"  {display_name}", image=_img, values=(tipo,), open=False, tags=(tag,)
                )

            # Guardar dados
            child_full_path = entry.get("full_path") or name
            self._item_data[child_iid] = {
                "name": display_name,
                "full_path": child_full_path,
                "is_folder": is_folder,
                "tipo": tipo,
                "populated": False,
            }

            # Adicionar placeholder em subpastas
            if is_folder:
                self.tree.insert(child_iid, "end", text="", values=("",), tags=("placeholder",))

        # Marcar como populado
        item_info["populated"] = True

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
            tipo = saved_data.get("tipo", "Pasta" if saved_data["is_folder"] else "Arquivo")
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
        item_id = self.tree.focus()  # type: ignore[attr-defined]
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

    def _on_right_click(self, event) -> None:
        """Handler para clique direito - mostra menu de contexto."""
        # Identificar o item sob o cursor
        iid = self.tree.identify_row(event.y)  # type: ignore[attr-defined]
        if not iid:
            return

        # Selecionar o item clicado
        self.tree.selection_set(iid)  # type: ignore[attr-defined]

        # Obter informações do item
        info = self.get_selected_info()
        if not info:
            return

        _, item_type, _ = info
        is_folder = item_type == "Pasta"

        # Limpar e reconstruir menu dinamicamente
        self._context_menu.delete(0, "end")

        if is_folder:
            # Menu para pasta
            if self._on_download_folder:
                self._context_menu.add_command(label="Baixar pasta (.zip)", command=self._on_download_folder)
            if self._on_delete:
                self._context_menu.add_command(label="Excluir", command=self._on_delete)
        else:
            # Menu para arquivo
            if self._on_open_file:
                self._context_menu.add_command(label="Visualizar", command=lambda: self._trigger_open_file())
            if self._on_download:
                self._context_menu.add_command(label="Baixar", command=self._on_download)
            if self._on_delete:
                self._context_menu.add_command(label="Excluir", command=self._on_delete)

        # Mostrar menu
        try:
            self._context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self._context_menu.grab_release()

    def _trigger_open_file(self) -> None:
        """Dispara o callback de abrir arquivo com os parâmetros corretos."""
        info = self.get_selected_info()
        if info and self._on_open_file:
            name, item_type, full_path = info
            self._on_open_file(name, item_type, full_path)
