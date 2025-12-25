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

    def reload_notes(self) -> None:
        """Força recarregamento das notas."""
        ...

    def reload_dashboard(self) -> None:
        """Força recarregamento do dashboard."""
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
        notifications_service: Any | None = None,  # Service de notificações (opcional)
        logger: logging.Logger | None = None,
    ) -> None:
        """Inicializa o controller.

        Args:
            vm: NotesViewModel para gerenciar estado.
            gateway: Implementação do protocolo de gateway (UI).
            notes_service: Service de notas (para criar/editar/deletar).
            notifications_service: Service de notificações (opcional).
            logger: Logger opcional (usa logger do módulo se não fornecido).
        """
        self._vm = vm
        self._gateway = gateway
        self._notes_service = notes_service
        self._notifications_service = notifications_service
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
            is_auth = self._gateway.is_authenticated()

            if not is_auth:
                self._gateway.show_error(
                    "Não autenticado",
                    "Você precisa estar autenticado para adicionar uma anotação.",
                )
                return (False, "Não autenticado")

            # Validar conexão
            is_onl = self._gateway.is_online()

            if not is_onl:
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

                # Forçar reload das notas para garantir que a UI seja atualizada
                self._gateway.reload_notes()

                # CRÍTICO: Dashboard também precisa ser atualizado (notas podem afetar dashboard)
                self._gateway.reload_dashboard()

                # Publicar notificação (falha não afeta criação da nota)
                try:
                    if self._notifications_service:
                        # Construir preview (máximo 120 chars)
                        preview = text.replace("\r", " ").replace("\n", " ").strip()
                        if len(preview) > 120:
                            preview = preview[:117] + "..."

                        # Resolver nome de exibição do autor usando RC_INITIALS_MAP
                        actor_name = self._notifications_service.resolve_display_name(user_email)

                        # Construir mensagem com nome (não email)
                        message = f"Anotações • {actor_name}: {preview}"

                        # Gerar request_id único para dedupe (baseado no ID da nota criada)
                        note_id = new_note.get("id") if isinstance(new_note, dict) else getattr(new_note, "id", None)
                        request_id = f"hub_notes_created:{note_id}" if note_id else None

                        # Publicar
                        self._notifications_service.publish(
                            module="hub_notes",
                            event="created",
                            message=message,
                            request_id=request_id,
                        )
                except Exception:
                    self._logger.exception("Falha ao publicar notificação de anotação (não fatal)")

            return (True, "")

        except Exception as e:
            self._logger.exception(f"NotesController.handle_add_note_click: EXCEÇÃO: {e}")
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

                # Forçar reload das notas
                self._gateway.reload_notes()
                self._gateway.reload_dashboard()

            return (True, "")

        except Exception as e:
            self._logger.exception("Erro ao editar nota")
            self._gateway.show_error("Erro", f"Erro ao editar nota: {e}")
            return (False, str(e))

    def handle_delete_note_click(self, note_id: Any) -> tuple[bool, str]:
        """Handle de clique para deletar nota.

        Implementa soft delete: atualiza o body da nota para "__RC_DELETED__"
        ao invés de remover permanentemente do banco de dados.
        Isso permite renderizar "Mensagem apagada" na UI mantendo histórico.

        Args:
            note_id: ID da nota a ser deletada.

        Returns:
            Tuple (success: bool, message: str)
        """
        try:
            # Encontrar nota no estado
            current_state = self._vm.state
            note_data = None
            note_author_email = None
            for note in current_state.notes:
                if note.id == note_id:
                    note_data = {
                        "id": note.id,
                        "body": note.body,
                    }
                    note_author_email = note.author_email
                    break

            if not note_data:
                self._gateway.show_error("Erro", "Nota não encontrada.")
                return (False, "Nota não encontrada")

            # Validar permissão: só pode apagar próprias notas
            current_user_email = self._gateway.get_user_email()
            if current_user_email and note_author_email:
                if current_user_email.strip().lower() != note_author_email.strip().lower():
                    self._gateway.show_info("Permissão negada", "Você só pode apagar mensagens enviadas por você.")
                    return (False, "Sem permissão")

            # Confirmar exclusão
            if not self._gateway.confirm_delete_note(note_data):
                return (False, "Cancelado")

            # Soft delete: atualizar body para marcador "__RC_DELETED__"
            if self._notes_service:
                # Verificar se service tem update_note (deveria ter)
                if hasattr(self._notes_service, "update_note"):
                    updated_note = self._notes_service.update_note(
                        note_id=note_id,
                        body="__RC_DELETED__",
                    )

                    # Atualizar estado
                    self._vm.after_note_updated(updated_note)
                else:
                    # Fallback: hard delete se update_note não existir
                    self._log.warning("NotesService não tem update_note, usando delete_note como fallback")
                    self._notes_service.delete_note(note_id)
                    self._vm.after_note_deleted(note_id)

                # Forçar reload das notas
                self._gateway.reload_notes()
                self._gateway.reload_dashboard()

            return (True, "")

        except Exception as e:
            self._logger.exception("Erro ao deletar nota")
            self._gateway.show_error("Erro", f"Erro ao deletar nota: {e}")
            return (False, str(e))

    def handle_toggle_pin(self, note_id: Any) -> tuple[bool, str]:
        """Handle para fixar/desfixar nota.

        MF-5: Inverte o estado is_pinned da nota.

        Args:
            note_id: ID da nota.

        Returns:
            Tuple (success: bool, message: str)
        """
        try:
            # Encontrar nota no estado
            current_state = self._vm.state
            note_data = None
            for note in current_state.notes:
                if note.id == note_id:
                    note_data = note
                    break

            if not note_data:
                self._gateway.show_error("Erro", "Nota não encontrada.")
                return (False, "Nota não encontrada")

            # Inverter flag is_pinned
            new_is_pinned = not getattr(note_data, "is_pinned", False)

            # Atualizar via service
            if self._notes_service:
                updated_note = self._notes_service.update_note(
                    note_id=note_id,
                    is_pinned=new_is_pinned,
                )

                # Atualizar estado
                self._vm.after_note_updated(updated_note)

                # Forçar reload das notas
                self._gateway.reload_notes()
                self._gateway.reload_dashboard()

            self._logger.debug(f"Nota {note_id} {'fixada' if new_is_pinned else 'desfixada'}")
            return (True, "")

        except Exception as e:
            self._logger.exception("Erro ao fixar/desfixar nota")
            self._gateway.show_error("Erro", f"Erro ao alterar fixação da nota: {e}")
            return (False, str(e))

    def handle_toggle_done(self, note_id: Any) -> tuple[bool, str]:
        """Handle para marcar/desmarcar nota como feita.

        MF-5: Inverte o estado is_done da nota.

        Args:
            note_id: ID da nota.

        Returns:
            Tuple (success: bool, message: str)
        """
        try:
            # Encontrar nota no estado
            current_state = self._vm.state
            note_data = None
            for note in current_state.notes:
                if note.id == note_id:
                    note_data = note
                    break

            if not note_data:
                self._gateway.show_error("Erro", "Nota não encontrada.")
                return (False, "Nota não encontrada")

            # Inverter flag is_done
            new_is_done = not getattr(note_data, "is_done", False)

            # Atualizar via service
            if self._notes_service:
                updated_note = self._notes_service.update_note(
                    note_id=note_id,
                    is_done=new_is_done,
                )

                # Atualizar estado
                self._vm.after_note_updated(updated_note)

                # Forçar reload das notas
                self._gateway.reload_notes()
                self._gateway.reload_dashboard()

            self._logger.debug(f"Nota {note_id} marcada como {'concluída' if new_is_done else 'pendente'}")
            return (True, "")

        except Exception as e:
            self._logger.exception("Erro ao marcar/desmarcar nota como feita")
            self._gateway.show_error("Erro", f"Erro ao alterar conclusão da nota: {e}")
            return (False, str(e))

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
