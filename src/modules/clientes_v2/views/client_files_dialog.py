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
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any, Optional

from src.ui.ctk_config import ctk
from src.ui.ui_tokens import SURFACE, SURFACE_DARK, TEXT_PRIMARY, TEXT_MUTED, APP_BG
from src.adapters.storage.supabase_storage import SupabaseStorageAdapter
from src.modules.uploads.components.helpers import get_clients_bucket, client_prefix_for_id, get_current_org_id
from src.modules.clientes.forms.client_subfolder_prompt import SubpastaDialog

log = logging.getLogger(__name__)


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

    def __init__(self, parent: Any, client_id: int, client_name: str = "Cliente", **kwargs: Any):
        """Inicializa o diálogo.

        Args:
            parent: Widget pai
            client_id: ID do cliente
            client_name: Nome do cliente para exibição
        """
        super().__init__(parent, **kwargs)

        self.client_id = client_id
        self.client_name = client_name

        # Resolver cliente Supabase
        self.supabase = _resolve_supabase_client()

        # Estado
        self._files: list[dict[str, Any]] = []
        self._org_id: str = ""
        self._loading: bool = False
        self._current_thread: Optional[threading.Thread] = None

        # Configurar janela
        self.title(f"Arquivos - {client_name}")
        self.geometry("1000x650")
        self.resizable(True, True)

        # Centralizar
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (1000 // 2)
        y = (self.winfo_screenheight() // 2) - (650 // 2)
        self.geometry(f"+{x}+{y}")

        # Tornar modal
        self.transient(parent)
        self.grab_set()

        # Usar cores do Hub
        self.configure(fg_color=APP_BG)

        self._build_ui()

        # Resolver org_id e carregar arquivos
        self.after(100, self._initialize)

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
        # Container principal
        container = ctk.CTkFrame(self, fg_color=SURFACE_DARK, corner_radius=12)
        container.pack(fill="both", expand=True, padx=20, pady=20)
        container.grid_rowconfigure(1, weight=1)
        container.grid_columnconfigure(0, weight=1)

        # Cabeçalho com título e botões
        header = ctk.CTkFrame(container, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header, text=f"📁 Arquivos - {self.client_name}", font=("Segoe UI", 18, "bold"), text_color=TEXT_PRIMARY
        ).grid(row=0, column=0, sticky="w")

        # Botões de ação
        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.grid(row=0, column=1, sticky="e")

        self.btn_refresh = ctk.CTkButton(
            btn_frame,
            text="🔄 Atualizar",
            command=self._refresh_files,
            width=100,
            fg_color=("#2563eb", "#3b82f6"),
            hover_color=("#1d4ed8", "#2563eb"),
        )
        self.btn_refresh.pack(side="left", padx=5)

        self.btn_upload = ctk.CTkButton(
            btn_frame,
            text="⬆️ Upload",
            command=self._on_upload,
            width=100,
            fg_color=("#059669", "#10b981"),
            hover_color=("#047857", "#059669"),
        )
        self.btn_upload.pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame, text="✖ Fechar", command=self.destroy, width=100, fg_color="gray", hover_color="darkgray"
        ).pack(side="left", padx=5)

        # Status label
        self.status_label = ctk.CTkLabel(
            container,
            text="Carregando arquivos...",
            font=("Segoe UI", 11),
            text_color=TEXT_MUTED,
        )
        self.status_label.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 5))

        # Lista de arquivos (scrollable)
        self.files_container = ctk.CTkScrollableFrame(container, fg_color=SURFACE, corner_radius=8)
        self.files_container.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.files_container.grid_columnconfigure(0, weight=1)

        # Bind Escape para fechar
        self.bind("<Escape>", lambda e: self.destroy())

    def _refresh_files(self) -> None:
        """Recarrega lista de arquivos em thread."""
        if self._loading:
            log.debug("[ClientFiles] Refresh já em andamento, ignorando")
            return

        self._loading = True
        self._update_status("Carregando arquivos...")
        self._disable_buttons()

        def _load_thread():
            try:
                bucket = get_clients_bucket()
                prefix = client_prefix_for_id(self.client_id, self._org_id)
                log.info(f"[ClientFiles] Listando arquivos: bucket={bucket}, prefix={prefix}")

                adapter = SupabaseStorageAdapter(bucket=bucket)
                items = adapter.list_files(prefix)

                # Filtrar apenas arquivos (não pastas)
                files = [item for item in items if item.get("metadata") is not None]

                log.info(f"[ClientFiles] {len(files)} arquivo(s) encontrado(s)")

                # Atualizar UI na thread principal
                self.after(0, lambda: self._on_files_loaded(files))

            except Exception as e:
                log.error(f"[ClientFiles] Erro ao listar arquivos: {e}", exc_info=True)
                self.after(0, lambda: self._on_load_error(str(e)))

        thread = threading.Thread(target=_load_thread, daemon=True)
        self._current_thread = thread
        thread.start()

    def _on_files_loaded(self, files: list[dict[str, Any]]) -> None:
        """Callback quando arquivos foram carregados."""
        self._files = files
        self._loading = False
        self._enable_buttons()
        self._render_files()

        count = len(files)
        self._update_status(f"{count} arquivo(s) encontrado(s)")

    def _on_load_error(self, error: str) -> None:
        """Callback quando houve erro ao carregar."""
        self._loading = False
        self._enable_buttons()
        self._update_status(f"Erro ao carregar arquivos: {error}")

        messagebox.showerror(
            "Erro",
            f"Não foi possível carregar os arquivos:\n\n{error}\n\nVerifique sua conexão e tente novamente.",
            parent=self,
        )

    def _render_files(self) -> None:
        """Renderiza lista de arquivos na UI."""
        # Limpar container
        for widget in self.files_container.winfo_children():
            widget.destroy()

        if not self._files:
            ctk.CTkLabel(
                self.files_container,
                text="📂 Nenhum arquivo encontrado",
                font=("Segoe UI", 14),
                text_color=TEXT_MUTED,
            ).pack(pady=40)
            return

        # Renderizar cada arquivo
        for i, file_info in enumerate(self._files):
            self._render_file_item(file_info, i)

    def _render_file_item(self, file_info: dict[str, Any], index: int) -> None:
        """Renderiza um item de arquivo."""
        name = file_info.get("name", "arquivo")
        metadata = file_info.get("metadata", {}) or {}
        size = metadata.get("size", 0)

        # Frame do item
        item_frame = ctk.CTkFrame(
            self.files_container,
            fg_color=SURFACE_DARK if index % 2 == 0 else SURFACE,
            corner_radius=4,
        )
        item_frame.pack(fill="x", padx=5, pady=2)
        item_frame.grid_columnconfigure(1, weight=1)

        # Ícone
        icon = "📄"
        if name.lower().endswith(".pdf"):
            icon = "📕"
        elif name.lower().endswith((".jpg", ".jpeg", ".png", ".gif")):
            icon = "🖼️"

        ctk.CTkLabel(
            item_frame,
            text=icon,
            font=("Segoe UI", 16),
            width=40,
        ).grid(row=0, column=0, padx=10, pady=10)

        # Info do arquivo
        info_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
        info_frame.grid(row=0, column=1, sticky="w", padx=5, pady=10)

        # Nome do arquivo (apenas última parte do path)
        display_name = Path(name).name
        ctk.CTkLabel(
            info_frame,
            text=display_name,
            font=("Segoe UI", 12, "bold"),
            text_color=TEXT_PRIMARY,
            anchor="w",
        ).pack(anchor="w")

        # Tamanho
        size_str = self._format_size(size)
        ctk.CTkLabel(
            info_frame,
            text=f"{size_str}",
            font=("Segoe UI", 10),
            text_color=TEXT_MUTED,
            anchor="w",
        ).pack(anchor="w")

        # Botões de ação
        actions_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
        actions_frame.grid(row=0, column=2, padx=10, pady=10)

        ctk.CTkButton(
            actions_frame,
            text="📂 Abrir",
            command=lambda f=file_info: self._on_open_file(f),
            width=80,
            height=28,
            fg_color=("#2563eb", "#3b82f6"),
            hover_color=("#1d4ed8", "#2563eb"),
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            actions_frame,
            text="⬇️ Baixar",
            command=lambda f=file_info: self._on_download_file(f),
            width=80,
            height=28,
            fg_color=("#059669", "#10b981"),
            hover_color=("#047857", "#059669"),
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            actions_frame,
            text="🗑️ Excluir",
            command=lambda f=file_info: self._on_delete_file(f),
            width=80,
            height=28,
            fg_color=("#dc2626", "#ef4444"),
            hover_color=("#b91c1c", "#dc2626"),
        ).pack(side="left", padx=2)

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

    def _upload_files(self, file_paths: tuple[str, ...], subfolder: str) -> None:
        """Executa upload de arquivos em thread."""
        self._loading = True
        self._update_status(f"Enviando {len(file_paths)} arquivo(s)...")
        self._disable_buttons()

        def _upload_thread():
            try:
                bucket = get_clients_bucket()
                prefix = client_prefix_for_id(self.client_id, self._org_id)
                adapter = SupabaseStorageAdapter(bucket=bucket)

                uploaded_count = 0
                for file_path in file_paths:
                    file_name = Path(file_path).name
                    remote_key = f"{prefix}/{subfolder}/{file_name}"

                    log.info(f"[ClientFiles] Uploading: {file_name} -> {remote_key}")

                    # Upload
                    adapter.upload_file(file_path, remote_key)
                    uploaded_count += 1

                    # Atualizar progresso
                    self.after(
                        0, lambda c=uploaded_count: self._update_status(f"Enviados {c}/{len(file_paths)} arquivo(s)...")
                    )

                log.info(f"[ClientFiles] Upload concluído: {uploaded_count} arquivo(s)")
                self.after(0, lambda: self._on_upload_complete(uploaded_count))

            except Exception as e:
                log.error(f"[ClientFiles] Erro no upload: {e}", exc_info=True)
                self.after(0, lambda: self._on_upload_error(str(e)))

        thread = threading.Thread(target=_upload_thread, daemon=True)
        self._current_thread = thread
        thread.start()

    def _on_upload_complete(self, count: int) -> None:
        """Callback quando upload foi concluído."""
        self._loading = False
        self._enable_buttons()

        messagebox.showinfo("Upload Concluído", f"{count} arquivo(s) enviado(s) com sucesso!", parent=self)

        # Recarregar lista
        self._refresh_files()

    def _on_upload_error(self, error: str) -> None:
        """Callback quando houve erro no upload."""
        self._loading = False
        self._enable_buttons()
        self._update_status("Erro no upload")

        messagebox.showerror("Erro no Upload", f"Não foi possível enviar os arquivos:\n\n{error}", parent=self)

    def _on_open_file(self, file_info: dict[str, Any]) -> None:
        """Abre arquivo (download temporário + abrir com sistema)."""
        if self._loading:
            return

        name = file_info.get("name", "")

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

                log.info(f"[ClientFiles] Downloading para abrir: {name} -> {local_path}")

                content = adapter.download_file(name)

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

                self.after(0, lambda: self._on_open_complete(file_name))

            except Exception as e:
                log.error(f"[ClientFiles] Erro ao abrir arquivo: {e}", exc_info=True)
                self.after(0, lambda: self._on_open_error(str(e)))

        thread = threading.Thread(target=_open_thread, daemon=True)
        self._current_thread = thread
        thread.start()

    def _on_open_complete(self, file_name: str) -> None:
        """Callback quando arquivo foi aberto."""
        self._loading = False
        self._enable_buttons()
        self._update_status(f"{file_name} aberto")

    def _on_open_error(self, error: str) -> None:
        """Callback quando houve erro ao abrir."""
        self._loading = False
        self._enable_buttons()
        self._update_status("Erro ao abrir arquivo")

        messagebox.showerror("Erro", f"Não foi possível abrir o arquivo:\n\n{error}", parent=self)

    def _on_download_file(self, file_info: dict[str, Any]) -> None:
        """Download de arquivo para local escolhido pelo usuário."""
        if self._loading:
            return

        name = file_info.get("name", "")
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

        def _download_thread():
            try:
                bucket = get_clients_bucket()
                adapter = SupabaseStorageAdapter(bucket=bucket)

                log.info(f"[ClientFiles] Downloading: {name} -> {save_path}")

                content = adapter.download_file(name)

                # Salvar conteúdo
                if isinstance(content, bytes):
                    Path(save_path).write_bytes(content)
                else:
                    # content é path string
                    import shutil

                    shutil.copy(content, save_path)

                log.info(f"[ClientFiles] Download concluído: {save_path}")
                self.after(0, lambda: self._on_download_complete(file_name, save_path))

            except Exception as e:
                log.error(f"[ClientFiles] Erro no download: {e}", exc_info=True)
                self.after(0, lambda: self._on_download_error(str(e)))

        thread = threading.Thread(target=_download_thread, daemon=True)
        self._current_thread = thread
        thread.start()

    def _on_download_complete(self, file_name: str, save_path: str) -> None:
        """Callback quando download foi concluído."""
        self._loading = False
        self._enable_buttons()
        self._update_status(f"{file_name} salvo")

        messagebox.showinfo("Download Concluído", f"Arquivo salvo em:\n{save_path}", parent=self)

    def _on_download_error(self, error: str) -> None:
        """Callback quando houve erro no download."""
        self._loading = False
        self._enable_buttons()
        self._update_status("Erro no download")

        messagebox.showerror("Erro no Download", f"Não foi possível baixar o arquivo:\n\n{error}", parent=self)

    def _on_delete_file(self, file_info: dict[str, Any]) -> None:
        """Exclui arquivo após confirmação."""
        if self._loading:
            return

        name = file_info.get("name", "")
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

                log.info(f"[ClientFiles] Deleting: {name}")

                success = adapter.delete_file(name)

                if success:
                    log.info(f"[ClientFiles] Arquivo excluído: {name}")
                    self.after(0, lambda: self._on_delete_complete(file_name))
                else:
                    self.after(0, lambda: self._on_delete_error("Falha ao excluir arquivo"))

            except Exception as e:
                log.error(f"[ClientFiles] Erro ao excluir: {e}", exc_info=True)
                self.after(0, lambda: self._on_delete_error(str(e)))

        thread = threading.Thread(target=_delete_thread, daemon=True)
        self._current_thread = thread
        thread.start()

    def _on_delete_complete(self, file_name: str) -> None:
        """Callback quando arquivo foi excluído."""
        self._loading = False
        self._enable_buttons()

        messagebox.showinfo("Arquivo Excluído", f"{file_name} foi excluído com sucesso.", parent=self)

        # Recarregar lista
        self._refresh_files()

    def _on_delete_error(self, error: str) -> None:
        """Callback quando houve erro ao excluir."""
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
        if hasattr(self, "btn_refresh"):
            self.btn_refresh.configure(state="disabled")
        if hasattr(self, "btn_upload"):
            self.btn_upload.configure(state="disabled")

    def _enable_buttons(self) -> None:
        """Habilita botões após operações."""
        if hasattr(self, "btn_refresh"):
            self.btn_refresh.configure(state="normal")
        if hasattr(self, "btn_upload"):
            self.btn_upload.configure(state="normal")

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
