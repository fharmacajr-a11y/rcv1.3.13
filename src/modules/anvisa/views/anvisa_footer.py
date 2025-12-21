# -*- coding: utf-8 -*-
"""Footer ANVISA para browser de arquivos.

Componente que adiciona funcionalidade de upload de PDFs para processos ANVISA.
"""

from __future__ import annotations

import logging
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Callable

import ttkbootstrap as ttb
from ttkbootstrap.constants import LEFT

from src.modules.anvisa.constants import REQUEST_TYPES
from src.modules.anvisa.helpers.process_slug import get_process_slug

log = logging.getLogger(__name__)

# Lista de processos ANVISA para combobox
# Usa todos os tipos definidos em constants.REQUEST_TYPES
ANVISA_PROCESSES = REQUEST_TYPES


class AnvisaFooter(ttb.Frame):
    """Footer com controles para upload de PDFs ANVISA."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        default_process: str | None = None,
        base_prefix: str,
        org_id: str,
        on_upload_complete: Callable[[], None] | None = None,
        padding: int | tuple[int, ...] = 0,
    ) -> None:
        """Inicializa footer ANVISA.

        Args:
            parent: Widget pai
            default_process: Processo pré-selecionado
            base_prefix: Prefixo base do cliente (ex: org123/client456)
            org_id: ID da organização
            on_upload_complete: Callback após upload completar
            padding: Padding do frame
        """
        super().__init__(parent, padding=padding)
        self._default_process = default_process
        self._base_prefix = base_prefix
        self._org_id = org_id
        self._on_upload_complete = on_upload_complete
        self._selected_files: list[str] = []
        self._build_ui()

    def _build_ui(self) -> None:
        """Constrói UI do footer."""
        # Título
        ttb.Label(
            self,
            text="📋 Upload ANVISA",
            font=("Segoe UI", 11, "bold"),  # type: ignore[arg-type]
            bootstyle="primary",
        ).pack(anchor="w", pady=(0, 8))

        # Separator
        ttb.Separator(self, orient="horizontal").pack(fill="x", pady=(0, 8))

        # Frame do combobox
        combo_frame = ttb.Frame(self)
        combo_frame.pack(fill="x", pady=(0, 8))

        ttb.Label(combo_frame, text="Escolha o processo:").pack(side=LEFT, padx=(0, 8))

        self._process_var = tk.StringVar(value=self._default_process or ANVISA_PROCESSES[0])
        self._process_combo = ttb.Combobox(
            combo_frame,
            textvariable=self._process_var,
            values=ANVISA_PROCESSES,
            state="readonly",
            width=35,
        )
        self._process_combo.pack(side=LEFT, fill="x", expand=True)

        # Label para mostrar arquivos selecionados
        self._files_label_var = tk.StringVar(value="Nenhum arquivo selecionado")
        self._files_label = ttb.Label(
            self,
            textvariable=self._files_label_var,
            bootstyle="secondary",
        )
        self._files_label.pack(anchor="w", pady=(0, 8))

        # Botões
        buttons_frame = ttb.Frame(self)
        buttons_frame.pack(fill="x")

        ttb.Button(
            buttons_frame,
            text="Selecionar PDFs...",
            bootstyle="info",
            command=self._on_select_pdfs,
            width=20,
        ).pack(side=LEFT, padx=(0, 8))

        self._btn_upload = ttb.Button(
            buttons_frame,
            text="Salvar/Enviar",
            bootstyle="success",
            command=self._on_upload,
            width=15,
            state="disabled",
        )
        self._btn_upload.pack(side=LEFT)

    def _on_select_pdfs(self) -> None:
        """Handler para selecionar PDFs."""
        files = filedialog.askopenfilenames(
            parent=self,
            title="Selecionar PDFs para upload",
            filetypes=[("PDF", "*.pdf"), ("Todos os arquivos", "*.*")],
        )

        if not files:
            return

        self._selected_files = list(files)
        count = len(self._selected_files)
        self._files_label_var.set(f"{count} arquivo(s) selecionado(s)")
        self._btn_upload.configure(state="normal")

        log.info(f"[ANVISA] {count} arquivo(s) selecionado(s) para upload")

    def _on_upload(self) -> None:
        """Handler para fazer upload dos PDFs."""
        if not self._selected_files:
            messagebox.showwarning(
                "Aviso",
                "Nenhum arquivo selecionado.",
                parent=self,
            )
            return

        process_name = self._process_var.get()
        if not process_name:
            messagebox.showwarning(
                "Aviso",
                "Selecione um processo.",
                parent=self,
            )
            return

        # Slugify do processo
        process_slug = get_process_slug(process_name)

        # Montar prefixo target: base_prefix/GERAL/anvisa/processo/
        target_prefix = f"{self._base_prefix}/GERAL/anvisa/{process_slug}/"

        log.info(f"[ANVISA] Iniciando upload: processo={process_name}, slug={process_slug}, target={target_prefix}")

        try:
            self._upload_files(target_prefix, process_name)
        except Exception as e:
            log.exception("Erro ao fazer upload de arquivos ANVISA")
            messagebox.showerror(
                "Erro no Upload",
                f"Não foi possível fazer upload dos arquivos.\n\nDetalhes: {e}",
                parent=self,
            )

    def _upload_files(self, target_prefix: str, process_name: str) -> None:
        """Faz upload dos arquivos selecionados.

        Args:
            target_prefix: Prefixo target no storage
            process_name: Nome do processo
        """
        from adapters.storage.api import upload_file

        uploaded_count = 0
        failed_files: list[str] = []

        for file_path in self._selected_files:
            try:
                file_name = Path(file_path).name
                remote_path = f"{target_prefix}{file_name}"

                log.info(f"[ANVISA] Uploading: {file_name} -> {remote_path}")

                # Upload via adapter (usa bucket padrão configurado)
                upload_file(
                    local_path=file_path,
                    remote_key=remote_path,
                    content_type="application/pdf",
                )

                uploaded_count += 1

            except Exception as e:
                log.exception(f"Erro ao fazer upload de {file_name}")
                failed_files.append(f"{file_name}: {str(e)}")

        # Mostrar resultado
        if failed_files:
            message = "Upload concluído com erros:\n\n"
            message += f"✅ {uploaded_count} arquivo(s) enviado(s)\n"
            message += f"❌ {len(failed_files)} arquivo(s) falharam:\n\n"
            message += "\n".join(failed_files[:5])  # Mostrar até 5 erros
            if len(failed_files) > 5:
                message += f"\n... e mais {len(failed_files) - 5} erro(s)"

            messagebox.showwarning(
                "Upload Concluído com Erros",
                message,
                parent=self,
            )
        else:
            messagebox.showinfo(
                "Upload Concluído",
                f"✅ {uploaded_count} arquivo(s) enviado(s) com sucesso!\n\n"
                f"Processo: {process_name}\n"
                f"Pasta: GERAL/anvisa/{get_process_slug(process_name)}/",
                parent=self,
            )

        # Limpar seleção
        self._selected_files = []
        self._files_label_var.set("Nenhum arquivo selecionado")
        self._btn_upload.configure(state="disabled")

        # Chamar callback se definido
        if self._on_upload_complete:
            try:
                self._on_upload_complete()
            except Exception:
                log.exception("Erro ao executar callback on_upload_complete")
