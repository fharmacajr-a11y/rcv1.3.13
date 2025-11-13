# -*- coding: utf-8 -*-
"""
Módulo para upload avançado de arquivos/pastas para Supabase Storage.
Permite escolher destino (bucket/pasta), upload múltiplo e progresso visual.
"""

import logging
import mimetypes
import os
import posixpath
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import List, Optional, Tuple

log = logging.getLogger(__name__)


class StorageDestinationDialog(tk.Toplevel):
    """Diálogo para selecionar bucket e pasta de destino no Supabase Storage."""

    def __init__(self, master, supabase_client, title="Destino no Storage"):
        super().__init__(master)
        self.title(title)
        self.resizable(False, False)
        self.grab_set()
        self.supabase = supabase_client
        self.result: Optional[Tuple[str, str]] = None  # (bucket, prefix)

        frm = ttk.Frame(self, padding=12)
        frm.grid(row=0, column=0, sticky="nsew")

        ttk.Label(frm, text="Bucket:").grid(row=0, column=0, sticky="w")
        self.cb_bucket = ttk.Combobox(frm, state="readonly", width=40)
        self.cb_bucket.grid(row=0, column=1, sticky="we", padx=(6, 0))

        ttk.Label(frm, text="Pasta (prefix):").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.ent_prefix = ttk.Entry(frm, width=42)
        self.ent_prefix.grid(row=1, column=1, sticky="we", padx=(6, 0), pady=(8, 0))

        self.tree = ttk.Treeview(frm, columns=("name",), show="tree", height=12)
        self.tree.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(8, 0))
        yscroll = ttk.Scrollbar(frm, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=yscroll.set)
        yscroll.grid(row=2, column=2, sticky="ns", pady=(8, 0))

        btns = ttk.Frame(frm)
        btns.grid(row=3, column=0, columnspan=2, sticky="e", pady=(10, 0))
        ttk.Button(btns, text="Cancelar", command=self._cancel).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(btns, text="OK", command=self._ok).grid(row=0, column=1)

        frm.columnconfigure(1, weight=1)

        self._load_buckets()

        self.cb_bucket.bind("<<ComboboxSelected>>", self._on_bucket_change)
        self.tree.bind("<<TreeviewOpen>>", self._on_open_node)
        self.tree.bind("<Double-1>", self._on_double_click)

        # Centralizar
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"+{x}+{y}")

    def _cancel(self):
        self.result = None
        self.destroy()

    def _ok(self):
        bucket = self.cb_bucket.get().strip()
        prefix = self.ent_prefix.get().strip().replace("\\", "/").strip("/")
        if not bucket:
            messagebox.showwarning("Atenção", "Selecione um bucket.", parent=self)
            return
        self.result = (bucket, prefix)
        self.destroy()

    def _load_buckets(self):
        try:
            buckets = self.supabase.storage.list_buckets()
            names = [b["name"] for b in buckets]
        except Exception as e:
            log.warning("Erro ao listar buckets: %s", e)
            names = []

        self.cb_bucket["values"] = names
        if names:
            self.cb_bucket.current(0)
            self._populate_root(names[0])

    def _on_bucket_change(self, _evt=None):
        bucket = self.cb_bucket.get()
        if bucket:
            self._populate_root(bucket)

    def _populate_root(self, bucket):
        # Limpa árvore
        for i in self.tree.get_children(""):
            self.tree.delete(i)

        # Lista "pastas" do bucket (nível 1)
        for item in self._list(bucket, ""):
            if item.get("id") == "folder" or item.get("name", "").endswith("/"):
                node = self.tree.insert("", "end", text=item["name"], values=(item["name"],))
                self.tree.insert(node, "end", text="…")  # marcador para expandir

    def _on_open_node(self, _evt=None):
        node = self.tree.focus()
        if not node:
            return

        bucket = self.cb_bucket.get()
        prefix = self._node_to_path(node)

        # Limpa filhos
        for c in self.tree.get_children(node):
            self.tree.delete(c)

        for item in self._list(bucket, prefix):
            if item.get("id") == "folder" or item.get("name", "").endswith("/"):
                child = self.tree.insert(node, "end", text=item["name"], values=(item["name"],))
                self.tree.insert(child, "end", text="…")  # expansível

    def _node_to_path(self, node):
        parts = []
        cur = node
        while cur:
            parent = self.tree.parent(cur)
            text = self.tree.item(cur, "text")
            if text and text != "…":
                parts.append(text)
            cur = parent
        parts.reverse()
        path = "/".join(p.strip("/") for p in parts if p)
        return path.strip("/")

    def _on_double_click(self, _evt=None):
        # Duplo clique numa pasta -> seta no Entry prefix
        prefix = self._node_to_path(self.tree.focus())
        self.ent_prefix.delete(0, tk.END)
        self.ent_prefix.insert(0, prefix)

    def _list(self, bucket, prefix):
        try:
            # Lista com path no prefix
            res = self.supabase.storage.from_(bucket).list(
                path=prefix or "",
                limit=1000,
                offset=0,
                sort_by={"column": "name", "order": "asc"},
            )

            # Normaliza "pastas"
            folders = {}
            for it in res:
                name = it.get("name", "")
                if not name:
                    continue

                # Se houver '/', considere apenas a primeira parte como "pasta"
                if "/" in name:
                    top = name.split("/", 1)[0] + "/"
                    folders[top] = {"id": "folder", "name": top}
                elif name.endswith("/"):
                    folders[name] = {"id": "folder", "name": name}

            return list(folders.values())
        except Exception as e:
            log.warning("Erro ao listar pasta '%s' no bucket '%s': %s", prefix, bucket, e)
            return []


