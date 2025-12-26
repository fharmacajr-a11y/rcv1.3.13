# -*- coding: utf-8 -*-
"""HubGatewayImpl - Implementação do NotesGatewayProtocol para HubScreen.

Este módulo contém os métodos que implementam o NotesGatewayProtocol,
anteriormente parte do HubScreen. Extraído em MF-10 para reduzir tamanho
e complexidade.

Responsabilidades:
- get_org_id: Obter ID da organização
- get_user_email: Obter email do usuário
- is_authenticated: Verificar autenticação
- is_online: Verificar conectividade
- show_error/show_info: Wrappers de messageboxes (delega para hub_dialogs)
- show_note_editor: Diálogo de edição (delega para hub_dialogs)
- confirm_delete_note: Diálogo de confirmação (delega para hub_dialogs)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import tkinter as tk

logger = logging.getLogger(__name__)


class HubGatewayImpl:
    """Implementação do NotesGatewayProtocol para HubScreen.

    Mantém referência ao HubScreen para acessar estado e widgets.
    Delega operações de UI para hub_dialogs.
    """

    def __init__(self, parent: tk.Misc) -> None:
        """Inicializa gateway com referência ao widget pai.

        Args:
            parent: Widget pai (HubScreen instance)
        """
        self._parent = parent

    # ═══════════════════════════════════════════════════════════════════════
    # Métodos de autenticação e estado
    # ═══════════════════════════════════════════════════════════════════════

    def get_org_id(self) -> str | None:
        """Obtém ID da organização atual.

        Returns:
            ID da organização ou None se não disponível
        """
        try:
            from src.core.session import get_current_user
            from infra.supabase_client import get_supabase, exec_postgrest

            # Primeiro tenta obter do cache de sessão
            user = get_current_user()
            if user and user.org_id:
                logger.debug(f"HubGatewayImpl.get_org_id: obtido do cache de sessão: {user.org_id}")
                return user.org_id

            # Fallback: buscar diretamente do Supabase se cache estiver vazio
            logger.debug("HubGatewayImpl.get_org_id: cache vazio, buscando do Supabase diretamente")
            client = get_supabase()
            session = client.auth.get_session() if client else None
            if session and hasattr(session, "user") and session.user:
                user_id = session.user.id
                # Buscar org_id na tabela memberships
                from infra.db_schemas import MEMBERSHIPS_SELECT_ORG_ROLE

                resp = exec_postgrest(
                    client.table("memberships").select(MEMBERSHIPS_SELECT_ORG_ROLE).eq("user_id", user_id)
                )
                rows = resp.data or []
                if rows:
                    owners = [r for r in rows if (r.get("role") or "").lower() == "owner"]
                    chosen = owners[0] if owners else rows[0]
                    org_id = chosen.get("org_id")
                    logger.debug(f"HubGatewayImpl.get_org_id: obtido do Supabase: {org_id}")
                    return org_id

            logger.warning("HubGatewayImpl.get_org_id: não foi possível obter org_id (sem sessão ou memberships)")
            return None
        except Exception as e:
            logger.error(f"HubGatewayImpl.get_org_id: ERRO: {e}", exc_info=True)
            return None

    def get_user_email(self) -> str | None:
        """Obtém email do usuário atual.

        Returns:
            Email do usuário ou None se não autenticado
        """
        try:
            from infra.supabase_client import get_supabase

            client = get_supabase()
            if not client:
                logger.warning("HubGatewayImpl.get_user_email: cliente Supabase não disponível")
                return None

            session = client.auth.get_session()
            if not session:
                logger.warning("HubGatewayImpl.get_user_email: sessão não encontrada")
                return None

            if not hasattr(session, "user") or not session.user:
                logger.warning("HubGatewayImpl.get_user_email: sessão sem usuário")
                return None

            email = session.user.email
            logger.debug(f"HubGatewayImpl.get_user_email: {email}")
            return email
        except Exception as e:
            logger.error(f"HubGatewayImpl.get_user_email: ERRO: {e}", exc_info=True)
            return None

    def is_authenticated(self) -> bool:
        """Verifica se usuário está autenticado.

        Returns:
            True se autenticado, False caso contrário
        """
        try:
            from infra.supabase_client import get_supabase

            client = get_supabase()
            if not client:
                logger.warning("HubGatewayImpl.is_authenticated: cliente Supabase não disponível")
                return False

            session = client.auth.get_session()
            has_user = bool(session and hasattr(session, "user") and session.user)

            if has_user:
                user_id = session.user.id if session.user else None
                user_email = session.user.email if session.user else None
                logger.debug(f"HubGatewayImpl.is_authenticated: TRUE (uid={user_id}, email={user_email})")
            else:
                logger.warning(
                    "HubGatewayImpl.is_authenticated: FALSE (session=%s, has_user_attr=%s)",
                    session is not None,
                    hasattr(session, "user") if session else False,
                )

            return has_user
        except Exception as e:
            logger.error(f"HubGatewayImpl.is_authenticated: ERRO: {e}", exc_info=True)
            return False

    def is_online(self) -> bool:
        """Verifica se há conexão com internet.

        Simplificação: verifica se está autenticado (implica online).
        Poderia ter validação de conectividade mais sofisticada.

        Returns:
            True se online, False caso contrário
        """
        return self.is_authenticated()

    # ═══════════════════════════════════════════════════════════════════════
    # Métodos de UI - Delegam para hub_dialogs
    # ═══════════════════════════════════════════════════════════════════════

    def show_note_editor(
        self,
        note_data: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Mostra editor de nota.

        Args:
            note_data: Dados da nota para editar (None para criar nova)

        Returns:
            Dict com dados atualizados se confirmado, None se cancelado
        """
        from src.modules.hub.views.hub_dialogs import show_note_editor

        return show_note_editor(self._parent, note_data)

    def confirm_delete_note(self, note_data: dict[str, Any]) -> bool:
        """Confirma exclusão de nota.

        Args:
            note_data: Dados da nota a ser deletada

        Returns:
            True se confirmado, False se cancelado
        """
        from src.modules.hub.views.hub_dialogs import confirm_delete_note

        return confirm_delete_note(self._parent, note_data)

    def show_error(self, title: str, message: str) -> None:
        """Mostra mensagem de erro.

        Args:
            title: Título do diálogo
            message: Mensagem de erro
        """
        from src.modules.hub.views.hub_dialogs import show_error

        show_error(self._parent, title, message)

    def show_info(self, title: str, message: str) -> None:
        """Mostra mensagem informativa.

        Args:
            title: Título do diálogo
            message: Mensagem informativa
        """
        from src.modules.hub.views.hub_dialogs import show_info

        show_info(self._parent, title, message)

    def reload_notes(self) -> None:
        """Força recarregamento das notas.

        Chama o método refresh_notes_async do HubScreen para
        atualizar a lista de notas após criar/editar/deletar.
        """
        try:
            if hasattr(self._parent, "refresh_notes_async"):
                self._parent.refresh_notes_async(force=True)
                logger.debug("HubGatewayImpl.reload_notes: refresh solicitado")
            elif hasattr(self._parent, "_hub_controller"):
                self._parent._hub_controller.refresh_notes(force=True)
                logger.debug("HubGatewayImpl.reload_notes: refresh via controller")
            else:
                logger.warning("HubGatewayImpl.reload_notes: método de refresh não encontrado")
        except Exception as e:
            logger.error(f"HubGatewayImpl.reload_notes: ERRO: {e}", exc_info=True)

    def reload_dashboard(self) -> None:
        """Força recarregamento do dashboard.

        Chama o método refresh_dashboard do HubController para
        atualizar o dashboard após operações que podem afetá-lo.
        """
        try:
            # Tentar através do controller (método preferido)
            if hasattr(self._parent, "_hub_controller") and self._parent._hub_controller:
                self._parent._hub_controller.refresh_dashboard()
                logger.debug("HubGatewayImpl.reload_dashboard: refresh solicitado via controller")
                return

            # Fallback: tentar método direto
            if hasattr(self._parent, "_load_dashboard"):
                self._parent._load_dashboard()
                logger.debug("HubGatewayImpl.reload_dashboard: refresh via _load_dashboard")
                return

            # Se chegou aqui, não conseguiu recarregar
            logger.warning("HubGatewayImpl.reload_dashboard: método de refresh não encontrado")

        except Exception as e:
            logger.error(f"HubGatewayImpl.reload_dashboard: ERRO: {e}", exc_info=True)
