# -*- coding: utf-8 -*-
"""
File Browser - Navegador de arquivos do Supabase Storage.

Este módulo implementa a interface de navegação de arquivos/pastas no bucket
do Supabase Storage. A arquitetura é baseada em uma função principal
(open_files_browser) que retorna uma janela Toplevel do Tkinter.

ESTRUTURA INTERNA (blocos lógicos):
═══════════════════════════════════

1. UI CONSTRUCTION (linhas ~140-400)
   - Criação da janela Toplevel e frames
   - Configuração do Treeview para listagem
   - Botões de ação (upload, download, delete, preview)
   - Barra de navegação e path label

2. LISTING & PAGINATION (linhas ~750-1010)
   - _fetch_children: busca lista de arquivos/pastas do Supabase
   - _populate_tree_async: carregamento assíncrono via ThreadPoolExecutor
   - _insert_children_page: paginação por blocos de 200 itens (PERF-003)
   - _load_next_page: botão "Carregar mais"
   - _update_load_more_button_state: controle de visibilidade do botão

3. FILE ACTIONS (linhas ~1140-1500)
   - Download: individual e em lote (.zip)
   - Upload: arquivos e pastas
   - Delete: arquivos, pastas e recursivo
   - Preview: PDF viewer integration
   - Rename/Move: operações de arquivo

4. TREE UTILITIES (linhas ~770-850)
   - _insert_row: inserção de linhas na Treeview
   - _get_rel_path: cálculo de caminho relativo
   - _is_folder_item: verificação de tipo
   - Helpers de navegação e seleção

5. STATUS & PREFERENCES (linhas ~400-610)
   - Sistema de status de pastas (neutral/ready/notready)
   - Persistência de estado entre sessões
   - Integração com prefs.py

PERFORMANCE:
───────────
- FUNC-001: Fetch assíncrono via ThreadPoolExecutor (não bloqueia GUI)
- PERF-002: Downloads individuais em threads
- PERF-003: Lazy loading/paginação para listas grandes (>200 itens)

TESTING:
────────
- Cobertura: ~2% direto (parte de UI não testada unit)
- Integração: testado via test_ui_components.py
- Smoke tests manuais em docs/scripts/

REFACTORING NOTES:
─────────────────
Este arquivo é mantido como monólito por razões históricas e práticas:
- Closures aninhadas compartilham estado (window, tree, buttons)
- Refatoração em classes/módulos requer mudança arquitetural maior
- Prioridade atual: estabilidade > modularidade excessiva
- Documentação interna compensa a falta de separação física

TODO (futuro):
- Converter em classe FileBrowserWindow com métodos
- Extrair ações em ActionHandler separado
- Separar lógica de paginação em PaginationManager
"""

import logging
import os
import threading
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path, PurePosixPath
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable, Dict, Optional, Tuple

from src.modules.pdf_preview import open_pdf_viewer
from src.modules.uploads import service as uploads_service
from src.modules.uploads.components.helpers import (
    client_prefix_for_id,
    format_cnpj_for_display,
    get_clients_bucket,
    strip_cnpj_from_razao,
)
from src.utils.prefs import (
    load_browser_status_map,
    load_last_prefix,
    save_browser_status_map,
    save_last_prefix,
)
from src.utils.resource_path import resource_path  # evita ciclo com app_gui

# Imports internos do pacote files_browser
from .constants import (
    DEFAULT_PAGE_SIZE,
    EMPTY_TAG,
    FOLDER_STATUS_NEUTRAL,
    FOLDER_STATUS_NOTREADY,
    FOLDER_STATUS_READY,
    PLACEHOLDER_TAG,
    STATUS_GLYPHS,
    UI_GAP,
    UI_PADX,
    UI_PADY,
)
from .utils import format_file_size, sanitize_filename, suggest_zip_filename


_executor = ThreadPoolExecutor(max_workers=4)
_log = logging.getLogger(__name__)

WindowKey = Tuple[str, str]
_OPEN_WINDOWS: Dict[WindowKey, tk.Toplevel] = {}


