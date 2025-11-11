"""View principal do módulo Auditoria."""
from __future__ import annotations

import os
import re
import tkinter as tk
import unicodedata
from tkinter import messagebox
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from ttkbootstrap import ttk

try:
    from infra.supabase_client import get_supabase  # type: ignore[import-untyped]
except Exception:
    def get_supabase():  # type: ignore[no-redef]
        return None

OFFLINE_MSG = "Recurso on-line. Verifique internet e credenciais do Supabase."

# === Storage config ===
STO_BUCKET = os.getenv("RC_STORAGE_BUCKET_CLIENTS", "").strip()
STO_CLIENT_FOLDER_FMT = os.getenv("RC_STORAGE_CLIENTS_FOLDER_FMT", "{client_id}").strip() or "{client_id}"


class AuditoriaFrame(ttk.Frame):
    """
    Tela de Auditoria:
      - Combobox para escolher Cliente
      - Botão 'Iniciar auditoria' (insere em public.auditorias)
      - Tabela com auditorias (cliente, status, criado/atualizado)

    Não altera nenhuma lógica global; funciona isolada.
    """

    def __init__(
        self,
        master: tk.Misc,
        go_back: Callable[[], None] | None = None,
        **kwargs
    ) -> None:
        """
        Inicializa a tela de Auditoria.

        Args:
            master: Widget pai (Tk ou Frame)
            go_back: Callback para voltar ao Hub (opcional)
            **kwargs: Argumentos adicionais para ttk.Frame
        """
        super().__init__(master, **kwargs)
        self._sb = get_supabase()
        self._go_back = go_back

        self._search_var = tk.StringVar()
        self._clientes: list[tuple[int, str]] = []  # [(id BIGINT, label)] - filtrada
        self._clientes_all: list[tuple[int, str]] = []  # lista completa (id, label)
        self._clientes_all_rows: list[dict] = []  # linhas cruas p/ busca (todos os campos)
        self._clientes_map: dict[int, str] = {}  # {id: label}
        self._cliente_var = tk.StringVar()

        self._build_ui()
        self.after(100, self._lazy_load)

    # ---------- UI ----------
    def _build_ui(self) -> None:
        """Constrói a interface da tela."""
        self.columnconfigure(0, weight=0)  # painel esquerdo
        self.columnconfigure(1, weight=1)  # centro (tabela)
        self.rowconfigure(1, weight=1)

        # Título
        title = ttk.Label(
            self,
            text="Auditoria",
            font=("-size", 16, "-weight", "bold")
        )
        title.grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(10, 6))

        # Painel esquerdo (filtros/ações)
        left = ttk.Frame(self)
        left.grid(row=1, column=0, sticky="nsw", padx=12, pady=8)
        left.columnconfigure(0, weight=1)

        # --- BUSCAR ---
        ttk.Label(left, text="Buscar cliente:").grid(row=0, column=0, sticky="w")
        self.ent_busca = ttk.Entry(left, textvariable=self._search_var, width=40)
        self.ent_busca.grid(row=1, column=0, sticky="ew", pady=(2, 6))
        btn_clear = ttk.Button(left, text="Limpar", command=lambda: self._clear_search())
        btn_clear.grid(row=2, column=0, sticky="ew", pady=(0, 10))

        # --- COMBOBOX DE CLIENTE ---
        ttk.Label(left, text="Cliente para auditoria:").grid(row=3, column=0, sticky="w")
        self.cmb_cliente = ttk.Combobox(left, textvariable=self._cliente_var, state="readonly", width=40)
        self.cmb_cliente.grid(row=4, column=0, sticky="ew", pady=(2, 8))
        self.lbl_notfound = ttk.Label(left, text="", foreground="#a33")
        self.lbl_notfound.grid(row=5, column=0, sticky="w", pady=(0, 8))

        btns = ttk.Frame(left)
        btns.grid(row=6, column=0, sticky="ew", pady=(0, 8))
        btns.columnconfigure((0, 1), weight=1)

        self.btn_iniciar = ttk.Button(btns, text="Iniciar auditoria", command=self._on_iniciar)
        self.btn_iniciar.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.btn_refresh = ttk.Button(btns, text="Atualizar lista", command=self._load_clientes)
        self.btn_refresh.grid(row=0, column=1, sticky="ew")

        if self._go_back:
            ttk.Button(left, text="Voltar", command=self._go_back).grid(row=7, column=0, sticky="ew")

        # Centro: tabela
        center = ttk.Frame(self)
        center.grid(row=1, column=1, sticky="nsew", padx=(8, 12), pady=8)
        center.rowconfigure(1, weight=1)
        center.columnconfigure(0, weight=1)

        # Header com label + toolbar
        header = ttk.Frame(center)
        header.grid(row=0, column=0, sticky="ew", padx=(6, 6), pady=(4, 6))
        header.grid_columnconfigure(0, weight=1)
        
        ttk.Label(header, text="Auditorias recentes").grid(row=0, column=0, sticky="w")
        
        self._btn_h_ver = ttk.Button(header, text="Ver subpastas", command=self._open_subpastas)
        self._btn_h_criar = ttk.Button(header, text="Criar pasta Auditoria", command=self._create_auditoria_folder)
        self._btn_h_ver.grid(row=0, column=1, padx=(8, 4))
        self._btn_h_criar.grid(row=0, column=2)

        self.tree = ttk.Treeview(
            center,
            columns=("cliente", "status", "created", "updated"),
            show="headings",
            height=16
        )
        self.tree.heading("cliente", text="Cliente")
        self.tree.heading("status", text="Status")
        self.tree.heading("created", text="Criado em")
        self.tree.heading("updated", text="Atualizado em")
        self.tree.column("cliente", width=320, anchor="w")
        self.tree.column("status", width=120, anchor="center")
        self.tree.column("created", width=140, anchor="center")
        self.tree.column("updated", width=140, anchor="center")
        self.tree.grid(row=1, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(center, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.lbl_offline = ttk.Label(center, text=OFFLINE_MSG, foreground="#666")
        self.lbl_offline.grid(row=2, column=0, sticky="w", pady=(6, 0))

    # ---------- Search Helpers ----------
    def _normalize(self, s: str) -> str:
        """Normaliza texto para busca (remove acentos, lowercase, só alfanum)."""
        s = s or ""
        s = unicodedata.normalize("NFKD", s)
        s = "".join(c for c in s if not unicodedata.combining(c))
        s = s.lower()
        return re.sub(r"[^a-z0-9]+", " ", s).strip()

    def _clear_search(self) -> None:
        """Limpa campo de busca."""
        self._search_var.set("")

    def _apply_filter(self) -> None:
        """Aplica filtro de busca nos clientes."""
        q = self._normalize(self._search_var.get())
        if not self._clientes_all:
            self.cmb_cliente["values"] = []
            self.cmb_cliente.set("")
            self.lbl_notfound.configure(text="Nenhum cliente encontrado")
            return

        if not q:
            self._clientes = list(self._clientes_all)
            values = [label for _id, label in self._clientes]
        else:
            tokens = q.split()
            filtered: list[tuple[int, str]] = []
            for row, item in zip(self._clientes_all_rows, self._clientes_all):
                hay = " ".join([
                    str(row.get("razao_social") or ""),
                    str(row.get("legal_name") or ""),
                    str(row.get("name") or ""),
                    str(row.get("display_name") or ""),
                    str(row.get("cnpj") or row.get("tax_id") or ""),
                    str(row.get("phone") or row.get("telefone") or ""),
                    str(row.get("celular") or row.get("mobile") or ""),
                    str(row.get("id") or "")
                ])
                hay_norm = self._normalize(hay)
                if all(t in hay_norm for t in tokens):
                    filtered.append(item)

            self._clientes = filtered
            values = [label for _id, label in filtered]

        self.cmb_cliente["values"] = values
        if values:
            self.cmb_cliente.current(0)
            self.lbl_notfound.configure(text="")
        else:
            self.cmb_cliente.set("")
            self.lbl_notfound.configure(text="Nenhum cliente encontrado")

    # ---------- Storage Helpers ----------
    def _client_storage_base(self, client_id: int | str) -> str:
        """Monta o prefixo do Storage para um cliente."""
        try:
            cid = int(client_id)
        except Exception:
            cid = client_id
        return STO_CLIENT_FOLDER_FMT.format(client_id=cid)

    def _require_storage_ready(self) -> bool:
        """Valida se storage está configurado/online."""
        if not self._sb:
            messagebox.showwarning("Storage", "Modo offline: sem Supabase inicializado.")
            return False
        if not STO_BUCKET:
            messagebox.showwarning("Storage", "Defina RC_STORAGE_BUCKET_CLIENTS no .env (bucket de clientes).")
            return False
        return True

    def _selected_client_id(self) -> Optional[int]:
        """Retorna o id do cliente atualmente selecionado no combobox."""
        try:
            idx = self.cmb_cliente.current()
            if idx is None or idx < 0:
                return None
            cid = self._clientes[idx][0]
            return int(cid)
        except Exception:
            return None

    # ---------- Loaders ----------
    def _lazy_load(self) -> None:
        """Carrega dados após inicialização da UI."""
        if not self._sb:
            self._set_offline(True)
            return
        self._set_offline(False)

        # rastrear digitação no campo de busca
        try:
            self._search_var.trace_add("write", lambda *args: self._apply_filter())
        except Exception:
            pass

        self._load_clientes()
        self._load_auditorias()

    def _set_offline(self, is_offline: bool) -> None:
        """
        Configura estado offline/online da tela.

        Args:
            is_offline: True se offline, False se online
        """
        state = "disabled" if is_offline else "normal"
        self.ent_busca.configure(state=state)
        self.cmb_cliente.configure(state="disabled" if is_offline else "readonly")
        self.btn_iniciar.configure(state=state)
        self.btn_refresh.configure(state=state)

        # Botões de storage (header direita)
        for w in (
            getattr(self, "_btn_h_ver", None),
            getattr(self, "_btn_h_criar", None)
        ):
            if w:
                w.configure(state=state)

        self.lbl_offline.configure(text=OFFLINE_MSG if is_offline else "")

    def _load_clientes(self) -> None:
        """Carrega lista de clientes do Supabase e preenche índice de busca."""
        if not self._sb:
            return

        try:
            res = (
                self._sb.table("clients")
                .select("*")
                .order("id")
                .execute()
            )
            data = getattr(res, "data", []) or []

            self._clientes_all = []
            self._clientes_all_rows = data
            self._clientes_map = {}

            tmp_list = []
            for row in data:
                try:
                    cid = int(row.get("id"))
                except Exception:
                    cid = row.get("id")  # type: ignore[assignment]
                nome = (
                    row.get("razao_social")
                    or row.get("legal_name")
                    or row.get("name")
                    or row.get("display_name")
                    or f"Cliente {cid}"
                )
                cnpj = row.get("cnpj") or row.get("tax_id") or ""
                label = f"{nome} — {cnpj}" if cnpj else nome
                tmp_list.append((cid, label))
                self._clientes_map[cid] = label

            self._clientes_all = tmp_list
            # aplica o filtro atual (se houver texto digitado)
            self._apply_filter()

        except Exception as e:
            messagebox.showwarning(
                "Clientes",
                f"Não foi possível carregar os clientes.\n{e}"
            )

    def _load_auditorias(self) -> None:
        """
        Carrega lista de auditorias do Supabase.

        Monta o nome do cliente via self._clientes_map, sem usar embed FK.
        """
        if not self._sb:
            return

        try:
            res = (
                self._sb.table("auditorias")
                .select("id, status, created_at, updated_at, cliente_id")
                .order("created_at", desc=True)
                .execute()
            )
            rows = getattr(res, "data", []) or []
            self.tree.delete(*self.tree.get_children())

            for r in rows:
                # Busca nome do cliente via mapa em memória
                cliente_id = r.get("cliente_id")
                if cliente_id is not None:
                    try:
                        cid = int(cliente_id)
                        cliente_nome = self._clientes_map.get(cid, f"#{cid}")
                    except (ValueError, TypeError):
                        cliente_nome = str(cliente_id)
                else:
                    cliente_nome = ""

                # Formata timestamps (remove T e microssegundos)
                created = (r.get("created_at") or "")[:19].replace("T", " ")
                updated = (r.get("updated_at") or "")[:19].replace("T", " ")

                self.tree.insert(
                    "",
                    "end",
                    iid=r["id"],
                    values=(cliente_nome, r.get("status", ""), created, updated)
                )
        except Exception as e:
            messagebox.showwarning(
                "Auditorias",
                f"Falha ao carregar auditorias.\n{e}"
            )

    # ---------- Actions ----------
    def _on_iniciar(self) -> None:
        """Handler do botão 'Iniciar auditoria'."""
        if not self._sb:
            return

        idx = self.cmb_cliente.current()
        if idx < 0 or idx >= len(self._clientes):
            messagebox.showinfo("Auditoria", "Selecione um cliente.")
            return

        cliente_id = int(self._clientes[idx][0])

        try:
            ins = (
                self._sb.table("auditorias")
                .insert({"cliente_id": cliente_id, "status": "em_andamento"})
                .execute()
            )
            if getattr(ins, "data", None):
                self._load_auditorias()
                messagebox.showinfo("Auditoria", "Auditoria iniciada com sucesso.")
        except Exception as e:
            messagebox.showerror(
                "Auditoria",
                f"Não foi possível iniciar a auditoria.\n{e}"
            )

    def _open_subpastas(self) -> None:
        """Abre a mesma janela de arquivos usada em Clientes."""
        if not self._sb:
            messagebox.showwarning("Storage", "Sem conexão com a nuvem.")
            return
        cid = self._selected_client_id()
        if cid is None:
            messagebox.showinfo("Storage", "Selecione um cliente.")
            return
        try:
            # Usa a MESMA janela dos Clientes (com todos os recursos)
            from src.shared.storage_ui_bridge import open_client_files_window
            open_client_files_window(self, self._sb, int(cid))
        except Exception as e:
            messagebox.showwarning("Storage", f"Falhou ao abrir subpastas.\n{e}")

    def _create_auditoria_folder(self) -> None:
        """Cria a pasta 'GERAL/Auditoria' no Storage do cliente."""
        if not self._sb:
            messagebox.showwarning("Criar pasta", "Sem conexão com a nuvem.")
            return
        cid = self._selected_client_id()
        if cid is None:
            messagebox.showinfo("Criar pasta", "Selecione um cliente.")
            return

        try:
            # Reutiliza helpers do módulo de arquivos dos Clientes
            from src.shared.storage_ui_bridge import (
                get_clients_bucket,
                client_prefix_for_id,
                _get_org_id_from_supabase
            )

            bucket = get_clients_bucket()  # ex.: 'rc-docs'
            org_id = _get_org_id_from_supabase(self._sb) or ""  # mesmo org usado nos Clientes
            base = client_prefix_for_id(int(cid), org_id)  # ex.: '<ORG>/<CLIENTE>'
            target = f"{base}/GERAL/Auditoria/.keep"

            # Upload do placeholder
            resp = self._sb.storage.from_(bucket).upload(  # type: ignore[union-attr]
                file=target,
                file_data=b"",
                file_options={"contentType": "text/plain", "upsert": False}
            )
            if getattr(resp, "error", None):
                raise RuntimeError(resp.error.get("message") or str(resp.error))  # type: ignore[union-attr]

            messagebox.showinfo("Criar pasta", "Pasta 'GERAL/Auditoria' criada com sucesso.")
        except Exception as e:
            messagebox.showwarning("Criar pasta", f"Falhou ao criar pasta.\n{e}")


class StorageBrowser(tk.Toplevel):
    """Navegador simples de subpastas no Storage (somente diretórios)."""

    def __init__(
        self,
        parent: tk.Misc,
        sb_client,  # type: ignore[no-untyped-def]
        bucket: str,
        base_prefix: str,
        title: str = "Subpastas"
    ) -> None:
        super().__init__(parent)
        self.title(title)
        self.geometry("720x420")
        self._sb = sb_client
        self._bucket = bucket
        self._stack: list[str] = [base_prefix.rstrip("/")]
        self._build_ui()
        self._load()

    def _build_ui(self) -> None:
        """Constrói a interface do navegador."""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky="ew", pady=(8, 6))
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="Caminho:").grid(row=0, column=0, sticky="w", padx=(8, 6))
        self.var_path = tk.StringVar(value=self._current_prefix())
        ent = ttk.Entry(top, textvariable=self.var_path, state="readonly")
        ent.grid(row=0, column=1, sticky="ew", padx=(0, 6))

        ttk.Button(top, text="Subir", command=self._go_up).grid(row=0, column=2, padx=(0, 8))

        self.tree = ttk.Treeview(self, columns=("tipo", "nome"), show="headings")
        self.tree.grid(row=1, column=0, sticky="nsew", padx=8)
        self.tree.heading("tipo", text="Tipo")
        self.tree.heading("nome", text="Nome")
        self.tree.bind("<Double-1>", lambda e: self._enter_selected())

        btns = ttk.Frame(self)
        btns.grid(row=2, column=0, sticky="ew", pady=(6, 8))
        btns.columnconfigure(0, weight=1)
        ttk.Button(btns, text="Fechar", command=self.destroy).grid(row=0, column=0, padx=8, sticky="e")

    def _current_prefix(self) -> str:
        """Retorna o prefixo atual da navegação."""
        return self._stack[-1]

    def _go_up(self) -> None:
        """Navega para o diretório pai."""
        if len(self._stack) > 1:
            self._stack.pop()
            self.var_path.set(self._current_prefix())
            self._load()

    def _enter_selected(self) -> None:
        """Entra no diretório selecionado."""
        sel = self.tree.selection()
        if not sel:
            return
        item = self.tree.item(sel[0])
        values = item.get("values", ["", ""])
        if values[0] == "pasta":
            name = values[1]
            self._stack.append(f"{self._current_prefix().rstrip('/')}/{name}")
            self.var_path.set(self._current_prefix())
            self._load()

    def _list_dir(self, prefix: str) -> list[dict]:  # type: ignore[type-arg]
        """Lista diretórios no prefixo (paginação até 100 por chamada)."""
        out: list[dict] = []  # type: ignore[type-arg]
        offset = 0
        while True:
            resp = self._sb.storage.from_(self._bucket).list(prefix, limit=100, offset=offset)
            data = getattr(resp, "data", []) or []
            out.extend(data)
            if len(data) < 100:
                break
            offset += 100
        return out

    def _load(self) -> None:
        """Carrega e exibe os diretórios do prefixo atual."""
        self.tree.delete(*self.tree.get_children())
        prefix = self._current_prefix().rstrip("/")
        try:
            entries = self._list_dir(prefix)
            # Em Storage, "pasta" é item com metadata == None (placeholder) e/ou itens sem '.'
            dirs = [e for e in entries if e.get("metadata") is None]
            for d in dirs:
                self.tree.insert("", "end", values=("pasta", d.get("name", "")))
        except Exception as e:
            messagebox.showwarning("Storage", f"Falha ao listar pastas.\n{e}")
