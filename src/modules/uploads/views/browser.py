"""Views do modulo Uploads / Arquivos."""

from __future__ import annotations

import logging
import threading
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tkinter import filedialog
from typing import Any, Callable

from src.ui.dialogs.rc_dialogs import show_info, show_error, ask_yes_no

# CustomTkinter (fonte centralizada)
from src.ui.ctk_config import ctk
from src.ui.widgets.button_factory import make_btn_icon

from src.modules.uploads.components.helpers import (
    client_prefix_for_id,
    format_cnpj_for_display,
    get_clients_bucket,
    strip_cnpj_from_razao,
)
from src.modules.uploads.service import (
    DownloadCancelledError,
    delete_storage_folder,
    delete_storage_object,
    download_bytes,
    download_folder_zip,
    download_storage_object,
    list_browser_items,
)
from src.modules.pdf_preview import open_pdf_viewer
from src.ui.components.progress_dialog import ProgressDialog
from src.ui.files_browser.utils import sanitize_filename, suggest_zip_filename
from src.ui.window_utils import prepare_hidden_window, show_centered_no_flash
from src.ui.dark_window_helper import set_win_dark_titlebar
from src.utils.prefs import load_browser_status_map
from src.utils.resource_path import resource_path

from .action_bar import ActionBar
from .file_list import FileList

import atexit as _atexit

_executor = ThreadPoolExecutor(max_workers=4)
_atexit.register(_executor.shutdown, wait=False)
_log = logging.getLogger(__name__)


def _resolve_parent(parent: Any) -> tk.Misc:
    """Resolve parent para um widget Tk válido ou levanta RuntimeError."""
    if isinstance(parent, tk.Misc):
        return parent
    try:
        default_root = getattr(tk, "_default_root", None)
    except Exception:  # noqa: BLE001
        default_root = None
    if isinstance(default_root, tk.Misc):
        return default_root
    raise RuntimeError(
        "UploadsBrowser: root/parent Tk não encontrado. "
        "Passe o parent (janela principal) ao abrir o navegador de arquivos."
    )


def _join(*parts: str) -> str:
    segs: list[str] = []
    for part in parts:
        if not part:
            continue
        segs.extend([segment for segment in str(part).split("/") if segment])
    return "/".join(segs)


def _norm(path: str) -> str:
    return _join(path)


def _short_prefix(p: str, max_len: int = 50) -> str:
    """Trunca o prefixo para exibição com reticências se exceder max_len."""
    p = p or ""
    return p if len(p) <= max_len else (p[:max_len] + "…")


def _short_client_code(prefix: str) -> str:
    """Abrevia o código do cliente no formato: prefix[:12] + '…' + prefix[-8:]."""
    p = prefix or ""
    return p if len(p) <= 24 else f"{p[:12]}…{p[-8:]}"


UI_GAP = 6
UI_PADX = 8
UI_PADY = 6
ZIP_TIMEOUT_SECONDS = 300

FOLDER_STATUS_NEUTRAL = "neutral"
FOLDER_STATUS_READY = "ready"
FOLDER_STATUS_NOTREADY = "notready"

STATUS_GLYPHS = {
    FOLDER_STATUS_NEUTRAL: ".",
    FOLDER_STATUS_READY: "OK",
    FOLDER_STATUS_NOTREADY: "X",
}


