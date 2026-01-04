"""Fluxo de upload para a tela de Auditoria (encapsulado em helper)."""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from tkinter import messagebox
from typing import TYPE_CHECKING, Any

from src.modules.auditoria.service import ArchiveError, AuditoriaServiceError, AuditoriaUploadResult
from src.modules.uploads.components.helpers import client_prefix_for_id
from src.modules.uploads.exceptions import UploadError
from src.modules.uploads.views import UploadDialog, UploadDialogContext, UploadDialogResult
from src.ui.dialogs.file_select import select_archive_file
from ..application import AuditoriaApplication
from .dialogs import DuplicatesDialog

logger = logging.getLogger(__name__)

if TYPE_CHECKING:  # pragma: no cover
    from .main_frame import AuditoriaFrame

try:
    from src.modules.uploads import open_files_browser  # type: ignore[import-untyped]
except Exception:
    open_files_browser = None  # fallback defensivo


class AuditoriaUploadFlow:
    def __init__(self, frame: "AuditoriaFrame", controller: AuditoriaApplication):  # type: ignore[name-defined]
        self.frame = frame
        self.controller = controller
        self._progress_dialog: Any | None = None
        self._cancel_flag = False

    def _close_progress_dialog(self) -> None:
        if getattr(self, "_progress_dialog", None):
            try:
                self._progress_dialog.close()  # type: ignore[union-attr]
            except Exception:
                logger.debug("Erro ao fechar progress dialog (provavelmente já fechado)", exc_info=True)
                pass
            self._progress_dialog = None

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

        msg = (
            f"Upload cancelado.\n\n{len(uploaded_paths)} arquivo(s) já foram enviados.\n\n"
            "Deseja remover esses arquivos?"
        )
        if messagebox.askyesno("Cancelar e Reverter", msg):
            # Lançar thread para remover arquivos
            def _do_rollback() -> None:
                try:
                    # Remover em lotes de 1000 (limite da API)
                    batch_size = 1000
                    for i in range(0, len(uploaded_paths), batch_size):
                        batch = uploaded_paths[i : i + batch_size]
                        self.controller.remove_storage_objects(bucket, batch)

                    self.frame.after(
                        0,
                        lambda: messagebox.showinfo(
                            "Revertido", f"{len(uploaded_paths)} arquivo(s) removido(s) com sucesso."
                        ),
                    )
                except AuditoriaServiceError as exc:
                    self.frame.after(
                        0,
                        lambda err=str(exc): messagebox.showerror(
                            "Erro ao Reverter", f"Falha ao remover arquivos:\n{err}"
                        ),
                    )

            threading.Thread(target=_do_rollback, daemon=True).start()
        else:
            messagebox.showinfo("Cancelado", "Upload cancelado. Arquivos já enviados foram mantidos.")

    def _busy_done(
        self,
        ok: int,
        fail: list[tuple[str, str]],
        base_prefix: str,
        cliente_nome: str,
        cnpj: str,
        client_id: int,
        org_id: str,
    ) -> None:
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

        # Usa implementação canônica de format_cnpj
        try:
            from src.utils.formatters import format_cnpj
        except Exception:
            # Fallback simplificado caso o import falhe
            def format_cnpj(raw: str) -> str:
                return str(raw)

        c_digits = "".join(filter(str.isdigit, cnpj or ""))
        cnpj_fmt = format_cnpj(c_digits) if c_digits else cnpj
        msg = f"Upload concluído para {cliente_nome} - {cnpj_fmt}.\n"
        msg += f"{ok} arquivo(s) enviado(s)."

        if fail:
            msg += f"\n\nFalhas: {len(fail)}"
            for path, err in fail[:3]:  # limita a 3 erros
                msg += f"\n- {Path(path).name}: {err}"
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
            except Exception:
                logger.exception("Falha ao abrir browser de arquivos após upload")

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
        self._cancel_flag = False

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

        # 3) Executar upload via dialog unificado
        def _upload_callable(ctx: UploadDialogContext) -> dict[str, Any]:
            ctx.report(
                label="Preparando envio...",
                detail=f"Validando {Path(path).name}",
                fraction=None,
            )

            try:
                context = self.controller.prepare_upload_context(client_id, org_id=org_id)
                self.frame._org_id = context.org_id
            except AuditoriaServiceError as exc:
                raise UploadError(str(exc)) from exc

            try:
                plan = self.controller.prepare_archive_plan(path)
            except (AuditoriaServiceError, ArchiveError) as exc:
                raise UploadError(str(exc)) from exc

            total_files = len(getattr(plan, "entries", []) or [])
            ctx.set_total(total_files or 1)

            try:
                existing_names = self.controller.list_existing_names_for_context(context)
            except AuditoriaServiceError:
                existing_names = set()

            try:
                duplicates_names = self.controller.detect_duplicate_file_names(plan, existing_names)
            except AuditoriaServiceError:
                duplicates_names = set()

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
                    if ctx.is_cancelled():
                        return {"context": context, "result": None, "cancelled": True}

                strategy_value = dialog_result["strategy"]
                if strategy_value is None:
                    raise UploadError("Upload cancelado pelo usuário.")
                strategy = strategy_value or "skip"

            def _handle_progress(prog: Any) -> None:
                fraction = 0.0
                if prog.total_bytes:
                    fraction = prog.done_bytes / prog.total_bytes
                elif prog.total_files:
                    fraction = prog.done_files / prog.total_files

                detail = (
                    f"{prog.done_files}/{prog.total_files} itens - "
                    f"{self._fmt_bytes(prog.done_bytes)}/{self._fmt_bytes(prog.total_bytes)}"
                )
                ctx.report(
                    label="Enviando arquivos...",
                    detail=detail,
                    completed=prog.done_files,
                    total=prog.total_files,
                    fraction=fraction,
                )

            try:
                result = self.controller.execute_archive_upload(
                    plan,
                    context,
                    strategy=strategy,
                    existing_names=existing_names,
                    duplicates=duplicates_names,
                    cancel_check=ctx.is_cancelled,
                    progress_callback=_handle_progress,
                )
            except AuditoriaServiceError as exc:
                raise UploadError(str(exc)) from exc

            return {"context": context, "result": result, "cancelled": False}

        def _on_upload_complete(outcome: UploadDialogResult) -> None:
            if outcome.error:
                self._busy_fail(outcome.error.message)
                return

            payload = outcome.result or {}
            result: AuditoriaUploadResult | None = payload.get("result")
            context = payload.get("context")

            if payload.get("cancelled") or (result and result.cancelled):
                if result and context:
                    self._ask_rollback(result.uploaded_paths, context.bucket)
                else:
                    messagebox.showinfo("Upload cancelado", "Upload cancelado pelo usuário.")
                return

            if not result or not context:
                self._busy_fail("Falha ao processar upload.")
                return

            self._busy_done(
                result.done_files,
                result.failed,
                context.base_prefix,
                cliente_nome,
                cnpj,
                client_id,
                context.org_id,
            )

        dialog = UploadDialog(
            self.frame,
            _upload_callable,
            title="Processando arquivos",
            message=f"Enviando {Path(path).name}...",
            total_items=None,
            on_complete=_on_upload_complete,
        )
        dialog.start()
