"""Views do modulo Uploads / Arquivos."""

from __future__ import annotations

import logging
import threading
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

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
from src.ui.files_browser.utils import sanitize_filename, suggest_zip_filename
from src.ui.window_utils import show_centered
from src.utils.prefs import load_browser_status_map
from src.utils.resource_path import resource_path

from .action_bar import ActionBar
from .file_list import FileList

_executor = ThreadPoolExecutor(max_workers=4)
_log = logging.getLogger(__name__)


def _join(*parts: str) -> str:
    segs: list[str] = []
    for part in parts:
        if not part:
            continue
        segs.extend([segment for segment in str(part).split("/") if segment])
    return "/".join(segs)


def _norm(path: str) -> str:
    return _join(path)


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


class UploadsBrowserWindow(tk.Toplevel):
    """Janela principal para navegar arquivos do Storage."""

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
        self.withdraw()
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

        razao_clean = strip_cnpj_from_razao(razao, cnpj)
        cnpj_fmt = format_cnpj_for_display(cnpj)
        if module == "auditoria":
            title = f"Arquivos: {razao_clean} - {cnpj_fmt} - ID {client_id}"
        else:
            title = f"Arquivos: ID {client_id} - {razao_clean} - {cnpj_fmt}"
        self.title(title)
        try:
            self.iconbitmap(resource_path("rc.ico"))
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao aplicar iconbitmap no UploadsBrowser: %s", exc)

        self._status_cache = load_browser_status_map(self._browser_key) if module == "auditoria" else {}
        self._build_ui()
        self.minsize(1000, 620)
        self.transient(parent)
        self.update_idletasks()
        show_centered(self)
        if modal:
            try:
                self.grab_set()
                self.focus_set()
            except Exception as exc:  # noqa: BLE001
                _log.debug("Falha ao configurar janela modal do UploadsBrowser: %s", exc)
        self._populate_initial_state()

    # ------------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)  # Linha do LabelFrame principal cresce

        # Barra superior com prefixo e botão atualizar
        top_bar = ttk.Frame(self, padding=(UI_PADX, UI_PADY))
        top_bar.grid(row=0, column=0, sticky="ew")
        top_bar.columnconfigure(1, weight=1)

        ttk.Label(top_bar, text="Prefixo atual:").grid(row=0, column=0, sticky="w")
        self.prefix_var = tk.StringVar(value=self._base_prefix)
        prefix_entry = ttk.Entry(top_bar, textvariable=self.prefix_var, state="readonly")
        prefix_entry.grid(row=0, column=1, sticky="ew", padx=(UI_GAP, 0))

        # Botão Atualizar removido - recarregamento é automático

        # LabelFrame contendo a árvore de arquivos (ocupa toda a área central)
        file_frame = ttk.LabelFrame(self, text="Nome do arquivo/pasta", padding=(UI_PADX, UI_PADY))
        file_frame.grid(row=1, column=0, sticky="nsew", padx=UI_PADX, pady=(0, UI_PADY))
        file_frame.rowconfigure(0, weight=1)
        file_frame.columnconfigure(0, weight=1)

        self.file_list = FileList(
            file_frame,
            on_download=self._download_selected,
            on_delete=self._delete_selected,
            on_open_file=self._view_selected,
            on_expand_folder=self._load_folder_children,
        )
        self.file_list.grid(row=0, column=0, sticky="nsew")
        self.file_list.tree.bind("<<TreeviewSelect>>", lambda _event: self._sync_actions_state())

        # Barra de ações no rodapé
        actions = ActionBar(
            self,
            padding=(UI_PADX, UI_PADY),
            on_download=self._download_selected,
            on_download_folder=self._download_folder_zip,
            on_delete=self._delete_selected,
            on_view=self._view_selected,
        )
        actions.grid(row=2, column=0, sticky="ew")

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------
    def _populate_initial_state(self) -> None:
        self.after(100, self._refresh_listing)

    def _sync_actions_state(self) -> None:
        """Placeholder para futuros ajustes de estado conforme a seleção atual."""
        return

    def _refresh_listing(self) -> None:
        """Carrega a árvore completa de arquivos do prefixo base do cliente."""
        prefix = self._base_prefix
        self.prefix_var.set(prefix)
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
            messagebox.showinfo("Baixar pasta", "Selecione uma pasta (ex.: GERAL, SIFAP).", parent=self)
            return

        item_name, item_type, full_path = selected_info
        if item_type != "Pasta":
            messagebox.showinfo("Baixar pasta", "Selecione uma pasta (ex.: GERAL, SIFAP).", parent=self)
            return

        remote_prefix = full_path
        destination = self._ask_zip_destination(remote_prefix)
        if destination is None:
            messagebox.showinfo("ZIP", "Operacao cancelada.", parent=self)
            return

        wait: tk.Toplevel | None = None
        cancel_event = threading.Event()

        try:
            wait = tk.Toplevel(self)
            wait.withdraw()
            wait.title("Aguarde...")
            wait.resizable(False, False)
            wait.transient(self)
            try:
                wait.iconbitmap(resource_path("rc.ico"))
            except Exception as exc:  # noqa: BLE001
                _log.debug("Falha ao definir icone em janela de progresso ZIP: %s", exc)

            frm = ttk.Frame(wait, padding=12)
            frm.pack(fill="both", expand=True)
            ttk.Label(
                frm,
                text=f"Preparando ZIP no Supabase - isto pode levar alguns segundos.\nPasta: {item_name}",
            ).pack(pady=(0, 8))
            pb = ttk.Progressbar(frm, mode="indeterminate", length=260)
            pb.pack()
            pb.start(12)

            btns = ttk.Frame(frm)
            btns.pack(pady=(10, 0))
            btn_cancel = ttk.Button(btns, text="Cancelar")
            btn_cancel.pack(side="left")

            def _do_cancel() -> None:
                btn_cancel.configure(state="disabled")
                try:
                    pb.stop()
                    pb.configure(mode="determinate", value=0, maximum=100)
                except Exception as exc:  # noqa: BLE001
                    _log.debug("Falha ao parar progressbar em cancelamento ZIP: %s", exc)
                cancel_event.set()

            btn_cancel.configure(command=_do_cancel)

            try:
                wait.update_idletasks()
                show_centered(wait)
                wait.grab_set()
                wait.focus_force()
            except Exception as exc:  # noqa: BLE001
                _log.debug("Falha ao exibir dialogo de progresso zip: %s", exc)

            def _download_zip_worker() -> Path:
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
                    pb.stop()
                except Exception as exc:  # noqa: BLE001
                    _log.debug("Falha ao parar progressbar no fim do ZIP: %s", exc)
                try:
                    wait.grab_release()
                except Exception as exc:  # noqa: BLE001
                    _log.debug("Falha ao liberar grab apos ZIP: %s", exc)
                try:
                    wait.destroy()
                except Exception as exc:  # noqa: BLE001
                    _log.debug("Falha ao destruir dialogo ZIP: %s", exc)

                try:
                    destino = future.result()
                except DownloadCancelledError:
                    messagebox.showinfo("Download cancelado", "Voce cancelou o download.", parent=self)
                except TimeoutError:
                    messagebox.showerror(
                        "Tempo esgotado",
                        "O servidor nao respondeu a tempo (conexao ou leitura). Verifique sua internet e tente novamente.",
                        parent=self,
                    )
                except Exception as err:
                    messagebox.showerror("Erro ao baixar pasta", str(err), parent=self)
                else:
                    messagebox.showinfo("Download concluido", f"ZIP salvo em\n{destino}", parent=self)

                try:
                    self.lift()
                    self.attributes("-topmost", True)
                    self.after(200, lambda: self.attributes("-topmost", False))
                except Exception as exc:  # noqa: BLE001
                    _log.debug("Falha ao trazer janela para frente apos ZIP: %s", exc)

            fut.add_done_callback(lambda future: self.after(0, lambda: _on_zip_finished(future)))
        except Exception as exc:
            if wait is not None:
                try:
                    wait.grab_release()
                except Exception as exc2:  # noqa: BLE001
                    _log.debug("Falha ao liberar grab em erro de ZIP: %s", exc2)
                try:
                    wait.destroy()
                except Exception as exc2:  # noqa: BLE001
                    _log.debug("Falha ao destruir janela ZIP em erro: %s", exc2)
            _log.exception("Erro ao iniciar download da pasta como ZIP", exc_info=exc)
            messagebox.showerror("Baixar pasta", f"Falha ao baixar pasta\n{exc}", parent=self)

    def _download_selected(self) -> None:
        selected_info = self.file_list.get_selected_info()
        if not selected_info:
            messagebox.showinfo("Arquivos", "Selecione um item para baixar.", parent=self)
            return

        item_name, item_type, full_path = selected_info

        if item_type == "Pasta":
            self._download_folder_zip()
            return

        remote_key = full_path
        local_path = filedialog.asksaveasfilename(parent=self, initialfile=item_name)
        if self._is_folder(item_name):
            self._download_folder_zip()
            return

        remote_key = full_path
        local_path = filedialog.asksaveasfilename(parent=self, initialfile=item_name)
        if not local_path:
            return
        try:
            result = download_storage_object(remote_key, local_path, bucket=self._bucket)
            if result.get("ok"):
                messagebox.showinfo("Download", f"Arquivo salvo em {local_path}.", parent=self)
            else:
                error_msg = result.get("message", "Erro desconhecido ao baixar arquivo")
                messagebox.showerror("Download", error_msg, parent=self)
        except Exception as exc:
            _log.exception("Download falhou")
            messagebox.showerror("Download", f"Falha ao baixar arquivo: {exc}", parent=self)

    def _delete_selected(self) -> None:
        selected_info = self.file_list.get_selected_info()
        if not selected_info:
            return

        item_name, item_type, full_path = selected_info
        remote_key = full_path

        if item_type == "Pasta":
            if not messagebox.askyesno(
                "Excluir pasta",
                "Tem certeza que deseja excluir esta pasta e todo o conteudo? Esta acao nao pode ser desfeita.",
                parent=self,
            ):
                return
            if self._delete_folder_handler is not None:
                try:
                    self._delete_folder_handler(self._bucket, remote_key)
                except Exception as exc:  # noqa: BLE001
                    _log.exception("Erro ao excluir pasta via delete_folder_handler")
                    messagebox.showerror("Excluir pasta", f"Falha ao excluir a pasta:\n{exc}", parent=self)
                    return
            else:
                try:
                    result = delete_storage_folder(remote_key, bucket=self._bucket)
                except Exception as exc:  # noqa: BLE001
                    _log.exception("Erro ao excluir pasta (recursivo)")
                    messagebox.showerror("Excluir pasta", f"Falha ao excluir a pasta:\n{exc}", parent=self)
                    return
                if not result.get("ok"):
                    error_txt = result.get("message") or "Falha ao excluir a pasta."
                    if result.get("errors"):
                        error_txt = f"{error_txt}\n{result['errors'][0]}"
                    messagebox.showerror("Excluir pasta", error_txt, parent=self)
                    return
            self._refresh_listing()
            messagebox.showinfo("Excluir", f"Pasta '{item_name}' excluida com sucesso.", parent=self)
        else:
            if not messagebox.askyesno("Excluir", f"Deseja excluir '{item_name}'?", parent=self):
                return
            try:
                success = delete_storage_object(remote_key, bucket=self._bucket)
                if success:
                    self._refresh_listing()
                    messagebox.showinfo("Excluir", f"Arquivo '{item_name}' excluido com sucesso.", parent=self)
                else:
                    messagebox.showerror(
                        "Excluir",
                        f"Falha ao excluir '{item_name}'. Verifique as permissoes ou tente novamente.",
                        parent=self,
                    )
            except Exception as exc:
                _log.exception("Delete falhou")
                messagebox.showerror("Excluir", f"Falha ao excluir arquivo: {exc}", parent=self)

    def _open_pdf_viewer(
        self,
        *,
        pdf_path: str | None = None,
        display_name: str | None = None,
        data_bytes: bytes | None = None,
        signature: str | None = None,
    ):
        """Abre o visualizador de PDF usando o singleton global."""
        return open_pdf_viewer(self, pdf_path=pdf_path, display_name=display_name, data_bytes=data_bytes)

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
                messagebox.showinfo(
                    "Visualizar arquivo",
                    "Selecione um arquivo para visualizar.",
                    parent=self,
                )
                return
            name, item_type, full_path = selected_info

        if item_type == "Pasta":
            messagebox.showinfo(
                "Visualizar arquivo",
                "Selecione um ARQUIVO, não uma pasta.",
                parent=self,
            )
            return

        nome = name.strip()
        ext = nome.lower().rsplit(".", 1)[-1] if "." in nome else ""

        # Só permite tipos suportados pelo viewer interno
        if ext not in ("pdf", "jpg", "jpeg", "png", "gif"):
            sufixo = f".{ext}" if ext else ""
            messagebox.showinfo(
                "Visualizar arquivo",
                f"Tipo de arquivo não suportado para visualização: {sufixo}",
                parent=self,
            )
            return

        remote_key = full_path

        try:
            data = download_bytes(self._bucket, remote_key)
        except Exception as exc:  # noqa: BLE001
            _log.exception("Erro ao baixar bytes do arquivo do Supabase para visualização")
            messagebox.showerror(
                "Visualizar arquivo",
                f"Não foi possível carregar este arquivo:\n{exc}",
                parent=self,
            )
            return

        if not data:
            messagebox.showerror(
                "Visualizar arquivo",
                "Não foi possível carregar este arquivo.",
                parent=self,
            )
            return

        try:
            self._open_pdf_viewer(data_bytes=data, display_name=nome, signature=remote_key or nome)
        except Exception as exc:  # noqa: BLE001
            _log.exception("Erro ao abrir visualizador interno para arquivo do Supabase")
            messagebox.showerror(
                "Visualizar arquivo",
                f"Falha ao abrir visualização:\n{exc}",
                parent=self,
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
    window = UploadsBrowserWindow(
        parent,
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

    if modal and parent is not None:
        try:
            parent.wait_window(window)
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao aguardar janela modal do UploadsBrowser: %s", exc)

    return window