class UploadsBrowserWindow(ctk.CTkToplevel):  # type: ignore[misc]
    """Janela principal para navegar arquivos do Storage (CustomTkinter)."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        org_id: str = "",
        client_id: int,
        razao: str = "",
        cnpj: str = "",
        bucket: str | None = None,
        base_prefix: str | None = None,
        supabase=None,  # type: ignore[no-untyped-def]
        start_prefix: str = "",
        module: str = "",
        modal: bool = False,
        delete_folder_handler: Callable[[str, str], Any] | None = None,
    ) -> None:
        super().__init__(parent)
        prepare_hidden_window(self)  # BUGFIX: Evitar flash branco ao abrir
        self._is_closing = False
        self._supabase = supabase
        self._module = module
        self._org_id = org_id
        self._client_id = client_id
        self._razao = razao
        self._cnpj = cnpj
        self._browser_key = f"org:{org_id}|client:{client_id}|module:{module or 'clientes'}"
        self._bucket = (bucket or get_clients_bucket()).strip()
        self._base_prefix = _norm(base_prefix or client_prefix_for_id(client_id, org_id))
        self._last_download_dir: str | None = None
        self._delete_folder_handler = delete_folder_handler
        self._pdf_viewer_window = None
        self._last_view_signature: str | None = None
        self._download_in_progress = False

        razao_clean = strip_cnpj_from_razao(razao, cnpj)
        cnpj_fmt = format_cnpj_for_display(cnpj)
        if module == "auditoria":
            title = f"Arquivos: {razao_clean} - {cnpj_fmt} - ID {client_id}"
        else:
            title = f"Arquivos: ID {client_id} - {razao_clean} - {cnpj_fmt}"
        self.title(title)

        # FIX: Apenas iconbitmap (Windows), sem carregar PNG para evitar uso em Label
        try:
            self.iconbitmap(resource_path("rc.ico"))
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao aplicar iconbitmap no UploadsBrowser: %s", exc)

        self._status_cache = load_browser_status_map(self._browser_key) if module == "auditoria" else {}
        self._build_ui()
        self.minsize(1000, 620)
        self.transient(parent)
        self.update_idletasks()

        # BUGFIX: Aplicar titlebar escura no Windows antes de mostrar
        set_win_dark_titlebar(self)

        # BUGFIX: Mostrar janela sem flash usando show_centered_no_flash
        show_centered_no_flash(self, parent, width=1000, height=620)

        # Registrar handler de fechamento
        self.protocol("WM_DELETE_WINDOW", self._close_window)

        # Bind ESC para fechar (usar mesmo handler)
        self.bind("<Escape>", lambda e: self._close_window())

        if modal:
            # Aplicar grab_set APENAS quando janela estiver viewable
            self.after(10, lambda: self._setup_modal_safe())

        self._populate_initial_state()

    # ------------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)  # Linha do LabelFrame principal cresce

        # Barra superior com código do cliente e botão refresh
        top_bar = ctk.CTkFrame(self)  # type: ignore[union-attr]
        top_bar.grid(row=0, column=0, sticky="ew", padx=UI_PADX, pady=(UI_PADY, 0))  # type: ignore[union-attr]
        top_bar.columnconfigure(0, weight=1)  # Entry expande  # type: ignore[union-attr]
        top_bar.columnconfigure(1, weight=0)  # Botão fixo  # type: ignore[union-attr]

        # Entry única com código do cliente
        self.prefix_var = tk.StringVar(value=f"Código do cliente no Supabase: {_short_client_code(self._base_prefix)}")
        prefix_entry = ctk.CTkEntry(top_bar, textvariable=self.prefix_var, state="readonly", width=500)  # type: ignore[union-attr]
        prefix_entry.grid(row=0, column=0, sticky="ew", padx=(0, UI_GAP))

        # Botão refresh (ícone-only) à direita
        btn_refresh_top = make_btn_icon(top_bar, text="⟳", width=40, command=self._refresh_listing)  # type: ignore[union-attr]
        btn_refresh_top.grid(row=0, column=1, sticky="e")

        # Frame contendo a árvore de arquivos (ocupa toda a área central)
        file_frame = ctk.CTkFrame(self)  # type: ignore[union-attr]
        file_frame.grid(row=1, column=0, sticky="nsew", padx=UI_PADX, pady=(UI_PADY, UI_PADY))  # type: ignore[union-attr]
        file_frame.rowconfigure(0, weight=1)  # Lista cresce  # type: ignore[union-attr]
        file_frame.rowconfigure(1, weight=0)  # Barra fixa  # type: ignore[union-attr]
        file_frame.columnconfigure(0, weight=1)  # type: ignore[union-attr]

        # FileList no topo
        self.file_list = FileList(
            file_frame,
            on_download=self._download_selected,
            on_delete=self._delete_selected,
            on_open_file=self._view_selected,
            on_expand_folder=self._load_folder_children,
            on_download_folder=self._download_folder_zip,
        )
        self.file_list.grid(row=0, column=0, sticky="nsew")
        self.file_list.tree.bind("<<TreeviewSelect>>", lambda _event: self._sync_actions_state())

        # Barra de ações embaixo da lista
        self.actions = ActionBar(
            file_frame,
            on_download=self._download_selected,
            on_download_folder=self._download_folder_zip,
            on_delete=self._delete_selected,
            on_view=self._view_selected,
            on_close=self._close_window,
        )
        self.actions.grid(row=1, column=0, sticky="ew", pady=(8, 0))

    # ------------------------------------------------------------------
    # UI actions
    # ------------------------------------------------------------------
    def _setup_modal_safe(self, retry_count: int = 0) -> None:
        """Configura comportamento modal APENAS quando janela está viewable.

        Args:
            retry_count: Contador de tentativas (máx 10 para evitar loop infinito)
        """
        max_retries = 10
        retry_delay_ms = 50

        try:
            # Verificar se a janela ainda existe
            if not self.winfo_exists():
                _log.warning("[UploadsBrowser] Janela não existe mais, abortando modal setup")
                return

            # Verificar se a janela está viewable (mapeada e visível)
            if not self.winfo_viewable():
                if retry_count < max_retries:
                    _log.info(
                        f"[UploadsBrowser] Janela não-viewable (tentativa {retry_count + 1}/{max_retries}), "
                        f"reagendando grab_set em {retry_delay_ms}ms"
                    )
                    self.after(retry_delay_ms, lambda: self._setup_modal_safe(retry_count + 1))
                    return
                else:
                    _log.warning(
                        f"[UploadsBrowser] Janela não ficou viewable após {max_retries} tentativas, "
                        f"abortando grab_set (modal pode não funcionar)"
                    )
                    return

            # Janela está viewable, aplicar grab_set
            self.grab_set()
            self.focus_set()
            _log.info("[UploadsBrowser] grab_set aplicado com sucesso (viewable=True)")

        except Exception as e:
            _log.error(f"[UploadsBrowser] Erro ao aplicar grab_set: {e}")

    def _close_window(self) -> None:
        """Fecha a janela respeitando o flag _is_closing e liberando grab."""
        if not self._is_closing:
            self._is_closing = True

            # Liberar grab ANTES de destruir (previne grab preso)
            try:
                self.grab_release()
                _log.debug("[UploadsBrowser] grab_release executado")
            except Exception as e:
                _log.debug(f"[UploadsBrowser] Erro em grab_release: {e}")

            self.destroy()

    def _show_download_done_dialog(self, text: str) -> None:
        """Mostra messagebox nativo do Windows para download concluído."""
        # FIX: Usar messagebox.showinfo nativo do Windows em vez de Toplevel custom
        # Isso cria um diálogo padrão do sistema operacional (não Tk)
        show_info(self, "Download", text)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------
    def _populate_initial_state(self) -> None:
        self.after(100, self._refresh_listing)

    def _sync_actions_state(self) -> None:
        """Atualiza o estado dos botões de ação conforme a seleção atual."""
        selected_info = self.file_list.get_selected_info()

        if not selected_info:
            # Nada selecionado: desabilitar todos os botões
            self.actions.set_enabled(download=False, download_folder=False, delete=False, view=False)
            return

        _, item_type, _ = selected_info

        if item_type == "Pasta":
            # Pasta selecionada: habilitar apenas download_folder e delete
            self.actions.set_enabled(download=False, download_folder=True, delete=True, view=False)
        else:
            # Arquivo selecionado: habilitar download, view e delete
            self.actions.set_enabled(download=True, download_folder=False, delete=True, view=True)

    def _refresh_listing(self) -> None:
        """Carrega a árvore completa de arquivos do prefixo base do cliente."""
        prefix = self._base_prefix
        self.prefix_var.set(f"Código do cliente no Supabase: {_short_client_code(prefix)}")
        _log.info("Browser prefix atual: %s (bucket=%s, cliente=%s)", prefix, self._bucket, self._client_id)
        items = list_browser_items(prefix, bucket=self._bucket)
        self.file_list.populate_tree_hierarchical(items, self._base_prefix, self._status_cache)
        self._sync_actions_state()

    def _load_folder_children(self, folder_path: str) -> list[dict]:
        """Carrega os filhos de uma pasta específica (lazy loading)."""
        _log.info("Carregando filhos de: %s", folder_path)
        # Garantir que folder_path termine com / para listar dentro da pasta
        if not folder_path.endswith("/"):
            folder_path = folder_path + "/"
        items = list_browser_items(folder_path, bucket=self._bucket)
        return list(items)  # Convert Iterable to list

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _is_folder(self, item_name: str | None) -> bool:
        """Determina se o item selecionado é pasta, usando a coluna 'Tipo'."""
        info = self.file_list.get_selected_info()
        if not info:
            return False
        _, item_type, _ = info
        return item_type.lower() == "pasta"

    def _suggest_zip_stem(self, remote_prefix: str) -> str:
        base_name = suggest_zip_filename(remote_prefix)
        sufixo = self._cnpj or f"ID {self._client_id}"
        composed = f"{base_name} - {sufixo} - {self._razao}".strip()
        return sanitize_filename(composed) or "arquivos"

    def _ask_zip_destination(self, remote_prefix: str) -> Path | None:
        initial_dir = self._last_download_dir or str(Path.home() / "Downloads")
        chosen_dir = filedialog.askdirectory(
            parent=self,
            initialdir=initial_dir,
            title="Escolha a pasta para salvar o ZIP",
            mustexist=True,
        )
        if not chosen_dir:
            self._last_download_dir = None
            return None

        self._last_download_dir = str(chosen_dir)
        stem = self._suggest_zip_stem(remote_prefix)
        return Path(chosen_dir) / f"{stem}.zip"

    def _download_folder_zip(self) -> None:
        selected_info = self.file_list.get_selected_info()
        if not selected_info:
            show_info(self, "Baixar pasta", "Selecione uma pasta (ex.: GERAL, SIFAP).")
            return

        item_name, item_type, full_path = selected_info
        if item_type != "Pasta":
            show_info(self, "Baixar pasta", "Selecione uma pasta (ex.: GERAL, SIFAP).")
            return

        remote_prefix = full_path
        destination = self._ask_zip_destination(remote_prefix)
        if destination is None:
            show_info(self, "ZIP", "Operacao cancelada.")
            return

        cancel_event = threading.Event()

        def _do_cancel() -> None:
            cancel_event.set()
            try:
                dlg.set_eta_text("Cancelando...")
            except Exception as exc:  # noqa: BLE001
                # Dialog pode estar destruído - cancelamento continua
                _log.debug("Falha ao atualizar texto de cancelamento: %s", type(exc).__name__)

        dlg = ProgressDialog(
            parent=self,
            title="Aguarde...",
            message="Preparando ZIP no Supabase.",
            detail=f"Pasta: {item_name}",
            can_cancel=True,
            on_cancel=_do_cancel,
        )
        dlg.set_progress(None)  # indeterminate
        dlg.set_eta_text("Aguardando resposta do servidor...")

        def _download_zip_worker() -> Path:
            """Worker que baixa ZIP."""
            return Path(
                download_folder_zip(
                    remote_prefix,
                    bucket=self._bucket,
                    zip_name=destination.stem,
                    out_dir=str(destination.parent),
                    timeout_s=ZIP_TIMEOUT_SECONDS,
                    cancel_event=cancel_event,
                )
            )

        fut = _executor.submit(_download_zip_worker)

        def _on_zip_finished(future) -> None:  # type: ignore[no-untyped-def]
            try:
                dlg.close()
            except Exception as exc:  # noqa: BLE001
                _log.debug("Falha ao fechar dialogo ZIP: %s", exc)

            try:
                destino = future.result()
            except DownloadCancelledError:
                show_info(self, "Download cancelado", "Voce cancelou o download.")
            except TimeoutError:
                show_error(
                    self,
                    "Tempo esgotado",
                    "O servidor nao respondeu a tempo (conexao ou leitura). Verifique sua internet e tente novamente.",
                )
            except Exception as err:
                show_error(self, "Erro ao baixar pasta", str(err))
            else:
                show_info(self, "Download concluído", f"ZIP salvo em:\n{destino}")

            try:
                self.lift()
                self.attributes("-topmost", True)
                self.after(200, lambda: self.attributes("-topmost", False))
            except Exception as exc:  # noqa: BLE001
                _log.debug("Falha ao trazer janela para frente apos ZIP: %s", exc)

        fut.add_done_callback(lambda future: self.after(0, lambda: _on_zip_finished(future)))

    def _download_selected(self) -> None:
        # Guard contra duplo-clique/execução duplicada
        if self._download_in_progress:
            return

        selected_info = self.file_list.get_selected_info()
        if not selected_info:
            show_info(self, "Arquivos", "Selecione um item para baixar.")
            return

        item_name, item_type, full_path = selected_info

        # Bloquear download de pasta pelo botão "Baixar"
        if item_type == "Pasta":
            show_info(self, "Baixar", "Para pasta, use o botão 'Baixar pasta (.zip)'.")
            return

        # Download de arquivo
        remote_key = full_path
        local_path = filedialog.asksaveasfilename(parent=self, initialfile=item_name)
        if not local_path:
            return

        self._download_in_progress = True
        try:
            result = download_storage_object(remote_key, local_path, bucket=self._bucket)
            if result.get("ok"):
                self._show_download_done_dialog(f"Arquivo salvo em {local_path}.")
            else:
                error_msg = result.get("message", "Erro desconhecido ao baixar arquivo")
                show_error(self, "Download", error_msg)
        except Exception as exc:
            _log.exception("Download falhou")
            show_error(self, "Download", f"Falha ao baixar arquivo: {exc}")
        finally:
            self._download_in_progress = False

    def _delete_selected(self) -> None:
        selected_info = self.file_list.get_selected_info()
        if not selected_info:
            return

        item_name, item_type, full_path = selected_info
        remote_key = full_path

        if item_type == "Pasta":
            if not ask_yes_no(
                self,
                "Excluir pasta",
                "Tem certeza que deseja excluir esta pasta e todo o conteudo? Esta acao nao pode ser desfeita.",
            ):
                return
            if self._delete_folder_handler is not None:
                try:
                    self._delete_folder_handler(self._bucket, remote_key)
                except Exception as exc:  # noqa: BLE001
                    _log.exception("Erro ao excluir pasta via delete_folder_handler")
                    show_error(self, "Excluir pasta", f"Falha ao excluir a pasta:\n{exc}")
                    return
            else:
                try:
                    result = delete_storage_folder(remote_key, bucket=self._bucket)
                except Exception as exc:  # noqa: BLE001
                    _log.exception("Erro ao excluir pasta (recursivo)")
                    show_error(self, "Excluir pasta", f"Falha ao excluir a pasta:\n{exc}")
                    return
                if not result.get("ok"):
                    error_txt = result.get("message") or "Falha ao excluir a pasta."
                    if result.get("errors"):
                        error_txt = f"{error_txt}\n{result['errors'][0]}"
                    show_error(self, "Excluir pasta", error_txt)
                    return
            self._refresh_listing()
            show_info(self, "Excluir", f"Pasta '{item_name}' excluida com sucesso.")
        else:
            if not ask_yes_no(self, "Excluir", f"Deseja excluir '{item_name}'?"):
                return
            try:
                success = delete_storage_object(remote_key, bucket=self._bucket)
                if success:
                    self._refresh_listing()
                    show_info(self, "Excluir", f"Arquivo '{item_name}' excluido com sucesso.")
                else:
                    show_error(
                        self,
                        "Excluir",
                        f"Falha ao excluir '{item_name}'. Verifique as permissoes ou tente novamente.",
                    )
            except Exception as exc:
                _log.exception("Delete falhou")
                show_error(self, "Excluir", f"Falha ao excluir arquivo: {exc}")

    def _open_pdf_viewer(
        self,
        *,
        pdf_path: str | None = None,
        display_name: str | None = None,
        data_bytes: bytes | None = None,
        _signature: str | None = None,
        signature: str | None = None,  # Compatibilidade com chamadas antigas
    ):
        """Abre o visualizador de PDF usando o singleton global.

        Args:
            pdf_path: Caminho local do PDF
            display_name: Nome para exibir
            data_bytes: Bytes do arquivo
            _signature: Assinatura/identificador (nome preferido)
            signature: Alias para _signature (compatibilidade)
        """
        # Compatibilidade: se passou signature mas não _signature, usar signature
        if _signature is None and signature is not None:
            _signature = signature

        return open_pdf_viewer(
            self,
            pdf_path=pdf_path,
            display_name=display_name,
            data_bytes=data_bytes,
        )

    def _view_selected(self, name: str = "", item_type: str = "", full_path: str = "") -> None:
        """Abre o arquivo selecionado no visualizador interno de PDF/imagens.

        - Se nada estiver selecionado: mostra aviso.
        - Se for pasta: informa que apenas arquivos podem ser visualizados.
        - Se a extensão não for suportada: informa o usuário.
        - Caso contrário: baixa os bytes do Supabase e abre no viewer nativo.
        """
        # Se chamado pelo callback do duplo clique, usa os parâmetros
        # Se chamado pelo botão, busca da seleção atual
        if not name:
            selected_info = self.file_list.get_selected_info()
            if not selected_info:
                show_info(
                    self,
                    "Visualizar arquivo",
                    "Selecione um arquivo para visualizar.",
                )
                return
            name, item_type, full_path = selected_info

        if item_type == "Pasta":
            show_info(
                self,
                "Visualizar arquivo",
                "Selecione um ARQUIVO, não uma pasta.",
            )
            return

        nome = name.strip()
        ext = nome.lower().rsplit(".", 1)[-1] if "." in nome else ""

        # Só permite tipos suportados pelo viewer interno
        if ext not in ("pdf", "jpg", "jpeg", "png", "gif"):
            sufixo = f".{ext}" if ext else ""
            show_info(
                self,
                "Visualizar arquivo",
                f"Tipo de arquivo não suportado para visualização: {sufixo}",
            )
            return

        remote_key = full_path

        try:
            data = download_bytes(self._bucket, remote_key)
        except Exception as exc:  # noqa: BLE001
            _log.exception("Erro ao baixar bytes do arquivo do Supabase para visualização")
            show_error(
                self,
                "Visualizar arquivo",
                f"Não foi possível carregar este arquivo:\n{exc}",
            )
            return

        if not data:
            show_error(
                self,
                "Visualizar arquivo",
                "Não foi possível carregar este arquivo.",
            )
            return

        try:
            self._open_pdf_viewer(data_bytes=data, display_name=nome, signature=remote_key or nome)
        except Exception as exc:  # noqa: BLE001
            _log.exception("Erro ao abrir visualizador interno para arquivo do Supabase")
            show_error(
                self,
                "Visualizar arquivo",
                f"Falha ao abrir visualização:\n{exc}",
            )


def open_files_browser(
    parent,
    *,
    org_id: str = "",
    client_id: int,
    razao: str = "",
    cnpj: str = "",
    bucket: str | None = None,
    base_prefix: str | None = None,
    supabase=None,  # type: ignore[no-untyped-def]
    start_prefix: str = "",
    module: str = "",
    modal: bool = False,
    delete_folder_handler: Callable[[str, str], Any] | None = None,
) -> UploadsBrowserWindow:
    """
    Entry point compatível com o open_files_browser legacy.

    Args:
        parent: Widget pai
        org_id: ID da organização
        client_id: ID do cliente
        razao: Razão social do cliente (opcional)
        cnpj: CNPJ do cliente (opcional)
        bucket: Nome do bucket (opcional, default: get_clients_bucket())
        base_prefix: Prefixo base do cliente (opcional)
        supabase: Cliente Supabase (opcional, não usado atualmente)
        start_prefix: Prefixo inicial para navegação (opcional)
        module: Nome do módulo que está abrindo o browser (ex: "auditoria")
        modal: Se True, janela fica modal ao parent
        delete_folder_handler: Handler para exclusao de pastas (opcional)

    Returns:
        Janela UploadsBrowserWindow criada e exibida
    """
    resolved_parent = _resolve_parent(parent)
    window = UploadsBrowserWindow(
        resolved_parent,
        org_id=org_id,
        client_id=client_id,
        razao=razao,
        cnpj=cnpj,
        bucket=bucket,
        base_prefix=base_prefix,
        supabase=supabase,
        start_prefix=start_prefix,
        module=module,
        modal=modal,
        delete_folder_handler=delete_folder_handler,
    )

    window.deiconify()

    if modal:
        try:
            resolved_parent.wait_window(window)
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao aguardar janela modal do UploadsBrowser: %s", exc)

    return window
