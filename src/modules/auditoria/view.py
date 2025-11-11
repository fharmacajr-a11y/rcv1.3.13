"""View principal do módulo Auditoria."""
from __future__ import annotations

import io
import mimetypes
import os
import re
import tempfile
import tkinter as tk
import unicodedata
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path, PurePosixPath
from tkinter import messagebox
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from ttkbootstrap import ttk

from src.ui import files_browser as fb
from src.ui.dialogs.file_select import select_archive_file, validate_archive_extension
from infra.archive_utils import extract_archive, ArchiveError

try:
    from infra.supabase_client import get_supabase  # type: ignore[import-untyped]
except Exception:
    def get_supabase():  # type: ignore[no-redef]
        return None

try:
    from src.ui.files_browser import format_cnpj_for_display  # type: ignore[import-untyped]
except Exception:
    def format_cnpj_for_display(cnpj: str) -> str:  # fallback defensivo
        c = ''.join(filter(str.isdigit, cnpj or ''))
        return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:14]}" if len(c) == 14 else (cnpj or "")

OFFLINE_MSG = "Recurso on-line. Verifique internet e credenciais do Supabase."

# === Storage config ===
STO_BUCKET = os.getenv("RC_STORAGE_BUCKET_CLIENTS", "").strip()
STO_CLIENT_FOLDER_FMT = os.getenv("RC_STORAGE_CLIENTS_FOLDER_FMT", "{client_id}").strip() or "{client_id}"


