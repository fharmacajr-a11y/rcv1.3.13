# -*- coding: utf-8 -*-
"""Tela Hub: menu vertical + bloco de notas compartilhado (append-only via Supabase)."""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from tkinter import messagebox, TclError
from typing import Any, Callable, Dict, List, Optional

import ttkbootstrap as tb

try:
    from src.core.logger import get_logger
except Exception:
    import logging

    def get_logger(name: str = __name__):
        return logging.getLogger(name)


from src.modules.hub.actions import on_show as actions_on_show
from src.modules.hub.authors import _author_display_name, _debug_resolve_author
from src.modules.hub.colors import _ensure_author_tag
from src.modules.hub.constants import (
    HUB_BTN_STYLE_AUDITORIA,
    HUB_BTN_STYLE_CLIENTES,
    HUB_BTN_STYLE_FLUXO_CAIXA,
    HUB_BTN_STYLE_SENHAS,
    MODULES_TITLE,
    PAD_OUTER,
)
from src.modules.hub.controller import append_note_incremental as controller_append_note_incremental
from src.modules.hub.controller import cancel_poll as controller_cancel_poll
from src.modules.hub.controller import on_realtime_note as controller_on_realtime_note
from src.modules.hub.controller import poll_notes_if_needed as controller_poll_notes_if_needed
from src.modules.hub.controller import refresh_notes_async as controller_refresh_notes_async
from src.modules.hub.controller import retry_after_table_missing as controller_retry_after_table_missing
from src.modules.hub.controller import schedule_poll as controller_schedule_poll
from src.modules.hub.layout import apply_hub_notes_right
from src.modules.hub.viewmodels import DashboardViewModel, NotesViewModel
from src.modules.hub.controllers import DashboardActionController, NotesController
from src.modules.hub.panels import build_notes_panel
from src.modules.hub.state import HubState
from src.modules.hub.views.dashboard_center import build_dashboard_center, build_dashboard_error
from src.modules.hub.state import ensure_hub_state as ensure_state
from src.modules.hub.utils import _normalize_note
from src.modules.hub.views.hub_screen_helpers import (
    calculate_module_button_style,
    calculate_notes_content_hash,
    calculate_notes_ui_state,
    format_note_line,
    format_timestamp,
    is_auth_ready,
    should_skip_refresh_by_cooldown,
    should_skip_render_empty_notes,
)

logger = get_logger(__name__)
log = logger

# Import do erro transitório
# Timezone handling com fallback (mantido para compatibilidade)
try:
    import tzlocal  # type: ignore[import-not-found]

    LOCAL_TZ = tzlocal.get_localzone()
except Exception:
    # Fallback: usa tzinfo do sistema
    try:
        LOCAL_TZ = datetime.now().astimezone().tzinfo
    except Exception:
        LOCAL_TZ = timezone.utc

# logger disponível desde o topo do módulo

# Constantes para retry de autenticação
AUTH_RETRY_MS = 2000  # 2 segundos

# Mapa de e-mail -> nome curto preferido (sempre em minúsculas)
# Cooldown para refresh de nomes (evitar chamadas duplicadas)
_NAMES_REFRESH_COOLDOWN_S = 30


