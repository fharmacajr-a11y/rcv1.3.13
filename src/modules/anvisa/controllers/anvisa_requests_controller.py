"""Controller headless para operações com demandas ANVISA.

Este controller encapsula as chamadas ao repositório de demandas ANVISA,
mantendo os imports pesados (infra) somente dentro dos métodos (lazy loading).

Uso típico:
    controller = AnvisaRequestsController()
    org_id = controller.resolve_org_id()
    requests = controller.list_requests(org_id)
"""

from __future__ import annotations

import logging
from typing import Any

__all__ = ["AnvisaRequestsController"]


class AnvisaRequestsController:
    """Controller para operações com demandas ANVISA (headless, sem UI)."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        """Inicializa o controller.

        Args:
            logger: Logger customizado. Se None, usa logger do módulo.
        """
        self._log = logger or logging.getLogger(__name__)

    def resolve_org_id(self) -> str:
        """Resolve o org_id do usuário logado.

        Obtém o user_id do usuário autenticado e resolve sua organização
        via tabela memberships.

        Returns:
            org_id da organização do usuário

        Raises:
            RuntimeError: Se usuário não autenticado ou organização não encontrada
        """
        from src.infra.repositories.anvisa_requests_repository import (
            _get_supabase_and_user,
            _resolve_org_id,
        )

        _, user_id = _get_supabase_and_user()
        org_id = _resolve_org_id(user_id)
        return org_id

    def list_requests(self, org_id: str) -> list[dict[str, Any]]:
        """Lista demandas ANVISA da organização.

        Args:
            org_id: ID da organização

        Returns:
            Lista de demandas com dados do cliente (join)
        """
        from src.infra.repositories.anvisa_requests_repository import list_requests

        return list_requests(org_id)

    def create_request(
        self,
        *,
        org_id: str,
        client_id: int,
        request_type: str,
        status: str,
    ) -> dict[str, Any]:
        """Cria nova demanda ANVISA.

        Args:
            org_id: ID da organização
            client_id: ID do cliente (BIGINT)
            request_type: Tipo da demanda
            status: Status inicial

        Returns:
            Dict com registro criado (incluindo id)
        """
        from src.infra.repositories.anvisa_requests_repository import create_request

        return create_request(
            org_id=org_id,
            client_id=client_id,
            request_type=request_type,
            status=status,
        )
