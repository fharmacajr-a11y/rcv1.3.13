"""Serviço de notificações (headless, sem Tkinter).

Gerencia notificações da organização, incluindo:
- Buscar notificações mais recentes
- Contar não lidas
- Marcar como lidas
- Publicar novas notificações
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any, Callable, Protocol

log = logging.getLogger(__name__)


class NotificationsRepository(Protocol):
    """Protocol para repositório de notificações."""

    def list_notifications(
        self, org_id: str, limit: int = 20, exclude_actor_email: str | None = None
    ) -> list[dict[str, Any]]:
        """Lista notificações de uma organização.

        Args:
            org_id: ID da organização
            limit: Número máximo de notificações
            exclude_actor_email: Email do autor a excluir (não mostrar próprias notificações)
        """
        ...

    def count_unread(self, org_id: str, exclude_actor_email: str | None = None) -> int:
        """Conta notificações não lidas.

        Args:
            org_id: ID da organização
            exclude_actor_email: Email do autor a excluir (não contar próprias notificações)
        """
        ...

    def mark_all_read(self, org_id: str) -> bool:
        """Marca todas como lidas."""
        ...

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
        ...

    # Métodos para "Excluir pra mim"
    def get_user_hidden_before(self, org_id: str, user_id: str) -> str | None:
        """Obtém timestamp hidden_before para um usuário."""
        ...

    def set_user_hidden_before(self, org_id: str, user_id: str, hidden_before_iso: str) -> bool:
        """Define timestamp hidden_before para um usuário (upsert)."""
        ...

    def list_hidden_notification_ids(self, org_id: str, user_id: str, limit: int = 5000) -> list[str]:
        """Lista IDs de notificações ocultadas pelo usuário."""
        ...

    def hide_notification_for_user(self, org_id: str, user_id: str, notification_id: str) -> bool:
        """Oculta uma notificação específica para o usuário."""
        ...

    def clear_hidden_ids_for_user(self, org_id: str, user_id: str) -> bool:
        """Limpa todos os IDs ocultados pelo usuário."""
        ...

    def count_unread_before(self, org_id: str, before_iso: str, exclude_actor_email: str | None = None) -> int:
        """Conta notificações não lidas antes de um timestamp."""
        ...

    def count_unread_by_ids(self, org_id: str, ids: list[str], exclude_actor_email: str | None = None) -> int:
        """Conta notificações não lidas por IDs."""
        ...


class NotificationsService:
    """Serviço de notificações (headless)."""

    def __init__(
        self,
        repository: NotificationsRepository,
        org_id_provider: Callable[[], str | None],
        user_provider: Callable[[], dict[str, Any] | None],
        logger: logging.Logger | None = None,
    ):
        """Inicializa serviço de notificações.

        Args:
            repository: Repositório de notificações
            org_id_provider: Função que retorna org_id atual
            user_provider: Função que retorna dados do usuário (uid, email)
            logger: Logger para operações (opcional)
        """
        self._repo = repository
        self._org_id_provider = org_id_provider
        self._user_provider = user_provider
        self._log = logger or log

        # Cache do mapa de iniciais (carregado do .env)
        self._initials_map: dict[str, str] | None = None

    def _load_initials_map(self) -> dict[str, str]:
        """Carrega o mapa de iniciais do .env (RC_INITIALS_MAP).

        Returns:
            Dicionário {email: nome} normalizado (emails em lowercase)
        """
        if self._initials_map is not None:
            return self._initials_map

        try:
            rc_initials_map = os.getenv("RC_INITIALS_MAP", "")
            if rc_initials_map:
                raw_map = json.loads(rc_initials_map)
                # Normalizar keys para lowercase
                self._initials_map = {k.lower(): v for k, v in raw_map.items()}
            else:
                self._initials_map = {}
        except Exception as exc:
            self._log.debug("[NotificationsService] Erro ao carregar RC_INITIALS_MAP: %s", exc)
            self._initials_map = {}

        return self._initials_map

    def _resolve_actor_info(self, actor_email: str | None) -> tuple[str, str]:
        """Resolve informações do autor da notificação.

        Args:
            actor_email: Email do autor (pode ser None ou vazio)

        Returns:
            Tupla (display_name, initial):
            - display_name: Nome resolvido ou "?" se não encontrado
            - initial: Primeira letra do nome (uppercase) ou "" se não encontrado
        """
        if not actor_email:
            return ("?", "")

        # Carregar mapa de iniciais
        initials_map = self._load_initials_map()

        # Normalizar email
        email_lower = actor_email.lower()

        # Tentar resolver pelo mapa
        if email_lower in initials_map:
            display_name = initials_map[email_lower]
            initial = display_name[0].upper() if display_name else ""
            return (display_name, initial)

        # Fallback: usar prefixo do email (antes do @)
        try:
            prefix = actor_email.split("@")[0]
            if prefix:
                # Capitalizar primeira letra do prefixo
                display_name = prefix.capitalize()
                initial = prefix[0].upper()
                return (display_name, initial)
        except Exception as exc:
            self._log.debug("Falha ao extrair iniciais de %s: %s", actor_email, exc)

        # Fallback final: usar email completo
        return (actor_email, actor_email[0].upper() if actor_email else "")

    def resolve_display_name(self, email: str | None) -> str:
        """Resolve email para nome de exibição usando RC_INITIALS_MAP.

        Método público para uso externo (ex: NotesController).

        Args:
            email: Email a resolver

        Returns:
            Nome resolvido (ex: "Junior") ou fallback:
            - Prefixo do email capitalizado (ex: "Farmacajr")
            - "?" se email vazio

        Example:
            >>> service.resolve_display_name("farmacajr@gmail.com")
            "Junior"
            >>> service.resolve_display_name("user@example.com")
            "User"
        """
        if not email:
            return "?"

        # Usar _resolve_actor_info (já implementa a lógica de RC_INITIALS_MAP)
        display_name, _ = self._resolve_actor_info(email)
        return display_name

    def fetch_latest(self, limit: int = 20, *, include_self: bool = False) -> list[dict[str, Any]]:
        """Busca notificações mais recentes.

        Args:
            limit: Número máximo de notificações
            include_self: Se True, inclui notificações do próprio usuário. Default False.

        Returns:
            Lista de notificações ordenadas por created_at desc
        """
        org_id = self._org_id_provider()
        if not org_id:
            self._log.debug("[NotificationsService] Sem org_id, retornando lista vazia")
            return []

        # Obter email do usuário atual para filtrar suas próprias notificações
        user_data = self._user_provider()
        current_email = user_data.get("email") if user_data else None

        # Se include_self=True, não filtrar por email (passar None para exclude_actor_email)
        exclude_email = None if include_self else current_email

        try:
            return self._repo.list_notifications(org_id, limit, exclude_actor_email=exclude_email)
        except Exception:
            self._log.exception("[NotificationsService] Erro ao buscar notificações")
            return []

    def fetch_latest_for_ui(self, limit: int = 20) -> list[dict[str, Any]]:
        """Busca notificações mais recentes com formatação para UI.

        Converte created_at para timezone local (America/Sao_Paulo) e adiciona
        campos formatados para exibição na interface.

        Filtra notificações ocultas pelo usuário (hide for me).

        Args:
            limit: Número máximo de notificações

        Returns:
            Lista de notificações com campos adicionais:
            - created_at_local_str: Data/hora formatada em timezone local (DD/MM/YYYY HH:MM)
            - request_id_short: Primeiros 8 caracteres do request_id (ou "—")
        """
        # Buscar mais itens para compensar os filtrados
        raw_notifications = self.fetch_latest(limit * 3, include_self=True)

        # Carregar dados de ocultação do usuário
        org_id = self._org_id_provider()
        user_data = self._user_provider()
        user_id = user_data.get("uid") if user_data else None

        hidden_before: str | None = None
        hidden_ids: set[str] = set()

        if org_id and user_id:
            try:
                raw_hidden_before = self._repo.get_user_hidden_before(org_id, user_id)
                # Validar tipo: deve ser str ou None (protege contra MagicMock/objetos)
                hidden_before = raw_hidden_before if isinstance(raw_hidden_before, str) else None

                raw_ids = self._repo.list_hidden_notification_ids(org_id, user_id)
                # Validar tipo: deve ser lista de strings (protege contra MagicMock/objetos)
                if isinstance(raw_ids, (list, set, tuple)):
                    hidden_ids = {x for x in raw_ids if isinstance(x, str) and x}
                else:
                    hidden_ids = set()
            except Exception as exc:
                self._log.debug("[NotificationsService] Erro ao carregar hidden data: %s", exc)

        # Filtrar notificações ocultas
        notifications: list[dict[str, Any]] = []
        for notif in raw_notifications:
            notif_id = notif.get("id", "")
            created_at = notif.get("created_at", "")

            # Pular se está na lista de IDs ocultos
            if notif_id and notif_id in hidden_ids:
                continue

            # Pular se created_at <= hidden_before
            if hidden_before and created_at and created_at <= hidden_before:
                continue

            notifications.append(notif)

            # Limitar ao máximo pedido
            if len(notifications) >= limit:
                break

        # Timezone local
        try:
            tz_local = ZoneInfo("America/Sao_Paulo")
        except Exception:
            self._log.warning("[NotificationsService] Falha ao obter timezone America/Sao_Paulo, usando UTC")
            tz_local = ZoneInfo("UTC")

        # Processar cada notificação
        for notif in notifications:
            # Converter created_at para local
            created_at = notif.get("created_at", "")
            if created_at:
                try:
                    # Parse ISO timestamp do Supabase (com Z ou +00:00)
                    dt_utc = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    # Converter para timezone local
                    dt_local = dt_utc.astimezone(tz_local)
                    # Formatar para exibição
                    notif["created_at_local_str"] = dt_local.strftime("%d/%m/%Y %H:%M")
                except Exception as exc:
                    self._log.debug("[NotificationsService] Erro ao converter created_at: %s", exc)
                    notif["created_at_local_str"] = created_at[:16]
            else:
                notif["created_at_local_str"] = "—"

            # Extrair primeiros 8 caracteres do request_id
            request_id = notif.get("request_id", "")
            if request_id and len(request_id) >= 8:
                notif["request_id_short"] = request_id[:8]
            else:
                notif["request_id_short"] = "—"

            # Resolver informações do autor
            actor_email = notif.get("actor_email", "")
            display_name, initial = self._resolve_actor_info(actor_email)
            notif["actor_display_name"] = display_name
            notif["actor_initial"] = initial

        return notifications

    def fetch_unread_count(self, *, include_self: bool = False) -> int:
        """Conta notificações não lidas (excluindo ocultas pelo usuário).

        Args:
            include_self: Se True, inclui notificações do próprio usuário. Default False.

        Returns:
            Número de notificações não lidas (descontando as ocultas)
        """
        org_id = self._org_id_provider()
        if not org_id:
            return 0

        # Obter dados do usuário
        user_data = self._user_provider()
        current_email = user_data.get("email") if user_data else None
        user_id = user_data.get("uid") if user_data else None

        # Se include_self=True, não filtrar por email (passar None para exclude_actor_email)
        exclude_email = None if include_self else current_email

        try:
            # Total de não lidas
            total = self._repo.count_unread(org_id, exclude_actor_email=exclude_email)

            if not user_id:
                return max(0, total)

            # Subtrair notificações ocultas via hidden_before
            hidden_before = self._repo.get_user_hidden_before(org_id, user_id)
            if hidden_before:
                hidden_before_count = self._repo.count_unread_before(
                    org_id, hidden_before, exclude_actor_email=exclude_email
                )
                total -= hidden_before_count

            # Subtrair notificações ocultas via IDs
            hidden_ids = self._repo.list_hidden_notification_ids(org_id, user_id)
            if hidden_ids:
                hidden_ids_count = self._repo.count_unread_by_ids(org_id, hidden_ids, exclude_actor_email=exclude_email)
                total -= hidden_ids_count

            return max(0, total)

        except Exception:
            self._log.exception("[NotificationsService] Erro ao contar não lidas")
            return 0

    def mark_all_read(self) -> bool:
        """Marca todas as notificações como lidas.

        Returns:
            True se sucesso, False caso contrário
        """
        org_id = self._org_id_provider()
        if not org_id:
            self._log.warning("[NotificationsService] Sem org_id, não pode marcar como lidas")
            return False

        try:
            return self._repo.mark_all_read(org_id)
        except Exception:
            self._log.exception("[NotificationsService] Erro ao marcar como lidas")
            return False

    def hide_notification_for_me(self, notification_id: str) -> bool:
        """Oculta uma notificação específica para o usuário atual.

        Args:
            notification_id: ID da notificação a ocultar

        Returns:
            True se sucesso, False caso contrário
        """
        org_id = self._org_id_provider()
        user_data = self._user_provider()
        user_id = user_data.get("uid") if user_data else None

        if not org_id or not user_id:
            self._log.warning("[NotificationsService] Sem org_id ou user_id para hide_notification_for_me")
            return False

        try:
            return self._repo.hide_notification_for_user(org_id, user_id, notification_id)
        except Exception:
            self._log.exception("[NotificationsService] Erro ao ocultar notificação %s", notification_id)
            return False

    def hide_all_for_me(self) -> bool:
        """Oculta todas as notificações para o usuário atual (via timestamp).

        Isso NÃO deleta as notificações do feed global, apenas as oculta para este usuário.

        Returns:
            True se sucesso, False caso contrário
        """
        org_id = self._org_id_provider()
        user_data = self._user_provider()
        user_id = user_data.get("uid") if user_data else None

        if not org_id or not user_id:
            self._log.warning("[NotificationsService] Sem org_id ou user_id para hide_all_for_me")
            return False

        try:
            # Definir hidden_before como agora (UTC ISO)
            now_utc = datetime.now(ZoneInfo("UTC")).isoformat()

            # 1) Definir timestamp hidden_before
            ok1 = self._repo.set_user_hidden_before(org_id, user_id, now_utc)

            # 2) Limpar IDs individuais (para evitar contagens duplicadas)
            ok2 = self._repo.clear_hidden_ids_for_user(org_id, user_id)

            if ok1:
                self._log.info("[NotificationsService] hide_all_for_me success: user=%s ts=%s", user_id, now_utc)
            else:
                self._log.warning(
                    "[NotificationsService] hide_all_for_me parcial: set_hidden_before=%s clear_ids=%s", ok1, ok2
                )

            return ok1

        except Exception:
            self._log.exception("[NotificationsService] Erro ao ocultar todas notificações")
            return False

    def publish(
        self,
        module: str,
        event: str,
        message: str,
        *,
        client_id: str | None = None,
        request_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Publica uma nova notificação.

        Args:
            module: Módulo de origem (ex: "anvisa")
            event: Tipo de evento (ex: "created", "updated", "deleted")
            message: Mensagem da notificação
            client_id: ID do cliente relacionado (opcional)
            request_id: ID da requisição relacionada (opcional)
            metadata: Dados adicionais (opcional)

        Returns:
            True se publicado com sucesso, False caso contrário

        Example:
            >>> service.publish(
            ...     module="anvisa",
            ...     event="created",
            ...     message="ANVISA • Cliente XYZ • Nova demanda criada",
            ...     client_id="456",
            ...     request_id="req-789"
            ... )
        """
        org_id = self._org_id_provider()
        if not org_id:
            self._log.warning("[NOTIF] publish ABORTADO: sem org_id (module=%s event=%s)", module, event)
            return False

        # Obter dados do usuário atual
        user_data = self._user_provider()
        actor_user_id = user_data.get("uid") if user_data else None  # UUID do usuário
        actor_email = user_data.get("email") if user_data else None

        if not actor_email:
            self._log.warning(
                "[NOTIF] publish SEM ACTOR: org=%s module=%s event=%s (continuando mesmo assim)", org_id, module, event
            )

        self._log.debug(
            "[NOTIF] publish called org=%s actor_user_id=%s actor_email=%s module=%s event=%s client=%s request=%s",
            org_id,
            actor_user_id,
            actor_email,
            module,
            event,
            client_id,
            request_id,
        )

        try:
            success = self._repo.insert_notification(
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

            if success:
                self._log.debug("[NOTIF] publish SUCCESS org=%s module=%s event=%s", org_id, module, event)
            else:
                self._log.error(
                    "[NOTIF] publish FAILED (repo retornou False) org=%s module=%s event=%s", org_id, module, event
                )

            return success

        except Exception:
            self._log.exception("[NOTIF] publish EXCEPTION: org=%s module=%s event=%s", org_id, module, event)
            return False
