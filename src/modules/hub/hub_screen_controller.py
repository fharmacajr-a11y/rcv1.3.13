# -*- coding: utf-8 -*-
"""HubScreenController - Orquestração headless do HubScreen.

Responsável por coordenar View, State, ViewModels e Services sem código Tkinter.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

# MF-40: Import do serviço assíncrono (extraído na MF-31)
from src.modules.hub.services import hub_async_tasks_service as async_tasks

# MF-3: Imports para handlers de dashboard
from src.modules.hub.views.hub_dashboard_callbacks import (
    handle_card_click,
    handle_client_picked_for_obligation,
    handle_new_obligation_click,
    handle_new_task_click,
    handle_view_all_activity_click,
)

if TYPE_CHECKING:
    from src.modules.hub.async_runner import HubAsyncRunner
    from src.modules.hub.controllers.quick_actions_controller import QuickActionsController
    from src.modules.hub.hub_lifecycle import HubLifecycle
    from src.modules.hub.state import HubState
    from src.modules.hub.viewmodels import (
        DashboardViewModel,
        NotesViewModel,
        QuickActionsViewModel,
    )
    from src.modules.hub.viewmodels.notes_vm import NoteItemView
    from src.modules.hub.views.hub_screen_view import HubScreenView


class HubScreenController:
    """Controller headless do HubScreen.

    Responsabilidades:
    - Lifecycle (start/stop/refresh de dashboard e notas)
    - Handlers de eventos de UI (cliques, edições, debug)
    - Integração com ViewModels (carregar dados, atualizar cache)

    NÃO responsável por:
    - Widgets Tkinter (isso é da View)
    - Layout/grid/pack (isso é da View)
    - Acesso direto a StringVar/IntVar (comunica via métodos da View)
    """

    def __init__(
        self,
        state: HubState,
        dashboard_vm: DashboardViewModel,
        notes_vm: NotesViewModel,
        quick_actions_vm: QuickActionsViewModel,
        async_runner: HubAsyncRunner,
        lifecycle: HubLifecycle,
        view: HubScreenView,
        quick_actions_controller: QuickActionsController,
        *,
        logger: logging.Logger | None = None,
    ) -> None:
        """Inicializa controller com dependências.

        MF-19: Callbacks de navegação removidos - toda navegação agora via QuickActionsController.

        Args:
            state: HubState (estado do Hub)
            dashboard_vm: DashboardViewModel
            notes_vm: NotesViewModel
            quick_actions_vm: QuickActionsViewModel
            async_runner: HubAsyncRunner
            lifecycle: HubLifecycle
            view: HubScreenView
            quick_actions_controller: QuickActionsController (MF-17, centralização MF-19)
            logger: Logger opcional
        """
        self.state = state
        self.dashboard_vm = dashboard_vm
        self.notes_vm = notes_vm
        self.quick_actions_vm = quick_actions_vm
        self.async_runner = async_runner
        self.lifecycle = lifecycle
        self.view = view
        self.quick_actions_controller = quick_actions_controller
        self.logger = logger or logging.getLogger(__name__)

        # Flag para logar warning de realtime apenas uma vez
        self._realtime_warning_logged = False

    # ═══════════════════════════════════════════════════════════════════════
    # LIFECYCLE - Gerenciamento de timers e polling
    # ═══════════════════════════════════════════════════════════════════════

    def start(self) -> None:
        """Inicia timers e polling (dashboard, notas, live sync).

        Delega para HubLifecycle que já gerencia isso.
        """
        self.state.is_active = True
        self.lifecycle.start()

    def stop(self) -> None:
        """Para timers e polling.

        Delega para HubLifecycle.
        """
        self.state.is_active = False
        self.lifecycle.stop()

    def refresh_dashboard(self) -> None:
        """Força refresh do dashboard (assíncrono).

        Carrega dados do dashboard via ViewModel e atualiza View.
        """
        if not self.state.is_active:
            return

        # Marcar timestamp de refresh
        self.state.mark_dashboard_refresh()

        # Carregar dados via async runner
        self.load_dashboard_data_async()

    def refresh_notes(self, *, force: bool = False) -> None:
        """Força refresh das notas (assíncrono).

        Args:
            force: Se True, ignora cooldown e força atualização
        """
        if not self.state.is_active:
            return

        # Verificar cooldown (5s) se não forçado
        if not force:
            import time

            if self.state.last_notes_refresh_time > 0:
                elapsed = time.time() - self.state.last_notes_refresh_time
                if elapsed < 5:
                    self.logger.debug(f"Notes refresh ignorado - cooldown ativo ({elapsed:.1f}s)")
                    return

        self.state.mark_notes_refresh()
        self.load_notes_data_async()

    def load_notes_data_async(self) -> None:
        """Carrega dados de notas de forma assíncrona via NotesViewModel.

        MF-31: Delega ao hub_async_tasks_service.
        """
        async_tasks.load_notes_data_async(self)

    def refresh_author_names_cache_async(self, *, force: bool = False) -> None:
        """Atualiza cache de nomes de autores de forma assíncrona.

        MF-31: Delega ao hub_async_tasks_service.

        Args:
            force: Se True, ignora cooldown.
        """
        async_tasks.refresh_author_names_cache_async(self, force=force)

    # ═══════════════════════════════════════════════════════════════════════
    # REALTIME - Setup e handlers de eventos realtime
    # ═══════════════════════════════════════════════════════════════════════

    def setup_realtime(self) -> None:
        """Configura canal de realtime para receber updates de notas."""
        # Sincronizar org_id
        if hasattr(self.view, "_get_org_id_safe"):
            self.state.org_id = self.view._get_org_id_safe()  # type: ignore

        org_id = self.state.org_id
        if not org_id:
            self.logger.debug("setup_realtime: org_id não disponível")
            return

        if self.state.live_sync_on and self.state.live_org_id == org_id:
            self.logger.debug("setup_realtime: já ativo para este org_id")
            return

        try:
            from src.infra.supabase_client import get_supabase

            client = get_supabase()
            channel_name = f"rc_notes_org_{org_id}"
            ch = client.realtime.channel(channel_name)

            # INSERTs da organização atual
            ch.on(
                "postgres_changes",
                {
                    "event": "INSERT",
                    "schema": "public",
                    "table": "rc_notes",
                    "filter": f"org_id=eq.{org_id}",
                },
                lambda payload: self.on_realtime_note(payload.get("new") or {}),
            )

            ch.subscribe()

            # Atualizar state
            self.state.live_sync_on = True
            self.state.live_org_id = org_id
            self.state.live_channel = ch

            self.logger.debug(f"Realtime configurado para org {org_id}")
        except AttributeError as exc:
            # MF-29: Realtime não disponível no cliente sync (erro esperado)
            if "sync client" in str(exc).lower() or "realtime" in str(exc).lower():
                if not self._realtime_warning_logged:
                    self.logger.warning(
                        "Realtime não disponível no cliente sync do Supabase; "
                        "continuando apenas com polling. Use cliente async se precisar de realtime."
                    )
                    self._realtime_warning_logged = True
            else:
                self.logger.error(f"Erro de atributo ao configurar realtime: {exc}")
            self.state.live_channel = None
            self.state.live_sync_on = False
        except Exception as exc:
            if not self._realtime_warning_logged:
                self.logger.debug(f"Realtime não disponível (usando apenas polling): {exc}")
                self._realtime_warning_logged = True
            self.state.live_channel = None
            self.state.live_sync_on = False

    def stop_realtime(self) -> None:
        """Para sync realtime (sair do Hub, logout)."""
        self.state.live_sync_on = False
        self.state.live_org_id = None

        try:
            if self.state.live_channel:
                self.state.live_channel.unsubscribe()
        except Exception as exc:
            self.logger.warning(f"Falha ao desinscrever live_channel: {exc}")

        self.state.live_channel = None

    def on_realtime_note(self, row: dict[str, Any]) -> None:
        """Handler chamado quando nota nova é recebida via realtime.

        Args:
            row: Dados da nota recebida do realtime
        """
        if not row or not row.get("id"):
            self.logger.debug("on_realtime_note: payload inválido (sem id)")
            return

        # Verificar se nota já existe no cache
        note_id = row.get("id")
        existing_ids = {n.get("id") for n in self.state.cached_notes if isinstance(n, dict)}

        if note_id in existing_ids:
            self.logger.debug(f"on_realtime_note: nota {note_id} já existe, ignorando")
            return

        # Append incremental
        self._append_note_incremental(row)

    def _append_note_incremental(self, row: dict[str, Any]) -> None:
        """Adiciona nota incrementalmente à lista em cache e UI.

        Args:
            row: Dados da nota a adicionar
        """
        # Adicionar ao cache
        self.state.cached_notes.insert(0, row)  # Novas no topo

        # Atualizar hash
        self.state.update_notes_hash(self.state.cached_notes)  # type: ignore[arg-type]

        # Renderizar via view
        try:
            if hasattr(self.view, "render_notes"):
                self.view.render_notes(self.state.cached_notes, force=True)  # type: ignore
        except Exception as exc:
            self.logger.error(f"Erro ao renderizar nota incremental: {exc}")

        self.logger.debug(f"Nota {row.get('id')} adicionada incrementalmente")

    # ═══════════════════════════════════════════════════════════════════════
    # QUICK ACTIONS - Handlers de atalhos rápidos do Hub
    # ═══════════════════════════════════════════════════════════════════════

    def on_quick_action_clicked(self, action_id: str) -> None:
        """Handler para clique em atalho rápido (Quick Action).

        MF-17: Delega para QuickActionsController, eliminando duplicação de lógica.

        Args:
            action_id: ID do atalho ("clientes", "senhas", "auditoria", etc.)
        """
        # Normalizar para lowercase (case-insensitive)
        action_id_lower = (action_id or "").lower()

        self.logger.debug(f"Quick action clicked: {action_id_lower}")

        try:
            # Delegar para QuickActionsController (MF-17)
            handled = self.quick_actions_controller.handle_action_click(action_id_lower)

            if handled:
                self.logger.debug(f"Quick action '{action_id_lower}' executada com sucesso")
            else:
                self.logger.warning(f"Quick action desconhecida: {action_id_lower}")

        except Exception as exc:
            self.logger.error(f"Erro ao executar quick action '{action_id_lower}': {exc}", exc_info=True)

    # ═══════════════════════════════════════════════════════════════════════
    # EVENTS - Handlers de eventos de UI
    # ═══════════════════════════════════════════════════════════════════════

    def on_module_clicked(self, module: str) -> None:
        """Handler para clique em módulo (Clientes, Senhas, etc.).

        MF-18/MF-19: Delega 100% para QuickActionsController.handle_module_click.
        Sem fallback - toda navegação centralizada.

        Args:
            module: Nome do módulo ("clientes", "senhas", "auditoria", etc.)
        """
        # Validação de entrada
        if not module:
            self.logger.warning("Module ID vazio ou None em on_module_clicked")
            return

        module_lower = module.lower()
        self.logger.debug(f"Module clicked: {module_lower}")

        try:
            # MF-18/MF-19: Delegar para QuickActionsController (centralização completa)
            handled = self.quick_actions_controller.handle_module_click(module_lower)

            if handled:
                self.logger.debug(f"Módulo '{module_lower}' tratado via QuickActionsController")
            else:
                self.logger.warning(f"Módulo desconhecido: {module_lower}")

        except Exception as exc:
            self.logger.error(f"Erro ao processar clique em módulo '{module_lower}': {exc}", exc_info=True)

    def on_card_clicked(self, card_type: str, client_id: str | None = None) -> None:
        """Handler para clique em card do dashboard.

        Args:
            card_type: Tipo de card ("clients", "pending", "tasks")
            client_id: ID do cliente (opcional, para cards específicos)
        """
        self.logger.debug(f"Card clicked: {card_type}, client_id={client_id}")

        # Delegar para callback específico baseado em card_type
        if card_type == "clients":
            self.on_card_clients_click()
        elif card_type == "pending":
            self.on_card_pendencias_click()
        elif card_type == "tasks":
            self.on_card_tarefas_click()
        else:
            self.logger.warning(f"Card type desconhecido: {card_type}")

    def on_add_note_clicked(self, note_text: str) -> None:
        """Handler para adicionar nota compartilhada.

        Args:
            note_text: Texto da nota a adicionar
        """
        # Delega para NotesController existente
        # Por enquanto, apenas log
        self.logger.debug(f"Add note: {note_text[:50]}...")

    def on_edit_note_clicked(self, note_id: str) -> None:
        """Handler para editar nota existente.

        Args:
            note_id: ID da nota a editar
        """
        self.logger.debug(f"Edit note: {note_id}")

    def on_delete_note_clicked(self, note_id: str) -> None:
        """Handler para excluir nota.

        Args:
            note_id: ID da nota a excluir
        """
        self.logger.debug(f"Delete note: {note_id}")

    def on_toggle_pin_clicked(self, note_id: str) -> None:
        """Handler para pin/unpin nota.

        Args:
            note_id: ID da nota
        """
        self.logger.debug(f"Toggle pin: {note_id}")

    def on_toggle_done_clicked(self, note_id: str) -> None:
        """Handler para marcar nota como done.

        Args:
            note_id: ID da nota
        """
        self.logger.debug(f"Toggle done: {note_id}")

    def on_debug_shortcut(self) -> None:
        """Handler para Ctrl+D (debug info).

        Será implementado delegando para helper existente.
        """
        self.logger.debug("Debug shortcut pressed")

    def on_refresh_authors_cache(self, force: bool = False) -> None:
        """Handler para Ctrl+L (refresh cache de autores).

        Args:
            force: Se True, ignora cooldown
        """
        if force or self.state.should_refresh_authors_cache():
            self.state.mark_authors_refresh()
            self.logger.debug("Refreshing authors cache...")

    # ─────────────────────────────────────────────────────────────────────
    # Dashboard Event Handlers
    # ─────────────────────────────────────────────────────────────────────

    def on_new_task(self) -> None:
        """Handler para criar nova tarefa (delega para helper).

        MF-3: Implementado - delega para handle_new_task_click.
        """
        self.logger.debug("Nova tarefa solicitada")
        try:
            handle_new_task_click(
                parent=self.view,
                get_org_id=self.view._get_org_id_safe,  # type: ignore[attr-defined]
                get_user_id=self.view._get_email_safe,  # type: ignore[attr-defined]
                on_success_callback=lambda: self.refresh_dashboard(),
            )
        except Exception as exc:
            self.logger.exception("Erro ao criar nova tarefa: %s", exc)

    def on_new_obligation(self) -> None:
        """Handler para criar nova obrigação (delega para helper).

        MF-3: Implementado - delega para handle_new_obligation_click.
        """
        self.logger.debug("Nova obrigação solicitada")
        try:
            # Callback para quando cliente for selecionado
            def on_client_picked(client_data: dict) -> None:
                handle_client_picked_for_obligation(
                    client_data=client_data,
                    parent=self.view,
                    get_org_id=self.view._get_org_id_safe,  # type: ignore[attr-defined]
                    get_user_id=self.view._get_email_safe,  # type: ignore[attr-defined]
                    get_main_app=self.view._get_app,  # type: ignore[attr-defined]
                    on_refresh_callback=lambda: self.refresh_dashboard(),
                )

            handle_new_obligation_click(
                parent=self.view,
                get_org_id=self.view._get_org_id_safe,  # type: ignore[attr-defined]
                get_user_id=self.view._get_email_safe,  # type: ignore[attr-defined]
                get_main_app=self.view._get_app,  # type: ignore[attr-defined]
                on_client_picked=on_client_picked,
            )
        except Exception as exc:
            self.logger.exception("Erro ao criar nova obrigação: %s", exc)

    def on_view_all_activity(self) -> None:
        """Handler para visualizar toda atividade da equipe (delega para helper).

        MF-3: Implementado - delega para handle_view_all_activity_click.
        """
        self.logger.debug("Ver toda atividade solicitada")
        try:
            handle_view_all_activity_click(self.view)
        except Exception as exc:
            self.logger.exception("Erro ao visualizar atividade: %s", exc)

    def on_card_clients_click(self) -> None:
        """Handler de clique no card 'Clientes Ativos'.

        MF-3: Implementado - delega para handle_card_click.
        """
        self.logger.debug("Card 'Clientes Ativos' clicado")
        try:
            # Obter dashboard_actions do view (compatível com arquitetura atual)
            if hasattr(self.view, "_dashboard_actions"):
                dashboard_actions = self.view._dashboard_actions  # type: ignore[attr-defined]
                handle_card_click(
                    card_type="clients",
                    state=self.dashboard_vm.state,
                    controller=dashboard_actions,
                    parent=self.view,
                )
            else:
                # Fallback para quick_actions_controller
                self.quick_actions_controller.handle_action_click("clientes")
        except Exception as exc:
            self.logger.exception("Erro ao processar clique no card Clientes: %s", exc)

    def on_card_pendencias_click(self) -> None:
        """Handler de clique no card 'Pendências Regulatórias'.

        MF-3: Implementado - delega para handle_card_click.
        """
        self.logger.debug("Card 'Pendências' clicado")
        try:
            # Obter dashboard_actions do view (compatível com arquitetura atual)
            if hasattr(self.view, "_dashboard_actions"):
                dashboard_actions = self.view._dashboard_actions  # type: ignore[attr-defined]
                handle_card_click(
                    card_type="pending",
                    state=self.dashboard_vm.state,
                    controller=dashboard_actions,
                    parent=self.view,
                )
            else:
                self.logger.warning("Dashboard actions não disponível para card pendencias")
        except Exception as exc:
            self.logger.exception("Erro ao processar clique no card Pendências: %s", exc)

    def on_card_tarefas_click(self) -> None:
        """Handler de clique no card 'Tarefas Hoje'.

        MF-3: Implementado - delega para handle_card_click.
        """
        self.logger.debug("Card 'Tarefas' clicado")
        try:
            # Obter dashboard_actions do view (compatível com arquitetura atual)
            if hasattr(self.view, "_dashboard_actions"):
                dashboard_actions = self.view._dashboard_actions  # type: ignore[attr-defined]
                handle_card_click(
                    card_type="tasks",
                    state=self.dashboard_vm.state,
                    controller=dashboard_actions,
                    parent=self.view,
                )
            else:
                self.logger.warning("Dashboard actions não disponível para card tarefas")
        except Exception as exc:
            self.logger.exception("Erro ao processar clique no card Tarefas: %s", exc)

    # ═══════════════════════════════════════════════════════════════════════
    # INTEGRATION - Integração com ViewModels/Services
    # ═══════════════════════════════════════════════════════════════════════

    def load_dashboard_data_async(self) -> None:
        """Carrega dados do dashboard de forma assíncrona via DashboardViewModel.

        MF-31: Delega ao hub_async_tasks_service.
        """
        async_tasks.load_dashboard_data_async(self)

    def load_dashboard_data(self) -> Any:
        """Carrega dados do dashboard via ViewModel.

        Returns:
            DashboardViewState com dados carregados
        """
        org_id = self.state.org_id
        if not org_id:
            return self.dashboard_vm.from_error("Organização não identificada")

        try:
            state = self.dashboard_vm.load(org_id=org_id, today=None)
            self.state.is_dashboard_loaded = True
            return state
        except Exception as exc:
            self.logger.exception("Erro ao carregar dashboard")
            return self.dashboard_vm.from_error(str(exc))

    def load_notes_data(self) -> list[NoteItemView]:
        """Carrega notas compartilhadas via ViewModel.

        Returns:
            Lista de NoteItemView
        """
        org_id = self.state.org_id
        if not org_id:
            return []

        try:
            state = self.notes_vm.load(
                org_id=org_id,
                author_names_cache=self.state.cached_authors,
            )
            self.state.is_notes_loaded = True
            return state.notes
        except Exception:
            self.logger.exception("Erro ao carregar notas")
            return []

    def refresh_author_names_cache(self, force: bool = False) -> None:
        """Atualiza cache de nomes de autores.

        Args:
            force: Se True, ignora cooldown
        """
        if not force and not self.state.should_refresh_authors_cache():
            return

        if self.state.names_refreshing:
            return

        self.state.mark_authors_refresh()
        self.logger.debug("Author names cache refresh scheduled")

    # ═══════════════════════════════════════════════════════════════════════
    # HELPERS - Métodos auxiliares
    # ═══════════════════════════════════════════════════════════════════════

    def update_notes_ui_state(self) -> None:
        """Atualiza estado do botão e placeholder de notas baseado em org_id."""
        has_org = bool(self.state.org_id)

        if has_org:
            self.view.update_notes_ui_state(
                button_enabled=True,
                placeholder_message=None,
            )
        else:
            self.view.update_notes_ui_state(
                button_enabled=False,
                placeholder_message="Aguardando autenticação...",
            )
