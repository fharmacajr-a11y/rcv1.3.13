"""View principal do módulo Auditoria."""

from __future__ import annotations

import mimetypes
import os
import re
import tempfile
import threading
import time
import tkinter as tk
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Callable, Optional, Any

from src.ui import files_browser as fb
from src.ui.dialogs.file_select import select_archive_file
from infra.archive_utils import extract_archive, ArchiveError
from helpers.formatters import format_cnpj, fmt_datetime_br

try:
    from infra.supabase_client import get_supabase  # type: ignore[import-untyped]
except Exception:

    def get_supabase():  # type: ignore[no-redef]
        return None


try:
    from src.ui.files_browser import format_cnpj_for_display  # type: ignore[import-untyped]
except Exception:

    def format_cnpj_for_display(cnpj: str) -> str:  # fallback defensivo
        c = "".join(filter(str.isdigit, cnpj or ""))
        return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:14]}" if len(c) == 14 else (cnpj or "")


OFFLINE_MSG = "Recurso on-line. Verifique internet e credenciais do Supabase."

# === Storage config ===
STO_BUCKET = os.getenv("RC_STORAGE_BUCKET_CLIENTS", "").strip()
STO_CLIENT_FOLDER_FMT = os.getenv("RC_STORAGE_CLIENTS_FOLDER_FMT", "{client_id}").strip() or "{client_id}"


# === Auditoria status helpers ===
DEFAULT_AUDITORIA_STATUS = "em_andamento"

# valores aceitos no BD (ajuste se sua tabela tiver outros)
STATUS_OPEN = {"em_andamento", "pendente", "em_processo"}
STATUS_LABELS: dict[str, str] = {
    "em_andamento": "Em andamento",
    "pendente": "Pendente",
    "finalizado": "Finalizado",
    "cancelado": "Cancelado",
}

# aliases legados -> status canônico aceito pelo banco
STATUS_ALIASES: dict[str, str] = {
    "em_processo": DEFAULT_AUDITORIA_STATUS,
}


def canonical_status(value: str | None) -> str:
    """Normaliza o status recebido para a forma aceita pelo banco."""
    raw = (value or "").strip()
    if not raw:
        return DEFAULT_AUDITORIA_STATUS
    normalized = raw.lower().replace(" ", "_")
    normalized = STATUS_ALIASES.get(normalized, normalized)
    return normalized


STATUS_MENU_ITEMS = tuple(STATUS_LABELS.keys())
STATUS_OPEN_CANONICAL = {canonical_status(status) for status in STATUS_OPEN}


def status_to_label(value: str | None) -> str:
    """Retorna o rótulo amigável para exibição na UI."""
    canon = canonical_status(value)
    label = STATUS_LABELS.get(canon)
    if label:
        return label
    safe = canon.replace("_", " ").strip()
    return safe.capitalize() if safe else ""


def label_to_status(label: str | None) -> str:
    """Converte um rótulo exibido em tela de volta para o valor salvo no banco."""
    if not label:
        return canonical_status("")
    lowered = label.strip().lower()
    for key, friendly in STATUS_LABELS.items():
        if friendly.lower() == lowered:
            return key
    raw = lowered.replace(" ", "_")
    return canonical_status(raw)


def is_status_open(value: str | None) -> bool:
    """Retorna True se o status estiver entre os considerados 'abertos'."""
    return canonical_status(value) in STATUS_OPEN_CANONICAL


def _cliente_display_id_first(cliente_id, razao, cnpj) -> str:
    """Mostra: ID 123 — RAZÃO — 00.000.000/0001-00."""
    parts: list[str] = []
    if cliente_id not in (None, "", 0):
        parts.append(f"ID {cliente_id}")
    if razao:
        parts.append(str(razao).strip())
    c = format_cnpj(cnpj or "")
    if c:
        parts.append(c)
    return " — ".join(parts)


def _cliente_razao_from_row(row: dict | None) -> str:
    """Extrai a razão social/nome mais representativo do registro do cliente."""
    if not isinstance(row, dict):
        return ""
    return (row.get("display_name") or row.get("razao_social") or row.get("Razao Social") or row.get("legal_name") or row.get("name") or "").strip()


def _cliente_cnpj_from_row(row: dict | None) -> str:
    """Extrai o CNPJ (ou tax_id) cru do registro do cliente."""
    if not isinstance(row, dict):
        return ""
    return (row.get("cnpj") or row.get("tax_id") or "").strip()


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
    skipped_count: int = 0  # Arquivos pulados (duplicatas com strategy=skip)
    failed_count: int = 0  # Arquivos que falharam no upload


