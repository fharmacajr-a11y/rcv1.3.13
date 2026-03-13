# -*- coding: utf-8 -*-
"""UploadsBrowserWindowV2 — browser de arquivos do cliente (implementação oficial).

Abre uma janela modal que lista, faz upload, download, visualização e
exclusão de arquivos do cliente no Supabase Storage.

SEQUÊNCIA DE ABERTURA (anti-flash):
 1. super().__init__(parent)       — cria Toplevel
 2. withdraw()                     — esconde IMEDIATAMENTE (sem exposição)
 3. configure(fg_color=APP_BG)     — bg antes de qualquer widget
 4. title(…) + iconbitmap(…)       — metadados da janela
 5. minsize(W, H)                  — tamanho mínimo ANTES de montar UI
 6. _build_ui()                    — monta TODA a UI
 7. update_idletasks()             — Tk calcula tamanhos finais
 8. transient(parent)              — vincula ao parent ANTES de deiconify
 9. _refresh_listing()             — carrega dados enquanto hidden
10. _center_on(parent, W, H)       — geometry final centralizada
11. deiconify()                    — UMA ÚNICA revelação, já no lugar certo
12. lift() + focus_set()           — traz ao frente
13. grab_set (deferred)            — torna modal
"""

from __future__ import annotations

import atexit as _atexit
import logging
import os
import queue
import sys
import tempfile
import tkinter as tk
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tkinter import filedialog
from typing import Any

from src.adapters.storage.supabase_storage import SupabaseStorageAdapter
from src.ui.dialogs.download_result_dialog import DownloadResultDialog
from src.modules.pdf_preview import open_pdf_viewer
from src.modules.uploads.service import (
    build_items_from_files,
    delete_storage_folder,
    delete_storage_object,
    download_bytes,
    download_storage_object,
    list_browser_items,
    upload_items_for_client,
)
from src.ui.ctk_config import ctk
from src.ui.dialogs.rc_dialogs import show_info, show_error, ask_yes_no
from src.ui.ui_tokens import (
    APP_BG,
    BODY_FONT,
    BORDER,
    SURFACE_2,
    SURFACE_DARK,
    TEXT_PRIMARY,
    TEXT_MUTED,
    PRIMARY_BLUE,
    PRIMARY_BLUE_HOVER,
)
from src.ui.widgets.button_factory import make_btn, make_btn_sm
from src.utils.formatters import format_cnpj as _fmt_cnpj
from src.utils.resource_path import resource_path
from .file_list import FileList

_log = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=4)
_atexit.register(_executor.shutdown, wait=False)

# Dimensões canônicas
_W = 1000
_H = 650

_UI_GAP = 6
_UI_PADX = 8
_UI_PADY = 6


