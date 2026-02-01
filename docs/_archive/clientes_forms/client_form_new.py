# -*- coding: utf-8 -*-
"""Facade para formulário de cliente.

Este arquivo mantém compatibilidade com código existente, delegando toda a
lógica para os componentes separados (View, Controller, State, Actions).

Refatoração: MICROFASE-11 (Divisão em 4 componentes - Facade)
Microfase: 6 (Subdialogs CustomTkinter)
"""

from __future__ import annotations

import logging
import tkinter as tk
from typing import Any

# MF-11: Imports movidos para o topo do arquivo (Ruff E402)
from src.ui.window_utils import center_on_parent as center_on_parent
from src.modules.clientes.components.status import apply_status_prefix as apply_status_prefix
from src.modules.clientes.core.service import (
    salvar_cliente_a_partir_do_form as salvar_cliente_a_partir_do_form,
    checar_duplicatas_para_form as checar_duplicatas_para_form,
)
from src.modules.forms.actions import preencher_via_pasta as preencher_via_pasta

from .client_form_view import ClientFormView
from .client_form_state import ClientFormState, extract_address_fields
from .client_form_controller import ClientFormController
from .client_form_actions import perform_save, ClientFormContext, ClientFormDeps
from .client_form_adapters import (
    TkMessageAdapter,
    FormDataAdapter,
    TkClientPersistence,
    TkUploadExecutor,
)
from .client_form_cnpj_actions import CnpjActionDeps, handle_cartao_cnpj_action
from . import client_form_upload_actions

# CustomTkinter: fonte única centralizada (Microfase 23 - SSoT)
from src.ui.ctk_config import HAS_CUSTOMTKINTER

# Importação condicional de modal CTk
if HAS_CUSTOMTKINTER:
    from src.modules.clientes.ui import ClientesModalCTK
else:
    ClientesModalCTK = None  # type: ignore[misc,assignment]

logger = logging.getLogger(__name__)


# Tipos para compatibilidade
ClientRow = tuple[Any, ...]
FormPreset = dict[str, str]


# =============================================================================
# Facade Principal
# =============================================================================


