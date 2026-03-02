# -*- coding: utf-8 -*-
"""Diálogo de gerenciamento de arquivos do cliente - ClientesV2.

Browser funcional de arquivos com Supabase Storage.

Fase 5: Refatorado em mixins para melhor manutenção:
  - _files_ui_mixin.py: Construção de UI e estado visual
  - _files_navigation_mixin.py: Navegação na árvore, renderização
  - _files_upload_mixin.py: Upload e exclusão de arquivos
  - _files_download_mixin.py: Download, visualização e ZIP
"""

from __future__ import annotations

import importlib
import logging
import os
import queue
import threading
import time
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional

from src.ui.ctk_config import ctk
from src.ui.ui_tokens import APP_BG
from src.ui.dark_window_helper import set_win_dark_titlebar
from src.ui.window_utils import apply_window_icon

from src.modules.clientes.ui.views._files_ui_mixin import FilesUIMixin
from src.modules.clientes.ui.views._files_navigation_mixin import FilesNavigationMixin
from src.modules.clientes.ui.views._files_upload_mixin import FilesUploadMixin
from src.modules.clientes.ui.views._files_download_mixin import FilesDownloadMixin, DownloadResultDialog  # noqa: F401 – re-export

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


class ClientFilesDialog(FilesDownloadMixin, FilesUploadMixin, FilesNavigationMixin, FilesUIMixin, ctk.CTkToplevel):
    """Diálogo para gerenciar arquivos de um cliente.

    Browser funcional com operações: listar, upload, download, excluir.

    Mixins (Fase 5):
      - FilesUIMixin: _build_ui, progress, button states, title, header
      - FilesNavigationMixin: tree events, refresh, render, navigate
      - FilesUploadMixin: upload, delete file/folder
      - FilesDownloadMixin: download, open/visualize, ZIP
    """

    def __init__(
        self,
        parent: Any,
        client_id: int,
        client_name: str = "Cliente",
        razao_social: str = "",
        cnpj: str = "",
        **kwargs: Any,
    ):
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
        self._executor: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="ClientFiles")

        # PROTEÇÃO: Controle de fechamento e after jobs
        self._closing: bool = False
        self._after_ids: set[str] = set()

        # Configurar janela (titlebar) — CNPJ sempre visível, razão truncada
        self._set_smart_title()  # pyright: ignore[reportAttributeAccessIssue]

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

        # Configurar ícone RC sem flash (antes de deiconify)
        try:
            apply_window_icon(self)
        except Exception:
            pass  # Ignora se falhar (Linux/Mac ou ícone não encontrado)

        # Centralizar
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (1000 // 2)
        y = (self.winfo_screenheight() // 2) - (650 // 2)
        self.geometry(f"1000x650+{x}+{y}")

        # Tornar modal (transient primeiro, grab depois)
        self.transient(parent)

        # Pré-carregar ícones do TreeView com PIL (referência em self evita garbage-collect)
        # Pastas NÃO usam image= — mantêm prefixo emoji no texto ("📁 nome")
        # PDFs e arquivos genéricos usam ícone de documento desenhado por PIL
        self._img_pdf: Any = None
        self._img_file: Any = None
        try:
            from PIL import Image, ImageDraw
            from PIL.ImageTk import PhotoImage as _ItkPhoto

            def _doc_icon(page_rgba: tuple, border_rgba: tuple) -> Any:
                """Desenha ícone de documento 14×16 com canto dobrado (dog-ear)."""
                W, H, fold = 14, 16, 4  # noqa: N806
                img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                d = ImageDraw.Draw(img)
                body = [(0, 0), (W - 1 - fold, 0), (W - 1, fold), (W - 1, H - 1), (0, H - 1)]
                d.polygon(body, fill=page_rgba, outline=border_rgba)
                d.polygon([(W - 1 - fold, 0), (W - 1, fold), (W - 1 - fold, fold)], fill=border_rgba)
                return _ItkPhoto(img)

            self._img_pdf = _doc_icon((220, 53, 69, 255), (150, 20, 40, 255))  # vermelho
            self._img_file = _doc_icon((180, 180, 190, 255), (110, 110, 120, 255))  # cinza
        except Exception as _icon_err:
            log.debug(f"[ClientFiles] Ícones PIL indisponíveis, usando fallback: {_icon_err}")

            # Fallback: quadrado de 1 pixel (invisível mas sem crash)
            def _tiny(color: str) -> tk.PhotoImage:
                im = tk.PhotoImage(width=1, height=1)
                im.put(color)
                return im

            self._img_pdf = _tiny("#dc3545")
            self._img_file = _tiny("#aaaaaa")

        # Construir UI completa ANTES de exibir
        self._build_ui()  # pyright: ignore[reportAttributeAccessIssue]

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
        from src.ui.dialogs.rc_dialogs import show_error
        from src.modules.uploads.components.helpers import get_current_org_id

        # Verificar se o cliente Supabase foi resolvido
        if self.supabase is None:
            log.error("[ClientFiles] Cliente Supabase não disponível")
            self.status_label.configure(
                text="❌ Erro: Cliente Supabase não disponível. Verifique a configuração.", text_color="#ef4444"
            )
            show_error(
                self,
                "Erro de Configuração",
                "Não foi possível conectar ao Supabase.\nVerifique a configuração e tente novamente.",
            )
            return

        try:
            self._org_id = get_current_org_id(self.supabase)
            log.info(f"[ClientFiles] org_id resolvido: {self._org_id}")
        except Exception as e:
            log.error(f"[ClientFiles] Erro ao resolver org_id: {e}", exc_info=True)
            self._org_id = ""

        self._refresh_files()  # pyright: ignore[reportAttributeAccessIssue]

    # ── Lifecycle helpers ─────────────────────────────────────────

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

    def _shutdown_executor(self) -> None:
        """Encerra o ThreadPoolExecutor de forma idempotente e não-bloqueante.

        Seguro para chamar múltiplas vezes — ignora silenciosamente se já
        encerrado (self._executor is None).
        """
        executor = self._executor
        if executor is None:
            return
        # Zera imediatamente para impedir novos submits antes do shutdown terminar
        self._executor = None  # pyright: ignore[reportAttributeAccessIssue]
        try:
            executor.shutdown(wait=False, cancel_futures=True)
            log.debug("[ClientFiles] ThreadPoolExecutor finalizado (cancel_futures)")
        except TypeError:
            # Python < 3.9 não suporta cancel_futures
            try:
                executor.shutdown(wait=False)
                log.debug("[ClientFiles] ThreadPoolExecutor finalizado (sem cancel_futures)")
            except Exception as e:
                log.warning(f"[ClientFiles] Erro ao finalizar executor (fallback): {e}")
        except Exception as e:
            log.warning(f"[ClientFiles] Erro ao finalizar executor: {e}")

    def _safe_close(self) -> None:
        """Fecha dialog com cleanup seguro."""
        if self._closing:
            return
        self._closing = True
        self._cancel_afters()

        self._shutdown_executor()

        try:
            self.destroy()
        except Exception:
            pass

    # ── Utilidades estáticas ──────────────────────────────────────

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
