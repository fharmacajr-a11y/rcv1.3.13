# -*- coding: utf-8 -*-
"""Mixin de upload e exclusão de arquivos para ClientFilesDialog.

Fase 5: Extraído de client_files_dialog.py para reduzir tamanho do arquivo.
Agrupa operações que **modificam** o conteúdo do bucket (upload + delete).
"""

from __future__ import annotations

import logging
from pathlib import Path
from tkinter import filedialog  # pyright: ignore[reportAttributeAccessIssue]
from typing import TYPE_CHECKING, Any

from src.adapters.storage.supabase_storage import SupabaseStorageAdapter
from src.modules.clientes.forms.client_subfolder_prompt import SubpastaDialog
from src.modules.uploads.components.helpers import client_prefix_for_id, get_clients_bucket
from src.ui.dialogs.rc_dialogs import ask_yes_no, show_error, show_info, show_warning

if TYPE_CHECKING:
    from src.modules.clientes.ui.views._dialogs_typing import FilesDialogProto

log = logging.getLogger(__name__)


class FilesUploadMixin:
    """Mixin: upload de arquivos e exclusão (file + folder)."""

    # ── Upload ────────────────────────────────────────────────────

    def _on_upload(self: FilesDialogProto) -> None:
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

    def _upload_files(self: FilesDialogProto, file_paths: tuple[str, ...], subfolder: str) -> None:
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
                    self._progress_queue.put({"action": "update", "value": progress})
                    self._progress_queue.put(
                        {"action": "status", "text": f"Enviados {uploaded_count}/{total} arquivo(s)..."}
                    )

                log.info(f"[ClientFiles] Upload concluído: {uploaded_count} arquivo(s)")
                self._safe_after(0, lambda: self._on_upload_complete(uploaded_count))

            except Exception as e:
                log.error(f"[ClientFiles] Erro no upload: {e}", exc_info=True)
                err_msg = str(e)
                self._safe_after(0, lambda: self._on_upload_error(err_msg))

        # Submeter para ThreadPoolExecutor
        if self._executor is not None and not self._closing:
            self._executor.submit(_upload_thread)

    def _on_upload_complete(self: FilesDialogProto, count: int) -> None:
        """Callback quando upload foi concluído."""
        if not self._ui_alive():
            return

        self._loading = False
        self._enable_buttons()
        self._progress_queue.put({"action": "hide"})

        show_info(self, "Upload Concluído", f"{count} arquivo(s) enviado(s) com sucesso!")

        # Recarregar lista
        self._refresh_files()

    def _on_upload_error(self: FilesDialogProto, error: str) -> None:
        """Callback quando houve erro no upload."""
        if not self._ui_alive():
            return

        self._loading = False
        self._enable_buttons()
        self._progress_queue.put({"action": "hide"})
        self._update_status("Erro no upload")

        show_error(self, "Erro no Upload", f"Não foi possível enviar os arquivos:\n\n{error}")

    # ── Exclusão (dispatcher) ─────────────────────────────────────

    def _on_excluir(self: FilesDialogProto) -> None:
        """Exclui arquivo selecionado."""
        item = self._get_selected_item()
        if not item:
            show_warning(self, "Atenção", "Selecione um arquivo para excluir.")
            return
        if item.get("is_folder"):
            self._on_delete_folder(item)
            return
        self._on_delete_file_from_metadata(item)

    # ── Exclusão de arquivo ───────────────────────────────────────

    def _on_delete_file_from_metadata(self: FilesDialogProto, metadata: dict[str, Any]) -> None:
        """Exclui arquivo após confirmação."""
        if self._loading:
            return

        name = metadata.get("name", "")
        full_path = metadata.get("full_path", name)  # CRÍTICO: usar full_path
        file_name = Path(name).name

        # Confirmar exclusão
        confirm = ask_yes_no(
            self,
            "Confirmar Exclusão",
            f"Deseja realmente excluir o arquivo?\n\n{file_name}\n\nEsta ação não pode ser desfeita.",
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
        if self._executor is not None and not self._closing:
            self._executor.submit(_delete_thread)

    # ── Exclusão recursiva de pastas ──────────────────────────────

    def _on_delete_folder(self: FilesDialogProto, metadata: dict[str, Any]) -> None:
        """Exclui pasta recursivamente após confirmação do usuário."""
        if self._loading:
            return

        folder_name = metadata.get("name", "")
        full_path = metadata.get("full_path", folder_name)

        confirm = ask_yes_no(
            self,
            "Confirmar Exclusão",
            f"Deseja realmente excluir a pasta e todo seu conteúdo?\n\n📁 {folder_name}\n\nEsta ação não pode ser desfeita.",
        )
        if not confirm:
            return

        self._loading = True
        self._disable_buttons()

        # Fase 1 — listar arquivos (indeterminate)
        self._progress_queue.put({"action": "show", "mode": "indeterminate"})
        self._progress_queue.put({"action": "status", "text": "Listando arquivos da pasta…"})

        def _delete_folder_thread() -> None:
            try:
                bucket = get_clients_bucket()
                adapter = SupabaseStorageAdapter(bucket=bucket)

                # ── Fase 1: enumerar todas as chaves recursivamente ──
                file_keys: list[str] = []

                def _enumerate(prefix: str) -> None:
                    items = adapter.list_files(prefix)
                    for item in items:
                        name = item.get("name", "")
                        full_item_path = f"{prefix}/{name}".strip("/")
                        item_meta = item.get("metadata")
                        if item_meta is not None:
                            # É arquivo (inclui .keep — queremos apagar tudo)
                            file_keys.append(full_item_path)
                        else:
                            # É subpasta — recursar
                            _enumerate(full_item_path)

                _enumerate(full_path)
                total = len(file_keys)

                if total == 0:
                    self._progress_queue.put({"action": "hide"})
                    self._safe_after(
                        0,
                        lambda fn=folder_name: self._on_delete_folder_empty(fn),
                    )
                    return

                # ── Fase 2: excluir em lotes com progresso determinado ──
                self._progress_queue.put({"action": "show", "mode": "determinate"})
                self._progress_queue.put({"action": "update", "value": 0.0})

                deleted = 0
                chunk_size = 1000
                for i in range(0, total, chunk_size):
                    chunk = file_keys[i : i + chunk_size]
                    self._progress_queue.put(
                        {
                            "action": "status",
                            "text": f"Excluindo {deleted}/{total} arquivo(s)…",
                        }
                    )
                    adapter.remove_files(chunk)
                    deleted += len(chunk)
                    self._progress_queue.put({"action": "update", "value": deleted / total})

                self._progress_queue.put({"action": "status", "text": f"Excluindo {deleted}/{total} arquivo(s)…"})

                log.info(
                    "[ClientFiles] Pasta excluída: %s (%d arquivo(s))",
                    full_path,
                    deleted,
                )
                self._safe_after(
                    0,
                    lambda fn=folder_name, c=deleted: self._on_delete_folder_complete(fn, c),
                )

            except Exception as exc:
                log.error("[ClientFiles] Erro ao excluir pasta: %s", exc, exc_info=True)
                error_msg = str(exc)
                self._safe_after(0, lambda msg=error_msg: self._on_delete_error(msg))

        if self._executor is not None and not self._closing:
            self._executor.submit(_delete_folder_thread)

    # ── Callbacks de exclusão ─────────────────────────────────────

    def _on_delete_folder_complete(self: FilesDialogProto, folder_name: str, count: int) -> None:
        """Callback quando pasta foi excluída com sucesso."""
        if not self._ui_alive():
            return

        self._loading = False
        self._progress_queue.put({"action": "hide"})
        self._enable_buttons()

        show_info(
            self,
            "Pasta Excluída",
            f"📁 {folder_name}\n\n{count} arquivo(s) excluído(s) com sucesso.",
        )
        self._refresh_files()

    def _on_delete_folder_empty(self: FilesDialogProto, folder_name: str) -> None:
        """Callback quando pasta estava vazia (nada a excluir)."""
        if not self._ui_alive():
            return

        self._loading = False
        self._enable_buttons()

        show_info(
            self,
            "Pasta Vazia",
            f"📁 {folder_name}\n\nA pasta não contém arquivos para excluir.",
        )

    def _on_delete_complete(self: FilesDialogProto, file_name: str) -> None:
        """Callback quando arquivo foi excluído."""
        if not self._ui_alive():
            return

        self._loading = False
        self._enable_buttons()

        show_info(self, "Arquivo Excluído", f"{file_name} foi excluído com sucesso.")

        # Recarregar lista
        self._refresh_files()

    def _on_delete_error(self: FilesDialogProto, error: str) -> None:
        """Callback quando houve erro ao excluir."""
        if not self._ui_alive():
            return

        self._loading = False
        self._enable_buttons()
        self._update_status("Erro ao excluir arquivo")

        show_error(
            self,
            "Erro",
            f"Não foi possível excluir o arquivo:\n\n{error}\n\nVerifique se você tem permissão para esta operação.",
        )
