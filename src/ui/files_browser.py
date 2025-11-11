# -*- coding: utf-8 -*-
import os
import re
import tempfile
import threading
import tkinter as tk
from pathlib import Path, PurePosixPath
from tkinter import filedialog, messagebox, ttk
from typing import Any, Optional

from adapters.storage.api import DownloadCancelledError, download_folder_zip
from infra.supabase.storage_helpers import download_bytes
from src.ui.forms.actions import download_file, list_storage_objects
from src.ui.pdf_preview_native import open_pdf_viewer
from src.utils.resource_path import resource_path  # evita ciclo com app_gui


def _cnpj_only_digits(text: str) -> str:
    """Retorna apenas dígitos do CNPJ; se vier None, devolve string vazia."""
    if text is None:
        return ""
    return re.sub(r"\D", "", str(text))


def format_cnpj_for_display(cnpj: str) -> str:
    """
    Formata CNPJ numérico em 00.000.000/0000-00.
    Se não tiver 14 dígitos (ex.: futuro alfanumérico), retorna como veio.
    """
    digits = _cnpj_only_digits(cnpj)
    if len(digits) == 14:
        return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"
    return str(cnpj or "")


def strip_cnpj_from_razao(razao: str, cnpj: str) -> str:
    """
    Remove do fim da razão social um CNPJ "cru" (14 dígitos) que tenha sido
    acidentalmente concatenado (com ou sem traços/'—').
    """
    if not razao:
        return ""
    raw = _cnpj_only_digits(cnpj or "")
    s = str(razao).strip()
    if raw:
        s = re.sub(rf"\s*[—–-]?\s*{re.escape(raw)}\s*$", "", s)
    return s.strip()


def get_clients_bucket() -> str:
    """Retorna o nome do bucket de clientes."""
    return "rc-docs"


def client_prefix_for_id(client_id: int, org_id: str) -> str:
    """
    Monta o prefixo do cliente no Storage.
    Formato: {org_id}/{client_id}
    """
    return f"{org_id}/{client_id}".strip("/")


def get_current_org_id(sb) -> str:  # type: ignore[no-untyped-def]
    """Obtém org_id do usuário logado via Supabase."""
    try:
        user = sb.auth.get_user()
        if not user or not user.user:
            return ""
        uid = user.user.id

        # Busca org_id na tabela memberships
        res = (
            sb.table("memberships")
            .select("org_id")
            .eq("user_id", uid)
            .limit(1)
            .execute()
        )
        if getattr(res, "data", None) and res.data and res.data[0].get("org_id"):
            return res.data[0]["org_id"]
    except Exception:
        pass
    return ""


