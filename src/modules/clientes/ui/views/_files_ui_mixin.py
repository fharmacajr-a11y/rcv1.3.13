# -*- coding: utf-8 -*-
"""Mixin de construção de UI e gerenciamento visual para ClientFilesDialog.

Fase 5: Extraído de client_files_dialog.py para reduzir tamanho do arquivo.
"""

from __future__ import annotations

import logging
import queue
import tkinter as tk
import tkinter.font as tkfont
from typing import TYPE_CHECKING, Any

from src.ui.ctk_config import ctk
from src.ui.ui_tokens import (
    BORDER,
    PRIMARY_BLUE,
    PRIMARY_BLUE_HOVER,
    SURFACE_2,
    SURFACE_DARK,
    TEXT_MUTED,
    TEXT_PRIMARY,
)
from src.ui.widgets.button_factory import make_btn, make_btn_sm
from src.ui.widgets.ctk_treeview_container import CTkTreeviewContainer
from src.utils.formatters import format_cnpj as _fmt_cnpj

if TYPE_CHECKING:
    from src.modules.clientes.ui.views._dialogs_typing import FilesDialogProto

log = logging.getLogger(__name__)


class FilesUIMixin:
    """Mixin: construção da interface e gerenciamento de estado visual."""

    # Comprimento máximo desejado para a titlebar
    _TITLE_MAX_LEN = 80

    # ── Construção da UI ─────────────────────────────────────────

    def _build_ui(self: FilesDialogProto) -> None:
        """Constrói a interface do diálogo."""
        # Container principal (flat, sem borda/moldura)
        container = ctk.CTkFrame(self, fg_color=("#F5F5F5", "#1e1e1e"), corner_radius=0, border_width=0)
        container.pack(fill="both", expand=True, padx=0, pady=0)

        # Configurar grid: somente row 4 (tree_frame) expande
        container.grid_columnconfigure(0, weight=1)  # pyright: ignore[reportAttributeAccessIssue]
        container.grid_rowconfigure(0, weight=0)  # header  # pyright: ignore[reportAttributeAccessIssue]
        container.grid_rowconfigure(1, weight=0)  # breadcrumb  # pyright: ignore[reportAttributeAccessIssue]
        container.grid_rowconfigure(2, weight=0)  # status label  # pyright: ignore[reportAttributeAccessIssue]
        container.grid_rowconfigure(3, weight=0)  # progress bar  # pyright: ignore[reportAttributeAccessIssue]
        container.grid_rowconfigure(4, weight=1)  # tree_frame (EXPANDE)  # pyright: ignore[reportAttributeAccessIssue]
        container.grid_rowconfigure(5, weight=0)  # footer  # pyright: ignore[reportAttributeAccessIssue]

        # Cabeçalho com título e botões
        header = ctk.CTkFrame(container, fg_color="transparent", border_width=0)
        header.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 5))
        header.grid_columnconfigure(0, weight=0)  # pyright: ignore[reportAttributeAccessIssue]
        header.grid_columnconfigure(1, weight=1)  # label expande  # pyright: ignore[reportAttributeAccessIssue]
        header.grid_columnconfigure(2, weight=0)  # pyright: ignore[reportAttributeAccessIssue]

        # Botão Voltar
        self.btn_back = make_btn_sm(
            header,
            text="⬅ Voltar",
            command=self._on_back,
            fg_color=("#6b7280", "#4b5563"),
            hover_color=("#4b5563", "#374151"),
            border_width=0,
        )
        self.btn_back.grid(row=0, column=0, sticky="w", padx=(0, 10))

        # Título principal — UMA label com texto completo: Arquivos - Razão - CNPJ
        cnpj_fmt = (_fmt_cnpj(self.cnpj) or self.cnpj) if self.cnpj else ""
        header_parts = ["📁 Arquivos"]
        if self.razao_social:
            header_parts.append(self.razao_social)
        if cnpj_fmt:
            header_parts.append(cnpj_fmt)
        header_text = " - ".join(header_parts)

        self._header_left_label = ctk.CTkLabel(
            header,
            text=header_text,
            font=("Segoe UI", 14, "bold"),
            text_color=TEXT_PRIMARY,
            anchor="w",
            justify="left",
        )
        self._header_left_label.grid(row=0, column=1, sticky="ew", padx=(0, 12))

        # Ajuste dinâmico: reduzir fonte do header inteiro até caber
        header.bind("<Configure>", self._on_header_configure)

        # Botões de ação
        btn_frame = ctk.CTkFrame(header, fg_color="transparent", border_width=0)
        btn_frame.grid(row=0, column=2, sticky="e", padx=0)

        self.btn_upload = make_btn_sm(
            btn_frame,
            text="Upload",
            command=self._on_upload,
            fg_color=("#059669", "#10b981"),
            hover_color=("#047857", "#059669"),
            border_width=0,
        )
        self.btn_upload.pack(side="left", padx=0)

        # Breadcrumb (caminho atual) — pill/card estilizado
        breadcrumb_frame = ctk.CTkFrame(
            container,
            corner_radius=10,
            fg_color=SURFACE_DARK,
            border_width=0,
        )
        breadcrumb_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=(5, 5))
        breadcrumb_frame.grid_columnconfigure(1, weight=1)  # pyright: ignore[reportAttributeAccessIssue]

        ctk.CTkLabel(
            breadcrumb_frame,
            text="📂 Caminho:",
            font=("Segoe UI", 10, "bold"),
            text_color=TEXT_MUTED,
        ).grid(row=0, column=0, padx=(10, 4), pady=7, sticky="w")

        self.breadcrumb_label = ctk.CTkLabel(
            breadcrumb_frame,
            text="/ (raiz)",
            font=("Segoe UI", 10),
            text_color=TEXT_PRIMARY,
            anchor="w",
            wraplength=600,
        )
        self.breadcrumb_label.grid(row=0, column=1, padx=(0, 6), pady=7, sticky="ew")

        ctk.CTkButton(
            breadcrumb_frame,
            text="Copiar",
            width=60,
            height=22,
            corner_radius=8,
            fg_color=("#e5e7eb", "#374151"),
            hover_color=("#d1d5db", "#4b5563"),
            text_color=("#6b7280", "#9ca3af"),
            font=("Segoe UI", 9),
            command=self._copy_breadcrumb,
            border_width=0,
        ).grid(row=0, column=2, padx=(0, 8), pady=4, sticky="e")

        # Status label (sempre visível, texto pequeno)
        self.status_label = ctk.CTkLabel(
            container,
            text="Carregando arquivos...",
            font=("Segoe UI", 10),
            text_color=TEXT_MUTED,
            anchor="w",
        )
        self.status_label.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 2))

        # Download status card (oculto por padrão — aparece durante downloads/uploads)
        self._dl_card = ctk.CTkFrame(
            container,
            corner_radius=10,
            fg_color=SURFACE_2,
            border_width=1,
            border_color=BORDER,
        )
        self._dl_card.grid(row=3, column=0, sticky="ew", padx=15, pady=(0, 6))
        self._dl_card.grid_columnconfigure(0, weight=1)
        self._dl_card.grid_columnconfigure(1, weight=0)

        self._dl_name_label = ctk.CTkLabel(
            self._dl_card,
            text="",
            font=("Segoe UI", 10),
            text_color=TEXT_PRIMARY,
            anchor="w",
        )
        self._dl_name_label.grid(row=0, column=0, padx=12, pady=(8, 2), sticky="w")

        self._dl_pct_label = ctk.CTkLabel(
            self._dl_card,
            text="",
            font=("Segoe UI", 9),
            text_color=TEXT_MUTED,
            anchor="e",
        )
        self._dl_pct_label.grid(row=0, column=1, padx=(0, 12), pady=(8, 2), sticky="e")

        self.progress_bar = ctk.CTkProgressBar(self._dl_card, mode="indeterminate", height=10, corner_radius=8)
        self.progress_bar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=(2, 10))
        self._dl_card.grid_remove()  # Ocultar inicialmente

        # Body: wrapper visual igual à lista de clientes (SURFACE_DARK + corner_radius)
        # FASE 4: Migração para CTkTreeviewContainer
        _tree_wrapper = ctk.CTkFrame(container, fg_color=SURFACE_DARK, corner_radius=10, border_width=0)
        _tree_wrapper.grid(row=4, column=0, sticky="nsew", padx=15, pady=(0, 10))
        _tree_wrapper.grid_rowconfigure(0, weight=1)  # pyright: ignore[reportAttributeAccessIssue]
        _tree_wrapper.grid_columnconfigure(0, weight=1)  # pyright: ignore[reportAttributeAccessIssue]

        self._tree_container = CTkTreeviewContainer(
            _tree_wrapper,
            columns=("tipo",),
            show="tree headings",
            selectmode="browse",
            rowheight=24,
            zebra=True,
            style_name="RC.Treeview",
            fg_color="transparent",
            show_hscroll=False,
        )
        self._tree_container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Obter referência ao Treeview interno (preserva API existente)
        self.tree = self._tree_container.get_treeview()

        # Headings
        self.tree.heading("#0", text="Nome do arquivo/pasta", anchor="w")
        self.tree.heading("tipo", text="Tipo", anchor="center")

        # Columns
        self.tree.column("#0", stretch=True, minwidth=200)
        self.tree.column("tipo", width=90, minwidth=80, stretch=False, anchor="center")

        # Double-click para navegar em pastas
        self.tree.bind("<Double-Button-1>", self._on_tree_double_click)

        # Bind para atualizar estados dos botões quando seleção muda
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_selection_change)

        # Obter cores do tema (CTkTreeviewContainer já registrou no manager)
        self._tree_colors = self._tree_container.get_colors()

        # Footer: Botões de ação
        footer_frame = ctk.CTkFrame(container, fg_color="transparent", border_width=0)
        footer_frame.grid(row=5, column=0, sticky="ew", padx=15, pady=(0, 15))

        # Ordem: Baixar | Baixar zip | Visualizar | Excluir (Excluir à direita)
        self.btn_baixar = make_btn(
            footer_frame,
            text="Baixar",
            command=self._on_baixar,
            fg_color=("#28a745", "#218838"),
            hover_color=("#218838", "#1e7e34"),
            border_width=0,
            state="disabled",
        )
        self.btn_baixar.pack(side="left", padx=2)

        self.btn_baixar_zip = make_btn(
            footer_frame,
            text="Baixar pasta (.zip)",
            command=self._on_baixar_pasta_zip,
            fg_color=("#7c3aed", "#8b5cf6"),
            hover_color=("#6d28d9", "#7c3aed"),
            border_width=0,
            state="disabled",
        )
        self.btn_baixar_zip.pack(side="left", padx=2)

        self.btn_visualizar = make_btn(
            footer_frame,
            text="Visualizar",
            command=self._on_visualizar,
            fg_color=PRIMARY_BLUE,
            hover_color=PRIMARY_BLUE_HOVER,
            border_width=0,
            state="disabled",
        )
        self.btn_visualizar.pack(side="left", padx=2)

        self.btn_excluir = make_btn(
            footer_frame,
            text="Excluir",
            command=self._on_excluir,
            fg_color=("#dc2626", "#ef4444"),
            hover_color=("#b91c1c", "#dc2626"),
            border_width=0,
            state="disabled",
        )
        self.btn_excluir.pack(side="left", padx=2)

        # Aplicar tema inicial (via theme manager)
        # Já aplicado no register_treeview

        # Bind Escape para fechar
        self.bind("<Escape>", lambda e: self._safe_close())

        # Protocol WM_DELETE_WINDOW para cleanup
        self.protocol("WM_DELETE_WINDOW", self._safe_close)

        # Iniciar polling da fila de progresso
        self._poll_progress_queue()

    # ── Progress helpers ─────────────────────────────────────────

    def _show_progress(self: FilesDialogProto, mode: str = "indeterminate") -> None:
        """Mostra card de download com barra de progresso.

        Args:
            mode: "indeterminate" ou "determinate"
        """
        # Parar animação anterior antes de trocar mode (evita conflito CTk)
        self.progress_bar.stop()
        self.progress_bar.configure(mode=mode)
        if mode == "indeterminate":
            self.progress_bar.start()
        else:
            self.progress_bar.set(0)
        if hasattr(self, "_dl_card") and self._dl_card.winfo_exists():
            self._dl_card.grid()
        if hasattr(self, "_dl_pct_label") and self._dl_pct_label.winfo_exists():
            self._dl_pct_label.configure(text="")

    def _hide_progress(self: FilesDialogProto) -> None:
        """Oculta card de download."""
        self.progress_bar.stop()
        if hasattr(self, "_dl_card") and self._dl_card.winfo_exists():
            self._dl_card.grid_remove()

    def _update_progress(self: FilesDialogProto, value: float) -> None:
        """Atualiza valor da barra de progresso (0.0 a 1.0)."""
        self.progress_bar.set(value)
        if hasattr(self, "_dl_pct_label") and self._dl_pct_label.winfo_exists():
            self._dl_pct_label.configure(text=f"{int(value * 100)}%")

    # ── Titlebar + Header helpers ─────────────────────────────────

    def _set_smart_title(self: FilesDialogProto) -> None:
        """Define self.title() garantindo que o CNPJ sempre apareça.

        Se a razão social for longa, trunca-a com "…" para caber.
        """
        cnpj_fmt = (_fmt_cnpj(self.cnpj) or self.cnpj) if self.cnpj else ""
        prefix = f"Arquivos - ID {self.client_id}"

        # Calcular espaço disponível para razão social
        fixed = prefix
        if cnpj_fmt:
            fixed += f" -  - {cnpj_fmt}"  # placeholder para razão

        max_razao = max(self._TITLE_MAX_LEN - len(fixed), 10)
        razao = self.razao_social or ""
        if len(razao) > max_razao:
            razao = razao[: max_razao - 1].rstrip() + "…"

        parts = [prefix]
        if razao:
            parts.append(razao)
        if cnpj_fmt:
            parts.append(cnpj_fmt)
        self.title(" - ".join(parts))

    def _on_header_configure(self: FilesDialogProto, _event: Any = None) -> None:
        """Recalcula header quando o container é redimensionado.

        Texto do header é único: «📁 Arquivos - Razão - CNPJ».

        Estratégia:
        1. Tenta texto completo reduzindo fonte de 14 até 10.
        2. Na fonte mínima (10), trunca apenas a Razão com «…» preservando
           o sufixo « - CNPJ» (CNPJ sempre visível).
        """
        try:
            if not self._ui_alive():
                return
            header = self._header_left_label.master
            avail = header.winfo_width()
            if avail <= 1:
                return  # ainda não renderizado

            # Espaço reservado por Voltar (col0) + btn_frame Upload (col2) + paddings
            back_w = 0
            if hasattr(self, "btn_back") and self.btn_back.winfo_exists():
                back_w = self.btn_back.winfo_reqwidth() + 10  # padx=(0,10)
            upload_w = 0
            for child in header.winfo_children():
                if isinstance(child, ctk.CTkFrame):
                    upload_w = child.winfo_reqwidth() + 10  # padx=(0,10)  # pyright: ignore[reportAttributeAccessIssue]
            # 12px padding à direita da label + 15px padx do header no container
            reserved = back_w + upload_w + 12 + 15

            available = avail - reserved
            if available <= 10:
                return

            cnpj_fmt = (_fmt_cnpj(self.cnpj) or self.cnpj) if self.cnpj else ""
            razao_full = self.razao_social or ""

            # Reconstrói texto completo
            def _build_text(razao: str) -> str:
                parts: list[str] = ["📁 Arquivos"]
                if razao:
                    parts.append(razao)
                if cnpj_fmt:
                    parts.append(cnpj_fmt)
                return " - ".join(parts)

            full_text = _build_text(razao_full)

            # 1) Reduzir fonte de 14 → 10 até texto completo caber
            for size in range(14, 9, -1):
                f = tkfont.Font(family="Segoe UI", size=size, weight="bold")
                if f.measure(full_text) <= available:
                    self._header_left_label.configure(text=full_text, font=("Segoe UI", size, "bold"))
                    return

            # 2) Fonte mínima: truncar Razão, mantendo CNPJ no final
            min_font = tkfont.Font(family="Segoe UI", size=10, weight="bold")
            if razao_full:
                for trim in range(len(razao_full) - 1, 3, -1):
                    trunc_text = _build_text(razao_full[:trim].rstrip() + "…")
                    if min_font.measure(trunc_text) <= available:
                        self._header_left_label.configure(text=trunc_text, font=("Segoe UI", 10, "bold"))
                        return

            # Fallback absoluto: só «Arquivos - CNPJ»
            self._header_left_label.configure(text=_build_text(""), font=("Segoe UI", 10, "bold"))

        except Exception:
            pass  # Não quebrar resize por erro cosmético

    # ── Polling e estado de botões ────────────────────────────────

    def _poll_progress_queue(self: FilesDialogProto) -> None:
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

    def _update_button_states(self: FilesDialogProto) -> None:
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

    # ── Breadcrumb e navegação visual ─────────────────────────────

    def _update_breadcrumb(self: FilesDialogProto) -> None:
        """Atualiza label do breadcrumb."""
        if not self._nav_stack:
            path_text = "/ (raiz)"
        else:
            path_text = "/" + "/".join(self._nav_stack)

        if hasattr(self, "breadcrumb_label") and self.breadcrumb_label.winfo_exists():
            self.breadcrumb_label.configure(text=path_text)

    def _update_back_button(self: FilesDialogProto) -> None:
        """Atualiza estado do botão Voltar."""
        if hasattr(self, "btn_back") and self.btn_back.winfo_exists():
            if self._nav_stack:
                self.btn_back.configure(state="normal")
            else:
                self.btn_back.configure(state="disabled")

    # ── Status e habilitação/desabilitação ────────────────────────

    def _update_status(self: FilesDialogProto, text: str) -> None:
        """Atualiza texto do status e sincroniza com card de download quando visível."""
        if hasattr(self, "status_label") and self.status_label.winfo_exists():
            self.status_label.configure(text=text)
        # Sincronizar com label do card de download quando card estiver visível
        try:
            if (
                hasattr(self, "_dl_name_label")
                and self._dl_name_label.winfo_exists()
                and hasattr(self, "_dl_card")
                and self._dl_card.winfo_exists()
                and self._dl_card.winfo_ismapped()
            ):
                self._dl_name_label.configure(text=text)
        except Exception:
            pass

    def _disable_buttons(self: FilesDialogProto) -> None:
        """Desabilita botões durante operações."""
        if not self._ui_alive():
            return

        buttons = [
            "btn_upload",
            "btn_back",
            "btn_visualizar",
            "btn_baixar",
            "btn_baixar_zip",
            "btn_excluir",
        ]

        for btn_name in buttons:
            if hasattr(self, btn_name):
                btn = getattr(self, btn_name)
                if btn is not None and btn.winfo_exists():
                    try:
                        btn.configure(state="disabled")
                    except tk.TclError:  # pyright: ignore[reportAttributeAccessIssue]
                        pass

    def _enable_buttons(self: FilesDialogProto) -> None:
        """Habilita botões após operações."""
        if not self._ui_alive():
            return

        # Botões que sempre devem ser habilitados
        for btn_name in ["btn_upload"]:
            if hasattr(self, btn_name):
                btn = getattr(self, btn_name)
                if btn is not None and btn.winfo_exists():
                    try:
                        btn.configure(state="normal")
                    except tk.TclError:  # pyright: ignore[reportAttributeAccessIssue]
                        pass

        # Atualizar estados dos botões do footer baseado na seleção
        self._update_button_states()
        self._update_back_button()  # Atualiza estado do botão Voltar
