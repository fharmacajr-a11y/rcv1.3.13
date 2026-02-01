# -*- coding: utf-8 -*-
"""Diálogo de gerenciamento de arquivos do cliente - ClientesV2.

Browser funcional de arquivos com Supabase Storage.
"""

from __future__ import annotations

import importlib
import logging
import os
import tempfile
import threading
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tkinter import filedialog, messagebox
from tkinter import ttk
from typing import Any, Optional
import queue

from src.ui.ctk_config import ctk
from src.ui.ui_tokens import SURFACE, SURFACE_DARK, TEXT_PRIMARY, TEXT_MUTED, APP_BG
from src.ui.ttk_treeview_manager import get_treeview_manager
from src.ui.ttk_treeview_theme import apply_zebra
from src.ui.dark_window_helper import set_win_dark_titlebar
from src.adapters.storage.supabase_storage import SupabaseStorageAdapter
from src.modules.uploads.components.helpers import get_clients_bucket, client_prefix_for_id, get_current_org_id
from src.modules.clientes.forms.client_subfolder_prompt import SubpastaDialog
from src.utils.paths import resource_path

log = logging.getLogger(__name__)


def log_slow(op_name: str, start_monotonic: float, threshold_ms: float = 1000.0) -> None:
    """Log warning se operação demorou mais que threshold.
    
    Args:
        op_name: Nome da operação (ex: "list_files", "download", "upload")
        start_monotonic: time.monotonic() quando operação iniciou
        threshold_ms: Threshold em milissegundos (padrão 1000ms)
        
    Note:
        Threshold aumentado de 250ms para 1000ms para reduzir ruído no console.
        Operações de rede de até 1s são consideradas normais.
    """
    import os
    
    # Só logar se RC_DEBUG_SLOW_OPS=1 ou se ultrapassou threshold
    debug_enabled = os.getenv("RC_DEBUG_SLOW_OPS", "0") == "1"
    
    elapsed_ms = (time.monotonic() - start_monotonic) * 1000
    if elapsed_ms > threshold_ms and debug_enabled:
        log.warning(f"[ClientFiles] Operação lenta: {op_name} levou {elapsed_ms:.0f}ms (>{threshold_ms:.0f}ms)")


def _resolve_supabase_client():
    """Resolve o cliente Supabase de forma robusta com fallback.

    Tenta localizar o singleton Supabase em diferentes módulos do projeto.
    Retorna o cliente ou None se não encontrado.
    """
    candidates = [
        ("src.infra.supabase_client", ("supabase", "get_supabase", "client")),
        ("src.infra.supabase.db_client", ("supabase", "supabase_client", "client", "get_client")),
        ("src.infra.supabase.auth_client", ("supabase", "supabase_client", "client")),
    ]
    for mod_name, attrs in candidates:
        try:
            mod = importlib.import_module(mod_name)
        except Exception:  # nosec B112 - Fallback pattern: tenta múltiplos caminhos até encontrar módulo válido
            continue
        for attr in attrs:
            if hasattr(mod, attr):
                obj = getattr(mod, attr)
                # Se for função (get_supabase), chama; senão retorna direto
                if callable(obj) and not hasattr(obj, "table"):
                    try:
                        return obj()
                    except Exception:  # nosec B112 - Fallback pattern: tenta invocar se for factory function
                        continue
                return obj
    log.warning("[ClientFiles] Não foi possível resolver o cliente Supabase")
    return None


class ClientFilesDialog(ctk.CTkToplevel):
    """Diálogo para gerenciar arquivos de um cliente.

    Browser funcional com operações: listar, upload, download, excluir.
    """

    def __init__(self, parent: Any, client_id: int, client_name: str = "Cliente", razao_social: str = "", cnpj: str = "", **kwargs: Any):
        """Inicializa o diálogo.

        Args:
            parent: Widget pai
            client_id: ID do cliente
            client_name: Nome do cliente para exibição
            razao_social: Razão social do cliente
            cnpj: CNPJ do cliente
        """
        super().__init__(parent, **kwargs)
        
        # CRÍTICO: Ocultar janela IMEDIATAMENTE para evitar flash branco
        # Pattern withdraw/deiconify: configura tudo antes de exibir
        self.withdraw()

        self.client_id = client_id
        self.client_name = client_name
        self.razao_social = razao_social or client_name
        self.cnpj = cnpj

        # Resolver cliente Supabase
        self.supabase = _resolve_supabase_client()

        # Estado
        self._files: list[dict[str, Any]] = []
        self._org_id: str = ""
        self._loading: bool = False
        self._current_thread: Optional[threading.Thread] = None
        self._nav_stack: list[str] = []  # Pilha de navegação (caminho da pasta atual)
        self._tree_metadata: dict[str, dict[str, Any]] = {}  # iid -> {full_path, is_folder, ...}
        self._progress_queue: queue.Queue = queue.Queue()  # Thread-safe para atualizar progresso
        self._tree_colors: Any = None  # TreeColors do tema atual
        
        # ThreadPoolExecutor para operações de rede (NUNCA na thread principal do Tk)
        self._executor: ThreadPoolExecutor = ThreadPoolExecutor(
            max_workers=4, thread_name_prefix="ClientFiles"
        )
        
        # PROTEÇÃO: Controle de fechamento e after jobs
        self._closing: bool = False
        self._after_ids: set[str] = set()

        # Configurar janela
        title_parts = ["Arquivos"]
        if client_id:
            title_parts.append(f"ID {client_id}")
        if razao_social:
            title_parts.append(razao_social)
        if cnpj:
            title_parts.append(cnpj)
        self.title(" - ".join(title_parts))
        
        # Usar cores do Hub (ANTES de geometry)
        self.configure(fg_color=APP_BG)
        
        # Geometry e resizable
        self.geometry("1000x650")
        
        # Usar Toplevel.resizable para evitar flicker do CTkToplevel.resizable
        try:
            from tkinter import Toplevel
            Toplevel.resizable(self, True, True)
        except Exception:
            self.resizable(True, True)

