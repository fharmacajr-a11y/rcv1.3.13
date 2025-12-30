"""Publisher de eventos de atividade ANVISA.

Encapsula a lógica de publicar eventos no RecentActivityStore,
removendo duplicação dos handlers de finalizar/cancelar/excluir.
"""

from __future__ import annotations

import logging
from typing import Any

__all__ = ["AnvisaActivityPublisher"]

log = logging.getLogger(__name__)


class AnvisaActivityPublisher:
    """Publisher de eventos de atividade para o módulo ANVISA."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        """Inicializa o publisher.

        Args:
            logger: Logger customizado. Se None, usa logger do módulo.
        """
        self._log = logger or log

    def publish(
        self,
        *,
        tk_root: Any,
        org_id: str,
        action: str,
        message: str,
        client_id: str | None,
        cnpj: str | None,
        request_id: str,
        request_type: str,
        due_date: str | None,
        razao_social: str | None,
    ) -> None:
        """Publica evento de atividade no RecentActivityStore.

        Args:
            tk_root: Widget root do Tkinter (para HubAsyncRunner)
            org_id: ID da organização
            action: Ação realizada ("Concluída", "Cancelada", "Excluída")
            message: Mensagem descritiva do evento
            client_id: ID do cliente (pode ser None)
            cnpj: CNPJ do cliente (pode ser None)
            request_id: ID da demanda
            request_type: Tipo da demanda
            due_date: Data de vencimento (pode ser None)
            razao_social: Razão social do cliente (pode ser None)
        """
        try:
            from src.modules.hub.recent_activity_store import (
                ActivityEvent,
                get_recent_activity_store,
            )
            from src.modules.hub.async_runner import HubAsyncRunner
            from src.core.session import get_current_user

            # Obter informações do usuário atual
            current_user = get_current_user()
            user_email = current_user.email if current_user and getattr(current_user, "email", None) else None
            user_id = current_user.uid if current_user and getattr(current_user, "uid", None) else None

            # Log de consistência
            self._log.info(
                f"[ANVISA][event] {action} - request={request_id} client_id={client_id} "
                f"cnpj={cnpj} razao={razao_social}"
            )

            # Criar evento estruturado
            event = ActivityEvent(
                org_id=org_id,
                module="ANVISA",
                action=action,
                message=message,
                client_id=int(client_id) if client_id else None,
                cnpj=cnpj,
                request_id=request_id,
                request_type=request_type,
                due_date=due_date,
                actor_email=user_email,
                actor_user_id=user_id,
                metadata={"razao_social": razao_social or ""},
            )

            # Criar runner para persistência assíncrona
            runner = HubAsyncRunner(tk_root=tk_root, logger=self._log)

            # Adicionar evento (persiste automaticamente)
            get_recent_activity_store().add_event(event, persist=True, runner=runner)

        except Exception as exc:
            self._log.warning(f"[ANVISA][activity] Falha ao registrar evento: {exc}")
