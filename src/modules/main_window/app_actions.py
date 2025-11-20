# -*- coding: utf-8 -*-
"""Helper para concentrar ações da App (clientes, lixeira, etc)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional
import logging

if TYPE_CHECKING:
    from src.modules.main_window.views.main_window import App


class AppActions:
    """Helper para concentrar ações da App (clientes, lixeira, etc).

    Nesta fase, a classe ainda não é usada; é só o esqueleto.
    """

    def __init__(self, app: "App", logger: Optional[logging.Logger] = None) -> None:
        self._app = app
        self._logger = logger or logging.getLogger(__name__)

    def novo_cliente(self) -> None:
        """Fluxo original de criação de novo cliente, movido da App."""
        from src import app_core

        app_core.novo_cliente(self._app)

    def editar_cliente(self) -> None:
        """Fluxo original de edição de cliente, movido da App."""
        from tkinter import messagebox
        from src import app_core

        values = self._app._selected_main_values()
        if not values:
            messagebox.showwarning("Atenção", "Selecione um cliente para editar.", parent=self._app)
            return
        try:
            pk = int(values[0])
        except Exception:
            messagebox.showerror("Erro", "ID inválido.", parent=self._app)
            return
        app_core.editar_cliente(self._app, pk)

    def _excluir_cliente(self) -> None:
        """Fluxo original de exclusão/movimento para lixeira, movido da App."""
        from tkinter import messagebox
        from src.modules.clientes import service as clientes_service
        from src.modules.lixeira import refresh_if_open as refresh_lixeira_if_open

        values = self._app._selected_main_values()
        if not values:
            # Nenhum cliente selecionado: ignora comando sem exibir popup.
            try:
                self._logger.info("Excluir cliente ignorado: nenhuma linha selecionada na lista principal.")
            except Exception:
                pass
            return

        try:
            client_id = int(values[0])
        except (TypeError, ValueError):
            messagebox.showerror("Erro", "Selecao invalida (ID ausente).", parent=self._app)
            self._logger.error("Invalid selected_values for exclusion: %s", values)
            return

        razao = ""
        if len(values) > 1:
            try:
                razao = (values[1] or "").strip()
            except Exception:
                razao = ""
        label_cli = f"{razao} (ID {client_id})" if razao else f"ID {client_id}"

        confirm = messagebox.askyesno(
            "Enviar para Lixeira",
            f"Deseja enviar o cliente {label_cli} para a Lixeira?",
            parent=self._app,
        )
        if confirm is False:
            return

        try:
            clientes_service.mover_cliente_para_lixeira(client_id)
        except Exception as exc:
            messagebox.showerror("Erro ao excluir", f"Falha ao enviar para a Lixeira: {exc}", parent=self._app)
            self._logger.exception("Failed to soft-delete client %s", label_cli)
            return

        try:
            self._app.carregar()
        except Exception:
            self._logger.exception("Failed to refresh client list after soft delete")

        try:
            refresh_lixeira_if_open()
        except Exception:
            self._logger.debug("Lixeira refresh skipped", exc_info=True)

        messagebox.showinfo("Lixeira", f"Cliente {label_cli} enviado para a Lixeira.", parent=self._app)
        self._logger.info("Cliente %s enviado para a Lixeira com sucesso", label_cli)

    def abrir_lixeira(self) -> None:
        """Fluxo original de abertura da UI de Lixeira, movido da App."""
        try:
            from src.ui.lixeira import abrir_lixeira as abrir_lixeira_ui
        except Exception:
            from src.modules.lixeira import abrir_lixeira as abrir_lixeira_ui

        abrir_lixeira_ui(self._app)

    def ver_subpastas(self) -> None:
        """Fluxo original de visualização de subpastas do cliente."""
        from tkinter import messagebox
        from src.modules.uploads import open_files_browser
        from src.modules.uploads.components.helpers import client_prefix_for_id, get_clients_bucket

        values = self._app._selected_main_values()
        if not values:
            messagebox.showwarning("Atenção", "Selecione um cliente primeiro.", parent=self._app)
            return
        try:
            client_id = int(values[0])
        except Exception:
            messagebox.showerror("Erro", "ID inválido.", parent=self._app)
            return
        razao = (values[1] or "").strip()
        cnpj = (values[2] or "").strip()

        u = self._app._get_user_cached()
        if not u:
            messagebox.showerror("Erro", "Usuário não autenticado.", parent=self._app)
            return
        org_id = self._app._get_org_id_cached(u["id"])
        if not org_id:
            messagebox.showerror("Erro", "Organização não encontrada para o usuário.", parent=self._app)
            return

        base_prefix = client_prefix_for_id(client_id, org_id)
        bucket = get_clients_bucket()

        open_files_browser(
            self._app,
            org_id=org_id,
            client_id=client_id,
            razao=razao,
            cnpj=cnpj,
            bucket=bucket,
            base_prefix=base_prefix,
            start_prefix=base_prefix,
            modal=True,
        )

    def enviar_para_supabase(self) -> None:
        """Fluxo original de envio de documentos para o Supabase, movido da App.

        Upload avançado para Supabase Storage.
        Permite escolher arquivos, múltiplos arquivos ou pasta inteira,
        com seleção de bucket/pasta de destino e barra de progresso.
        Inclui fallback quando list_buckets() não funciona (RLS).
        Upload padrão: cliente/GERAL
        """
        from tkinter import messagebox
        import os
        from uploader_supabase import send_to_supabase_interactive

        # Log de início do fluxo
        self._logger.info("CALL enviar_para_supabase (interativo)")

        try:
            # Obtém base do cliente (ORG_UID/CLIENT_ID)
            base = self._app.get_current_client_storage_prefix()

            # Log do prefix calculado
            if not base:
                self._logger.warning("enviar_para_supabase: nenhum cliente selecionado (base_prefix vazio)")
            else:
                self._logger.debug("enviar_para_supabase: base_prefix=%s", base)

            # Configuração de bucket e subprefix
            default_bucket = os.getenv("SUPABASE_BUCKET") or "rc-docs"
            default_subprefix = "GERAL"

            # Log antes de abrir o diálogo
            self._logger.info(
                "enviar_para_supabase: abrindo diálogo de upload (bucket=%s, base_prefix=%s, subprefix=%s)",
                default_bucket,
                base,
                default_subprefix,
            )

            # Chamada ao uploader interativo
            ok_count, failed_count = send_to_supabase_interactive(
                self._app,
                default_bucket=default_bucket,
                base_prefix=base,  # força cair dentro do cliente
                default_subprefix=default_subprefix,  # padrão: enviar para GERAL
            )

            # Log de conclusão com resultados
            if ok_count == 0 and failed_count == 0:
                self._logger.info("enviar_para_supabase: diálogo fechado sem uploads (cancelado ou nenhum arquivo selecionado)")
            else:
                self._logger.info(
                    "enviar_para_supabase: diálogo fechado (sucesso=%d, falhas=%d)",
                    ok_count,
                    failed_count,
                )

        except Exception as e:
            # Log de erro com stack trace completo
            self._logger.error("Erro ao enviar para Supabase (interativo): %s", e, exc_info=True)
            messagebox.showerror("Erro", f"Erro ao enviar para Supabase:\n{str(e)}", parent=self._app)