# Configurar ícone
        try:
            self.iconbitmap(resource_path("rc.ico"))
        except Exception:
            pass  # Ignora se falhar (Linux/Mac ou ícone não encontrado)

        # Centralizar
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (1000 // 2)
        y = (self.winfo_screenheight() // 2) - (650 // 2)
        self.geometry(f"1000x650+{x}+{y}")

        # Tornar modal (transient primeiro, grab depois)
        self.transient(parent)
        
        # Construir UI completa ANTES de exibir
        self._build_ui()
        
        # Processar layout (garante que tudo está renderizado)
        self.update_idletasks()
        
        # Aplicar titlebar escura no Windows (após ter winfo_id)
        try:
            set_win_dark_titlebar(self)
            log.debug("[ClientFiles] Titlebar escura aplicada")
        except Exception as e:
            log.debug(f"[ClientFiles] Erro ao aplicar titlebar escura: {e}")
        
        # EXIBIR JANELA (agora sim, tudo configurado)
        self.deiconify()
        
        # grab_set APÓS deiconify (janela já renderizada, evita flash)
        self.grab_set()

        # Resolver org_id e carregar arquivos
        self._safe_after(100, self._initialize)

        log.info(f"[ClientFiles] Diálogo aberto para cliente ID={client_id}")

    def _initialize(self) -> None:
        """Inicializa org_id e carrega arquivos."""
        # Verificar se o cliente Supabase foi resolvido
        if self.supabase is None:
            log.error("[ClientFiles] Cliente Supabase não disponível")
            self.status_label.configure(
                text="❌ Erro: Cliente Supabase não disponível. Verifique a configuração.", text_color="#ef4444"
            )
            messagebox.showerror(
                "Erro de Configuração",
                "Não foi possível conectar ao Supabase.\n" "Verifique a configuração e tente novamente.",
                parent=self,
            )
            return

        try:
            self._org_id = get_current_org_id(self.supabase)
            log.info(f"[ClientFiles] org_id resolvido: {self._org_id}")
        except Exception as e:
            log.error(f"[ClientFiles] Erro ao resolver org_id: {e}", exc_info=True)
            self._org_id = ""

        self._refresh_files()

    def _build_ui(self) -> None:
        """Constrói a interface do diálogo."""
        # Container principal (flat, sem borda/moldura)
        container = ctk.CTkFrame(self, fg_color=("#F5F5F5", "#1e1e1e"), corner_radius=0, border_width=0)
        container.pack(fill="both", expand=True, padx=0, pady=0)
        
        # Configurar grid: somente row 4 (tree_frame) expande
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=0)  # header
        container.grid_rowconfigure(1, weight=0)  # breadcrumb
        container.grid_rowconfigure(2, weight=0)  # status label
        container.grid_rowconfigure(3, weight=0)  # progress bar
        container.grid_rowconfigure(4, weight=1)  # tree_frame (EXPANDE)
        container.grid_rowconfigure(5, weight=0)  # footer

        # Cabeçalho com título e botões
        header = ctk.CTkFrame(container, fg_color="transparent", border_width=0)
        header.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 5))
        header.grid_columnconfigure(1, weight=1)

        # Botão Voltar
        self.btn_back = ctk.CTkButton(
            header,
            text="⬅ Voltar",
            command=self._on_back,
            width=90,
            height=32,
            fg_color=("#6b7280", "#4b5563"),
            hover_color=("#4b5563", "#374151"),
            border_width=0,
        )
        self.btn_back.grid(row=0, column=0, sticky="w", padx=(0, 10))

        # Título principal
        title_parts = ["📁 Arquivos"]
        if self.client_id:
            title_parts.append(f"ID {self.client_id}")
        if self.razao_social:
            title_parts.append(self.razao_social)
        if self.cnpj:
            title_parts.append(self.cnpj)
        
        title_text = " - ".join(title_parts)
        ctk.CTkLabel(
            header, text=title_text, font=("Segoe UI", 14, "bold"), text_color=TEXT_PRIMARY
        ).grid(row=0, column=1, sticky="w")

        # Botões de ação
        btn_frame = ctk.CTkFrame(header, fg_color="transparent", border_width=0)
        btn_frame.grid(row=0, column=2, sticky="e")

        self.btn_refresh = ctk.CTkButton(
            btn_frame,
            text="Atualizar",
            command=self._refresh_files,
            width=80,
            height=32,
            fg_color=("#2563eb", "#3b82f6"),
            hover_color=("#1d4ed8", "#2563eb"),
            border_width=0,
        )
        self.btn_refresh.pack(side="left", padx=2)

        self.btn_upload = ctk.CTkButton(
            btn_frame,
            text="Upload",
            command=self._on_upload,
            width=80,
            height=32,
            fg_color=("#059669", "#10b981"),
            hover_color=("#047857", "#059669"),
            border_width=0,
        )
        self.btn_upload.pack(side="left", padx=2)

        # Breadcrumb (caminho atual)
        breadcrumb_frame = ctk.CTkFrame(container, fg_color="transparent", border_width=0)
        breadcrumb_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=(5, 5))

        ctk.CTkLabel(
            breadcrumb_frame,
            text="📂 Caminho:",
            font=("Segoe UI", 10, "bold"),
            text_color=TEXT_MUTED,
        ).pack(side="left", padx=(0, 5))

        self.breadcrumb_label = ctk.CTkLabel(
            breadcrumb_frame,
            text="/ (raiz)",
            font=("Segoe UI", 10),
            text_color=TEXT_PRIMARY,
        )
        self.breadcrumb_label.pack(side="left")

        # Status label
        self.status_label = ctk.CTkLabel(
            container,
            text="Carregando arquivos...",
            font=("Segoe UI", 10),
            text_color=TEXT_MUTED,
        )
        self.status_label.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 5))

        # Barra de progresso (inicialmente oculta)
        self.progress_bar = ctk.CTkProgressBar(container, mode="indeterminate", height=4)
        self.progress_bar.grid(row=3, column=0, sticky="ew", padx=15, pady=(0, 5))
        self.progress_bar.grid_remove()  # Ocultar inicialmente

        # Body: TreeView + Scrollbar
        body_frame = ctk.CTkFrame(container, fg_color="transparent", border_width=0)
        body_frame.grid(row=4, column=0, sticky="nsew", padx=15, pady=(0, 10))
        body_frame.grid_rowconfigure(0, weight=1)
        body_frame.grid_columnconfigure(0, weight=1)

        # Treeview
        self.tree = ttk.Treeview(
            body_frame,
            columns=("tipo",),
            show="tree headings",
            selectmode="browse",
        )
        self.tree.grid(row=0, column=0, sticky="nsew")

        # Headings
        self.tree.heading("#0", text="Nome do arquivo/pasta", anchor="w")
        self.tree.heading("tipo", text="Tipo", anchor="w")

        # Columns
        self.tree.column("#0", stretch=True, minwidth=200)
        self.tree.column("tipo", width=120, stretch=False, anchor="w")

        # Scrollbar
        scrollbar = ttk.Scrollbar(body_frame, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Double-click para navegar em pastas
        self.tree.bind("<Double-Button-1>", self._on_tree_double_click)
        
        # Bind para atualizar estados dos botões quando seleção muda
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_selection_change)

        # Registrar Treeview no manager global (aplica tema automaticamente)
        manager = get_treeview_manager()
        _, self._tree_colors = manager.register(
            tree=self.tree,
            master=self,
            style_name="RC.Treeview",
            zebra=True
        )

        # Footer: Botões de ação
        footer_frame = ctk.CTkFrame(container, fg_color="transparent", border_width=0)
        footer_frame.grid(row=5, column=0, sticky="ew", padx=15, pady=(0, 15))

        self.btn_baixar = ctk.CTkButton(
            footer_frame,
            text="Baixar",
            command=self._on_baixar,
            width=100,
            height=32,
            fg_color=("#059669", "#10b981"),
            hover_color=("#047857", "#059669"),
            border_width=0,
            state="disabled",  # Inicialmente desabilitado
        )
        self.btn_baixar.pack(side="left", padx=2)

        self.btn_baixar_zip = ctk.CTkButton(
            footer_frame,
            text="Baixar pasta (.zip)",
            command=self._on_baixar_pasta_zip,
            width=160,
            height=32,
            fg_color=("#7c3aed", "#8b5cf6"),
            hover_color=("#6d28d9", "#7c3aed"),
            border_width=0,
            state="disabled",  # Inicialmente desabilitado
        )
        self.btn_baixar_zip.pack(side="left", padx=2)

        self.btn_excluir = ctk.CTkButton(
            footer_frame,
            text="Excluir",
            command=self._on_excluir,
            width=100,
            height=32,
            fg_color=("#dc2626", "#ef4444"),
            hover_color=("#b91c1c", "#dc2626"),
            border_width=0,
            state="disabled",  # Inicialmente desabilitado
        )
        self.btn_excluir.pack(side="left", padx=2)

        self.btn_visualizar = ctk.CTkButton(
            footer_frame,
            text="Visualizar",
            command=self._on_visualizar,
            width=120,
            height=32,
            fg_color=("#2563eb", "#3b82f6"),
            hover_color=("#1d4ed8", "#2563eb"),
            border_width=0,
            state="disabled",  # Inicialmente desabilitado
        )
        self.btn_visualizar.pack(side="left", padx=2)

        # Botão Fechar à direita
        self.btn_fechar = ctk.CTkButton(
            footer_frame,
            text="Fechar",
            command=self._safe_close,
            width=80,
            height=32,
            fg_color=("#6b7280", "#4b5563"),
            hover_color=("#4b5563", "#374151"),
            border_width=0,
        )
        self.btn_fechar.pack(side="right", padx=2)

        # Aplicar tema inicial (via theme manager)
        # Já aplicado no register_treeview

        # Bind Escape para fechar
        self.bind("<Escape>", lambda e: self._safe_close())
        
        # Protocol WM_DELETE_WINDOW para cleanup
        self.protocol("WM_DELETE_WINDOW", self._safe_close)

        # Iniciar polling da fila de progresso
        self._poll_progress_queue()

    def _show_progress(self, mode: str = "indeterminate") -> None:
        """Mostra barra de progresso.
        
        Args:
            mode: "indeterminate" ou "determinate"
        """
        self.progress_bar.configure(mode=mode)
        self.progress_bar.grid()
        if mode == "indeterminate":
            self.progress_bar.start()

    def _hide_progress(self) -> None:
        """Oculta barra de progresso."""
        self.progress_bar.stop()
        self.progress_bar.grid_remove()

    def _update_progress(self, value: float) -> None:
        """Atualiza valor da barra de progresso (0.0 a 1.0)."""
        self.progress_bar.set(value)

    def _safe_after(self, ms: int, callback: Any) -> Optional[str]:
        """Agenda callback com proteção contra widgets destruídos."""
        if self._closing or not self.winfo_exists():
            return None
        try:
            aid = self.after(ms, callback)
            self._after_ids.add(aid)
            return aid
        except Exception:
            return None
    
    def _cancel_afters(self) -> None:
        """Cancela todos os after jobs pendentes."""
        for aid in list(self._after_ids):
            try:
                self.after_cancel(aid)
            except Exception:
                pass
        self._after_ids.clear()
    
    def _ui_alive(self) -> bool:
        """Verifica se UI ainda está viva e acessível."""
        return (not self._closing) and self.winfo_exists()
    
    def _safe_close(self) -> None:
        """Fecha dialog com cleanup seguro."""
        if self._closing:
            return
        self._closing = True
        self._cancel_afters()
        
        # Shutdown do executor (espera workers terminarem, timeout 2s)
        try:
            self._executor.shutdown(wait=True, cancel_futures=True)
            log.debug("[ClientFiles] ThreadPoolExecutor finalizado")
        except Exception as e:
            log.warning(f"[ClientFiles] Erro ao finalizar executor: {e}")
        
        try:
            self.destroy()
        except Exception:
            pass
    
    def _poll_progress_queue(self) -> None:
        """Verifica fila de progresso e atualiza UI (thread-safe)."""
        if not self._ui_alive():
            return
        
        try:
            while True:
                msg = self._progress_queue.get_nowait()
                action = msg.get("action")
                
                if action == "show":
                    mode = msg.get("mode", "indeterminate")
                    self._show_progress(mode)
                elif action == "hide":
                    self._hide_progress()
                elif action == "update":
                    value = msg.get("value", 0.0)
                    self._update_progress(value)
                elif action == "status":
                    text = msg.get("text", "")
                    self._update_status(text)
        except queue.Empty:
            pass
        
        # Continuar polling apenas se ainda ativo
        if self._ui_alive():
            self._safe_after(100, self._poll_progress_queue)

    def _on_tree_double_click(self, event: Any) -> None:
        """Handler de duplo clique no tree."""
        selection = self.tree.selection()
        if not selection:
            return
        
        iid = selection[0]
        metadata = self._tree_metadata.get(iid)
        if not metadata:
            return
        
        if metadata.get("is_folder"):
            # Navegar para pasta
            folder_name = metadata.get("name", "")
            self._navigate_to_folder(folder_name)

    def _on_tree_selection_change(self, event: Any = None) -> None:
        """Handler quando seleção do TreeView muda."""
        self._update_button_states()

    def _update_button_states(self) -> None:
        """Atualiza estados dos botões baseado na seleção atual."""
        selection = self.tree.selection()
        
        if not selection:
            # Nada selecionado: desabilitar tudo
            self.btn_baixar.configure(state="disabled")
            self.btn_baixar_zip.configure(state="disabled")
            self.btn_excluir.configure(state="disabled")
            self.btn_visualizar.configure(state="disabled")
            return
        
        iid = selection[0]
        metadata = self._tree_metadata.get(iid)
        
        if not metadata:
            # Metadata não encontrado: desabilitar tudo
            self.btn_baixar.configure(state="disabled")
            self.btn_baixar_zip.configure(state="disabled")
            self.btn_excluir.configure(state="disabled")
            self.btn_visualizar.configure(state="disabled")
            return
        
        is_folder = metadata.get("is_folder", False)
        
        if is_folder:
            # Pasta selecionada
            self.btn_baixar.configure(state="disabled")
            self.btn_baixar_zip.configure(state="normal")  # Baixar pasta como ZIP
            self.btn_excluir.configure(state="normal")
            self.btn_visualizar.configure(state="disabled")
        else:
            # Arquivo selecionado
            self.btn_baixar.configure(state="normal")
            self.btn_baixar_zip.configure(state="disabled")
            self.btn_excluir.configure(state="normal")
            self.btn_visualizar.configure(state="normal")

    def _refresh_files(self) -> None:
        """Recarrega lista de arquivos em thread worker."""
        if self._loading:
            log.debug("[ClientFiles] Refresh já em andamento, ignorando")
            return

        self._loading = True
        self._update_status("Carregando arquivos...")
        self._disable_buttons()

        def _load_thread():
            start_time = time.monotonic()
            try:
                bucket = get_clients_bucket()
                base_prefix = client_prefix_for_id(self.client_id, self._org_id)
                current_path = "/".join(self._nav_stack)
                full_prefix = f"{base_prefix}/{current_path}".strip("/") if current_path else base_prefix
                log.info(f"[ClientFiles] Listando: bucket={bucket}, prefix={full_prefix}")

                adapter = SupabaseStorageAdapter(bucket=bucket)
                items = adapter.list_files(full_prefix)
                
                # Instrumentação: log se list_files demorou muito
                log_slow("list_files", start_time)

                # Separar pastas e arquivos, adicionar full_path
                folders = []
                files = []
                for item in items:
                    name = item.get("name", "")
                    # Ignorar arquivos .keep
                    if name.endswith("/.keep") or name.endswith(".keep"):
                        continue
                    
                    # Adicionar full_path (CRÍTICO para evitar 404)
                    item["full_path"] = f"{full_prefix}/{name}".strip("/")
                    
                    # Se tem metadata, é arquivo; senão é pasta
                    if item.get("metadata") is not None:
                        files.append(item)
                    else:
                        folders.append(item)

                # Combinar: pastas primeiro, depois arquivos
                all_items = folders + files

                log.info(f"[ClientFiles] {len(folders)} pasta(s), {len(files)} arquivo(s)")

                # Atualizar UI na thread principal
                self._safe_after(0, lambda items=all_items: self._on_files_loaded(items))

            except Exception as e:
                log.error(f"[ClientFiles] Erro ao listar arquivos: {e}", exc_info=True)
                error_msg = str(e)
                self._safe_after(0, lambda msg=error_msg: self._on_load_error(msg))

        # Submeter para ThreadPoolExecutor (não mais threading.Thread direto)
        self._executor.submit(_load_thread)

    def _on_files_loaded(self, files: list[dict[str, Any]]) -> None:
        """Callback quando arquivos foram carregados."""
        if not self._ui_alive():
            return
        
        self._files = files
        self._loading = False
        self._enable_buttons()
        self._render_files()
        self._update_breadcrumb()
        self._update_back_button()

        count = len(files)
        self._update_status(f"{count} arquivo(s) encontrado(s)")

    def _on_load_error(self, error: str) -> None:
        """Callback quando houve erro ao carregar."""
        if not self._ui_alive():
            return
        
        self._loading = False
        self._enable_buttons()
        self._update_status(f"Erro ao carregar arquivos: {error}")

        messagebox.showerror(
            "Erro",
            f"Não foi possível carregar os arquivos:\n\n{error}\n\nVerifique sua conexão e tente novamente.",
            parent=self,
        )

    def _render_files(self) -> None:
        """Renderiza lista de arquivos na UI (TreeView)."""
        self._render_tree()

    def _render_tree(self) -> None:
        """Renderiza arquivos no TreeView."""
        # Limpar tree
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._tree_metadata.clear()

        if not self._files:
            # Inserir placeholder
            self.tree.insert("", "end", text="📂 Nenhum arquivo encontrado", values=("",), tags=("even",))
            return

        # Renderizar cada item
        for i, file_info in enumerate(self._files):
            name = file_info.get("name", "")
            full_path = file_info.get("full_path", name)
            metadata = file_info.get("metadata", {}) or {}
            is_folder = metadata is None or not metadata

            # Ícone e tipo
            if is_folder:
                icon = "📁"
                tipo = "Pasta"
            elif name.lower().endswith(".pdf"):
                icon = "📕"
                tipo = "PDF"
            elif name.lower().endswith((".jpg", ".jpeg", ".png", ".gif")):
                icon = "🖼️"
                tipo = "Imagem"
            elif name.lower().endswith((".doc", ".docx")):
                icon = "📄"
                tipo = "Word"
            elif name.lower().endswith((".xls", ".xlsx")):
                icon = "📈"
                tipo = "Excel"
            else:
                icon = "📄"
                tipo = "Arquivo"

            display_name = f"{icon} {Path(name).name}"
            tag = "even" if i % 2 == 0 else "odd"

            # Inserir no tree
            iid = self.tree.insert("", "end", text=display_name, values=(tipo,), tags=(tag,))

            # Armazenar metadata
            self._tree_metadata[iid] = {
                "name": name,
                "full_path": full_path,
                "is_folder": is_folder,
                "metadata": metadata,
            }
        
        # Reaplicar zebra para garantir consistência visual
        if self._tree_colors:
            apply_zebra(self.tree, self._tree_colors)

    def _navigate_to_folder(self, folder_name: str) -> None:
        """Navega para uma subpasta."""
        self._nav_stack.append(folder_name)
        self._refresh_files()

    def _get_selected_item(self) -> Optional[dict[str, Any]]:
        """Retorna metadados do item selecionado no tree."""
        selection = self.tree.selection()
        if not selection:
            return None
        iid = selection[0]
        return self._tree_metadata.get(iid)

    def _on_visualizar(self) -> None:
        """Visualiza/abre arquivo selecionado."""
        item = self._get_selected_item()
        if not item:
            messagebox.showwarning("Atenção", "Selecione um arquivo para visualizar.", parent=self)
            return
        if item.get("is_folder"):
            messagebox.showinfo("Info", "Selecione um arquivo, não uma pasta.", parent=self)
            return
        self._on_open_file_from_metadata(item)

    def _on_baixar(self) -> None:
        """Baixa arquivo selecionado."""
        item = self._get_selected_item()
        if not item:
            messagebox.showwarning("Atenção", "Selecione um arquivo para baixar.", parent=self)
            return
        if item.get("is_folder"):
            messagebox.showinfo("Info", "Selecione um arquivo, não uma pasta.", parent=self)
            return
        self._on_download_file_from_metadata(item)

    def _on_excluir(self) -> None:
        """Exclui arquivo selecionado."""
        item = self._get_selected_item()
        if not item:
            messagebox.showwarning("Atenção", "Selecione um arquivo para excluir.", parent=self)
            return
        if item.get("is_folder"):
            messagebox.showinfo("Info", "Não é possível excluir pastas (apenas arquivos).", parent=self)
            return
        self._on_delete_file_from_metadata(item)

    def _on_back(self) -> None:
        """Volta um nível na navegação."""
        if self._nav_stack:
            self._nav_stack.pop()
            self._refresh_files()

    def _update_breadcrumb(self) -> None:
        """Atualiza label do breadcrumb."""
        if not self._nav_stack:
            path_text = "/ (raiz)"
        else:
            path_text = "/" + "/".join(self._nav_stack)
        
        if hasattr(self, "breadcrumb_label") and self.breadcrumb_label.winfo_exists():
            self.breadcrumb_label.configure(text=path_text)

    def _update_back_button(self) -> None:
        """Atualiza estado do botão Voltar."""
        if hasattr(self, "btn_back") and self.btn_back.winfo_exists():
            if self._nav_stack:
                self.btn_back.configure(state="normal")
            else:
                self.btn_back.configure(state="disabled")

    def _on_upload(self) -> None:
        """Handler para upload de arquivos."""
        if self._loading:
            return

        # Selecionar arquivos
        files = filedialog.askopenfilenames(
            title="Selecione os arquivos para upload",
            parent=self,
            filetypes=[
                ("Arquivos PDF", "*.pdf"),
                ("Imagens", "*.jpg;*.jpeg;*.png;*.gif"),
                ("Todos os arquivos", "*.*"),
            ],
        )

        if not files:
            return

        # Pedir subpasta
        dlg = SubpastaDialog(self, default="GERAL")
        self.wait_window(dlg)
        subfolder = dlg.result

        if subfolder is None:  # Cancelado
            return

        subfolder = subfolder.strip() or "GERAL"

        self._upload_files(files, subfolder)

    def _on_baixar_pasta_zip(self) -> None:
        """Baixa pasta selecionada como ZIP."""
        item = self._get_selected_item()
        if not item:
            messagebox.showwarning("Atenção", "Selecione uma pasta para baixar.", parent=self)
            return
        if not item.get("is_folder"):
            messagebox.showinfo("Info", "Selecione uma pasta, não um arquivo.", parent=self)
            return
        
        # Baixar pasta selecionada como ZIP
        folder_name = item.get("name", "pasta")
        full_path = item.get("full_path", "")
        
        # Definir nome padrão do ZIP
        zip_name = f"{Path(folder_name).name}.zip"
        
        # Pedir local para salvar
        save_path = filedialog.asksaveasfilename(
            title="Salvar pasta como ZIP",
            initialfile=zip_name,
            parent=self,
            defaultextension=".zip",
            filetypes=[("Arquivos ZIP", "*.zip")],
        )
        
        if not save_path:
            return
        
        self._download_folder_as_zip(full_path, save_path)

    def _download_folder_as_zip(self, folder_prefix: str, save_path: str) -> None:
        """Baixa pasta específica como ZIP."""
        self._loading = True
        self._update_status("Preparando download ZIP...")
        self._disable_buttons()
        
        # Mostrar progresso indeterminado
        self._progress_queue.put({"action": "show", "mode": "indeterminate"})

        def _download_zip_thread():
            try:
                bucket = get_clients_bucket()
                log.info(f"[ClientFiles] Iniciando download ZIP: prefix={folder_prefix}")

                adapter = SupabaseStorageAdapter(bucket=bucket)

                # Criar ZIP temporário
                temp_zip = Path(tempfile.gettempdir()) / f"rc_zip_{os.getpid()}.zip"

                with zipfile.ZipFile(temp_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                    # Função recursiva para listar e baixar arquivos
                    def _collect_files(prefix: str, relative_path: str = ""):
                        items = adapter.list_files(prefix)
                        file_count = 0

                        for item in items:
                            name = item.get("name", "")
                            if name.endswith("/.keep") or name.endswith(".keep"):
                                continue

                            full_item_path = f"{prefix}/{name}".strip("/")
                            relative_item_path = f"{relative_path}/{name}".strip("/") if relative_path else name

                            metadata = item.get("metadata")
                            if metadata is not None:
                                # É arquivo - baixar e adicionar ao ZIP
                                self._progress_queue.put({
                                    "action": "status",
                                    "text": f"Baixando {relative_item_path}..."
                                })
                                
                                try:
                                    content = adapter.download_file(full_item_path)
                                    if isinstance(content, bytes):
                                        zf.writestr(relative_item_path, content)
                                    else:
                                        # content é path local
                                        zf.write(content, relative_item_path)
                                    file_count += 1
                                except Exception as e:
                                    log.warning(f"[ClientFiles] Erro ao baixar {full_item_path}: {e}")
                            else:
                                # É pasta - recursão
                                file_count += _collect_files(full_item_path, relative_item_path)

                        return file_count

                    # Iniciar coleta recursiva
                    total_files = _collect_files(folder_prefix)

                log.info(f"[ClientFiles] ZIP criado com {total_files} arquivo(s)")

                # Mover ZIP para local escolhido
                import shutil
                shutil.move(str(temp_zip), save_path)

                self._safe_after(0, lambda count=total_files, path=save_path: self._on_download_zip_complete(count, path))

            except Exception as e:
                log.error(f"[ClientFiles] Erro no download ZIP: {e}", exc_info=True)
                error_msg = str(e)
                self._safe_after(0, lambda msg=error_msg: self._on_download_zip_error(msg))

        # Submeter para ThreadPoolExecutor
        self._executor.submit(_download_zip_thread)

    def _on_download_zip(self) -> None:
        """Baixa pasta atual completa como ZIP (recursivo)."""
        if self._loading:
            return

        # Definir nome padrão do ZIP
        if self._nav_stack:
            zip_name = f"{self._nav_stack[-1]}.zip"
        else:
            zip_name = f"cliente_{self.client_id}_arquivos.zip"

        # Pedir local para salvar
        save_path = filedialog.asksaveasfilename(
            title="Salvar pasta como ZIP",
            initialfile=zip_name,
            parent=self,
            defaultextension=".zip",
            filetypes=[("Arquivos ZIP", "*.zip")],
        )

        if not save_path:
            return

        self._loading = True
        self._update_status("Preparando download ZIP...")
        self._disable_buttons()

        def _download_zip_thread():
            try:
                bucket = get_clients_bucket()
                base_prefix = client_prefix_for_id(self.client_id, self._org_id)
                current_path = "/".join(self._nav_stack)
                full_prefix = f"{base_prefix}/{current_path}".strip("/") if current_path else base_prefix

                log.info(f"[ClientFiles] Iniciando download ZIP: prefix={full_prefix}")

                adapter = SupabaseStorageAdapter(bucket=bucket)

                # Criar ZIP temporário
                temp_zip = Path(tempfile.gettempdir()) / f"rc_zip_{os.getpid()}.zip"

                with zipfile.ZipFile(temp_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                    # Função recursiva para listar e baixar arquivos
                    def _collect_files(prefix: str, relative_path: str = ""):
                        items = adapter.list_files(prefix)
                        file_count = 0

                        for item in items:
                            name = item.get("name", "")
                            if name.endswith("/.keep") or name.endswith(".keep"):
                                continue

                            full_item_path = f"{prefix}/{name}".strip("/")
                            relative_item_path = f"{relative_path}/{name}".strip("/") if relative_path else name

                            metadata = item.get("metadata")
                            if metadata is not None:
                                # É arquivo - baixar e adicionar ao ZIP
                                self.after(0, lambda p=relative_item_path: self._update_status(f"Baixando {p}..."))
                                
                                try:
                                    content = adapter.download_file(full_item_path)
                                    if isinstance(content, bytes):
                                        zf.writestr(relative_item_path, content)
                                    else:
                                        # content é path local
                                        zf.write(content, relative_item_path)
                                    file_count += 1
                                except Exception as e:
                                    log.warning(f"[ClientFiles] Erro ao baixar {full_item_path}: {e}")
                            else:
                                # É pasta - recursão
                                file_count += _collect_files(full_item_path, relative_item_path)

                        return file_count

                    # Iniciar coleta recursiva
                    total_files = _collect_files(full_prefix)

                log.info(f"[ClientFiles] ZIP criado com {total_files} arquivo(s)")

                # Mover ZIP para local escolhido
                import shutil
                shutil.move(str(temp_zip), save_path)

                self._safe_after(0, lambda count=total_files, path=save_path: self._on_download_zip_complete(count, path))

            except Exception as e:
                log.error(f"[ClientFiles] Erro no download ZIP: {e}", exc_info=True)
                error_msg = str(e)
                self._safe_after(0, lambda msg=error_msg: self._on_download_zip_error(msg))

        # Submeter para ThreadPoolExecutor
        self._executor.submit(_download_zip_thread)

    def _on_download_zip_complete(self, file_count: int, save_path: str) -> None:
        """Callback quando download ZIP foi concluído."""
        if not self._ui_alive():
            return
        
        self._loading = False
        self._enable_buttons()
        self._progress_queue.put({"action": "hide"})
        self._update_status("ZIP criado com sucesso")

        messagebox.showinfo(
            "Download ZIP Concluído",
            f"Pasta baixada com sucesso!\n\n{file_count} arquivo(s) no ZIP\n\nSalvo em:\n{save_path}",
            parent=self,
        )

    def _on_download_zip_error(self, error: str) -> None:
        """Callback quando houve erro no download ZIP."""
        if not self._ui_alive():
            return
        
        self._loading = False
        self._enable_buttons()
        self._progress_queue.put({"action": "hide"})
        self._update_status("Erro no download ZIP")

        messagebox.showerror("Erro no Download ZIP", f"Não foi possível criar o ZIP:\n\n{error}", parent=self)

    def _upload_files(self, file_paths: tuple[str, ...], subfolder: str) -> None:
        """Executa upload de arquivos em thread."""
        self._loading = True
        self._update_status(f"Enviando {len(file_paths)} arquivo(s)...")
        self._disable_buttons()
        
        # Mostrar progresso determinado
        self._progress_queue.put({"action": "show", "mode": "determinate"})

        def _upload_thread():
            try:
                bucket = get_clients_bucket()
                prefix = client_prefix_for_id(self.client_id, self._org_id)
                adapter = SupabaseStorageAdapter(bucket=bucket)

                uploaded_count = 0
                total = len(file_paths)
                
                for file_path in file_paths:
                    file_name = Path(file_path).name
                    remote_key = f"{prefix}/{subfolder}/{file_name}"

                    log.info(f"[ClientFiles] Uploading: {file_name} -> {remote_key}")

                    # Upload
                    adapter.upload_file(file_path, remote_key)
                    uploaded_count += 1

                    # Atualizar progresso
                    progress = uploaded_count / total
                    self._progress_queue.put({
                        "action": "update",
                        "value": progress
                    })
                    self._progress_queue.put({
                        "action": "status",
                        "text": f"Enviados {uploaded_count}/{total} arquivo(s)..."
                    })

                log.info(f"[ClientFiles] Upload concluído: {uploaded_count} arquivo(s)")
                self._safe_after(0, lambda: self._on_upload_complete(uploaded_count))

            except Exception as e:
                log.error(f"[ClientFiles] Erro no upload: {e}", exc_info=True)
                self._safe_after(0, lambda: self._on_upload_error(str(e)))

        # Submeter para ThreadPoolExecutor
        self._executor.submit(_upload_thread)

    def _on_upload_complete(self, count: int) -> None:
        """Callback quando upload foi concluído."""
        if not self._ui_alive():
            return
        
        self._loading = False
        self._enable_buttons()
        self._progress_queue.put({"action": "hide"})

        messagebox.showinfo("Upload Concluído", f"{count} arquivo(s) enviado(s) com sucesso!", parent=self)

        # Recarregar lista
        self._refresh_files()

    def _on_upload_error(self, error: str) -> None:
        """Callback quando houve erro no upload."""
        if not self._ui_alive():
            return
        
        self._loading = False
        self._enable_buttons()
        self._progress_queue.put({"action": "hide"})
        self._update_status("Erro no upload")

        messagebox.showerror("Erro no Upload", f"Não foi possível enviar os arquivos:\n\n{error}", parent=self)

    def _on_open_file_from_metadata(self, metadata: dict[str, Any]) -> None:
        """Abre arquivo (download temporário + abrir com sistema)."""
        if self._loading:
            return

        name = metadata.get("name", "")
        full_path = metadata.get("full_path", name)  # CRÍTICO: usar full_path

        self._loading = True
        self._update_status(f"Abrindo {Path(name).name}...")
        self._disable_buttons()

        def _open_thread():
            try:
                bucket = get_clients_bucket()
                adapter = SupabaseStorageAdapter(bucket=bucket)

                # Download para pasta temporária
                temp_dir = tempfile.gettempdir()
                file_name = Path(name).name
                local_path = Path(temp_dir) / "rc_temp_files" / file_name
                local_path.parent.mkdir(parents=True, exist_ok=True)

                # Usar full_path completo (CRÍTICO para evitar 404)
                remote_key = full_path
                log.info(f"[ClientFiles] Downloading para abrir: {remote_key} -> {local_path}")

                content = adapter.download_file(remote_key)

                # Salvar conteúdo
                if isinstance(content, bytes):
                    local_path.write_bytes(content)
                else:
                    # content é path string
                    import shutil

                    shutil.copy(content, local_path)

                log.info(f"[ClientFiles] Arquivo baixado, abrindo: {local_path}")

                # Abrir com sistema (Windows: os.startfile)
                if os.name == "nt":  # Windows
                    os.startfile(str(local_path))  # nosec B606 - Local path controlado (download de Supabase Storage)
                elif os.name == "posix":  # Linux/Mac
                    import subprocess  # nosec B404 - Necessário para xdg-open em Linux

                    subprocess.Popen(["xdg-open", str(local_path)])  # nosec B603, B607 - xdg-open com path local controlado

                self._safe_after(0, lambda fn=file_name: self._on_open_complete(fn))

            except Exception as e:
                log.error(f"[ClientFiles] Erro ao abrir arquivo: {e}", exc_info=True)
                error_msg = str(e)
                self._safe_after(0, lambda msg=error_msg: self._on_open_error(msg))

        # Submeter para ThreadPoolExecutor
        self._executor.submit(_open_thread)

    def _on_open_complete(self, file_name: str) -> None:
        """Callback quando arquivo foi aberto."""
        if not self._ui_alive():
            return
        
        self._loading = False
        self._enable_buttons()
        self._update_status(f"{file_name} aberto")

    def _on_open_error(self, error: str) -> None:
        """Callback quando houve erro ao abrir."""
        if not self._ui_alive():
            return
        
        self._loading = False
        self._enable_buttons()
        self._update_status("Erro ao abrir arquivo")

        messagebox.showerror("Erro", f"Não foi possível abrir o arquivo:\n\n{error}", parent=self)

    def _on_download_file_from_metadata(self, metadata: dict[str, Any]) -> None:
        """Download de arquivo para local escolhido pelo usuário."""
        if self._loading:
            return

        name = metadata.get("name", "")
        full_path = metadata.get("full_path", name)  # CRÍTICO: usar full_path
        file_name = Path(name).name

        # Pedir local para salvar
        save_path = filedialog.asksaveasfilename(
            title="Salvar arquivo como",
            initialfile=file_name,
            parent=self,
            defaultextension=Path(file_name).suffix,
        )

        if not save_path:
            return

        self._loading = True
        self._update_status(f"Baixando {file_name}...")
        self._disable_buttons()
        
        # Mostrar progresso indeterminado
        self._progress_queue.put({"action": "show", "mode": "indeterminate"})

        def _download_thread():
            try:
                bucket = get_clients_bucket()
                adapter = SupabaseStorageAdapter(bucket=bucket)

                # Usar full_path completo (CRÍTICO para evitar 404)
                remote_key = full_path
                log.info(f"[ClientFiles] Downloading: {remote_key} -> {save_path}")

                content = adapter.download_file(remote_key)

                # Salvar conteúdo
                if isinstance(content, bytes):
                    Path(save_path).write_bytes(content)
                else:
                    # content é path string
                    import shutil

                    shutil.copy(content, save_path)

                log.info(f"[ClientFiles] Download concluído: {save_path}")
                self._safe_after(0, lambda fn=file_name, sp=save_path: self._on_download_complete(fn, sp))

            except Exception as e:
                log.error(f"[ClientFiles] Erro no download: {e}", exc_info=True)
                error_msg = str(e)
                self._safe_after(0, lambda msg=error_msg: self._on_download_error(msg))

        # Submeter para ThreadPoolExecutor
        self._executor.submit(_download_thread)

    def _on_download_complete(self, file_name: str, save_path: str) -> None:
        """Callback quando download foi concluído."""
        if not self._ui_alive():
            return
        
        self._loading = False
        self._enable_buttons()
        self._progress_queue.put({"action": "hide"})
        self._update_status(f"{file_name} salvo")

        messagebox.showinfo("Download Concluído", f"Arquivo salvo em:\n{save_path}", parent=self)

    def _on_download_error(self, error: str) -> None:
        """Callback quando houve erro no download."""
        if not self._ui_alive():
            return
        
        self._loading = False
        self._enable_buttons()
        self._progress_queue.put({"action": "hide"})
        self._update_status("Erro no download")

        messagebox.showerror("Erro no Download", f"Não foi possível baixar o arquivo:\n\n{error}", parent=self)

    def _on_delete_file_from_metadata(self, metadata: dict[str, Any]) -> None:
        """Exclui arquivo após confirmação."""
        if self._loading:
            return

        name = metadata.get("name", "")
        full_path = metadata.get("full_path", name)  # CRÍTICO: usar full_path
        file_name = Path(name).name

        # Confirmar exclusão
        confirm = messagebox.askyesno(
            "Confirmar Exclusão",
            f"Deseja realmente excluir o arquivo?\n\n{file_name}\n\nEsta ação não pode ser desfeita.",
            parent=self,
            icon="warning",
        )

        if not confirm:
            return

        self._loading = True
        self._update_status(f"Excluindo {file_name}...")
        self._disable_buttons()

        def _delete_thread():
            try:
                bucket = get_clients_bucket()
                adapter = SupabaseStorageAdapter(bucket=bucket)

                # Usar full_path completo (CRÍTICO para evitar 404)
                remote_key = full_path
                log.info(f"[ClientFiles] Deleting: {remote_key}")

                success = adapter.delete_file(remote_key)

                if success:
                    log.info(f"[ClientFiles] Arquivo excluído: {remote_key}")
                    self._safe_after(0, lambda fn=file_name: self._on_delete_complete(fn))
                else:
                    error_msg = "Falha ao excluir arquivo"
                    self._safe_after(0, lambda msg=error_msg: self._on_delete_error(msg))

            except Exception as e:
                log.error(f"[ClientFiles] Erro ao excluir: {e}", exc_info=True)
                error_msg = str(e)
                self._safe_after(0, lambda msg=error_msg: self._on_delete_error(msg))

        # Submeter para ThreadPoolExecutor
        self._executor.submit(_delete_thread)

    def _on_delete_complete(self, file_name: str) -> None:
        """Callback quando arquivo foi excluído."""
        if not self._ui_alive():
            return
        
        self._loading = False
        self._enable_buttons()

        messagebox.showinfo("Arquivo Excluído", f"{file_name} foi excluído com sucesso.", parent=self)

        # Recarregar lista
        self._refresh_files()

    def _on_delete_error(self, error: str) -> None:
        """Callback quando houve erro ao excluir."""
        if not self._ui_alive():
            return
        
        self._loading = False
        self._enable_buttons()
        self._update_status("Erro ao excluir arquivo")

        messagebox.showerror(
            "Erro",
            f"Não foi possível excluir o arquivo:\n\n{error}\n\nVerifique se você tem permissão para esta operação.",
            parent=self,
        )

    def _update_status(self, text: str) -> None:
        """Atualiza texto do status."""
        if hasattr(self, "status_label") and self.status_label.winfo_exists():
            self.status_label.configure(text=text)

    def _disable_buttons(self) -> None:
        """Desabilita botões durante operações."""
        if not self._ui_alive():
            return
        
        import tkinter as tk
        
        buttons = [
            "btn_refresh", "btn_upload", "btn_back", "btn_visualizar",
            "btn_baixar", "btn_baixar_zip", "btn_excluir"
        ]
        
        for btn_name in buttons:
            if hasattr(self, btn_name):
                btn = getattr(self, btn_name)
                if btn is not None and btn.winfo_exists():
                    try:
                        btn.configure(state="disabled")
                    except tk.TclError:
                        pass

    def _enable_buttons(self) -> None:
        """Habilita botões após operações."""
        if not self._ui_alive():
            return
        
        import tkinter as tk
        
        # Botões que sempre devem ser habilitados
        for btn_name in ["btn_refresh", "btn_upload"]:
            if hasattr(self, btn_name):
                btn = getattr(self, btn_name)
                if btn is not None and btn.winfo_exists():
                    try:
                        btn.configure(state="normal")
                    except tk.TclError:
                        pass
        
        # Atualizar estados dos botões do footer baseado na seleção
        self._update_button_states()
        self._update_back_button()  # Atualiza estado do botão Voltar

    @staticmethod
    def _format_size(size: int) -> str:
        """Formata tamanho de arquivo em formato legível."""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.1f} GB"
