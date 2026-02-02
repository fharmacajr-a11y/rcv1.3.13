# -*- coding: utf-8 -*-
"""HubScreen - Orquestrador central do HUB.

Responsabilidades (MF-22: Thin Orchestrator):
- Inicializar componentes via HubScreenBuilder (MF-22)
- Construir painéis de UI (delegando para views especializados)
- Expor API pública para MainWindow e protocolos de navegação
- Coordenar lifecycle (polling, live sync, timers)
- Delegar navegação para NavigationFacade (MF-22)
- Delegar dashboard para DashboardFacade (MF-22)

Arquitetura (MF-10..MF-22):
- ViewModels: Dashboard, Notes, QuickActions
- Controllers: DashboardAction, Notes, QuickActions, HubScreen
- Services: Polling (MF-14), Lifecycle (MF-15), Builder (MF-22)
- Renderers: Dashboard (MF-17), Notes (MF-20)
- Facades: Navigation, Dashboard (MF-22)
- State: HubStateManager (MF-19) centraliza mutações

Histórico: HUB-REFACTOR-01..08, HUB-SPLIT-01..04, MF-10..MF-22
"""

from __future__ import annotations

import tkinter as tk
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk
from src.ui.ui_tokens import APP_BG

try:
    from src.core.logger import get_logger
except Exception:
    import logging

    def get_logger(name: str = __name__):
        return logging.getLogger(name)


from src.modules.hub.hub_lifecycle import HubLifecycle
from src.modules.hub.hub_state_manager import HubStateManager
from src.modules.hub.layout import apply_hub_notes_right
from src.modules.hub.state import HubState, ensure_state
from src.modules.hub.viewmodels import (
    DashboardViewState,
)

# MF-30: build_dashboard_* removidos (agora em HubDashboardView)
# MF-13: hub_dashboard_callbacks não é mais importado diretamente aqui
# MF-22: Dashboard e Navigation handlers movidos para facades
# MF-23: Notes operations movidos para HubNotesFacade
# ORG-003: Helpers consolidados em hub/helpers/
from src.modules.hub.helpers.debug import show_debug_info
from src.modules.hub.helpers.session import (
    get_app_from_widget,
    get_email_safe_from_widget,
    get_org_id_safe_from_widget,
    get_user_id_safe_from_widget,
    is_auth_ready,
)

# ORG-004: Helpers puros extraídos
from src.modules.hub.views.hub_screen_pure import get_local_timezone

# MF-10: Módulos extraídos para reduzir complexidade
# MF-13: Handlers de dashboard extraídos (agora em facades - MF-22)
# MF-22: Dashboard e Navigation handlers movidos para facades
# MF-14: Serviço de polling extraído
# MF-15: Serviço de lifecycle impl extraído

logger = get_logger(__name__)
log = logger

# ORG-004: Timezone handling movido para hub_screen_pure.py
LOCAL_TZ = get_local_timezone()

# logger disponível desde o topo do módulo


