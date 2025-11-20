"""Ações de storage (subpastas, exclusão) para a tela de Auditoria."""

from __future__ import annotations

from tkinter import messagebox
from typing import TYPE_CHECKING

from src.modules.auditoria.service import AuditoriaServiceError
from ..application import AuditoriaApplication

if TYPE_CHECKING:  # pragma: no cover
    from .main_frame import AuditoriaFrame

try:
    from src.modules.uploads import open_files_browser  # type: ignore[import-untyped]
except Exception:
    open_files_browser = None  # Fallback defensivo


class AuditoriaStorageActions:
    def __init__(self, frame: "AuditoriaFrame", controller: AuditoriaApplication):  # type: ignore[name-defined]
        self.frame = frame
        self.controller = controller

    # ---------- Subpastas ----------
    def open_subpastas(self) -> None:
        """
        Abre janela de arquivos da auditoria selecionada.
        Garante apenas 1 janela por auditoria (foca se já existe).
        """
        supabase_client = self.controller.get_supabase_client()
        if not supabase_client:
            messagebox.showwarning("Storage", "Sem conexão com a nuvem.")
            return

        sel = self.frame.tree.selection()
        if not sel:
            messagebox.showinfo("Atenção", "Selecione uma auditoria na lista.")
            return

        iid = sel[0]
        row = self.frame._aud_index.get(iid)
        if not row:
            messagebox.showwarning("Atenção", "Nenhuma auditoria válida selecionada.")
            return

        # Usa iid diretamente como chave (já é string)
        aud_key = iid

        # Se já existe janela para esta auditoria, traz para frente
        win = self.frame._open_browsers.get(aud_key)
        if win and win.winfo_exists():
            try:
                win.lift()
                win.attributes("-topmost", True)
                win.after(150, lambda: win.attributes("-topmost", False))
                win.focus_force()
            except Exception:
                pass
            return

        try:
            if not self.frame._org_id:
                self.frame._org_id = self.controller.get_current_org_id()

            client_id = row["cliente_id"]
            storage_ctx = self.controller.get_storage_context(client_id, org_id=self.frame._org_id)
            self.frame._org_id = storage_ctx.org_id
            prefix = storage_ctx.auditoria_prefix
            delete_handler = self.controller.make_delete_folder_handler(storage_ctx.auditoria_prefix)

            if open_files_browser:
                browser_win = open_files_browser(
                    self.frame,
                    supabase=supabase_client,
                    client_id=client_id,
                    org_id=storage_ctx.org_id,
                    razao=row["cliente_nome"],
                    cnpj=row["cnpj"],
                    bucket=storage_ctx.bucket,
                    base_prefix=storage_ctx.client_root,
                    start_prefix=prefix,
                    module="auditoria",
                    modal=True,
                    delete_folder_handler=delete_handler,
                )
            else:
                browser_win = None

            if browser_win:
                self.frame._open_browsers[aud_key] = browser_win

                def _on_close() -> None:
                    self.frame._open_browsers.pop(aud_key, None)
                    browser_win.destroy()

                browser_win.protocol("WM_DELETE_WINDOW", _on_close)
        except Exception as e:
            messagebox.showwarning("Storage", f"Falhou ao abrir subpastas.\n{e}")

    def create_auditoria_folder(self) -> None:
        """Cria a pasta 'GERAL/Auditoria' no Storage do cliente."""
        if not self.controller.is_online():
            messagebox.showwarning("Criar pasta", "Sem conexão com a nuvem.")
            return
        cid = self.frame._selected_client_id()
        if cid is None:
            messagebox.showinfo("Criar pasta", "Selecione um cliente.")
            return

        try:
            self.controller.ensure_auditoria_folder(int(cid))
            messagebox.showinfo("Criar pasta", "Pasta 'GERAL/Auditoria' criada com sucesso.")
        except (AuditoriaServiceError, ValueError) as exc:
            messagebox.showwarning("Criar pasta", f"Falhou ao criar pasta.\n{exc}")

    def delete_auditorias(self) -> None:
        """Exclui as auditorias selecionadas da tabela (não remove arquivos do Storage)."""
        sels = list(self.frame.tree.selection())
        if not sels:
            messagebox.showwarning("Atenção", "Selecione uma ou mais auditorias para excluir.")
            return

        if not self.controller.is_online():
            messagebox.showwarning("Auditoria", "Sem conexão com o banco de dados.")
            return

        # Extrai db_ids usando list comprehension
        ids = [self.frame._aud_index[i]["db_id"] for i in sels if i in self.frame._aud_index]

        if not ids:
            messagebox.showwarning("Atenção", "Nenhuma auditoria válida selecionada.")
            return

        # Coleta nomes para confirmação
        nomes = [self.frame._aud_index[i]["cliente_nome"] for i in sels if i in self.frame._aud_index]
        lista_nomes = "\n".join(nomes[:5]) + ("..." if len(nomes) > 5 else "")

        if not messagebox.askyesno("Confirmar exclusão", f"Excluir {len(ids)} auditoria(s)?\n\n{lista_nomes}", parent=self.frame):
            return

        try:
            self.controller.delete_auditorias(ids)
        except AuditoriaServiceError as exc:
            messagebox.showerror("Erro", f"Falha ao excluir: {exc}", parent=self.frame)
            return

        # Atualiza UI local (remoção otimista)
        for iid in sels:
            self.frame.tree.delete(iid)
            self.frame._aud_index.pop(iid, None)

        # Desabilita botões
        self.frame._btn_h_ver.configure(state="disabled")
        self.frame._btn_h_delete.configure(state="disabled")

        messagebox.showinfo("Pronto", f"{len(ids)} auditoria(s) excluída(s).", parent=self.frame)
