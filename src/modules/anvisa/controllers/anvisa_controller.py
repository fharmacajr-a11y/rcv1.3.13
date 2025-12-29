"""Controller headless para operações de demandas ANVISA.

Controller sem dependências de GUI (Tkinter).
Gerencia operações de delete e close (finalização) de demandas.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

from ..utils.anvisa_logging import fmt_ctx
from ..utils.anvisa_errors import log_exception

log = logging.getLogger(__name__)


class AnvisaRequestsRepository(Protocol):
    """Protocol para repositório de demandas ANVISA."""

    def delete_request(self, request_id: str) -> bool:
        """Exclui demanda por ID.

        Args:
            request_id: UUID da demanda como string

        Returns:
            True se sucesso, False caso contrário
        """
        ...

    def update_request_status(self, request_id: str, new_status: str) -> bool:
        """Atualiza status da demanda.

        Args:
            request_id: UUID da demanda como string
            new_status: Novo status

        Returns:
            True se sucesso, False caso contrário
        """
        ...

    def create_request(
        self,
        *,
        org_id: str,
        client_id: int,
        request_type: str,
        status: str,
        created_by: str | None = None,
        payload: dict | None = None,
    ) -> str | None:
        """Cria nova demanda ANVISA.

        Args:
            org_id: ID da organização
            client_id: ID do cliente (BIGINT)
            request_type: Tipo da demanda
            status: Status inicial
            created_by: ID do usuário criador (opcional)
            payload: Dados adicionais em JSON (opcional)

        Returns:
            UUID da demanda criada como string, ou None se falhar
        """
        ...


class AnvisaController:
    """Controller headless para operações ANVISA (sem GUI)."""

    def __init__(
        self,
        repository: AnvisaRequestsRepository,
        logger: logging.Logger,
        notifications_service: Any | None = None,
    ) -> None:
        """Inicializa controller.

        Args:
            repository: Repositório de demandas ANVISA
            logger: Logger para operações
            notifications_service: Serviço de notificações (opcional)
        """
        self._repo = repository
        self._log = logger
        self._notifications_service = notifications_service

    def _fmt_notif(
        self,
        *,
        action: str,
        request_type: str | None,
        client_id: str | None,
    ) -> str:
        """Formata mensagem de notificação ANVISA padronizada.

        Args:
            action: Tipo da ação ("created", "deleted", "finalized", "canceled", "status_other")
            request_type: Tipo da demanda (ex: "ALTERACAO_RAZAO_SOCIAL")
            client_id: ID numérico do cliente

        Returns:
            Mensagem formatada no padrão "ANVISA • <ação>: <tipo> (Cliente <id>)"
        """
        base_map = {
            "created": "Nova demanda criada",
            "deleted": "Demanda excluída",
            "finalized": "Demanda finalizada",
            "canceled": "Demanda cancelada",
            "status_other": "Demanda atualizada",
        }
        base = base_map.get(action, "Demanda atualizada")

        if request_type and client_id:
            return f"ANVISA • {base}: {request_type} (Cliente {client_id})"
        if request_type:
            return f"ANVISA • {base}: {request_type}"
        if client_id:
            return f"ANVISA • {base} (Cliente {client_id})"
        return f"ANVISA • {base}"

    def delete_request(
        self,
        request_id: str,
        *,
        client_id: str | None = None,
        request_type: str | None = None,
    ) -> bool:
        """Exclui demanda por ID.

        Args:
            request_id: UUID da demanda (string)
            client_id: ID numérico do cliente (para notificação)
            request_type: Tipo da demanda (para notificação)

        Returns:
            True se excluído com sucesso, False caso contrário
        """
        ctx = {"request_id": request_id, "action": "delete"}

        try:
            self._log.info(f"[Controller] Excluindo demanda [{fmt_ctx(**ctx)}]")
            repo_success = self._repo.delete_request(request_id)

            if repo_success:
                self._log.info(f"[Controller] Demanda excluída com sucesso [{fmt_ctx(**ctx)}]")

                # Publicar notificação (falha não afeta retorno da operação)
                if self._notifications_service:
                    self._log.info("[Controller] Publicando notificação de exclusão")
                    try:
                        message = self._fmt_notif(
                            action="deleted",
                            request_type=request_type,
                            client_id=client_id,
                        )
                        metadata = {"request_type": request_type} if request_type else None
                        notif_success = self._notifications_service.publish(
                            module="anvisa",
                            event="deleted",
                            message=message,
                            request_id=request_id,
                            client_id=client_id,
                            metadata=metadata,
                        )
                        if not notif_success:
                            self._log.warning("[Controller] Publish de exclusão retornou False")
                    except Exception:
                        self._log.exception("[Controller] EXCEPTION ao publicar notificação de exclusão")
                else:
                    self._log.warning("[Controller] notifications_service é None - não pode publicar")
            else:
                self._log.warning(f"[Controller] Falha ao excluir (não encontrada ou RLS bloqueou) [{fmt_ctx(**ctx)}]")

            return repo_success

        except Exception as exc:
            log_exception(self._log, "[Controller] Erro ao excluir demanda", exc, **ctx)
            return False

    def set_status(
        self,
        request_id: str,
        status: str,
        *,
        client_id: str | None = None,
        request_type: str | None = None,
    ) -> bool:
        """Atualiza status da demanda (método genérico).

        Args:
            request_id: UUID da demanda (string)
            status: Novo status
            client_id: ID numérico do cliente (para notificação)
            request_type: Tipo da demanda (para notificação)

        Returns:
            True se atualizado com sucesso, False caso contrário
        """
        ctx = {"request_id": request_id, "action": "set_status", "status": status}

        try:
            self._log.info(f"[Controller] Atualizando status [{fmt_ctx(**ctx)}]")
            repo_success = self._repo.update_request_status(request_id, status)

            if repo_success:
                self._log.info(f"[Controller] Status atualizado com sucesso [{fmt_ctx(**ctx)}]")

                # Publicar notificação (falha não afeta retorno da operação)
                if self._notifications_service:
                    self._log.info("[Controller] Publicando notificação de status")
                    try:
                        # Mapear status para mensagem amigável
                        status_map = {
                            "done": "finalizada",
                            "canceled": "cancelada",
                            "in_progress": "em andamento",
                            "submitted": "submetida",
                        }
                        status_text = status_map.get(status, status)

                        # Determinar action para formatação
                        if status == "done":
                            action = "finalized"
                        elif status == "canceled":
                            action = "canceled"
                        else:
                            action = "status_other"

                        # Montar mensagem
                        if action in ("finalized", "canceled"):
                            message = self._fmt_notif(
                                action=action,
                                request_type=request_type,
                                client_id=client_id,
                            )
                        else:
                            # Manter o status_text no texto quando não for done/canceled
                            base = f"Demanda {status_text}"
                            if request_type and client_id:
                                message = f"ANVISA • {base}: {request_type} (Cliente {client_id})"
                            elif request_type:
                                message = f"ANVISA • {base}: {request_type}"
                            elif client_id:
                                message = f"ANVISA • {base} (Cliente {client_id})"
                            else:
                                message = f"ANVISA • {base}"

                        # Montar metadata
                        metadata: dict[str, str] = {"new_status": status}
                        if request_type:
                            metadata["request_type"] = request_type

                        notif_success = self._notifications_service.publish(
                            module="anvisa",
                            event="status_changed",
                            message=message,
                            request_id=request_id,
                            client_id=client_id,
                            metadata=metadata,
                        )
                        if not notif_success:
                            self._log.warning("[Controller] Publish de status retornou False")
                    except Exception:
                        self._log.exception("[Controller] EXCEPTION ao publicar notificação de status")
                else:
                    self._log.warning("[Controller] notifications_service é None - não pode publicar")
            else:
                self._log.warning(
                    f"[Controller] Falha ao atualizar status (não encontrada ou RLS bloqueou) [{fmt_ctx(**ctx)}]"
                )

            return repo_success

        except Exception as exc:
            log_exception(self._log, "[Controller] Erro ao atualizar status", exc, **ctx)
            return False

    def close_request(
        self,
        request_id: str,
        *,
        client_id: str | None = None,
        request_type: str | None = None,
    ) -> bool:
        """Finaliza demanda (status -> FINALIZADA).

        Args:
            request_id: UUID da demanda (string)
            client_id: ID numérico do cliente (para notificação)
            request_type: Tipo da demanda (para notificação)

        Returns:
            True se finalizado com sucesso, False caso contrário
        """
        from ..constants import DEFAULT_CLOSE_STATUS

        return self.set_status(request_id, DEFAULT_CLOSE_STATUS, client_id=client_id, request_type=request_type)

    def cancel_request(
        self,
        request_id: str,
        *,
        client_id: str | None = None,
        request_type: str | None = None,
    ) -> bool:
        """Cancela demanda (status -> canceled).

        Args:
            request_id: UUID da demanda (string)
            client_id: ID numérico do cliente (para notificação)
            request_type: Tipo da demanda (para notificação)

        Returns:
            True se cancelado com sucesso, False caso contrário
        """
        return self.set_status(request_id, "canceled", client_id=client_id, request_type=request_type)

    def create_request(
        self,
        *,
        org_id: str,
        client_id: str,
        request_type: str,
        created_by: str | None = None,
        payload: dict | None = None,
    ) -> str | None:
        """Cria nova demanda ANVISA.

        Args:
            org_id: ID da organização
            client_id: ID do cliente (string)
            request_type: Tipo da demanda
            created_by: ID do usuário criador (opcional)
            payload: Dados adicionais em JSON (opcional)

        Returns:
            UUID da demanda criada como string, ou None se falhar
        """
        ctx = {
            "org_id": org_id,
            "client_id": client_id,
            "action": "create",
            "type": request_type,
        }

        try:
            from ..constants import DEFAULT_CREATE_STATUS

            self._log.info(f"[Controller] Criando demanda [{fmt_ctx(**ctx)}]")

            # Converter client_id para int (BIGINT no DB)
            client_id_int = int(client_id)

            # Usar status padrão de criação
            status = DEFAULT_CREATE_STATUS

            # Criar no repositório
            request_id = self._repo.create_request(
                org_id=org_id,
                client_id=client_id_int,
                request_type=request_type,
                status=status,
                created_by=created_by,
                payload=payload,
            )

            if request_id:
                ctx["request_id"] = request_id
                self._log.info(f"[Controller] Demanda criada com sucesso [{fmt_ctx(**ctx)}]")

                # Publicar notificação (falha não afeta retorno da operação)
                if self._notifications_service:
                    self._log.info("[Controller] Publicando notificação de criação")
                    try:
                        message = self._fmt_notif(
                            action="created",
                            request_type=request_type,
                            client_id=client_id,
                        )
                        notif_success = self._notifications_service.publish(
                            module="anvisa",
                            event="created",
                            message=message,
                            client_id=client_id,
                            request_id=request_id,
                            metadata={"request_type": request_type},
                        )
                        if not notif_success:
                            self._log.warning("[Controller] Publish de criação retornou False")
                    except Exception:
                        self._log.exception("[Controller] EXCEPTION ao publicar notificação de criação")
                else:
                    self._log.warning("[Controller] notifications_service é None - não pode publicar")
            else:
                self._log.warning(
                    f"[Controller] Falha ao criar demanda (RLS bloqueou ou constraint violada) [{fmt_ctx(**ctx)}]"
                )

            return request_id

        except Exception as exc:
            log_exception(self._log, "[Controller] Erro ao criar demanda", exc, **ctx)
            return None
