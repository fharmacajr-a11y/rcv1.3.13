"""View do painel central de Dashboard do Hub.

Extraído de HubScreen na MF-26 para reduzir o tamanho do monolito.
MF-30: Estendido para incluir lógica de renderização do dashboard.

Este módulo é responsável pela construção visual do painel central
e pela renderização dos cards de dashboard.
"""

from typing import Any, Callable

from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk
from src.ui.ui_tokens import APP_BG
import tkinter as tk

# MF-30: Importar helpers de renderização
from src.modules.hub.views.dashboard_center import build_dashboard_center, build_dashboard_error


class HubDashboardView:
    """View do painel central de Dashboard do Hub.

    Responsabilidades (MF-26 + MF-30):
    - Criar o frame container central (center_spacer)
    - Criar o ScrollableFrame para permitir scroll dos cards
    - Renderizar conteúdo do dashboard (loading, erro, dados, vazio)

    Esta classe NÃO conhece HubScreen diretamente, apenas recebe:
    - parent: widget pai onde o painel será anexado
    - Dados já processados para renderização

    A lógica de CARREGAR dados (async) permanece no HubScreen/Controller.
    Esta view apenas DESENHA o que recebe.
    """

    def __init__(self, parent: Any):
        """Inicializa a view do painel de dashboard.

        Args:
            parent: Widget pai (onde o painel será criado)
        """
        self._parent = parent
        self.center_spacer: tk.Frame | None = None
        self.dashboard_scroll: Any = None  # ScrollableFrame

    def build(self) -> tk.Frame:
        """Constrói e retorna o frame do painel de dashboard.

        Este método cria:
        - Frame container (center_spacer)
        - Frame normal dentro do container (sem scrollbar)

        O conteúdo do dashboard (cards) será renderizado posteriormente
        via outros métodos que acessam `dashboard_scroll.content`.

        Returns:
            O frame container do painel de dashboard (center_spacer)
        """
        # Container da coluna central - MICROFASE 35: fundo APP_BG
        if HAS_CUSTOMTKINTER and ctk is not None:
            self.center_spacer = ctk.CTkFrame(
                self._parent,
                fg_color=APP_BG,
                corner_radius=0,
            )
        else:
            self.center_spacer = tk.Frame(self._parent)

        # Frame normal dentro do container (sem scrollbar) - fundo transparente
        if HAS_CUSTOMTKINTER and ctk is not None:
            self.dashboard_scroll = ctk.CTkFrame(
                self.center_spacer,
                fg_color="transparent",
            )
        else:
            self.dashboard_scroll = tk.Frame(self.center_spacer)
        self.dashboard_scroll.pack(fill="both", expand=True)

        # Compatibilidade: quem chama espera .content
        self.dashboard_scroll.content = self.dashboard_scroll  # type: ignore[attr-defined]

        return self.center_spacer

    # ═══════════════════════════════════════════════════════════════════════════
    # MF-30/MF-32: Métodos de renderização do dashboard
    # ═══════════════════════════════════════════════════════════════════════════

    def render_loading(self) -> None:
        """Renderiza estado de loading no dashboard.

        MF-32: Adicionado para completar cenários de renderização.
        """
        import logging

        logger = logging.getLogger(__name__)
        logger.debug("[HubDashboardView] Renderizando loading...")

        if not self.dashboard_scroll:
            logger.warning("[HubDashboardView] dashboard_scroll é None, não pode renderizar loading")
            return

        # Limpar conteúdo e mostrar loading
        for widget in self.dashboard_scroll.content.winfo_children():
            widget.destroy()

        if HAS_CUSTOMTKINTER and ctk is not None:
            loading_label = ctk.CTkLabel(
                self.dashboard_scroll.content,
                text="Carregando dashboard...",
                font=("Segoe UI", 12),
                text_color=("#6b7280", "#9ca3af"),
                fg_color="transparent",
            )
        else:
            loading_label = tk.Label(
                self.dashboard_scroll.content,
                text="Carregando dashboard...",
                font=("Segoe UI", 12),
            )
        loading_label.pack(pady=50)

    def render_empty(self) -> None:
        """Renderiza estado vazio (sem dados) no dashboard.

        MF-32: Adicionado para completar cenários de renderização.
        """
        if not self.dashboard_scroll:
            return

        # Limpar conteúdo e mostrar mensagem de vazio
        for widget in self.dashboard_scroll.content.winfo_children():
            widget.destroy()

        if HAS_CUSTOMTKINTER and ctk is not None:
            empty_label = ctk.CTkLabel(
                self.dashboard_scroll.content,
                text="Nenhum dado disponível no momento.",
                font=("Segoe UI", 12),
                text_color=("#6b7280", "#9ca3af"),
                fg_color="transparent",
            )
        else:
            empty_label = tk.Label(
                self.dashboard_scroll.content,
                text="Nenhum dado disponível no momento.",
                font=("Segoe UI", 12),
            )
        empty_label.pack(pady=50)

    def render_error(self, message: str | None = None) -> None:
        """Renderiza tela de erro no dashboard.

        MF-32: Renomeado de render_dashboard_error para consistência.

        Args:
            message: Mensagem de erro opcional (se None, usa mensagem padrão)
        """
        if not self.dashboard_scroll:
            return

        build_dashboard_error(self.dashboard_scroll.content, message)

    def render_dashboard_error(self, message: str | None = None) -> None:
        """Alias para render_error (compatibilidade com código existente).

        MF-32: Mantido para não quebrar chamadas existentes.
        """
        self.render_error(message)

    def render_data(
        self,
        state: Any,  # DashboardViewState
        on_new_task: Callable[[], None] | None = None,
        on_new_obligation: Callable[[], None] | None = None,
        on_view_all_activity: Callable[[], None] | None = None,
        on_card_clients_click: Callable[[Any], None] | None = None,
        on_card_pendencias_click: Callable[[Any], None] | None = None,
        on_card_tarefas_click: Callable[[Any], None] | None = None,
    ) -> None:
        """Renderiza dados do dashboard (cards, atividades).

        MF-32: Renomeado de render_dashboard_data para consistência.

        Args:
            state: DashboardViewState com snapshot e cards formatados
            on_new_task: Callback para criar nova tarefa
            on_new_obligation: Callback para criar nova obrigação
            on_view_all_activity: Callback para visualizar toda atividade
            on_card_clients_click: Callback para clique no card de clientes
            on_card_pendencias_click: Callback para clique no card de pendências
            on_card_tarefas_click: Callback para clique no card de tarefas
        """
        import logging

        logger = logging.getLogger(__name__)
        logger.debug(f"[HubDashboardView] render_data INICIANDO - Snapshot: {bool(getattr(state, 'snapshot', None))}")

        try:
            if not self.dashboard_scroll:
                logger.error("[HubDashboardView] dashboard_scroll é None, não pode renderizar dados")
                return

            # CRÍTICO: Limpar todo conteúdo existente (incluindo "Carregando dashboard...")
            logger.debug("[HubDashboardView] Limpando widgets antigos...")
            for widget in self.dashboard_scroll.content.winfo_children():
                widget.destroy()

            # Validação: se não houver snapshot, mostrar vazio
            if not getattr(state, "snapshot", None):
                logger.warning("[HubDashboardView] state.snapshot é None/vazio, renderizando estado vazio")
                self.render_empty()
                return

            logger.debug("[HubDashboardView] Chamando build_dashboard_center...")

            # Obter tk_root para carregar histórico do Supabase
            tk_root = self.dashboard_scroll.content.winfo_toplevel()

            # Delegar para helper de renderização
            # No modo ANVISA-only, callbacks são sempre passados (controller decide ação)
            build_dashboard_center(
                self.dashboard_scroll.content,
                state,
                on_new_task=on_new_task or (lambda: None),
                on_new_obligation=on_new_obligation or (lambda: None),
                on_view_all_activity=on_view_all_activity or (lambda: None),
                on_card_clients_click=on_card_clients_click or (lambda s: None),
                on_card_pendencias_click=on_card_pendencias_click or (lambda s: None),
                on_card_tarefas_click=on_card_tarefas_click or (lambda s: None),
                tk_root=tk_root,
            )

            logger.debug("[HubDashboardView] render_data CONCLUÍDO com sucesso")
        except Exception as e:
            logger.exception(f"[HubDashboardView] ERRO em render_data: {e}")
            # Tentar mostrar mensagem de erro ao invés de travar
            try:
                self.render_error(f"Erro ao renderizar dashboard: {e}")
            except Exception:
                logger.exception("[HubDashboardView] Falha ao renderizar tela de erro")

    def render_dashboard_data(
        self,
        state: Any,  # DashboardViewState
        on_new_task: Callable[[], None] | None = None,
        on_new_obligation: Callable[[], None] | None = None,
        on_view_all_activity: Callable[[], None] | None = None,
        on_card_clients_click: Callable[[Any], None] | None = None,
        on_card_pendencias_click: Callable[[Any], None] | None = None,
        on_card_tarefas_click: Callable[[Any], None] | None = None,
    ) -> None:
        """Alias para render_data (compatibilidade com código existente).

        MF-32: Mantido para não quebrar chamadas existentes.
        """
        self.render_data(
            state,
            on_new_task=on_new_task,
            on_new_obligation=on_new_obligation,
            on_view_all_activity=on_view_all_activity,
            on_card_clients_click=on_card_clients_click,
            on_card_pendencias_click=on_card_pendencias_click,
            on_card_tarefas_click=on_card_tarefas_click,
        )
