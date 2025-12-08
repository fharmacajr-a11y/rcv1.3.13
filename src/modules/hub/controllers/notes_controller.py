# -*- coding: utf-8 -*-
"""Controller headless para ações da Central de Anotações.

Este controller encapsula toda a lógica de ações quando o usuário
interage com as notas (adicionar, editar, deletar, fixar, marcar como feita).

Segue o padrão MVVM:
- ViewModel (NotesViewModel): lógica de apresentação (formatação, ordenação)
- Controller (NotesController): lógica de ações de usuário
- View (HubScreen + panels): apenas layout e binding de eventos
"""

from __future__ import annotations

import logging
from typing import Any, Protocol, runtime_checkable

from src.modules.hub.viewmodels import NotesViewModel, NotesViewState

try:
    from src.core.logger import get_logger
except Exception:

    def get_logger(name: str = __name__):
        return logging.getLogger(name)


logger = get_logger(__name__)


@runtime_checkable
class NotesGatewayProtocol(Protocol):
    """Protocol para interação entre NotesController e a View.

    Define a interface mínima que o NotesController precisa
    para interagir com a UI sem depender de Tkinter diretamente.
    """

    def show_note_editor(self, note_data: dict[str, Any] | None = None) -> dict[str, Any] | None:
        """Mostra editor de nota (criar ou editar).

        Args:
            note_data: Dados da nota para editar (None para criar nova).

        Returns:
            Dados da nota editada/criada, ou None se cancelado.
        """
        ...

    def confirm_delete_note(self, note_data: dict[str, Any]) -> bool:
        """Confirma exclusão de nota.

        Args:
            note_data: Dados da nota a ser deletada.

        Returns:
            True se confirmado, False se cancelado.
        """
        ...

    def show_error(self, title: str, message: str) -> None:
        """Mostra mensagem de erro.

        Args:
            title: Título do erro.
            message: Mensagem de erro.
        """
        ...

    def show_info(self, title: str, message: str) -> None:
        """Mostra mensagem informativa.

        Args:
            title: Título.
            message: Mensagem.
        """
        ...

    def get_org_id(self) -> str | None:
        """Obtém ID da organização atual.

        Returns:
            org_id ou None se não disponível.
        """
        ...

    def get_user_email(self) -> str | None:
        """Obtém email do usuário atual.

        Returns:
            email ou None se não disponível.
        """
        ...

    def is_authenticated(self) -> bool:
        """Verifica se usuário está autenticado.

        Returns:
            True se autenticado, False caso contrário.
        """
        ...

    def is_online(self) -> bool:
        """Verifica se há conexão com internet.

        Returns:
            True se online, False caso contrário.
        """
        ...


