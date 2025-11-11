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
    start_prefix: str = ""
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

    # À direita: Visualizar
    btn_preview = ttk.Button(right_box, text="Visualizar", state="disabled")
    btn_preview.pack(side="right")

    # TreeView (listagem de arquivos)
    tree = ttk.Treeview(
        docs_window, columns=("type",), show="tree headings", selectmode="browse"
    )
    tree.heading("#0", text="Nome do arquivo/pasta", anchor="w")
    tree.heading("type", text="Tipo", anchor="center")
    tree.column("#0", width=560, stretch=True)
    tree.column("type", width=120, anchor="center", stretch=False)
    tree.pack(expand=True, fill="both", padx=8, pady=8)

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

    def populate_tree(parent_item, rel_prefix: str):
        # Usa o prefixo atual da navegação
        current = docs_window._current_prefix  # type: ignore[attr-defined]
        full_prefix = (
            current if not rel_prefix else f"{current}/{rel_prefix}".rstrip("/")
        )
        objects = list_storage_objects(BUCKET, prefix=full_prefix) or []
        for obj in objects:
            name = (obj.get("name") or "").strip("/")
            is_folder = bool(obj.get("is_folder"))
            item_id = tree.insert(
                parent_item,
                "end",
                text=name,
                values=("Pasta" if is_folder else "Arquivo",),
                open=False,
            )
            if is_folder:
                tree.insert(item_id, "end", text="", values=("...",))

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
            return
        _, tipo, rel, nome = info
        if tipo != "Arquivo" or not rel or not nome.lower().endswith(".pdf"):
            btn_preview.configure(state="disabled")
            return
        btn_preview.configure(state="normal")

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
        if tipo != "Arquivo" or not rel or not nome.lower().endswith(".pdf"):
            _update_preview_state()
            return

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
                    "Nao foi possivel carregar este PDF.",
                    parent=docs_window,
                )
            else:
                tmp_path = None
                try:
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                    try:
                        tmp.write(data)
                        tmp_path = tmp.name
                    finally:
                        tmp.close()
                    viewer = open_pdf_viewer(docs_window, tmp_path, display_name=nome)

                    def _cleanup(_event=None):
                        try:
                            os.unlink(tmp_path)
                        except OSError:
                            pass

                    viewer.bind("<Destroy>", _cleanup, add="+")
                except Exception as exc:
                    if tmp_path:
                        try:
                            os.unlink(tmp_path)
                        except OSError:
                            pass
                    messagebox.showerror(
                        "Visualizar",
                        f"Falha ao abrir visualizacao: {exc}",
                        parent=docs_window,
                    )
            _update_preview_state()

        _run_bg(_target, _done)

    btn_preview.configure(command=on_preview)

    def on_double_click(_event=None):
        do_download()

    tree.bind("<<TreeviewOpen>>", on_tree_open)
    tree.bind("<Double-1>", on_double_click)
    tree.bind("<<TreeviewSelect>>", lambda _e: _update_preview_state())

    # Inicialização
    _sync_path_label()
    populate_tree("", rel_prefix="")
    _update_preview_state()

    return docs_window
