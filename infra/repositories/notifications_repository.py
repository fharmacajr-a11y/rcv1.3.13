"""Repositório para operações com notificações da organização.

Este módulo fornece uma camada de abstração para gerenciar notificações,
delegando operações de persistência para o Supabase.

Funcionalidades:
- Listar notificações de uma organização
- Contar notificações não lidas
- Marcar todas como lidas
- Inserir novas notificações

NOTA IMPORTANTE - Schema da Tabela org_notifications:
    - Colunas principais: org_id, module, event, message, is_read, created_at
    - Actor: actor_user_id (UUID), actor_email (TEXT)
    - Relacionamentos: client_id, request_id
    - Se houver mudança no schema do Supabase, pode ser necessário recarregar:
      Execute no banco: NOTIFY pgrst, 'reload schema';
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from infra.db_schemas import (
    ORG_NOTIFICATIONS_SELECT_FIELDS_COUNT,
    ORG_NOTIFICATIONS_SELECT_FIELDS_LIST,
)

log = logging.getLogger(__name__)


def _extract_uuid_from_request_id(value: str) -> str | None:
    """Extrai UUID de request_id que pode ter formato 'prefixo:<uuid>' ou '<uuid>'.

    Args:
        value: String com UUID ou prefixo:<uuid>

    Returns:
        UUID canonicalizado como string, ou None se inválido

    Example:
        >>> _extract_uuid_from_request_id("550e8400-e29b-41d4-a716-446655440000")
        '550e8400-e29b-41d4-a716-446655440000'
        >>> _extract_uuid_from_request_id("hub_notes_created:550e8400-e29b-41d4-a716-446655440000")
        '550e8400-e29b-41d4-a716-446655440000'
        >>> _extract_uuid_from_request_id("invalid") is None
        True
    """
    if not value:
        return None

    # Se contém ":", pegar parte após o último ":"
    if ":" in value:
        uuid_part = value.split(":")[-1]
    else:
        uuid_part = value

    # Validar e canonicalizar UUID
    try:
        uuid_obj = uuid.UUID(uuid_part)
        return str(uuid_obj)
    except (ValueError, AttributeError):
        return None


def list_notifications(org_id: str, limit: int = 20, exclude_actor_email: str | None = None) -> list[dict[str, Any]]:
    """Lista notificações de uma organização.

    Args:
        org_id: ID da organização
        limit: Número máximo de notificações a retornar (default: 20)
        exclude_actor_email: Email do autor a excluir (não mostrar próprias notificações)

    Returns:
        Lista de notificações ordenadas por created_at desc

    Example:
        >>> notifications = list_notifications("org-123", limit=10)
        >>> for notif in notifications:
        ...     print(notif["message"], notif["is_read"])
    """
    from infra.supabase_client import supabase

    try:
        query = supabase.table("org_notifications").select(ORG_NOTIFICATIONS_SELECT_FIELDS_LIST).eq("org_id", org_id)

        # Filtrar notificações do próprio autor
        if exclude_actor_email:
            query = query.neq("actor_email", exclude_actor_email)

        response = query.order("created_at", desc=True).limit(limit).execute()

        data = getattr(response, "data", None) or []
        log.debug(
            "[Notifications] Listadas %d notificação(ões) (org_id=%s, exclude_actor=%s)",
            len(data),
            org_id,
            exclude_actor_email,
        )

        return data

    except Exception:
        log.exception("Erro ao listar notificações (org_id=%s)", org_id)
        return []


def count_unread(org_id: str, exclude_actor_email: str | None = None) -> int:
    """Conta notificações não lidas de uma organização.

    Args:
        org_id: ID da organização
        exclude_actor_email: Email do autor a excluir (não contar próprias notificações)

    Returns:
        Número de notificações não lidas

    Example:
        >>> count = count_unread("org-123")
        >>> print(f"Você tem {count} notificações não lidas")
    """
    from infra.supabase_client import supabase

    try:
        query = (
            supabase.table("org_notifications")
            .select(ORG_NOTIFICATIONS_SELECT_FIELDS_COUNT, count="exact")
            .eq("org_id", org_id)
            .eq("is_read", False)
        )

        # Filtrar notificações do próprio autor
        if exclude_actor_email:
            query = query.neq("actor_email", exclude_actor_email)

        response = query.execute()

        count = getattr(response, "count", 0) or 0
        log.debug("[Notifications] %d não lida(s) (org_id=%s, exclude_actor=%s)", count, org_id, exclude_actor_email)

        return count

    except Exception:
        log.exception("Erro ao contar notificações não lidas (org_id=%s)", org_id)
        return 0


def mark_all_read(org_id: str) -> bool:
    """Marca todas as notificações de uma organização como lidas.

    Args:
        org_id: ID da organização

    Returns:
        True se sucesso, False caso contrário

    Example:
        >>> success = mark_all_read("org-123")
        >>> if success:
        ...     print("Todas notificações marcadas como lidas")
    """
    from infra.supabase_client import supabase

    try:
        log.info("[NOTIF] mark_all_read start org=%s", org_id)

        response = (
            supabase.table("org_notifications")
            .update({"is_read": True})
            .eq("org_id", org_id)
            .eq("is_read", False)
            .execute()
        )

        data = getattr(response, "data", None) or []
        count = len(data)

        log.info("[NOTIF] mark_all_read ok updated=%d org=%s", count, org_id)

        return True

    except Exception:
        log.exception("[NOTIF] Erro ao marcar notificações como lidas (org_id=%s)", org_id)
        return False


def insert_notification(
    org_id: str,
    module: str,
    event: str,
    message: str,
    *,
    actor_user_id: str | None = None,
    actor_email: str | None = None,
    client_id: str | None = None,
    request_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> bool:
    """Insere uma nova notificação no repositório.

    Args:
        org_id: ID da organização
        module: Módulo de origem (ex: "anvisa", "clients", "uploads")
        event: Tipo de evento (ex: "created", "updated", "deleted")
        message: Mensagem da notificação
        actor_user_id: UUID do usuário que gerou a ação (opcional)
        actor_email: Email do usuário que gerou a ação (opcional)
        client_id: ID do cliente relacionado (opcional)
        request_id: ID da requisição relacionada (opcional)
        metadata: Dados adicionais em JSON (opcional) - NOTA: tabela pode não ter esta coluna

    Returns:
        True se inserido com sucesso, False caso contrário

    Example:
        >>> success = insert_notification(
        ...     org_id="org-123",
        ...     module="anvisa",
        ...     event="created",
        ...     message="ANVISA • Cliente Farmácia XYZ • Nova demanda criada",
        ...     actor_email="user@example.com",
        ...     client_id="456",
        ...     request_id="req-789"
        ... )
    """
    from infra.supabase_client import supabase
    from postgrest.exceptions import APIError

    # Normalizar request_id (extrair UUID se formato prefixo:<uuid>)
    request_id_original = request_id
    request_id_db = None
    if request_id_original:
        uuid_part = _extract_uuid_from_request_id(request_id_original)
        request_id_db = uuid_part if uuid_part else request_id_original

        # Log se normalizou
        if uuid_part and uuid_part != request_id_original:
            log.info(
                "[NOTIF] request_id normalizado: original=%s db=%s",
                request_id_original,
                request_id_db,
            )

    try:
        # Dedupe: se request_id presente, verificar se já existe notificação com mesmos parâmetros
        if request_id_db:
            log.debug(
                "[NOTIF] Verificando duplicação: org=%s module=%s event=%s request_id=%s",
                org_id,
                module,
                event,
                request_id_db,
            )
            try:
                existing_check = (
                    supabase.table("org_notifications")
                    .select(ORG_NOTIFICATIONS_SELECT_FIELDS_COUNT)
                    .eq("org_id", org_id)
                    .eq("module", module)
                    .eq("event", event)
                    .eq("request_id", request_id_db)
                    .limit(1)
                    .execute()
                )

                existing_data = getattr(existing_check, "data", None) or []
                if existing_data:
                    existing_id = existing_data[0].get("id")
                    log.info(
                        "[NOTIF] Notificação já existe (dedupe): id=%s org=%s module=%s event=%s request_id=%s",
                        existing_id,
                        org_id,
                        module,
                        event,
                        request_id_db,
                    )
                    return True  # Não duplicar, retornar sucesso
            except Exception as check_exc:
                # Se falhar check, continuar com insert (fail-safe)
                log.warning(
                    "[NOTIF] Falha no pre-check de duplicação (continuando com insert): %s",
                    check_exc,
                )

        row = {
            "org_id": org_id,
            "module": module,
            "event": event,
            "message": message,
            "is_read": False,
        }

        if actor_user_id:
            row["actor_user_id"] = actor_user_id
        if actor_email:
            row["actor_email"] = actor_email
        if client_id:
            row["client_id"] = client_id
        if request_id_db:
            row["request_id"] = request_id_db
        # NOTA: metadata removido - tabela org_notifications pode não ter esta coluna
        # Se necessário, pode ser incluído na mensagem JSON-encoded

        log.info(
            "[NOTIF] insert start org=%s module=%s event=%s client=%s request=%s actor_user_id=%s actor_email=%s",
            org_id,
            module,
            event,
            client_id,
            request_id_db,
            actor_user_id,
            actor_email,
        )

        response = supabase.table("org_notifications").insert(row).execute()

        data = getattr(response, "data", None) or []

        if not data:
            log.error(
                "[NOTIF] INSERT bloqueado (RLS/constraint): org_id=%s, module=%s, event=%s", org_id, module, event
            )
            return False

        created = data[0]
        notif_id = created.get("id")
        log.info("[NOTIF] insert ok id=%s module=%s event=%s org=%s", notif_id, module, event, org_id)

        return True

    except APIError as api_err:
        # Erro PostgREST - extrair detalhes estruturados (robusto contra str/dict)
        error_data_raw = api_err.args[0] if api_err.args else None

        # Normalizar para dict (error_data_raw pode ser str ou dict)
        if isinstance(error_data_raw, dict):
            error_data = error_data_raw
        elif isinstance(error_data_raw, str):
            error_data = {"message": error_data_raw}
        else:
            error_data = {"message": str(api_err)}

        error_message = error_data.get("message", str(api_err))
        error_code = error_data.get("code", "unknown")
        error_details = error_data.get("details", "")
        error_hint = error_data.get("hint", "")

        # Fallback para erro 22P02 (invalid UUID): tentar sem request_id
        if (
            error_code == "22P02"
            and "invalid input syntax for type uuid" in error_message.lower()
            and "request_id" in row
        ):
            log.warning(
                "[NOTIF] Erro UUID em request_id (code=22P02), tentando retry sem request_id: org=%s module=%s",
                org_id,
                module,
            )
            try:
                # Remover request_id e tentar novamente (1 retry apenas)
                row_retry = {k: v for k, v in row.items() if k != "request_id"}
                response_retry = supabase.table("org_notifications").insert(row_retry).execute()
                data_retry = getattr(response_retry, "data", None) or []

                if data_retry:
                    notif_id_retry = data_retry[0].get("id")
                    log.info(
                        "[NOTIF] insert ok (retry sem request_id): id=%s module=%s event=%s org=%s",
                        notif_id_retry,
                        module,
                        event,
                        org_id,
                    )
                    return True
            except Exception as retry_exc:
                log.exception(
                    "[NOTIF] Retry sem request_id também falhou: org=%s module=%s | exc=%s",
                    org_id,
                    module,
                    retry_exc,
                )

        log.exception(
            "[NOTIF] Erro PostgREST ao inserir: org=%s module=%s event=%s | code=%s message=%s details=%s hint=%s",
            org_id,
            module,
            event,
            error_code,
            error_message,
            error_details,
            error_hint,
        )
        return False

    except Exception as exc:
        log.exception(
            "[NOTIF] Erro geral ao inserir notificação: org=%s module=%s event=%s | exc=%s", org_id, module, event, exc
        )
        return False


class NotificationsRepositoryAdapter:
    """Adapter para usar funções do repository como métodos de instância."""

    def list_notifications(
        self, org_id: str, limit: int = 20, exclude_actor_email: str | None = None
    ) -> list[dict[str, Any]]:
        """Lista notificações de uma organização."""
        return list_notifications(org_id, limit, exclude_actor_email=exclude_actor_email)

    def count_unread(self, org_id: str, exclude_actor_email: str | None = None) -> int:
        """Conta notificações não lidas."""
        return count_unread(org_id, exclude_actor_email=exclude_actor_email)

    def mark_all_read(self, org_id: str) -> bool:
        """Marca todas como lidas."""
        return mark_all_read(org_id)

    def insert_notification(
        self,
        org_id: str,
        module: str,
        event: str,
        message: str,
        *,
        actor_user_id: str | None = None,
        actor_email: str | None = None,
        client_id: str | None = None,
        request_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Insere nova notificação."""
        return insert_notification(
            org_id=org_id,
            module=module,
            event=event,
            message=message,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            client_id=client_id,
            request_id=request_id,
            metadata=metadata,
        )