class NotesController:
    """Controller headless para ações da Central de Anotações.

    Responsabilidades:
    - Receber eventos de ações do usuário (cliques, entrada de texto)
    - Validar pré-condições (autenticação, conexão)
    - Orquestrar chamadas ao ViewModel e ao service
    - Delegar interações UI para o gateway (dialogs, confirmações)

    Não tem dependências de Tkinter - é totalmente headless e testável.
    """

    def __init__(
        self,
        vm: NotesViewModel,
        gateway: NotesGatewayProtocol,
        notes_service: Any = None,  # Service de notas (injetável)
        logger: logging.Logger | None = None,
    ) -> None:
        """Inicializa o controller.

        Args:
            vm: NotesViewModel para gerenciar estado.
            gateway: Implementação do protocolo de gateway (UI).
            notes_service: Service de notas (para criar/editar/deletar).
            logger: Logger opcional (usa logger do módulo se não fornecido).
        """
        self._vm = vm
        self._gateway = gateway
        self._notes_service = notes_service
        self._logger = logger or globals()["logger"]

    def handle_add_note_click(self, note_text: str) -> tuple[bool, str]:
        """Handle de clique no botão 'Adicionar' nota.

        Args:
            note_text: Texto da nota digitada pelo usuário.

        Returns:
            Tuple (success: bool, message: str)
        """
        try:
            # Validar entrada
            text = note_text.strip()
            if not text:
                return (False, "Texto vazio")

            # Validar autenticação
            if not self._gateway.is_authenticated():
                self._gateway.show_error(
                    "Não autenticado",
                    "Você precisa estar autenticado para adicionar uma anotação.",
                )
                return (False, "Não autenticado")

            # Validar conexão
            if not self._gateway.is_online():
                self._gateway.show_error(
                    "Sem conexão",
                    "Não é possível adicionar anotações sem conexão com a internet.",
                )
                return (False, "Sem conexão")

            # Obter contexto
            org_id = self._gateway.get_org_id()
            user_email = self._gateway.get_user_email()

            if not org_id or not user_email:
                self._gateway.show_error(
                    "Erro",
                    "Não foi possível obter informações da organização ou usuário.",
                )
                return (False, "Contexto inválido")

            # Criar nota via service
            if self._notes_service:
                new_note = self._notes_service.create_note(
                    org_id=org_id,
                    author_email=user_email,
                    body=text,
                )

                # Atualizar estado do ViewModel
                self._vm.after_note_created(new_note)

            self._logger.debug("Nota adicionada com sucesso")
            return (True, "")

        except Exception as e:
            self._logger.exception("Erro ao adicionar nota")
            self._gateway.show_error(
                "Erro",
                f"Erro ao adicionar anotação: {e}",
            )
            return (False, str(e))

    def handle_edit_note_click(self, note_id: Any) -> tuple[bool, str]:
        """Handle de clique para editar nota existente.

        Args:
            note_id: ID da nota a ser editada.

        Returns:
            Tuple (success: bool, message: str)
        """
        try:
            # Encontrar nota no estado
            current_state = self._vm.state
            note_data = None
            for note in current_state.notes:
                if note.id == note_id:
                    note_data = {
                        "id": note.id,
                        "body": note.body,
                        "created_at": note.created_at,
                        "author_email": note.author_email,
                        "author_name": note.author_name,
                    }
                    break

            if not note_data:
                self._gateway.show_error("Erro", "Nota não encontrada.")
                return (False, "Nota não encontrada")

            # Mostrar editor
            updated_data = self._gateway.show_note_editor(note_data)
            if not updated_data:
                return (False, "Cancelado")

            # Atualizar via service
            if self._notes_service:
                updated_note = self._notes_service.update_note(
                    note_id=note_id,
                    body=updated_data.get("body", ""),
                )

                # Atualizar estado
                self._vm.after_note_updated(updated_note)

            return (True, "")

        except Exception as e:
            self._logger.exception("Erro ao editar nota")
            self._gateway.show_error("Erro", f"Erro ao editar nota: {e}")
            return (False, str(e))

    def handle_delete_note_click(self, note_id: Any) -> tuple[bool, str]:
        """Handle de clique para deletar nota.

        Args:
            note_id: ID da nota a ser deletada.

        Returns:
            Tuple (success: bool, message: str)
        """
        try:
            # Encontrar nota no estado
            current_state = self._vm.state
            note_data = None
            for note in current_state.notes:
                if note.id == note_id:
                    note_data = {
                        "id": note.id,
                        "body": note.body,
                    }
                    break

            if not note_data:
                self._gateway.show_error("Erro", "Nota não encontrada.")
                return (False, "Nota não encontrada")

            # Confirmar exclusão
            if not self._gateway.confirm_delete_note(note_data):
                return (False, "Cancelado")

            # Deletar via service
            if self._notes_service:
                self._notes_service.delete_note(note_id)

                # Atualizar estado
                self._vm.after_note_deleted(note_id)

            return (True, "")

        except Exception as e:
            self._logger.exception("Erro ao deletar nota")
            self._gateway.show_error("Erro", f"Erro ao deletar nota: {e}")
            return (False, str(e))

    def handle_toggle_pin(self, note_id: Any) -> tuple[bool, str]:
        """Handle para fixar/desfixar nota (futuro).

        Args:
            note_id: ID da nota.

        Returns:
            Tuple (success: bool, message: str)
        """
        # TODO: implementar quando necessário
        self._logger.debug("Toggle pin não implementado ainda")
        return (False, "Não implementado")

    def handle_toggle_done(self, note_id: Any) -> tuple[bool, str]:
        """Handle para marcar/desmarcar nota como feita (futuro).

        Args:
            note_id: ID da nota.

        Returns:
            Tuple (success: bool, message: str)
        """
        # TODO: implementar quando necessário
        self._logger.debug("Toggle done não implementado ainda")
        return (False, "Não implementado")

    def handle_load_notes(self, org_id: str, author_names_cache: dict[str, str] | None = None) -> NotesViewState:
        """Handle para carregar notas.

        Args:
            org_id: ID da organização.
            author_names_cache: Cache de nomes de autores.

        Returns:
            NotesViewState atualizado.
        """
        try:
            return self._vm.load(org_id, author_names_cache)
        except Exception as e:
            self._logger.exception("Erro ao carregar notas via controller")
            self._gateway.show_error("Erro", f"Erro ao carregar notas: {e}")
            return self._vm.state