def form_cliente(
    self: tk.Misc,
    row: ClientRow | None = None,
    preset: FormPreset | None = None,
) -> None:
    """Abre formulário de cliente (facade).

    Mantém assinatura e comportamento idênticos ao código original,
    mas delega toda a lógica para componentes separados.

    Args:
        self: Widget pai (geralmente MainWindow).
        row: Row do cliente para editar (None para novo).
        preset: Valores pré-preenchidos para novo cliente (None se não houver).
    """
    # -------------------------------------------------------------------------
    # 1. Criar Estado
    # -------------------------------------------------------------------------

    state = ClientFormState()

    # Carregar dados de row ou preset
    if row:
        state.load_from_row(row)
    elif preset:
        state.load_from_preset(preset)

    # Extrair campos de endereço do self (se disponível)
    try:
        cliente_like = None
        for attr_name in ("_cliente_atual", "cliente_atual", "cliente"):
            cliente_like = getattr(self, attr_name, None)
            if cliente_like is not None:
                break

        if cliente_like:
            addr_fields = extract_address_fields(cliente_like)
            state.data.endereco = addr_fields.get("endereco", "")
            state.data.bairro = addr_fields.get("bairro", "")
            state.data.cidade = addr_fields.get("cidade", "")
            state.data.cep = addr_fields.get("cep", "")
    except Exception as exc:  # noqa: BLE001
        logger.debug(f"Falha ao extrair campos de endereço: {exc}")

    # -------------------------------------------------------------------------
    # 2. Criar View e Handlers
    # -------------------------------------------------------------------------

    # Referências mutáveis para closures
    view_ref: list[ClientFormView | None] = [None]
    controller_ref: list[ClientFormController | None] = [None]
    row_ref: list[ClientRow | None] = [row]
    cnpj_busy: list[bool] = [False]

    class Handlers:
        """Implementação dos handlers de eventos do formulário."""

        def on_save(self) -> None:
            """Handler para botão Salvar."""
            controller = controller_ref[0]
            if controller:
                controller.handle_save(
                    show_success=True,
                    close_form=True,
                    refresh_list=True,
                )

        def on_save_and_upload(self) -> None:
            """Handler para botão Salvar e Enviar."""
            controller = controller_ref[0]
            if controller:
                result = controller.handle_save_and_upload()
                if not result.success and result.message:
                    logger.warning(f"Falha no upload: {result.message}")

        def on_cartao_cnpj(self) -> None:
            """Handler para botão Cartão CNPJ com tratamento robusto de erros."""
            from tkinter import messagebox

            if cnpj_busy[0]:
                return

            cnpj_busy[0] = True
            controller = controller_ref[0]
            view = view_ref[0]

            if controller:
                controller.set_cartao_cnpj_button_enabled(False)

            try:
                if not view or not view.window:
                    return

                # Criar adaptadores
                from .client_form_adapters import (
                    TkMessageSink,
                    TkFormFieldSetter,
                    TkDirectorySelector,
                )

                deps = CnpjActionDeps(
                    messages=TkMessageSink(parent=view.window),
                    field_setter=TkFormFieldSetter(ents=view.ents),
                    directory_selector=TkDirectorySelector(parent=view.window),
                )

                result = handle_cartao_cnpj_action(deps)

                # Marca formulário como modificado se houve sucesso
                if result.ok and controller:
                    controller.mark_dirty()

            except Exception as exc:
                logger.exception("Erro ao processar Cartão CNPJ")
                if view and view.window:
                    # Usa modal CTk se disponível
                    if HAS_CUSTOMTKINTER and ClientesModalCTK is not None:
                        ClientesModalCTK.error(
                            view.window,
                            "Erro",
                            f"Falha ao processar Cartão CNPJ:\n{exc}",
                        )
                    else:
                        from tkinter import messagebox

                        messagebox.showerror(
                            "Erro",
                            f"Falha ao processar Cartão CNPJ:\n{exc}",
                            parent=view.window,
                        )

            finally:
                cnpj_busy[0] = False
                if controller:
                    controller.set_cartao_cnpj_button_enabled(True)

        def on_cancel(self) -> None:
            """Handler para botão Cancelar (e fechar janela)."""
            view = view_ref[0]
            if view and view.window:
                # Unregister do host
                try:
                    if hasattr(self, "unregister_edit_form"):
                        self.unregister_edit_form(view.window)
                except Exception as exc:  # noqa: BLE001
                    logger.debug(f"Falha ao cancelar registro do form_cliente: {exc}")

                view.close()

        def on_senhas(self) -> None:
            """Handler para botão Senhas."""
            from src.modules.passwords.helpers import open_senhas_for_cliente

            view = view_ref[0]
            if not view or not view.window:
                return

            cid = state.client_id
            if not cid:
                # Usa modal CTk se disponível
                if HAS_CUSTOMTKINTER and ClientesModalCTK is not None:
                    ClientesModalCTK.info(
                        view.window,
                        "Senhas do Cliente",
                        "Salve o cliente antes de abrir as senhas.",
                    )
                else:
                    from tkinter import messagebox

                    messagebox.showinfo(
                        "Senhas do Cliente",
                        "Salve o cliente antes de abrir as senhas.",
                        parent=view.window,
                    )
                return

            try:
                razao_text = view.get_field_value("Razão Social")
                open_senhas_for_cliente(view.window, str(cid), razao_social=razao_text)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Falha ao abrir senhas do cliente: %s", exc)
                # Usa modal CTk se disponível
                if HAS_CUSTOMTKINTER and ClientesModalCTK is not None:
                    ClientesModalCTK.error(
                        view.window,
                        "Erro",
                        f"Falha ao abrir senhas: {exc}",
                    )
                else:
                    from tkinter import messagebox

                    messagebox.showerror(
                        "Erro",
                        f"Falha ao abrir senhas: {exc}",
                        parent=view.window,
                    )

        def on_dirty(self, *args: Any) -> None:
            """Handler para marcação de dirty state."""
            controller = controller_ref[0]
            if controller:
                controller.mark_dirty()

    handlers = Handlers()
    view = ClientFormView(parent=self, handlers=handlers)
    view_ref[0] = view

    # -------------------------------------------------------------------------
    # 3. Criar Serviços para Controller
    # -------------------------------------------------------------------------

    def _perform_save(
        *,
        show_success: bool,
        close_window: bool,
        refresh_list: bool = True,
        update_row: bool = True,
    ) -> bool:
        """Serviço de salvamento (usado pelo controller)."""
        nonlocal row_ref

        if not view or not view.window:
            return False

        # Criar adaptadores para o módulo headless
        msg_adapter = TkMessageAdapter(parent=view.window)
        data_adapter = FormDataAdapter(view.ents, view.status_var or tk.StringVar())

        # Montar contexto
        ctx = ClientFormContext(
            is_new=(state.client_id is None),
            client_id=state.client_id,
            row=row_ref[0],
            duplicate_check_exclude_id=state.client_id,
        )

        # Montar dependências
        deps = ClientFormDeps(
            messages=msg_adapter,
            data_collector=data_adapter,
            parent_window=view.window,
        )

        # Delegar ao módulo headless
        ctx = perform_save(ctx, deps, show_success=show_success)

        # Processar resultado
        if ctx.abort:
            return False

        # Atualizar estado local
        if ctx.saved_id:
            state.update_client_id(ctx.saved_id)
            state.mark_clean()

            if update_row:
                if row_ref[0]:
                    row_ref[0] = (ctx.saved_id,) + tuple(row_ref[0][1:])
                else:
                    row_ref[0] = (ctx.saved_id,)

        # Refresh de lista
        if refresh_list:
            try:
                self.carregar()
            except Exception as exc:  # noqa: BLE001
                logger.debug(f"Falha ao recarregar lista após salvar cliente: {exc}")

        # Fechar janela
        if close_window:
            try:
                if hasattr(self, "unregister_edit_form"):
                    self.unregister_edit_form(view.window)
            except Exception as exc:  # noqa: BLE001
                logger.debug(f"Falha ao remover form_cliente do host: {exc}")
            view.close()

        return True

    def _upload_flow_service() -> tuple[bool, bool, str | None]:
        """Serviço de upload (usado pelo controller)."""
        if not view or not view.window:
            return (False, False, "View não disponível")

        try:
            # Callback para atualizar row nonlocal
            def _update_row_callback(client_id: int) -> None:
                nonlocal row_ref
                row_ref[0] = (client_id,)

            # Adaptador para persistir cliente antes do upload
            persistence = TkClientPersistence(
                state=state,  # type: ignore[arg-type]
                on_persist_client=lambda: _perform_save(
                    show_success=False,
                    close_window=False,
                    refresh_list=False,
                    update_row=False,
                ),
                on_update_row=_update_row_callback,
            )

            # Adaptador para executar upload
            uploader = TkUploadExecutor(state=state)  # type: ignore[arg-type]

            # Preparar contexto de upload
            upload_ctx = client_form_upload_actions.prepare_upload_context(
                client_id=state.client_id,
                row=row_ref[0],
                ents=view.ents,
                win=view.window,
                arquivos_selecionados=None,
            )

            # Preparar dependências
            upload_deps = client_form_upload_actions.UploadDeps(
                executor=uploader,
                persistence=persistence,
                host=self,
            )

            # Executar fluxo de salvar e enviar
            upload_ctx = client_form_upload_actions.execute_salvar_e_enviar(upload_ctx, upload_deps)

            # Processar resultado
            if upload_ctx.abort:
                logger.warning(f"Upload abortado: {upload_ctx.error_message or 'Razão desconhecida'}")
                return (False, False, upload_ctx.error_message)

            # Atualizar estado local se cliente foi criado
            newly_created = False
            if upload_ctx.newly_created and upload_ctx.client_id:
                state.update_client_id(upload_ctx.client_id)
                newly_created = True
                if row_ref[0] is None or len(row_ref[0]) == 0:
                    row_ref[0] = (upload_ctx.client_id,)

            return (True, newly_created, None)

        except Exception as exc:
            logger.exception("Erro em upload flow service")
            return (False, False, str(exc))

    # -------------------------------------------------------------------------
    # 4. Criar Controller
    # -------------------------------------------------------------------------

    # Callback para save_silent
    def _save_silent() -> bool:
        return _perform_save(
            show_success=False,
            close_window=False,
            refresh_list=True,
            update_row=True,
        )

    state._on_save_silent = _save_silent

    controller = ClientFormController(
        state=state,
        save_service=_perform_save,
        upload_flow_service=_upload_flow_service,
        view=view,
    )
    controller_ref[0] = controller

    # -------------------------------------------------------------------------
    # 5. Construir UI
    # -------------------------------------------------------------------------

    view.build_ui()

    # Preencher campos com dados do estado
    view.fill_fields(state.data.to_dict())

    # Configurar status
    if view.status_var and state.data.status:
        view.status_var.set(state.data.status)

    # Registrar form no host
    if hasattr(self, "register_edit_form"):
        try:
            # Criar EditFormState para compatibilidade
            from .client_form_adapters import EditFormState

            edit_state = EditFormState(
                client_id=state.client_id,
                on_save_silent=_save_silent,
                initializing_flag=[state.initializing],
            )
            self.register_edit_form(view.window, edit_state)
        except Exception as exc:  # noqa: BLE001
            logger.debug(f"Falha ao registrar form_cliente no host: {exc}")

    # -------------------------------------------------------------------------
    # 6. Finalizar e Exibir
    # -------------------------------------------------------------------------

    # Habilitar botão de upload
    controller.set_upload_button_enabled(True)

    # Finalizar inicialização (habilita dirty tracking)
    state.finish_initialization()

    # Atualizar título
    controller.update_title()

    # Exibir janela
    view.show()

    logger.debug("[form_cliente] Formulário exibido com sucesso")