class HubScreen(tk.Frame if not (HAS_CUSTOMTKINTER and ctk) else ctk.CTkFrame):  # type: ignore[misc]
    """HubScreen - Orquestrador central do HUB.

    Responsável por:
    - Criar e coordenar ViewModels, Controllers, Lifecycle
    - Construir painéis de UI (delegando para helpers)
    - Expor API pública para MainWindow
    - Implementar protocolos de navegação
    """

    DEBUG_NOTES = False  # mude pra True se quiser logs

    # ==============================================================================
    # INICIALIZAÇÃO
    # ==============================================================================

    def __init__(
        self,
        master: tk.Misc,
        *,
        open_clientes: Optional[Callable[[], None]] = None,
        open_sifap: Optional[Callable[[], None]] = None,
        open_anvisa: Optional[Callable[[], None]] = None,
        open_farmacia_popular: Optional[Callable[[], None]] = None,
        open_sngpc: Optional[Callable[[], None]] = None,  # Corrigido: snjpc -> sngpc
        open_mod_sifap: Optional[Callable[[], None]] = None,
        open_cashflow: Optional[Callable[[], None]] = None,
        open_sites: Optional[Callable[[], None]] = None,
        **kwargs,
    ) -> None:
        """Inicializa HubScreen com menu vertical, dashboard central e notas compartilhadas."""
        # Compatibilidade kwargs
        open_clientes = (
            open_clientes or kwargs.pop("on_open_clientes", None) or open_sifap or kwargs.pop("on_open_sifap", None)
        )
        open_anvisa = open_anvisa or kwargs.pop("on_open_anvisa", None)
        open_farmacia_popular = open_farmacia_popular or kwargs.pop("on_open_farmacia_popular", None)
        open_sngpc = open_sngpc or kwargs.pop("on_open_sngpc", None) or kwargs.pop("on_open_snjpc", None)
        open_mod_sifap = open_mod_sifap or kwargs.pop("on_open_mod_sifap", None)
        open_cashflow = open_cashflow or kwargs.pop("on_open_cashflow", None)
        open_sites = open_sites or kwargs.pop("on_open_sites", None)

        # Don't pass padding to super().__init__ - CTkFrame doesn't support it
        # Use pack/grid padding instead if needed
        super().__init__(master, **kwargs)

        # MICROFASE 35: Configurar fg_color para evitar fundo cinza
        if HAS_CUSTOMTKINTER and ctk is not None:
            self.configure(fg_color=APP_BG)

        # Flag para evitar destroy duplo
        self._destroy_called = False

        # FASE 5A: ID do after para cancelar no destroy
        self._hub_build_after_id: Optional[str] = None

        # BUGFIX-UX-STARTUP-HUB-001 (C3): Instrumentação para medir custo de construção
        import os

        _debug_ui = os.getenv("RC_DEBUG_STARTUP_UI") == "1"
        if _debug_ui:
            from time import perf_counter
            from src.utils.perf import perf_mark

            _t0_hub = perf_counter()

        # Inicialização estruturada em métodos privados
        self._init_state(
            open_clientes=open_clientes,
            open_anvisa=open_anvisa,
            open_farmacia_popular=open_farmacia_popular,
            open_sngpc=open_sngpc,
            open_mod_sifap=open_mod_sifap,
            open_cashflow=open_cashflow,
            open_sites=open_sites,
        )

        if _debug_ui:
            perf_mark("Hub._init_state", _t0_hub, logger)

        # FASE 5A: Skeleton UI imediato + deferred build para não travar o paint
        self._build_skeleton_ui()
        self._hub_build_after_id = self.after(0, self._build_deferred_ui)

        if _debug_ui:
            perf_mark("Hub.__init__ skeleton", _t0_hub, logger)

    # ============================================================================
    # MÉTODOS DE INICIALIZAÇÃO (Builders Privados)
    # ============================================================================

    def _init_state(
        self,
        *,
        open_clientes: Optional[Callable[[], None]] = None,
        open_anvisa: Optional[Callable[[], None]] = None,
        open_farmacia_popular: Optional[Callable[[], None]] = None,
        open_sngpc: Optional[Callable[[], None]] = None,
        open_mod_sifap: Optional[Callable[[], None]] = None,
        open_cashflow: Optional[Callable[[], None]] = None,
        open_sites: Optional[Callable[[], None]] = None,
    ) -> None:
        """Inicializa estado interno via HubScreenBuilder (MF-22).

        MF-16: Simplificado - delega criação de componentes para HubComponentFactory.
        MF-19: Usa HubStateManager para centralizar mutações de estado.
        MF-22: Usa HubScreenBuilder para encapsular toda lógica de inicialização.
        """
        from src.modules.hub.services.hub_screen_builder import HubScreenBuilder

        # Criar builder e construir componentes
        builder = HubScreenBuilder(logger_instance=logger)
        components = builder.build(
            self,
            open_clientes=open_clientes,
            open_anvisa=open_anvisa,
            open_farmacia_popular=open_farmacia_popular,
            open_sngpc=open_sngpc,
            open_mod_sifap=open_mod_sifap,
            open_cashflow=open_cashflow,
            open_sites=open_sites,
        )

        # Injetar componentes no HubScreen
        self._dashboard_vm = components.dashboard_vm
        self._notes_vm = components.notes_vm
        self._quick_actions_vm = components.quick_actions_vm
        self._dashboard_actions = components.dashboard_actions
        self._notes_controller = components.notes_controller
        self._quick_actions_controller = components.quick_actions_controller
        self._hub_controller = components.hub_controller
        self._async = components.async_runner
        self._lifecycle_manager = components.lifecycle_manager
        self._polling_service = components.polling_service
        self._lifecycle_impl = components.lifecycle_impl
        self._navigation_helper = components.navigation_helper
        self._gateway_helper = components.gateway_helper
        self._hub_view = components.hub_view
        self._dashboard_renderer = components.dashboard_renderer
        self._notes_renderer = components.notes_renderer
        self._navigation_facade = components.navigation_facade
        self._dashboard_facade = components.dashboard_facade
        self._notes_facade = components.notes_facade  # MF-23
        self._lifecycle_facade = components.lifecycle_facade  # MF-24
        self._authors_cache_facade = components.authors_cache_facade  # MF-25

        # MF-28: _lifecycle é acessado via property, não precisa atribuição aqui
        # self._lifecycle = self._lifecycle_manager._lifecycle  # REMOVIDO - causa erro (property sem setter)

        logger.debug("HubScreen componentes criados via HubScreenBuilder (MF-22)")

    # ==============================================================================
    # CONSTRUÇÃO DE UI
    # ==============================================================================

    def _build_skeleton_ui(self) -> None:
        """FASE 5A: Cria placeholder imediato 'Carregando Hub...' para não travar o paint.

        Inicializa atributos como None para compatibilidade com código existente.
        """
        # Inicializar atributos que serão criados no deferred
        self.modules_panel: Optional[tk.Frame] = None
        self.center_spacer: Optional[tk.Frame] = None
        self.notes_panel: Optional[tk.Frame] = None
        self.dashboard_scroll: Optional[tk.Widget] = None
        self._dashboard_view: Optional[Any] = None

        # Criar placeholder simples
        if HAS_CUSTOMTKINTER and ctk:
            self._loading_placeholder = ctk.CTkLabel(
                self,
                text="Carregando Hub...",
                font=("Segoe UI", 14),
                text_color=("#666666", "#999999"),
            )
        else:
            self._loading_placeholder = tk.Label(
                self,
                text="Carregando Hub...",
                font=("Segoe UI", 14),
                fg="#666666",
                bg=APP_BG,
            )

        self._loading_placeholder.pack(expand=True)
        logger.debug("HubScreen: skeleton UI criado (placeholder)")

    def _build_deferred_ui(self) -> None:
        """FASE 5A: Constrói UI pesada após skeleton (via after 0).

        Destrói placeholder e monta módulos/dashboard/notes/layout/bindings/timers.
        Protegido contra widget já destruído (TclError).
        """
        try:
            # Verificar se widget ainda existe
            if not self.winfo_exists():
                logger.debug("HubScreen: widget destruído antes de deferred build")
                return
        except tk.TclError:
            logger.debug("HubScreen: TclError ao verificar widget em deferred build")
            return

        import os

        _debug_ui = os.getenv("RC_DEBUG_STARTUP_UI") == "1"

        if _debug_ui:
            from time import perf_counter
            from src.utils.perf import perf_mark

            _t0_deferred = perf_counter()

        try:
            # Remover placeholder
            if hasattr(self, "_loading_placeholder") and self._loading_placeholder:
                self._loading_placeholder.destroy()
                self._loading_placeholder = None

            if _debug_ui:
                _t0_qa = perf_counter()

            # BUILD MODULES PANEL (delegado para HubQuickActionsView - MF-25)
            from src.modules.hub.views.hub_quick_actions_view import HubQuickActionsView

            quick_actions_view = HubQuickActionsView(
                self,
                on_open_clientes=self.open_clientes,
                on_open_cashflow=self.open_cashflow,
                on_open_anvisa=self.open_anvisa,
                on_open_farmacia_popular=self.open_farmacia_popular,
                on_open_sngpc=self.open_sngpc,
                on_open_mod_sifap=self.open_mod_sifap,
            )
            self.modules_panel = quick_actions_view.build()

            if _debug_ui:
                perf_mark("Hub.deferred.quick_actions", _t0_qa, logger)
                _t0_dash = perf_counter()

            # BUILD DASHBOARD PANEL (delegado para HubDashboardView - MF-26)
            from src.modules.hub.views.hub_dashboard_view import HubDashboardView

            self._dashboard_view = HubDashboardView(self)
            self.center_spacer = self._dashboard_view.build()
            self.dashboard_scroll = self._dashboard_view.dashboard_scroll
            # Renderizar estado inicial de loading (evita painel em branco)
            self._dashboard_view.render_loading()

            if _debug_ui:
                perf_mark("Hub.deferred.dashboard", _t0_dash, logger)
                _t0_notes = perf_counter()

            self._build_notes_panel()

            if _debug_ui:
                perf_mark("Hub.deferred.notes_panel", _t0_notes, logger)
                _t0_layout = perf_counter()

            # SETUP LAYOUT
            widgets = {
                "modules_panel": self.modules_panel,
                "spacer": self.center_spacer,
                "notes_panel": self.notes_panel,
            }
            apply_hub_notes_right(self, widgets)

            if _debug_ui:
                perf_mark("Hub.deferred.layout", _t0_layout, logger)

            self._setup_bindings()
            self._start_timers()

            if _debug_ui:
                perf_mark("Hub.deferred TOTAL", _t0_deferred, logger)

            logger.debug("HubScreen: deferred UI build completo")

        except tk.TclError as e:
            logger.debug(f"HubScreen: TclError durante deferred build (widget destruído?): {e}")
        except Exception as e:
            logger.exception(f"HubScreen: erro durante deferred build: {e}")

    # MF-25, MF-26: Painéis de quick actions e dashboard extraídos para views dedicados

    def _build_notes_panel(self) -> None:
        """Constrói painel de notas (MVC-REFAC-001: wrapper para hub_screen_layout)."""
        from src.modules.hub.views.hub_screen_layout import build_notes_panel

        build_notes_panel(self)

    def _setup_layout(self) -> None:
        """Configura layout grid de 3 colunas (MVC-REFAC-001: wrapper para hub_screen_layout)."""
        from src.modules.hub.views.hub_screen_layout import setup_layout

        setup_layout(self)

    def _setup_bindings(self) -> None:
        """Configura atalhos de teclado (MVC-REFAC-001: wrapper para hub_screen_handlers)."""
        from src.modules.hub.views.hub_screen_handlers import setup_bindings

        setup_bindings(self)

    def _start_timers(self) -> None:
        """Inicia lifecycle do HUB (MVC-REFAC-001: wrapper para hub_screen_handlers)."""
        from src.modules.hub.views.hub_screen_handlers import start_timers

        start_timers(self)

    # ==============================================================================
    # AUXILIARES E UTILITÁRIOS
    # ==============================================================================

    def _auth_ready(self) -> bool:
        """Verifica se autenticação está pronta (MF-35: usa helper headless)."""
        try:
            app = get_app_from_widget(self)
            has_app = app is not None
            auth = getattr(app, "auth", None) if has_app else None
            has_auth = auth is not None
            is_authenticated = has_auth and bool(getattr(auth, "is_authenticated", False))
            return is_auth_ready(has_app, has_auth, is_authenticated)
        except Exception:
            return False

    def _get_org_id_safe(self) -> Optional[str]:
        """Obtém org_id de forma segura (sem exceção).

        MF-35: Wrapper fino para get_org_id_safe_from_widget (helper headless).
        """
        return get_org_id_safe_from_widget(self)

    def _get_email_safe(self) -> Optional[str]:
        """Obtém email de forma segura (sem exceção).

        MF-35: Wrapper fino para get_email_safe_from_widget (helper headless).
        """
        return get_email_safe_from_widget(self)

    def _get_user_id_safe(self) -> Optional[str]:
        """Obtém user_id de forma segura (sem exceção).

        MF-35: Wrapper fino para get_user_id_safe_from_widget (helper headless).
        """
        return get_user_id_safe_from_widget(self)

    def _start_home_timers_safely_impl(self) -> bool:
        """Inicia timers apenas quando autenticação estiver pronta.

        MF-15: Wrapper que delega para HubLifecycleImpl.start_home_timers_safely.

        Returns:
            True se auth pronta e timers iniciados, False caso contrário.
        """
        return self._lifecycle_impl.start_home_timers_safely()

    # ==============================================================================
    # DASHBOARD
    # ==============================================================================

    def _load_dashboard(self) -> None:
        """Carrega dashboard async (MF-15-D: delega para HubScreenController)."""
        self._hub_controller.load_dashboard_data_async()

    def _load_notes(self) -> None:
        """Carrega notas async (delega para HubScreenController)."""
        self._hub_controller.load_notes_data_async()

    def _update_dashboard_ui(self, state: DashboardViewState) -> None:
        """Atualiza UI do dashboard (MF-17: delega para HubDashboardRenderer)."""
        try:
            logger.debug(
                "[HubScreen._update_dashboard_ui] INICIANDO - error_message: %s, snapshot: %s",
                bool(state.error_message),
                bool(state.snapshot),
            )
            logger.debug(
                "[HubScreen._update_dashboard_ui] Renderer disponível: %s",
                self._dashboard_renderer is not None,
            )

            # MF-17: Delegar TODA a renderização para o renderer (sem lógica aqui)
            self._dashboard_renderer.render_dashboard(
                state,
                on_new_task=self._on_new_task,
                on_new_obligation=self._on_new_obligation,
                on_view_all_activity=self._on_view_all_activity,
                on_card_clients_click=self._on_card_clients_click,
                on_card_pendencias_click=self._on_card_pendencias_click,
                on_card_tarefas_click=self._on_card_tarefas_click,
            )
            logger.debug("[HubScreen._update_dashboard_ui] CONCLUÍDO")
        except Exception as e:
            logger.exception(f"[HubScreen._update_dashboard_ui] ERRO: {e}")

    def update_dashboard(self, state: DashboardViewState) -> None:
        """API pública para atualizar dashboard (MF-15-B: usado por HubScreenController)."""
        self._update_dashboard_ui(state)

    def _on_new_task(self) -> None:
        """Abre diálogo para criar nova tarefa (MF-13, MF-22: via DashboardFacade)."""
        self._dashboard_facade.on_new_task()

    def _on_new_obligation(self) -> None:
        """Abre seleção de Clientes e janela de obrigações (MF-13, MF-22: via DashboardFacade)."""
        self._dashboard_facade.on_new_obligation()

    def _on_view_all_activity(self) -> None:
        """Abre visualização completa da atividade da equipe (MF-13, MF-22: via DashboardFacade)."""
        self._dashboard_facade.on_view_all_activity()

    def _on_card_clients_click(self) -> None:
        """Handler de clique no card 'Clientes Ativos' (MF-13, MF-22: via DashboardFacade)."""
        self._dashboard_facade.on_card_clients_click()

    def _on_card_pendencias_click(self) -> None:
        """Handler de clique no card 'Pendências Regulatórias' (MF-13, MF-22: via DashboardFacade)."""
        self._dashboard_facade.on_card_pendencias_click()

    def _on_card_tarefas_click(self) -> None:
        """Handler de clique no card 'Tarefas Hoje' (MF-13, MF-22: via DashboardFacade)."""
        self._dashboard_facade.on_card_tarefas_click()

    # ==============================================================================
    # NAVEGAÇÃO (API pública)
    # ==============================================================================

    def go_to_clients(self) -> None:
        """Navega para Clientes (MF-10, MF-22: via NavigationFacade)."""
        self._navigation_facade.go_to_clients()

    def go_to_pending(self) -> None:
        """Navega para Pendências Regulatórias/Auditoria (MF-10, MF-22: via NavigationFacade)."""
        self._navigation_facade.go_to_pending()

    def go_to_tasks_today(self) -> None:
        """Abre tarefas de hoje (MF-10, MF-22: via NavigationFacade)."""
        self._navigation_facade.go_to_tasks_today()

    def open_clientes(self) -> None:
        """Abre módulo de Clientes (MF-10, MF-22: via NavigationFacade)."""
        self._navigation_facade.open_clientes()

    def open_fluxo_caixa(self) -> None:
        """Abre módulo de Fluxo de Caixa (MF-10, MF-22: via NavigationFacade)."""
        self._navigation_facade.open_fluxo_caixa()

    def open_anvisa(self) -> None:
        """Abre módulo de Anvisa (MF-10, MF-22: via NavigationFacade)."""
        self._navigation_facade.open_anvisa()

    def open_anvisa_history(self, client_id: str) -> None:
        """Abre histórico de regularizações ANVISA para um cliente específico.

        Primeiro abre a tela ANVISA, depois agenda abertura do histórico.

        Args:
            client_id: ID do cliente para abrir histórico.
        """
        # Abrir tela ANVISA primeiro
        self.open_anvisa()

        # Agendar abertura do histórico após tela renderizar
        def _deferred_open_history():
            try:
                app = get_app_from_widget(self)
                if not app:
                    logger.warning("open_anvisa_history: app não disponível")
                    return

                # Obter instância da tela ANVISA
                anvisa_screen = getattr(app, "_anvisa_screen_instance", None)
                if anvisa_screen and hasattr(anvisa_screen, "open_history_for_client"):
                    anvisa_screen.open_history_for_client(client_id)
                else:
                    logger.warning("open_anvisa_history: anvisa_screen sem método open_history_for_client")
            except Exception as e:
                logger.exception(f"Erro ao abrir histórico ANVISA: {e}")

        # after_idle + after(150ms) garante layout/geometry prontos
        self.after_idle(lambda: self.after(150, _deferred_open_history))

    def open_anvisa_history_picker(self, items: list[dict[str, Any]]) -> None:
        """Abre um seletor (modal) para escolher qual histórico ANVISA abrir.

        Usado quando há múltiplos clientes com tarefas ANVISA hoje.

        Args:
            items: Lista de items (clients_of_the_day ou pending_tasks).
        """
        try:
            from src.modules.hub.views.hub_dialogs import pick_anvisa_history_target

            choice = pick_anvisa_history_target(self, items)
            if not choice:
                return

            action, client_id = choice
            if action == "anvisa":
                self.open_anvisa()
                return
            if action == "history" and client_id:
                self.open_anvisa_history(client_id)
                return

            # Fallback seguro
            self.open_anvisa()
        except Exception as e:
            logger.exception(f"Erro ao abrir picker de histórico ANVISA: {e}")
            # Fallback seguro
            self.open_anvisa()

    def open_farmacia_popular(self) -> None:
        """Abre módulo de Farmácia Popular (MF-10, MF-22: via NavigationFacade)."""
        self._navigation_facade.open_farmacia_popular()

    def open_sngpc(self) -> None:
        """Abre módulo de Sngpc (MF-10, MF-22: via NavigationFacade)."""
        self._navigation_facade.open_sngpc()

    def open_sifap(self) -> None:
        """Abre módulo de Sifap (MF-10, MF-22: via NavigationFacade)."""
        self._navigation_facade.open_sifap()

    def open_sites(self) -> None:
        """Abre módulo de Sites (MF-10, MF-22: via NavigationFacade)."""
        self._navigation_facade.open_sites()

    # ==============================================================================
    # NOTAS (Gateway + Renderização)
    # ==============================================================================

    def show_note_editor(self, note_data: dict[str, Any] | None = None) -> dict[str, Any] | None:
        """Mostra editor de nota (MF-10: delega para HubGatewayImpl)."""
        return self._gateway_helper.show_note_editor(note_data)

    def confirm_delete_note(self, note_data: dict[str, Any]) -> bool:
        """Confirma exclusão de nota (MF-10)."""
        return self._gateway_helper.confirm_delete_note(note_data)

    def show_error(self, title: str, message: str) -> None:
        """Mostra mensagem de erro (MF-10)."""
        self._gateway_helper.show_error(title, message)

    def show_info(self, title: str, message: str) -> None:
        """Mostra mensagem informativa (MF-10)."""
        self._gateway_helper.show_info(title, message)

    def get_org_id(self) -> str | None:
        """Obtém ID da organização (MF-10)."""
        return self._gateway_helper.get_org_id()

    def get_user_email(self) -> str | None:
        """Obtém email do usuário (MF-10)."""
        return self._gateway_helper.get_user_email()

    def is_authenticated(self) -> bool:
        """Verifica se usuário está autenticado (MF-10)."""
        return self._gateway_helper.is_authenticated()

    def is_online(self) -> bool:
        """Verifica se há conexão com internet (MF-10)."""
        return self._gateway_helper.is_online()

    def _handle_client_picked_for_obligation(self, client_data: dict) -> None:
        """Callback quando cliente é selecionado (MF-13, MF-22: via DashboardFacade)."""
        self._dashboard_facade.on_client_picked_for_obligation(client_data)

    def _get_main_app(self):
        """Obtém app principal (MF-21: usa helper headless)."""
        return get_app_from_widget(self)

    def _update_notes_ui_state(self) -> None:
        """Atualiza estado do botão/placeholder baseado em org_id (MF-20, MF-23: via NotesFacade)."""
        self._notes_facade.update_notes_ui_state()

    def _start_notes_polling(self) -> None:
        """Inicia polling de notas e refresh de cache de autores (MF-14, MF-23: via NotesFacade)."""
        self._notes_facade.start_notes_polling()

    def _refresh_author_names_cache_impl(self, force: bool = False) -> None:
        """Atualiza cache de nomes de autores async (MF-14, MF-25: via AuthorsCacheFacade)."""
        self._authors_cache_facade.refresh_author_names_cache(force=force)

    def _start_live_sync_impl(self):
        """Inicia sync de notas (MF-15, MF-24: via LifecycleFacade)."""
        self._lifecycle_facade.start_live_sync_impl()

    def _stop_live_sync_impl(self):
        """Para sync (MF-15, MF-24: via LifecycleFacade)."""
        self._lifecycle_facade.stop_live_sync_impl()

    def on_show(self):
        """Chamado quando a tela fica visível (MF-24: via LifecycleFacade)."""
        self._lifecycle_facade.on_show()

    def _schedule_poll(self, delay_ms: int = 6000):
        """Agenda polling fallback (MF-14, MF-24: via LifecycleFacade)."""
        self._lifecycle_facade.schedule_poll(delay_ms=delay_ms)

    def _poll_notes_if_needed(self):
        """Polling de notas se necessário (MF-15-D, MF-23: via NotesFacade)."""
        self._notes_facade.poll_notes_if_needed()

    def _poll_notes_impl(self) -> None:
        """Implementação de polling de notas (MF-14, MF-23: via NotesFacade)."""
        self._notes_facade.poll_notes_impl(force=False)

    def _on_realtime_note(self, row: dict):
        """Handler de eventos realtime de notas (MF-15-D, MF-23: via NotesFacade)."""
        self._notes_facade.on_realtime_note(row)

    def _append_note_incremental(self, row: dict):
        """Adiciona nota incremental (MF-15-D, MF-23: via NotesFacade)."""
        self._notes_facade.append_note_incremental(row)

    # ─────────────────────────────────────────────────────────────────────────
    # Subsection: Debug e diagnóstico
    # ─────────────────────────────────────────────────────────────────────────

    def _collect_notes_debug(self) -> dict:
        """Coleta informações de debug sobre notas (MF-36, MF-23: via NotesFacade)."""
        return self._notes_facade.collect_notes_debug()

    # ─────────────────────────────────────────────────────────────────────────
    # Subsection: Renderização e formatação de notas
    # ─────────────────────────────────────────────────────────────────────────

    def render_notes(self, notes: List[Dict[str, Any]], force: bool = False) -> None:
        """Renderiza lista de notas no histórico (MF-20, MF-34, MF-23: via NotesFacade).

        Args:
            notes: Lista de dicionários com dados das notas
            force: Se True, ignora cache de hash e força re-renderização
        """
        self._notes_facade.render_notes(notes=notes, force=force)

    def refresh_notes_async(self, force: bool = False) -> None:
        """Refresh assíncrono de notas (MF-15-D, MF-23: via NotesFacade)."""
        self._notes_facade.refresh_notes_async(force=force)

    def reload_notes(self) -> None:
        """Atalho/backward-compat usado pelo NotesController para recarregar notas.

        Este método existe para compatibilidade com o NotesGatewayProtocol.
        Delega para refresh_notes_async com force=True.
        """
        self.refresh_notes_async(force=True)

    def reload_dashboard(self) -> None:
        """Força recarregamento do dashboard.

        Este método existe para compatibilidade com o NotesGatewayProtocol.
        Delega para refresh_dashboard do controller.
        """
        if self._hub_controller:
            self._hub_controller.refresh_dashboard()

    def _retry_after_table_missing(self) -> None:
        """Retry após erro de tabela ausente (MF-15-D, MF-23: via NotesFacade)."""
        self._notes_facade.retry_after_table_missing()

    def _on_add_note_clicked(self) -> None:
        """Handler para clique no botão 'Adicionar' nota (MF-23: via NotesFacade)."""
        try:
            # Obter texto da entrada
            note_text = self.new_note.get("1.0", "end-1c").strip()

            # Delegar à facade
            success, message = self._notes_facade.on_add_note(note_text)

            if success:
                # Limpar entrada
                self.new_note.delete("1.0", "end")
                # Refresh automático será feito via polling/realtime
            else:
                if message:  # Mensagens vazias já foram tratadas
                    logger.debug(f"Falha ao adicionar nota: {message}")
        except Exception as e:
            logger.exception("Erro no handler _on_add_note_clicked")
            self.show_error("Erro", f"Erro inesperado ao adicionar nota: {e}")

    def stop_polling(self) -> None:
        """Para polling e timers (MF-28, MF-19, MF-24, MF-26: via LifecycleFacade)."""
        if hasattr(self, "_lifecycle_facade") and self._lifecycle_facade is not None:
            self._lifecycle_facade.stop_polling()
        else:
            logger.warning("stop_polling chamado, mas _lifecycle_facade não disponível")

    def start_polling(self) -> None:
        """Inicia polling e timers (MF-28, MF-19, MF-24, MF-26: via LifecycleFacade)."""
        if hasattr(self, "_lifecycle_facade") and self._lifecycle_facade is not None:
            self._lifecycle_facade.start_polling()
        else:
            logger.warning("start_polling chamado, mas _lifecycle_facade não disponível")

    # ==============================================================================
    # ESTADO E LIFECYCLE
    # ==============================================================================

    @property
    def _lifecycle(self) -> HubLifecycle:
        """Acesso ao HubLifecycle interno (MF-28: compatibilidade)."""
        return self._lifecycle_manager.lifecycle

    @property
    def state(self) -> HubState:
        """Read-only access to HubState (MF-19)."""
        if not isinstance(getattr(self, "_hub_state", None), HubState):
            self._hub_state = ensure_state(self)
            # MF-19: Recriar StateManager se estado foi recriado
            if not hasattr(self, "_state_manager"):
                self._state_manager = HubStateManager(self._hub_state)
        return self._state_manager.state

    # ==============================================================================
    # STATE MANAGEMENT - MF-19 (API pública para modificar estado)
    # ==============================================================================

    def set_polling_active(self, active: bool) -> None:
        """Define polling ativo (MF-19)."""
        self._state_manager.set_polling_active(active)

    def update_notes_data(self, notes: List[Dict[str, Any]], update_snapshot: bool = True) -> None:
        """Atualiza dados de notas (MF-19)."""
        self._state_manager.update_notes_data(notes, update_snapshot)

    def set_notes_snapshot(self, snapshot: Optional[List[Tuple]]) -> None:
        """Define snapshot de notas (MF-19)."""
        self._state_manager.set_notes_snapshot(snapshot)

    def set_notes_table_missing(self, missing: bool) -> None:
        """Define estado de tabela de notas ausente (MF-19)."""
        self._state_manager.set_notes_table_missing(missing)

    def set_notes_table_missing_notified(self, notified: bool) -> None:
        """Define se erro de tabela ausente foi notificado (MF-19)."""
        self._state_manager.set_notes_table_missing_notified(notified)

    def set_names_cache_loaded(self, loaded: bool) -> None:
        """Define estado de cache de nomes carregado (MF-19, MF-25: via AuthorsCacheFacade)."""
        self._authors_cache_facade.set_names_cache_loaded(loaded)

    def clear_author_cache(self) -> None:
        """Limpa cache de autores (MF-19, MF-25: via AuthorsCacheFacade)."""
        self._authors_cache_facade.clear_author_cache()

    def add_pending_name_fetch(self, email: str) -> None:
        """Adiciona email ao set de fetches pendentes (MF-19, MF-25: via AuthorsCacheFacade)."""
        self._authors_cache_facade.add_pending_name_fetch(email)

    def remove_pending_name_fetch(self, email: str) -> None:
        """Remove email do set de fetches pendentes (MF-19, MF-25: via AuthorsCacheFacade)."""
        self._authors_cache_facade.remove_pending_name_fetch(email)

    def clear_pending_name_fetch(self) -> None:
        """Limpa todos os fetches pendentes (MF-19)."""
        self._state_manager.clear_pending_name_fetch()

    def update_live_last_ts(self, timestamp: str) -> None:
        """Atualiza timestamp da última nota (live sync) (MF-19)."""
        self._state_manager.update_live_last_ts(timestamp)

    def set_live_last_ts(self, timestamp: Optional[str]) -> None:
        """Define timestamp da última nota (live sync) (MF-19)."""
        self._state_manager.set_live_last_ts(timestamp)

    # ==============================================================================
    # LEGACY STATE PROPERTIES (retrocompatibilidade)
    # ==============================================================================

    @property
    def _author_tags(self):
        s = ensure_state(self)
        if s.author_tags is None:
            s.author_tags = {}
        return s.author_tags

    @_author_tags.setter
    def _author_tags(self, value):
        # MF-19: Usa StateManager para mutações
        self._state_manager.set_author_tags(value or {})

    @property
    def _poll_job(self):
        return ensure_state(self).poll_job

    @_poll_job.setter
    def _poll_job(self, value):
        # MF-19: Usa StateManager para mutações
        self._state_manager.set_poll_job(value)

    @property
    def _is_refreshing(self):
        return ensure_state(self).is_refreshing

    @_is_refreshing.setter
    def _is_refreshing(self, value):
        # MF-19: Usa StateManager para mutações
        self._state_manager.set_refreshing(bool(value))

    def hub_state(self) -> HubState:
        """Convenience accessor for the HubState container."""
        return self.state

    def destroy(self) -> None:
        """Override destroy para parar lifecycle e polling (MF-26: com proteção duplo)."""
        # Verificar se widget ainda existe e não foi destruído
        if self._destroy_called:
            return

        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return

        # Marcar como destruído
        self._destroy_called = True

        # FASE 5A: Cancelar deferred build se ainda não executou
        if hasattr(self, "_hub_build_after_id") and self._hub_build_after_id is not None:
            try:
                self.after_cancel(self._hub_build_after_id)
                logger.debug("HubScreen.destroy: deferred build cancelado")
            except (tk.TclError, Exception) as e:
                logger.debug(f"HubScreen.destroy: erro ao cancelar deferred build: {e}")
            self._hub_build_after_id = None

        try:
            # Parar lifecycle interno (compatibilidade)
            if hasattr(self, "_lifecycle") and self._lifecycle is not None:
                self._lifecycle.stop()
        except Exception as e:
            logger.debug(f"Erro ao parar _lifecycle no destroy: {e}")

        try:
            # Parar polling via facade (MF-24)
            self.stop_polling()
        except Exception as e:
            logger.debug(f"Erro ao parar polling no destroy: {e}")

        # FASE 5A: Encerrar HubAsyncRunner antes de destruir widget
        try:
            if hasattr(self, "_async") and self._async is not None:
                self._async.shutdown()
                logger.debug("HubScreen.destroy: _async.shutdown() chamado")
        except Exception as e:
            logger.debug(f"Erro ao encerrar _async no destroy: {e}")

        try:
            super().destroy()
        except Exception as e:
            logger.debug(f"Erro ao chamar super().destroy(): {e}")

    # ==============================================================================
    # COMPATIBILIDADE (aliases para métodos legados)
    # ==============================================================================

    def _start_live_sync(self):
        """Alias de compatibilidade para _start_live_sync_impl (MF-24: via LifecycleFacade)."""
        return self._lifecycle_facade.start_live_sync()

    def _refresh_author_names_cache_async(self, force: bool = False):
        """Alias de compatibilidade para _refresh_author_names_cache_impl."""
        return self._refresh_author_names_cache_impl(force=force)

    # ==============================================================================
    # DEBUG E DIAGNÓSTICO
    # ==============================================================================

    def _show_debug_info(self, event=None) -> None:
        """Gera relatório JSON de diagnóstico (atalho Ctrl+D)."""
        show_debug_info(
            parent=self,
            collect_debug_data=self._collect_notes_debug,
        )
