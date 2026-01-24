# -*- coding: utf-8 -*-
"""Diálogo de upload de arquivos para ClientesV2 - FASE 3.3.

Dialog 100% CustomTkinter para seleção e upload de arquivos para cliente.
"""

from __future__ import annotations

import logging
import mimetypes
from pathlib import Path
from typing import Any, Callable, Optional

from tkinter import filedialog, messagebox

from src.ui.ctk_config import ctk
from src.ui.ui_tokens import SURFACE, SURFACE_DARK, TEXT_PRIMARY, TEXT_MUTED, APP_BG

log = logging.getLogger(__name__)

# Extensões de arquivo aceitas (podem ser configuradas)
ALLOWED_EXTENSIONS = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".tiff",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".txt",
    ".csv",
    ".zip",
    ".rar",
}

# MIME types aceitos
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/bmp",
    "image/tiff",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain",
    "text/csv",
    "application/zip",
    "application/x-zip-compressed",  # ZIP tem múltiplos MIME types
    "application/x-rar-compressed",
    "application/vnd.rar",
}


class ClientUploadDialog(ctk.CTkToplevel):
    """Diálogo para upload de arquivos para cliente."""

    def __init__(
        self,
        parent: Any,
        client_id: int,
        client_name: str = "",
        on_complete: Optional[Callable[[], None]] = None,
        **kwargs: Any,
    ):
        """Inicializa o diálogo.

        Args:
            parent: Widget pai
            client_id: ID do cliente
            client_name: Nome do cliente (para exibição)
            on_complete: Callback após upload bem-sucedido
        """
        super().__init__(parent, **kwargs)

        self.client_id = client_id
        self.client_name = client_name
        self.on_complete = on_complete
        self.selected_files: list[str] = []

        # Configurar janela
        self.title(f"Upload de Arquivos - {client_name or f'Cliente {client_id}'}")
        self.geometry("700x500")
        self.resizable(False, False)

        # Centralizar
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (700 // 2)
        y = (self.winfo_screenheight() // 2) - (500 // 2)
        self.geometry(f"+{x}+{y}")

        # Tornar modal
        self.transient(parent)
        self.grab_set()

        self._build_ui()

    def _build_ui(self) -> None:
        """Constrói a interface do diálogo."""
        self.configure(fg_color=APP_BG)

        # Container principal
        main_frame = ctk.CTkFrame(self, fg_color=SURFACE_DARK, corner_radius=12)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Título
        ctk.CTkLabel(
            main_frame,
            text=f"📤 Upload para: {self.client_name or f'Cliente {self.client_id}'}",
            font=("Segoe UI", 16, "bold"),
            text_color=TEXT_PRIMARY,
        ).pack(pady=(20, 10))

        # Área de seleção de arquivos
        selection_frame = ctk.CTkFrame(main_frame, fg_color=SURFACE, corner_radius=8)
        selection_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Botão para selecionar arquivos
        ctk.CTkButton(
            selection_frame,
            text="📁 Selecionar Arquivo(s)",
            command=self._select_files,
            width=200,
            height=40,
            fg_color=("#17a2b8", "#138496"),
            hover_color=("#138496", "#117a8b"),
            text_color="#ffffff",
            font=("Segoe UI", 12, "bold"),
        ).pack(pady=20)

        # Label de info
        ctk.CTkLabel(
            selection_frame,
            text="Formatos aceitos: PDF, imagens, documentos Office, ZIP",
            font=("Segoe UI", 10),
            text_color=TEXT_MUTED,
        ).pack(pady=(0, 10))

        # Lista de arquivos selecionados
        list_label = ctk.CTkLabel(
            selection_frame, text="Arquivos selecionados:", font=("Segoe UI", 11, "bold"), text_color=TEXT_PRIMARY
        )
        list_label.pack(anchor="w", padx=20, pady=(10, 5))

        # Scrollable frame para lista de arquivos
        self.files_list_frame = ctk.CTkScrollableFrame(selection_frame, fg_color=SURFACE_DARK, height=200)
        self.files_list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # Inicialmente vazio
        self._no_files_label = ctk.CTkLabel(
            self.files_list_frame, text="Nenhum arquivo selecionado", font=("Segoe UI", 10), text_color=TEXT_MUTED
        )
        self._no_files_label.pack(pady=20)

        # Botões de ação
        buttons_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        buttons_frame.pack(fill="x", padx=20, pady=(0, 20))

        # Botão Cancelar
        ctk.CTkButton(
            buttons_frame,
            text="Cancelar",
            command=self.destroy,
            width=120,
            height=36,
            fg_color=("#e5e7eb", "#374151"),
            hover_color=("#d1d5db", "#1f2937"),
            text_color=TEXT_PRIMARY,
            font=("Segoe UI", 11),
        ).pack(side="right", padx=(10, 0))

        # Botão Upload
        self.upload_btn = ctk.CTkButton(
            buttons_frame,
            text="📤 Fazer Upload",
            command=self._do_upload,
            width=140,
            height=36,
            fg_color=("#28a745", "#218838"),
            hover_color=("#218838", "#1e7e34"),
            text_color="#ffffff",
            font=("Segoe UI", 11, "bold"),
            state="disabled",
        )
        self.upload_btn.pack(side="right")

    def _select_files(self) -> None:
        """Abre dialog para seleção de arquivos."""
        filetypes = [
            (
                "Todos os aceitos",
                "*.pdf *.png *.jpg *.jpeg *.gif *.bmp *.doc *.docx *.xls *.xlsx *.txt *.csv *.zip *.rar",
            ),
            ("Documentos PDF", "*.pdf"),
            ("Imagens", "*.png *.jpg *.jpeg *.gif *.bmp"),
            ("Documentos Office", "*.doc *.docx *.xls *.xlsx"),
            ("Todos os arquivos", "*.*"),
        ]

        files = filedialog.askopenfilenames(parent=self, title="Selecionar arquivos para upload", filetypes=filetypes)

        if not files:
            return

        # Validar arquivos
        valid_files: list[str] = []
        invalid_files: list[str] = []

        for file_path in files:
            if self._validate_file(file_path):
                valid_files.append(file_path)
            else:
                invalid_files.append(Path(file_path).name)

        # Mostrar aviso se houver arquivos inválidos
        if invalid_files:
            msg = "Os seguintes arquivos têm formato não aceito e foram ignorados:\n\n"
            msg += "\n".join(f"• {name}" for name in invalid_files[:10])
            if len(invalid_files) > 10:
                msg += f"\n... e mais {len(invalid_files) - 10} arquivos"
            messagebox.showwarning("Arquivos Inválidos", msg, parent=self)

        # Atualizar lista de arquivos selecionados
        if valid_files:
            self.selected_files = valid_files
            self._update_files_list()
            self.upload_btn.configure(state="normal")

    def _validate_file(self, file_path: str) -> bool:
        """Valida se arquivo tem extensão e MIME type aceitos.

        Args:
            file_path: Caminho do arquivo

        Returns:
            True se válido, False caso contrário
        """
        path = Path(file_path)

        # Validar extensão
        if path.suffix.lower() not in ALLOWED_EXTENSIONS:
            log.warning(f"Extensão não aceita: {path.suffix} - {path.name}")
            return False

        # Validar MIME type
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type and mime_type not in ALLOWED_MIME_TYPES:
            log.warning(f"MIME type não aceito: {mime_type} - {path.name}")
            return False

        return True

    def _update_files_list(self) -> None:
        """Atualiza a lista visual de arquivos selecionados."""
        # Limpar lista atual
        for widget in self.files_list_frame.winfo_children():
            widget.destroy()

        if not self.selected_files:
            self._no_files_label = ctk.CTkLabel(
                self.files_list_frame, text="Nenhum arquivo selecionado", font=("Segoe UI", 10), text_color=TEXT_MUTED
            )
            self._no_files_label.pack(pady=20)
            return

        # Adicionar cada arquivo
        for file_path in self.selected_files:
            path = Path(file_path)
            size = path.stat().st_size if path.exists() else 0
            size_str = self._format_size(size)

            file_frame = ctk.CTkFrame(self.files_list_frame, fg_color=SURFACE)
            file_frame.pack(fill="x", pady=2, padx=5)

            # Nome do arquivo
            ctk.CTkLabel(
                file_frame, text=f"📄 {path.name}", font=("Segoe UI", 10), text_color=TEXT_PRIMARY, anchor="w"
            ).pack(side="left", padx=10, pady=5, fill="x", expand=True)

            # Tamanho
            ctk.CTkLabel(file_frame, text=size_str, font=("Segoe UI", 9), text_color=TEXT_MUTED).pack(
                side="right", padx=10
            )

    @staticmethod
    def _format_size(size: int) -> str:
        """Formata tamanho do arquivo."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def _do_upload(self) -> None:
        """Executa o upload dos arquivos selecionados."""
        if not self.selected_files:
            messagebox.showwarning("Nenhum arquivo", "Selecione pelo menos um arquivo.", parent=self)
            return

        try:
            # Importar serviços de upload
            from src.modules.uploads import service as upload_service
            from src.adapters.storage.api import upload_file, using_storage_backend
            from src.adapters.storage.supabase_storage import SupabaseStorageAdapter

            # Preparar itens para upload
            items = upload_service.build_items_from_files(self.selected_files, self.client_id)

            if not items:
                messagebox.showerror("Erro", "Não foi possível preparar arquivos para upload.", parent=self)
                return

            # Confirmar upload
            msg = f"Deseja enviar {len(items)} arquivo(s) para o cliente?\n\n"
            msg += "\n".join(f"• {Path(item['local_path']).name}" for item in items[:5])
            if len(items) > 5:
                msg += f"\n... e mais {len(items) - 5} arquivos"

            if not messagebox.askyesno("Confirmar Upload", msg, parent=self):
                return

            # Criar dialog de progresso
            from src.ui.components.progress_dialog import ProgressDialog

            progress = ProgressDialog(
                self,
                title="Upload em andamento",
                message="Enviando arquivos...",
                detail=f"0 de {len(items)} concluídos",
            )

            # Executar uploads
            adapter = SupabaseStorageAdapter(bucket="rc-docs")
            with using_storage_backend(adapter):
                success_count = 0
                for idx, item in enumerate(items, 1):
                    try:
                        # Atualizar progresso
                        progress.set_message(f"Enviando: {Path(item['local_path']).name}")
                        progress.set_detail(f"{idx} de {len(items)}")
                        progress.set_progress(idx / len(items))
                        progress.update()

                        # Upload
                        upload_file(item["local_path"], item["storage_key"], item.get("content_type"))
                        success_count += 1

                    except Exception as e:
                        log.error(f"Erro ao enviar {item['local_path']}: {e}")
                        # Continuar com próximo arquivo

            # Fechar progresso
            progress.close()

            # Mostrar resultado
            if success_count == len(items):
                messagebox.showinfo(
                    "Upload Concluído", f"✅ {success_count} arquivo(s) enviado(s) com sucesso!", parent=self
                )
            else:
                messagebox.showwarning(
                    "Upload Parcial",
                    f"⚠️ {success_count} de {len(items)} arquivo(s) enviado(s).\n" f"Alguns arquivos falharam.",
                    parent=self,
                )

            # Chamar callback e fechar
            if self.on_complete and success_count > 0:
                self.on_complete()

            self.destroy()

        except Exception as e:
            log.error(f"Erro ao fazer upload: {e}", exc_info=True)
            messagebox.showerror("Erro no Upload", f"Erro ao enviar arquivos:\n{e}", parent=self)
