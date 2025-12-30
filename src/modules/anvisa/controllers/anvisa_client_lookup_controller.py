"""Controller para lookup de cliente ANVISA.

Encapsula a busca de dados de cliente (CNPJ, razão social) no Supabase,
mantendo os imports pesados (infra) somente dentro dos métodos (lazy loading).
"""

from __future__ import annotations

import logging
from typing import Any

__all__ = ["AnvisaClientLookupController"]

log = logging.getLogger(__name__)


class AnvisaClientLookupController:
    """Controller para lookup de dados de cliente (headless, sem UI)."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        """Inicializa o controller.

        Args:
            logger: Logger customizado. Se None, usa logger do módulo.
        """
        self._log = logger or log

    def lookup_client_cnpj_razao(
        self,
        *,
        org_id: str,
        client_id: str,
    ) -> tuple[str | None, str]:
        """Busca CNPJ e razão social de um cliente.

        Args:
            org_id: ID da organização
            client_id: ID do cliente

        Returns:
            Tupla (cnpj, razao_social). Se não encontrado, retorna (None, "").
        """
        try:
            from infra.supabase_client import get_supabase

            sb = get_supabase()
            resp = (
                sb.table("clients")
                .select("cnpj,razao_social")
                .eq("org_id", org_id)
                .eq("id", client_id)
                .limit(1)
                .execute()
            )

            data: list[dict[str, Any]] = getattr(resp, "data", None) or []
            if data:
                cnpj = data[0].get("cnpj")
                razao = data[0].get("razao_social") or ""
                return cnpj, razao

            return None, ""

        except Exception as exc:
            self._log.warning(f"[ANVISA][lookup] Erro ao buscar cliente: {exc}")
            return None, ""
