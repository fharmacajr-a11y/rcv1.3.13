# -*- coding: utf-8 -*-
"""Repositório para operações com demandas ANVISA.

Este módulo fornece uma camada de abstração para gerenciar demandas ANVISA de clientes,
delegando operações de persistência para o Supabase.

Funcionalidades:
- Listar demandas ANVISA com dados do cliente (join)
- Criar novas demandas
- Atualizar status de demandas existentes

Note:
    As demandas são armazenadas na tabela client_anvisa_requests com RLS habilitado.
    O org_id é obrigatório para todas as operações (validado por RLS via memberships).
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)


def _get_supabase_and_user() -> tuple[Any, str]:
    """Retorna (supabase, user_id) do usuário logado.

    Raises:
        RuntimeError: Se usuário não estiver autenticado

    Returns:
        Tupla com (cliente Supabase, user_id)
    """
    from infra.supabase_client import supabase

    try:
        # Compatibilidade com supabase-py v1 e v2
        resp = supabase.auth.get_user()
        user = getattr(resp, "user", None) or resp
        user_id = getattr(user, "id", None)

        if not user_id:
            raise RuntimeError("Usuário não autenticado no Supabase. Faça login novamente.")

        return supabase, user_id
    except Exception as exc:
        log.exception("Erro ao obter usuário autenticado")
        raise RuntimeError(f"Falha na autenticação: {exc}") from exc


def _resolve_org_id(user_id: str) -> str:
    """Resolve o org_id do usuário logado via tabela memberships.

    Args:
        user_id: ID do usuário autenticado

    Raises:
        RuntimeError: Se organização não for encontrada

    Returns:
        org_id da organização do usuário
    """
    from infra.supabase_client import supabase

    try:
        response = supabase.table("memberships").select("org_id").eq("user_id", user_id).limit(1).execute()
        data = getattr(response, "data", None) or []

        if not data:
            raise RuntimeError("Organização não encontrada para o usuário atual.")

        return data[0]["org_id"]
    except Exception as exc:
        log.exception("Erro ao resolver org_id")
        raise RuntimeError(f"Falha ao obter organização: {exc}") from exc


def list_requests(org_id: str) -> list[dict[str, Any]]:
    """Lista demandas ANVISA com dados do cliente (join).

    Args:
        org_id: ID da organização proprietária das demandas

    Returns:
        Lista de demandas com campos:
        - id: ID da demanda
        - client_id: ID do cliente
        - request_type: Tipo da demanda
        - status: Status da demanda
        - created_at: Data de criação
        - updated_at: Data da última atualização
        - clients: Dict com razao_social e cnpj (embedded via FK)

    Example:
        >>> demandas = list_requests("org-123")
        >>> for d in demandas:
        ...     print(d["clients"]["razao_social"], d["request_type"])
    """
    from infra.supabase_client import supabase

    try:
        response = (
            supabase.table("client_anvisa_requests")
            .select("id,client_id,request_type,status,created_at,updated_at,clients(razao_social,cnpj)")
            .eq("org_id", org_id)
            .order("updated_at", desc=True)
            .execute()
        )

        data = getattr(response, "data", None) or []
        log.info("[ANVISA] Listadas %d demanda(s) (org_id=%s)", len(data), org_id)

        return data

    except Exception as exc:
        log.exception("Erro ao listar demandas ANVISA (org_id=%s)", org_id)
        raise RuntimeError(f"Falha ao carregar demandas: {exc}") from exc


def create_request(
    org_id: str,
    client_id: int,
    request_type: str,
    status: str = "draft",
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Cria uma nova demanda ANVISA no repositório.

    Args:
        org_id: ID da organização proprietária
        client_id: ID do cliente (BIGINT, referencia public.clients.id)
        request_type: Tipo da demanda (ex: "Alteração do Responsável Legal")
        status: Status inicial (default: "draft")
        payload: Dados adicionais em JSON (opcional)

    Returns:
        Registro da demanda criada com todos os campos (incluindo ID gerado)

    Raises:
        RuntimeError: Se inserção falhar (RLS, FK violation, etc.)

    Example:
        >>> nova = create_request(
        ...     org_id="org-123",
        ...     client_id=456,
        ...     request_type="Alteração de Porte",
        ...     status="draft"
        ... )
        >>> print(nova["id"])
    """
    from infra.supabase_client import supabase

    try:
        # Garantir que client_id é int (BIGINT no DB)
        client_id_int = int(client_id)

        row = {
            "org_id": org_id,
            "client_id": client_id_int,
            "request_type": request_type,
            "status": status,
        }

        if payload:
            row["payload"] = payload

        response = supabase.table("client_anvisa_requests").insert(row).execute()

        data = getattr(response, "data", None) or []

        if not data:
            log.error(
                "[ANVISA] INSERT bloqueado (RLS/constraint): org_id=%s, client_id=%d, tipo=%s",
                org_id,
                client_id_int,
                request_type,
            )
            raise RuntimeError(
                "INSERT bloqueado por RLS ou constraint em 'client_anvisa_requests'. "
                "Verifique se usuário tem permissão e se client_id existe em public.clients."
            )

        created = data[0]
        log.info(
            "[ANVISA] Demanda criada: id=%s, client_id=%d, tipo=%s, org_id=%s",
            created.get("id"),
            client_id_int,
            request_type,
            org_id,
        )

        return created

    except Exception as exc:
        log.exception("Erro ao criar demanda ANVISA: org_id=%s, client_id=%s, tipo=%s", org_id, client_id, request_type)
        raise RuntimeError(f"Falha ao inserir demanda: {exc}") from exc


