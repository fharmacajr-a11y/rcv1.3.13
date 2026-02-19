# -*- coding: utf-8 -*-
"""MF-16: Factory para componentes do HubScreen.

Este módulo é responsável por construir todos os componentes internos
do HubScreen (ViewModels, Controllers, Services, Helpers), reduzindo
a complexidade do método _init_state.

Responsabilidades:
- Criar ViewModels (Dashboard, Notes, QuickActions)
- Criar Controllers (Dashboard, Notes, QuickActions, HubScreen)
- Criar Services (Async Runner, Polling, Lifecycle, Navigation, Gateway)
- Configurar dependências e injeções

Benefícios:
- Redução de ~100 linhas em hub_screen.py
- Centralização da lógica de criação
- Facilita testes (mock factory)
- Melhora legibilidade de _init_state
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    from src.modules.hub.views.hub_screen import HubScreen

try:
    from src.core.logger import get_logger
except Exception:
    import logging as _logging

    def get_logger(name: str) -> logging.Logger:
        return _logging.getLogger(name)


logger = get_logger(__name__)


@dataclass
class HubComponents:
    """Container para todos os componentes criados pela factory.

    MF-16: Agrupa ViewModels, Controllers, Services e Helpers
    para facilitar injeção no HubScreen.
    MF-17: Adiciona dashboard_renderer.
    MF-22: Adiciona facades (navigation_facade, dashboard_facade).
    """

    # ViewModels
    dashboard_vm: Any
    notes_vm: Any
    quick_actions_vm: Any

    # Controllers
    dashboard_actions: Any
    notes_controller: Any
    quick_actions_controller: Any
    hub_controller: Any

    # Services
    async_runner: Any
    lifecycle_manager: Any
    polling_service: Any
    lifecycle_impl: Any

    # Helpers (MF-10)
    navigation_helper: Any
    gateway_helper: Any

    # Views (MF-15-C)
    hub_view: Any
    hub_callbacks: Any

    # Renderers (MF-17, MF-20)
    dashboard_renderer: Any
    notes_renderer: Any  # MF-20

    # Facades (MF-22, MF-23, MF-24, MF-25)
    navigation_facade: Any
    dashboard_facade: Any
    notes_facade: Any  # MF-23
    lifecycle_facade: Any  # MF-24
    authors_cache_facade: Any  # MF-25


class HubComponentFactory:
    """Factory para criar componentes do HubScreen.

    MF-16: Extrai lógica de criação de _init_state para módulo dedicado,
    permitindo:
    - Redução de complexidade em hub_screen.py
    - Reutilização de lógica de criação
    - Facilidade de teste (mock factory)
    - Clareza de dependências
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """Inicializa factory.

        Args:
            logger: Logger opcional (usa logger do módulo se None)
        """
        self._logger = logger or globals()["logger"]

    def create_components(
        self,
        screen: HubScreen,
        *,
        open_clientes: Optional[Callable[[], None]] = None,
        open_farmacia_popular: Optional[Callable[[], None]] = None,
        open_sngpc: Optional[Callable[[], None]] = None,
        open_mod_sifap: Optional[Callable[[], None]] = None,
        open_cashflow: Optional[Callable[[], None]] = None,
        open_sites: Optional[Callable[[], None]] = None,
    ) -> HubComponents:
        """Cria todos os componentes necessários para o HubScreen.

        Args:
            screen: Instância do HubScreen (usado como parent/gateway/navigator)
            open_*: Callbacks de navegação para módulos externos

        Returns:
            HubComponents com todas as instâncias criadas

        Raises:
            Exception: Se HubScreenController não puder ser criado (fatal)
        """
        # Obter state do screen (já deve estar inicializado)
        from src.modules.hub.state import ensure_state

        state = ensure_state(screen)

        # ========================================================================
        # VIEWMODELS (Headless - sem dependências de Tkinter)
        # ========================================================================

        # Dashboard ViewModel
        from src.modules.hub.viewmodels.dashboard_vm import DashboardViewModel

        dashboard_vm = DashboardViewModel()
        self._logger.debug("DashboardViewModel criado")

        # Notes ViewModel
        from src.modules.hub.viewmodels.notes_vm import NotesViewModel

        try:
            from src.core.services.notes_service_adapter import NotesServiceAdapter

            notes_service = NotesServiceAdapter()
            self._logger.debug("NotesServiceAdapter criado com sucesso")
        except Exception as e:
            self._logger.warning(f"NotesServiceAdapter não pôde ser criado: {e}")
            notes_service = None
        notes_vm = NotesViewModel(service=notes_service)  # type: ignore[arg-type]  # NotesServiceAdapter é compatível com protocol
        self._logger.debug("NotesViewModel criado")

        # QuickActions ViewModel
        from src.modules.hub.viewmodels.quick_actions_vm import QuickActionsViewModel

        quick_actions_vm = QuickActionsViewModel(features_service=None, logger=self._logger)
        self._logger.debug("QuickActionsViewModel criado")

        # ========================================================================
        # ASYNC RUNNER (criado antes dos Controllers)
        # ========================================================================

        from src.modules.hub.async_runner import HubAsyncRunner

        async_runner = HubAsyncRunner(tk_root=screen, logger=self._logger)
        self._logger.debug("HubAsyncRunner criado")

        # ========================================================================
        # CONTROLLERS (Headless - usam screen como adapter/gateway/navigator)
        # ========================================================================

        # Dashboard Action Controller
        from src.modules.hub.controllers.dashboard_actions import DashboardActionController

        dashboard_actions = DashboardActionController(navigator=screen, logger=self._logger)
        self._logger.debug("DashboardActionController criado")

        # Notes Controller
        from src.modules.hub.controllers.notes_controller import NotesController

        # ORG-003: Helper movido para hub/helpers/
        from src.modules.hub.helpers.session import get_app_from_widget

        # Obter notifications_service do MainWindow (seguindo padrão ANVISA)
        app = get_app_from_widget(screen)
        notifications_service = getattr(app, "notifications_service", None) if app else None

        notes_controller = NotesController(
            vm=notes_vm,
            gateway=screen,
            notes_service=notes_service,
            notifications_service=notifications_service,
            logger=self._logger,
        )
        self._logger.debug("NotesController criado")

        # QuickActions Controller
        from src.modules.hub.controllers.quick_actions_controller import QuickActionsController

        quick_actions_controller = QuickActionsController(navigator=screen, logger=self._logger)
        self._logger.debug("QuickActionsController criado")

        # ========================================================================
        # LIFECYCLE MANAGER
        # ========================================================================

        from src.modules.hub.views.hub_lifecycle_manager import HubLifecycleManager

        lifecycle_manager = HubLifecycleManager(tk_root=screen, logger=self._logger)
        self._logger.debug("HubLifecycleManager criado")

        # ========================================================================
        # HUB SCREEN VIEW + CONTROLLER (MF-15-C)
        # ========================================================================

        from src.modules.hub.hub_screen_controller import HubScreenController
        from src.modules.hub.views.hub_screen_view import HubScreenView

        # Criar callbacks protocol para HubScreenView (inline class)
        hub_callbacks = self._create_hub_callbacks(
            screen=screen,
            dashboard_actions=dashboard_actions,
            notes_controller=notes_controller,
        )
        self._logger.debug("HubScreenCallbacks criado")

        # Criar HubScreenView real
        hub_view = HubScreenView(
            parent=screen,
            callbacks=hub_callbacks,  # type: ignore[arg-type]
            open_clientes=open_clientes,
            open_farmacia_popular=open_farmacia_popular,
            open_sngpc=open_sngpc,
            open_mod_sifap=open_mod_sifap,
            open_cashflow=open_cashflow,
            open_sites=open_sites,
        )
        self._logger.debug("HubScreenView criado")

        # Injetar referências necessárias na view
        hub_view._hub_screen = screen
        hub_view._dashboard_actions = dashboard_actions

        # Criar HubScreenController
        hub_controller = HubScreenController(
            state=state,
            dashboard_vm=dashboard_vm,
            notes_vm=notes_vm,
            quick_actions_vm=quick_actions_vm,
            async_runner=async_runner,
            lifecycle=lifecycle_manager._lifecycle,  # Usar o HubLifecycle interno
            view=screen,  # type: ignore[arg-type]  # HubScreen implementa HubScreenView funcionalmente
            quick_actions_controller=quick_actions_controller,
            logger=self._logger,
        )
        self._logger.debug("HubScreenController criado com HubScreen como view")

        # ========================================================================
        # HELPERS (MF-10: Navigation + Gateway)
        # ========================================================================

        from src.modules.hub.views.hub_navigation import HubNavigationHelper
        from src.modules.hub.views.hub_gateway_impl import HubGatewayImpl

        navigation_helper = HubNavigationHelper(screen)
        gateway_helper = HubGatewayImpl(screen)
        self._logger.debug("HubNavigationHelper e HubGatewayImpl criados")

        # ========================================================================
        # SERVICES (MF-14: Polling, MF-15: Lifecycle)
        # ========================================================================

        from src.modules.hub.services.hub_polling_service import HubPollingService
        from src.modules.hub.services.hub_lifecycle_impl import HubLifecycleImpl

        polling_service = HubPollingService(callbacks=screen)  # type: ignore[arg-type]
        lifecycle_impl = HubLifecycleImpl(callbacks=screen)  # type: ignore[arg-type]
        self._logger.debug("HubPollingService e HubLifecycleImpl criados")

        # ========================================================================
        # DASHBOARD RENDERER (MF-17)
        # ========================================================================

        from src.modules.hub.views.hub_dashboard_renderer import HubDashboardRenderer

        # Criar callbacks para o renderer (inline class)
        dashboard_renderer_callbacks = self._create_dashboard_renderer_callbacks(screen)
        dashboard_renderer = HubDashboardRenderer(callbacks=dashboard_renderer_callbacks)  # type: ignore[arg-type]
        self._logger.debug("HubDashboardRenderer criado")

        # ========================================================================
        # NOTES RENDERER (MF-20)
        # ========================================================================

        from src.modules.hub.views.hub_notes_renderer import HubNotesRenderer

        # Criar callbacks para o renderer (inline class)
        notes_renderer_callbacks = self._create_notes_renderer_callbacks(screen)
        notes_renderer = HubNotesRenderer(callbacks=notes_renderer_callbacks)  # type: ignore[arg-type]
        self._logger.debug("HubNotesRenderer criado")

        # ========================================================================
        # FACADES (MF-22)
        # ========================================================================

        from src.modules.hub.views.hub_navigation_facade import HubNavigationFacade
        from src.modules.hub.views.hub_dashboard_facade import HubDashboardFacade

        # Navigation Facade
        navigation_facade = HubNavigationFacade(
            nav_helper=navigation_helper,
            debug_logger=getattr(screen, "_dlog", None),
        )
        self._logger.debug("HubNavigationFacade criado")

        # Dashboard Facade (precisa de mais dependências)
        dashboard_facade = HubDashboardFacade(
            parent=screen,
            dashboard_vm=dashboard_vm,
            dashboard_actions=dashboard_actions,
            renderer=dashboard_renderer,
            state_manager=screen._state_manager,
            get_org_id=lambda: screen._get_org_id_safe(),
            get_user_id=lambda: screen._get_user_id_safe(),
            get_main_app=lambda: screen._get_main_app(),
            on_refresh_callback=lambda: screen._load_dashboard(),
            debug_logger=getattr(screen, "_dlog", None),
        )
        self._logger.debug("HubDashboardFacade criado")

        # Notes Facade (MF-23)
        from src.modules.hub.views.hub_notes_facade import HubNotesFacade

        notes_facade = HubNotesFacade(
            parent=screen,
            notes_controller=notes_controller,
            hub_controller=hub_controller,
            notes_renderer=notes_renderer,
            polling_service=polling_service,
            state_manager=screen._state_manager,
            get_org_id=lambda: screen._get_org_id_safe(),
            get_email=lambda: screen._get_email_safe(),
            debug_logger=getattr(screen, "_dlog", None),
        )
        self._logger.debug("HubNotesFacade criado")

        # Authors Cache Facade (MF-25)
        from src.modules.hub.views.hub_authors_cache_facade import HubAuthorsCacheFacade

        authors_cache_facade = HubAuthorsCacheFacade(
            polling_service=polling_service,
            state_manager=screen._state_manager,
            get_org_id=lambda: screen._get_org_id_safe(),
            auth_ready_callback=lambda: screen._auth_ready(),
            debug_logger=getattr(screen, "_dlog", None),
        )
        self._logger.debug("HubAuthorsCacheFacade criado")

        # Lifecycle Facade (MF-24)
        from src.modules.hub.views.hub_lifecycle_facade import HubLifecycleFacade

        lifecycle_facade = HubLifecycleFacade(
            parent=screen,
            lifecycle_manager=lifecycle_manager,
            lifecycle_impl=lifecycle_impl,
            polling_service=polling_service,
            state_manager=screen._state_manager,
            auth_ready_callback=lambda: screen._auth_ready(),
            get_org_id=lambda: screen._get_org_id_safe(),
            get_email=lambda: screen._get_email_safe(),
            start_live_sync_callback=lambda: screen._start_live_sync(),
            render_notes_callback=lambda notes, force: screen.render_notes(notes, force),
            refresh_author_cache_callback=lambda force: authors_cache_facade.refresh_author_names_cache(force),
            clear_author_cache_callback=lambda: authors_cache_facade.clear_author_cache(),
            debug_logger=getattr(screen, "_dlog", None),
        )
        self._logger.debug("HubLifecycleFacade criado")

        # ========================================================================
        # RETORNAR CONTAINER
        # ========================================================================

        return HubComponents(
            # ViewModels
            dashboard_vm=dashboard_vm,
            notes_vm=notes_vm,
            quick_actions_vm=quick_actions_vm,
            # Controllers
            dashboard_actions=dashboard_actions,
            notes_controller=notes_controller,
            quick_actions_controller=quick_actions_controller,
            hub_controller=hub_controller,
            # Services
            async_runner=async_runner,
            lifecycle_manager=lifecycle_manager,
            polling_service=polling_service,
            lifecycle_impl=lifecycle_impl,
            # Helpers
            navigation_helper=navigation_helper,
            gateway_helper=gateway_helper,
            # Views
            hub_view=hub_view,
            hub_callbacks=hub_callbacks,
            # Renderers (MF-17, MF-20)
            dashboard_renderer=dashboard_renderer,
            notes_renderer=notes_renderer,
            # Facades (MF-22, MF-23, MF-24, MF-25)
            navigation_facade=navigation_facade,
            dashboard_facade=dashboard_facade,
            notes_facade=notes_facade,
            lifecycle_facade=lifecycle_facade,
            authors_cache_facade=authors_cache_facade,
        )

    def _create_hub_callbacks(
        self,
        screen: HubScreen,
        dashboard_actions: Any,
        notes_controller: Any,
    ) -> Any:
        """Cria instância de HubScreenCallbacks (inline class).

        MF-16: Extrai criação da classe inline de _init_state.

        Args:
            screen: HubScreen instance
            dashboard_actions: DashboardActionController instance
            notes_controller: NotesController instance

        Returns:
            Instância de HubScreenCallbacks
        """

        class HubScreenCallbacks:
            """Implementação de HubViewCallbacks usando métodos do HubScreen."""

            def __init__(self, hub: HubScreen):
                self.hub = hub

            def on_module_click(self, module: str) -> None:
                pass  # Não usado ainda

            def on_card_click(self, card_type: str, client_id: str | None = None) -> None:
                if dashboard_actions:
                    if card_type == "clients":
                        dashboard_actions.handle_card_clients_click(self.hub._dashboard_vm.state)
                    elif card_type == "pending":
                        dashboard_actions.handle_card_pendencias_click(self.hub._dashboard_vm.state)
                    elif card_type == "tasks":
                        dashboard_actions.handle_card_tarefas_click(self.hub._dashboard_vm.state)

            def on_new_task_click(self) -> None:
                if dashboard_actions:
                    dashboard_actions.handle_new_task_click()

            def on_new_obligation_click(self) -> None:
                if dashboard_actions:
                    dashboard_actions.handle_new_obligation_click()

            def on_view_all_activity_click(self) -> None:
                if dashboard_actions:
                    dashboard_actions.handle_view_all_activity_click()

            def on_add_note_click(self, note_text: str) -> None:
                notes_controller.handle_add_note_click(note_text)

            def on_edit_note_click(self, note_id: str) -> None:
                notes_controller.handle_edit_note_click(note_id)

            def on_delete_note_click(self, note_id: str) -> None:
                notes_controller.handle_delete_note_click(note_id)

            def on_toggle_pin_click(self, note_id: str) -> None:
                notes_controller.handle_toggle_pin(note_id)

            def on_toggle_done_click(self, note_id: str) -> None:
                notes_controller.handle_toggle_done(note_id)

            def on_debug_shortcut(self) -> None:
                if hasattr(self.hub, "_debug_info"):
                    self.hub._debug_info()

            def on_refresh_authors_cache(self, force: bool = False) -> None:
                if hasattr(self.hub, "_reload_names_cache"):
                    self.hub._reload_names_cache(force=force)

        return HubScreenCallbacks(screen)

    def _create_dashboard_renderer_callbacks(self, screen: HubScreen) -> Any:
        """Cria instância de DashboardRendererCallbacks (inline class).

        MF-17: Extrai criação dos callbacks para o dashboard renderer.

        Args:
            screen: HubScreen instance

        Returns:
            Instância de DashboardRendererCallbacks
        """

        class DashboardRendererCallbacks:
            """Implementação de DashboardRenderCallbacks usando HubScreen."""

            def __init__(self, hub: HubScreen):
                self.hub = hub

            def get_dashboard_view(self):
                """Retorna a instância do HubDashboardView."""
                return self.hub._dashboard_view

        return DashboardRendererCallbacks(screen)

    def _create_notes_renderer_callbacks(self, screen: HubScreen) -> Any:
        """Cria instância de NotesRendererCallbacks (inline class).

        MF-20: Extrai criação dos callbacks para o notes renderer.

        Args:
            screen: HubScreen instance

        Returns:
            Instância de NotesRendererCallbacks
        """

        class NotesRendererCallbacks:
            """Implementação de NotesRenderCallbacks usando HubScreen."""

            def __init__(self, hub: HubScreen):
                self.hub = hub

            def get_notes_view(self):
                """Retorna a instância do HubNotesView."""
                return self.hub._notes_view

            def get_state(self):
                """Retorna o estado atual do Hub."""
                return self.hub.state

            def get_debug_logger(self):
                """Retorna função de debug logging (opcional)."""
                if hasattr(self.hub, "_dlog"):
                    return self.hub._dlog
                return None

        return NotesRendererCallbacks(screen)
