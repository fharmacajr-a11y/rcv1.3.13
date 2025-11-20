"""Fluxo de upload para a tela de Auditoria (encapsulado em helper)."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox
from typing import TYPE_CHECKING, Any, Callable

from src.modules.auditoria.service import ArchiveError, AuditoriaServiceError
from src.modules.uploads.components.helpers import client_prefix_for_id
from src.ui.dialogs.file_select import select_archive_file
from ..application import AuditoriaApplication
from .dialogs import DuplicatesDialog, UploadProgressDialog

if TYPE_CHECKING:  # pragma: no cover
    from .main_frame import AuditoriaFrame

try:
    from src.modules.uploads import open_files_browser  # type: ignore[import-untyped]
except Exception:
    open_files_browser = None  # fallback defensivo


@dataclass
class ProgressState:
    total_files: int = 0
    total_bytes: int = 0
    done_files: int = 0
    done_bytes: int = 0
    start_ts: float = 0.0
    ema_bps: float = 0.0  # Exponential Moving Average de bytes por segundo
    skipped_count: int = 0  # Arquivos pulados (duplicatas com strategy=skip)
    failed_count: int = 0  # Arquivos que falharam no upload


class AuditoriaUploadFlow:
    def __init__(self, frame: "AuditoriaFrame", controller: AuditoriaApplication):  # type: ignore[name-defined]
        self.frame = frame
        self.controller = controller
        self._progress_dialog: UploadProgressDialog | None = None
        self._cancel_flag = False

    # ---------- Progresso ----------
    def _handle_upload_progress(self, state: ProgressState, progress: Any) -> None:
        """Recebe progresso do service e atualiza o estado local na thread principal."""

        def _apply() -> None:
            state.total_files = progress.total_files
            state.total_bytes = progress.total_bytes
            state.done_files = progress.done_files
            state.done_bytes = progress.done_bytes
            state.skipped_count = progress.skipped_duplicates
            state.failed_count = progress.failed_count
            dialog = self._progress_dialog
            if dialog:
                dialog.update_with_state(state)

        self.frame.after(0, _apply)

    def _open_progress_dialog(self, titulo: str, msg: str) -> None:
        self._close_progress_dialog()
        self._cancel_flag = False
        self._progress_dialog = UploadProgressDialog(self.frame, titulo, msg, on_cancel=self._on_progress_cancel)

    def _close_progress_dialog(self) -> None:
        if self._progress_dialog:
            self._progress_dialog.close()
            self._progress_dialog = None

    def _on_progress_cancel(self) -> None:
        self._cancel_flag = True

    def _ask_rollback(self, uploaded_paths: list[str], bucket: str) -> None:
        """
        Pergunta ao usuário se deseja reverter arquivos já enviados após cancelamento.

        Args:
            uploaded_paths: Lista de caminhos completos dos arquivos enviados
            bucket: Nome do bucket
        """
        self._close_progress_dialog()

        if not uploaded_paths:
            messagebox.showinfo("Cancelado", "Upload cancelado. Nenhum arquivo foi enviado.")
            return

        msg = f"Upload cancelado.\n\n{len(uploaded_paths)} arquivo(s) já foram enviados.\n\nDeseja remover esses arquivos?"
        if messagebox.askyesno("Cancelar e Reverter", msg):
            # Lançar thread para remover arquivos
            def _do_rollback() -> None:
                try:
                    # Remover em lotes de 1000 (limite da API)
                    batch_size = 1000
                    for i in range(0, len(uploaded_paths), batch_size):
                        batch = uploaded_paths[i : i + batch_size]
                        self.controller.remove_storage_objects(bucket, batch)

                    self.frame.after(0, lambda: messagebox.showinfo("Revertido", f"{len(uploaded_paths)} arquivo(s) removido(s) com sucesso."))
                except AuditoriaServiceError as exc:
                    self.frame.after(0, lambda err=str(exc): messagebox.showerror("Erro ao Reverter", f"Falha ao remover arquivos:\n{err}"))

            threading.Thread(target=_do_rollback, daemon=True).start()
        else:
            messagebox.showinfo("Cancelado", "Upload cancelado. Arquivos já enviados foram mantidos.")

    def _busy_done(self, ok: int, fail: list[tuple[str, str]], base_prefix: str, cliente_nome: str, cnpj: str, client_id: int, org_id: str) -> None:
        """
        Callback de sucesso do upload (executado na thread principal via after()).

        Args:
            ok: Número de arquivos enviados com sucesso
            fail: Lista de falhas [(path, erro)]
            base_prefix: Prefixo do Storage onde foram enviados
            cliente_nome: Nome do cliente
            cnpj: CNPJ do cliente
            client_id: ID do cliente
            org_id: ID da organização
        """
        # FASE 1: Fechar modal primeiro
        self._close_progress_dialog()

        if self._cancel_flag:
            messagebox.showinfo("Upload cancelado", "O upload foi cancelado pelo usuário.")
            return

        try:
            from helpers.formatters import format_cnpj as _format_cnpj  # import local para evitar dependência circular
        except Exception:

            def _format_cnpj(raw: str) -> str:
                return raw

        def _format_cnpj_normalizer(value: str) -> str:
            return _format_cnpj(value)

        normalizer: Callable[[str], str] = _format_cnpj_normalizer

        c_digits = "".join(filter(str.isdigit, cnpj or ""))
        cnpj_fmt = normalizer(c_digits) if c_digits else cnpj
        msg = f"Upload concluído para {cliente_nome} — {cnpj_fmt}.\n"
        msg += f"{ok} arquivo(s) enviado(s)."

        if fail:
            msg += f"\n\nFalhas: {len(fail)}"
            for path, err in fail[:3]:  # limita a 3 erros
                msg += f"\n• {Path(path).name}: {err}"
            if len(fail) > 3:
                msg += f"\n... e mais {len(fail) - 3} erro(s)"

        messagebox.showinfo("Auditoria", msg)

        # FASE 2: Reabrir browser após 50ms (finalização suave)
        def _refresh_browser() -> None:
            try:
                if open_files_browser:
                    base_client_prefix = client_prefix_for_id(client_id, org_id)
                    bucket = self.controller.get_clients_bucket()
                    delete_handler = self.controller.make_delete_folder_handler(base_prefix)
                    open_files_browser(
                        self.frame,
                        supabase=self.controller.get_supabase_client(),
                        client_id=client_id,
                        org_id=org_id,
                        razao=cliente_nome,
                        cnpj=cnpj,
                        bucket=bucket,
                        base_prefix=base_client_prefix,
                        start_prefix=base_prefix,
                        module="auditoria",
                        modal=True,
                        delete_folder_handler=delete_handler,
                    )
            except Exception as e:
                print(f"[AUDITORIA][UPLOAD] Não foi possível abrir browser: {e}")

        self.frame.after(50, _refresh_browser)

    def _busy_fail(self, err: str) -> None:
        """
        Callback de erro do upload (executado na thread principal via after()).

        Args:
            err: Mensagem de erro
        """
        self._close_progress_dialog()
        messagebox.showerror("Erro no upload", f"Falha no envio:\n\n{err}")

    # ---------- Fluxo principal ----------
    def upload_archive_to_auditoria(self) -> None:
        """Upload de arquivo .zip, .rar ou .7z para Auditoria preservando subpastas."""
        if not self.controller.is_online():
            messagebox.showwarning("Nuvem", "Sem conexão com o Supabase.")
            return

        # 1) Garantir auditoria selecionada
        sel = self.frame.tree.selection()
        if not sel:
            messagebox.showwarning("Atenção", "Selecione uma auditoria na lista.")
            return

        iid = sel[0]
        row = self.frame._aud_index.get(iid)
        if not row:
            messagebox.showwarning("Atenção", "Nenhuma auditoria válida selecionada.")
            return

        # Cache org_id se necessário
        if not self.frame._org_id:
            try:
                self.frame._org_id = self.controller.get_current_org_id()
            except AuditoriaServiceError as exc:
                messagebox.showwarning("Auditoria", f"Não foi possível identificar a organização do usuário.\n{exc}")
                return

        org_id = self.frame._org_id
        client_id = row["cliente_id"]
        cliente_nome = row["cliente_nome"]
        cnpj = row.get("cnpj", "")

        # 2) Escolher arquivo .zip, .rar ou .7z
        path = select_archive_file(title="Selecione arquivo .ZIP, .RAR ou .7Z (volumes: selecione .7z.001)")
        if not path:
            return

        # Validar extensão usando função centralizada
        if not self.controller.is_supported_archive(path):
            messagebox.showwarning(
                "Arquivo não suportado",
                "Formato não suportado. Selecione um arquivo .zip, .rar ou .7z.\n"
                "Para volumes, selecione o arquivo .7z.001.\n"
                f"Arquivo selecionado: {Path(path).name}",
            )
            return

        # 3) Mostrar modal de progresso
        self._open_progress_dialog("Processando arquivos", f"Enviando {Path(path).name}...")

        # 4) Lançar thread worker
        threading.Thread(
            target=self.worker_upload,
            args=(path, client_id, org_id, cliente_nome, cnpj),
            daemon=True,
        ).start()

    def worker_upload(self, archive_path: str, client_id: int, org_id: str, cliente_nome: str, cnpj: str) -> None:
        """Executa upload delegando processamento pesado ao service."""
        try:
            context = self.controller.prepare_upload_context(client_id, org_id=org_id)
            self.frame._org_id = context.org_id
        except AuditoriaServiceError as exc:
            self.frame.after(0, lambda err=str(exc): self._busy_fail(err))
            return

        plan = None
        try:
            plan = self.controller.prepare_archive_plan(archive_path)
        except (AuditoriaServiceError, ArchiveError) as exc:
            self.frame.after(0, lambda err=str(exc): self._busy_fail(err))
            return

        try:
            try:
                existing_names = self.controller.list_existing_names_for_context(context)
            except AuditoriaServiceError:
                existing_names = set()

            duplicates_names = self.controller.detect_duplicate_file_names(plan, existing_names)
            strategy = "skip"

            if duplicates_names:
                dialog_result: dict[str, Any] = {"strategy": None}

                def _show_dup_dialog() -> None:
                    dlg = DuplicatesDialog(self.frame, len(duplicates_names), sorted(duplicates_names))
                    self.frame.wait_window(dlg)
                    dialog_result["strategy"] = dlg.strategy

                self.frame.after(0, _show_dup_dialog)

                while dialog_result["strategy"] is None:
                    time.sleep(0.05)
                    if self._cancel_flag:
                        self.controller.cleanup_archive_plan(plan)
                        return

                strategy_value = dialog_result["strategy"]
                if strategy_value is None:
                    self.frame.after(0, lambda: self._busy_fail("Upload cancelado pelo usuário"))
                    return
                strategy = strategy_value or "skip"

            state = ProgressState()
            state.start_ts = time.monotonic()

            result = self.controller.execute_archive_upload(
                plan,
                context,
                strategy=strategy,
                existing_names=existing_names,
                duplicates=duplicates_names,
                cancel_check=lambda: self._cancel_flag,
                progress_callback=lambda prog: self._handle_upload_progress(state, prog),
            )
        except AuditoriaServiceError as exc:
            self.frame.after(0, lambda err=str(exc): self._busy_fail(err))
            return
        except Exception as exc:
            self.frame.after(0, lambda err=str(exc): self._busy_fail(err))
            return
        finally:
            self.controller.cleanup_archive_plan(plan)

        if result.cancelled or self._cancel_flag:

            def _show_cancel_summary() -> None:
                msg = (
                    "Upload cancelado.\n\n"
                    f"{result.done_files} arquivo(s) enviado(s)\n"
                    f"{result.skipped_duplicates} pulado(s) (duplicatas)\n"
                    f"{len(result.failed)} falha(s)"
                )
                messagebox.showinfo("Upload Cancelado", msg)
                self._close_progress_dialog()

            self.frame.after(0, _show_cancel_summary)
            return

        self.frame.after(
            0,
            lambda: self._busy_done(
                result.done_files,
                result.failed,
                context.base_prefix,
                cliente_nome,
                cnpj,
                client_id,
                context.org_id,
            ),
        )
