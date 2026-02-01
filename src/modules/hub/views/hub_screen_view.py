# -*- coding: utf-8 -*-
"""HubScreenView - View Tkinter pura do HubScreen.

Responsável apenas por UI: widgets, layout, bindings.
Não contém lógica de negócio, chamadas a services ou estado.
"""

from __future__ import annotations

import logging
import tkinter as tk
from typing import Any, Callable, Protocol


from src.modules.hub.viewmodels import DashboardViewState
from src.modules.hub.views.dashboard_center import build_dashboard_center, build_dashboard_error
from src.modules.hub.views.notes_panel_view import NotesViewCallbacks, build_notes_side_panel

# ORG-006: Constantes e funções puras extraídas
from src.modules.hub.views.hub_screen_view_constants import (
    BTN_GRID_PADX,
    BTN_GRID_PADY,
    FRAME_INNER_PADDING,
    FRAME_PACK_PADY,
    MSG_LOADING_NOTES,
    MSG_NO_NOTES_YET,
    SECTION_CADASTROS_LABEL,
    SECTION_REGULATORIO_LABEL,
)
from src.modules.hub.views.hub_screen_view_pure import format_note_line, make_module_button

logger = logging.getLogger(__name__)


class HubViewCallbacks(Protocol):
    """Protocolo de callbacks do HubScreen para o Controller.

    View não conhece lógica de negócio - apenas chama callbacks.
    """

    def on_module_click(self, module: str) -> None:
        """Callback para clique em módulo (Clientes, Senhas, etc.)."""
        ...

    def on_card_click(self, card_type: str, client_id: str | None = None) -> None:
        """Callback para clique em card do dashboard."""
        ...

    def on_new_task_click(self) -> None:
        """Callback para botão '+' de nova tarefa."""
        ...

    def on_new_obligation_click(self) -> None:
        """Callback para botão '+' de nova obrigação."""
        ...

    def on_view_all_activity_click(self) -> None:
        """Callback para 'Ver todas as atividades'."""
        ...

    def on_add_note_click(self, note_text: str) -> None:
        """Callback para adicionar nota."""
        ...

    def on_edit_note_click(self, note_id: str) -> None:
        """Callback para editar nota."""
        ...

    def on_delete_note_click(self, note_id: str) -> None:
        """Callback para deletar nota."""
        ...

    def on_toggle_pin_click(self, note_id: str) -> None:
        """Callback para pin/unpin nota."""
        ...

    def on_toggle_done_click(self, note_id: str) -> None:
        """Callback para marcar nota como done."""
        ...

    def on_debug_shortcut(self) -> None:
        """Callback para Ctrl+D (debug info)."""
        ...

    def on_refresh_authors_cache(self, force: bool = False) -> None:
        """Callback para Ctrl+L (refresh cache de autores)."""
        ...