class UploadsBrowserWindowV2(ctk.CTkToplevel):  # type: ignore[misc]
    """Browser de arquivos do cliente — implementação oficial."""

    # ------------------------------------------------------------------
    # Overrides críticos: bloqueiam repaints tardios do CTkToplevel
    # ------------------------------------------------------------------
    def _windows_set_titlebar_color(self, color_mode: str) -> None:
        """Override: aplica DWM dark/light titlebar SEM o ciclo withdraw/deiconify.

        CAUSA RAIZ DO FLASH:
        CTkToplevel.__init__  faz  tkinter.Toplevel.__init__()  que MAPEIA a
        janela no Win32 (visível).  O _windows_set_titlebar_color original
        chama super().withdraw() quase imediatamente, fechando o gap.
        Nosso override anterior NÃO fazia withdraw — o gap de 2-5 ms até
        o PASSO 2 (self.withdraw()) permitia ao DWM renderizar 1 frame
        da janela vazia.

        FIX: na PRIMEIRA chamada (durante CTkToplevel.__init__), fazemos
        withdraw imediato via tkinter.Toplevel.withdraw  (bypassa a lógica
        de flags do CTkToplevel, sem update() nem after(5, revert)).
        Chamadas subsequentes (theme change) só aplicam DWM.
        """
        if sys.platform != "win32":
            return
        try:
            import ctypes as _ctypes  # noqa: PLC0415

            # --- WITHDRAW IMEDIATO na 1ª chamada (durante __init__) ---
            if not getattr(self, "_v2_titlebar_initialized", False):
                self._v2_titlebar_initialized = True
                tk.Toplevel.withdraw(self)

            _hwnd = _ctypes.windll.user32.GetParent(self.winfo_id())
            _v = _ctypes.c_int(1 if str(color_mode).lower() == "dark" else 0)
            _sz = _ctypes.sizeof(_v)
            # DWMWA_USE_IMMERSIVE_DARK_MODE = 20 (Win11 / Win10 ≥ 2004)
            _ctypes.windll.dwmapi.DwmSetWindowAttribute(_hwnd, 20, _ctypes.byref(_v), _sz)
            # Fallback legado = 19 (Win10 < 2004)
            _ctypes.windll.dwmapi.DwmSetWindowAttribute(_hwnd, 19, _ctypes.byref(_v), _sz)
        except Exception as exc:  # noqa: BLE001
            _log.debug("[BrowserV2] _windows_set_titlebar_color falhou: %s", exc)

    def iconbitmap(self, bitmap=None, default=None):  # type: ignore[override]
        """Bloqueia o after(200) que CTkToplevel.__init__ agenda para substituir
        rc.ico pelo ícone padrão do CTkinter (CustomTkinter_icon_Windows.ico).

        Análise da causa raiz:
        - CTkToplevel.__init__ faz: self.after(200, lambda: self.iconbitmap(CTk_icon))
        - self.iconbitmap() resolve via MRO para tkinter.Wm.iconbitmap (bypassa
          CTkToplevel.wm_iconbitmap), então o lambda dispara mesmo com
          _iconbitmap_method_called=True.
        - Como _refresh_listing() bloqueia o event loop, o callback ainda está
          pendente quando deiconify() é chamado e dispara na 1ª iteração do loop
          → WM_SETICON → repaint visível → flash.
        - Fix: definir iconbitmap nesta classe (prioritário no MRO) e ignorar
          chamadas com o caminho do CTkinter.
        """
        if bitmap is not None and "customtkinter" in str(bitmap).lower():
            self._iconbitmap_method_called = True  # manter flag consistente
            return None
        return super().iconbitmap(bitmap=bitmap, default=default)  # type: ignore[misc]

    # ------------------------------------------------------------------
    # Construtor
    # ------------------------------------------------------------------
    def __init__(
        self,
        parent: tk.Misc,
        *,
        client_id: int,
        razao: str = "",
        cnpj: str = "",
        org_id: str = "",
        bucket: str = "",
        base_prefix: str = "",
    ) -> None:
        # PASSO 1 — cria o Toplevel (ainda não aparece na tela)
        super().__init__(parent)

        # PASSO 2 — esconder IMEDIATAMENTE antes de qualquer outro comando
        # Isso garante que a janela jamais seja exibida em estado parcial.
        self.withdraw()

        # PASSO 3 — cor de fundo antes de qualquer widget (elimina flash branco)
        self.configure(fg_color=APP_BG)

        self._is_closing = False
        self._client_id = client_id
        self._razao = razao
        self._cnpj = cnpj
        self._org_id = org_id
        self._bucket = bucket
        self._base_prefix = base_prefix
        self._status_cache: dict[str, str] = {}
        self._after_ids: set[str] = set()
        self._download_in_progress = False
        self._pdf_viewer_window = None
        self._nav_stack: list[str] = []
        self._progress_queue: queue.Queue = queue.Queue()

        # PASSO 4 — título (ID + razão + CNPJ formatado)
        razao_display = razao.strip() or f"ID {client_id}"
        cnpj_fmt = (_fmt_cnpj(cnpj) or cnpj.strip()) if cnpj.strip() else ""
        _title = f"Arquivos: ID {client_id} — {razao_display}"
        if cnpj_fmt:
            _title = f"{_title} — {cnpj_fmt}"
        self.title(_title)

        # PASSO 5 — ícone: chamada direta, sem after() agendado
        # apply_window_icon agenda window.after(250, _reapply_icon) que dispara
        # APÓS deiconify e causa repainting visível (flash). Basta iconbitmap
        # direto pois override de _windows_set_titlebar_color já impede que
        # CTkToplevel substitua o ícone numa troca de tema.
        try:
            self.iconbitmap(resource_path("rc.ico"))
        except Exception as exc:  # noqa: BLE001
            _log.debug("[BrowserV2] iconbitmap falhou: %s", exc)

        # PASSO 6 — minsize e resizable ANTES de montar a UI
        # Fundamental: update_idletasks usará este valor ao calcular reqwidth
        self.minsize(_W, _H)
        # Resizable explícito — bypassa CTkToplevel.resizable que agenda
        # after(10, _windows_set_titlebar_color). Bypass direto.
        try:
            from tkinter import Toplevel as _Toplevel

            _Toplevel.resizable(self, True, True)
        except Exception:
            self.resizable(True, True)

        # PASSO 7 — montar TODO o layout (janela ainda hidden)
        self._build_ui()

        # PASSO 7b — handlers de fechamento (antes de qualquer revelação)
        self.protocol("WM_DELETE_WINDOW", self._close_window)
        self.bind("<Escape>", lambda _e: self._close_window())
        # Tecla Delete no nível da janela: delega para _delete_selected (defesa em profundidade).
        # Garante que mesmo se o foco estiver no browser toplevel (não em um widget filho),
        # Delete acione a exclusão do item do storage, nunca do cliente.
        self.bind("<Delete>", lambda _e: self._delete_selected())

        # PASSO 8 — forçar Tk a calcular tamanhos reais após _build_ui
        self.update_idletasks()

        # PASSO 9 — titlebar escura já aplicada em _windows_set_titlebar_color()
        # durante super().__init__() no PASSO 1 (CTkToplevel chama o override
        # que usa GetParent + DwmSetWindowAttribute sem withdraw/deiconify).

        # PASSO 10 — vincular ao parent ANTES do deiconify
        self.transient(parent)

        # PASSO 11 — CARREGAR CONTEÚDO ENQUANTO HIDDEN (elimina flash/repaint)
        # Causa raiz do flash: janela abria vazia → after(100ms) populava a tree
        # → repaint visível. Solução: popular sincronamente ANTES do deiconify.
        # Tradeoff: chamada de rede bloqueia main thread ~0.5-2s enquanto hidden;
        # janela só aparece quando já tem conteúdo (zero flash após abertura).
        self._refresh_listing()

        # PASSO 12 — geometria estabilizada APÓS popular a tree
        # A tree sabe quantos itens tem → Tk pode ajustar reqheight intern.
        # update_idletasks() aqui garante que _center_on use o tamanho real.
        self.update_idletasks()

        # PASSO 13 — geometry centralizada (janela ainda hidden, tamanho final)
        self._center_on(parent, _W, _H)

        # PASSO 14 — UMA ÚNICA revelação, já no lugar certo, já com conteúdo
        self.deiconify()

        # PASSO 15 — foco (somente após deiconify)
        self.lift()
        self.focus_set()

        # PASSO 16 — grab_set com retry seguro (aguarda janela viewable)
        # Torna modal, impedindo interação com o editor.
        self._safe_after(10, self._setup_modal_safe)

        _log.info(
            "[BrowserV2] Janela aberta: client_id=%s razao=%r",
            client_id,
            razao_display,
        )

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------

    def _safe_after(self, ms: int, callback: Any) -> str | None:
        """Agenda callback com proteção contra widgets destruídos."""
        if self._is_closing:
            return None
        try:
            if not self.winfo_exists():
                return None
            aid = self.after(ms, callback)
            self._after_ids.add(aid)
            return aid
        except Exception:  # noqa: BLE001
            return None

    def _setup_modal_safe(self, retry_count: int = 0) -> None:
        """Aplica grab_set apenas quando a janela está viewable."""
        max_retries = 10
        retry_delay_ms = 50

        try:
            if not self.winfo_exists():
                return
            if not self.winfo_viewable():
                if retry_count < max_retries:
                    self._safe_after(
                        retry_delay_ms,
                        lambda: self._setup_modal_safe(retry_count + 1),
                    )
                    return
                _log.warning("[BrowserV2] Janela não ficou viewable, abortando grab_set")
                return
            self.grab_set()
            _log.debug("[BrowserV2] grab_set aplicado (viewable=True)")
        except Exception as e:  # noqa: BLE001
            _log.error("[BrowserV2] Erro ao aplicar grab_set: %s", e)

    # ------------------------------------------------------------------
    # Geometria — cálculo simples e explícito sem funções externas
    # ------------------------------------------------------------------
    def _center_on(self, parent: tk.Misc, width: int, height: int) -> None:
        """Centraliza sobre *parent* usando as dimensões fixas da janela.

        Usa os valores nominais width/height (_W/_H) como tamanho definitivo.
        winfo_reqwidth/reqheight NÃO são usados para dimensionar: após popular
        uma TreeView eles retornam o tamanho necessário para exibir TODAS as
        linhas sem scroll, causando janela gigante.
        Não chama update() no parent.
        """
        try:
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            pw = parent.winfo_width()
            ph = parent.winfo_height()

            # winfo_width/height retornam 1 se Tk ainda não mediu a janela.
            # winfo_geometry() é mais confiável: sempre reflete a última
            # geometry() aplicada pelo window manager.
            if pw < 50 or ph < 50:
                import re as _re

                _m = _re.match(r"(\d+)x(\d+)", parent.winfo_geometry())
                if _m:
                    pw, ph = int(_m.group(1)), int(_m.group(2))

            if pw < 50 or ph < 50:
                raise ValueError(f"Parent muito pequeno: {pw}x{ph}")

            x = px + (pw - width) // 2
            y = py + (ph - height) // 2

            # Clamp básico: garante que a janela fique na tela principal
            x = max(0, x)
            y = max(0, y)

        except Exception as exc:
            _log.debug("[BrowserV2] Fallback para centro da tela: %s", exc)
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            x = (sw - width) // 2
            y = (sh - height) // 2

        self.geometry(f"{width}x{height}+{x}+{y}")
        _log.debug("[BrowserV2] Geometry aplicada: %dx%d+%d+%d", width, height, x, y)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        """Monta o layout visual completo (header, breadcrumb, tree, footer)."""
        # Configurar grid: somente row 4 (tree_wrapper) expande
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=0)  # header
        self.rowconfigure(1, weight=0)  # breadcrumb
        self.rowconfigure(2, weight=0)  # status label
        self.rowconfigure(3, weight=0)  # _dl_card (oculto por padrão)
        self.rowconfigure(4, weight=1)  # tree_wrapper (EXPANDE)
        self.rowconfigure(5, weight=0)  # footer

        # ── Header (row 0): Voltar | Título | Upload ───────────────────
        header = ctk.CTkFrame(self, fg_color="transparent", border_width=0)  # type: ignore[union-attr]
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))
        header.columnconfigure(0, weight=0)
        header.columnconfigure(1, weight=1)  # título expande
        header.columnconfigure(2, weight=0)

        # Botão Voltar — fecha a janela (volta à tela anterior)
        make_btn_sm(
            header,
            text="⬅ Voltar",
            command=self._close_window,
            fg_color=("#6b7280", "#4b5563"),
            hover_color=("#4b5563", "#374151"),
            border_width=0,
        ).grid(row=0, column=0, sticky="w", padx=(0, 10))

        # Título inline: "📁 Arquivos — Razão — CNPJ"
        cnpj_fmt = (_fmt_cnpj(self._cnpj) or self._cnpj.strip()) if self._cnpj.strip() else ""
        header_parts = ["📁 Arquivos"]
        if self._razao.strip():
            header_parts.append(self._razao.strip())
        if cnpj_fmt:
            header_parts.append(cnpj_fmt)
        ctk.CTkLabel(  # type: ignore[union-attr]
            header,
            text=" — ".join(header_parts),
            font=("Segoe UI", 14, "bold"),
            text_color=TEXT_PRIMARY,
            anchor="w",
            justify="left",
        ).grid(row=0, column=1, sticky="ew", padx=(0, 12))

        # Botão Upload
        make_btn_sm(
            header,
            text="⬆ Upload",
            command=self._handle_upload,
            fg_color=("#059669", "#10b981"),
            hover_color=("#047857", "#059669"),
            border_width=0,
        ).grid(row=0, column=2, sticky="e")

        # ── Breadcrumb (row 1): barra de caminho ────────────────────────
        breadcrumb_frame = ctk.CTkFrame(  # type: ignore[union-attr]
            self,
            corner_radius=10,
            fg_color=SURFACE_DARK,
            border_width=0,
        )
        breadcrumb_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=(4, 6))
        breadcrumb_frame.columnconfigure(1, weight=1)

        ctk.CTkLabel(  # type: ignore[union-attr]
            breadcrumb_frame,
            text="📂 Caminho:",
            font=BODY_FONT,
            text_color=TEXT_MUTED,
        ).grid(row=0, column=0, padx=(12, 4), pady=8, sticky="w")

        self.breadcrumb_label = ctk.CTkLabel(  # type: ignore[union-attr]
            breadcrumb_frame,
            text="/ (raiz)",
            font=BODY_FONT,
            text_color=TEXT_PRIMARY,
            anchor="w",
            wraplength=700,
        )
        self.breadcrumb_label.grid(row=0, column=1, padx=(0, 8), pady=8, sticky="ew")

        ctk.CTkButton(  # type: ignore[union-attr]
            breadcrumb_frame,
            text="Copiar",
            width=64,
            height=26,
            corner_radius=8,
            fg_color=("#e5e7eb", "#374151"),
            hover_color=("#d1d5db", "#4b5563"),
            text_color=("#6b7280", "#9ca3af"),
            font=("Segoe UI", 10),
            command=self._copy_path_to_clipboard,
            border_width=0,
        ).grid(row=0, column=2, padx=(0, 10), pady=5, sticky="e")

        # ── Status label (row 2): contador / texto auxiliar ──────────────
        self.status_label = ctk.CTkLabel(  # type: ignore[union-attr]
            self,
            text="Carregando arquivos\u2026",
            font=BODY_FONT,
            text_color=TEXT_MUTED,
            anchor="w",
        )
        self.status_label.grid(row=2, column=0, sticky="ew", padx=16, pady=(2, 4))

        # ── Card de progresso (row 3): oculto por padrão — aparece durante downloads/uploads ───
        self._dl_card = ctk.CTkFrame(  # type: ignore[union-attr]
            self,
            corner_radius=10,
            fg_color=SURFACE_2,
            border_width=1,
            border_color=BORDER,
        )
        self._dl_card.grid(row=3, column=0, sticky="ew", padx=16, pady=(2, 6))
        self._dl_card.columnconfigure(0, weight=1)
        self._dl_card.columnconfigure(1, weight=0)

        self._dl_name_label = ctk.CTkLabel(  # type: ignore[union-attr]
            self._dl_card,
            text="",
            font=("Segoe UI", 10),
            text_color=TEXT_PRIMARY,
            anchor="w",
        )
        self._dl_name_label.grid(row=0, column=0, padx=12, pady=(8, 2), sticky="w")

        self._dl_pct_label = ctk.CTkLabel(  # type: ignore[union-attr]
            self._dl_card,
            text="",
            font=("Segoe UI", 9),
            text_color=TEXT_MUTED,
            anchor="e",
        )
        self._dl_pct_label.grid(row=0, column=1, padx=(0, 12), pady=(8, 2), sticky="e")

        self.progress_bar = ctk.CTkProgressBar(  # type: ignore[union-attr]
            self._dl_card, mode="indeterminate", height=10, corner_radius=8
        )
        self.progress_bar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=(2, 10))
        self._dl_card.grid_remove()  # Ocultar inicialmente  # type: ignore[attr-defined]

        # ── Área da árvore (row 4): wrapper visual + FileList ──────────────────
        _tree_wrapper = ctk.CTkFrame(  # type: ignore[union-attr]
            self, fg_color=SURFACE_DARK, corner_radius=10, border_width=0
        )
        _tree_wrapper.grid(row=4, column=0, sticky="nsew", padx=16, pady=(2, 8))
        _tree_wrapper.rowconfigure(0, weight=1)
        _tree_wrapper.columnconfigure(0, weight=1)

        self.file_list = FileList(
            _tree_wrapper,
            on_download=lambda: None,
            on_delete=self._delete_selected,
            on_open_file=lambda _n, _t, _p: None,
            on_expand_folder=self._load_folder_children,
            on_download_folder=lambda: None,
            fg_color="transparent",
        )
        self.file_list.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.file_list.tree.bind("<<TreeviewSelect>>", lambda _event: self._sync_actions_state())

        # ── Rodapé (row 5): ações construtivas à esquerda, destrutiva à direita ──
        footer_frame = ctk.CTkFrame(self, fg_color="transparent", border_width=0)  # type: ignore[union-attr]
        footer_frame.grid(row=5, column=0, sticky="ew", padx=16, pady=(0, 14))

        # Baixar (verde)
        self.btn_baixar = make_btn(
            footer_frame,
            text="Baixar",
            command=self._download_selected,
            fg_color=("#28a745", "#218838"),
            hover_color=("#218838", "#1e7e34"),
            border_width=0,
            state="disabled",
        )
        self.btn_baixar.pack(side="left", padx=(0, 6))

        # Baixar pasta (.zip) (roxo)
        self.btn_baixar_zip = make_btn(
            footer_frame,
            text="Baixar pasta (.zip)",
            command=self._download_folder_zip,
            fg_color=("#7c3aed", "#8b5cf6"),
            hover_color=("#6d28d9", "#7c3aed"),
            border_width=0,
            state="disabled",
        )
        self.btn_baixar_zip.pack(side="left", padx=(0, 6))

        # Visualizar (azul)
        self.btn_visualizar = make_btn(
            footer_frame,
            text="Visualizar",
            command=self._view_selected,
            fg_color=PRIMARY_BLUE,
            hover_color=PRIMARY_BLUE_HOVER,
            border_width=0,
            state="disabled",
        )
        self.btn_visualizar.pack(side="left", padx=(0, 6))

        # Excluir (vermelho — separado à direita)
        self.btn_excluir = make_btn(
            footer_frame,
            text="Excluir",
            command=self._delete_selected,
            fg_color=("#dc2626", "#ef4444"),
            hover_color=("#b91c1c", "#dc2626"),
            border_width=0,
            state="disabled",
        )
        self.btn_excluir.pack(side="right", padx=0)

        # Iniciar polling da fila de progresso
        self._poll_progress_queue()

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------
    def _sync_actions_state(self) -> None:
        """Habilita/desabilita botões de ação conforme item selecionado."""
        self._update_breadcrumb_for_selected()
        selected_info = self.file_list.get_selected_info()

        if not selected_info:
            self.btn_baixar.configure(state="disabled")
            self.btn_baixar_zip.configure(state="disabled")
            self.btn_visualizar.configure(state="disabled")
            self.btn_excluir.configure(state="disabled")
            return

        _, item_type, _ = selected_info

        if item_type == "Pasta":
            self.btn_baixar.configure(state="disabled")
            self.btn_baixar_zip.configure(state="normal")
            self.btn_visualizar.configure(state="disabled")
            self.btn_excluir.configure(state="normal")
        else:
            self.btn_baixar.configure(state="normal")
            self.btn_baixar_zip.configure(state="disabled")
            self.btn_visualizar.configure(state="normal")
            self.btn_excluir.configure(state="normal")

    def _refresh_listing(self) -> None:
        """Carrega a árvore completa de arquivos do prefixo base do cliente."""
        prefix = self._base_prefix
        _log.info(
            "[BrowserV2] Listando: prefix=%s bucket=%s client_id=%s",
            prefix,
            self._bucket,
            self._client_id,
        )
        items = list(list_browser_items(prefix, bucket=self._bucket))
        self.file_list.populate_tree_hierarchical(items, self._base_prefix, self._status_cache)
        n = len(items)
        if hasattr(self, "status_label") and self.status_label.winfo_exists():
            if n == 0:
                self.status_label.configure(text="Nenhum arquivo encontrado nesta pasta")
            elif n == 1:
                self.status_label.configure(text="1 arquivo encontrado")
            else:
                self.status_label.configure(text=f"{n} arquivos encontrados")
        self._update_breadcrumb()
        self._sync_actions_state()

    def _load_folder_children(self, folder_path: str) -> list[dict]:
        """Carrega filhos de uma pasta específica (lazy loading)."""
        _log.info("[BrowserV2] Carregando filhos de: %s", folder_path)
        if not folder_path.endswith("/"):
            folder_path = folder_path + "/"
        items = list_browser_items(folder_path, bucket=self._bucket)
        return list(items)

    # ------------------------------------------------------------------
    # Ações: Copiar caminho
    # ------------------------------------------------------------------
    def _copy_path_to_clipboard(self) -> None:
        """Copia o caminho atual (breadcrumb) para a área de transferência."""
        try:
            text = self.breadcrumb_label.cget("text")
            self.clipboard_clear()
            self.clipboard_append(text)
            show_info(self, "Copiar caminho", f"Caminho copiado:\n{text}")
        except Exception as exc:  # noqa: BLE001
            _log.debug("[BrowserV2] Erro ao copiar caminho: %s", exc)

    # ------------------------------------------------------------------
    # Ações: Visualizar
    # ------------------------------------------------------------------
    def _view_selected(self, name: str = "", item_type: str = "", full_path: str = "") -> None:
        """Abre o arquivo selecionado no visualizador interno (PDF/imagens)."""
        if not name:
            selected_info = self.file_list.get_selected_info()
            if not selected_info:
                show_info(self, "Visualizar arquivo", "Selecione um arquivo para visualizar.")
                return
            name, item_type, full_path = selected_info

        if item_type == "Pasta":
            show_info(self, "Visualizar arquivo", "Selecione um ARQUIVO, não uma pasta.")
            return

        nome = name.strip()
        ext = nome.lower().rsplit(".", 1)[-1] if "." in nome else ""

        if ext not in ("pdf", "jpg", "jpeg", "png", "gif"):
            sufixo = f".{ext}" if ext else ""
            show_info(self, "Visualizar arquivo", f"Tipo não suportado para visualização: {sufixo}")
            return

        remote_key = full_path
        try:
            data = download_bytes(self._bucket, remote_key)
        except Exception as exc:  # noqa: BLE001
            _log.exception("[BrowserV2] Erro ao baixar bytes para visualização")
            show_error(self, "Visualizar arquivo", f"Não foi possível carregar este arquivo:\n{exc}")
            return

        if not data:
            show_error(self, "Visualizar arquivo", "Não foi possível carregar este arquivo.")
            return

        try:
            open_pdf_viewer(self, data_bytes=data, display_name=nome)
        except Exception as exc:  # noqa: BLE001
            _log.exception("[BrowserV2] Erro ao abrir visualizador")
            show_error(self, "Visualizar arquivo", f"Falha ao abrir visualização:\n{exc}")

    # ------------------------------------------------------------------
    # Ações: Baixar arquivo
    # ------------------------------------------------------------------
    def _download_selected(self) -> None:
        """Baixa o arquivo selecionado para o disco."""
        if self._download_in_progress:
            return

        selected_info = self.file_list.get_selected_info()
        if not selected_info:
            show_info(self, "Arquivos", "Selecione um item para baixar.")
            return

        item_name, item_type, full_path = selected_info

        if item_type == "Pasta":
            show_info(self, "Baixar", "Para pasta, use o botão 'Baixar pasta (.zip)'.")
            return

        local_path = filedialog.asksaveasfilename(parent=self, initialfile=item_name)
        if not local_path:
            return

        self._download_in_progress = True
        try:
            result = download_storage_object(full_path, local_path, bucket=self._bucket)
            if result.get("ok"):
                DownloadResultDialog(self, title="Download Concluído", file_name=item_name, save_path=local_path)
            else:
                show_error(self, "Download", result.get("message", "Erro desconhecido ao baixar arquivo"))
        except Exception as exc:
            _log.exception("[BrowserV2] Download falhou")
            show_error(self, "Download", f"Falha ao baixar arquivo:\n{exc}")
        finally:
            self._download_in_progress = False

    # ------------------------------------------------------------------
    # Ações: Baixar pasta (.zip) — progresso inline
    # ------------------------------------------------------------------
    def _download_folder_zip(self) -> None:
        """Baixa a pasta selecionada como ZIP com progresso inline."""
        if self._download_in_progress:
            return

        selected_info = self.file_list.get_selected_info()
        if not selected_info:
            show_info(self, "Baixar pasta", "Selecione uma pasta para baixar como ZIP.")
            return

        item_name, item_type, full_path = selected_info
        if item_type != "Pasta":
            show_info(self, "Baixar pasta", "Selecione uma PASTA para baixar como ZIP.")
            return

        zip_name = f"{item_name}.zip"
        save_path = filedialog.asksaveasfilename(
            title="Salvar pasta como ZIP",
            initialfile=zip_name,
            parent=self,
            defaultextension=".zip",
            filetypes=[("Arquivos ZIP", "*.zip")],
        )
        if not save_path:
            return

        self._download_in_progress = True
        if hasattr(self, "status_label") and self.status_label.winfo_exists():
            self.status_label.configure(text="Preparando download ZIP...")
        self._progress_queue.put({"action": "show", "mode": "indeterminate"})

        folder_prefix = full_path

        def _worker() -> None:
            try:
                adapter = SupabaseStorageAdapter(bucket=self._bucket)
                self._progress_queue.put({"action": "status", "text": "Listando arquivos..."})

                file_list: list[tuple[str, str]] = []  # (full_path, relative_path)

                def _enumerate(prefix: str, rel: str = "") -> None:
                    for item in adapter.list_files(prefix):
                        name = item.get("name", "")
                        if not name or name == ".keep" or name.endswith("/.keep"):
                            continue
                        full_item = f"{prefix}/{name}".strip("/")
                        rel_item = f"{rel}/{name}".strip("/") if rel else name
                        if item.get("metadata") is not None:
                            file_list.append((full_item, rel_item))
                        else:
                            _enumerate(full_item, rel_item)

                _enumerate(folder_prefix)
                total = len(file_list)

                if total == 0:
                    self._progress_queue.put({"action": "status", "text": "Pasta vazia — nada para baixar."})
                    self._progress_queue.put({"action": "hide"})
                    self.after(
                        0,
                        lambda: (
                            setattr(self, "_download_in_progress", False),
                            show_info(self, "Baixar ZIP", "Pasta não contém arquivos."),
                        ),
                    )
                    return

                self._progress_queue.put({"action": "show", "mode": "determinate"})
                self._progress_queue.put({"action": "update", "value": 0.0})

                fd, tmp = tempfile.mkstemp(suffix=".zip", prefix="rc_zip_")
                os.close(fd)
                temp_zip = Path(tmp)
                done = 0

                try:
                    with zipfile.ZipFile(temp_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                        for fp_item, rel_path in file_list:
                            self._progress_queue.put(
                                {
                                    "action": "status",
                                    "text": f"Baixando {rel_path} ({done + 1}/{total})...",
                                }
                            )
                            try:
                                content = adapter.download_file(fp_item)
                                if isinstance(content, bytes):
                                    zf.writestr(rel_path, content)
                                else:
                                    zf.write(str(content), rel_path)
                                done += 1
                                self._progress_queue.put({"action": "update", "value": done / total})
                            except Exception as e:
                                _log.warning("[BrowserV2] Erro ao baixar %s: %s", fp_item, e)

                    import shutil

                    shutil.move(str(temp_zip), save_path)

                    file_count = done
                    saved = save_path
                    self.after(0, lambda c=file_count, p=saved: self._on_zip_complete(c, p))
                finally:
                    temp_zip.unlink(missing_ok=True)

            except Exception as exc:
                err_msg = str(exc)
                _log.exception("[BrowserV2] Erro no ZIP")
                self.after(0, lambda m=err_msg: self._on_zip_error(m))

        _executor.submit(_worker)

    def _on_zip_complete(self, file_count: int, save_path: str) -> None:
        """Callback quando download ZIP concluiu com sucesso."""
        self._download_in_progress = False
        self._progress_queue.put({"action": "hide"})
        if hasattr(self, "status_label") and self.status_label.winfo_exists():
            self.status_label.configure(text="ZIP criado com sucesso")
        try:
            self.lift()
        except Exception:  # noqa: BLE001
            pass
        DownloadResultDialog(
            self,
            title="Download ZIP Concluído",
            file_name="pasta.zip",
            save_path=save_path,
            extra_info=f"Pasta com {file_count} arquivo(s) baixada com sucesso.",
        )

    def _on_zip_error(self, error: str) -> None:
        """Callback quando download ZIP falhou."""
        self._download_in_progress = False
        self._progress_queue.put({"action": "hide"})
        if hasattr(self, "status_label") and self.status_label.winfo_exists():
            self.status_label.configure(text="Erro no download ZIP")
        show_error(self, "Erro no Download ZIP", f"Não foi possível criar o ZIP:\n\n{error}")

    # ------------------------------------------------------------------
    # Ações: Excluir
    # ------------------------------------------------------------------
    def _delete_selected(self) -> None:
        """Exclui o item selecionado (arquivo ou pasta)."""
        selected_info = self.file_list.get_selected_info()
        if not selected_info:
            return

        item_name, item_type, full_path = selected_info

        if item_type == "Pasta":
            if not ask_yes_no(
                self,
                "Excluir pasta",
                "Tem certeza que deseja excluir esta pasta e todo o conteúdo?\nEsta ação não pode ser desfeita.",
            ):
                return
            try:
                result = delete_storage_folder(full_path, bucket=self._bucket)
            except Exception as exc:  # noqa: BLE001
                _log.exception("[BrowserV2] Erro ao excluir pasta")
                show_error(self, "Excluir pasta", f"Falha ao excluir a pasta:\n{exc}")
                return
            if not result.get("ok"):
                error_txt = result.get("message") or "Falha ao excluir a pasta."
                show_error(self, "Excluir pasta", error_txt)
                return
            self._refresh_listing()
            show_info(self, "Excluir", f"Pasta '{item_name}' excluída com sucesso.")
        else:
            if not ask_yes_no(self, "Excluir", f"Deseja excluir '{item_name}'?"):
                return
            try:
                ok = delete_storage_object(full_path, bucket=self._bucket)
                if ok:
                    self._refresh_listing()
                    show_info(self, "Excluir", f"Arquivo '{item_name}' excluído com sucesso.")
                else:
                    show_error(self, "Excluir", f"Falha ao excluir '{item_name}'.")
            except Exception as exc:
                _log.exception("[BrowserV2] Delete falhou")
                show_error(self, "Excluir", f"Falha ao excluir arquivo:\n{exc}")

    # ------------------------------------------------------------------
    # Ações: Upload
    # ------------------------------------------------------------------
    def _handle_upload(self) -> None:
        """Upload simples: abre seletor de arquivo(s) e envia para o prefix do cliente."""
        cnpj_digits = "".join(c for c in (self._cnpj or "") if c.isdigit())
        if not cnpj_digits:
            show_info(self, "Upload", "CNPJ do cliente não disponível. Não é possível fazer upload.")
            return

        paths = filedialog.askopenfilenames(
            parent=self,
            title="Selecione os arquivos para enviar",
            filetypes=[
                ("Documentos", "*.pdf *.doc *.docx *.xls *.xlsx *.csv *.jpg *.jpeg *.png"),
                ("Todos os arquivos", "*.*"),
            ],
        )
        if not paths:
            return

        items = build_items_from_files(list(paths))
        if not items:
            show_info(self, "Upload", "Nenhum arquivo válido selecionado.")
            return

        try:
            ok_count, failures = upload_items_for_client(
                items,
                cnpj_digits=cnpj_digits,
                bucket=self._bucket,
                client_id=self._client_id,
                org_id=self._org_id,
            )
        except Exception as exc:
            _log.exception("[BrowserV2] Upload falhou")
            show_error(self, "Upload", f"Falha ao enviar arquivos:\n{exc}")
            return

        if failures:
            failed_names = ", ".join(str(f[0].path.name) for f in failures[:5])
            show_info(self, "Upload", f"{ok_count} arquivo(s) enviado(s).\n{len(failures)} falha(s): {failed_names}")
        else:
            show_info(self, "Upload", f"{ok_count} arquivo(s) enviado(s) com sucesso.")

        self._refresh_listing()

    # ------------------------------------------------------------------
    # Breadcrumb
    # ------------------------------------------------------------------
    def _update_breadcrumb(self) -> None:
        """Atualiza label do breadcrumb com base no _nav_stack."""
        if not self._nav_stack:
            path_text = "/ (raiz)"
        else:
            path_text = "/" + "/".join(self._nav_stack)
        if hasattr(self, "breadcrumb_label") and self.breadcrumb_label.winfo_exists():
            self.breadcrumb_label.configure(text=path_text)

    def _update_breadcrumb_for_selected(self) -> None:
        """Atualiza breadcrumb com caminho amigável do item selecionado."""
        selected_info = self.file_list.get_selected_info()
        if not selected_info:
            self._update_breadcrumb()
            return
        _name, item_type, full_path = selected_info
        # Calcular caminho relativo ao base_prefix
        base = self._base_prefix.rstrip("/").lstrip("/")
        fp = full_path.lstrip("/")
        if base and fp.startswith(base + "/"):
            rel = fp[len(base) + 1 :]
        else:
            rel = fp
        folder_part = rel.rstrip("/") if item_type == "Pasta" else (rel.rsplit("/", 1)[0] if "/" in rel else "")
        if hasattr(self, "breadcrumb_label") and self.breadcrumb_label.winfo_exists():
            self.breadcrumb_label.configure(text=("/" + folder_part) if folder_part else "/ (raiz)")

    # ------------------------------------------------------------------
    # Progresso inline (_dl_card + _progress_queue)
    # ------------------------------------------------------------------
    def _show_progress(self, mode: str = "indeterminate") -> None:
        """Mostra card de progresso."""
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

    def _hide_progress(self) -> None:
        """Oculta card de progresso."""
        self.progress_bar.stop()
        if hasattr(self, "_dl_card") and self._dl_card.winfo_exists():
            self._dl_card.grid_remove()  # type: ignore[attr-defined]

    def _update_progress(self, value: float) -> None:
        """Atualiza barra de progresso determinada (0.0–1.0)."""
        self.progress_bar.set(value)
        if hasattr(self, "_dl_pct_label") and self._dl_pct_label.winfo_exists():
            self._dl_pct_label.configure(text=f"{int(value * 100)}%")

    def _poll_progress_queue(self) -> None:
        """Drena fila de progresso e atualiza UI."""
        if self._is_closing:
            return
        try:
            while True:
                msg = self._progress_queue.get_nowait()
                action = msg.get("action")
                if action == "show":
                    self._show_progress(msg.get("mode", "indeterminate"))
                elif action == "hide":
                    self._hide_progress()
                elif action == "update":
                    self._update_progress(msg.get("value", 0.0))
                elif action == "status":
                    text = msg.get("text", "")
                    if hasattr(self, "status_label") and self.status_label.winfo_exists():
                        self.status_label.configure(text=text)
                    try:
                        if (
                            hasattr(self, "_dl_name_label")
                            and self._dl_name_label.winfo_exists()
                            and hasattr(self, "_dl_card")
                            and self._dl_card.winfo_exists()
                            and self._dl_card.winfo_ismapped()  # type: ignore[attr-defined]
                        ):
                            self._dl_name_label.configure(text=text)
                    except Exception:  # noqa: BLE001
                        pass
        except queue.Empty:
            pass
        if not self._is_closing:
            self._safe_after(100, self._poll_progress_queue)

    # ------------------------------------------------------------------
    # Fechamento
    # ------------------------------------------------------------------
    def _cancel_afters(self) -> None:
        """Cancela todos os after jobs pendentes."""
        for aid in list(self._after_ids):
            try:
                self.after_cancel(aid)
            except Exception:  # noqa: BLE001
                pass
        self._after_ids.clear()

    def _close_window(self) -> None:
        """Fecha a janela de forma limpa e previsível."""
        if self._is_closing:
            return
        self._is_closing = True
        self._cancel_afters()
        _log.info("[BrowserV2] Fechando janela (client_id=%s)", self._client_id)
        try:
            self.destroy()
        except Exception:  # noqa: BLE001
            pass


# ------------------------------------------------------------------
# Função de entrada pública (padrão do módulo)
# ------------------------------------------------------------------
def open_files_browser_v2(
    parent: Any,
    *,
    client_id: int,
    razao: str = "",
    cnpj: str = "",
    org_id: str = "",
    bucket: str = "",
    base_prefix: str = "",
) -> UploadsBrowserWindowV2 | None:
    """Abre o Browser V2 para o cliente informado.

    Retorna a instância criada (ou None em caso de erro) para facilitar testes.
    """
    try:
        win = UploadsBrowserWindowV2(
            parent,
            client_id=client_id,
            razao=razao,
            cnpj=cnpj,
            org_id=org_id,
            bucket=bucket,
            base_prefix=base_prefix,
        )
        return win
    except Exception as exc:
        _log.error("[BrowserV2] Falha ao abrir: %s", exc, exc_info=True)
        return None
