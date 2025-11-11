"""View principal do módulo Auditoria."""
from __future__ import annotations

import io
import mimetypes
import os
import re
import tempfile
import threading
import time
import tkinter as tk
import unicodedata
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
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


# --- HELPERS DE BUSCA ROBUSTA ---

def _norm_text(s: str | None) -> str:
    """Remove acentos, faz casefold e trim; seguro para None."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s.casefold().strip()


def _digits(s: str | None) -> str:
    """Mantém só dígitos (CNPJ, telefones etc.)."""
    return re.sub(r"\D+", "", s or "")


def _collect_name_like_fields(row: dict) -> list[str]:  # type: ignore[type-arg]
    """
    Varre o dict e pega valores de chaves que parecem conter nomes de pessoas:
    'nome', 'contato', 'responsavel', 'representante', 'proprietario', etc.
    É tolerante a variações/capitalizações.
    """
    if not isinstance(row, dict):
        return []
    name_keys = []
    for k, v in row.items():
        kl = str(k).casefold()
        if any(tag in kl for tag in ("nome", "contat", "respons", "represent", "propriet", "socio", "sócio")):
            if isinstance(v, str) and v.strip():
                name_keys.append(v)
    return name_keys


def _build_search_index(row: dict) -> dict:  # type: ignore[type-arg]
    """
    Retorna um índice com textos prontos para busca:
    - 'razao': razão social normalizada
    - 'cnpj': apenas dígitos
    - 'nomes': lista de nomes de contato/responsável etc. (normalizados)
    """
    razao = _norm_text(row.get("razao_social") or row.get("Razao Social") or row.get("razao") or "")
    cnpj = _digits(row.get("cnpj") or row.get("CNPJ") or "")
    nomes = [_norm_text(x) for x in _collect_name_like_fields(row)]
    return {"razao": razao, "cnpj": cnpj, "nomes": nomes}


@dataclass
class _ProgressState:
    """Estado do progresso de upload para barra determinística."""
    total_files: int = 0
    total_bytes: int = 0
    done_files: int = 0
    done_bytes: int = 0
    start_ts: float = 0.0
    ema_bps: float = 0.0  # Exponential Moving Average de bytes por segundo


@dataclass
class _UploadPlan:
    """Plano de upload para um arquivo (com estratégia de duplicatas)."""
    source_path: Path  # Caminho local do arquivo
    dest_name: str     # Nome de destino no Storage
    upsert: bool       # True = substituir se existir, False = erro se existir
    file_size: int     # Tamanho em bytes


def _next_copy_name(name: str, existing: set[str]) -> str:
    """
    Gera nome com sufixo (2), (3), ... evitando colisão.

    Args:
        name: Nome original do arquivo (ex: "doc.pdf")
        existing: Set de nomes já existentes

    Returns:
        Nome sem colisão (ex: "doc (2).pdf")

    Example:
        >>> _next_copy_name("doc.pdf", {"doc.pdf", "doc (2).pdf"})
        'doc (3).pdf'
    """
    if name not in existing:
        return name

    # Separar nome e extensão
    stem = Path(name).stem
    suffix = Path(name).suffix

    # Tentar (2), (3), ... até encontrar disponível
    counter = 2
    while True:
        candidate = f"{stem} ({counter}){suffix}"
        if candidate not in existing:
            return candidate
        counter += 1


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

        # Bindings para busca e seleção
        def _on_busca_key(event=None):  # type: ignore[no-untyped-def]
            if hasattr(self, "_busca_after") and self._busca_after:
                try:
                    self.after_cancel(self._busca_after)
                except Exception:
                    pass
            self._busca_after = self.after(140, lambda: self._filtra_clientes(self.ent_busca.get()))

        self.ent_busca.bind("<KeyRelease>", _on_busca_key)

        def _on_select_cliente(event=None):  # type: ignore[no-untyped-def]
            label = self.cmb_cliente.get()
            self._cliente_selecionado = self._label2cliente.get(label) if hasattr(self, "_label2cliente") else None

        self.cmb_cliente.bind("<<ComboboxSelected>>", _on_select_cliente)

        # Inicializa variáveis
        self._busca_after: str | None = None
        self._label2cliente: dict[str, dict] = {}  # type: ignore[type-arg]
        self._cliente_selecionado: dict | None = None  # type: ignore[type-arg]

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

    def _filtra_clientes(self, query: str) -> None:
        """Filtra por razão, nomes (contato/responsável/representante) e CNPJ (com/sem máscara)."""
        q_text = _norm_text(query)
        q_digits = _digits(query)

        base: list[dict] = getattr(self, "_clientes_all_rows", []) or []  # type: ignore[type-arg]

        filtrados: list[dict] = []  # type: ignore[type-arg]
        for cli in base:
            idx = _build_search_index(cli)
            # 1) Se o usuário digitou CNPJ (>= 5 dígitos), priorize match numérico
            if len(q_digits) >= 5 and q_digits in idx["cnpj"]:
                filtrados.append(cli)
                continue
            # 2) Match textual em razão social e nomes de contato
            if q_text and (
                q_text in idx["razao"]
                or any(q_text in nome for nome in idx["nomes"])
            ):
                filtrados.append(cli)
                continue
            # 3) Query vazia -> mantém tudo
            if not q_text and not q_digits:
                filtrados = base
                break

        # monta labels e mapa label->obj
        labels = [
            f"{c.get('razao_social') or c.get('Razao Social') or 'Cliente'} — {c.get('cnpj') or ''}"
            for c in filtrados
        ]

        # Mapeia cliente_id para cada label
        self._clientes = []
        for c in filtrados:
            try:
                cid = int(c.get("id", 0))
            except (ValueError, TypeError):
                cid = 0
            idx = filtrados.index(c)
            if idx < len(labels):
                self._clientes.append((cid, labels[idx]))

        # Mapa label->cliente completo
        self._label2cliente = {labels[i]: filtrados[i] for i in range(len(labels))}

        # atualiza combobox
        try:
            self.cmb_cliente.configure(values=labels, state="readonly")
        except Exception:
            # fallback se a combobox ainda não existir no momento da chamada
            return

        if labels:
            # pré-seleciona 1º resultado
            self.cmb_cliente.set(labels[0])
            if hasattr(self, "lbl_notfound"):
                self.lbl_notfound.configure(text="")
        else:
            self.cmb_cliente.set("")
            if hasattr(self, "lbl_notfound"):
                self.lbl_notfound.configure(text="Nenhum cliente encontrado")

    def _apply_filter(self) -> None:
        """Aplica filtro de busca nos clientes (compatibilidade)."""
        self._filtra_clientes(self._search_var.get())

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

    # ---------- Helper para progresso ----------
    def _fmt_eta(self, seconds: float) -> str:
        """Formata segundos em HH:MM:SS."""
        if seconds <= 0:
            return "00:00:00"
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def _list_existing_names(self, bucket: str, prefix: str) -> set[str]:
        """
        Lista nomes de arquivos existentes no Storage (com paginação).

        Args:
            bucket: Nome do bucket
            prefix: Prefixo/caminho da pasta (ex: "org_id/client_id/GERAL/Auditoria")

        Returns:
            Set de nomes de arquivos existentes
        """
        existing: set[str] = set()
        limit = 1000
        offset = 0

        try:
            while True:
                resp = self._sb.storage.from_(bucket).list(  # type: ignore[union-attr]
                    prefix,
                    {"limit": limit, "offset": offset}
                )

                if not resp:
                    break

                for item in resp:
                    if item.get("name"):
                        existing.add(item["name"])

                # Se retornou menos que o limit, acabou
                if len(resp) < limit:
                    break

                offset += limit
        except Exception:
            # Em caso de erro, retorna o que conseguiu até agora
            pass

        return existing

    def _fmt_bytes(self, bytes_val: int) -> str:
        """
        Formata bytes em formato legível (KB, MB, GB).

        Args:
            bytes_val: Valor em bytes

        Returns:
            String formatada (ex: "1.5 MB", "320 KB")
        """
        if bytes_val < 1024:
            return f"{bytes_val} B"
        elif bytes_val < 1_048_576:  # < 1 MB
            return f"{bytes_val / 1024:.1f} KB"
        elif bytes_val < 1_073_741_824:  # < 1 GB
            return f"{bytes_val / 1_048_576:.1f} MB"
        else:
            return f"{bytes_val / 1_073_741_824:.1f} GB"

    def _progress_update_ui(self, state: _ProgressState, alpha: float = 0.2) -> None:
        """
        Atualiza UI da barra de progresso com % por bytes, MB/s e ETA (thread-safe via after()).

        Args:
            state: Estado atual do progresso
            alpha: Fator de suavização EMA (0.2 = suave)
        """
        if not hasattr(self, "_pb") or not hasattr(self, "_busy"):
            return

        # Calcular velocidade instantânea
        elapsed = time.monotonic() - state.start_ts
        if elapsed > 0:
            instant_bps = state.done_bytes / elapsed
            # EMA para suavizar
            if state.ema_bps == 0:
                state.ema_bps = instant_bps
            else:
                state.ema_bps = alpha * instant_bps + (1 - alpha) * state.ema_bps

        # Calcular % e ETA
        pct = 0.0
        eta_str = "00:00:00"
        speed_str = "0.0 MB/s"
        bytes_str = "0 B / 0 B"

        if state.total_bytes > 0:
            pct = (state.done_bytes / state.total_bytes) * 100
            bytes_str = f"{self._fmt_bytes(state.done_bytes)} / {self._fmt_bytes(state.total_bytes)}"

            if state.ema_bps > 0:
                remaining_bytes = state.total_bytes - state.done_bytes
                eta_sec = remaining_bytes / state.ema_bps
                # Formatar ETA (mm:ss se < 1h, senão HH:MM:SS)
                if eta_sec < 3600:
                    m = int(eta_sec // 60)
                    s = int(eta_sec % 60)
                    eta_str = f"{m:02d}:{s:02d}"
                else:
                    eta_str = self._fmt_eta(eta_sec)
                speed_str = f"{state.ema_bps / 1_048_576:.1f} MB/s"

        # Atualizar barra
        self._pb["value"] = pct

        # Atualizar labels (se existirem)
        if hasattr(self, "_lbl_status"):
            status_text = f"{pct:.0f}% — {state.done_files}/{state.total_files} itens • {bytes_str}"
            self._lbl_status.configure(text=status_text)

        if hasattr(self, "_lbl_eta"):
            if eta_sec < 3600:
                eta_text = f"ETA ~ {eta_str} @ {speed_str}"
            else:
                eta_text = f"{eta_str} restantes @ {speed_str}"
            self._lbl_eta.configure(text=eta_text)

    # ---------- Modal de Progresso ----------
    def _show_busy(self, titulo: str, msg: str) -> None:
        """
        Mostra janela modal de progresso determinístico com %, MB/s, ETA e opção de cancelar.

        Args:
            titulo: Título da janela
            msg: Mensagem exibida
        """
        parent = self.winfo_toplevel()
        self._busy = tk.Toplevel(parent)
        self._busy.title(titulo)
        self._busy.transient(parent)
        self._busy.grab_set()  # bloqueia interação no pai
        self._busy.resizable(False, False)

        # Centralizar janela (ajustado para incluir labels de status/ETA)
        self._busy.update_idletasks()
        w = 420
        h = 220
        x = (self._busy.winfo_screenwidth() // 2) - (w // 2)
        y = (self._busy.winfo_screenheight() // 2) - (h // 2)
        self._busy.geometry(f"{w}x{h}+{x}+{y}")

        # Label de mensagem principal
        lbl = ttk.Label(self._busy, text=msg, font=("-size", 10))
        lbl.pack(padx=20, pady=(20, 12))

        # Progressbar determinística
        self._pb = ttk.Progressbar(self._busy, mode="determinate", length=360, maximum=100)
        self._pb.pack(padx=20, pady=(0, 8), fill="x")
        self._pb["value"] = 0

        # Label de status (% e itens)
        self._lbl_status = ttk.Label(self._busy, text="0% — 0/0 itens", font=("-size", 9))
        self._lbl_status.pack(padx=20, pady=(0, 4))

        # Label de ETA e velocidade
        self._lbl_eta = ttk.Label(self._busy, text="00:00:00 restantes @ 0.0 MB/s", font=("-size", 9), foreground="#666")
        self._lbl_eta.pack(padx=20, pady=(0, 16))

        self._cancel_flag = False

        def _cancel():
            self._cancel_flag = True
            btn_cancel.configure(state="disabled", text="Cancelando...")

        btn_cancel = ttk.Button(self._busy, text="Cancelar", command=_cancel)
        btn_cancel.pack(pady=(0, 20))

    def _close_busy(self) -> None:
        """Fecha a janela modal de progresso (se existir)."""
        try:
            if hasattr(self, "_busy") and self._busy:
                self._busy.destroy()
        except Exception:
            pass

    def _ask_rollback(self, uploaded_paths: list[str], bucket: str) -> None:
        """
        Pergunta ao usuário se deseja reverter arquivos já enviados após cancelamento.

        Args:
            uploaded_paths: Lista de caminhos completos dos arquivos enviados
            bucket: Nome do bucket
        """
        self._close_busy()

        if not uploaded_paths:
            messagebox.showinfo("Cancelado", "Upload cancelado. Nenhum arquivo foi enviado.")
            return

        msg = f"Upload cancelado.\n\n{len(uploaded_paths)} arquivo(s) já foram enviados.\n\nDeseja remover esses arquivos?"
        if messagebox.askyesno("Cancelar e Reverter", msg):
            # Lançar thread para remover arquivos
            def _do_rollback():
                try:
                    # Remover em lotes de 1000 (limite da API)
                    batch_size = 1000
                    for i in range(0, len(uploaded_paths), batch_size):
                        batch = uploaded_paths[i:i + batch_size]
                        self._sb.storage.from_(bucket).remove(batch)  # type: ignore[union-attr]

                    self.after(0, lambda: messagebox.showinfo(
                        "Revertido",
                        f"{len(uploaded_paths)} arquivo(s) removido(s) com sucesso."
                    ))
                except Exception as e:
                    self.after(0, lambda err=str(e): messagebox.showerror(
                        "Erro ao Reverter",
                        f"Falha ao remover arquivos:\n{err}"
                    ))

            threading.Thread(target=_do_rollback, daemon=True).start()
        else:
            messagebox.showinfo("Cancelado", "Upload cancelado. Arquivos já enviados foram mantidos.")

    def _busy_done(self, ok: int, fail: list[tuple[str, str]], base_prefix: str, cliente_nome: str, cnpj: str, client_id: int, org_id: str) -> None:
        """
        Callback de sucesso do upload (executado na thread principal via after()).

        Args:
            ok: Número de arquivos enviados com sucesso
            fail: Lista de falhas [(path, erro)]
            base_prefix: Prefixo do Storage onde foram enviados
            cliente_nome: Nome do cliente
            cnpj: CNPJ do cliente
            client_id: ID do cliente
            org_id: ID da organização
        """
        # FASE 1: Fechar modal primeiro
        self._close_busy()

        if self._cancel_flag:
            messagebox.showinfo("Upload cancelado", "O upload foi cancelado pelo usuário.")
            return

        cnpj_fmt = format_cnpj_for_display(cnpj)
        msg = f"Upload concluído para {cliente_nome} — {cnpj_fmt}.\n"
        msg += f"{ok} arquivo(s) enviado(s)."

        if fail:
            msg += f"\n\nFalhas: {len(fail)}"
            for path, err in fail[:3]:  # limita a 3 erros
                msg += f"\n• {Path(path).name}: {err}"
            if len(fail) > 3:
                msg += f"\n... e mais {len(fail) - 3} erro(s)"

        messagebox.showinfo("Auditoria", msg)

        # FASE 2: Reabrir browser após 50ms (finalização suave)
        def _refresh_browser():
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

        self.after(50, _refresh_browser)

    def _busy_fail(self, err: str) -> None:
        """
        Callback de erro do upload (executado na thread principal via after()).

        Args:
            err: Mensagem de erro
        """
        self._close_busy()
        messagebox.showerror("Erro no upload", f"Falha no envio:\n\n{err}")

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

        # 3) Mostrar modal de progresso
        self._show_busy("Processando arquivos", f"Enviando {Path(path).name}...")

        # 4) Lançar thread worker
        threading.Thread(
            target=self._worker_upload,
            args=(path, client_id, org_id, cliente_nome, cnpj),
            daemon=True
        ).start()

    def _worker_upload(
        self,
        archive_path: str,
        client_id: int,
        org_id: str,
        cliente_nome: str,
        cnpj: str
    ) -> None:
        """
        Worker thread para extrair e fazer upload de arquivos com:
        - Pré-check de duplicatas com diálogo de escolha
        - Tracking de arquivos enviados para reversão
        - Progresso determinístico por bytes
        - Cancelamento com opção de rollback

        Args:
            archive_path: Caminho do arquivo compactado
            client_id: ID do cliente
            org_id: ID da organização
            cliente_nome: Nome do cliente
            cnpj: CNPJ do cliente
        """
        bucket = "rc-docs"
        base_prefix = f"{org_id}/{client_id}/GERAL/Auditoria".strip("/")
        path = Path(archive_path)

        fail: list[tuple[str, str]] = []
        uploaded_paths: list[str] = []  # Para rollback em caso de cancelamento

        try:
            # Detectar extensão
            path_lower = str(path).lower()
            is_7z_volume = ".7z." in path_lower and path_lower.split(".7z.")[-1].isdigit()

            if path_lower.endswith(".zip"):
                ext = "zip"
            elif path_lower.endswith(".rar"):
                ext = "rar"
            elif path_lower.endswith(".7z") or is_7z_volume:
                ext = "7z"
            else:
                ext = ""

            if not ext:
                self.after(0, lambda: self._busy_fail("Formato não suportado"))
                return

            # ====== FASE 1: PRÉ-SCAN + MONTAGEM DE LISTA DE ARQUIVOS ======
            files_to_upload: list[tuple[str, int]] = []  # (rel_path, file_size)

            if ext == "zip":
                with zipfile.ZipFile(path, "r") as zf:
                    for info in zf.infolist():
                        if info.is_dir():
                            continue
                        rel = info.filename.lstrip("/").replace("\\", "/")
                        if not rel or rel.startswith((".", "__MACOSX")) or ".." in rel:
                            continue
                        files_to_upload.append((rel, info.file_size))

            elif ext in ("rar", "7z"):
                # RAR/7Z: extrai para tmpdir
                tmpdir_obj = tempfile.TemporaryDirectory()
                tmpdir = tmpdir_obj.name
                try:
                    extract_archive(path, tmpdir)
                except ArchiveError as e:
                    self.after(0, lambda err=str(e): self._busy_fail(f"Erro ao extrair: {err}"))
                    tmpdir_obj.cleanup()
                    return

                if self._cancel_flag:
                    tmpdir_obj.cleanup()
                    return

                base = Path(tmpdir)
                for f in base.rglob("*"):
                    if f.is_file():
                        rel = f.relative_to(base).as_posix()
                        if not rel or rel.startswith((".", "__MACOSX")) or ".." in rel:
                            continue
                        files_to_upload.append((rel, f.stat().st_size))

            # ====== FASE 2: PRÉ-CHECK DE DUPLICATAS ======
            existing_names = self._list_existing_names(bucket, base_prefix)
            file_names = {Path(rel).name for rel, _ in files_to_upload}
            duplicates_names = file_names & existing_names

            strategy = "skip"  # Padrão

            if duplicates_names:
                # Mostrar diálogo (thread-safe via after + wait)
                dialog_result: dict[str, str | None] = {"strategy": None}

                def _show_dup_dialog():
                    dlg = DuplicatesDialog(self, len(duplicates_names), sorted(duplicates_names))
                    self.wait_window(dlg)
                    dialog_result["strategy"] = dlg.strategy

                self.after(0, _show_dup_dialog)

                # Aguardar resposta (polling simples)
                while dialog_result["strategy"] is None:
                    time.sleep(0.05)
                    if self._cancel_flag:
                        if ext in ("rar", "7z"):
                            tmpdir_obj.cleanup()
                        return

                strategy = dialog_result["strategy"]

                if strategy is None:  # Cancelou
                    if ext in ("rar", "7z"):
                        tmpdir_obj.cleanup()
                    self.after(0, lambda: self._busy_fail("Upload cancelado pelo usuário"))
                    return

            # ====== FASE 3: MONTAR PLANO DE UPLOAD ======
            upload_plans: list[_UploadPlan] = []

            for rel, file_size in files_to_upload:
                file_name = Path(rel).name
                is_dup = file_name in duplicates_names

                if is_dup:
                    if strategy == "skip":
                        continue  # Não adiciona ao plano
                    elif strategy == "replace":
                        # Substituir: usar nome original com upsert=True
                        upload_plans.append(_UploadPlan(
                            source_path=Path(rel),
                            dest_name=rel,
                            upsert=True,
                            file_size=file_size
                        ))
                    elif strategy == "rename":
                        # Renomear: gerar novo nome com sufixo
                        new_name = _next_copy_name(file_name, existing_names)
                        existing_names.add(new_name)  # Atualizar set para evitar colisões futuras
                        # Manter estrutura de diretórios
                        dir_part = str(Path(rel).parent)
                        if dir_part == ".":
                            new_rel = new_name
                        else:
                            new_rel = f"{dir_part}/{new_name}"
                        upload_plans.append(_UploadPlan(
                            source_path=Path(rel),
                            dest_name=new_rel,
                            upsert=False,
                            file_size=file_size
                        ))
                else:
                    # Não duplicado: upload normal
                    upload_plans.append(_UploadPlan(
                        source_path=Path(rel),
                        dest_name=rel,
                        upsert=False,
                        file_size=file_size
                    ))

            if not upload_plans:
                if ext in ("rar", "7z"):
                    tmpdir_obj.cleanup()
                self.after(0, lambda: self._busy_fail("Nenhum arquivo para enviar (todos pulados ou duplicados)"))
                return

            # ====== FASE 4: UPLOAD COM TRACKING ======
            state = _ProgressState()
            state.total_files = len(upload_plans)
            state.total_bytes = sum(p.file_size for p in upload_plans)
            state.start_ts = time.monotonic()

            # Upload por extensão
            if ext == "zip":
                with zipfile.ZipFile(path, "r") as zf:
                    for plan in upload_plans:
                        if self._cancel_flag:
                            break

                        try:
                            # Ler conteúdo
                            data = zf.read(str(plan.source_path))
                            dest = f"{base_prefix}/{plan.dest_name}".strip("/")
                            mime = _guess_mime(plan.dest_name)

                            # Upload
                            self._sb.storage.from_(bucket).upload(  # type: ignore[union-attr]
                                dest,
                                data,
                                {"content-type": mime, "upsert": str(plan.upsert).lower(), "cacheControl": "3600"}
                            )

                            # Tracking
                            uploaded_paths.append(dest)
                            state.done_files += 1
                            state.done_bytes += plan.file_size

                            # Atualizar UI
                            self.after(0, lambda s=state: self._progress_update_ui(s))

                        except Exception as e:
                            fail.append((plan.dest_name, str(e)))

            elif ext in ("rar", "7z"):
                base = Path(tmpdir)
                for plan in upload_plans:
                    if self._cancel_flag:
                        break

                    try:
                        file_path = base / plan.source_path
                        dest = f"{base_prefix}/{plan.dest_name}".strip("/")
                        mime = _guess_mime(plan.dest_name)

                        # Upload
                        with open(file_path, "rb") as fh:
                            self._sb.storage.from_(bucket).upload(  # type: ignore[union-attr]
                                dest,
                                fh.read(),
                                {"content-type": mime, "upsert": str(plan.upsert).lower(), "cacheControl": "3600"}
                            )

                        # Tracking
                        uploaded_paths.append(dest)
                        state.done_files += 1
                        state.done_bytes += plan.file_size

                        # Atualizar UI
                        self.after(0, lambda s=state: self._progress_update_ui(s))

                    except Exception as e:
                        fail.append((plan.dest_name, str(e)))

                # Cleanup tmpdir
                tmpdir_obj.cleanup()

            # ====== FASE 5: VERIFICAR CANCELAMENTO ======
            if self._cancel_flag:
                self.after(0, lambda paths=uploaded_paths: self._ask_rollback(paths, bucket))
                return

        except Exception as e:
            self.after(0, lambda err=str(e): self._busy_fail(err))
            return

        # ====== FASE 6: FINALIZAÇÃO ======
        self.after(0, lambda: self._busy_done(state.done_files, fail, base_prefix, cliente_nome, cnpj, client_id, org_id))


class DuplicatesDialog(tk.Toplevel):
    """Diálogo para escolher estratégia ao encontrar arquivos duplicados."""

    def __init__(self, parent: tk.Misc, duplicates_count: int, sample_names: list[str]):
        """
        Args:
            parent: Janela pai
            duplicates_count: Total de duplicatas encontradas
            sample_names: Amostra de até 20 nomes duplicados
        """
        super().__init__(parent)
        self.title("Duplicatas Detectadas")

        # transient requer uma janela Toplevel/Tk
        if hasattr(parent, 'winfo_toplevel'):
            self.transient(parent.winfo_toplevel())

        self.grab_set()
        self.resizable(False, False)

        # Resultado
        self.strategy: str | None = None  # "skip", "replace", "rename" ou None (cancelou)

        # Centralizar
        self.update_idletasks()
        w = 500
        h = 450
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

        # Cabeçalho
        msg = f"Encontrados {duplicates_count} arquivo(s) duplicado(s).\nEscolha como proceder:"
        lbl_msg = ttk.Label(self, text=msg, font=("-size", 10), wraplength=460)
        lbl_msg.pack(padx=20, pady=(20, 10))

        # Frame de amostra (scrollable)
        frame_sample = ttk.LabelFrame(self, text="Amostra (até 20 nomes)", padding=10)
        frame_sample.pack(padx=20, pady=(0, 16), fill="both", expand=True)

        # Text widget com scrollbar
        txt_frame = ttk.Frame(frame_sample)
        txt_frame.pack(fill="both", expand=True)

        txt_scroll = ttk.Scrollbar(txt_frame)
        txt_scroll.pack(side="right", fill="y")

        self.txt_sample = tk.Text(
            txt_frame,
            height=8,
            width=50,
            yscrollcommand=txt_scroll.set,
            wrap="none",
            font=("Consolas", 9),
            state="normal"
        )
        self.txt_sample.pack(side="left", fill="both", expand=True)
        txt_scroll.config(command=self.txt_sample.yview)

        # Preencher amostra
        for name in sample_names[:20]:
            self.txt_sample.insert("end", f"• {name}\n")
        self.txt_sample.config(state="disabled")

        # Frame de opções
        frame_opts = ttk.LabelFrame(self, text="Estratégia", padding=10)
        frame_opts.pack(padx=20, pady=(0, 16), fill="x")

        self.var_strategy = tk.StringVar(value="skip")

        rb_skip = ttk.Radiobutton(
            frame_opts,
            text="⊘ Pular duplicatas (não envia arquivos que já existem)",
            variable=self.var_strategy,
            value="skip"
        )
        rb_skip.pack(anchor="w", pady=2)

        rb_replace = ttk.Radiobutton(
            frame_opts,
            text="♻ Substituir duplicatas (sobrescrever com novos arquivos)",
            variable=self.var_strategy,
            value="replace"
        )
        rb_replace.pack(anchor="w", pady=2)

        rb_rename = ttk.Radiobutton(
            frame_opts,
            text="✏ Renomear duplicatas (adicionar sufixo: arquivo (2).pdf)",
            variable=self.var_strategy,
            value="rename"
        )
        rb_rename.pack(anchor="w", pady=2)

        # Botões
        frame_btns = ttk.Frame(self)
        frame_btns.pack(padx=20, pady=(0, 20))

        btn_ok = ttk.Button(frame_btns, text="OK", command=self._on_ok, width=12)
        btn_ok.pack(side="left", padx=5)

        btn_cancel = ttk.Button(frame_btns, text="Cancelar", command=self._on_cancel, width=12)
        btn_cancel.pack(side="left", padx=5)

        # Focus no OK
        btn_ok.focus_set()

        # Bind Enter/Escape
        self.bind("<Return>", lambda e: self._on_ok())
        self.bind("<Escape>", lambda e: self._on_cancel())

    def _on_ok(self) -> None:
        """Confirma a escolha."""
        self.strategy = self.var_strategy.get()
        self.destroy()

    def _on_cancel(self) -> None:
        """Cancela o upload."""
        self.strategy = None
        self.destroy()


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