def open_files_browser(
    parent,
    *,
    org_id: str,
    client_id: Any,
    razao: str = "",
    cnpj: str = "",
    supabase=None,  # type: ignore[no-untyped-def]
    start_prefix: str = "",
    module: str = ""
) -> tk.Toplevel:
    """
    Abre uma janela para navegar/baixar arquivos do Storage.

    Args:
        parent: Widget pai
        org_id: ID da organização
        client_id: ID do cliente
        razao: Razão social do cliente (opcional)
        cnpj: CNPJ do cliente (opcional)
        supabase: Cliente Supabase (opcional)
        start_prefix: Prefixo inicial opcional (ex: "{org_id}/{client_id}/GERAL/Auditoria")
                     Se fornecido, substitui o root_prefix padrão
        module: Nome do módulo que está abrindo o browser (ex: "auditoria")

    Returns:
        Janela Toplevel criada
    """
    BUCKET = "rc-docs"

    # Se start_prefix fornecido, usa ele; senão constrói padrão
    if start_prefix:
        root_prefix = start_prefix.strip("/")
    else:
        root_prefix = f"{org_id}/{client_id}".strip("/")

    # Título padronizado com CNPJ formatado e razão limpa
    razao_clean = strip_cnpj_from_razao(razao, cnpj)
    cnpj_fmt = format_cnpj_for_display(cnpj)
    docs_window = tk.Toplevel(parent)
    docs_window.title(f"Arquivos: {razao_clean} — {cnpj_fmt} — ID {client_id}")
    try:
        docs_window.iconbitmap(resource_path("rc.ico"))
    except Exception:
        pass

    # Guardar raiz e prefixo atual para navegação
    docs_window._org_id = org_id  # type: ignore[attr-defined]
    docs_window._client_id = client_id  # type: ignore[attr-defined]
    docs_window._base_root = f"{org_id}/{client_id}".strip("/")  # type: ignore[attr-defined]
    # Se start_prefix passado, respeita; senão começa na raiz do cliente
    docs_window._current_prefix = root_prefix  # type: ignore[attr-defined]

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

    _invalid_chars = r'[<>:"/\\|?*]'

    def _sanitize_filename(name: str) -> str:
        import re as _re

        s = _re.sub(_invalid_chars, "_", name).strip()
        return s.rstrip(" .")

    # Centraliza a janela
    _center_on_parent(docs_window, parent, width=760, height=520)

    # --- NAV BAR (setas + caminho) ---
    nav = ttk.Frame(docs_window)
    nav.pack(side="top", anchor="w", fill="x", padx=8, pady=(8, 0))

    # Setas de navegação
    btn_prev = ttk.Button(nav, text="←", width=3)
    btn_next = ttk.Button(nav, text="→", width=3)

    # Label do caminho
    path_var = tk.StringVar()

    def _sync_path_label():
        path_var.set(f"Supabase: {BUCKET}/{docs_window._current_prefix}")  # type: ignore[attr-defined]

    path_lbl = ttk.Label(nav, textvariable=path_var, foreground="#7a7a7a")

    btn_prev.pack(side="left", padx=(0, 6))
    btn_next.pack(side="left", padx=(0, 12))
    path_lbl.pack(side="left", padx=(0, 6))

    def _set_prefix(prefix: str):
        """Define o prefixo atual e recarrega a listagem."""
        prefix = prefix.strip("/")
        # Trava na raiz do cliente
        if not prefix.startswith(docs_window._base_root):  # type: ignore[attr-defined]
            prefix = docs_window._base_root  # type: ignore[attr-defined]
        docs_window._current_prefix = prefix  # type: ignore[attr-defined]
        _sync_path_label()
        _refresh_listing()

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
        - Senão, segue trilha: base → GERAL → GERAL/Auditoria
        """
        # Tenta entrar na pasta selecionada
        sel = tree.selection()  # type: ignore[name-defined]
        if sel:
            item = sel[0]
            vals = tree.item(item, "values")  # type: ignore[name-defined]
            if vals and len(vals) > 0:
                tipo = vals[0] if len(vals) == 1 else (vals[1] if len(vals) > 1 else "")
                if (tipo or "").lower() == "pasta":
                    name = tree.item(item)["text"]  # type: ignore[name-defined]
                    _set_prefix(f"{docs_window._current_prefix}/{name}".strip("/"))  # type: ignore[attr-defined]
                    return

        # Fallback por etapas
        cur = docs_window._current_prefix  # type: ignore[attr-defined]
        base = docs_window._base_root  # type: ignore[attr-defined]
        if cur == base:
            _set_prefix(f"{base}/GERAL")
        elif cur == f"{base}/GERAL":
            _set_prefix(f"{base}/GERAL/Auditoria")
        else:
            pass  # Já no fim da trilha

    btn_prev.configure(command=_go_up_one)
    btn_next.configure(command=_go_forward)

    def _refresh_listing():
        """Recarrega a listagem de arquivos usando o prefixo atual."""
        # Limpa a árvore
        for item in tree.get_children():  # type: ignore[name-defined]
            tree.delete(item)  # type: ignore[name-defined]
        # Atualiza o label de caminho
        _sync_path_label()
        # Recarrega
        populate_tree("", rel_prefix="")  # type: ignore[name-defined]

    # Header com botões de ação
    header = ttk.Frame(docs_window)
    header.pack(side="top", fill="x", padx=8, pady=(8, 0))

    left_box = ttk.Frame(header)
    left_box.pack(side="left")
    right_box = ttk.Frame(header)
    right_box.pack(side="right")

    # À esquerda: Baixar selecionado e Baixar pasta (.zip)
    btn_download_sel = ttk.Button(left_box, text="Baixar selecionado", command=lambda: do_download())  # type: ignore[name-defined]
    btn_zip_folder = ttk.Button(left_box, text="Baixar pasta (.zip)")
    btn_download_sel.pack(side="left", padx=(0, 6))
    btn_zip_folder.pack(side="left")

    # À direita: Visualizar + Excluir (se auditoria)
    btn_preview = ttk.Button(right_box, text="Visualizar", state="disabled")
    btn_preview.pack(side="right", padx=(0, 6) if module == "auditoria" else (0, 0))
    
    # Botão de exclusão (apenas para auditoria)
    if module == "auditoria":
        btn_delete = ttk.Button(right_box, text="Excluir selecionado", state="disabled")
        btn_delete.pack(side="right")
    else:
        btn_delete = None  # type: ignore[assignment]

    # Frame de filtro (Ctrl+F)
    filter_frame = ttk.Frame(docs_window)
    filter_frame.pack(side="top", fill="x", padx=8, pady=(0, 4))

    ttk.Label(filter_frame, text="🔍 Filtrar:").pack(side="left", padx=(0, 4))
    filter_var = tk.StringVar()
    filter_entry = ttk.Entry(filter_frame, textvariable=filter_var, width=40)
    filter_entry.pack(side="left", fill="x", expand=True)

    btn_clear_filter = ttk.Button(filter_frame, text="✕", width=3, command=lambda: filter_var.set(""))
    btn_clear_filter.pack(side="left", padx=(4, 0))

    # Bind Enter para aplicar filtro
    filter_entry.bind("<Return>", lambda e: _refresh_listing())  # type: ignore[name-defined]

    # Bind Ctrl+F para focar no filtro
    docs_window.bind("<Control-f>", lambda e: filter_entry.focus_set())
    docs_window.bind("<Control-F>", lambda e: filter_entry.focus_set())

    # TreeView (listagem de arquivos) com coluna de tamanho
    tree_container = ttk.Frame(docs_window)
    tree_container.pack(expand=True, fill="both", padx=8, pady=8)

    tree = ttk.Treeview(
        tree_container, columns=("type", "size"), show="tree headings", selectmode="browse"
    )
    tree.heading("#0", text="Nome do arquivo/pasta", anchor="w")
    tree.heading("type", text="Tipo", anchor="center")
    tree.heading("size", text="Tamanho", anchor="e")
    tree.column("#0", width=400, stretch=True)
    tree.column("type", width=100, anchor="center", stretch=False)
    tree.column("size", width=100, anchor="e", stretch=False)

    # Scrollbars (vertical e horizontal)
    scroll_y = ttk.Scrollbar(tree_container, orient="vertical", command=tree.yview)
    scroll_x = ttk.Scrollbar(tree_container, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

    tree.grid(row=0, column=0, sticky="nsew")
    scroll_y.grid(row=0, column=1, sticky="ns")
    scroll_x.grid(row=1, column=0, sticky="ew")

    tree_container.rowconfigure(0, weight=1)
    tree_container.columnconfigure(0, weight=1)

    # Label "Carregando..." (oculto por padrão)
    loading_label = ttk.Label(tree_container, text="⏳ Carregando...", foreground="#888")

    # Variáveis para ordenação
    sort_column = {"col": None, "reverse": False}

    def _sort_tree(col: str):
        """Ordena a Treeview por coluna clicada."""
        # Inverte direção se clicar na mesma coluna
        if sort_column["col"] == col:
            sort_column["reverse"] = not sort_column["reverse"]
        else:
            sort_column["col"] = col
            sort_column["reverse"] = False

        # Coleta itens (apenas raiz, ignorando filhos expandidos)
        items = [(tree.set(k, col), k) for k in tree.get_children("")]

        # Ordenação especial para tamanho (numérico)
        if col == "size":
            def _parse_size(s: str) -> float:
                if not s or s == "-":
                    return 0.0
                s = s.strip()
                if s.endswith(" GB"):
                    return float(s[:-3]) * 1024 * 1024 * 1024
                elif s.endswith(" MB"):
                    return float(s[:-3]) * 1024 * 1024
                elif s.endswith(" KB"):
                    return float(s[:-3]) * 1024
                elif s.endswith(" B"):
                    return float(s[:-2])
                return 0.0
            items.sort(key=lambda x: _parse_size(x[0]), reverse=sort_column["reverse"])
        else:
            items.sort(reverse=sort_column["reverse"])

        # Reordena itens
        for idx, (_, k) in enumerate(items):
            tree.move(k, "", idx)

        # Atualiza indicador de ordenação no cabeçalho
        for c in ["#0", "type", "size"]:
            tree.heading(c, text=tree.heading(c)["text"].split(" ")[0])  # Remove setas

        arrow = " ▼" if sort_column["reverse"] else " ▲"
        current_text = tree.heading(col)["text"].split(" ")[0]
        tree.heading(col, text=current_text + arrow)

    # Bind click nos cabeçalhos
    tree.heading("#0", command=lambda: _sort_tree("#0"))
    tree.heading("type", command=lambda: _sort_tree("type"))
    tree.heading("size", command=lambda: _sort_tree("size"))

    # Footer com botão Fechar
    footer = ttk.Frame(docs_window)
    footer.pack(side="bottom", fill="x", padx=8, pady=(0, 6))

    btn_close = ttk.Button(footer, text="Fechar", command=docs_window.destroy)
    btn_close.pack(side="right")
    docs_window.bind("<Escape>", lambda e: docs_window.destroy())

    def _run_bg(target, on_done):
        res: dict[str, Any] = {"value": None, "err": None}

        def _worker():
            try:
                res["value"] = target()
            except Exception as e:
                res["err"] = e
            finally:
                docs_window.after(0, lambda: on_done(res["value"], res["err"]))

        threading.Thread(target=_worker, daemon=True).start()

    def _format_size(bytes_val: int | None) -> str:
        """Formata tamanho em bytes para string legível."""
        if bytes_val is None or bytes_val == 0:
            return "-"

        if bytes_val < 1024:
            return f"{bytes_val} B"
        elif bytes_val < 1024 * 1024:
            return f"{bytes_val / 1024:.1f} KB"
        elif bytes_val < 1024 * 1024 * 1024:
            return f"{bytes_val / (1024 * 1024):.1f} MB"
        else:
            return f"{bytes_val / (1024 * 1024 * 1024):.2f} GB"

    def populate_tree(parent_item, rel_prefix: str):
        # Mostra label "Carregando..." se for chamada da raiz
        if not parent_item:
            loading_label.grid(row=0, column=0, sticky="nsew")
            docs_window.update_idletasks()

        # Usa o prefixo atual da navegação
        current = docs_window._current_prefix  # type: ignore[attr-defined]
        full_prefix = (
            current if not rel_prefix else f"{current}/{rel_prefix}".rstrip("/")
        )

        # Obter filtro
        filter_text = filter_var.get().strip().lower()

        objects = list_storage_objects(BUCKET, prefix=full_prefix) or []
        for obj in objects:
            name = (obj.get("name") or "").strip("/")
            is_folder = bool(obj.get("is_folder"))
            size_bytes = obj.get("metadata", {}).get("size") if not is_folder else None

            # Aplicar filtro (apenas arquivos, pastas sempre mostradas)
            if filter_text and not is_folder:
                if filter_text not in name.lower():
                    continue

            item_id = tree.insert(
                parent_item,
                "end",
                text=name,
                values=("Pasta" if is_folder else "Arquivo", _format_size(size_bytes)),
                open=False,
            )
            if is_folder:
                tree.insert(item_id, "end", text="", values=("...", "-"))

        # Oculta label "Carregando..."
        if not parent_item:
            loading_label.grid_forget()

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
        sel = tree.selection()
        if not sel:
            return
        item = sel[0]
        kids = tree.get_children(item)
        if kids and tree.item(kids[0])["text"] == "":
            tree.delete(kids[0])
            rel = _get_rel_path(item)
            rel_prefix = (rel + "/") if rel else ""
            populate_tree(item, rel_prefix)

    def _current_item_info() -> tuple[str, str, str, str] | None:
        sel = tree.selection()
        if not sel:
            return None
        item = sel[0]
        tipo = (tree.item(item).get("values") or [""])[0]
        rel = _get_rel_path(item)
        nome = (tree.item(item).get("text") or "").strip()
        return item, tipo, rel, nome

    def _update_preview_state() -> None:
        info = _current_item_info()
        if not info:
            btn_preview.configure(state="disabled")
            if btn_delete:
                btn_delete.configure(state="disabled")
            return
        _, tipo, rel, nome = info
        if tipo != "Arquivo" or not rel:
            btn_preview.configure(state="disabled")
            if btn_delete:
                btn_delete.configure(state="disabled")
            return

        # Habilitar visualização para PDF e imagens (JPG, PNG, GIF)
        ext = nome.lower().split(".")[-1] if "." in nome else ""
        if ext in ("pdf", "jpg", "jpeg", "png", "gif"):
            btn_preview.configure(state="normal")
        else:
            btn_preview.configure(state="disabled")
        
        # Habilitar exclusão para qualquer arquivo selecionado (auditoria)
        if btn_delete:
            btn_delete.configure(state="normal")

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

        base = nome or os.path.basename(rel)
        stem, ext = os.path.splitext(base)
        sufixo = cnpj or f"ID {client_id}"
        suggest = _sanitize_filename(f"{stem} - {sufixo}{ext}")

        local_path = filedialog.asksaveasfilename(
            parent=docs_window, title="Salvar como", initialfile=suggest
        )
        if local_path:
            try:
                download_file(BUCKET, file_path, local_path)
                messagebox.showinfo("Sucesso", "Arquivo baixado!", parent=docs_window)
            except Exception as e:
                messagebox.showerror(
                    "Erro", f"Falha ao baixar: {e}", parent=docs_window
                )

    # Baixar pasta como ZIP (com Cancelar)
    def on_zip_folder():
        sel = tree.selection()
        if not sel:
            messagebox.showinfo(
                "Baixar pasta",
                "Selecione uma pasta (ex.: GERAL, SIFAP).",
                parent=docs_window,
            )
            return
        item = sel[0]
        tipo = (tree.item(item).get("values") or [""])[0]
        if (tipo or "").lower() != "pasta":
            messagebox.showinfo(
                "Baixar pasta", "O item selecionado nao e pasta.", parent=docs_window
            )
            return

        rel = _get_rel_path(item)
        if not rel:
            messagebox.showerror(
                "Baixar pasta",
                "Nao foi possivel determinar a pasta.",
                parent=docs_window,
            )
            return

        # Usa o prefixo atual ao invés do root_prefix fixo
        current = docs_window._current_prefix  # type: ignore[attr-defined]
        prefix = f"{current}/{rel}".strip("/")
        pasta = rel.rstrip("/").split("/")[-1] or "pasta"
        ident = cnpj or f"ID {client_id}"
        zip_name = _sanitize_filename(f"{pasta} - {ident} - {razao}".strip())

        # Pasta de destino (Cancelar => Downloads)
        initial = str(Path.home() / "Downloads")
        chosen_dir = filedialog.askdirectory(
            parent=docs_window,
            title="Escolha a pasta para salvar o ZIP (Cancelar = Downloads padrao)",
            initialdir=initial,
            mustexist=True,
        )
        out_dir = chosen_dir or None

        # Dialogo "Aguarde..."
        wait = tk.Toplevel(docs_window)
        wait.withdraw()
        wait.title("Aguarde...")
        wait.resizable(False, False)
        wait.transient(docs_window)
        try:
            wait.iconbitmap(resource_path("rc.ico"))
        except Exception:
            pass
        wait.grab_set()

        frm = ttk.Frame(wait, padding=12)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text=f"Compactando e baixando: {pasta}").pack(pady=(0, 8))
        pb = ttk.Progressbar(frm, mode="indeterminate", length=260)
        pb.pack()
        pb.start(12)

        # Centraliza e mostra
        docs_window.update_idletasks()
        pw, ph = docs_window.winfo_width(), docs_window.winfo_height()
        px, py = docs_window.winfo_rootx(), docs_window.winfo_rooty()
        w, h = 320, 140
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
        wait.geometry(f"{w}x{h}+{x}+{y}")
        wait.deiconify()

        cancel_event = threading.Event()
        btns = ttk.Frame(frm)
        btns.pack(pady=(10, 0))
        btn_cancel = ttk.Button(btns, text="Cancelar")
        btn_cancel.pack(side="left")

        def _do_cancel():
            btn_cancel.configure(state="disabled")
            try:
                pb.stop()
                pb.configure(mode="determinate", value=0, maximum=100)
            except Exception:
                pass
            cancel_event.set()

        btn_cancel.configure(command=_do_cancel)
        btn_zip_folder.configure(state="disabled")

        def _target():
            return download_folder_zip(
                prefix,
                bucket=BUCKET,
                zip_name=zip_name,
                out_dir=out_dir,
                timeout_s=300,
                cancel_event=cancel_event,
            )

        def _done(destino, err):
            try:
                wait.grab_release()
            except Exception:
                pass
            try:
                wait.destroy()
            except Exception:
                pass
            btn_zip_folder.configure(state="normal")

            if err:
                if isinstance(err, DownloadCancelledError):
                    messagebox.showinfo(
                        "Download cancelado",
                        "Voce cancelou o download.",
                        parent=docs_window,
                    )
                elif isinstance(err, TimeoutError):
                    messagebox.showerror(
                        "Tempo esgotado",
                        "O servidor nao respondeu a tempo (conexao ou leitura). "
                        "Verifique sua internet e tente novamente.",
                        parent=docs_window,
                    )
                else:
                    messagebox.showerror(
                        "Erro ao baixar pasta", str(err), parent=docs_window
                    )
            else:
                messagebox.showinfo(
                    "Download concluido",
                    f"ZIP salvo em:\n{destino}",
                    parent=docs_window,
                )

            try:
                docs_window.lift()
                docs_window.attributes("-topmost", True)
                docs_window.after(
                    200, lambda: docs_window.attributes("-topmost", False)
                )
            except Exception:
                pass

        _run_bg(_target, _done)

    btn_zip_folder.configure(command=on_zip_folder)

    def on_preview() -> None:
        info = _current_item_info()
        if not info:
            return
        _item, tipo, rel, nome = info
        if tipo != "Arquivo" or not rel:
            _update_preview_state()
            return

        # Detectar extensão
        ext = nome.lower().split(".")[-1] if "." in nome else ""

        btn_preview.configure(state="disabled")
        # Usa o prefixo atual ao invés do root_prefix fixo
        current = docs_window._current_prefix  # type: ignore[attr-defined]
        remote_path = f"{current}/{rel}".strip("/")

        def _target():
            return download_bytes(BUCKET, remote_path)

        def _done(data, err):
            if err or not data:
                messagebox.showerror(
                    "Visualizar",
                    f"Não foi possível carregar este arquivo.",
                    parent=docs_window,
                )
            elif ext in ("pdf", "jpg", "jpeg", "png", "gif"):
                # Visualizador unificado para PDF e imagens
                try:
                    viewer = open_pdf_viewer(
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
                    parent=docs_window
                )
            _update_preview_state()

        _run_bg(_target, _done)

    btn_preview.configure(command=on_preview)

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
        
        # Confirma exclusão
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
        
        def _target():
            # Usa cliente supabase para remover
            if supabase:
                storage = supabase.storage.from_(BUCKET)
                result = storage.remove([remote_path])
                return result
            return None
        
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
                # Recarrega a árvore
                current_prefix = docs_window._current_prefix  # type: ignore[attr-defined]
                rel_prefix = current_prefix.replace(root_prefix, "").lstrip("/")
                populate_tree("", rel_prefix=rel_prefix)
                _update_preview_state()
        
        _run_bg(_target, _done)
    
    # Conecta botão de exclusão
    if btn_delete:
        btn_delete.configure(command=on_delete_selected)
        # Bind tecla Delete
        tree.bind("<Delete>", lambda _e: on_delete_selected())

    def on_double_click(_event=None):
        """Duplo-clique: visualiza arquivo ou expande/colapsa pasta."""
        info = _current_item_info()
        if not info:
            return
        
        item, tipo, rel, nome = info
        
        if tipo == "Pasta":
            # Toggle expansão de pastas
            if tree.item(item, "open"):
                tree.item(item, open=False)
            else:
                tree.item(item, open=True)
        else:
            # Visualiza arquivo
            on_preview()

    tree.bind("<<TreeviewOpen>>", on_tree_open)
    tree.bind("<Double-1>", on_double_click)
    tree.bind("<<TreeviewSelect>>", lambda _e: _update_preview_state())

    # Inicialização
    _sync_path_label()
    populate_tree("", rel_prefix="")
    _update_preview_state()

    return docs_window