def _guess_mime(path: str) -> str:
    """Detecta MIME type de um arquivo pelo nome/extensão."""
    # Mapeamento explícito para extensões de arquivo compactado
    ext = path.lower().rsplit(".", 1)[-1] if "." in path else ""
    if ext == "7z" or ".7z." in path.lower():  # .7z ou volumes .7z.001
        return "application/x-7z-compressed"
    elif ext == "zip":
        return "application/zip"
    elif ext == "rar":
        return "application/x-rar-compressed"
    
    # Fallback para mimetypes
    mt, _ = mimetypes.guess_type(path)
    return mt or "application/octet-stream"


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

        # Índice de auditorias: {iid: {db_id, auditoria_id, cliente_nome, cnpj, ...}}
        self._aud_index: dict[str, dict] = {}

        # Rastreio de janelas "Ver subpastas" abertas por auditoria_id (chave string)
        self._open_browsers: dict[str, tk.Toplevel] = {}

        # Org ID do usuário logado (cache)
        self._org_id: str = ""

        self._build_ui()
        self.after(100, self._lazy_load)    # ---------- UI ----------
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

        self._btn_h_ver = ttk.Button(header, text="Ver subpastas", command=self._open_subpastas, state="disabled")
        # Botão desativado (upload com upsert já cria as pastas necessárias)
        # self._btn_h_criar = ttk.Button(header, text="Criar pasta Auditoria", command=self._create_auditoria_folder)
        self._btn_h_enviar_zip = ttk.Button(header, text="Enviar ZIP/RAR/7Z p/ Auditoria", command=self._upload_archive_to_auditoria)
        self._btn_h_delete = ttk.Button(header, text="Excluir auditoria(s)", command=self._delete_auditorias, state="disabled")

        self._btn_h_ver.grid(row=0, column=1, padx=(8, 4))
        # self._btn_h_criar.grid(row=0, column=2, padx=(4, 4))
        self._btn_h_enviar_zip.grid(row=0, column=2, padx=(4, 4))
        self._btn_h_delete.grid(row=0, column=3, padx=(4, 6))

        self.tree = ttk.Treeview(
            center,
            columns=("cliente", "status", "created", "updated"),
            show="headings",
            selectmode="extended",
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

        # Bind para habilitar/desabilitar botão Ver subpastas
        self.tree.bind("<<TreeviewSelect>>", self._on_auditoria_select)

        scrollbar = ttk.Scrollbar(center, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.lbl_offline = ttk.Label(center, text=OFFLINE_MSG, foreground="#666")
        self.lbl_offline.grid(row=2, column=0, sticky="w", pady=(6, 0))

    # ---------- Search Helpers ----------
    def _normalize(self, s: str) -> str:
        """Normaliza texto para busca (remove acentos, casefold, só alfanum)."""
        s = s or ""
        # Remove acentos (decomposição Unicode)
        s = unicodedata.normalize("NFKD", s)
        s = "".join(c for c in s if not unicodedata.combining(c))
        # casefold() é mais robusto que lower() para comparações i18n
        s = s.casefold()
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
            # getattr(self, "_btn_h_criar", None),  # botão comentado
            getattr(self, "_btn_h_enviar_zip", None)
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
        Popula self._aud_index para rastreamento de IDs.
        """
        if not self._sb:
            return

        try:
            # Limpa índice anterior
            self._aud_index.clear()

            res = (
                self._sb.table("auditorias")
                .select("id, cliente_id, status, created_at, updated_at")
                .order("updated_at", desc=True)
                .execute()
            )
            rows = getattr(res, "data", []) or []
            self.tree.delete(*self.tree.get_children())

            for r in rows:
                # Busca nome do cliente via mapa em memória
                cliente_id = r.get("cliente_id")
                cnpj = ""
                if cliente_id is not None:
                    try:
                        cid = int(cliente_id)
                        cliente_nome = self._clientes_map.get(cid, f"#{cid}")
                        # Busca CNPJ do cliente
                        for row_data in self._clientes_all_rows:
                            if row_data.get("id") == cid:
                                cnpj = row_data.get("cnpj", "")
                                break
                    except (ValueError, TypeError):
                        cliente_nome = str(cliente_id)
                        cid = 0
                else:
                    cliente_nome = ""
                    cid = 0

                # Formata timestamps (remove T e microssegundos)
                created = (r.get("created_at") or "")[:19].replace("T", " ")
                updated = (r.get("updated_at") or "")[:19].replace("T", " ")

                # IID = string do id (sempre disponível)
                iid = str(r["id"])

                # Popula índice de auditoria
                self._aud_index[iid] = {
                    "db_id": r["id"],  # ID inteiro para DELETE
                    "cliente_id": cid,
                    "cliente_nome": cliente_nome,
                    "cnpj": cnpj,
                    "status": r.get("status", ""),
                    "created_at": created,
                    "updated_at": updated
                }

                self.tree.insert(
                    "",
                    "end",
                    iid=iid,
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

    def _on_auditoria_select(self, event=None) -> None:  # type: ignore[no-untyped-def]
        """Handler de seleção na Treeview de auditorias. Habilita/desabilita botões Ver subpastas e Excluir."""
        sel = self.tree.selection()
        if sel and sel[0] in self._aud_index:
            self._btn_h_ver.configure(state="normal")
        else:
            self._btn_h_ver.configure(state="disabled")

        # Habilita botão Excluir se houver seleção
        if sel:
            self._btn_h_delete.configure(state="normal")
        else:
            self._btn_h_delete.configure(state="disabled")

    def _delete_auditorias(self) -> None:
        """Exclui as auditorias selecionadas da tabela (não remove arquivos do Storage)."""
        if not self._sb:
            messagebox.showwarning("Auditoria", "Sem conexão com o banco de dados.")
            return

        sels = list(self.tree.selection())
        if not sels:
            messagebox.showwarning("Atenção", "Selecione uma ou mais auditorias para excluir.")
            return

        # Extrai db_ids usando list comprehension
        ids = [self._aud_index[i]["db_id"] for i in sels if i in self._aud_index]

        if not ids:
            messagebox.showwarning("Atenção", "Nenhuma auditoria válida selecionada.")
            return

        # Coleta nomes para confirmação
        nomes = [self._aud_index[i]["cliente_nome"] for i in sels if i in self._aud_index]
        lista_nomes = "\n".join(nomes[:5]) + ("..." if len(nomes) > 5 else "")

        if not messagebox.askyesno(
            "Confirmar exclusão",
            f"Excluir {len(ids)} auditoria(s)?\n\n{lista_nomes}",
            parent=self
        ):
            return

        try:
            # DELETE em lote usando .in_() com db_id (int)
            self._sb.table("auditorias").delete().in_("id", ids).execute()
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao excluir: {e}", parent=self)
            return

        # Atualiza UI local (remoção otimista)
        for iid in sels:
            self.tree.delete(iid)
            self._aud_index.pop(iid, None)

        # Desabilita botões
        self._btn_h_ver.configure(state="disabled")
        self._btn_h_delete.configure(state="disabled")

        messagebox.showinfo("Pronto", f"{len(ids)} auditoria(s) excluída(s).", parent=self)

    def _open_subpastas(self) -> None:
        """
        Abre janela de arquivos da AUDITORIA SELECIONADA.
        Garante apenas 1 janela por auditoria (foca se já existe).
        """
        if not self._sb:
            messagebox.showwarning("Storage", "Sem conexão com a nuvem.")
            return

        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Atenção", "Selecione uma auditoria na lista.")
            return

        iid = sel[0]
        row = self._aud_index.get(iid)
        if not row:
            messagebox.showwarning("Atenção", "Nenhuma auditoria válida selecionada.")
            return

        # Usa iid diretamente como chave (já é string)
        aud_key = iid

        # Se já existe janela para esta auditoria, traz para frente
        win = self._open_browsers.get(aud_key)
        if win and win.winfo_exists():
            try:
                win.lift()
                win.attributes("-topmost", True)
                win.after(150, lambda: win.attributes("-topmost", False))
                win.focus_force()
            except Exception:
                pass
            return

        try:
            from src.ui.files_browser import open_files_browser, get_current_org_id

            # Cache org_id para reutilização
            if not self._org_id:
                self._org_id = get_current_org_id(self._sb)

            org_id = self._org_id
            client_id = row["cliente_id"]

            # Prefixo completo: {org_id}/{client_id}/GERAL/Auditoria
            prefix = f"{org_id}/{client_id}/GERAL/Auditoria"

            # Debug visual
            print(f"[AUDITORIA] Abrindo Storage - Prefixo: {prefix}")
            print(f"[AUDITORIA] Cliente: {row['cliente_nome']} (ID {client_id})")
            print(f"[AUDITORIA] Auditoria ID: {iid}")

            # Cria a janela com start_prefix para abrir diretamente na pasta Auditoria
            browser_win = open_files_browser(
                self,
                supabase=self._sb,
                client_id=client_id,
                org_id=org_id,
                razao=row["cliente_nome"],
                cnpj=row["cnpj"],
                start_prefix=prefix
            )

            # Registra janela
            if browser_win:
                self._open_browsers[aud_key] = browser_win

                def _on_close():
                    self._open_browsers.pop(aud_key, None)
                    browser_win.destroy()

                browser_win.protocol("WM_DELETE_WINDOW", _on_close)
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
            from src.ui.files_browser import (
                get_clients_bucket,
                client_prefix_for_id,
                get_current_org_id
            )

            bucket = get_clients_bucket()  # "rc-docs"
            org_id = get_current_org_id(self._sb)
            base = client_prefix_for_id(int(cid), org_id)  # "{org_id}/{client_id}"
            target = f"{base}/GERAL/Auditoria/.keep"

            # Upload do placeholder com API correta (upsert string para evitar 409)
            resp = self._sb.storage.from_(bucket).upload(  # type: ignore[union-attr]
                path=target,
                file=b"",
                file_options={"content-type": "text/plain", "upsert": "true"}
            )
            if hasattr(resp, "error") and resp.error:
                raise RuntimeError(getattr(resp.error, "message", str(resp.error)))

            messagebox.showinfo("Criar pasta", "Pasta 'GERAL/Auditoria' criada com sucesso.")
        except Exception as e:
            messagebox.showwarning("Criar pasta", f"Falhou ao criar pasta.\n{e}")

    def _auditoria_prefix(self, client_id: int) -> tuple[str, str]:
        """Retorna (bucket, base_prefix) para o cliente atual."""
        org_id = fb.get_current_org_id(self._sb)
        bucket = fb.get_clients_bucket()
        base = fb.client_prefix_for_id(client_id, org_id)  # ex: "{org_id}/{client_id}"
        return bucket, f"{base}/GERAL/Auditoria"

    def _upload_archive_to_auditoria(self) -> None:
        """Upload de arquivo .zip, .rar ou .7z para Auditoria preservando subpastas."""
        if not self._sb:
            messagebox.showwarning("Nuvem", "Sem conexão com o Supabase.")
            return

        # 1) Garantir auditoria selecionada
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Atenção", "Selecione uma auditoria na lista.")
            return

        iid = sel[0]
        row = self._aud_index.get(iid)
        if not row:
            messagebox.showwarning("Atenção", "Nenhuma auditoria válida selecionada.")
            return

        # Cache org_id se necessário
        if not self._org_id:
            from src.ui.files_browser import get_current_org_id
            self._org_id = get_current_org_id(self._sb)

        org_id = self._org_id
        client_id = row["cliente_id"]
        cliente_nome = row["cliente_nome"]
        cnpj = row.get("cnpj", "")
        bucket = "rc-docs"
        base_prefix = f"{org_id}/{client_id}/GERAL/Auditoria".strip("/")

        # 2) Escolher arquivo .zip, .rar ou .7z
        path = select_archive_file(title="Selecione arquivo .ZIP, .RAR ou .7Z (volumes: selecione .7z.001)")
        if not path:
            return

        # Validar extensão usando função centralizada
        from infra.archive_utils import is_supported_archive
        if not is_supported_archive(path):
            messagebox.showwarning(
                "Arquivo não suportado",
                "Formato não suportado. Selecione um arquivo .zip, .rar ou .7z.\n"
                "Para volumes, selecione o arquivo .7z.001.\n"
                f"Arquivo selecionado: {Path(path).name}"
            )
            return

        # Detectar extensão (simplificado - detecta .7z ou volume .7z.001)
        path_lower = path.lower()
        is_7z_volume = ".7z." in path_lower and path_lower.split(".7z.")[-1].isdigit()
        
        if path_lower.endswith(".zip"):
            ext = "zip"
        elif path_lower.endswith(".rar"):
            ext = "rar"
        elif path_lower.endswith(".7z") or is_7z_volume:
            ext = "7z"
        else:
            ext = ""

        enviados = 0
        erro = None

        # 3) Estratégia baseada na extensão
        try:
            if ext == "zip":
                # ZIP: leitura direta de membros preservando estrutura
                with zipfile.ZipFile(path, "r") as zf:
                    for info in zf.infolist():
                        if info.is_dir():
                            continue
                        rel = info.filename.lstrip("/").replace("\\", "/")
                        # Segurança e limpeza
                        if not rel or rel.startswith((".", "__MACOSX")):
                            continue
                        if ".." in rel:
                            continue
                        # Upload mantendo subpastas
                        data = zf.read(info)
                        dest = f"{base_prefix}/{rel}".strip("/")
                        mime = _guess_mime(rel)
                        self._sb.storage.from_(bucket).upload(  # type: ignore[union-attr]
                            dest,
                            data,
                            {"content-type": mime, "upsert": "true", "cacheControl": "3600"}
                        )
                        enviados += 1

            elif ext == "rar":
                # RAR: extração temporária via 7-Zip + upload
                try:
                    with tempfile.TemporaryDirectory() as tmpdir:
                        # Extrai usando 7-Zip
                        extract_archive(path, tmpdir)

                        base = Path(tmpdir)
                        for f in base.rglob("*"):
                            if f.is_file():
                                rel = f.relative_to(base).as_posix()
                                # Segurança e limpeza
                                if not rel or rel.startswith((".", "__MACOSX")):
                                    continue
                                if ".." in rel:
                                    continue
                                dest = f"{base_prefix}/{rel}".strip("/")
                                mime = _guess_mime(f.name)
                                with open(f, "rb") as fh:
                                    self._sb.storage.from_(bucket).upload(  # type: ignore[union-attr]
                                        dest,
                                        fh.read(),
                                        {"content-type": mime, "upsert": "true", "cacheControl": "3600"}
                                    )
                                enviados += 1
                except ArchiveError as e:
                    messagebox.showerror(
                        "Erro ao extrair RAR",
                        f"Não foi possível extrair o arquivo RAR.\n\n{e}"
                    )
                    return

            elif ext == "7z":
                # 7Z: extração temporária via py7zr + upload (suporta senha e volumes)
                try:
                    with tempfile.TemporaryDirectory() as tmpdir:
                        # Extrai usando py7zr (suporta volumes .7z.001 automaticamente)
                        extract_archive(path, tmpdir)

                        base = Path(tmpdir)
                        for f in base.rglob("*"):
                            if f.is_file():
                                rel = f.relative_to(base).as_posix()
                                # Segurança e limpeza
                                if not rel or rel.startswith((".", "__MACOSX")):
                                    continue
                                if ".." in rel:
                                    continue
                                dest = f"{base_prefix}/{rel}".strip("/")
                                mime = _guess_mime(f.name)
                                with open(f, "rb") as fh:
                                    self._sb.storage.from_(bucket).upload(  # type: ignore[union-attr]
                                        dest,
                                        fh.read(),
                                        {"content-type": mime, "upsert": "true", "cacheControl": "3600"}
                                    )
                                enviados += 1
                except ArchiveError as e:
                    messagebox.showerror(
                        "Erro ao extrair 7Z",
                        f"Não foi possível extrair o arquivo .7z.\n\n{e}"
                    )
                    return

            else:
                # Nunca deve chegar aqui devido à validação anterior
                messagebox.showwarning(
                    "Atenção",
                    "Formato não suportado. Selecione um arquivo .zip, .rar ou .7z.\n"
                    "Para volumes, selecione o arquivo .7z.001."
                )
                return

        except ArchiveError as e:
            messagebox.showerror("Erro no arquivo", f"{e}")
            return
        except Exception as e:
            erro = e

        if erro:
            messagebox.showerror("Erro no upload", f"{erro}")
            return

        # Mensagem de sucesso com Razão Social + CNPJ formatado
        cnpj_fmt = format_cnpj_for_display(cnpj)
        messagebox.showinfo(
            "Auditoria",
            f"Upload concluído para {cliente_nome} — {cnpj_fmt}.\n"
            f"{enviados} arquivo(s) enviados para {base_prefix}/"
        )

        # Reabrir/atualizar browser para visualizar arquivos enviados
        try:
            from src.ui.files_browser import open_files_browser
            open_files_browser(
                self,
                supabase=self._sb,
                client_id=client_id,
                org_id=org_id,
                razao=cliente_nome,
                cnpj=cnpj,
                start_prefix=base_prefix
            )
        except Exception as e:
            print(f"[AUDITORIA][UPLOAD] Não foi possível abrir browser: {e}")



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
