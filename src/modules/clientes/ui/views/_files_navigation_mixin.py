# -*- coding: utf-8 -*-
"""Mixin de navegação na árvore de arquivos para ClientFilesDialog.

Fase 5: Extraído de client_files_dialog.py para reduzir tamanho do arquivo.
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from src.adapters.storage.supabase_storage import SupabaseStorageAdapter
from src.modules.uploads.components.helpers import client_prefix_for_id, get_clients_bucket
from src.ui.dialogs.rc_dialogs import show_error
from src.ui.ttk_treeview_theme import apply_zebra

if TYPE_CHECKING:
    from src.modules.clientes.ui.views._dialogs_typing import FilesDialogProto

log = logging.getLogger(__name__)


def _log_slow(op_name: str, start_monotonic: float, threshold_ms: float = 1000.0) -> None:
    """Log warning se operação demorou mais que threshold.

    Args:
        op_name: Nome da operação (ex: "list_files", "download", "upload")
        start_monotonic: time.monotonic() quando operação iniciou
        threshold_ms: Threshold em milissegundos (padrão 1000ms)

    Note:
        Threshold aumentado de 250ms para 1000ms para reduzir ruído no console.
        Operações de rede de até 1s são consideradas normais.
    """
    debug_enabled = os.getenv("RC_DEBUG_SLOW_OPS", "0") == "1"

    elapsed_ms = (time.monotonic() - start_monotonic) * 1000
    if elapsed_ms > threshold_ms and debug_enabled:
        log.warning(f"[ClientFiles] Operação lenta: {op_name} levou {elapsed_ms:.0f}ms (>{threshold_ms:.0f}ms)")


class FilesNavigationMixin:
    """Mixin: navegação na árvore de arquivos, renderização e seleção."""

    # ── Eventos do TreeView ───────────────────────────────────────

    def _on_tree_double_click(self: FilesDialogProto, event: Any) -> None:
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

    def _on_tree_selection_change(self: FilesDialogProto, event: Any = None) -> None:
        """Handler quando seleção do TreeView muda."""
        self._update_button_states()

    # ── Carregamento de arquivos ──────────────────────────────────

    def _refresh_files(self: FilesDialogProto) -> None:
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
                _log_slow("list_files", start_time)

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
        if self._executor is not None and not self._closing:
            self._executor.submit(_load_thread)

    def _on_files_loaded(self: FilesDialogProto, files: list[dict[str, Any]]) -> None:
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

    def _on_load_error(self: FilesDialogProto, error: str) -> None:
        """Callback quando houve erro ao carregar."""
        if not self._ui_alive():
            return

        self._loading = False
        self._enable_buttons()
        self._update_status(f"Erro ao carregar arquivos: {error}")

        show_error(
            self,
            "Erro",
            f"Não foi possível carregar os arquivos:\n\n{error}\n\nVerifique sua conexão e tente novamente.",
        )

    # ── Renderização ──────────────────────────────────────────────

    def _render_files(self: FilesDialogProto) -> None:
        """Renderiza lista de arquivos na UI (TreeView)."""
        self._render_tree()

    def _render_tree(self: FilesDialogProto) -> None:
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

            base_name = Path(name).name
            tag = "even" if i % 2 == 0 else "odd"

            if is_folder:
                # Pasta: prefixo emoji no texto (método original que funcionava)
                tipo = "Pasta"
                iid = self.tree.insert(
                    "",
                    "end",
                    text=f"📁 {base_name}",
                    values=(tipo,),
                    tags=(tag,),
                )
            elif name.lower().endswith(".pdf"):
                tipo = "PDF"
                iid = self.tree.insert(
                    "",
                    "end",
                    text=f"  {base_name}",
                    image=self._img_pdf,
                    values=(tipo,),
                    tags=(tag,),
                )
            elif name.lower().endswith((".jpg", ".jpeg", ".png", ".gif")):
                tipo = "Imagem"
                iid = self.tree.insert(
                    "",
                    "end",
                    text=f"  {base_name}",
                    image=self._img_file,
                    values=(tipo,),
                    tags=(tag,),
                )
            elif name.lower().endswith((".doc", ".docx")):
                tipo = "Word"
                iid = self.tree.insert(
                    "",
                    "end",
                    text=f"  {base_name}",
                    image=self._img_file,
                    values=(tipo,),
                    tags=(tag,),
                )
            elif name.lower().endswith((".xls", ".xlsx")):
                tipo = "Excel"
                iid = self.tree.insert(
                    "",
                    "end",
                    text=f"  {base_name}",
                    image=self._img_file,
                    values=(tipo,),
                    tags=(tag,),
                )
            else:
                tipo = "Arquivo"
                iid = self.tree.insert(
                    "",
                    "end",
                    text=f"  {base_name}",
                    image=self._img_file,
                    values=(tipo,),
                    tags=(tag,),
                )

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

    # ── Navegação ─────────────────────────────────────────────────

    def _navigate_to_folder(self: FilesDialogProto, folder_name: str) -> None:
        """Navega para uma subpasta."""
        self._nav_stack.append(folder_name)
        self._refresh_files()

    def _get_selected_item(self: FilesDialogProto) -> Optional[dict[str, Any]]:
        """Retorna metadados do item selecionado no tree."""
        selection = self.tree.selection()
        if not selection:
            return None
        iid = selection[0]
        return self._tree_metadata.get(iid)

    def _on_back(self: FilesDialogProto) -> None:
        """Volta um nível na navegação."""
        if self._nav_stack:
            self._nav_stack.pop()
            self._refresh_files()

    def _copy_breadcrumb(self: FilesDialogProto) -> None:
        """Copia o caminho do breadcrumb para a área de transferência."""
        try:
            if hasattr(self, "breadcrumb_label") and self.breadcrumb_label.winfo_exists():
                path_text = self.breadcrumb_label.cget("text")
                self.clipboard_clear()
                self.clipboard_append(path_text)
        except Exception:
            pass