def update_request_status(request_id: str, new_status: str) -> bool:
    """Atualiza o status de uma demanda ANVISA.

    Args:
        request_id: ID (UUID) da demanda a ser atualizada
        new_status: Novo status (ex: "draft", "done", "canceled", "in_progress")

    Returns:
        True se atualizou com sucesso, False caso contrário

    Example:
        >>> updated = update_request_status("123e4567-e89b-12d3-a456-426614174000", "done")
        >>> print(updated)
        True
    """
    from infra.supabase_client import supabase
    from src.modules.anvisa.constants import STATUS_ALL, STATUS_ALIASES

    # Normalizar status para valor aceito pelo banco
    status_normalized = new_status.strip().lower()
    status_normalized = STATUS_ALIASES.get(status_normalized, status_normalized)

    # Validar se status é permitido
    if status_normalized not in STATUS_ALL:
        log.error(
            "[ANVISA] Status inválido: %r (normalizado=%r, permitidos=%s)", new_status, status_normalized, STATUS_ALL
        )
        return False

    try:
        log.debug(
            "[ANVISA] Atualizando status: id=%s, status=%s (normalizado=%s)", request_id, new_status, status_normalized
        )

        # Tentar obter org_id para garantir update com RLS
        try:
            _, user_id = _get_supabase_and_user()
            org_id = _resolve_org_id(user_id)

            # Update filtrando por id e org_id
            response = (
                supabase.table("client_anvisa_requests")
                .update({"status": status_normalized})
                .eq("id", request_id)
                .eq("org_id", org_id)
                .execute()
            )
        except Exception:
            # Fallback: tentar update sem org_id (RLS vai validar)
            log.debug("[ANVISA] Fallback: tentando update sem filtro org_id")
            response = (
                supabase.table("client_anvisa_requests")
                .update({"status": status_normalized})
                .eq("id", request_id)
                .execute()
            )

        data = getattr(response, "data", None) or []
        count = getattr(response, "count", None)

        # Verificar se alguma linha foi afetada
        if not data and count == 0:
            log.warning(
                "[ANVISA] 0 linhas atualizadas: id=%s, status=%s (RLS bloqueou ou não existe)",
                request_id,
                status_normalized,
            )
            return False

        if not data:
            log.warning("[ANVISA] Nenhuma demanda encontrada: id=%s", request_id)
            return False

        log.info("[ANVISA] Status atualizado: id=%s, status=%s (%d linha(s))", request_id, status_normalized, len(data))
        return True

    except Exception:
        log.exception("[ANVISA] Erro ao atualizar status: id=%s", request_id)
        return False


def delete_request(request_id: str) -> bool:
    """Exclui uma demanda ANVISA.

    Args:
        request_id: ID (UUID) da demanda a ser excluída

    Returns:
        True se excluiu com sucesso, False caso contrário

    Raises:
        RuntimeError: Se exclusão falhar

    Example:
        >>> deleted = delete_request("123e4567-e89b-12d3-a456-426614174000")
        >>> print(deleted)
        True
    """
    from infra.supabase_client import supabase

    try:
        response = supabase.table("client_anvisa_requests").delete().eq("id", request_id).execute()

        data = getattr(response, "data", None) or []

        if not data:
            log.warning("[ANVISA] Nenhuma demanda encontrada para exclusão: id=%s", request_id)
            return False

        log.info("[ANVISA] Demanda excluída: id=%s", request_id)
        return True

    except Exception as exc:
        log.exception("Erro ao excluir demanda ANVISA: id=%s", request_id)
        raise RuntimeError(f"Falha ao excluir demanda: {exc}") from exc


class AnvisaRequestsRepositoryAdapter:
    """Adapter para usar funções do repository como métodos de instância.

    Permite que o controller/service usem o repository via Protocol/interface.
    """

    def list_requests(self, org_id: str) -> list[dict[str, Any]]:
        """Lista todas as demandas de uma organização.

        Args:
            org_id: ID da organização

        Returns:
            Lista de demandas (dicts)
        """
        return list_requests(org_id)

    def delete_request(self, request_id: str) -> bool:
        """Exclui demanda por ID.

        Args:
            request_id: UUID da demanda como string

        Returns:
            True se sucesso, False caso contrário
        """
        return delete_request(request_id)

    def update_request_status(self, request_id: str, new_status: str) -> bool:
        """Atualiza status da demanda.

        Args:
            request_id: UUID da demanda como string
            new_status: Novo status

        Returns:
            True se sucesso, False caso contrário
        """
        return update_request_status(request_id, new_status)

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
        """Cria nova demanda ANVISA e retorna UUID.

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
        try:
            # Chamar função de criação
            created = create_request(
                org_id=org_id,
                client_id=client_id,
                request_type=request_type,
                status=status,
                payload=payload,
            )

            # Extrair e retornar ID (UUID string)
            return created.get("id") if created else None

        except Exception:
            log.exception("Erro ao criar demanda no adapter")
            return None