def open_files_browser(
    parent,
    *,
    org_id: str,
    client_id: int,
    razao: str = "",
    cnpj: str = "",
    supabase=None,  # type: ignore[no-untyped-def]
    start_prefix: str = "",
    module: str = "",
    delete_folder_handler: Callable[[str, str], None] | None = None,
) -> tk.Toplevel:
    """
    Abre uma janela para navegar/baixar arquivos do Storage.

    Args:
        parent: Widget pai
        org_id: ID da organizaÃ§Ã£o
        client_id: ID do cliente
        razao: RazÃ£o social do cliente (opcional)
        cnpj: CNPJ do cliente (opcional)
        supabase: Cliente Supabase (opcional)
        start_prefix: Prefixo inicial opcional (ex: "{org_id}/{client_id}/GERAL/Auditoria")
                     Se fornecido, substitui o root_prefix padrÃ£o
        module: Nome do mÃ³dulo que estÃ¡ abrindo o browser (ex: "auditoria")

    Returns:
        Janela Toplevel criada
    """
    window_key: WindowKey = (str(org_id or ""), str(client_id))
    existing = _OPEN_WINDOWS.get(window_key)
    if existing is not None:
        try:
            exists = bool(existing.winfo_exists())
        except Exception:
            exists = False
        if exists:
            try:
                existing.deiconify()
                existing.lift()
                existing.focus_force()
            except Exception:
                _log.debug("Falha ao restaurar janela existente")
            if start_prefix:
                navigate_fn = getattr(existing, "_navigate_to_prefix", None)
                if callable(navigate_fn):
                    try:
                        navigate_fn(start_prefix.strip("/"))
                    except Exception:
                        _log.debug("Falha ao navegar para prefixo %s", start_prefix)
            return existing
        _OPEN_WINDOWS.pop(window_key, None)

    BUCKET = get_clients_bucket()
    is_auditoria_context = module == "auditoria"
    show_nav_buttons = is_auditoria_context
    enable_status_column = is_auditoria_context
    browser_key = f"org:{org_id}|client:{client_id}|module:{module or 'clientes'}"

    client_root = client_prefix_for_id(client_id, org_id)
    default_prefix = client_root
    if start_prefix:
        root_prefix = start_prefix.strip("/")
    else:
        remembered = load_last_prefix(browser_key) if module else None
        if remembered and module:
            root_prefix = remembered.strip("/")
        else:
            root_prefix = default_prefix

    if not root_prefix:
        root_prefix = default_prefix

    # TÃ­tulo padronizado com CNPJ formatado e razÃ£o limpa
    razao_clean = strip_cnpj_from_razao(razao, cnpj)
    cnpj_fmt = format_cnpj_for_display(cnpj)
    docs_window = tk.Toplevel(parent)
    docs_window._is_closing = False  # type: ignore[attr-defined]
    docs_window._window_key = window_key  # type: ignore[attr-defined]
    _OPEN_WINDOWS[window_key] = docs_window
    _original_destroy = docs_window.destroy

    status_cache = load_browser_status_map(browser_key) if enable_status_column else {}

    def _safe_after(ms: int, fn) -> None:
        try:
            if getattr(docs_window, "_is_closing", False):
                return
            if docs_window.winfo_exists():
                docs_window.after(ms, fn)
        except Exception:
            _log.debug("Falha ao agendar after em docs_window")

    if is_auditoria_context:
        title = f"Arquivos: {razao_clean} – {cnpj_fmt} – ID {client_id}"
    else:
        title = f"Arquivos: ID {client_id} – {razao_clean} – {cnpj_fmt}"
    docs_window.title(title)
    try:
        docs_window.iconbitmap(resource_path("rc.ico"))
    except Exception:
        _log.debug("Falha ao configurar ícone da janela")

    # Guardar raiz e prefixo atual para navegaÃ§Ã£o
    docs_window._org_id = org_id  # type: ignore[attr-defined]
    docs_window._client_id = client_id  # type: ignore[attr-defined]
    docs_window._browser_key = browser_key  # type: ignore[attr-defined]
    docs_window._base_root = client_root  # type: ignore[attr-defined]
    # Se start_prefix passado, respeita; senÃ£o comeÃ§a na raiz do cliente
    docs_window._current_prefix = root_prefix  # type: ignore[attr-defined]
    docs_window._root_remote = docs_window._base_root  # type: ignore[attr-defined]
    docs_window._current_root = docs_window._current_prefix  # type: ignore[attr-defined]
    docs_window._zip_cancel_evt = threading.Event()  # type: ignore[attr-defined]
    docs_window._folder_status = dict(status_cache) if enable_status_column else {}  # type: ignore[attr-defined]
    docs_window._preview_in_progress = False  # type: ignore[attr-defined]
    # Atributos para paginação de listagem
    docs_window._children_all = []  # type: ignore[attr-defined]
    docs_window._children_page_size = DEFAULT_PAGE_SIZE  # type: ignore[attr-defined]
    docs_window._children_offset = 0  # type: ignore[attr-defined]
    docs_window._current_parent_iid = ""  # type: ignore[attr-defined]
    docs_window._current_parent_prefix = ""  # type: ignore[attr-defined]

    # Helpers
    def _center_on_parent(
        win: tk.Toplevel,
        parent_win: tk.Misc,
        width: int | None = None,
        height: int | None = None,
    ):
        win.update_idletasks()
        pw, ph = parent_win.winfo_width(), parent_win.winfo_height()
        px, py = parent_win.winfo_rootx(), parent_win.winfo_rooty()
        w = width or max(1, win.winfo_width())
        h = height or max(1, win.winfo_height())
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
        win.geometry(f"{w}x{h}+{x}+{y}")

    # Centraliza a janela com tamanho maior
    _center_on_parent(docs_window, parent, width=980, height=620)

    # ConfiguraÃ§Ã£o de grid para layout estÃ¡vel
    docs_window.minsize(980, 620)
    docs_window.columnconfigure(0, weight=1)
    docs_window.rowconfigure(1, weight=1)  # linha da Treeview/scroll

    header = ttk.Frame(docs_window)
    header.grid(row=0, column=0, sticky="ew")
    header.columnconfigure(0, weight=1)

    # --- NAV BAR (setas + caminho) ---
    nav = ttk.Frame(header, padding=(UI_PADX, UI_PADY, UI_PADX, 0))
    nav.grid(row=0, column=0, sticky="ew")

    # Setas de navegaÃ§Ã£o (apenas para Auditoria, clientes usam double-click)
    btn_prev: ttk.Button | None = None
    btn_next: ttk.Button | None = None
    if show_nav_buttons:
        btn_prev = ttk.Button(nav, text="←", width=3)
        btn_next = ttk.Button(nav, text="→", width=3)

    # Label do caminho
    path_var = tk.StringVar()

    def _sync_path_label():
        path_var.set(f"Supabase: {BUCKET}/{docs_window._current_prefix}")  # type: ignore[attr-defined]

    path_lbl = ttk.Label(nav, textvariable=path_var, foreground="#7a7a7a")

    if show_nav_buttons and btn_prev and btn_next:
        btn_prev.pack(side="left", padx=(0, UI_GAP))
        btn_next.pack(side="left", padx=(0, UI_GAP))
    path_lbl.pack(side="left", padx=(0, UI_GAP))

    def _set_prefix(prefix: str):
        """Define o prefixo atual e recarrega a listagem."""
        prefix = prefix.strip("/")
        # Trava na raiz do cliente
        if not prefix.startswith(docs_window._base_root):  # type: ignore[attr-defined]
            prefix = docs_window._base_root  # type: ignore[attr-defined]
        docs_window._current_prefix = prefix  # type: ignore[attr-defined]
        docs_window._current_root = prefix  # type: ignore[attr-defined]
        _sync_path_label()
        _refresh_listing()

    docs_window._navigate_to_prefix = _set_prefix  # type: ignore[attr-defined]

    def _go_up_one():
        """Sobe um nível na hierarquia de pastas (botão ←)."""
        current = docs_window._current_prefix  # type: ignore[attr-defined]
        base = docs_window._base_root  # type: ignore[attr-defined]
        p = PurePosixPath(current)
        if str(p) == base:
            return  # Já está na raiz
        newp = str(p.parent)
        if not newp.startswith(base):
            newp = base
        _set_prefix(newp)

    def _go_forward():
        """
        Avança (botão →):
        - Se há pasta selecionada, entra nela
        - Senão, retorna para a raiz do cliente
        """
        sel = tree.selection()  # type: ignore[name-defined]
        if sel:
            item = sel[0]
            vals = tree.item(item, "values")  # type: ignore[name-defined]
            if vals:
                tipo = str(vals[0]).lower()
                if tipo == "pasta":
                    name = tree.item(item)["text"]  # type: ignore[name-defined]
                    _set_prefix(f"{docs_window._current_prefix}/{name}".strip("/"))  # type: ignore[attr-defined]
                    return

        base = docs_window._base_root  # type: ignore[attr-defined]
        _set_prefix(base)

    if show_nav_buttons and btn_prev and btn_next:
        btn_prev.configure(command=_go_up_one)
        btn_next.configure(command=_go_forward)

    def _refresh_listing():
        """Recarrega a listagem de arquivos usando o prefixo atual."""
        # Limpa a arvore
        for item in tree.get_children():  # type: ignore[name-defined]
            tree.delete(item)  # type: ignore[name-defined]
        # Atualiza o label de caminho
        _sync_path_label()
        # Recarrega usando versao assincrona para evitar travamento
        _populate_tree_async("", rel_prefix="")  # type: ignore[name-defined]

    # Barra superior (aÃ§Ãµes principais)
    topbar = ttk.Frame(header, padding=(UI_PADX, UI_PADY, UI_PADX, UI_PADY))
    topbar.grid(row=1, column=0, sticky="ew")
    topbar.columnconfigure(0, weight=1)
    topbar.columnconfigure(1, weight=0)
    setattr(docs_window, "topbar", topbar)

    left = ttk.Frame(topbar)
    left.grid(row=0, column=0, sticky="w")

    right = ttk.Frame(topbar)
    right.grid(row=0, column=1, sticky="e")

    btn_visualizar: Optional[ttk.Button] = None
    btn_baixar: Optional[ttk.Button] = None
    btn_zip: Optional[ttk.Button] = None
    btn_excluirsel: Optional[ttk.Button] = None
    btn_delete_files: Optional[ttk.Button] = None
    btn_delete_folder: Optional[ttk.Button] = None

    btn_baixar = ttk.Button(left, text="Baixar selecionado", command=lambda: do_download(), width=18)  # type: ignore[name-defined]
    btn_zip = ttk.Button(left, text="Baixar pasta (.zip)", width=18)
    btn_baixar.grid(row=0, column=0, padx=(0, UI_GAP))
    btn_zip.grid(row=0, column=1)
    setattr(docs_window, "btn_baixar", btn_baixar)
    setattr(docs_window, "btn_zip", btn_zip)

    btn_visualizar = ttk.Button(right, text="Visualizar", state="disabled")
    btn_visualizar.grid(row=0, column=0, padx=(0, UI_GAP))
    setattr(docs_window, "btn_visualizar", btn_visualizar)

    if module == "auditoria":
        btn_excluirsel = ttk.Button(right, text="Excluir selecionado", state="disabled")
        btn_excluirsel.grid(row=0, column=1)
        setattr(docs_window, "btn_excluirsel", btn_excluirsel)
        setattr(docs_window, "btn_delete_files", None)
        if delete_folder_handler is not None:
            btn_delete_folder = ttk.Button(right, text="Excluir pasta", state="disabled")
            btn_delete_folder.grid(row=0, column=2, padx=(0, UI_GAP))
            setattr(docs_window, "btn_delete_folder", btn_delete_folder)
        else:
            setattr(docs_window, "btn_delete_folder", None)
    else:
        setattr(docs_window, "btn_excluirsel", None)
        btn_delete_files = ttk.Button(right, text="Excluir arquivo(s)", state="disabled")
        btn_delete_files.grid(row=0, column=1, padx=(0, UI_GAP))
        btn_delete_folder = ttk.Button(right, text="Excluir pasta", state="disabled")
        btn_delete_folder.grid(row=0, column=2, padx=(0, UI_GAP))
        setattr(docs_window, "btn_delete_files", btn_delete_files)
        setattr(docs_window, "btn_delete_folder", btn_delete_folder)

    # TreeView (listagem de arquivos) com coluna de tamanho
    tree_container = ttk.Frame(docs_window)
    tree_container.grid(row=1, column=0, sticky="nsew", padx=UI_PADX, pady=UI_PADY)

    columns: list[str] = ["type", "size"]
    if enable_status_column:
        columns.append("status")
    if "_fullpath" not in columns:
        columns.append("_fullpath")

    tree = ttk.Treeview(
        tree_container,
        columns=tuple(columns),
        show="tree headings",
        selectmode="browse",
    )

    tree.heading("#0", text="Nome do arquivo/pasta", anchor="w")
    tree.heading("type", text="Tipo", anchor="center")
    tree.heading("size", text="Tamanho", anchor="e")
    if enable_status_column and "status" in tree["columns"]:
        tree.heading("status", text="Status", anchor="center")
    tree.column("#0", width=400, stretch=True)
    tree.column("type", width=100, anchor="center", stretch=False)
    tree.column("size", width=100, anchor="e", stretch=False)
    if enable_status_column and "status" in tree["columns"]:
        tree.column("status", width=80, anchor="center", stretch=False)
    if "_fullpath" in tree["columns"]:
        tree.heading("_fullpath", text="")
        tree.column("_fullpath", width=0, minwidth=0, stretch=False)

    # Ocultar coluna "size" conforme solicitaÃ§Ã£o do usuÃ¡rio
    try:
        display_cols = ["type"]
        if enable_status_column and "status" in tree["columns"]:
            display_cols.append("status")
        tree["displaycolumns"] = tuple(display_cols)
        tree.heading("size", text="")
        tree.column("size", width=0, stretch=False, minwidth=0)
        if "_fullpath" in tree["columns"]:
            tree.column("_fullpath", width=0, stretch=False, minwidth=0)
    except Exception:
        _log.debug("Falha ao configurar coluna _fullpath")

    # Scrollbars (vertical e horizontal)
    scroll_y = ttk.Scrollbar(tree_container, orient="vertical", command=tree.yview)
    scroll_x = ttk.Scrollbar(tree_container, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

    tree.grid(row=0, column=0, sticky="nsew")
    scroll_y.grid(row=0, column=1, sticky="ns")
    scroll_x.grid(row=1, column=0, sticky="ew")

    tree_container.rowconfigure(0, weight=1)
    tree_container.columnconfigure(0, weight=1)

    # Constantes já importadas de .constants, mas mantidas aqui por clarity local
    loading_nodes: set[str] = set()

    def _folder_status_for_display(full_path: str) -> str:
        if not enable_status_column:
            return ""
        status = docs_window._folder_status.get(full_path, FOLDER_STATUS_NEUTRAL)  # type: ignore[attr-defined]
        return STATUS_GLYPHS.get(status, STATUS_GLYPHS[FOLDER_STATUS_NEUTRAL])

    def _insert_row(parent, text, values, full_path: str, is_folder: bool):
        show_status = ""
        if enable_status_column and is_folder:
            show_status = _folder_status_for_display(full_path)
        base_values = list(values)
        new_values = base_values[:]
        if enable_status_column and "status" in tree["columns"]:
            new_values.append(show_status)
        if "_fullpath" in tree["columns"]:
            new_values.append("")
        iid = tree.insert(parent, "end", text=text, values=new_values)
        try:
            tree.set(iid, "_fullpath", full_path)
        except Exception:
            _log.debug("Falha ao definir _fullpath para item %s", iid)
        return iid

    def _get_item_fullpath(iid: str) -> str:
        try:
            return tree.set(iid, "_fullpath")
        except Exception:
            parts = []
            cur = iid
            while cur:
                parts.append(tree.item(cur, "text"))
                cur = tree.parent(cur)
            return "/".join(reversed([p for p in parts if p]))

    def _is_folder_iid(iid: str) -> bool:
        try:
            tipo = tree.set(iid, "type")
        except Exception:
            vals = tree.item(iid, "values")
            tipo = vals[0] if vals else ""
        return str(tipo).strip().lower() == "pasta"

    def _apply_folder_status(iid: str, status: str) -> None:
        if not enable_status_column:
            return
        full_path = _get_item_fullpath(iid)
        if not full_path:
            return
        docs_window._folder_status[full_path] = status  # type: ignore[attr-defined]
        glyph = STATUS_GLYPHS.get(status, STATUS_GLYPHS[FOLDER_STATUS_NEUTRAL])
        if enable_status_column and "status" in tree["columns"]:
            try:
                tree.set(iid, "status", glyph)
            except Exception:
                _log.debug("Falha ao definir status para item %s", iid)
        try:
            repo = getattr(docs_window, "repo", None)
            if repo and hasattr(repo, "set_folder_status"):
                repo.set_folder_status(full_path, status)
        except Exception:
            _log.debug("Falha ao persistir status da pasta %s", full_path)

    def _cycle_folder_status(iid: str) -> None:
        if not enable_status_column:
            return
        full_path = _get_item_fullpath(iid)
        if not full_path:
            return
        current = docs_window._folder_status.get(full_path, FOLDER_STATUS_NEUTRAL)  # type: ignore[attr-defined]
        nxt = {
            FOLDER_STATUS_NEUTRAL: FOLDER_STATUS_READY,
            FOLDER_STATUS_READY: FOLDER_STATUS_NOTREADY,
            FOLDER_STATUS_NOTREADY: FOLDER_STATUS_NEUTRAL,
        }.get(current, FOLDER_STATUS_NEUTRAL)
        _apply_folder_status(iid, nxt)

    def _on_tree_left_click(event):
        if not enable_status_column:
            return
        iid = tree.identify_row(event.y)
        col = tree.identify_column(event.x)
        if not iid or not col or col == "#0":
            return
        display_columns = list(tree["displaycolumns"])
        try:
            status_index = display_columns.index("status") + 1
        except ValueError:
            return
        if col == f"#{status_index}" and _is_folder_iid(iid):
            _cycle_folder_status(iid)

    def _ensure_status_menu() -> tk.Menu:
        ctx = getattr(docs_window, "_ctx_folder_menu", None)
        if ctx is None:
            ctx = tk.Menu(tree, tearoff=False)
            ctx.add_command(
                label="Marcar como PRONTA  ✓",
                command=lambda: _apply_folder_status(docs_window._ctx_iid, FOLDER_STATUS_READY),  # type: ignore[attr-defined]
            )
            ctx.add_command(
                label="Marcar como NÃO PRONTA  ✗",
                command=lambda: _apply_folder_status(docs_window._ctx_iid, FOLDER_STATUS_NOTREADY),  # type: ignore[attr-defined]
            )
            ctx.add_command(
                label="Limpar status  •",
                command=lambda: _apply_folder_status(docs_window._ctx_iid, FOLDER_STATUS_NEUTRAL),  # type: ignore[attr-defined]
            )
            docs_window._ctx_folder_menu = ctx  # type: ignore[attr-defined]
        return ctx  # type: ignore[return-value]

    def _on_tree_right_click(event):
        if not enable_status_column:
            return
        row = tree.identify_row(event.y)
        col = tree.identify_column(event.x)
        region = tree.identify_region(event.x, event.y)
        if not row or region != "cell" or not _is_folder_iid(row):
            return
        display_columns = list(tree["displaycolumns"])
        try:
            status_index = display_columns.index("status") + 1
        except ValueError:
            return
        if col != f"#{status_index}":
            return
        try:
            tree.selection_set(row)
        except Exception:
            _log.debug("Falha ao selecionar linha %s", row)
        docs_window._ctx_iid = row  # type: ignore[attr-defined]
        menu = _ensure_status_menu()
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            try:
                menu.grab_release()
            except Exception:
                _log.debug("Falha ao liberar grab do menu")

    # FunÃ§Ã£o de ordenaÃ§Ã£o da Treeview
    def _sort_tree(col: str, reverse: bool = False):
        """Ordena a Treeview por coluna clicada."""
        # LÃª valores atuais
        items = []
        for k in tree.get_children(""):
            if col == "#0":
                val = tree.item(k, "text")  # coluna Ã¡rvore: pega via item()
            else:
                val = tree.set(k, col)  # demais colunas: pega via set()
            items.append((val, k))

        # Ordena (numÃ©rico se der, senÃ£o string)
        def _key(x):
            v = x[0]
            # OrdenaÃ§Ã£o especial para tamanho
            if col == "size":
                if not v or v == "-":
                    return 0.0
                s = str(v).strip()
                if s.endswith(" GB"):
                    return float(s[:-3]) * 1024 * 1024 * 1024
                elif s.endswith(" MB"):
                    return float(s[:-3]) * 1024 * 1024
                elif s.endswith(" KB"):
                    return float(s[:-3]) * 1024
                elif s.endswith(" B"):
                    return float(s[:-2])
                return 0.0
            # OrdenaÃ§Ã£o numÃ©rica genÃ©rica
            try:
                return float(str(v).replace(",", "."))
            except Exception:
                return str(v).lower()

        items.sort(key=_key, reverse=reverse)

        # Reposiciona
        for idx, (_, k) in enumerate(items):
            tree.move(k, "", idx)

        # Alterna ordem no prÃ³ximo clique
        tree.heading(col, command=lambda: _sort_tree(col, not reverse))

        # Atualiza indicador de ordenaÃ§Ã£o no cabeÃ§alho
        columns_to_reset = ["#0", "type", "size"]
        if enable_status_column and "status" in tree["columns"]:
            columns_to_reset.append("status")
        for c in columns_to_reset:
            current_text = tree.heading(c)["text"]
            base_text = current_text.split(" ")[0] if current_text else ""
            tree.heading(c, text=base_text)  # Remove setas

        arrow = " ▼" if reverse else " ▲"
        current_text = tree.heading(col)["text"].split(" ")[0]
        tree.heading(col, text=current_text + arrow)

    # Bind click nos cabeÃ§alhos
    tree.heading("#0", command=lambda: _sort_tree("#0"))
    tree.heading("type", command=lambda: _sort_tree("type"))
    tree.heading("size", command=lambda: _sort_tree("size"))
    if enable_status_column and "status" in tree["columns"]:
        tree.heading("status", command=lambda: _sort_tree("status"))

    # Footer com botÃ£o Fechar
    footer = ttk.Frame(docs_window)
    footer.grid(row=2, column=0, sticky="ew", padx=UI_PADX, pady=(0, UI_PADY))

    def _persist_state_on_close() -> None:
        try:
            current_prefix = getattr(docs_window, "_current_prefix", "")
            key = getattr(docs_window, "_browser_key", "")
            if current_prefix and key:
                save_last_prefix(key, current_prefix)
            if enable_status_column and key:
                status_map = getattr(docs_window, "_folder_status", {})
                if isinstance(status_map, dict):
                    save_browser_status_map(key, status_map)
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao persistir estado em _persist_state_on_close: %s", exc)

    def _on_close() -> None:
        if getattr(docs_window, "_is_closing", False):
            return
        docs_window._is_closing = True  # type: ignore[attr-defined]
        for name in (
            "btn_visualizar",
            "btn_baixar",
            "btn_zip",
            "btn_excluirsel",
            "btn_delete_files",
            "btn_delete_folder",
        ):
            btn = getattr(docs_window, name, None)
            if btn is not None:
                try:
                    btn.configure(state="disabled")
                except Exception as exc:  # noqa: BLE001
                    _log.debug("Falha ao desabilitar botão %s em _on_close: %s", name, exc)
        window_key = getattr(docs_window, "_window_key", None)
        if window_key is not None:
            _OPEN_WINDOWS.pop(window_key, None)
        _persist_state_on_close()
        try:
            _original_destroy()
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao executar _original_destroy: %s", exc)

    # Botão "Carregar mais" (lado esquerdo)
    btn_load_more = ttk.Button(
        footer,
        text="Carregar mais arquivos",
        command=lambda: _load_next_page(),  # type: ignore[name-defined]
        state="disabled",
    )
    btn_load_more.grid(row=0, column=0, sticky="w")
    setattr(docs_window, "btn_load_more", btn_load_more)

    btn_close = ttk.Button(footer, text="Fechar", command=_on_close)
    btn_close.grid(row=0, column=1, sticky="e")
    docs_window.bind("<Escape>", lambda e: _on_close())
    docs_window.protocol("WM_DELETE_WINDOW", _on_close)
    docs_window.destroy = _on_close  # type: ignore[assignment]

    def _run_bg(target, on_done):
        res: dict[str, Any] = {"value": None, "err": None}

        def _worker():
            try:
                res["value"] = target()
            except Exception as e:
                res["err"] = e
            finally:
                _safe_after(0, lambda: on_done(res["value"], res["err"]))

        threading.Thread(target=_worker, daemon=True).start()

    def _set_actions_empty_state() -> None:
        try:
            btn_visualizar.configure(state="disabled")
            btn_baixar.configure(state="disabled")
            btn_zip.configure(state="disabled")
            if btn_excluirsel is not None:
                btn_excluirsel.configure(state="disabled")
            if btn_delete_files is not None:
                btn_delete_files.configure(state="disabled")
            if btn_delete_folder is not None:
                btn_delete_folder.configure(state="disabled")
            path_var.set(f"Supabase: {BUCKET}/{docs_window._current_prefix} (sem arquivos)")  # type: ignore[attr-defined]
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao definir estado vazio de ações: %s", exc)

    def _set_actions_normal_state() -> None:
        try:
            btn_baixar.configure(state="normal")
            try:
                btn_zip.configure(state="normal")
            except Exception as exc:  # noqa: BLE001
                _log.debug("Falha ao habilitar btn_zip: %s", exc)
            btn_visualizar.configure(state="disabled")
            if btn_excluirsel is not None:
                btn_excluirsel.configure(state="disabled")
            if btn_delete_files is not None:
                btn_delete_files.configure(state="disabled")
            if btn_delete_folder is not None:
                btn_delete_folder.configure(state="disabled")
            _sync_path_label()
            docs_window._current_root = docs_window._current_prefix  # type: ignore[attr-defined]
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao definir estado normal de ações: %s", exc)

    # Aliases para funções do módulo utils (manter compatibilidade interna)
    _format_size = format_file_size
    _sanitize_filename = sanitize_filename

    def _zip_suggest_name(prefix_path: str) -> str:
        """Adapter: usa suggest_zip_filename mas adiciona contexto do cliente."""
        base_name = suggest_zip_filename(prefix_path)
        sufixo = cnpj or f"ID {client_id}"
        return sanitize_filename(f"{base_name} - {sufixo} - {razao}".strip())

    def _toast_error(message: str) -> None:
        try:
            messagebox.showerror("Erro", message, parent=docs_window)
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao exibir mensagem de erro: %s", exc)

    def _destino_zip(remote_key: str) -> str | None:
        initial_dir = getattr(docs_window, "_last_download_dir", None) or str(Path.home() / "Downloads")
        chosen_dir = filedialog.askdirectory(
            parent=docs_window,
            initialdir=initial_dir,
            title="Escolha a pasta para salvar o ZIP",
            mustexist=True,
        )
        if not chosen_dir:
            docs_window._last_download_dir = None  # type: ignore[attr-defined]
            return None

        docs_window._last_download_dir = chosen_dir  # type: ignore[attr-defined]
        fname = _zip_suggest_name(remote_key)
        return os.path.join(chosen_dir, f"{fname}.zip")

    def _resolve_full_prefix(rel_prefix: str) -> str:
        base = docs_window._current_prefix  # type: ignore[attr-defined]
        rel = (rel_prefix or "").strip("/")
        return f"{base}/{rel}".strip("/") if rel else base

    def _fetch_children(rel_prefix: str) -> list[dict[str, Any]]:
        full_prefix = _resolve_full_prefix(rel_prefix)
        objects = uploads_service.list_storage_objects(BUCKET, prefix=full_prefix) or []
        items: list[dict[str, Any]] = []
        for obj in objects:
            raw_name = (obj.get("name") or "").strip("/")
            if not raw_name:
                continue
            display_name = raw_name.rsplit("/", 1)[-1]
            is_folder = bool(obj.get("is_folder"))
            size_bytes = obj.get("metadata", {}).get("size") if not is_folder else None
            items.append(
                {
                    "name": display_name,
                    "is_folder": is_folder,
                    "size": size_bytes,
                }
            )
        return items

    def _clear_children(parent_iid: str) -> None:
        for child in tree.get_children(parent_iid):
            tree.delete(child)

    def _insert_children(
        parent_iid: str,
        entries: list[dict[str, Any]],
        parent_full_prefix: str,
    ) -> int:
        count = 0
        for entry in entries:
            name = entry.get("name", "").strip()
            if not name:
                continue
            is_folder = bool(entry.get("is_folder"))
            size_bytes = entry.get("size") if not is_folder else None
            values = ("Pasta" if is_folder else "Arquivo", _format_size(size_bytes))
            full_path = "/".join(part for part in (parent_full_prefix, name) if part).strip("/")
            item_id = _insert_row(parent_iid, name, values, full_path, is_folder)
            count += 1
            if is_folder:
                blank_values = [""] * len(tree["columns"])
                tree.insert(
                    item_id,
                    "end",
                    text="",
                    values=blank_values,
                    open=False,
                    tags=(PLACEHOLDER_TAG,),
                )
        return count

    def _is_placeholder(iid: str) -> bool:
        try:
            return PLACEHOLDER_TAG in tree.item(iid, "tags")
        except Exception:
            return False

    def _needs_population(iid: str) -> bool:
        kids = tree.get_children(iid)
        if not kids:
            return True
        return any(_is_placeholder(child) for child in kids)

    def _is_folder_item(iid: str) -> bool:
        try:
            vals = tree.item(iid, "values") or []
        except Exception:
            return False
        if not vals:
            return False
        tipo = str(vals[0] or "").lower()
        return tipo == "pasta"

    def populate_tree(parent_item, rel_prefix: str):
        """
        DEPRECATED: Use _populate_tree_async() para carregamento assíncrono.
        Mantido para compatibilidade com código legado.
        """
        target_parent = parent_item or ""
        _clear_children(target_parent)

        try:
            entries = _fetch_children(rel_prefix)
        except Exception as exc:
            _toast_error(f"Falha ao listar arquivos: {exc}")
            return

        if target_parent == "":
            if not entries:
                _set_actions_empty_state()
                return
            _set_actions_normal_state()

        parent_full_prefix = _resolve_full_prefix(rel_prefix)
        inserted = _insert_children(target_parent, entries, parent_full_prefix)
        if target_parent and inserted == 0:
            info_values = ["Info"] + [""] * (len(tree["columns"]) - 1)
            tree.insert(
                target_parent,
                "end",
                text="(vazio)",
                values=info_values,
                open=False,
                tags=(EMPTY_TAG,),
            )

    def _populate_tree_async(parent_item, rel_prefix: str):
        """
        Versão assíncrona de populate_tree() para evitar travamento da GUI.

        Carrega a listagem de arquivos em thread de fundo e atualiza a UI
        no thread principal via after(). Usa paginação para listas grandes.
        """
        target_parent = parent_item or ""
        _clear_children(target_parent)

        # Adicionar placeholder "Carregando..."
        blank_values = [""] * len(tree["columns"])
        placeholder = tree.insert(
            target_parent,
            "end",
            text="Carregando arquivos...",
            values=blank_values,
            open=False,
            tags=(PLACEHOLDER_TAG,),
        )

        # Desabilitar botões durante carregamento
        if target_parent == "":
            _set_actions_empty_state()

        def work():
            try:
                data = _fetch_children(rel_prefix)
            except Exception as exc:
                data = exc

            def finish():
                if not tree.winfo_exists():
                    return
                if tree.exists(placeholder):
                    tree.delete(placeholder)

                if isinstance(data, Exception):
                    _toast_error(f"Falha ao listar arquivos: {data}")
                    if target_parent == "":
                        _set_actions_empty_state()
                    return

                if target_parent == "":
                    if not data:
                        _set_actions_empty_state()
                        return
                    _set_actions_normal_state()

                # Guardar lista completa e resetar offset para paginação
                docs_window._children_all = data  # type: ignore[attr-defined]
                docs_window._children_offset = 0  # type: ignore[attr-defined]
                docs_window._current_parent_iid = target_parent  # type: ignore[attr-defined]
                docs_window._current_parent_prefix = _resolve_full_prefix(rel_prefix)  # type: ignore[attr-defined]

                # Inserir primeira página
                _insert_children_page()  # type: ignore[name-defined]

                if target_parent and len(data) == 0:
                    info_values = ["Info"] + [""] * (len(tree["columns"]) - 1)
                    tree.insert(
                        target_parent,
                        "end",
                        text="(vazio)",
                        values=info_values,
                        open=False,
                        tags=(EMPTY_TAG,),
                    )

            try:
                _safe_after(0, finish)
            except Exception as exc:  # noqa: BLE001
                _log.debug("Falha ao agendar finish em _populate_tree_async: %s", exc)

        _executor.submit(work)

    def _insert_children_page() -> None:
        """
        Insere próxima página de arquivos/pastas na Treeview.
        Usa os atributos _children_all, _children_offset, _children_page_size.
        """
        all_children = docs_window._children_all  # type: ignore[attr-defined]
        offset = docs_window._children_offset  # type: ignore[attr-defined]
        page_size = docs_window._children_page_size  # type: ignore[attr-defined]
        parent_iid = docs_window._current_parent_iid  # type: ignore[attr-defined]
        parent_full_prefix = docs_window._current_parent_prefix  # type: ignore[attr-defined]

        start = offset
        end = min(start + page_size, len(all_children))
        page = all_children[start:end]

        # Inserir itens da página atual
        for entry in page:
            name = entry.get("name", "").strip()
            if not name:
                continue
            is_folder = bool(entry.get("is_folder"))
            size_bytes = entry.get("size") if not is_folder else None
            values = ("Pasta" if is_folder else "Arquivo", _format_size(size_bytes))
            full_path = "/".join(part for part in (parent_full_prefix, name) if part).strip("/")
            item_id = _insert_row(parent_iid, name, values, full_path, is_folder)
            if is_folder:
                blank_values = [""] * len(tree["columns"])
                tree.insert(
                    item_id,
                    "end",
                    text="",
                    values=blank_values,
                    open=False,
                    tags=(PLACEHOLDER_TAG,),
                )

        # Atualizar offset
        docs_window._children_offset = end  # type: ignore[attr-defined]

        # Atualizar estado do botão "Carregar mais"
        _update_load_more_button_state()  # type: ignore[name-defined]

    def _load_next_page() -> None:
        """
        Carrega e insere a próxima página de itens na Treeview.
        Chamado pelo botão "Carregar mais".
        """
        _insert_children_page()

    def _update_load_more_button_state() -> None:
        """
        Habilita/desabilita o botão "Carregar mais" dependendo se há mais itens.
        """
        btn_load_more = getattr(docs_window, "btn_load_more", None)
        if btn_load_more is None:
            return

        all_children = docs_window._children_all  # type: ignore[attr-defined]
        offset = docs_window._children_offset  # type: ignore[attr-defined]
        parent_iid = docs_window._current_parent_iid  # type: ignore[attr-defined]

        # Só mostrar botão para listagem raiz (parent_iid == "")
        if parent_iid != "":
            try:
                btn_load_more.grid_remove()
            except Exception as exc:  # noqa: BLE001
                _log.debug("Falha ao remover btn_load_more do grid: %s", exc)
            return

        # Habilitar/desabilitar conforme há mais itens
        if offset >= len(all_children):
            try:
                btn_load_more.configure(state="disabled")
            except Exception as exc:  # noqa: BLE001
                _log.debug("Falha ao desabilitar btn_load_more: %s", exc)
        else:
            try:
                btn_load_more.configure(state="normal")
                btn_load_more.grid()
            except Exception as exc:  # noqa: BLE001
                _log.debug("Falha ao habilitar/mostrar btn_load_more: %s", exc)

    def _populate_children_async(parent_iid: str, rel_prefix: str) -> None:
        if not tree.exists(parent_iid):
            return

        rel_norm = (rel_prefix or "").strip("/")
        if parent_iid in loading_nodes:
            return
        loading_nodes.add(parent_iid)
        _clear_children(parent_iid)
        blank_values = [""] * len(tree["columns"])
        placeholder = tree.insert(
            parent_iid,
            "end",
            text="Carregando...",
            values=blank_values,
            open=False,
            tags=(PLACEHOLDER_TAG,),
        )
        tree.item(parent_iid, open=True)

        def work():
            try:
                data = _fetch_children(rel_norm)
            except Exception as exc:  # pragma: no cover - log via UI
                data = exc

            def finish():
                loading_nodes.discard(parent_iid)
                if not tree.winfo_exists() or not tree.exists(parent_iid):
                    return
                if tree.exists(placeholder):
                    tree.delete(placeholder)
                if isinstance(data, Exception):
                    _toast_error(f"Falha ao listar subpastas: {data}")
                    return

                parent_full_prefix_async = _resolve_full_prefix(rel_norm)
                inserted_count = _insert_children(parent_iid, data, parent_full_prefix_async)
                if inserted_count == 0:
                    info_values = ["Info"] + [""] * (len(tree["columns"]) - 1)
                    tree.insert(
                        parent_iid,
                        "end",
                        text="(vazio)",
                        values=info_values,
                        open=False,
                        tags=(EMPTY_TAG,),
                    )

            try:
                _safe_after(0, finish)
            except Exception as exc:  # noqa: BLE001
                _log.debug("Falha ao agendar finish em _populate_children_async: %s", exc)
                loading_nodes.discard(parent_iid)

        _executor.submit(work)

    def _get_rel_path(item) -> str:
        parts = []
        cur = item
        while cur:
            t = tree.item(cur)["text"]
            if t:
                parts.append(t)
            cur = tree.parent(cur)
        parts.reverse()
        return "/".join(parts)

    def on_tree_open(_event=None):
        candidates: list[str] = []
        focus_item = tree.focus()
        if focus_item:
            candidates.append(focus_item)
        candidates.extend(list(tree.selection()))

        seen: set[str] = set()
        for item in candidates:
            if not item or item in seen:
                continue
            seen.add(item)
            if not _is_folder_item(item):
                continue
            if not _needs_population(item):
                continue
            rel = _get_rel_path(item)
            _populate_children_async(item, rel)

    def _current_item_info() -> tuple[str, str, str, str] | None:
        sel = tree.selection()
        if not sel:
            return None
        item = sel[0]
        tipo = (tree.item(item).get("values") or [""])[0]
        rel = _get_rel_path(item)
        nome = (tree.item(item).get("text") or "").strip()
        return item, tipo, rel, nome

    def _selected_folder_target() -> tuple[str, str] | None:
        """
        Retorna (prefixo_completo, nome_da_pasta) se uma pasta vÃ¡lida estiver selecionada.
        """
        info = _current_item_info()
        if not info:
            return None
        _item, tipo, rel, nome = info
        if (tipo or "").lower() != "pasta":
            return None

        rel_clean = rel.strip("/")
        current = docs_window._current_prefix  # type: ignore[attr-defined]
        full_prefix = f"{current}/{rel_clean}".strip("/") if rel_clean else current
        base_root = docs_window._base_root  # type: ignore[attr-defined]
        if not full_prefix.startswith(base_root):
            return None

        folder_name = rel_clean.split("/")[-1] if rel_clean else (nome or "")
        folder_name = (folder_name or "pasta").strip() or "pasta"
        return full_prefix, folder_name

    def _full_path_from_rel(rel_path: str) -> str | None:
        rel_clean = (rel_path or "").strip("/")
        current = docs_window._current_prefix  # type: ignore[attr-defined]
        remote_path = f"{current}/{rel_clean}".strip("/") if rel_clean else current
        root_remote = docs_window._root_remote  # type: ignore[attr-defined]
        if not remote_path.startswith(root_remote):
            return None
        return remote_path

    def _collect_files_under_prefix(prefix: str) -> list[str]:
        entries = uploads_service.list_storage_objects(BUCKET, prefix=prefix) or []
        collected: list[str] = []
        for entry in entries:
            full_path = (entry.get("full_path") or "").strip("/")
            if not full_path:
                continue
            if entry.get("is_folder"):
                collected.extend(_collect_files_under_prefix(full_path))
            else:
                collected.append(full_path)
        return collected

    def _update_preview_state() -> None:
        selection = tree.selection()
        if btn_delete_files is not None:
            has_file = any(str((tree.item(item).get("values") or [""])[0]).lower() == "arquivo" for item in selection)
            btn_delete_files.configure(state="normal" if has_file else "disabled")
        if btn_delete_folder is not None:
            enable_folder = False
            if len(selection) == 1:
                tipo_sel = str((tree.item(selection[0]).get("values") or [""])[0]).lower()
                enable_folder = tipo_sel == "pasta"
            btn_delete_folder.configure(state="normal" if enable_folder else "disabled")

        preview_busy = getattr(docs_window, "_preview_in_progress", False)
        info = _current_item_info()
        if not info:
            btn_visualizar.configure(state="disabled")
            if btn_excluirsel is not None:
                btn_excluirsel.configure(state="disabled")
            return
        _, tipo, rel, nome = info
        tipo_lower = str(tipo or "").lower()
        if tipo_lower != "arquivo" or not rel or preview_busy:
            btn_visualizar.configure(state="disabled")
            if btn_excluirsel is not None:
                btn_excluirsel.configure(state="disabled")
            return

        # Habilitar visualização para PDF e imagens (JPG, PNG, GIF)
        ext = nome.lower().split(".")[-1] if "." in nome else ""
        if ext in ("pdf", "jpg", "jpeg", "png", "gif") and not preview_busy:
            btn_visualizar.configure(state="normal")
        else:
            btn_visualizar.configure(state="disabled")

        if btn_excluirsel is not None:
            btn_excluirsel.configure(state="normal")

    def do_download():
        info = _current_item_info()
        if not info:
            return
        _item, tipo, rel, nome = info
        if tipo != "Arquivo" or not rel:
            return
        # Usa o prefixo atual ao invés do root_prefix fixo
        current = docs_window._current_prefix  # type: ignore[attr-defined]
        file_path = f"{current}/{rel}".strip("/")
        root_remote = docs_window._root_remote  # type: ignore[attr-defined]
        if not file_path.startswith(root_remote):
            return

        base = nome or os.path.basename(rel)
        stem, ext = os.path.splitext(base)
        sufixo = cnpj or f"ID {client_id}"
        suggest = _sanitize_filename(f"{stem} - {sufixo}{ext}")

        local_path = filedialog.asksaveasfilename(parent=docs_window, title="Salvar como", initialfile=suggest)
        if local_path:
            # Desabilitar botão durante download
            btn_baixar.configure(state="disabled")

            def _download_worker():
                try:
                    uploads_service.download_file(BUCKET, file_path, local_path)
                    return None  # sucesso
                except Exception as e:
                    return e  # erro

            def _on_download_complete(error):
                # Reabilitar botão
                btn_baixar.configure(state="normal")

                if error is None:
                    try:
                        messagebox.showinfo("Sucesso", "Arquivo baixado!", parent=docs_window)
                    except Exception as exc:  # noqa: BLE001
                        _log.debug("Falha ao exibir mensagem de sucesso em download: %s", exc)
                else:
                    try:
                        messagebox.showerror("Erro", f"Falha ao baixar: {error}", parent=docs_window)
                    except Exception as exc:  # noqa: BLE001
                        _log.debug("Falha ao exibir mensagem de erro em download: %s", exc)

            # Executar download em thread de fundo
            def _worker():
                result = _download_worker()
                _safe_after(0, lambda: _on_download_complete(result))

            threading.Thread(target=_worker, daemon=True).start()

    # Baixar pasta como ZIP (com Cancelar)
    def on_zip_folder():
        target = _selected_folder_target()
        if not target:
            messagebox.showinfo(
                "Baixar pasta",
                "Selecione uma pasta (ex.: GERAL, SIFAP).",
                parent=docs_window,
            )
            return

        prefix, pasta = target
        root_remote = docs_window._root_remote  # type: ignore[attr-defined]
        if not prefix.startswith(root_remote):
            messagebox.showerror(
                "Baixar pasta",
                "Prefixo invalido para download.",
                parent=docs_window,
            )
            return

        ident = cnpj or f"ID {client_id}"
        suggested_name = _sanitize_filename(f"{pasta} - {ident} - {razao}".strip())

        try:
            destino_zip = _destino_zip(prefix)
        except Exception as exc:
            _log.exception("Falha ao escolher destino do ZIP", exc_info=exc)
            try:
                messagebox.showerror("Erro", "Não foi possível carregar este arquivo.", parent=docs_window)
            except Exception as exc2:  # noqa: BLE001
                _log.debug("Falha ao exibir erro de destino ZIP: %s", exc2)
            return

        if not destino_zip:
            try:
                messagebox.showinfo("ZIP", "Operacao cancelada.", parent=docs_window)
            except Exception as exc:  # noqa: BLE001
                _log.debug("Falha ao exibir mensagem de cancelamento ZIP: %s", exc)
            return

        wait: tk.Toplevel | None = None

        try:
            zip_path = Path(destino_zip)
            out_dir = str(zip_path.parent)
            zip_name_param = zip_path.stem or suggested_name

            wait = tk.Toplevel(docs_window)
            wait.withdraw()
            wait.title("Aguarde...")
            wait.resizable(False, False)
            wait.transient(docs_window)
            try:
                wait.iconbitmap(resource_path("rc.ico"))
            except Exception as exc:  # noqa: BLE001
                _log.debug("Falha ao definir ícone em wait ZIP: %s", exc)
            wait.grab_set()

            frm = ttk.Frame(wait, padding=12)
            frm.pack(fill="both", expand=True)
            ttk.Label(frm, text=f"Compactando e baixando: {pasta}").pack(pady=(0, 8))
            pb = ttk.Progressbar(frm, mode="indeterminate", length=260)
            pb.pack()
            pb.start(12)

            docs_window.update_idletasks()
            pw, ph = docs_window.winfo_width(), docs_window.winfo_height()
            px, py = docs_window.winfo_rootx(), docs_window.winfo_rooty()
            w, h = 320, 140
            x = px + (pw - w) // 2
            y = py + (ph - h) // 2
            wait.geometry(f"{w}x{h}+{x}+{y}")
            wait.deiconify()

            cancel_event = docs_window._zip_cancel_evt  # type: ignore[attr-defined]
            cancel_event.clear()
            btns = ttk.Frame(frm)
            btns.pack(pady=(10, 0))
            btn_cancel = ttk.Button(btns, text="Cancelar")
            btn_cancel.pack(side="left")

            def _do_cancel():
                btn_cancel.configure(state="disabled")
                try:
                    pb.stop()
                    pb.configure(mode="determinate", value=0, maximum=100)
                except Exception as exc:  # noqa: BLE001
                    _log.debug("Falha ao parar progressbar em _do_cancel: %s", exc)
                cancel_event.set()

            btn_cancel.configure(command=_do_cancel)
            btn_zip.configure(state="disabled")

            def _baixar_zip_worker():
                return uploads_service.download_folder_zip(
                    prefix,
                    bucket=BUCKET,
                    zip_name=zip_name_param,
                    out_dir=out_dir,
                    timeout_s=300,
                    cancel_event=cancel_event,
                )

            fut = _executor.submit(_baixar_zip_worker)

            def _on_zip_finished(future):
                try:
                    pb.stop()
                except Exception as exc:  # noqa: BLE001
                    _log.debug("Falha ao parar pb em _on_zip_finished: %s", exc)
                try:
                    wait.grab_release()
                except Exception as exc:  # noqa: BLE001
                    _log.debug("Falha ao liberar grab em _on_zip_finished: %s", exc)
                try:
                    wait.destroy()
                except Exception as exc:  # noqa: BLE001
                    _log.debug("Falha ao destruir wait em _on_zip_finished: %s", exc)

                btn_zip.configure(state="normal")

                try:
                    destino = future.result()
                except uploads_service.DownloadCancelledError:
                    try:
                        messagebox.showinfo(
                            "Download cancelado",
                            "Voce cancelou o download.",
                            parent=docs_window,
                        )
                    except Exception as exc:  # noqa: BLE001
                        _log.debug("Falha ao exibir mensagem de cancelamento: %s", exc)
                except TimeoutError:
                    try:
                        messagebox.showerror(
                            "Tempo esgotado",
                            "O servidor nao respondeu a tempo (conexao ou leitura). Verifique sua internet e tente novamente.",
                            parent=docs_window,
                        )
                    except Exception as exc:  # noqa: BLE001
                        _log.debug("Falha ao exibir mensagem de timeout: %s", exc)
                except Exception as err:
                    try:
                        messagebox.showerror("Erro ao baixar pasta", str(err), parent=docs_window)
                    except Exception as exc:  # noqa: BLE001
                        _log.debug("Falha ao exibir mensagem de erro genérico: %s", exc)
                else:
                    try:
                        messagebox.showinfo(
                            "Download concluido",
                            f"ZIP salvo em\n{destino}",
                            parent=docs_window,
                        )
                    except Exception as exc:  # noqa: BLE001
                        _log.debug("Falha ao exibir mensagem de sucesso ZIP: %s", exc)

                try:
                    docs_window.lift()
                    docs_window.attributes("-topmost", True)
                    _safe_after(200, lambda: docs_window.attributes("-topmost", False))
                except Exception as exc:  # noqa: BLE001
                    _log.debug("Falha ao trazer janela para frente após ZIP: %s", exc)

            def _dispatch_done(future):
                try:
                    _safe_after(0, lambda: _on_zip_finished(future))
                except Exception as exc:  # noqa: BLE001
                    _log.debug("Falha ao agendar _on_zip_finished: %s", exc)

            fut.add_done_callback(_dispatch_done)
        except Exception as exc:
            if wait is not None:
                try:
                    wait.grab_release()
                except Exception as exc2:  # noqa: BLE001
                    _log.debug("Falha ao liberar grab em exception handler: %s", exc2)
                try:
                    wait.destroy()
                except Exception as exc2:  # noqa: BLE001
                    _log.debug("Falha ao destruir wait em exception handler: %s", exc2)
            try:
                btn_zip.configure(state="normal")
            except Exception as exc2:  # noqa: BLE001
                _log.debug("Falha ao reabilitar btn_zip em exception handler: %s", exc2)
            _log.exception("Erro ao iniciar download da pasta como ZIP", exc_info=exc)
            try:
                messagebox.showerror("Baixar pasta", f"Falha ao baixar pasta\n{exc}", parent=docs_window)
            except Exception as exc2:  # noqa: BLE001
                _log.debug("Falha ao exibir erro final em on_zip_folder: %s", exc2)

    btn_zip.configure(command=on_zip_folder)

    def _on_delete_files() -> None:
        if module == "auditoria":
            return

        selected_items = list(tree.selection())
        file_keys: list[str] = []
        for item in selected_items:
            tipo_val = (tree.item(item).get("values") or [""])[0]
            if str(tipo_val or "").lower() != "arquivo":
                continue
            rel = _get_rel_path(item)
            full_path = _full_path_from_rel(rel)
            if full_path:
                file_keys.append(full_path)

        if not file_keys:
            messagebox.showinfo("Excluir arquivo(s)", "Selecione um ou mais arquivos para excluir.", parent=docs_window)
            return

        if not messagebox.askyesno(
            "Excluir arquivo(s)",
            "Tem certeza que deseja excluir o(s) arquivo(s) selecionado(s)? Esta aÃ§Ã£o nÃ£o pode ser desfeita.",
            parent=docs_window,
        ):
            return

        try:
            for key in file_keys:
                uploads_service.delete_file(key)
        except Exception as exc:
            _log.exception("Erro ao excluir arquivos do cliente", exc_info=exc)
            messagebox.showerror("Excluir arquivo(s)", f"Falha ao excluir arquivo(s):\n{exc}", parent=docs_window)
            return

        messagebox.showinfo("Excluir arquivo(s)", "Arquivo(s) excluído(s) com sucesso.", parent=docs_window)
        _refresh_listing()

    def _on_delete_folder() -> None:
        target = _selected_folder_target()
        if not target:
            messagebox.showinfo("Excluir pasta", "Selecione uma pasta para excluir.", parent=docs_window)
            return

        prefix, pasta = target
        if not messagebox.askyesno(
            "Excluir pasta",
            "Tem certeza que deseja excluir esta pasta e todo o conteÃºdo? Esta aÃ§Ã£o nÃ£o pode ser desfeita.",
            parent=docs_window,
        ):
            return

        if module == "auditoria":
            if delete_folder_handler is None:
                return
            try:
                delete_folder_handler(BUCKET, prefix)
            except Exception as exc:
                _log.exception("Erro ao excluir pasta do modulo Auditoria", exc_info=exc)
                messagebox.showerror("Excluir pasta", f"Falha ao excluir a pasta:\n{exc}", parent=docs_window)
                return
        else:
            try:
                file_keys = _collect_files_under_prefix(prefix)
                for key in file_keys:
                    uploads_service.delete_file(key)
            except Exception as exc:
                _log.exception("Erro ao excluir pasta do cliente", exc_info=exc)
                messagebox.showerror("Excluir pasta", f"Falha ao excluir a pasta:\n{exc}", parent=docs_window)
                return

        messagebox.showinfo("Excluir pasta", f"Pasta '{pasta}' excluída com sucesso.", parent=docs_window)
        _refresh_listing()

    if btn_delete_files is not None:
        btn_delete_files.configure(command=_on_delete_files)
    if btn_delete_folder is not None:
        btn_delete_folder.configure(command=_on_delete_folder)

    def on_preview() -> None:
        if getattr(docs_window, "_preview_in_progress", False):
            return

        info = _current_item_info()
        if not info:
            return
        _item, tipo, rel, nome = info
        if (tipo or "").lower() != "arquivo" or not rel:
            _update_preview_state()
            return

        # Detectar extensão
        ext = nome.lower().split(".")[-1] if "." in nome else ""
        current = docs_window._current_prefix  # type: ignore[attr-defined]
        remote_path = f"{current}/{rel}".strip("/")
        root_remote = docs_window._root_remote  # type: ignore[attr-defined]
        if not remote_path.startswith(root_remote):
            _update_preview_state()
            return

        docs_window._preview_in_progress = True  # type: ignore[attr-defined]
        btn_visualizar.configure(state="disabled")

        def _target():
            return uploads_service.download_bytes(BUCKET, remote_path)

        def _done(data, err):
            try:
                if err or not data:
                    messagebox.showerror(
                        "Visualizar",
                        "Não foi possível carregar este arquivo.",
                        parent=docs_window,
                    )
                elif ext in ("pdf", "jpg", "jpeg", "png", "gif"):
                    # Visualizador unificado para PDF e imagens
                    try:
                        open_pdf_viewer(
                            docs_window,
                            data_bytes=data,
                            display_name=nome,
                        )
                    except Exception as exc:
                        messagebox.showerror(
                            "Visualizar",
                            f"Falha ao abrir visualização: {exc}",
                            parent=docs_window,
                        )
                else:
                    messagebox.showinfo(
                        "Visualizar",
                        f"Tipo de arquivo não suportado para visualização: .{ext}",
                        parent=docs_window,
                    )
            finally:
                docs_window._preview_in_progress = False  # type: ignore[attr-defined]
                _update_preview_state()

        _run_bg(_target, _done)

    btn_visualizar.configure(command=on_preview)

    def on_delete_selected():
        """Exclui arquivo selecionado (apenas no módulo auditoria)."""
        if module != "auditoria":
            return

        info = _current_item_info()
        if not info:
            return

        item, tipo, rel, nome = info
        if tipo != "Arquivo" or not rel:
            messagebox.showwarning(
                "Excluir",
                "Por favor, selecione um arquivo para excluir.",
                parent=docs_window,
            )
            return

        resposta = messagebox.askyesno(
            "Confirmar exclusão",
            f"Deseja realmente excluir o arquivo:\n\n{nome}\n\nEsta ação não pode ser desfeita.",
            parent=docs_window,
        )

        if not resposta:
            return

        # Monta caminho completo
        current = docs_window._current_prefix  # type: ignore[attr-defined]
        remote_path = f"{current}/{rel}".strip("/")
        root_remote = docs_window._root_remote  # type: ignore[attr-defined]
        if not remote_path.startswith(root_remote):
            return

        def _target():
            # Delega para uploads_service (camada de serviço)
            try:
                uploads_service.delete_file(remote_path)
                return True
            except Exception as e:
                return e

        def _done(result, err):
            if err:
                messagebox.showerror(
                    "Erro ao excluir",
                    f"Não foi possível excluir o arquivo:\n{err}",
                    parent=docs_window,
                )
            else:
                messagebox.showinfo(
                    "Arquivo excluído",
                    f"O arquivo '{nome}' foi excluído com sucesso.",
                    parent=docs_window,
                )
                # Recarrega a arvore (versao assincrona)
                current_prefix = docs_window._current_prefix  # type: ignore[attr-defined]
                rel_prefix = current_prefix.replace(root_prefix, "").lstrip("/")
                _populate_tree_async("", rel_prefix=rel_prefix)
                _update_preview_state()

        _run_bg(_target, _done)

    # Conecta botÃ£o de exclusÃ£o
    if btn_excluirsel is not None:
        btn_excluirsel.configure(command=on_delete_selected)
        # Bind tecla Delete
        tree.bind("<Delete>", lambda _e: on_delete_selected())

    def _activate_selection() -> bool:
        """Expande/colapsa pasta ou visualiza arquivo selecionado."""
        info = _current_item_info()
        if not info:
            return False

        item, tipo, rel, _nome = info
        tipo_lower = str(tipo or "").lower()
        if tipo_lower == "pasta":
            is_open = bool(tree.item(item, "open"))
            if is_open:
                tree.item(item, open=False)
            else:
                tree.item(item, open=True)
                if _needs_population(item):
                    _populate_children_async(item, rel)
            _update_preview_state()
            return True

        if tipo_lower == "arquivo":
            on_preview()
            return True
        return False

    def on_double_click(_event=None):
        if _activate_selection():
            return "break"
        return None

    def on_enter_key(_event=None):
        if _activate_selection():
            return "break"
        return None

    tree.bind("<<TreeviewOpen>>", on_tree_open)
    if enable_status_column:
        tree.bind("<Button-3>", _on_tree_right_click, add="+")
        tree.bind("<Button-1>", _on_tree_left_click, add="+")
    tree.bind("<Double-1>", on_double_click)
    tree.bind("<Return>", on_enter_key)
    tree.bind("<KP_Enter>", on_enter_key)
    tree.bind("<<TreeviewSelect>>", lambda _e: _update_preview_state())

    # Inicializacao (usa versao assincrona para evitar travamento)
    _sync_path_label()
    _populate_tree_async("", rel_prefix="")
    _update_preview_state()

    return docs_window