class HubScreen(tb.Frame):
    """
    Hub: menu vertical à esquerda + bloco de notas à direita.
    Sem conteúdo central. Sem painel de login/status (a StatusBar global já existe).
    """

    DEBUG_NOTES = False  # mude pra True se quiser logs

    def _dlog(self, tag, **kw):
        if not getattr(self, "DEBUG_NOTES", self.DEBUG_NOTES):
            return
        try:
            import json
            import time

            line = {"t": int(time.time() * 1000), "tag": tag, **kw}
            logger.info("[HUB] %s", json.dumps(line, ensure_ascii=False))
        except Exception as exc:  # noqa: BLE001
            logger.debug("[HUB] Falha ao logar debug de notas: %s", exc)

    def __init__(
        self,
        master,
        *,
        open_clientes: Optional[Callable[[], None]] = None,
        open_sifap: Optional[Callable[[], None]] = None,
        open_anvisa: Optional[Callable[[], None]] = None,
        open_auditoria: Optional[Callable[[], None]] = None,
        open_farmacia_popular: Optional[Callable[[], None]] = None,
        open_sngpc: Optional[Callable[[], None]] = None,  # Corrigido: snjpc -> sngpc
        open_senhas: Optional[Callable[[], None]] = None,
        open_mod_sifap: Optional[Callable[[], None]] = None,
        open_cashflow: Optional[Callable[[], None]] = None,
        open_sites: Optional[Callable[[], None]] = None,
        **kwargs,
    ) -> None:
        """Inicializa a tela HubScreen com menu vertical, dashboard central e notas compartilhadas.

        A inicialização é dividida em etapas organizadas para melhor legibilidade:
        1. Configuração de estado inicial (callbacks, atributos, HubState)
        2. Construção dos painéis de UI (módulos, dashboard, notas)
        3. Setup de layout (grid 3 colunas)
        4. Configuração de bindings (atalhos de teclado)
        5. Início de timers (polling, dashboard, live sync)
        """
        # Compatibilidade com kwargs antigos (mantém snjpc para retrocompatibilidade)
        open_clientes = (
            open_clientes or kwargs.pop("on_open_clientes", None) or open_sifap or kwargs.pop("on_open_sifap", None)
        )
        open_anvisa = open_anvisa or kwargs.pop("on_open_anvisa", None)
        open_auditoria = open_auditoria or kwargs.pop("on_open_auditoria", None)
        open_farmacia_popular = open_farmacia_popular or kwargs.pop("on_open_farmacia_popular", None)
        open_sngpc = open_sngpc or kwargs.pop("on_open_sngpc", None) or kwargs.pop("on_open_snjpc", None)
        open_senhas = open_senhas or kwargs.pop("on_open_passwords", None) or kwargs.pop("on_open_senhas", None)
        open_mod_sifap = open_mod_sifap or kwargs.pop("on_open_mod_sifap", None)
        open_cashflow = open_cashflow or kwargs.pop("on_open_cashflow", None)
        open_sites = open_sites or kwargs.pop("on_open_sites", None)

        super().__init__(master, padding=0, **kwargs)

        # Inicialização estruturada em métodos privados
        self._init_state(
            open_clientes=open_clientes,
            open_anvisa=open_anvisa,
            open_auditoria=open_auditoria,
            open_farmacia_popular=open_farmacia_popular,
            open_sngpc=open_sngpc,
            open_senhas=open_senhas,
            open_mod_sifap=open_mod_sifap,
            open_cashflow=open_cashflow,
            open_sites=open_sites,
        )
        self._build_modules_panel()
        self._build_dashboard_panel()
        self._build_notes_panel()
        self._setup_layout()
        self._setup_bindings()
        self._start_timers()

    # ============================================================================
    # MÉTODOS DE INICIALIZAÇÃO (Builders Privados)
    # ============================================================================

    def _init_state(
        self,
        *,
        open_clientes: Optional[Callable[[], None]] = None,
        open_anvisa: Optional[Callable[[], None]] = None,
        open_auditoria: Optional[Callable[[], None]] = None,
        open_farmacia_popular: Optional[Callable[[], None]] = None,
        open_sngpc: Optional[Callable[[], None]] = None,
        open_senhas: Optional[Callable[[], None]] = None,
        open_mod_sifap: Optional[Callable[[], None]] = None,
        open_cashflow: Optional[Callable[[], None]] = None,
        open_sites: Optional[Callable[[], None]] = None,
    ) -> None:
        """Inicializa estado interno: HubState, callbacks, atributos de polling/cache."""
        self.AUTH_RETRY_MS = AUTH_RETRY_MS
        s = ensure_state(self)
        s.auth_retry_ms = AUTH_RETRY_MS
        self._hub_state: HubState = s

        # Armazenar callbacks de navegação
        self.open_clientes = open_clientes
        self.open_anvisa = open_anvisa
        self.open_auditoria = open_auditoria
        self.open_farmacia_popular = open_farmacia_popular
        self.open_sngpc = open_sngpc
        self.open_senhas = open_senhas
        self.open_mod_sifap = open_mod_sifap
        self.open_cashflow = open_cashflow
        self.open_sites = open_sites

        # Estado de polling
        self._notes_poll_ms = 10000  # 10 segundos
        self._notes_last_snapshot: Optional[List[tuple]] = None  # snapshot (id, ts) para detectar mudanças
        self._notes_last_data: Optional[List[Dict[str, Any]]] = None  # dados completos normalizados
        self._polling_active = False
        self._notes_after_handle = None
        self._clients_after_handle = None

        # Estado de erro de tabela ausente
        self._notes_table_missing = False
        self._notes_table_missing_notified = False
        self._notes_retry_ms = 60000  # 60 segundos antes de tentar novamente

        # Cache de nomes de autores (email lowercase -> display_name)
        self._author_names_cache: Dict[str, str] = {}
        self._email_prefix_map: Dict[str, str] = {}  # {prefixo: email_completo} para notas legadas
        self._names_cache_loaded = False
        self._names_refreshing = False
        self._names_last_refresh = 0.0
        self._last_org_for_names: Optional[str] = None
        self._pending_name_fetch: set = set()  # controle de fetch on-demand
        # Debounce de re-render
        self._last_names_cache_hash = None  # md5 do cache de nomes
        self._last_render_hash = None  # md5 do conteúdo renderizado
        self._names_cache_loading = False  # trava anti reentrância

        # Live sync
        self._live_channel = None
        self._live_org_id = None
        self._live_sync_on = False
        self._live_last_ts = None  # ISO da última nota conhecida

        # Dashboard ViewModel
        self._dashboard_vm = DashboardViewModel()

        # Dashboard Action Controller (headless)
        # Usa self como navigator adapter (implementa HubNavigatorProtocol)
        self._dashboard_actions = DashboardActionController(navigator=self, logger=logger)

        # Notes ViewModel
        try:
            from src.modules.notas.service import NotesService

            notes_service = NotesService()
        except Exception:
            notes_service = None
        self._notes_vm = NotesViewModel(notes_service=notes_service)

        # Notes Controller (headless)
        # Usa self como gateway adapter (implementa NotesGatewayProtocol)
        self._notes_controller = NotesController(
            vm=self._notes_vm,
            gateway=self,
            notes_service=notes_service,
            logger=logger,
        )

    def _build_modules_panel(self) -> None:
        """Constrói o painel de módulos (menu vertical à esquerda) com 3 blocos."""
        self.modules_panel = tb.Labelframe(self, text=MODULES_TITLE, padding=PAD_OUTER)
        modules_panel = self.modules_panel

        def mk_btn(
            parent_frame: tb.Frame,
            text: str,
            cmd: Optional[Callable] = None,
            highlight: bool = False,
            yellow: bool = False,
            bootstyle: Optional[str] = None,
        ) -> tb.Button:
            """Cria um botão com estilo consistente no painel de módulos."""
            style = calculate_module_button_style(
                highlight=highlight,
                yellow=yellow,
                bootstyle=bootstyle,
            )

            b = tb.Button(
                parent_frame,
                text=text,
                command=(cmd or self._noop),
                bootstyle=style,
            )
            # Não faz pack/grid aqui; o caller posiciona
            return b

        # --- Bloco 1: Cadastros / Acesso ---
        frame_cadastros = tb.Labelframe(modules_panel, text="Cadastros / Acesso", bootstyle="dark", padding=(8, 6))
        frame_cadastros.pack(fill="x", pady=(0, 8))
        frame_cadastros.columnconfigure(0, weight=1)
        frame_cadastros.columnconfigure(1, weight=1)

        btn_clientes = mk_btn(frame_cadastros, "Clientes", self.open_clientes, bootstyle=HUB_BTN_STYLE_CLIENTES)
        btn_clientes.grid(row=0, column=0, sticky="ew", padx=3, pady=3)

        btn_senhas = mk_btn(frame_cadastros, "Senhas", self.open_senhas, bootstyle=HUB_BTN_STYLE_SENHAS)
        btn_senhas.grid(row=0, column=1, sticky="ew", padx=3, pady=3)

        # --- Bloco 2: Gestão / Auditoria ---
        frame_gestao = tb.Labelframe(modules_panel, text="Gestão / Auditoria", bootstyle="dark", padding=(8, 6))
        frame_gestao.pack(fill="x", pady=(0, 8))
        frame_gestao.columnconfigure(0, weight=1)
        frame_gestao.columnconfigure(1, weight=1)

        btn_auditoria = mk_btn(frame_gestao, "Auditoria", self.open_auditoria, bootstyle=HUB_BTN_STYLE_AUDITORIA)
        btn_auditoria.grid(row=0, column=0, sticky="ew", padx=3, pady=3)

        # --- Fluxo de Caixa ---
        if getattr(self, "open_cashflow", None):
            btn_fluxo_caixa = mk_btn(
                frame_gestao, "Fluxo de Caixa", self.open_cashflow, bootstyle=HUB_BTN_STYLE_FLUXO_CAIXA
            )
        else:
            btn_fluxo_caixa = mk_btn(frame_gestao, "Fluxo de Caixa", None, bootstyle=HUB_BTN_STYLE_FLUXO_CAIXA)
            btn_fluxo_caixa.configure(state="disabled")
        btn_fluxo_caixa.grid(row=0, column=1, sticky="ew", padx=3, pady=3)

        # --- Bloco 3: Regulatório / Programas ---
        frame_regulatorio = tb.Labelframe(
            modules_panel, text="Regulatório / Programas", bootstyle="dark", padding=(8, 6)
        )
        frame_regulatorio.pack(fill="x", pady=(0, 0))
        frame_regulatorio.columnconfigure(0, weight=1)
        frame_regulatorio.columnconfigure(1, weight=1)

        btn_anvisa = mk_btn(frame_regulatorio, "Anvisa", self.open_anvisa, bootstyle="secondary")
        btn_anvisa.grid(row=0, column=0, sticky="ew", padx=3, pady=3)

        btn_farmacia_pop = mk_btn(
            frame_regulatorio, "Farmácia Popular", self.open_farmacia_popular, bootstyle="secondary"
        )
        btn_farmacia_pop.grid(row=0, column=1, sticky="ew", padx=3, pady=3)

        btn_sngpc = mk_btn(frame_regulatorio, "Sngpc", self.open_sngpc, bootstyle="secondary")
        btn_sngpc.grid(row=1, column=0, sticky="ew", padx=3, pady=3)

        btn_sifap = mk_btn(frame_regulatorio, "Sifap", self.open_mod_sifap, bootstyle="secondary")
        btn_sifap.grid(row=1, column=1, sticky="ew", padx=3, pady=3)

    def _build_dashboard_panel(self) -> None:
        """Constrói o painel central com ScrollableFrame para o dashboard."""
        # Container da coluna central
        self.center_spacer = tb.Frame(self)

        # ScrollableFrame dentro do container para permitir scroll do dashboard
        from src.ui.widgets.scrollable_frame import ScrollableFrame

        self.dashboard_scroll = ScrollableFrame(self.center_spacer)
        self.dashboard_scroll.pack(fill="both", expand=True)

    def _build_notes_panel(self) -> None:
        """Constrói o painel de notas compartilhadas (lateral direita)."""
        self.notes_panel = build_notes_panel(self, parent=self)

    def _setup_layout(self) -> None:
        """Configura o layout grid de 3 colunas (módulos | dashboard | notas)."""
        widgets = {
            "modules_panel": self.modules_panel,
            "spacer": self.center_spacer,
            "notes_panel": self.notes_panel,
        }
        apply_hub_notes_right(self, widgets)

    def _setup_bindings(self) -> None:
        """Configura atalhos de teclado (Ctrl+D para diagnóstico, Ctrl+L para reload cache)."""
        # Configurar atalhos (apenas uma vez)
        self._binds_ready = getattr(self, "_binds_ready", False)
        if not self._binds_ready:
            # Ctrl+D para diagnóstico
            self.bind_all("<Control-d>", self._show_debug_info)
            self.bind_all("<Control-D>", self._show_debug_info)

            # Ctrl+L para recarregar cache de nomes (teste)
            self.bind_all(
                "<Control-l>",
                lambda e: self._refresh_author_names_cache_async(force=True),
            )
            self.bind_all(
                "<Control-L>",
                lambda e: self._refresh_author_names_cache_async(force=True),
            )
            self._binds_ready = True

    def _start_timers(self) -> None:
        """Inicia timers de polling (notas) e carregamento de dashboard."""
        # Iniciar timers com gate de autenticação
        self.after(500, self._start_home_timers_safely)

        # Carregar dashboard no centro
        self.after(600, self._load_dashboard)

    # ============================================================================
    # MÉTODOS AUXILIARES E CALLBACKS
    # ============================================================================

    def _auth_ready(self) -> bool:
        """Verifica se autenticação está pronta (sem levantar exceção)."""
        try:
            app = self._get_app()
            has_app = app is not None
            auth = getattr(app, "auth", None) if has_app else None
            has_auth = auth is not None
            is_authenticated = has_auth and bool(getattr(auth, "is_authenticated", False))
            return is_auth_ready(has_app, has_auth, is_authenticated)
        except Exception:
            return False

    def _get_org_id_safe(self) -> Optional[str]:
        """Obtém org_id de forma segura (sem exceção)."""
        try:
            app = self._get_app()
            if not app or not hasattr(app, "auth") or not app.auth:
                return None

            auth = app.auth  # guarda local para satisfazer narrowing do Pyright
            # Tentar via accessor seguro
            org_id = auth.get_org_id()
            if org_id:
                return org_id

            # Fallback: usar método antigo se disponível
            if hasattr(app, "_get_org_id_cached"):
                user_id = auth.get_user_id()
                if user_id:
                    return app._get_org_id_cached(user_id)

            return None
        except Exception as e:
            log.debug("Não foi possível obter org_id: %s", e)
            return None

    def _get_email_safe(self) -> Optional[str]:
        """Obtém email de forma segura (sem exceção)."""
        try:
            app = self._get_app()
            if not app or not hasattr(app, "auth") or not app.auth:
                return None
            return app.auth.get_email()
        except Exception as e:
            log.debug("Não foi possível obter email: %s", e)
            return None

    def _get_user_id_safe(self) -> Optional[str]:
        """Obtém user_id de forma segura (sem exceção)."""
        try:
            app = self._get_app()
            if not app or not hasattr(app, "auth") or not app.auth:
                return None
            return app.auth.get_user_id()
        except Exception as e:
            log.debug("Não foi possível obter user_id: %s", e)
            return None

    def _start_home_timers_safely(self) -> None:
        """Inicia timers apenas quando autenticação estiver pronta."""
        if not self._auth_ready():
            log.debug("HubScreen: Autenticação ainda não pronta, aguardando...")
            self.after(AUTH_RETRY_MS, self._start_home_timers_safely)
            return

        log.debug("HubScreen: Autenticação pronta, iniciando timers.")

        # Forçar recarga do cache de nomes ao trocar de conta/login
        self._names_cache_loaded = False
        self._author_names_cache = {}
        self._email_prefix_map = {}  # limpar mapa de prefixos também
        self._last_org_for_names = None  # força recarga mesmo se org for igual

        self._update_notes_ui_state()  # Atualizar estado do botão/placeholder
        self._start_notes_polling()

    def _load_dashboard(self) -> None:
        """Carrega os dados do dashboard de forma assíncrona via ViewModel.

        Obtém o org_id atual, usa o DashboardViewModel para buscar snapshot
        em uma thread separada (para não travar a UI), e atualiza o painel
        central quando pronto.
        """
        org_id = self._get_org_id_safe()
        if not org_id:
            log.debug("HubScreen: org_id não disponível, aguardando para carregar dashboard...")
            # Reagendar se auth ainda não está pronta
            if not self._auth_ready():
                self.after(AUTH_RETRY_MS, self._load_dashboard)
            return

        def _fetch_via_viewmodel():
            """Thread worker para buscar snapshot via ViewModel."""
            # Usar ViewModel para carregar (headless, sem Tkinter)
            state = self._dashboard_vm.load(org_id=org_id, today=None)

            # Agendar atualização da UI na thread principal
            self.after(0, lambda: self._update_dashboard_ui(state))

        # Executar em thread separada para não bloquear a UI
        threading.Thread(target=_fetch_via_viewmodel, daemon=True).start()

    def _update_dashboard_ui(self, state: "DashboardViewState") -> None:
        """Atualiza a UI do dashboard baseado no estado do ViewModel.

        Args:
            state: Estado do DashboardViewModel com snapshot e cards formatados.
        """

        # Se houver erro, mostrar tela de erro
        if state.error_message:
            log.error("Dashboard em estado de erro: %s", state.error_message)
            build_dashboard_error(self.dashboard_scroll.content)
            return

        # Se não houver snapshot, não fazer nada (estado inválido)
        if not state.snapshot:
            log.warning("Dashboard sem snapshot disponível")
            return

        # Renderizar dashboard com state completo (ViewModel driving UI)
        build_dashboard_center(
            self.dashboard_scroll.content,
            state,  # ← Passa DashboardViewState completo, não apenas snapshot
            on_new_task=self._on_new_task,
            on_new_obligation=self._on_new_obligation,
            on_view_all_activity=self._on_view_all_activity,
            on_card_clients_click=self._on_card_clients_click,
            on_card_pendencias_click=self._on_card_pendencias_click,
            on_card_tarefas_click=self._on_card_tarefas_click,
        )

    def _on_new_task(self) -> None:
        """Abre diálogo para criar nova tarefa."""
        try:
            # Obter org_id e user_id
            org_id = self._get_org_id_safe()
            user_id = self._get_user_id_safe()

            if not org_id or not user_id:
                messagebox.showwarning(
                    "Autenticação Necessária",
                    "Por favor, faça login para criar tarefas.",
                    parent=self,
                )
                return

            # Carregar lista de clientes
            clients: list = []
            try:
                from data.supabase_repo import list_clients_for_picker

                clients = list_clients_for_picker(org_id, limit=500)
            except Exception as e:  # noqa: BLE001
                log.warning("Não foi possível carregar clientes: %s", e)

            # Abrir diálogo
            from src.modules.tasks.views import NovaTarefaDialog

            dialog = NovaTarefaDialog(
                parent=self,
                org_id=org_id,
                user_id=user_id,
                on_success=self._load_dashboard,
                clients=clients,
            )
            dialog.deiconify()  # Mostra a janela

        except Exception as e:  # noqa: BLE001
            log.exception("Erro ao abrir diálogo de nova tarefa")
            messagebox.showerror(
                "Erro",
                f"Erro ao abrir diálogo: {e}",
                parent=self,
            )

    def _on_new_obligation(self) -> None:
        """Abre modo seleção de Clientes e depois janela de obrigações do cliente selecionado."""
        try:
            # Obter org_id e user_id
            org_id = self._get_org_id_safe()
            user_id = self._get_user_id_safe()

            if not org_id or not user_id:
                messagebox.showwarning(
                    "Autenticação Necessária",
                    "Por favor, faça login para criar obrigações.",
                    parent=self,
                )
                return

            # Salvar IDs para uso no callback
            self._pending_obligation_org_id = org_id
            self._pending_obligation_user_id = user_id

            # Abrir modo seleção de Clientes usando API explícita
            app = self._get_main_app()
            if not app:
                messagebox.showwarning(
                    "Erro",
                    "Aplicação principal não encontrada.",
                    parent=self,
                )
                return

            from src.modules.main_window.controller import start_client_pick_mode, navigate_to

            # Usar nova API com callback específico para Obrigações
            start_client_pick_mode(
                app,
                on_client_picked=self._handle_client_picked_for_obligation,
                banner_text="🔍 Modo seleção: escolha um cliente para gerenciar obrigações",
                return_to=lambda: navigate_to(app, "hub"),
            )

        except Exception as e:  # noqa: BLE001
            log.exception("Erro ao iniciar fluxo de nova obrigação")
            messagebox.showerror(
                "Erro",
                f"Erro ao iniciar fluxo: {e}",
                parent=self,
            )

    def _on_view_all_activity(self) -> None:
        """Abre visualização completa da atividade da equipe."""
        try:
            messagebox.showinfo(
                "Em Desenvolvimento",
                "A visualização completa da atividade estará disponível em breve.\n\n"
                "No momento, você pode ver as últimas atividades diretamente no Hub.",
                parent=self,
            )
        except Exception as e:  # noqa: BLE001
            log.exception("Erro ao abrir visualização de atividades")
            messagebox.showerror(
                "Erro",
                f"Erro ao abrir visualização: {e}",
                parent=self,
            )

    def _on_card_clients_click(self) -> None:
        """Handler de clique no card 'Clientes Ativos' - delega para controller."""
        try:
            state = self._dashboard_vm.state
            self._dashboard_actions.handle_clients_card_click(state)
        except Exception as e:  # noqa: BLE001
            log.exception("Erro ao navegar para Clientes a partir do card")
            messagebox.showerror(
                "Erro",
                f"Erro ao abrir tela de Clientes: {e}",
                parent=self,
            )

    def _on_card_pendencias_click(self) -> None:
        """Handler de clique no card 'Pendências Regulatórias' - delega para controller."""
        try:
            state = self._dashboard_vm.state
            self._dashboard_actions.handle_pending_card_click(state)
        except Exception as e:  # noqa: BLE001
            log.exception("Erro ao navegar para Auditoria a partir do card")
            messagebox.showerror(
                "Erro",
                f"Erro ao abrir tela de Auditoria: {e}",
                parent=self,
            )

    def _on_card_tarefas_click(self) -> None:
        """Handler de clique no card 'Tarefas Hoje' - delega para controller."""
        try:
            state = self._dashboard_vm.state
            self._dashboard_actions.handle_tasks_today_card_click(state)
        except Exception as e:  # noqa: BLE001
            log.exception("Erro ao abrir tarefas a partir do card")
            messagebox.showerror(
                "Erro",
                f"Erro ao abrir tarefas: {e}",
                parent=self,
            )

    # ============================================================================
    # MÉTODOS DE NAVEGAÇÃO (HubNavigatorProtocol)
    # ============================================================================

    def go_to_clients(self) -> None:
        """Navega para a tela de Clientes (implementa HubNavigatorProtocol)."""
        if self.open_clientes:
            self.open_clientes()
        else:
            log.debug("HubScreen: Callback open_clientes não definido")

    def go_to_pending(self) -> None:
        """Navega para a tela de Pendências Regulatórias/Auditoria (implementa HubNavigatorProtocol)."""
        if self.open_auditoria:
            self.open_auditoria()
        else:
            log.debug("HubScreen: Callback open_auditoria não definido")

    def go_to_tasks_today(self) -> None:
        """Abre interface de tarefas de hoje (implementa HubNavigatorProtocol)."""
        # Por enquanto, abre o diálogo de nova tarefa (mesma ação do botão ➕)
        # No futuro, pode abrir uma visualização filtrada de tarefas pendentes
        self._on_new_task()

    # ============================================================================
    # MÉTODOS DE GATEWAY NOTES (NotesGatewayProtocol)
    # ============================================================================

    def show_note_editor(self, note_data: dict[str, Any] | None = None) -> dict[str, Any] | None:
        """Mostra editor de nota (NotesGatewayProtocol).

        Args:
            note_data: Dados da nota para editar (None para criar nova).

        Returns:
            Dados da nota editada/criada, ou None se cancelado.
        """
        # TODO: Implementar dialog de edição quando necessário
        logger.debug("show_note_editor não implementado ainda")
        return None

    def confirm_delete_note(self, note_data: dict[str, Any]) -> bool:
        """Confirma exclusão de nota (NotesGatewayProtocol).

        Args:
            note_data: Dados da nota a ser deletada.

        Returns:
            True se confirmado, False se cancelado.
        """
        body = note_data.get("body", "")
        preview = body[:50] + "..." if len(body) > 50 else body
        return messagebox.askyesno(
            "Confirmar exclusão",
            f"Excluir anotação:\n\n{preview}",
            parent=self,
        )

    def show_error(self, title: str, message: str) -> None:
        """Mostra mensagem de erro (NotesGatewayProtocol)."""
        messagebox.showerror(title, message, parent=self)

    def show_info(self, title: str, message: str) -> None:
        """Mostra mensagem informativa (NotesGatewayProtocol)."""
        messagebox.showinfo(title, message, parent=self)

    def get_org_id(self) -> str | None:
        """Obtém ID da organização atual (NotesGatewayProtocol)."""
        try:
            from src.data.supabase_repo import SupabaseClientManager

            repo = SupabaseClientManager.get_instance()
            return repo.org_id if repo else None
        except Exception:
            return None

    def get_user_email(self) -> str | None:
        """Obtém email do usuário atual (NotesGatewayProtocol)."""
        try:
            from src.data.supabase_repo import SupabaseClientManager

            repo = SupabaseClientManager.get_instance()
            session = repo.get_session() if repo else None
            return session.user.email if session and session.user else None
        except Exception:
            return None

    def is_authenticated(self) -> bool:
        """Verifica se usuário está autenticado (NotesGatewayProtocol)."""
        try:
            from src.data.supabase_repo import SupabaseClientManager

            repo = SupabaseClientManager.get_instance()
            session = repo.get_session() if repo else None
            return bool(session and session.user)
        except Exception:
            return False

    def is_online(self) -> bool:
        """Verifica se há conexão com internet (NotesGatewayProtocol)."""
        # Simplificação: verifica se está autenticado (implica online)
        # Poderia ter validação de conectividade mais sofisticada
        return self.is_authenticated()

    # ============================================================================
    # HANDLERS DE CALLBACKS DE CLIENTES
    # ============================================================================

    def _handle_client_picked_for_obligation(self, client_data: dict) -> None:
        """Callback chamado quando cliente é selecionado no modo pick."""
        try:
            org_id = getattr(self, "_pending_obligation_org_id", None)
            user_id = getattr(self, "_pending_obligation_user_id", None)

            if not org_id or not user_id:
                log.warning("org_id ou user_id não disponível no callback de obrigações")
                return

            # Extrair dados do cliente
            client_id = client_data.get("id")
            if not client_id:
                log.warning("Client data sem ID: %s", client_data)
                return

            # Converter para int se necessário
            if isinstance(client_id, str):
                try:
                    client_id = int(client_id)
                except ValueError:
                    log.error("Não foi possível converter client_id '%s' para int", client_id)
                    return

            # Montar nome do cliente para exibição
            client_name = client_data.get("razao_social") or client_data.get("nome") or f"Cliente {client_id}"

            # Abrir janela de obrigações
            from src.modules.clientes.views.client_obligations_window import show_client_obligations_window

            # Voltar para o Hub primeiro
            app = self._get_main_app()
            if app:
                from src.modules.main_window.controller import navigate_to

                navigate_to(app, "hub")

            # Depois abrir janela de obrigações
            show_client_obligations_window(
                parent=self.winfo_toplevel(),
                org_id=org_id,
                created_by=user_id,
                client_id=client_id,
                client_name=client_name,
                on_refresh_hub=self._load_dashboard,
            )

        except Exception as e:  # noqa: BLE001
            log.exception("Erro ao processar cliente selecionado para obrigações")
            messagebox.showerror(
                "Erro",
                f"Erro ao processar seleção: {e}",
                parent=self,
            )

    def _get_main_app(self):
        """Obtém referência ao app principal navegando pela hierarquia de widgets."""
        widget = self.master
        while widget:
            if hasattr(widget, "show_frame") and hasattr(widget, "_main_frame_ref"):
                return widget
            widget = getattr(widget, "master", None)
        return None

    def _update_notes_ui_state(self) -> None:
        """Atualiza estado do botão e placeholder baseado em org_id."""
        org_id = self._get_org_id_safe()
        state = calculate_notes_ui_state(has_org_id=bool(org_id))

        # Aplicar estado ao botão
        btn_state = "normal" if state["button_enabled"] else "disabled"
        self.btn_add_note.configure(state=btn_state)

        # Aplicar estado ao campo de texto
        text_state = "normal" if state["text_field_enabled"] else "disabled"
        self.new_note.configure(state="normal")  # Temporário para editar
        self.new_note.delete("1.0", "end")

        if state["placeholder_message"]:
            self.new_note.insert("1.0", state["placeholder_message"])

        self.new_note.configure(state=text_state)

    # -------------------- Polling e Cache --------------------

    def _start_notes_polling(self) -> None:
        """Inicia o polling de atualizações de notas."""
        if not self._polling_active:
            self._polling_active = True
            # Carregar cache de nomes na primeira vez
            self._refresh_author_names_cache_async(force=True)
            self.refresh_notes_async(force=True)

    def _refresh_author_names_cache_async(self, force: bool = False) -> None:
        """
        Atualiza cache de nomes de autores (profiles.display_name) de forma assíncrona.

        Args:
            force: Se True, ignora cooldown e força atualização
        """
        # Evitar reentrância (exceto se force=True)
        if getattr(self, "_names_cache_loading", False) and not force:
            return
        self._names_cache_loading = True

        # Evitar chamadas duplicadas
        if self._names_refreshing:
            self._names_cache_loading = False
            return

        # Cooldown de 30 segundos (exceto se force=True)
        if should_skip_refresh_by_cooldown(
            last_refresh=self._names_last_refresh,
            cooldown_seconds=_NAMES_REFRESH_COOLDOWN_S,
            force=force,
        ):
            self._names_cache_loading = False
            return

        org_id = self._get_org_id_safe()
        if not org_id:
            self._names_cache_loading = False
            return

        # Se organização mudou, invalidar cache
        if self._last_org_for_names and self._last_org_for_names != org_id:
            self._author_names_cache = {}
            self._email_prefix_map = {}  # invalidar mapa de prefixos também
            self._names_cache_loaded = False
            log.info("Cache de nomes invalidado (mudança de organização)")

        self._names_refreshing = True

        def _work():
            mapping = {}
            prefix_map = {}
            try:
                from src.core.services.profiles_service import (
                    get_display_names_map,
                    get_email_prefix_map,
                )

                mapping = get_display_names_map(org_id)
                prefix_map = get_email_prefix_map(org_id)
            except Exception as e:
                log.debug("Erro ao carregar nomes de autores: %s", e)

            def _ui():
                try:
                    old_hash = getattr(self, "_last_names_cache_hash", None)
                    self._author_names_cache = mapping or {}
                    self._email_prefix_map = prefix_map or {}

                    import hashlib
                    import json

                    cache_json = json.dumps(self._author_names_cache, sort_keys=True, ensure_ascii=False)
                    new_hash = hashlib.sha256(cache_json.encode("utf-8")).hexdigest()
                    self._last_names_cache_hash = new_hash
                    self._names_cache_loaded = True

                    self._names_refreshing = False
                    self._names_last_refresh = time.time()
                    self._last_org_for_names = org_id
                    log.debug(
                        "Cache de nomes carregado: %d entradas",
                        len(self._author_names_cache),
                    )
                    log.debug(
                        "Mapa de prefixos carregado: %d entradas",
                        len(self._email_prefix_map),
                    )

                    if new_hash != old_hash:
                        # força um único re-render
                        self._last_render_hash = None
                        notes_last_data = getattr(self, "_notes_last_data", None)
                        notes_last_snapshot = getattr(self, "_notes_last_snapshot", None)
                        if notes_last_data and isinstance(notes_last_data, list):
                            self.render_notes(notes_last_data)
                        elif notes_last_snapshot and isinstance(notes_last_snapshot, list):
                            self.render_notes(notes_last_snapshot)
                finally:
                    self._names_cache_loading = False

            try:
                self.after(0, _ui)
            except Exception:
                self._names_cache_loading = False

        threading.Thread(target=_work, daemon=True).start()

    # -------------------- Live Sync de Notas em Tempo Real --------------------

    def _start_live_sync(self):
        """Inicia sync de notas da org atual: Realtime + fallback polling."""
        if self._live_sync_on:
            return
        org_id = self._get_org_id_safe()
        if not org_id:
            return
        self._live_org_id = org_id
        self._live_sync_on = True

        # 1) marcar timestamp da última nota já renderizada (para polling)
        try:
            notes = getattr(self, "_notes_last_data", None) or []
            if notes:
                self._live_last_ts = max((n.get("created_at") or "") for n in notes)
        except Exception:
            self._live_last_ts = None

        # 2) tentar Realtime
        try:
            # [finalize-notes] import seguro dentro de função
            from infra.supabase_client import get_supabase  # usar cliente existente

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
                lambda payload: self._on_realtime_note(payload.get("new") or {}),
            )

            ch.subscribe()
            self._live_channel = ch
        except Exception:
            self._live_channel = None

        # 3) fallback por polling a cada 6s
        self._schedule_poll()

    def _stop_live_sync(self):
        """Para sync (sair do Hub, logout)."""
        self._live_sync_on = False
        self._live_org_id = None
        try:
            if self._live_channel:
                self._live_channel.unsubscribe()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[HUB] Falha ao desinscrever live_channel: %s", exc)
        self._live_channel = None
        controller_cancel_poll(self)

    def on_show(self):
        actions_on_show(self)

    def _schedule_poll(self, delay_ms: int = 6000):
        controller_schedule_poll(self, delay_ms)

    def _poll_notes_if_needed(self):
        controller_poll_notes_if_needed(self)

    def _on_realtime_note(self, row: dict):
        controller_on_realtime_note(self, row)

    def _append_note_incremental(self, row: dict):
        controller_append_note_incremental(self, row)

    # -------------------- Utilitários de Nome e Cor --------------------

    def _collect_notes_debug(self) -> dict:
        """
        Coleta informações de debug sobre notas e resolução de autores.
        """
        notes = getattr(self, "_notes_last_data", None) or getattr(self, "_notes_last_snapshot", None) or []
        out = {
            "org_id": (self._get_org_id_safe() if hasattr(self, "_get_org_id_safe") else None),
            "current_user": (
                getattr(self, "_current_user_email", None) or self._get_email_safe()
                if hasattr(self, "_get_email_safe")
                else ""
            ),
            "names_cache_size": len(getattr(self, "_author_names_cache", {}) or {}),
            "prefix_map_size": len(getattr(self, "_email_prefix_map", {}) or {}),
            "names_cache": dict(getattr(self, "_author_names_cache", {}) or {}),
            "prefix_map": dict(getattr(self, "_email_prefix_map", {}) or {}),
            "samples": [],
        }

        # normaliza entrada (se for tupla/lista)
        def _author_of(n):
            if isinstance(n, dict):
                return n.get("author_email") or n.get("author") or n.get("email") or ""
            if isinstance(n, (tuple, list)):
                if len(n) >= 2:  # (ts, author, body) ou (author, body)
                    return str(n[1])
                if len(n) == 1:
                    return str(n[0])
            return str(n)

        for n in list(notes)[:20]:
            out["samples"].append(_debug_resolve_author(self, _author_of(n)))
        return out

    # -------------------- Fim DEBUG --------------------

    # -------------------- Formatação e Renderização --------------------

    def render_notes(self, notes: List[Dict[str, Any]], force: bool = False) -> None:
        """Renderiza lista de notas no histórico com nomes coloridos e timezone local.

        Args:
            notes: Lista de dicionários com dados das notas
            force: Se True, ignora cache de hash e força re-renderização
        """
        # Verificação defensiva: garantir que cache de tags existe
        s = ensure_state(self)
        author_tags = s.author_tags
        if author_tags is None:
            s.author_tags = {}
            author_tags = s.author_tags

        # Normalizar entrada: converter tuplas/listas para dicts
        notes = [_normalize_note(x) for x in (notes or [])]

        # NÃO apaga se vier vazio/None (evita 'branco' e piscas)
        if should_skip_render_empty_notes(notes):
            self._dlog("render_skip_empty")
            return

        # Hash de conteúdo pra evitar re-render desnecessário
        render_hash = calculate_notes_content_hash(notes)

        # Se não forçado, verificar se hash é igual (skip re-render)
        if not force:
            if render_hash == getattr(self, "_last_render_hash", None):
                self._dlog("render_skip_samehash")
                return

        self._last_render_hash = render_hash

        try:
            # 1) Verificar se o atributo existe e não é None
            if not hasattr(self, "notes_history") or self.notes_history is None:
                logger.warning("Hub: notes_history ausente ao renderizar; pulando atualização de notas.")
                return

            # 2) Verificar se o widget Tk ainda existe
            #    winfo_exists() retorna 1 se o widget existir, 0 se já foi destruído.
            if not self.notes_history.winfo_exists():
                logger.warning("Hub: notes_history destruído (frame/aba fechada?); pulando atualização de notas.")
                return

            # A partir daqui, é seguro usar o widget
            self.notes_history.configure(state="normal")
            self.notes_history.delete("1.0", "end")

            for n in notes:
                email = (n.get("author_email") or "").strip().lower()
                name = (n.get("author_name") or "").strip()

                if not name:
                    # usar cache → mapa local → fetch → placeholder
                    name = _author_display_name(self, email)

                # Aplicar tag de cor com fallback defensivo
                tag = None
                try:
                    tag = _ensure_author_tag(self.notes_history, email, author_tags)
                except Exception:
                    logger.exception("Hub: falha ao aplicar estilo/tag do autor; renderizando sem cor.")
                    tag = None  # segue sem tag

                created_at = n.get("created_at")
                created_at_str = str(created_at) if created_at is not None else ""
                ts = format_timestamp(created_at_str) if created_at_str else "??"
                body = (n.get("body") or "").rstrip("\n")

                # Inserir: [data] <nome colorido>: corpo
                if tag:
                    self.notes_history.insert("end", f"[{ts}] ")
                    self.notes_history.insert("end", name, (tag,))
                    self.notes_history.insert("end", f": {body}\n")
                else:
                    line = (
                        format_note_line(created_at_str, name or email, body)
                        if created_at_str
                        else f"?? {name or email}: {body}"
                    )
                    self.notes_history.insert("end", f"{line}\n")

            self.notes_history.configure(state="disabled")
            # Scrollar para o fim (mais recente)
            self.notes_history.see("end")
            self.notes_history.see("end")
        except TclError:
            logger.exception("Hub: erro crítico ao renderizar lista de notas.")
        except Exception:
            logger.exception("Hub: erro crítico ao renderizar lista de notas.")
            try:
                self.notes_history.configure(state="disabled")
            except Exception as exc:  # noqa: BLE001
                logger.debug("[HUB] Falha ao restaurar estado disabled: %s", exc)

    def refresh_notes_async(self, force: bool = False) -> None:
        controller_refresh_notes_async(self, force)

    def _retry_after_table_missing(self) -> None:
        controller_retry_after_table_missing(self)

    def _on_add_note_clicked(self) -> None:
        """Handler para clique no botão 'Adicionar' nota.

        Usa o NotesController para validar e adicionar a nota.
        """
        try:
            # Obter texto da entrada
            note_text = self.new_note.get("1.0", "end-1c").strip()

            # Delegar ao controller
            success, message = self._notes_controller.handle_add_note_click(note_text)

            if success:
                # Limpar entrada
                self.new_note.delete("1.0", "end")
                # Refresh automático será feito via polling/realtime
            else:
                if message:  # Mensagens vazias já foram tratadas pelo controller
                    logger.debug(f"Falha ao adicionar nota: {message}")
        except Exception as e:
            logger.exception("Erro no handler _on_add_note_clicked")
            self.show_error("Erro", f"Erro inesperado ao adicionar nota: {e}")

    def _get_app(self):
        """Obtém referência para a janela principal (App)."""
        try:
            # Subir na hierarquia até encontrar a janela raiz
            widget = self.master
            while widget:
                if hasattr(widget, "auth") or hasattr(widget, "_org_id_cache"):
                    return widget
                widget = getattr(widget, "master", None)
        except Exception as exc:  # noqa: BLE001
            logger.debug("[HUB] Falha ao obter referência da App: %s", exc)
        return None

    def _is_online(self, app) -> bool:
        """Verifica se está online."""
        try:
            if hasattr(app, "_net_is_online"):
                return bool(app._net_is_online)
        except Exception as exc:  # noqa: BLE001
            logger.debug("[HUB] Falha ao verificar _net_is_online: %s", exc)
        return True  # Assume online se não conseguir verificar

    def stop_polling(self) -> None:
        """Para o polling de notas e cancela timers pendentes."""
        self._polling_active = False

        # Cancelar timers pendentes
        if self._notes_after_handle:
            try:
                self.after_cancel(self._notes_after_handle)
            except Exception as exc:  # noqa: BLE001
                logger.debug("[HUB] Falha ao cancelar after de notas: %s", exc)
            self._notes_after_handle = None

        if self._clients_after_handle:
            try:
                self.after_cancel(self._clients_after_handle)
            except Exception as exc:  # noqa: BLE001
                logger.debug("[HUB] Falha ao cancelar after de clientes: %s", exc)
            self._clients_after_handle = None

        controller_cancel_poll(self)

    @property
    def state(self) -> HubState:
        """Read-only access to the HubState container."""
        if not isinstance(getattr(self, "_hub_state", None), HubState):
            self._hub_state = ensure_state(self)
        return self._hub_state

    @property
    def _author_tags(self):
        s = ensure_state(self)
        if s.author_tags is None:
            s.author_tags = {}
        return s.author_tags

    @_author_tags.setter
    def _author_tags(self, value):
        s = ensure_state(self)
        s.author_tags = value or {}

    @property
    def _poll_job(self):
        return ensure_state(self).poll_job

    @_poll_job.setter
    def _poll_job(self, value):
        ensure_state(self).poll_job = value

    @property
    def _is_refreshing(self):
        return ensure_state(self).is_refreshing

    @_is_refreshing.setter
    def _is_refreshing(self, value):
        ensure_state(self).is_refreshing = bool(value)

    def hub_state(self) -> HubState:
        """Convenience accessor for the HubState container."""
        return self.state

    def destroy(self) -> None:
        """Override destroy para parar polling."""
        self.stop_polling()
        super().destroy()

    def _noop(self) -> None:
        """Placeholder para botões sem ação."""
        pass

    def _show_debug_info(self, event=None) -> None:
        """Gera relatório JSON de diagnóstico (atalho Ctrl+D)."""
        import json
        import os
        from datetime import datetime

        try:
            # Coleta informações de debug
            debug_data = self._collect_notes_debug()

            # Gera nome do arquivo com timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"debug_notes_report_{timestamp}.json"

            # Salva no diretório de trabalho
            filepath = os.path.abspath(filename)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(debug_data, f, ensure_ascii=False, indent=2)

            # Mostra mensagem com o caminho do arquivo
            messagebox.showinfo(
                "Relatório de Debug Gerado",
                f"Relatório salvo em:\n{filepath}",
                parent=self,
            )

            # Imprime no console como backup
            logger.info("\n=== DEBUG NOTES REPORT ===")
            logger.info(json.dumps(debug_data, ensure_ascii=False, indent=2))
            logger.info("=== Salvo em: %s ===\n", filepath)

        except Exception as e:
            log.error("Erro ao gerar relatório de debug: %s", e)
            messagebox.showerror("Erro", f"Erro ao gerar relatório: {e}", parent=self)
