# -*- coding: utf-8 -*-
"""Mixin de download e visualização de arquivos para ClientFilesDialog.

Fase 5: Extraído de client_files_dialog.py para reduzir tamanho do arquivo.
Agrupa operações de **leitura** do bucket: download, abrir/visualizar, ZIP.
Inclui também a classe auxiliar ``DownloadResultDialog``.
"""

from __future__ import annotations

import logging
import os
import tempfile
import zipfile
from pathlib import Path
from tkinter import filedialog  # pyright: ignore[reportAttributeAccessIssue]
from typing import TYPE_CHECKING, Any

from src.adapters.storage.supabase_storage import SupabaseStorageAdapter
from src.modules.uploads.components.helpers import client_prefix_for_id, get_clients_bucket
from src.ui.ctk_config import ctk
from src.ui.dark_window_helper import set_win_dark_titlebar
from src.ui.dialogs.rc_dialogs import show_error, show_info, show_warning
from src.ui.ui_tokens import (
    BORDER,
    BUTTON_RADIUS,
    DIALOG_BTN_H,
    DIALOG_BTN_W,
    PRIMARY_BLUE,
    PRIMARY_BLUE_HOVER,
    SURFACE_2,
    TEXT_MUTED,
    TEXT_PRIMARY,
)
from src.ui.window_utils import apply_window_icon

if TYPE_CHECKING:
    from src.modules.clientes.ui.views._dialogs_typing import FilesDialogProto

log = logging.getLogger(__name__)