def enviar_para_supabase_avancado(parent, supabase_client) -> None:
    """
    Função principal para enviar arquivos/pastas para Supabase Storage.

    Args:
        parent: Janela pai (App ou Toplevel)
        supabase_client: Cliente Supabase configurado
    """
    if supabase_client is None:
        messagebox.showerror("Supabase", "Cliente Supabase não configurado.", parent=parent)
        return

    # 1) Escolha de arquivos (um ou vários). Se cancelar, oferecemos pasta.
    try:
        file_paths = filedialog.askopenfilenames(title="Selecione arquivo(s) para enviar ao Supabase", parent=parent)
    except Exception:
        file_paths = ()

    if not file_paths:
        if not messagebox.askyesno(
            "Enviar pasta",
            "Nenhum arquivo selecionado. Deseja enviar uma PASTA inteira?",
            parent=parent,
        ):
            return

        folder = filedialog.askdirectory(title="Escolha a PASTA para enviar ao Supabase", parent=parent)
        if not folder:
            return
        sources = ("folder", folder)
    else:
        sources = ("files", list(file_paths))

    # 2) Selecionar destino no Storage (bucket + prefix)
    dlg = StorageDestinationDialog(parent, supabase_client, title="Escolha o destino no Storage")
    parent.wait_window(dlg)
    if not dlg.result:
        return

    bucket, prefix = dlg.result

    # 3) Confirmação
    if sources[0] == "files":
        total = len(sources[1])
        resumo = "\n".join(os.path.basename(p) for p in sources[1][:5])
        if total > 5:
            resumo += f"\n... e +{total - 5} arquivo(s)"
    else:
        total = sum(len(files) for _, _, files in os.walk(sources[1]))
        resumo = f"Pasta: {os.path.basename(sources[1])} (≈{total} arquivos)"

    if not messagebox.askyesno(
        "Confirmar envio",
        f"Destino: {bucket}/{prefix or '(raiz)'}\nItens: {total}\n\nProsseguir com o envio?",
        parent=parent,
    ):
        return

    # 4) Janela de progresso
    prog = tk.Toplevel(parent)
    prog.title("Aguarde…")
    prog.resizable(False, False)
    prog.transient(parent)
    prog.grab_set()

    ttk.Label(prog, text="Enviando arquivos para o Supabase...").grid(row=0, column=0, padx=16, pady=(16, 8))
    pb = ttk.Progressbar(prog, length=360, mode="determinate", maximum=max(total, 1))
    pb.grid(row=1, column=0, padx=16, pady=(0, 16))

    # Centralizar
    prog.update_idletasks()
    w = prog.winfo_width()
    h = prog.winfo_height()
    x = (prog.winfo_screenwidth() - w) // 2
    y = (prog.winfo_screenheight() - h) // 2
    prog.geometry(f"+{x}+{y}")

    prog.update_idletasks()

    def _upload():
        ok, fail = 0, 0
        errors: List[str] = []

        def _upload_file(local_path, remote_rel):
            nonlocal ok, fail
            try:
                remote_path = posixpath.join(prefix, remote_rel).strip("/") if prefix else remote_rel.strip("/")
                content_type = mimetypes.guess_type(local_path)[0] or "application/octet-stream"

                with open(local_path, "rb") as fh:
                    supabase_client.storage.from_(bucket).upload(
                        path=remote_path,
                        file=fh,
                        file_options={"content-type": content_type, "upsert": "true"},
                    )
                ok += 1
                log.info("Upload OK: %s -> %s/%s", local_path, bucket, remote_path)
            except Exception as e:
                fail += 1
                error_msg = f"{os.path.basename(local_path)}: {str(e)[:100]}"
                errors.append(error_msg)
                log.error("Erro ao enviar %s: %s", local_path, e)

            pb.step(1)
            try:
                prog.update_idletasks()
            except Exception:
                pass

        if sources[0] == "files":
            for p in sources[1]:
                _upload_file(p, os.path.basename(p))
        else:
            root_folder = sources[1]
            for r, _dirs, files in os.walk(root_folder):
                for f in files:
                    lp = os.path.join(r, f)
                    rel = os.path.relpath(lp, root_folder).replace("\\", "/")
                    _upload_file(lp, rel)

        try:
            prog.destroy()
        except Exception:
            pass

        # Inserção opcional em tabela 'documents' (ignorar se schema não tiver user_id)
        # NOTA: Remova ou ajuste este bloco conforme seu schema
        try:
            # Exemplo (comentado para não causar erro):
            # supabase_client.table("documents").insert({
            #     "file_count": ok,
            #     "bucket": bucket,
            #     "prefix": prefix
            # }).execute()
            pass
        except Exception as e:
            # Não interrompe o fluxo por causa de schema (ex.: 'user_id' inexistente)
            log.warning("Erro ao inserir metadados em 'documents': %s", e)

        if fail == 0:
            messagebox.showinfo("Supabase", f"Envio concluído: {ok} arquivo(s).", parent=parent)
        else:
            error_detail = "\n".join(errors[:5])
            if len(errors) > 5:
                error_detail += f"\n... e mais {len(errors) - 5} erro(s)"
            messagebox.showwarning(
                "Supabase",
                f"Envio finalizado: {ok} OK, {fail} falha(s).\n\nErros:\n{error_detail}",
                parent=parent,
            )

    threading.Thread(target=_upload, daemon=True).start()
