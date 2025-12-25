# -*- coding: utf-8 -*-
"""Controller headless para notificações da TopBar.

REFATORAÇÃO P2 (Microfase 3):
- Camada headless (sem Tkinter) para apresentação de notificações
- Normalização, formatação e ordenação
- Desacopla lógica de apresentação da UI
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class NotificationVM:
    """ViewModel de notificação (headless).

    Contém dados pré-formatados para exibição na UI.
    """

    id: str
    """ID único da notificação."""

    created_at_raw: str | None
    """Timestamp original (ISO ou outro formato)."""

    created_at_display: str
    """Data/hora formatada para exibição (ex: '21/12/2025 14:30')."""

    message_display: str
    """Mensagem formatada para lista (sem quebras, truncada se necessário)."""

    actor_display: str
    """Nome/email do autor para coluna 'Por'."""

    is_read: bool
    """Se a notificação foi lida."""

    module: str | None
    """Módulo de origem (para detalhes)."""

    event: str | None
    """Evento/ação (para detalhes)."""

    request_id: str | None
    """ID da requisição (para detalhes)."""

    actor_email: str | None
    """Email do autor (para detalhes)."""

    actor_display_name: str | None
    """Nome completo do autor (para detalhes)."""

    raw: dict[str, Any]
    """Dados originais completos (fallback para campos não mapeados)."""


class TopbarNotificationsController:
    """Controller headless para apresentação de notificações.

    Responsável por:
    - Normalizar dados brutos de notificações
    - Formatar strings de exibição (data, mensagem, autor)
    - Ordenar itens por data (desc)
    - Montar linhas do Treeview (tree_row)
    - Montar payload de detalhes (detail_payload)
    """

    def __init__(self, preview_max: int = 120):
        """Inicializa o controller.

        Args:
            preview_max: Tamanho máximo da mensagem na lista (trunca com "...")
        """
        self._preview_max = preview_max

    def build_items(
        self,
        raw_list: list[dict[str, Any]],
        *,
        resolve_actor: Callable[[str], str] | None = None,
    ) -> list[NotificationVM]:
        """Constrói lista de ViewModels a partir de dados brutos.

        Args:
            raw_list: Lista de notificações brutas (dicts do service)
            resolve_actor: Função opcional para resolver nome do autor (email -> nome)

        Returns:
            Lista de NotificationVM ordenados por data (desc)
        """
        items: list[NotificationVM] = []

        for raw in raw_list:
            # Extrair campos
            notif_id = raw.get("id")
            if not notif_id:
                # Sem ID, pular
                continue

            created_at_raw = raw.get("created_at")
            created_at_display = raw.get("created_at_local_str", "--")

            # Normalizar mensagem
            message_raw = raw.get("message", "")
            message_display = self._format_message(message_raw, raw.get("is_read", False))

            # Normalizar autor
            actor_email = raw.get("actor_email", "")
            actor_display_name = raw.get("actor_display_name", "")
            actor_initial = raw.get("actor_initial", "")

            if resolve_actor and actor_email:
                actor_display = resolve_actor(actor_email)
            else:
                actor_display = self._format_actor(
                    actor_display_name,
                    actor_initial,
                )

            # Criar ViewModel
            vm = NotificationVM(
                id=str(notif_id),
                created_at_raw=created_at_raw,
                created_at_display=created_at_display,
                message_display=message_display,
                actor_display=actor_display,
                is_read=raw.get("is_read", False),
                module=raw.get("module"),
                event=raw.get("event"),
                request_id=raw.get("request_id"),
                actor_email=actor_email,
                actor_display_name=actor_display_name,
                raw=raw,
            )

            items.append(vm)

        # Ordenar por data (mais recentes primeiro)
        # Usar created_at_raw para ordenação se disponível, senão usar created_at_display
        items.sort(
            key=lambda x: (x.created_at_raw or x.created_at_display or ""),
            reverse=True,
        )

        return items

    def _format_message(self, message: str, is_read: bool) -> str:
        """Formata mensagem para exibição na lista.

        Args:
            message: Mensagem original
            is_read: Se foi lida

        Returns:
            Mensagem formatada (sem quebras, truncada, com bullet se não lida)
        """
        # Limpar e normalizar
        cleaned = message.strip()
        # Substituir quebras de linha por espaço
        cleaned = cleaned.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
        # Remover espaços múltiplos
        cleaned = " ".join(cleaned.split())

        # Truncar se necessário
        if len(cleaned) > self._preview_max:
            cleaned = cleaned[: self._preview_max - 3] + "..."

        # Adicionar bullet se não lida
        if not is_read:
            cleaned = "\u25cf " + cleaned  # Bullet point

        return cleaned

    def _format_actor(self, display_name: str, initial: str) -> str:
        """Formata nome do autor para coluna 'Por'.

        Args:
            display_name: Nome completo do autor
            initial: Inicial do autor (fallback)

        Returns:
            Nome formatado para exibição
        """
        name = (display_name or "").strip()
        if name and name != "?":
            return name

        init = (initial or "").strip()
        if init:
            return init

        return "\u2014"  # Em dash (fallback)

    def tree_row(self, item: NotificationVM) -> tuple[str, str, str]:
        """Monta linha do Treeview (3 colunas).

        Args:
            item: ViewModel da notificação

        Returns:
            Tupla (data, mensagem, por) para inserir no Treeview
        """
        return (
            item.created_at_display,
            item.message_display,
            item.actor_display,
        )

    def detail_payload(self, item: NotificationVM) -> dict[str, str]:
        """Monta payload de detalhes para messagebox.

        Args:
            item: ViewModel da notificação

        Returns:
            Dict com campos formatados para exibição de detalhes
        """
        # Formatar usuário completo (nome + email)
        if item.actor_display_name and item.actor_display_name != "?" and item.actor_email and item.actor_email != "--":
            user_info = f"{item.actor_display_name} <{item.actor_email}>"
        elif item.actor_email and item.actor_email != "--":
            user_info = item.actor_email
        else:
            user_info = "--"

        return {
            "created_at": item.created_at_display,
            "module": item.module or "--",
            "event": item.event or "--",
            "message": item.raw.get("message", ""),  # Mensagem completa (não truncada)
            "request_id": item.request_id or "--",
            "user": user_info,
        }