class FilesDownloadMixin:
    """Mixin: download, abertura e visualização de arquivos."""

    # ── Dispatchers (chamados pelos botões do footer) ─────────────

    def _on_visualizar(self: FilesDialogProto) -> None:
        """Visualiza/abre arquivo selecionado."""
        item = self._get_selected_item()
        if not item:
            show_warning(self, "Atenção", "Selecione um arquivo para visualizar.")
            return
        if item.get("is_folder"):
            show_info(self, "Info", "Selecione um arquivo, não uma pasta.")
            return
        self._on_open_file_from_metadata(item)

    def _on_baixar(self: FilesDialogProto) -> None:
        """Baixa arquivo selecionado."""
        item = self._get_selected_item()
        if not item:
            show_warning(self, "Atenção", "Selecione um arquivo para baixar.")
            return
        if item.get("is_folder"):
            show_info(self, "Info", "Selecione um arquivo, não uma pasta.")
            return
        self._on_download_file_from_metadata(item)

    # ── Abrir arquivo (download temporário + sistema) ─────────────

    def _on_open_file_from_metadata(self: FilesDialogProto, metadata: dict[str, Any]) -> None:
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
        if self._executor is not None and not self._closing:
            self._executor.submit(_open_thread)

    def _on_open_complete(self: FilesDialogProto, file_name: str) -> None:
        """Callback quando arquivo foi aberto."""
        if not self._ui_alive():
            return

        self._loading = False
        self._enable_buttons()
        self._update_status(f"{file_name} aberto")

    def _on_open_error(self: FilesDialogProto, error: str) -> None:
        """Callback quando houve erro ao abrir."""
        if not self._ui_alive():
            return

        self._loading = False
        self._enable_buttons()
        self._update_status("Erro ao abrir arquivo")

        show_error(self, "Erro", f"Não foi possível abrir o arquivo:\n\n{error}")

    # ── Download de arquivo individual ────────────────────────────

    def _on_download_file_from_metadata(self: FilesDialogProto, metadata: dict[str, Any]) -> None:
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
        if self._executor is not None and not self._closing:
            self._executor.submit(_download_thread)

    def _on_download_complete(self: FilesDialogProto, file_name: str, save_path: str) -> None:
        """Callback quando download foi concluído."""
        if not self._ui_alive():
            return

        self._loading = False
        self._enable_buttons()
        self._progress_queue.put({"action": "hide"})
        self._update_status(f"{file_name} salvo")

        DownloadResultDialog(self, title="Download Concluído", file_name=file_name, save_path=save_path)

    def _on_download_error(self: FilesDialogProto, error: str) -> None:
        """Callback quando houve erro no download."""
        if not self._ui_alive():
            return

        self._loading = False
        self._enable_buttons()
        self._progress_queue.put({"action": "hide"})
        self._update_status("Erro no download")

        show_error(self, "Erro no Download", f"Não foi possível baixar o arquivo:\n\n{error}")

    # ── Download de pasta como ZIP (selecionada) ──────────────────

    def _on_baixar_pasta_zip(self: FilesDialogProto) -> None:
        """Baixa pasta selecionada como ZIP."""
        item = self._get_selected_item()
        if not item:
            show_warning(self, "Atenção", "Selecione uma pasta para baixar.")
            return
        if not item.get("is_folder"):
            show_info(self, "Info", "Selecione uma pasta, não um arquivo.")
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

    def _download_folder_as_zip(self: FilesDialogProto, folder_prefix: str, save_path: str) -> None:
        """Baixa pasta específica como ZIP com progresso determinado por arquivo."""
        self._loading = True
        self._update_status("Preparando download ZIP...")
        self._disable_buttons()

        # Iniciar com indeterminate enquanto lista arquivos
        self._progress_queue.put({"action": "show", "mode": "indeterminate"})

        def _download_zip_thread():
            try:
                bucket = get_clients_bucket()
                log.info(f"[ClientFiles] Iniciando download ZIP: prefix={folder_prefix}")

                adapter = SupabaseStorageAdapter(bucket=bucket)

                # ── FASE 1: Listar todos os arquivos recursivamente ──
                self._progress_queue.put({"action": "status", "text": "Listando arquivos..."})

                file_list: list[tuple[str, str]] = []  # (full_path, relative_path)

                def _enumerate_files(prefix: str, relative_path: str = "") -> None:
                    items = adapter.list_files(prefix)
                    for item in items:
                        name = item.get("name", "")
                        if name.endswith("/.keep") or name.endswith(".keep"):
                            continue
                        full_item_path = f"{prefix}/{name}".strip("/")
                        relative_item_path = f"{relative_path}/{name}".strip("/") if relative_path else name
                        metadata = item.get("metadata")
                        if metadata is not None:
                            file_list.append((full_item_path, relative_item_path))
                        else:
                            _enumerate_files(full_item_path, relative_item_path)

                _enumerate_files(folder_prefix)
                total_files = len(file_list)

                if total_files == 0:
                    self._progress_queue.put({"action": "status", "text": "Pasta vazia — nada para baixar."})
                    self._safe_after(0, lambda: self._on_download_zip_error("Pasta não contém arquivos."))
                    return

                # ── FASE 2: Baixar com progresso determinado ──
                self._progress_queue.put({"action": "show", "mode": "determinate"})
                self._progress_queue.put({"action": "update", "value": 0.0})

                temp_zip = Path(tempfile.gettempdir()) / f"rc_zip_{os.getpid()}.zip"

                with zipfile.ZipFile(temp_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                    done = 0
                    for full_path, rel_path in file_list:
                        self._progress_queue.put(
                            {"action": "status", "text": f"Baixando {rel_path} ({done + 1}/{total_files})..."}
                        )
                        try:
                            content = adapter.download_file(full_path)
                            if isinstance(content, bytes):
                                zf.writestr(rel_path, content)
                            else:
                                zf.write(content, rel_path)
                            done += 1
                            progress = done / total_files
                            self._progress_queue.put({"action": "update", "value": progress})
                        except Exception as e:
                            log.warning(f"[ClientFiles] Erro ao baixar {full_path}: {e}")

                log.info(f"[ClientFiles] ZIP criado com {done} arquivo(s)")

                import shutil

                shutil.move(str(temp_zip), save_path)

                self._safe_after(0, lambda count=done, path=save_path: self._on_download_zip_complete(count, path))

            except Exception as e:
                log.error(f"[ClientFiles] Erro no download ZIP: {e}", exc_info=True)
                error_msg = str(e)
                self._safe_after(0, lambda msg=error_msg: self._on_download_zip_error(msg))

        # Submeter para ThreadPoolExecutor
        if self._executor is not None and not self._closing:
            self._executor.submit(_download_zip_thread)

    # ── Download ZIP da pasta atual ───────────────────────────────

    def _on_download_zip(self: FilesDialogProto) -> None:
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

        # Iniciar com indeterminate enquanto lista arquivos
        self._progress_queue.put({"action": "show", "mode": "indeterminate"})

        def _download_zip_thread():
            try:
                bucket = get_clients_bucket()
                base_prefix = client_prefix_for_id(self.client_id, self._org_id)
                current_path = "/".join(self._nav_stack)
                full_prefix = f"{base_prefix}/{current_path}".strip("/") if current_path else base_prefix

                log.info(f"[ClientFiles] Iniciando download ZIP: prefix={full_prefix}")

                adapter = SupabaseStorageAdapter(bucket=bucket)

                # ── FASE 1: Listar todos os arquivos recursivamente ──
                self._progress_queue.put({"action": "status", "text": "Listando arquivos..."})

                file_list: list[tuple[str, str]] = []  # (full_path, relative_path)

                def _enumerate_files(prefix: str, relative_path: str = "") -> None:
                    items = adapter.list_files(prefix)
                    for item in items:
                        name = item.get("name", "")
                        if name.endswith("/.keep") or name.endswith(".keep"):
                            continue
                        full_item_path = f"{prefix}/{name}".strip("/")
                        relative_item_path = f"{relative_path}/{name}".strip("/") if relative_path else name
                        metadata = item.get("metadata")
                        if metadata is not None:
                            file_list.append((full_item_path, relative_item_path))
                        else:
                            _enumerate_files(full_item_path, relative_item_path)

                _enumerate_files(full_prefix)
                total_files = len(file_list)

                if total_files == 0:
                    self._progress_queue.put({"action": "status", "text": "Pasta vazia — nada para baixar."})
                    self._safe_after(0, lambda: self._on_download_zip_error("Pasta não contém arquivos."))
                    return

                # ── FASE 2: Baixar com progresso determinado ──
                self._progress_queue.put({"action": "show", "mode": "determinate"})
                self._progress_queue.put({"action": "update", "value": 0.0})

                temp_zip = Path(tempfile.gettempdir()) / f"rc_zip_{os.getpid()}.zip"

                with zipfile.ZipFile(temp_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                    done = 0
                    for full_path, rel_path in file_list:
                        self._progress_queue.put(
                            {"action": "status", "text": f"Baixando {rel_path} ({done + 1}/{total_files})..."}
                        )
                        try:
                            content = adapter.download_file(full_path)
                            if isinstance(content, bytes):
                                zf.writestr(rel_path, content)
                            else:
                                zf.write(content, rel_path)
                            done += 1
                            progress = done / total_files
                            self._progress_queue.put({"action": "update", "value": progress})
                        except Exception as e:
                            log.warning(f"[ClientFiles] Erro ao baixar {full_path}: {e}")

                log.info(f"[ClientFiles] ZIP criado com {done} arquivo(s)")

                import shutil

                shutil.move(str(temp_zip), save_path)

                self._safe_after(0, lambda count=done, path=save_path: self._on_download_zip_complete(count, path))

            except Exception as e:
                log.error(f"[ClientFiles] Erro no download ZIP: {e}", exc_info=True)
                error_msg = str(e)
                self._safe_after(0, lambda msg=error_msg: self._on_download_zip_error(msg))

        # Submeter para ThreadPoolExecutor
        if self._executor is not None and not self._closing:
            self._executor.submit(_download_zip_thread)

    # ── Callbacks de download ZIP ─────────────────────────────────

    def _on_download_zip_complete(self: FilesDialogProto, file_count: int, save_path: str) -> None:
        """Callback quando download ZIP foi concluído."""
        if not self._ui_alive():
            return

        self._loading = False
        self._enable_buttons()
        self._progress_queue.put({"action": "hide"})
        self._update_status("ZIP criado com sucesso")

        DownloadResultDialog(
            self,
            title="Download ZIP Concluído",
            file_name="pasta.zip",
            save_path=save_path,
            extra_info=f"Pasta com {file_count} arquivo(s) baixada com sucesso.",
        )

    def _on_download_zip_error(self: FilesDialogProto, error: str) -> None:
        """Callback quando houve erro no download ZIP."""
        if not self._ui_alive():
            return

        self._loading = False
        self._enable_buttons()
        self._progress_queue.put({"action": "hide"})
        self._update_status("Erro no download ZIP")

        show_error(self, "Erro no Download ZIP", f"Não foi possível criar o ZIP:\n\n{error}")


# ============================================================================
# Popup de resultado de download (classe auxiliar)
# ============================================================================


class DownloadResultDialog(ctk.CTkToplevel):
    """Popup CTk para exibir resultado de download.

    Substitui tkinter.messagebox.showinfo para manter ícone RC e visual CTk.
    Segue o padrão anti-flash: prepare_hidden_window → build → show_centered_no_flash.
    """

    def __init__(
        self,
        parent: Any,
        title: str,
        file_name: str,
        save_path: str,
        extra_info: str = "",
        **kwargs: Any,
    ):
        super().__init__(parent, **kwargs)

        # Anti-flash: ocultar imediatamente antes de qualquer build
        from src.ui.window_utils import prepare_hidden_window, show_centered_no_flash as _show_centered

        prepare_hidden_window(self)

        self.title(title)
        self.configure(fg_color=SURFACE_2)
        self.resizable(False, False)

        # Ícone RC (antes de deiconify para evitar flash)
        try:
            apply_window_icon(self)
        except Exception:
            pass

        # Modal (transient antes de exibir)
        self.transient(parent)

        # Titlebar escura no Windows
        try:
            set_win_dark_titlebar(self)
        except Exception:
            pass

        self._build(title, file_name, save_path, extra_info)

        # Exibir centralizado sem flash; height=None → mede winfo_reqheight automaticamente
        _show_centered(self, parent, width=500, height=None)
        self.minsize(480, 235)  # pyright: ignore[reportAttributeAccessIssue]

        # grab_set após deiconify
        self.after(50, self.grab_set)

        # Fechar com Escape/Enter
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Return>", lambda e: self.destroy())

    def _build(self, title: str, file_name: str, save_path: str, extra_info: str) -> None:
        """Constrói o conteúdo visual do popup."""
        from src.ui.dialog_icons import make_icon_label

        # corner_radius=0 + padx/pady=0: card preenche a janela sem expor
        # fundo do pai → elimina "halo" branco ao redor das bordas arredondadas.
        card = ctk.CTkFrame(
            self,
            corner_radius=0,
            fg_color=SURFACE_2,
            border_width=1,
            border_color=BORDER,
        )
        card.pack(fill="both", expand=True, padx=0, pady=0)
        card.grid_columnconfigure(0, weight=1)  # pyright: ignore[reportAttributeAccessIssue]

        # Ícone gráfico de sucesso (PIL desenhado, sem emoji)
        make_icon_label(card, "success", size=44).grid(row=0, column=0, pady=(20, 2))

        # Título
        ctk.CTkLabel(
            card,
            text=title,
            font=("Segoe UI", 13, "bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=1, column=0, pady=(0, 2))

        # Informação extra (ex: quantidade de arquivos no ZIP)
        if extra_info:
            ctk.CTkLabel(
                card,
                text=extra_info,
                font=("Segoe UI", 10),
                text_color=TEXT_MUTED,
            ).grid(row=2, column=0, pady=(0, 4))

        # Rótulo "Arquivo salvo em:"
        ctk.CTkLabel(
            card,
            text="Arquivo salvo em:",
            font=("Segoe UI", 10),
            text_color=TEXT_MUTED,
            anchor="w",
        ).grid(row=3, column=0, sticky="w", padx=20, pady=(6, 0))

        # Caixa de caminho (CTkTextbox somente leitura)
        path_box = ctk.CTkTextbox(
            card,
            height=46,
            corner_radius=8,
            font=("Segoe UI", 9),
            activate_scrollbars=False,
            wrap="word",
        )
        path_box.grid(row=4, column=0, sticky="ew", padx=20, pady=(2, 10))
        path_box.insert("1.0", save_path)
        path_box.configure(state="disabled")

        # Botões
        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.grid(row=5, column=0, pady=(0, 20))

        ctk.CTkButton(
            btn_frame,
            text="Copiar caminho",
            width=DIALOG_BTN_W,
            height=DIALOG_BTN_H,
            corner_radius=BUTTON_RADIUS,
            fg_color=("#6b7280", "#4b5563"),
            hover_color=("#4b5563", "#374151"),
            command=lambda p=save_path: self._copy_path(p),
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="OK",
            width=DIALOG_BTN_W,
            height=DIALOG_BTN_H,
            corner_radius=BUTTON_RADIUS,
            fg_color=PRIMARY_BLUE,
            hover_color=PRIMARY_BLUE_HOVER,
            command=self.destroy,
        ).pack(side="left", padx=5)

    def _copy_path(self, path: str) -> None:
        """Copia o caminho para a área de transferência."""
        try:
            self.clipboard_clear()  # pyright: ignore[reportAttributeAccessIssue]
            self.clipboard_append(path)  # pyright: ignore[reportAttributeAccessIssue]
        except Exception:
            pass