class HubScreenView:
    """View pura do HubScreen (UI Tkinter).

    Responsabilidades:
    - Criar widgets Tkinter (frames, labels, buttons, etc.)
    - Montar layout grid 3 colunas (módulos | dashboard | notas)
    - Configurar bindings de eventos → callbacks
    - Expor métodos de atualização visual (update_dashboard, update_notes, etc.)

    NÃO responsável por:
    - Lógica de negócio (salvar, validar, buscar dados)
    - Chamadas a services/repos/ViewModels
    - Estado de dados (apenas referências a widgets)
    - Timers/polling (delegado ao Controller via Lifecycle)
    """

    def __init__(
        self,
        parent: tk.Misc,
        callbacks: HubViewCallbacks,
        *,
        open_clientes: Callable[[], None] | None = None,
        open_anvisa: Callable[[], None] | None = None,
        open_farmacia_popular: Callable[[], None] | None = None,
        open_sngpc: Callable[[], None] | None = None,
        open_mod_sifap: Callable[[], None] | None = None,
        open_cashflow: Callable[[], None] | None = None,
        open_sites: Callable[[], None] | None = None,
    ) -> None:
        """Inicializa a view com callbacks do controller.

        Args:
            parent: Widget pai (HubScreen frame)
            callbacks: Protocolo de callbacks para eventos
            open_*: Callbacks de navegação para módulos
        """
        self.parent = parent
        self.callbacks = callbacks

        # Armazenar callbacks de navegação
        self.open_clientes = open_clientes
        self.open_anvisa = open_anvisa
        self.open_farmacia_popular = open_farmacia_popular
        self.open_sngpc = open_sngpc
        self.open_mod_sifap = open_mod_sifap
        self.open_cashflow = open_cashflow
        self.open_sites = open_sites

        # Widgets principais (criados em build_layout)
        self.modules_panel: tk.LabelFrame | None = None
        self.center_spacer: tk.Frame | None = None
        self.dashboard_scroll: Any | None = None
        self.notes_panel: Any | None = None
        self.notes_history: Any | None = None
        self.new_note: Any | None = None
        self.btn_add_note: Any | None = None

        # Referências necessárias para o HubScreenController
        # Serão injetadas pelo HubScreen após criação
        self._hub_screen: Any | None = None  # Referência ao HubScreen (para métodos como get_org_id)
        self._dashboard_actions: Any | None = None  # DashboardActionController
        self._notes_view: Any | None = None  # HubNotesView para render_notes

    def build_layout(self) -> None:
        """Constrói layout 3 colunas (módulos | dashboard | notas).

        Layout grid:
        - Coluna 0: Painel de módulos (peso 0, largura fixa)
        - Coluna 1: Dashboard central (peso 1, expansível)
        - Coluna 2: Painel de notas (peso 0, largura fixa)
        """
        # Build painel de módulos (esquerda)
        self._build_modules_panel()

        # Build painel de dashboard (centro)
        self._build_dashboard_panel()

        # Build painel de notas (direita)
        self._build_notes_panel()

        # Setup layout grid
        self._setup_layout()

        # Setup bindings de teclado
        self._setup_bindings()

    def _build_modules_panel(self) -> None:
        """Constrói o painel de módulos (menu vertical à esquerda).

        Delega construção para build_modules_panel helper, mas inline
        para compatibilidade com testes existentes.
        """
        from src.modules.hub.constants import (
            HUB_BTN_STYLE_CLIENTES,
            HUB_BTN_STYLE_FLUXO_CAIXA,
            MODULES_TITLE,
            PAD_OUTER,
        )

        # ORG-006: Helper movido para hub_screen_view_pure.py
        # Helper inline `mk_btn` agora é `make_module_button`

        # Painel principal
        self.modules_panel = tk.LabelFrame(self.parent, text=MODULES_TITLE, padding=PAD_OUTER)

        # BLOCO 1: Cadastros / Acesso
        frame_cadastros = tk.LabelFrame(
            self.modules_panel,
            text=SECTION_CADASTROS_LABEL,
            padding=FRAME_INNER_PADDING,
        )
        frame_cadastros.pack(fill="x", pady=FRAME_PACK_PADY)
        frame_cadastros.columnconfigure(0, weight=1)
        frame_cadastros.columnconfigure(1, weight=1)

        btn_clientes = make_module_button(frame_cadastros, "Clientes", self.open_clientes, HUB_BTN_STYLE_CLIENTES)
        btn_clientes.grid(row=0, column=0, sticky="ew", padx=BTN_GRID_PADX, pady=BTN_GRID_PADY)

        # BLOCO 2: Gestão
        frame_gestao = tk.LabelFrame(
            self.modules_panel,
            text="Gestão",
            padding=FRAME_INNER_PADDING,
        )
        frame_gestao.pack(fill="x", pady=FRAME_PACK_PADY)
        frame_gestao.columnconfigure(0, weight=1)

        btn_fluxo_caixa = make_module_button(
            frame_gestao, "Fluxo de Caixa", self.open_cashflow, HUB_BTN_STYLE_FLUXO_CAIXA
        )
        btn_fluxo_caixa.grid(row=0, column=0, sticky="ew", padx=BTN_GRID_PADX, pady=BTN_GRID_PADY)

        # BLOCO 3: Regulatório / Programas
        frame_regulatorio = tk.LabelFrame(
            self.modules_panel,
            text=SECTION_REGULATORIO_LABEL,
            padding=FRAME_INNER_PADDING,
        )
        frame_regulatorio.pack(fill="x", pady=(0, 0))
        frame_regulatorio.columnconfigure(0, weight=1)
        frame_regulatorio.columnconfigure(1, weight=1)

        btn_anvisa = make_module_button(frame_regulatorio, "Anvisa", self.open_anvisa, "info")
        btn_anvisa.grid(row=0, column=0, sticky="ew", padx=BTN_GRID_PADX, pady=BTN_GRID_PADY)

        btn_sngpc = make_module_button(frame_regulatorio, "Sngpc", self.open_sngpc, "secondary")
        btn_sngpc.grid(row=0, column=1, sticky="ew", padx=BTN_GRID_PADX, pady=BTN_GRID_PADY)

    def _build_dashboard_panel(self) -> None:
        """Constrói o painel central para o dashboard (sem scrollbar)."""
        # Container da coluna central
        self.center_spacer = tk.Frame(self.parent)

        # Frame normal dentro do container (sem scrollbar)
        self.dashboard_scroll = tk.Frame(self.center_spacer)
        self.dashboard_scroll.pack(fill="both", expand=True)

        # Compatibilidade: quem chama espera .content
        self.dashboard_scroll.content = self.dashboard_scroll  # type: ignore[attr-defined]

    def _build_notes_panel(self) -> None:
        """Constrói o painel de notas compartilhadas (lateral direita).

        Delega a construção de UI para build_notes_side_panel helper.
        """

        # Preparar callbacks de notas (wrappers que extraem texto do widget)
        def on_add_wrapper() -> None:
            if self.new_note:
                text = self.new_note.get("1.0", "end-1c").strip()
                self.callbacks.on_add_note_click(text)

        def on_edit_wrapper(note_id: str) -> None:
            self.callbacks.on_edit_note_click(note_id)

        def on_delete_wrapper(note_id: str) -> None:
            self.callbacks.on_delete_note_click(note_id)

        def on_pin_wrapper(note_id: str) -> None:
            self.callbacks.on_toggle_pin_click(note_id)

        def on_done_wrapper(note_id: str) -> None:
            self.callbacks.on_toggle_done_click(note_id)

        notes_callbacks = NotesViewCallbacks(
            on_add_note_click=on_add_wrapper,
            on_edit_note_click=on_edit_wrapper,
            on_delete_note_click=on_delete_wrapper,
            on_toggle_pin_click=on_pin_wrapper,
            on_toggle_done_click=on_done_wrapper,
        )

        # Build panel usando helper (extrai lógica de UI)
        # State inicial vazio (será atualizado pelo controller)
        from src.modules.hub.viewmodels import NotesViewModel

        empty_state = NotesViewModel().state

        # Cast parent para tk.Frame (parent é sempre Frame no HubScreen)
        parent_frame = self.parent if isinstance(self.parent, tk.Frame) else tk.Frame(self.parent)

        self.notes_panel = build_notes_side_panel(
            parent=parent_frame,
            state=empty_state,
            callbacks=notes_callbacks,
        )

        # Store references to widgets for update methods
        self.notes_history = self.notes_panel.notes_history  # type: ignore[attr-defined]
        self.new_note = self.notes_panel.new_note  # type: ignore[attr-defined]
        self.btn_add_note = self.notes_panel.btn_add_note  # type: ignore[attr-defined]

    def _setup_layout(self) -> None:
        """Configura o layout grid de 3 colunas (módulos | dashboard | notas)."""
        from src.modules.hub.layout import apply_hub_notes_right

        widgets = {
            "modules_panel": self.modules_panel,
            "spacer": self.center_spacer,
            "notes_panel": self.notes_panel,
        }
        apply_hub_notes_right(self.parent, widgets)

    def _setup_bindings(self) -> None:
        """Configura atalhos de teclado (Ctrl+D para diagnóstico, Ctrl+L para reload cache)."""
        # Ctrl+D para diagnóstico
        self.parent.bind_all("<Control-d>", lambda _e: self.callbacks.on_debug_shortcut())
        self.parent.bind_all("<Control-D>", lambda _e: self.callbacks.on_debug_shortcut())

        # Ctrl+L para recarregar cache de nomes (teste)
        self.parent.bind_all("<Control-l>", lambda _e: self.callbacks.on_refresh_authors_cache(force=True))
        self.parent.bind_all("<Control-L>", lambda _e: self.callbacks.on_refresh_authors_cache(force=True))

    # ═══════════════════════════════════════════════════════════════════════
    # Métodos de Atualização de UI
    # ═══════════════════════════════════════════════════════════════════════

    def update_dashboard(
        self,
        state: DashboardViewState,
        *,
        on_new_task: Callable[[], None] | None = None,
        on_new_obligation: Callable[[], None] | None = None,
        on_view_all_activity: Callable[[], None] | None = None,
        on_card_clients_click: Callable[[DashboardViewState], None] | None = None,
        on_card_pendencias_click: Callable[[DashboardViewState], None] | None = None,
        on_card_tarefas_click: Callable[[DashboardViewState], None] | None = None,
    ) -> None:
        """Atualiza painel central do dashboard.

        Args:
            state: Estado do DashboardViewModel
            on_*: Callbacks para eventos do dashboard
        """
        if not self.dashboard_scroll:
            return

        # Se houver erro, mostrar tela de erro
        if state.error_message:
            build_dashboard_error(self.dashboard_scroll.content)
            return

        # Se não houver snapshot, não fazer nada (estado inválido)
        if not state.snapshot:
            return

        # No modo ANVISA-only, desabilitar cliques em Pendências/Tarefas
        # (dados vêm de anvisa_requests, não de obligations/tasks)
        anvisa_only = state.snapshot.anvisa_only if state.snapshot else False

        # Callbacks para cards - desabilitados em modo ANVISA-only
        card_pendencias_cb = (
            None if anvisa_only else (on_card_pendencias_click or (lambda _s: self.callbacks.on_card_click("pending")))
        )
        card_tarefas_cb = (
            None if anvisa_only else (on_card_tarefas_click or (lambda _s: self.callbacks.on_card_click("tasks")))
        )

        # TODO ANVISA-only: no futuro, pode-se implementar:
        # card_pendencias_cb = (lambda _s: self.callbacks.open_module("anvisa")) if anvisa_only else ...
        # card_tarefas_cb = (lambda _s: self.callbacks.open_module("anvisa")) if anvisa_only else ...

        # Renderizar dashboard com state completo
        build_dashboard_center(
            self.dashboard_scroll.content,
            state,
            on_new_task=on_new_task or self.callbacks.on_new_task_click,
            on_new_obligation=on_new_obligation or self.callbacks.on_new_obligation_click,
            on_view_all_activity=on_view_all_activity or self.callbacks.on_view_all_activity_click,
            on_card_clients_click=on_card_clients_click or (lambda _s: self.callbacks.on_card_click("clients")),
            on_card_pendencias_click=card_pendencias_cb,
            on_card_tarefas_click=card_tarefas_cb,
        )

    def update_notes_panel(self, notes: list[dict[str, Any]]) -> None:
        """Atualiza painel de notas compartilhadas.

        Args:
            notes: Lista de notas para renderizar
        """
        if not self.notes_history:
            return

        # Habilitar edição temporária
        self.notes_history.configure(state="normal")
        self.notes_history.delete("1.0", "end")

        # ORG-006: Renderização de notas usando função pura
        # Renderizar notas
        if not notes:
            self.notes_history.insert("end", MSG_NO_NOTES_YET)
        else:
            for note in notes:
                line = format_note_line(note)
                self.notes_history.insert("end", line)

        # Desabilitar edição novamente
        self.notes_history.configure(state="disabled")

        # Auto-scroll para o final
        self.notes_history.see("end")

    def show_loading(self, _message: str = "Carregando...") -> None:
        """Exibe estado de loading.

        Args:
            _message: Mensagem de loading (não utilizada ainda)
        """
        # Desabilitar botões e campos durante loading
        if self.btn_add_note:
            self.btn_add_note.configure(state="disabled")

        if self.new_note:
            self.new_note.configure(state="disabled")

        # ORG-006: Mensagem de loading extraída para constante
        # Opcional: Poderia criar um overlay de loading
        # ou atualizar o painel de notas com mensagem
        if self.notes_history:
            self.notes_history.configure(state="normal")
            self.notes_history.delete("1.0", "end")
            self.notes_history.insert("end", MSG_LOADING_NOTES)
            self.notes_history.configure(state="disabled")

    def hide_loading(self) -> None:
        """Esconde estado de loading.

        Reativa widgets que foram desabilitados durante loading.
        """
        # Reabilitar botões e campos
        if self.btn_add_note:
            self.btn_add_note.configure(state="normal")

        if self.new_note:
            self.new_note.configure(state="normal")

    def update_notes_ui_state(self, *, button_enabled: bool, placeholder_message: str | None = None) -> None:
        """Atualiza estado do botão e placeholder de notas.

        Args:
            button_enabled: Se botão de adicionar deve estar habilitado
            placeholder_message: Mensagem placeholder (None para habilitar campo)
        """
        if not self.btn_add_note or not self.new_note:
            return

        # Atualizar botão
        btn_state = "normal" if button_enabled else "disabled"
        self.btn_add_note.configure(state=btn_state)

        # Atualizar campo de texto
        text_state = "normal" if not placeholder_message else "disabled"
        self.new_note.configure(state="normal")  # Temporário para editar
        self.new_note.delete("1.0", "end")

        if placeholder_message:
            self.new_note.insert("1.0", placeholder_message)

        self.new_note.configure(state=text_state)

    def clear_new_note_text(self) -> None:
        """Limpa campo de nova nota (após sucesso)."""
        if self.new_note:
            self.new_note.delete("1.0", "end")

    # ═══════════════════════════════════════════════════════════════════════
    # Métodos de Acesso (usados pelo HubScreenController)
    # ═══════════════════════════════════════════════════════════════════════

    def _get_org_id_safe(self) -> str | None:
        """Obtém org_id de forma segura (delegando para HubScreen).

        Returns:
            org_id ou None se não disponível.
        """
        if self._hub_screen and hasattr(self._hub_screen, "_get_org_id_safe"):
            return self._hub_screen._get_org_id_safe()
        return None

    def _get_email_safe(self) -> str | None:
        """Obtém email de forma segura (delegando para HubScreen).

        Returns:
            email ou None se não disponível.
        """
        if self._hub_screen and hasattr(self._hub_screen, "_get_email_safe"):
            return self._hub_screen._get_email_safe()
        return None

    def _get_user_id_safe(self) -> str | None:
        """Obtém user_id de forma segura (delegando para HubScreen).

        Returns:
            user_id ou None se não disponível.
        """
        if self._hub_screen and hasattr(self._hub_screen, "_get_user_id_safe"):
            return self._hub_screen._get_user_id_safe()
        return None

    def _get_app(self) -> Any | None:
        """Obtém referência ao MainApp (delegando para HubScreen).

        Returns:
            MainApp ou None se não disponível.
        """
        if self._hub_screen and hasattr(self._hub_screen, "_get_app"):
            return self._hub_screen._get_app()
        return None

    # ═══════════════════════════════════════════════════════════════════════
    # Métodos de Renderização (delegados)
    # ═══════════════════════════════════════════════════════════════════════

    def render_notes(self, notes: list[dict[str, Any]], force: bool = False) -> None:
        """Renderiza lista de notas (delega para HubNotesView).

        Args:
            notes: Lista de notas para renderizar (dicts ou NoteItemView).
            force: Se True, força re-renderização mesmo se cache não mudou.
        """
        # MF-39: Converter NoteItemView para dict se necessário
        notes_as_dicts = []
        for note in notes or []:
            if isinstance(note, dict):
                notes_as_dicts.append(note)
            else:
                # NoteItemView ou objeto similar - converter para dict
                notes_as_dicts.append(
                    {
                        "id": getattr(note, "id", None),
                        "body": getattr(note, "body", ""),
                        "created_at": getattr(note, "created_at", ""),
                        "author_email": getattr(note, "author_email", ""),
                        "author_name": getattr(note, "author_name", ""),
                        "is_pinned": getattr(note, "is_pinned", False),
                        "is_done": getattr(note, "is_done", False),
                    }
                )

        if self._notes_view and hasattr(self._notes_view, "render_notes"):
            # Delegar para HubNotesView
            # MF-38: Corrigido - state é HubState (dataclass), não dict
            state = getattr(self._hub_screen, "state", None)
            author_tags = state.author_tags if state else {}
            author_cache = state.author_cache if state else {}

            self._notes_view.render_notes(
                notes_as_dicts,
                force=force,
                author_tags=author_tags,
                author_names_cache=author_cache,
                hub_screen=self._hub_screen,
                debug_logger=lambda tag: None,  # No-op debug logger
            )
        elif self.notes_history:
            # Fallback: renderização simples direta no widget
            self.update_notes_panel(notes_as_dicts)