@dataclass
class _UploadPlan:
    """Plano de upload para um arquivo (com estratégia de duplicatas)."""

    source_path: Path  # Caminho local do arquivo
    dest_name: str  # Nome de destino no Storage
    upsert: bool  # True = substituir se existir, False = erro se existir
    file_size: int  # Tamanho em bytes


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

    def __init__(self, master: tk.Misc, go_back: Callable[[], None] | None = None, **kwargs) -> None:
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
        self._clientes_all_rows: list[dict] = []  # linhas cruas p/ busca (todos os campos)
        self._cliente_display_to_id: dict[str, int] = {}
        self._cliente_display_map: dict[str, str] = {}
        self._clientes_rows_map: dict[str, dict] = {}
        self._cliente_var = tk.StringVar()
        self._selected_cliente_id: int | None = None

        # Índice de auditorias: {iid: {db_id, auditoria_id, cliente_nome, cnpj, ...}}
        self._aud_index: dict[str, dict] = {}

        # Rastreio de janelas "Ver subpastas" abertas por auditoria_id (chave string)
        self._open_browsers: dict[str, tk.Toplevel] = {}

        # Org ID do usuário logado (cache)
        self._org_id: str = ""
        self._status_menu: tk.Menu | None = None
        self._status_menu_items: tuple[str, ...] = STATUS_MENU_ITEMS
        self._status_click_iid: str | None = None
        self._menu_refresh_added = False

        UI_GAP = 6  # espacinho horizontal curto entre botões
        UI_PADX = 8
        UI_PADY = 6
        self.UI_GAP = UI_GAP
        self.UI_PADX = UI_PADX
        self.UI_PADY = UI_PADY

        self._build_ui()

        try:
            import ttkbootstrap as tb  # type: ignore[import]  # noqa: F401
        except Exception:
            style = ttk.Style(self)
            style.configure("RC.Success.TButton", foreground="white")
            style.map("RC.Success.TButton", background=[("!disabled", "#198754"), ("active", "#157347")])
            self.btn_iniciar.configure(style="RC.Success.TButton")

            style.configure("RC.Danger.TButton", foreground="white")
            style.map("RC.Danger.TButton", background=[("!disabled", "#DC3545"), ("active", "#BB2D3B")])
            self.btn_excluir.configure(style="RC.Danger.TButton")
        else:
            self.btn_iniciar.configure(bootstyle="success")  # type: ignore[arg-type]
            self.btn_excluir.configure(bootstyle="danger")  # type: ignore[arg-type]

        # ---------- UI ----------
        self.after(100, self._lazy_load)

    def _build_ui(self) -> None:
        """Constrói a interface da tela."""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        UI_GAP = getattr(self, "UI_GAP", 6)
        UI_PADX = getattr(self, "UI_PADX", 8)
        UI_PADY = getattr(self, "UI_PADY", 6)

        # ===== Toolbar superior =====
        self.toolbar = ttk.Frame(self)
        self.toolbar.grid(row=0, column=0, sticky="ew", padx=UI_PADX, pady=(UI_PADY, 0))
        self.toolbar.configure(padding=(UI_PADX, UI_PADY, UI_PADX, UI_PADY))
        for col in range(0, 8):
            self.toolbar.columnconfigure(col, weight=0)
        self.toolbar.columnconfigure(7, weight=1)

        # Buscar cliente
        self.search_var = getattr(self, "search_var", self._search_var if hasattr(self, "_search_var") else tk.StringVar())
        self._search_var = self.search_var
        if not hasattr(self, "on_limpar_busca"):
            self.on_limpar_busca = self._clear_search

        ttk.Label(self.toolbar, text="Buscar cliente:").grid(row=0, column=0, sticky="w", padx=(0, UI_GAP))
        self.entry_busca = ttk.Entry(self.toolbar, textvariable=self.search_var, width=32)
        self.entry_busca.grid(row=0, column=1, sticky="w", padx=(0, UI_GAP))
        self.ent_busca = self.entry_busca

        def _on_busca_key(event=None):  # type: ignore[no-untyped-def]
            after_id = getattr(self, "_busca_after", None)
            if after_id:
                try:
                    self.after_cancel(after_id)
                except Exception:
                    pass
            self._busca_after = self.after(140, lambda: self._filtra_clientes(self.ent_busca.get()))

        self.entry_busca.bind("<KeyRelease>", _on_busca_key)

        self.btn_limpar = ttk.Button(self.toolbar, text="Limpar", command=getattr(self, "on_limpar_busca", self._clear_search))
        self.btn_limpar.grid(row=0, column=2, padx=(0, UI_GAP))

        # Cliente para auditoria
        self.cliente_var = getattr(self, "cliente_var", self._cliente_var if hasattr(self, "_cliente_var") else tk.StringVar())
        self._cliente_var = self.cliente_var
        ttk.Label(self.toolbar, text="Cliente para auditoria:").grid(row=0, column=3, sticky="e", padx=(UI_GAP, UI_GAP))
        self.combo_cliente = ttk.Combobox(self.toolbar, textvariable=self.cliente_var, state="readonly", width=48)
        self.combo_cliente.grid(row=0, column=4, sticky="w")
        self.cmb_cliente = self.combo_cliente

        ttk.Label(self.toolbar, text="").grid(row=0, column=7, sticky="ew")

        def _on_select_cliente(event=None):  # type: ignore[no-untyped-def]
            self._selected_cliente_id = self._get_selected_cliente_id()

        self.combo_cliente.bind("<<ComboboxSelected>>", _on_select_cliente)

        btn_refresh = getattr(self, "btn_refresh", None)
        if btn_refresh and getattr(btn_refresh, "winfo_exists", lambda: False)():
            btn_refresh.destroy()
        self.btn_refresh = None  # type: ignore[assignment]

        for attr in ("btn_subpastas", "btn_enviar", "btn_excluir", "btn_iniciar"):
            widget = getattr(self, attr, None)
            if widget and getattr(widget, "winfo_exists", lambda: False)():
                widget.destroy()
            setattr(self, attr, None)

        # Remover botões obsoletos herdados
        btn_voltar = getattr(self, "btn_voltar", None)
        if btn_voltar and getattr(btn_voltar, "winfo_exists", lambda: False)():
            btn_voltar.destroy()
        btn_atualizar = getattr(self, "btn_atualizar", None)
        if btn_atualizar and getattr(btn_atualizar, "winfo_exists", lambda: False)():
            btn_atualizar.destroy()

        # Inicializa variáveis auxiliares de busca
        self._busca_after: str | None = None

        # Linha divisória após toolbar
        self.sep_top = ttk.Separator(self, orient="horizontal")
        self.sep_top.grid(row=1, column=0, sticky="ew", padx=UI_PADX, pady=(0, UI_GAP))

        # Container da lista (Labelframe)
        self.list_frame = ttk.Labelframe(self, text="Auditorias recentes", padding=(6, 4, 6, 6))
        self.list_frame.grid(row=2, column=0, sticky="nsew", padx=UI_PADX, pady=(0, UI_PADY))
        self.rowconfigure(2, weight=1)
        self.columnconfigure(0, weight=1)
        self.list_frame.columnconfigure(0, weight=1)
        self.list_frame.rowconfigure(0, weight=1)

        # Grade / Treeview dentro da list_frame
        self.tree_container = ttk.Frame(self.list_frame)
        self.tree_container.grid(row=0, column=0, sticky="nsew")
        self.tree_container.columnconfigure(0, weight=1)
        self.tree_container.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(self.tree_container, columns=("cliente", "status", "criado", "atualizado"), show="headings", selectmode="extended", height=16)
        for cid, title in (
            ("cliente", "Cliente"),
            ("status", "Status"),
            ("criado", "Criado em"),
            ("atualizado", "Atualizado em"),
        ):
            self.tree.heading(cid, text=title, anchor="center")
            self.tree.column(cid, anchor="center", stretch=True)
        self.tree.grid(row=0, column=0, sticky="nsew")

        self.tree.bind("<<TreeviewSelect>>", self._on_auditoria_select)
        self.tree.bind("<Button-3>", self._open_status_menu)

        scrollbar = ttk.Scrollbar(self.tree_container, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.lbl_notfound = ttk.Label(self.list_frame, text="", foreground="#a33")
        self.lbl_notfound.grid(row=1, column=0, sticky="w", pady=(UI_GAP, 0))

        # Barra de ações dentro do Labelframe
        if hasattr(self, "actions_bottom") and getattr(self.actions_bottom, "winfo_exists", lambda: False)():  # type: ignore[attr-defined]
            self.actions_bottom.destroy()  # type: ignore[attr-defined]
        if hasattr(self, "lf_actions") and getattr(self.lf_actions, "winfo_exists", lambda: False)():  # type: ignore[attr-defined]
            self.lf_actions.destroy()  # type: ignore[attr-defined]

        self.lf_actions = ttk.Frame(self.list_frame, padding=(UI_PADX, UI_PADY, UI_PADX, UI_PADY))
        self.lf_actions.grid(row=1, column=0, sticky="ew")
        self.list_frame.rowconfigure(1, weight=0)

        self.lf_actions.columnconfigure(0, weight=1)
        for col in (1, 2, 3, 4):
            self.lf_actions.columnconfigure(col, weight=0)

        iniciar_cmd = getattr(self, "on_iniciar_auditoria", self._on_iniciar)
        subpastas_cmd = getattr(self, "on_ver_subpastas", self._open_subpastas)
        enviar_cmd = getattr(self, "on_enviar_arquivos", self._upload_archive_to_auditoria)
        excluir_cmd = getattr(self, "on_excluir", self._delete_auditorias)

        self.btn_iniciar = ttk.Button(self.lf_actions, text="Iniciar auditoria", command=iniciar_cmd)
        self.btn_subpastas = ttk.Button(self.lf_actions, text="Ver subpastas", command=subpastas_cmd, state="disabled")
        self.btn_enviar = ttk.Button(self.lf_actions, text="Enviar arquivos para Auditoria", command=enviar_cmd)
        self.btn_excluir = ttk.Button(self.lf_actions, text="Excluir auditoria(s)", command=excluir_cmd, state="disabled")

        ttk.Label(self.lf_actions, text="").grid(row=0, column=0, sticky="ew")

        self.btn_iniciar.grid(row=0, column=1, padx=(0, UI_GAP), sticky="e")
        self.btn_subpastas.grid(row=0, column=2, padx=(0, UI_GAP), sticky="e")
        self.btn_enviar.grid(row=0, column=3, padx=(0, UI_GAP), sticky="e")
        self.btn_excluir.grid(row=0, column=4, padx=(0, 0), sticky="e")

        # Aliases para manter compatibilidade com trechos existentes
        self._btn_h_ver = self.btn_subpastas
        self._btn_h_enviar_zip = self.btn_enviar
        self._btn_h_delete = self.btn_excluir

        try:
            self.bind_all("<F5>", lambda event: self._load_auditorias())
        except Exception:
            pass
        self._add_refresh_menu_entry()

        self.lbl_offline = ttk.Label(self, text=OFFLINE_MSG, foreground="#666")
        self.lbl_offline.grid(row=4, column=0, sticky="w", padx=UI_PADX, pady=(UI_PADY, 0))

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
            if not isinstance(cli, dict):
                continue
            idx = _build_search_index(cli)
            # 1) Se o usuário digitou CNPJ (>= 5 dígitos), priorize match numérico
            if len(q_digits) >= 5 and q_digits in idx["cnpj"]:
                filtrados.append(cli)
                continue
            # 2) Match textual em razão social e nomes de contato
            if q_text and (q_text in idx["razao"] or any(q_text in nome for nome in idx["nomes"])):
                filtrados.append(cli)
                continue
            # 3) Query vazia -> mantém tudo
            if not q_text and not q_digits:
                filtrados = base
                break

        self._fill_clientes_combo(filtrados)

        if filtrados:
            if hasattr(self, "lbl_notfound"):
                self.lbl_notfound.configure(text="")
        else:
            if hasattr(self, "lbl_notfound"):
                self.lbl_notfound.configure(text="Nenhum cliente encontrado")

    @staticmethod
    def _status_label(status: str) -> str:
        return status_to_label(status)

    def _apply_filter(self) -> None:
        """Aplica filtro de busca nos clientes (compatibilidade)."""
        self._filtra_clientes(self._search_var.get())

    def _fill_clientes_combo(self, clientes: list[dict]) -> None:  # type: ignore[type-arg]
        """Atualiza a combobox com a lista filtrada de clientes."""
        values: list[str] = []
        mapping: dict[str, int] = {}

        for cli in clientes:
            if not isinstance(cli, dict):
                continue
            raw_id = cli.get("id")
            try:
                cid_int = int(raw_id) if raw_id not in (None, "") else None
            except Exception:
                cid_int = None

            razao = _cliente_razao_from_row(cli)
            cnpj_raw = _cliente_cnpj_from_row(cli)
            ident = cid_int if cid_int is not None else raw_id
            display = _cliente_display_id_first(ident, razao, cnpj_raw)
            values.append(display)

            if cid_int is not None:
                mapping[display] = cid_int
                self._cliente_display_map[str(cid_int)] = display
            elif raw_id not in (None, ""):
                try:
                    mapping[display] = int(str(raw_id))
                except Exception:
                    # sem ID numérico -> não fornece mapping para criação
                    pass

            if raw_id not in (None, ""):
                self._cliente_display_map[str(raw_id)] = display

        self._cliente_display_to_id = mapping

        try:
            self.combo_cliente.configure(values=values, state="readonly")
        except Exception:
            return

        current = self.cliente_var.get()
        if values and (not current or current not in values):
            self.cliente_var.set(values[0])
        elif not values:
            self.cliente_var.set("")

        self._selected_cliente_id = self._get_selected_cliente_id()

    def _get_selected_cliente_id(self) -> int | None:
        """Retorna o cliente_id selecionado na combobox (ou None)."""
        try:
            display = self.cliente_var.get().strip()
        except Exception:
            return None
        if not display:
            return None
        raw = self._cliente_display_to_id.get(display)
        if raw is None:
            return None
        try:
            return int(raw)
        except Exception:
            try:
                return int(str(raw))
            except Exception:
                return None

    def _has_open_auditoria_for(self, cliente_id: int | str | None) -> bool:
        """Procura na lista atual se há auditoria 'aberta' para o cliente."""
        if cliente_id in (None, "", 0):
            return False

        target_str = str(cliente_id)
        target_int: int | None
        try:
            target_int = int(cliente_id)
        except Exception:
            target_int = None

        for rec in self._aud_index.values():
            rec_cliente = rec.get("cliente_id")
            if rec_cliente is None:
                continue

            match = False
            if target_int is not None:
                try:
                    match = int(rec_cliente) == target_int
                except Exception:
                    match = False
            if not match and str(rec_cliente) == target_str:
                match = True

            if match and is_status_open(rec.get("status")):
                return True
        return False

    def _do_refresh(self) -> None:
        """Recarrega listas de clientes e auditorias."""
        client_loader = getattr(self, "_load_clientes", None)
        if callable(client_loader):
            client_loader()

        loader = getattr(self, "_load_auditorias", None)
        if callable(loader):
            loader()
            return

        fallback = getattr(self, "load_rows", None)
        if callable(fallback):
            fallback([])

    def _add_refresh_menu_entry(self) -> None:
        """Adiciona ação de recarregar à barra de menus, se existir."""
        if getattr(self, "_menu_refresh_added", False):
            return

        try:
            root = self.winfo_toplevel()
        except Exception:
            return
        if not root or not root.winfo_exists():
            return

        try:
            menu_name = root["menu"]
        except Exception:
            menu_name = None
        if not menu_name:
            return

        try:
            top_menu = root.nametowidget(menu_name)
        except Exception:
            return
        if not isinstance(top_menu, tk.Menu):
            return

        exibir_menu: tk.Menu | None = None
        try:
            end_index = top_menu.index("end")
        except Exception:
            end_index = None
        if end_index is not None:
            for idx in range(end_index + 1):
                try:
                    if top_menu.type(idx) == "cascade" and top_menu.entrycget(idx, "label") == "Exibir":
                        exibir_menu = top_menu.nametowidget(top_menu.entrycget(idx, "menu"))  # type: ignore[arg-type]
                        break
                except Exception:
                    continue

        if exibir_menu is None:
            exibir_menu = tk.Menu(top_menu, tearoff=False)
            top_menu.add_cascade(label="Exibir", menu=exibir_menu)

        if not isinstance(exibir_menu, tk.Menu):
            return
        
        assert exibir_menu is not None  # Type narrowing for Pyright

        try:
            end_index = exibir_menu.index("end")
        except Exception:
            end_index = None
        if end_index is not None:
            for idx in range(end_index + 1):
                try:
                    if exibir_menu.entrycget(idx, "label") == "Recarregar lista":
                        self._menu_refresh_added = True
                        return
                except Exception:
                    continue

        try:
            exibir_menu.add_command(label="Recarregar lista", accelerator="F5", command=self._do_refresh)
            self._menu_refresh_added = True
        except Exception:
            pass

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
        return self._get_selected_cliente_id()

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

        # Botões de storage (header direita)
        for w in (
            getattr(self, "_btn_h_ver", None),
            # getattr(self, "_btn_h_criar", None),  # botão comentado
            getattr(self, "_btn_h_enviar_zip", None),
        ):
            if w:
                w.configure(state=state)

        self.lbl_offline.configure(text=OFFLINE_MSG if is_offline else "")

    def _load_clientes(self) -> None:
        """Carrega lista de clientes do Supabase e preenche índice de busca."""
        if not self._sb:
            return

        try:
            res = self._sb.table("clients").select("*").order("id").execute()
            data = getattr(res, "data", []) or []

            self._clientes_all_rows = [row for row in data if isinstance(row, dict)]  # type: ignore[list-item]
            self._cliente_display_map.clear()
            self._clientes_rows_map.clear()

            for row in self._clientes_all_rows:
                raw_id = row.get("id")
                ident_int: int | None
                try:
                    ident_int = int(raw_id) if raw_id not in (None, "") else None
                except Exception:
                    ident_int = None

                razao = _cliente_razao_from_row(row)
                cnpj_raw = _cliente_cnpj_from_row(row)
                ident = ident_int if ident_int is not None else raw_id
                display = _cliente_display_id_first(ident, razao, cnpj_raw)

                if raw_id is not None:
                    key = str(raw_id)
                    self._cliente_display_map[key] = display
                    self._clientes_rows_map[key] = row
                if ident_int is not None:
                    key_int = str(ident_int)
                    self._cliente_display_map[key_int] = display
                    self._clientes_rows_map[key_int] = row

            # aplica o filtro atual (se houver texto digitado)
            self._apply_filter()

        except Exception as e:
            messagebox.showwarning("Clientes", f"Não foi possível carregar os clientes.\n{e}")

    def _load_auditorias(self) -> None:
        """
            Carrega lista de auditorias do Supabase.

        Monta o nome do cliente via cache local (sem usar embed FK).
            Popula self._aud_index para rastreamento de IDs.
        """
        if not self._sb:
            return

        try:
            # Limpa índice anterior
            self._aud_index.clear()

            res = self._sb.table("auditorias").select("id, cliente_id, status, created_at, updated_at").order("updated_at", desc=True).execute()
            rows = getattr(res, "data", []) or []
            self.tree.delete(*self.tree.get_children())

            for r in rows:
                if not isinstance(r, dict):
                    continue

                aud_id = r.get("id")
                if aud_id is None:
                    continue

                iid = str(aud_id)

                raw_cliente_id = r.get("cliente_id")
                cliente_row = None
                cliente_id_int: int | None = None
                if raw_cliente_id not in (None, ""):
                    key_raw = str(raw_cliente_id)
                    cliente_row = self._clientes_rows_map.get(key_raw)
                    if cliente_row is None:
                        try:
                            cliente_row = self._clientes_rows_map.get(str(int(raw_cliente_id)))
                        except Exception:
                            cliente_row = None
                    try:
                        cliente_id_int = int(raw_cliente_id)
                    except Exception:
                        cliente_id_int = None

                razao = _cliente_razao_from_row(cliente_row) or _cliente_razao_from_row(r)
                cnpj_raw = _cliente_cnpj_from_row(cliente_row)
                if not cnpj_raw:
                    cnpj_raw = r.get("cnpj") or r.get("tax_id") or ""
                cliente_ident = cliente_id_int if cliente_id_int is not None else raw_cliente_id
                cliente_txt = _cliente_display_id_first(cliente_ident, razao, cnpj_raw)
                if not cliente_txt:
                    cliente_txt = self._cliente_display_map.get(str(raw_cliente_id), "")

                status_raw = r.get("status") or DEFAULT_AUDITORIA_STATUS
                status_db = canonical_status(status_raw)
                status_display = status_to_label(status_db)

                created_iso = r.get("created_at") or r.get("criado")
                updated_iso = r.get("updated_at") or r.get("atualizado")
                created_br = fmt_datetime_br(created_iso)
                updated_br = fmt_datetime_br(updated_iso)

                cliente_cnpj_fmt = format_cnpj(cnpj_raw)

                self._aud_index[iid] = {
                    "db_id": aud_id,
                    "cliente_id": cliente_id_int if cliente_id_int is not None else raw_cliente_id,
                    "cliente_display": cliente_txt,
                    "cliente_nome": razao or cliente_txt,
                    "cliente_razao": razao,
                    "cnpj": cliente_cnpj_fmt,
                    "status": status_db,
                    "status_display": status_display,
                    "created_at": created_br,
                    "created_at_iso": created_iso,
                    "updated_at": updated_br,
                    "updated_at_iso": updated_iso,
                }

                self.tree.insert("", "end", iid=iid, values=(cliente_txt, status_display, created_br, updated_br))
        except Exception as e:
            messagebox.showwarning("Auditorias", f"Falha ao carregar auditorias.\n{e}")

    def _ensure_status_menu(self) -> tk.Menu:
        if self._status_menu and self._status_menu.winfo_exists():
            return self._status_menu

        menu = tk.Menu(self, tearoff=0)
        for status in self._status_menu_items:
            menu.add_command(label=self._status_label(status), command=lambda value=status: self._apply_status_from_menu(value))
        self._status_menu = menu
        return menu

    def _open_status_menu(self, event: tk.Event) -> None:  # type: ignore[name-defined]
        """Exibe menu de contexto de status apenas quando o clique for na coluna 'status'."""
        row = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if not row or col != "#2":
            return

        try:
            self.tree.selection_set(row)
        except Exception:
            pass

        self._status_click_iid = row
        menu = self._ensure_status_menu()
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _apply_status_from_menu(self, new_status: str) -> None:
        iid = self._status_click_iid or next(iter(self.tree.selection()), None)
        self._status_click_iid = None
        if not iid:
            return
        self._set_auditoria_status(iid, new_status)

    def _set_auditoria_status(self, iid: str, new_status: str) -> None:
        row = self._aud_index.get(iid)
        if not row:
            return

        normalized = label_to_status(new_status)
        desired_db = canonical_status(normalized or new_status)
        if desired_db not in STATUS_LABELS:
            messagebox.showerror("Auditoria", "Status selecionado inválido.")
            return

        current = canonical_status(row.get("status"))
        if current == desired_db:
            return

        if not self._sb:
            messagebox.showwarning("Auditoria", "Sem conexão com o banco de dados.")
            return

        try:
            res = self._sb.table("auditorias").update({"status": desired_db}).eq("id", row["db_id"]).select("status, updated_at").execute()
            data = getattr(res, "data", None) or []
            updated_iso = data[0].get("updated_at") if data else None
        except Exception as e:
            messagebox.showerror("Auditoria", f"Falha ao atualizar status.\n{e}")
            return

        row["status"] = desired_db
        row["status_display"] = status_to_label(desired_db)
        if updated_iso:
            row["updated_at_iso"] = updated_iso
            row["updated_at"] = fmt_datetime_br(updated_iso)

        self.tree.set(iid, "status", row["status_display"])
        if row.get("updated_at"):
            self.tree.set(iid, "atualizado", row["updated_at"])

    # ---------- Actions ----------
    def _on_iniciar(self) -> None:
        """Handler do botão 'Iniciar auditoria'."""
        if not self._sb:
            return

        cliente_id = self._get_selected_cliente_id()
        if not cliente_id:
            messagebox.showwarning("Auditoria", "Selecione um cliente para iniciar a auditoria.")
            return

        if self._has_open_auditoria_for(cliente_id):
            msg = "Já existe uma auditoria em andamento para este cliente.\n\nDeseja iniciar outra auditoria para a mesma farmácia?"
            if not messagebox.askyesno("Confirmar", msg):
                return

        try:
            ins = self._sb.table("auditorias").insert({"cliente_id": cliente_id, "status": DEFAULT_AUDITORIA_STATUS}).execute()
            if getattr(ins, "data", None):
                self._load_auditorias()
                messagebox.showinfo("Auditoria", "Auditoria iniciada com sucesso.")
        except Exception as e:
            messagebox.showerror("Auditoria", f"Não foi possível iniciar a auditoria.\n{e}")

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

        if not messagebox.askyesno("Confirmar exclusão", f"Excluir {len(ids)} auditoria(s)?\n\n{lista_nomes}", parent=self):
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
                start_prefix=prefix,
                module="auditoria",
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
            from src.ui.files_browser import get_clients_bucket, client_prefix_for_id, get_current_org_id

            bucket = get_clients_bucket()  # "rc-docs"
            org_id = get_current_org_id(self._sb)
            base = client_prefix_for_id(int(cid), org_id)  # "{org_id}/{client_id}"
            target = f"{base}/GERAL/Auditoria/.keep"

            # Upload do placeholder com API correta (upsert string para evitar 409)
            resp = self._sb.storage.from_(bucket).upload(  # type: ignore[union-attr]
                path=target, file=b"", file_options={"content-type": "text/plain", "upsert": "true"}
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
                    prefix, {"limit": limit, "offset": offset}
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
                        batch = uploaded_paths[i : i + batch_size]
                        self._sb.storage.from_(bucket).remove(batch)  # type: ignore[union-attr]

                    self.after(0, lambda: messagebox.showinfo("Revertido", f"{len(uploaded_paths)} arquivo(s) removido(s) com sucesso."))
                except Exception as e:
                    self.after(0, lambda err=str(e): messagebox.showerror("Erro ao Reverter", f"Falha ao remover arquivos:\n{err}"))

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
                    self, supabase=self._sb, client_id=client_id, org_id=org_id, razao=cliente_nome, cnpj=cnpj, start_prefix=base_prefix, module="auditoria"
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
                f"Arquivo selecionado: {Path(path).name}",
            )
            return

        # 3) Mostrar modal de progresso
        self._show_busy("Processando arquivos", f"Enviando {Path(path).name}...")

        # 4) Lançar thread worker
        threading.Thread(target=self._worker_upload, args=(path, client_id, org_id, cliente_nome, cnpj), daemon=True).start()

    def _worker_upload(self, archive_path: str, client_id: int, org_id: str, cliente_nome: str, cnpj: str) -> None:
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
                dialog_result: dict[str, Any] = {"strategy": None, "apply_once": True}

                def _show_dup_dialog():
                    dlg = DuplicatesDialog(self, len(duplicates_names), sorted(duplicates_names))
                    self.wait_window(dlg)
                    dialog_result["strategy"] = dlg.strategy
                    dialog_result["apply_once"] = dlg.apply_once

                self.after(0, _show_dup_dialog)

                # Aguardar resposta (polling simples)
                while dialog_result["strategy"] is None:
                    time.sleep(0.05)
                    if self._cancel_flag:
                        if ext in ("rar", "7z"):
                            tmpdir_obj.cleanup()
                        return

                strategy = dialog_result["strategy"]
                _apply_once = dialog_result["apply_once"]  # Reserved for future use (TODO)

                if strategy is None:  # Cancelou
                    if ext in ("rar", "7z"):
                        tmpdir_obj.cleanup()
                    self.after(0, lambda: self._busy_fail("Upload cancelado pelo usuário"))
                    return

                # TODO: Se apply_once=False, persistir strategy em preferências para próximos envios
                # Por enquanto, apenas aplica à sessão atual

            # ====== FASE 3: MONTAR PLANO DE UPLOAD ======
            upload_plans: list[_UploadPlan] = []
            skipped_count = 0  # Contador de arquivos pulados

            for rel, file_size in files_to_upload:
                file_name = Path(rel).name
                is_dup = file_name in duplicates_names

                if is_dup:
                    if strategy == "skip":
                        skipped_count += 1  # Incrementa contador
                        continue  # Não adiciona ao plano
                    elif strategy == "replace":
                        # Substituir: usar nome original com upsert=True
                        upload_plans.append(_UploadPlan(source_path=Path(rel), dest_name=rel, upsert=True, file_size=file_size))
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
                        upload_plans.append(_UploadPlan(source_path=Path(rel), dest_name=new_rel, upsert=False, file_size=file_size))
                else:
                    # Não duplicado: upload normal
                    upload_plans.append(_UploadPlan(source_path=Path(rel), dest_name=rel, upsert=False, file_size=file_size))

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
            state.skipped_count = skipped_count  # Inicializar contador de pulados

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
                                dest, data, {"content-type": mime, "upsert": str(plan.upsert).lower(), "cacheControl": "3600"}
                            )

                            # Tracking
                            uploaded_paths.append(dest)
                            state.done_files += 1
                            state.done_bytes += plan.file_size

                            # Atualizar UI
                            self.after(0, lambda s=state: self._progress_update_ui(s))

                        except Exception as e:
                            state.failed_count += 1  # Incrementar contador de falhas
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
                                dest, fh.read(), {"content-type": mime, "upsert": str(plan.upsert).lower(), "cacheControl": "3600"}
                            )

                        # Tracking
                        uploaded_paths.append(dest)
                        state.done_files += 1
                        state.done_bytes += plan.file_size

                        # Atualizar UI
                        self.after(0, lambda s=state: self._progress_update_ui(s))

                    except Exception as e:
                        state.failed_count += 1  # Incrementar contador de falhas
                        fail.append((plan.dest_name, str(e)))

                # Cleanup tmpdir
                tmpdir_obj.cleanup()

            # ====== FASE 5: VERIFICAR CANCELAMENTO ======
            if self._cancel_flag:
                # Mostrar resumo de cancelamento ao invés de rollback
                def _show_cancel_summary():
                    uploaded = state.done_files
                    skipped = state.skipped_count
                    failed = state.failed_count
                    msg = f"Upload cancelado.\n\n📤 {uploaded} arquivo(s) enviado(s)\n⊘ {skipped} pulado(s) (duplicatas)\n❌ {failed} falha(s)"
                    messagebox.showinfo("Upload Cancelado", msg)
                    self._close_busy()

                self.after(0, _show_cancel_summary)
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
        if hasattr(parent, "winfo_toplevel"):
            self.transient(parent.winfo_toplevel())

        self.grab_set()
        self.resizable(False, False)

        # Resultado
        self.strategy: str | None = None  # "skip", "replace", "rename" ou None (cancelou)
        self.apply_once: bool = True  # Checkbox "Aplicar só a este envio"

        # Centralizar
        self.update_idletasks()
        w = 560
        h = 480
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

        # Cabeçalho
        msg = f"Encontrados {duplicates_count} arquivo(s) duplicado(s).\nEscolha como proceder:"
        lbl_msg = ttk.Label(self, text=msg, font=("-size", 10), wraplength=520)
        lbl_msg.pack(padx=20, pady=(20, 10))

        # Frame de amostra com Treeview
        frame_sample = ttk.LabelFrame(self, text="Amostra (até 20 arquivos)", padding=10)
        frame_sample.pack(padx=20, pady=(0, 12), fill="both", expand=True)

        # Treeview com scrollbar
        tree_frame = ttk.Frame(frame_sample)
        tree_frame.pack(fill="both", expand=True)

        self.tree_sample = ttk.Treeview(tree_frame, columns=("arquivo",), show="tree headings", height=min(len(sample_names[:20]), 10), selectmode="none")
        self.tree_sample.heading("#0", text="")
        self.tree_sample.heading("arquivo", text="Arquivo", anchor="w")
        self.tree_sample.column("#0", width=0, stretch=False)
        self.tree_sample.column("arquivo", width=500, anchor="w", stretch=True)

        scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_sample.yview)
        self.tree_sample.configure(yscrollcommand=scroll.set)
        self.tree_sample.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        # Preencher amostra
        for name in sample_names[:20]:
            self.tree_sample.insert("", "end", values=(name,))
        if len(sample_names) > 20:
            self.tree_sample.insert("", "end", values=(f"... e mais {len(sample_names) - 20} arquivo(s)",))

        # Checkbox "Aplicar só a este envio"
        self.var_apply_once = tk.BooleanVar(value=True)
        chk_apply = ttk.Checkbutton(self, text="✓ Aplicar só a este envio (não lembrar esta escolha)", variable=self.var_apply_once)
        chk_apply.pack(padx=20, pady=(0, 12), anchor="w")

        # Frame de opções
        frame_opts = ttk.LabelFrame(self, text="Estratégia", padding=10)
        frame_opts.pack(padx=20, pady=(0, 16), fill="x")

        self.var_strategy = tk.StringVar(value="skip")

        rb_skip = ttk.Radiobutton(frame_opts, text="⊘ Pular duplicatas (não envia arquivos que já existem)", variable=self.var_strategy, value="skip")
        rb_skip.pack(anchor="w", pady=2)

        rb_replace = ttk.Radiobutton(frame_opts, text="♻ Substituir duplicatas (sobrescrever com novos arquivos)", variable=self.var_strategy, value="replace")
        rb_replace.pack(anchor="w", pady=2)

        rb_rename = ttk.Radiobutton(frame_opts, text="✏ Renomear duplicatas (adicionar sufixo: arquivo (2).pdf)", variable=self.var_strategy, value="rename")
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
        self.apply_once = self.var_apply_once.get()
        self.destroy()

    def _on_cancel(self) -> None:
        """Cancela o upload."""
        self.strategy = None
        self.apply_once = True
        self.destroy()
