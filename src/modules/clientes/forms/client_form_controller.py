# -*- coding: utf-8 -*-
"""Controller headless para orquestração do formulário de clientes.

Este módulo implementa o controller que orquestra o fluxo de negócio do
formulário de clientes (salvar, upload, etc.), separado da UI.

Refatoração: UI-DECOUPLE-CLIENT-FORM-003 (Fase 3)
Refatoração: MICROFASE-11 (Divisão em 4 componentes - Controller expandido)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Protocol

from .client_form_state import ClientFormState, build_window_title

logger = logging.getLogger(__name__)


# =============================================================================
# Estado do Formulário
# =============================================================================


@dataclass
class FormState:
    """Estado do formulário de edição de cliente.

    Gerencia estado interno do formulário: se é novo, se foi modificado,
    qual o ID do cliente, etc. Separado da UI para facilitar testes.
    """

    client_id: int | None
    """ID do cliente (None se novo)."""

    is_new: bool
    """Indica se é um novo cliente."""

    is_dirty: bool
    """Indica se o formulário foi modificado."""

    row: tuple[Any, ...] | None = None
    """Dados originais da linha do cliente."""

    def mark_dirty(self) -> None:
        """Marca formulário como modificado."""
        self.is_dirty = True

    def mark_clean(self) -> None:
        """Marca formulário como não modificado."""
        self.is_dirty = False

    def update_client_id(self, client_id: int | None) -> None:
        """Atualiza o ID do cliente e recalcula is_new."""
        self.client_id = client_id
        self.is_new = client_id is None


# =============================================================================
# Resultados de Operações
# =============================================================================


@dataclass
class SaveResult:
    """Resultado de operação de salvamento."""

    success: bool
    """Indica se o salvamento foi bem-sucedido."""

    client_id: int | None
    """ID do cliente após salvar."""

    close_form: bool
    """Indica se o formulário deve ser fechado."""

    message: str | None = None
    """Mensagem opcional (erro ou sucesso)."""


@dataclass
class UploadResult:
    """Resultado de operação de upload."""

    success: bool
    """Indica se o upload foi bem-sucedido."""

    newly_created: bool = False
    """Indica se o cliente foi criado durante este fluxo."""

    message: str | None = None
    """Mensagem opcional (erro ou sucesso)."""


# =============================================================================
# Protocols de Serviços
# =============================================================================


class SaveService(Protocol):
    """Protocolo para serviço de salvamento de cliente."""

    def __call__(
        self,
        *,
        show_success: bool,
        close_window: bool,  # noqa: ARG002 - Protocol signature
        refresh_list: bool,
        update_row: bool,  # noqa: ARG002 - Protocol signature
    ) -> bool:
        """Salva cliente com opções de UI.

        Args:
            show_success: Se deve exibir mensagem de sucesso.
            close_window: Se deve fechar a janela após salvar.
            refresh_list: Se deve atualizar lista de clientes.
            update_row: Se deve atualizar row nonlocal.

        Returns:
            True se salvamento foi bem-sucedido.
        """
        ...


class UploadFlowService(Protocol):
    """Protocolo para serviço de fluxo de upload."""

    def __call__(self) -> tuple[bool, bool, str | None]:
        """Executa fluxo de salvar e enviar documentos.

        Returns:
            Tuple (success, newly_created, error_message).
        """
        ...


# =============================================================================
# Controller Principal
# =============================================================================


class ClientFormController:
    """Controller headless para orquestração do formulário de clientes.

    Este controller separa a lógica de negócio (quando salvar, quando fazer upload,
    etc.) da UI (Tkinter). Facilita testes e permite reutilização em contextos
    diferentes (ex.: CLI, API).

    Refatoração MICROFASE-11: Expandido para integrar View + State + Actions.
    """

    def __init__(
        self,
        state: ClientFormState,
        save_service: SaveService,
        upload_flow_service: UploadFlowService | None = None,
        view: Any | None = None,
    ) -> None:
        """Inicializa o controller.

        Args:
            state: Estado completo do formulário (ClientFormState).
            save_service: Serviço para salvar cliente.
            upload_flow_service: Serviço para fluxo de upload (opcional).
            view: View do formulário (ClientFormView, opcional).
        """
        self._state = state
        self._save_service = save_service
        self._upload_flow_service = upload_flow_service
        self._view = view

    @property
    def state(self) -> ClientFormState:
        """Retorna o estado atual do formulário."""
        return self._state

    @property
    def view(self) -> Any | None:
        """Retorna a view do formulário."""
        return self._view

    def set_view(self, view: Any) -> None:
        """Define a view do formulário após inicialização.

        Args:
            view: View do formulário (ClientFormView).
        """
        self._view = view
        logger.debug("[ClientFormController] View configurada")

    def handle_save(
        self,
        *,
        show_success: bool = True,
        close_form: bool = True,
        refresh_list: bool = True,
    ) -> SaveResult:
        """Orquestra o fluxo de salvar cliente.

        Args:
            show_success: Se deve exibir mensagem de sucesso.
            close_form: Se deve fechar o formulário após salvar.
            refresh_list: Se deve atualizar lista de clientes.

        Returns:
            SaveResult com resultado da operação.
        """
        logger.debug(
            f"[ClientFormController] handle_save (client_id={self._state.client_id}, "
            f"show_success={show_success}, close_form={close_form})"
        )

        success = self._save_service(
            show_success=show_success,
            close_window=close_form,
            refresh_list=refresh_list,
            update_row=True,
        )

        # Atualizar título se salvo com sucesso e view disponível
        if success and self._view and not close_form:
            self._update_view_title()

        return SaveResult(
            success=success,
            client_id=self._state.client_id,
            close_form=close_form and success,
            message=None,
        )

    def handle_save_and_upload(self) -> UploadResult:
        """Orquestra o fluxo de salvar cliente + upload de documentos.

        Returns:
            UploadResult com resultado da operação.
        """
        logger.debug(f"[ClientFormController] handle_save_and_upload (client_id={self._state.client_id})")

        if self._upload_flow_service is None:
            logger.warning("handle_save_and_upload chamado mas upload_flow_service não configurado")
            return UploadResult(
                success=False,
                message="Serviço de upload não disponível",
            )

        success, newly_created, error_message = self._upload_flow_service()

        # Atualizar título se view disponível
        if success and self._view:
            self._update_view_title()

        return UploadResult(
            success=success,
            newly_created=newly_created,
            message=error_message,
        )

    def handle_cancel(self) -> None:
        """Orquestra o cancelamento do formulário."""
        logger.debug(f"[ClientFormController] handle_cancel (client_id={self._state.client_id})")

        # TODO: Verificar dirty state e perguntar confirmação
        # Por ora, apenas fecha a view
        if self._view:
            self._view.close()

    def mark_dirty(self) -> None:
        """Marca o formulário como modificado."""
        self._state.mark_dirty()

    def mark_clean(self) -> None:
        """Marca o formulário como não modificado."""
        self._state.mark_clean()

    def _update_view_title(self) -> None:
        """Atualiza o título da view com base no estado atual."""
        if not self._view:
            return

        try:
            title = build_window_title(
                self._state,
                razao_social=self._state.data.razao_social,
                cnpj=self._state.data.cnpj,
            )
            self._view.update_title(title)
        except Exception as exc:  # noqa: BLE001
            logger.debug(f"Falha ao atualizar título da view: {exc}")

    def update_title(self) -> None:
        """Atualiza título da janela (método público para compatibilidade)."""
        self._update_view_title()

    def set_upload_button_enabled(self, enabled: bool) -> None:
        """Habilita/desabilita botão de upload via view.

        Args:
            enabled: True para habilitar, False para desabilitar.
        """
        if self._view:
            try:
                self._view.set_upload_button_enabled(enabled)
            except Exception as exc:  # noqa: BLE001
                logger.debug(f"Falha ao atualizar botão de upload: {exc}")

    def set_cartao_cnpj_button_enabled(self, enabled: bool) -> None:
        """Habilita/desabilita botão Cartão CNPJ via view.

        Args:
            enabled: True para habilitar, False para desabilitar.
        """
        if self._view:
            try:
                self._view.set_cartao_cnpj_button_enabled(enabled)
            except Exception as exc:  # noqa: BLE001
                logger.debug(f"Falha ao atualizar botão Cartão CNPJ: {exc}")
