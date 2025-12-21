"""Mixin para handlers de eventos e menu de contexto."""

from __future__ import annotations

import logging
from tkinter import messagebox
from typing import Any

from ..utils.anvisa_errors import extract_postgrest_error, user_message_from_error, log_exception
from ..utils.anvisa_logging import fmt_ctx

log = logging.getLogger(__name__)


class AnvisaHandlersMixin:
    """Mixin com handlers, menu de contexto e ações de exclusão/finalização."""

    def _on_tree_select(self, event: Any) -> None:
        """Handler do evento de seleção na Treeview principal.

        Habilita/desabilita botão Excluir conforme seleção.
        """
        selection = self.tree_requests.selection()  # type: ignore[attr-defined]
        if selection:
            self._btn_excluir.configure(state="normal")  # type: ignore[attr-defined]
        else:
            self._btn_excluir.configure(state="disabled")  # type: ignore[attr-defined]

    def _on_tree_right_click(self, event: Any) -> None:
        """Handler do botão direito na Treeview principal.

        Exibe menu de contexto com opções.

        Args:
            event: Evento do Tkinter
        """
        # Identificar linha sob o mouse
        iid = self.tree_requests.identify_row(event.y)  # type: ignore[attr-defined]
        if not iid:
            return

        # Selecionar e focar linha ANTES de abrir menu
        self.tree_requests.selection_set(iid)  # type: ignore[attr-defined]
        self.tree_requests.focus(iid)  # type: ignore[attr-defined]

        # Extrair dados da linha
        item = self.tree_requests.item(iid)  # type: ignore[attr-defined]
        values = item["values"]

        if len(values) < 3:
            return

        # Salvar contexto (iid é o client_id)
        self._ctx_client_id = str(values[0])  # type: ignore[attr-defined]
        self._ctx_razao = str(values[1])  # type: ignore[attr-defined]
        self._ctx_cnpj = str(values[2])  # type: ignore[attr-defined]
        self._ctx_request_type = str(values[3]) if len(values) > 3 else ""  # type: ignore[attr-defined]
        self._ctx_request_id = None  # Não temos request_id específico no contexto  # type: ignore[attr-defined]

        # Mostrar menu de contexto
        try:
            self._main_ctx_menu.tk_popup(event.x_root, event.y_root)  # type: ignore[attr-defined]
        finally:
            self._main_ctx_menu.grab_release()  # type: ignore[attr-defined]

    def _ctx_open_history(self) -> None:
        """Abre histórico de demandas via menu de contexto."""
        if self._ctx_client_id and self._ctx_razao and self._ctx_cnpj:  # type: ignore[attr-defined]
            self._open_history_popup(  # type: ignore[attr-defined]
                self._ctx_client_id,  # type: ignore[attr-defined]
                self._ctx_razao,  # type: ignore[attr-defined]
                self._ctx_cnpj,  # type: ignore[attr-defined]
                center=True,
            )

    def _ctx_delete_request(self) -> None:
        """Exclui demanda via menu de contexto.

        Como a tabela principal agora mostra 1 linha por CLIENTE:
        - Se cliente tem 1 demanda: excluir direto
        - Se cliente tem 2+ demandas: abrir histórico e avisar
        """
        if not self._ctx_client_id:  # type: ignore[attr-defined]
            return

        client_id = self._ctx_client_id  # type: ignore[attr-defined]
        razao = self._ctx_razao or ""  # type: ignore[attr-defined]
        cnpj = self._ctx_cnpj or ""  # type: ignore[attr-defined]

        # Verificar quantas demandas esse cliente tem
        demandas = self._requests_by_client.get(client_id, [])  # type: ignore[attr-defined]

        if len(demandas) == 0:
            messagebox.showinfo("Aviso", "Cliente não possui demandas.")
            return

        if len(demandas) == 1:
            # Apenas 1 demanda: excluir direto
            request_id = str(demandas[0].get("id", ""))
            request_type = demandas[0].get("request_type", "")

            # Confirmar exclusão
            confirm = messagebox.askyesno(
                "Confirmar Exclusão",
                f"Tem certeza que deseja excluir a demanda?\n\n"
                f"Cliente: {razao}\n"
                f"Tipo: {request_type}\n\n"
                f"Esta ação não pode ser desfeita.",
                icon="warning",
            )

            if not confirm:
                return

            try:
                ctx = {"request_id": request_id, "client_id": client_id, "action": "delete"}
                log.debug(f"[ANVISA View] Excluindo demanda [{fmt_ctx(**ctx)}]")

                # Excluir via controller
                success = self._controller.delete_request(request_id)  # type: ignore[attr-defined]

                if success:
                    # Invalidar cache
                    self._demandas_cache.pop(client_id, None)  # type: ignore[attr-defined]
                    self._requests_by_client.pop(client_id, None)  # type: ignore[attr-defined]

                    # Recarregar lista principal
                    self._load_requests_from_cloud()  # type: ignore[attr-defined]

                    self.last_action.set(f"Demanda excluída: {request_type}")  # type: ignore[attr-defined]

                    # Desabilitar botão Excluir (nenhuma seleção agora)
                    self._btn_excluir.configure(state="disabled")  # type: ignore[attr-defined]
                else:
                    messagebox.showwarning(
                        "Aviso",
                        "Demanda não encontrada ou já foi excluída.",
                    )

            except Exception as exc:
                log_exception(log, "[ANVISA View] Erro ao excluir demanda", exc, **ctx)
                self.last_action.set("Erro ao excluir demanda")  # type: ignore[attr-defined]

                # Extrair erro e gerar mensagem amigável
                err_dict = extract_postgrest_error(exc)
                user_msg = user_message_from_error(
                    err_dict, default="Não foi possível excluir a demanda. Verifique os logs para mais detalhes."
                )

                messagebox.showerror(
                    "Erro ao Excluir",
                    user_msg,
                )
        else:
            # Cliente tem múltiplas demandas: abrir histórico
            messagebox.showinfo(
                "Múltiplas Demandas",
                f"Este cliente possui {len(demandas)} demandas.\n\n"
                f"Abrindo o histórico para selecionar qual demanda excluir.",
            )

            # Abrir popup de histórico
            self._open_history_popup(client_id, razao, cnpj, center=True)  # type: ignore[attr-defined]

    def _on_delete_request_clicked(self) -> None:
        """Handler do botão Excluir - remove demanda do Supabase.

        Como a tabela principal agora mostra 1 linha por CLIENTE:
        - Se cliente tem 1 demanda: excluir direto
        - Se cliente tem 2+ demandas: abrir histórico e avisar
        """
        selection = self.tree_requests.selection()  # type: ignore[attr-defined]
        if not selection:
            return

        client_id = selection[0]  # iid agora é client_id

        # Obter dados da linha para confirmação
        item = self.tree_requests.item(client_id)  # type: ignore[attr-defined]
        values = item["values"]
        razao = values[1] if len(values) > 1 else ""
        cnpj = values[2] if len(values) > 2 else ""

        # Verificar quantas demandas esse cliente tem
        demandas = self._requests_by_client.get(client_id, [])  # type: ignore[attr-defined]

        if len(demandas) == 0:
            messagebox.showinfo("Aviso", "Cliente não possui demandas.")
            return

        if len(demandas) == 1:
            # Apenas 1 demanda: excluir direto
            request_id = str(demandas[0].get("id", ""))
            request_type = demandas[0].get("request_type", "")

            # Confirmar exclusão
            confirm = messagebox.askyesno(
                "Confirmar Exclusão",
                f"Tem certeza que deseja excluir a demanda?\n\n"
                f"Cliente: {razao}\n"
                f"Tipo: {request_type}\n\n"
                f"Esta ação não pode ser desfeita.",
                icon="warning",
            )

            if not confirm:
                return

            try:
                ctx = {"request_id": request_id, "client_id": client_id, "action": "delete"}
                log.debug(f"[ANVISA View] Excluindo demanda [{fmt_ctx(**ctx)}]")

                # Excluir via controller (UUID string)
                success = self._controller.delete_request(request_id)  # type: ignore[attr-defined]

                if success:
                    # Invalidar cache
                    self._demandas_cache.pop(client_id, None)  # type: ignore[attr-defined]
                    self._requests_by_client.pop(client_id, None)  # type: ignore[attr-defined]

                    # Recarregar lista principal
                    self._load_requests_from_cloud()  # type: ignore[attr-defined]

                    self.last_action.set(f"Demanda excluída: {request_type}")  # type: ignore[attr-defined]

                    # Desabilitar botão Excluir (nenhuma seleção agora)
                    self._btn_excluir.configure(state="disabled")  # type: ignore[attr-defined]
                else:
                    messagebox.showwarning(
                        "Aviso",
                        "Demanda não encontrada ou já foi excluída.",
                    )

            except Exception as exc:
                log_exception(log, "[ANVISA View] Erro ao excluir demanda", exc, **ctx)
                self.last_action.set("Erro ao excluir demanda")  # type: ignore[attr-defined]

                # Extrair erro e gerar mensagem amigável
                err_dict = extract_postgrest_error(exc)
                user_msg = user_message_from_error(
                    err_dict, default="Não foi possível excluir a demanda. Verifique os logs para mais detalhes."
                )

                messagebox.showerror(
                    "Erro ao Excluir",
                    user_msg,
                )
        else:
            # Cliente tem múltiplas demandas: abrir histórico
            messagebox.showinfo(
                "Múltiplas Demandas",
                f"Este cliente possui {len(demandas)} demandas.\n\n"
                f"Abrindo o histórico para selecionar qual demanda excluir.",
            )

            # Abrir popup de histórico
            self._open_history_popup(client_id, razao, cnpj, center=True)  # type: ignore[attr-defined]

    def _finalizar_demanda(self, client_id: str) -> None:
        """Finaliza demanda selecionada no popup.

        Args:
            client_id: ID do cliente
        """
        if not self._history_tree_popup:  # type: ignore[attr-defined]
            return

        selection = self._history_tree_popup.selection()  # type: ignore[attr-defined]
        if not selection:
            return

        demanda_id = selection[0]

        # Obter dados da demanda
        item = self._history_tree_popup.item(demanda_id)  # type: ignore[attr-defined]
        values = item["values"]

        if not values or values[0] == "Sem demandas":
            return

        tipo = str(values[0])
        status = str(values[1])

        # Verificar se já está finalizada
        if status == "Finalizado":
            messagebox.showinfo(
                "Demanda Finalizada",
                "Esta demanda já está finalizada.",
            )
            return

        # Confirmar
        confirm = messagebox.askyesno(
            "Confirmar Finalização",
            f"Marcar esta demanda como Finalizada?\n\n"
            f"Tipo: {tipo}\n\n"
            f"Esta ação irá mudar o status para 'CONCLUIDA'.",
            icon="question",
        )

        if not confirm:
            return

        try:
            ctx = {"request_id": demanda_id, "client_id": client_id, "action": "close"}
            log.debug(f"[ANVISA View] Finalizando demanda [{fmt_ctx(**ctx)}]")

            # Finalizar via controller (status -> CONCLUIDA)
            success = self._controller.close_request(demanda_id)  # type: ignore[attr-defined]

            if success:
                # Invalidar caches
                self._demandas_cache.pop(client_id, None)  # type: ignore[attr-defined]
                self._requests_by_client.pop(client_id, None)  # type: ignore[attr-defined]

                # Recarregar histórico
                razao = self._ctx_razao or ""  # type: ignore[attr-defined]
                cnpj = self._ctx_cnpj or ""  # type: ignore[attr-defined]
                self._update_history_popup(client_id, razao, cnpj)  # type: ignore[attr-defined]

                # Recarregar lista principal (para atualizar "Ultima Alteração")
                self._load_requests_from_cloud()  # type: ignore[attr-defined]

                # Manter seleção no cliente
                try:
                    self.tree_requests.selection_set(client_id)  # type: ignore[attr-defined]
                    self.tree_requests.focus(client_id)  # type: ignore[attr-defined]
                    self.tree_requests.see(client_id)  # type: ignore[attr-defined]
                except Exception:
                    pass  # Ignorar se cliente não existir mais (todas demandas excluídas)

                self.last_action.set(f"Demanda finalizada: {tipo}")  # type: ignore[attr-defined]

                messagebox.showinfo(
                    "Sucesso",
                    "Demanda finalizada com sucesso!",
                )
            else:
                messagebox.showwarning(
                    "Aviso",
                    "Não foi possível finalizar a demanda.\n\n"
                    "Motivos comuns:\n"
                    "- Demanda não encontrada\n"
                    "- Permissão/RLS bloqueando atualização\n\n"
                    "Veja o log para detalhes.",
                )

        except Exception as exc:
            log_exception(log, "[ANVISA View] Erro ao finalizar demanda", exc, **ctx)
            self.last_action.set("Erro ao finalizar demanda")  # type: ignore[attr-defined]

            # Extrair erro e gerar mensagem amigável
            err_dict = extract_postgrest_error(exc)
            user_msg = user_message_from_error(
                err_dict, default="Não foi possível finalizar a demanda. Verifique os logs para mais detalhes."
            )

            messagebox.showerror(
                "Erro ao Finalizar",
                user_msg,
            )

    def _cancelar_demanda(self, client_id: str) -> None:
        """Cancela demanda selecionada no popup (status -> canceled).

        Args:
            client_id: ID do cliente
        """
        if not self._history_tree_popup:  # type: ignore[attr-defined]
            return

        selection = self._history_tree_popup.selection()  # type: ignore[attr-defined]
        if not selection:
            return

        demanda_id = selection[0]

        # Obter dados da demanda
        item = self._history_tree_popup.item(demanda_id)  # type: ignore[attr-defined]
        values = item["values"]

        if not values or values[0] == "Sem demandas":
            return

        tipo = str(values[0])
        status = str(values[1])

        # Verificar se já está finalizada
        if status == "Finalizado":
            messagebox.showinfo(
                "Demanda Finalizada",
                "Esta demanda já está finalizada.",
            )
            return

        # Confirmar
        confirm = messagebox.askyesno(
            "Confirmar Cancelamento",
            f"Cancelar esta demanda?\n\n" f"Tipo: {tipo}\n\n" f"Esta ação irá mudar o status para 'canceled'.",
            icon="question",
        )

        if not confirm:
            return

        try:
            ctx = {"request_id": demanda_id, "client_id": client_id, "action": "cancel"}
            log.debug(f"[ANVISA View] Cancelando demanda [{fmt_ctx(**ctx)}]")

            # Cancelar via controller (status -> canceled)
            success = self._controller.cancel_request(demanda_id)  # type: ignore[attr-defined]

            if success:
                # Invalidar caches
                self._demandas_cache.pop(client_id, None)  # type: ignore[attr-defined]
                self._requests_by_client.pop(client_id, None)  # type: ignore[attr-defined]

                # Recarregar histórico
                razao = self._ctx_razao or ""  # type: ignore[attr-defined]
                cnpj = self._ctx_cnpj or ""  # type: ignore[attr-defined]
                self._update_history_popup(client_id, razao, cnpj)  # type: ignore[attr-defined]

                # Recarregar lista principal (para atualizar "Ultima Alteração")
                self._load_requests_from_cloud()  # type: ignore[attr-defined]

                # Manter seleção no cliente
                try:
                    self.tree_requests.selection_set(client_id)  # type: ignore[attr-defined]
                    self.tree_requests.focus(client_id)  # type: ignore[attr-defined]
                    self.tree_requests.see(client_id)  # type: ignore[attr-defined]
                except Exception:
                    pass  # Ignorar se cliente não existir mais

                self.last_action.set(f"Demanda cancelada: {tipo}")  # type: ignore[attr-defined]

                messagebox.showinfo(
                    "Sucesso",
                    "Demanda cancelada com sucesso!",
                )
            else:
                messagebox.showwarning(
                    "Aviso",
                    "Não foi possível cancelar a demanda.\n\n"
                    "Motivos comuns:\n"
                    "- Demanda não encontrada\n"
                    "- Permissão/RLS bloqueando atualização\n\n"
                    "Veja o log para detalhes.",
                )

        except Exception as exc:
            log_exception(log, "[ANVISA View] Erro ao cancelar demanda", exc, **ctx)
            self.last_action.set("Erro ao cancelar demanda")  # type: ignore[attr-defined]

            # Extrair erro e gerar mensagem amigável
            err_dict = extract_postgrest_error(exc)
            user_msg = user_message_from_error(
                err_dict, default="Não foi possível cancelar a demanda. Verifique os logs para mais detalhes."
            )

            messagebox.showerror(
                "Erro ao Cancelar",
                user_msg,
            )

    def _excluir_demanda_popup(self, client_id: str) -> None:
        """Exclui demanda selecionada no popup.

        Args:
            client_id: ID do cliente
        """
        if not self._history_tree_popup:  # type: ignore[attr-defined]
            return

        selection = self._history_tree_popup.selection()  # type: ignore[attr-defined]
        if not selection:
            return

        demanda_id = selection[0]

        # Obter dados da demanda
        item = self._history_tree_popup.item(demanda_id)  # type: ignore[attr-defined]
        values = item["values"]

        if not values or values[0] == "Sem demandas":
            return

        tipo = str(values[0])

        # Confirmar exclusão
        confirm = messagebox.askyesno(
            "Confirmar Exclusão",
            f"Tem certeza que deseja excluir a demanda?\n\n" f"Tipo: {tipo}\n\n" f"Esta ação não pode ser desfeita.",
            icon="warning",
        )

        if not confirm:
            return

        try:
            ctx = {"request_id": demanda_id, "client_id": client_id, "action": "delete"}
            log.debug(f"[ANVISA View] Excluindo demanda [{fmt_ctx(**ctx)}]")

            # Excluir via controller (UUID string)
            success = self._controller.delete_request(demanda_id)  # type: ignore[attr-defined]

            if success:
                # Invalidar caches
                self._demandas_cache.pop(client_id, None)  # type: ignore[attr-defined]
                self._requests_by_client.pop(client_id, None)  # type: ignore[attr-defined]

                # Recarregar histórico
                razao = self._ctx_razao or ""  # type: ignore[attr-defined]
                cnpj = self._ctx_cnpj or ""  # type: ignore[attr-defined]
                self._update_history_popup(client_id, razao, cnpj)  # type: ignore[attr-defined]

                # Recarregar tabela principal (para atualizar contadores ou remover cliente)
                self._load_requests_from_cloud()  # type: ignore[attr-defined]

                # Tentar manter seleção no cliente (se ainda existir)
                try:
                    self.tree_requests.selection_set(client_id)  # type: ignore[attr-defined]
                    self.tree_requests.focus(client_id)  # type: ignore[attr-defined]
                except Exception:
                    pass  # Cliente foi removido (todas demandas excluídas)

                self.last_action.set(f"Demanda excluída: {tipo}")  # type: ignore[attr-defined]

                messagebox.showinfo(
                    "Sucesso",
                    "Demanda excluída com sucesso!",
                )
            else:
                messagebox.showwarning(
                    "Aviso",
                    "Demanda não encontrada ou já foi excluída.",
                )

        except Exception as exc:
            log_exception(log, "[ANVISA View] Erro ao excluir demanda", exc, **ctx)
            self.last_action.set("Erro ao excluir demanda")  # type: ignore[attr-defined]

            # Extrair erro e gerar mensagem amigável
            err_dict = extract_postgrest_error(exc)
            user_msg = user_message_from_error(
                err_dict, default="Não foi possível excluir a demanda. Verifique os logs para mais detalhes."
            )

            messagebox.showerror(
                "Erro ao Excluir",
                user_msg,
            )

    def _on_tree_double_click(self, event: Any) -> None:
        """Handler do double-click na Treeview - abre browser de arquivos.

        Args:
            event: Evento do Tkinter
        """
        selection = self.tree_requests.selection()  # type: ignore[attr-defined]
        if not selection:
            return

        request_id = selection[0]

        # Obter dados da linha
        item = self.tree_requests.item(request_id)  # type: ignore[attr-defined]
        values = item["values"]

        if len(values) < 4:
            log.warning("[ANVISA] Linha selecionada não tem dados suficientes")
            return

        client_id = values[0]
        razao = values[1]
        cnpj = values[2]
        request_type = values[3]

        log.info(f"[ANVISA] Double-click: client_id={client_id}, request_type={request_type}")

        # Abrir browser de arquivos com contexto ANVISA
        self._open_files_browser_anvisa_mode(  # type: ignore[attr-defined]
            client_id=int(client_id),
            razao=razao,
            cnpj=cnpj,
            request_type=request_type,
        )

    def _open_files_browser_anvisa_mode(
        self,
        client_id: int,
        razao: str,
        cnpj: str,
        request_type: str,
    ) -> None:
        """Abre browser de arquivos do cliente em modo ANVISA.

        Reutiliza janela existente se já estiver aberta para o mesmo cliente.

        Args:
            client_id: ID do cliente
            razao: Razão social
            cnpj: CNPJ
            request_type: Tipo de demanda ANVISA
        """
        client_id_str = str(client_id)

        # Verificar se já existe janela aberta para este cliente
        existing_win = self._anvisa_browser_windows.get(client_id_str)  # type: ignore[attr-defined]
        if existing_win is not None:
            try:
                if existing_win.winfo_exists():
                    # Janela existe: trazer para frente
                    existing_win.deiconify()
                    existing_win.lift()
                    existing_win.focus_force()
                    log.info(f"[ANVISA] Reutilizando janela existente para client_id={client_id}")
                    return
            except Exception:
                # Janela foi destruída: remover do dict
                self._anvisa_browser_windows.pop(client_id_str, None)  # type: ignore[attr-defined]

        try:
            from src.modules.uploads import open_files_browser
            from infra.supabase_client import supabase

            org_id = self._resolve_org_id()  # type: ignore[attr-defined]
            if not org_id:
                messagebox.showerror(
                    "Erro",
                    "Não foi possível obter organização do usuário.\n\nFaça login novamente.",
                )
                return

            log.info(f"[ANVISA] Abrindo browser para client_id={client_id}, processo={request_type}")

            # Callback de cleanup quando janela for fechada
            def on_browser_close():
                self._anvisa_browser_windows.pop(client_id_str, None)  # type: ignore[attr-defined]
                log.info(f"[ANVISA] Janela fechada para client_id={client_id}")

            # Abrir browser com contexto ANVISA
            browser_window = open_files_browser(
                self,  # type: ignore[arg-type]
                supabase=supabase,
                client_id=client_id,
                org_id=org_id,
                razao=razao,
                cnpj=cnpj,
                modal=False,
                anvisa_context={
                    "request_type": request_type,
                    "on_upload_complete": lambda: self._load_requests_from_cloud(),  # type: ignore[attr-defined]
                },
            )

            # Guardar referência da janela
            if browser_window is not None:
                self._anvisa_browser_windows[client_id_str] = browser_window  # type: ignore[attr-defined]

                # Configurar cleanup no close
                original_protocol = browser_window.protocol("WM_DELETE_WINDOW")

                def on_close_wrapper():
                    on_browser_close()
                    if callable(original_protocol):
                        original_protocol()
                    else:
                        browser_window.destroy()

                browser_window.protocol("WM_DELETE_WINDOW", on_close_wrapper)

            self.last_action.set(f"Arquivos abertos: {razao}")  # type: ignore[attr-defined]

        except Exception as e:
            log.exception("Erro ao abrir browser de arquivos")
            messagebox.showerror(
                "Erro",
                f"Não foi possível abrir arquivos do cliente.\n\nDetalhes: {e}",
            )
