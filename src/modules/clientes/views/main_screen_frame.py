# -*- coding: utf-8 -*-
# pyright: strict, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownParameterType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportUnknownLambdaType=false, reportUntypedBaseClass=false, reportPrivateUsage=false

"""Main screen frame - Classe principal MainScreenFrame (ciclo de vida, wiring).

Responsável pela classe principal MainScreenFrame (ciclo de vida, wiring).
"""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import messagebox
from typing import Any, Callable, Sequence

try:
    import ttkbootstrap as tb
except Exception:
    from tkinter import ttk

    tb = ttk  # fallback

from src.modules.clientes.controllers.batch_operations import BatchOperationsCoordinator
from src.modules.clientes.controllers.connectivity import ClientesConnectivityController
from src.modules.clientes.controllers.connectivity_state_manager import ConnectivityStateManager
from src.modules.clientes.controllers.event_router import EventRouter
from src.modules.clientes.controllers.main_screen_actions import MainScreenActions
from src.modules.clientes.controllers.pick_mode_manager import PickModeManager
from src.modules.clientes.controllers.selection_manager import SelectionManager
from src.modules.clientes.viewmodel import ClienteRow, ClientesViewModel
from src.modules.clientes.views.main_screen_helpers import (
    DEFAULT_ORDER_LABEL,
    ORDER_CHOICES,
    normalize_order_choices,
    normalize_order_label,
)
from src.modules.clientes.views.pick_mode import PickModeController

# Importar mixins
from .main_screen_batch import MainScreenBatchMixin
from .main_screen_dataflow import MainScreenDataflowMixin
from .main_screen_events import MainScreenEventsMixin

log = logging.getLogger("app_gui")

__all__ = ["MainScreenFrame"]


class MainScreenFrame(
    MainScreenEventsMixin,
    MainScreenDataflowMixin,
    MainScreenBatchMixin,
    tb.Frame,  # pyright: ignore[reportGeneralTypeIssues]
):
    """Frame da tela principal (lista de clientes + ações).

    Responsável pela UI Tkinter e orquestração de managers headless.
    Recebe callbacks do App para operações de negócio.
    """

    def __init__(
        self,
        master: tk.Misc,
        *,
        on_new: Callable[[], None] | None = None,
        on_edit: Callable[[], None] | None = None,
        on_delete: Callable[[], None] | None = None,
        on_upload: Callable[[], None] | None = None,
        on_open_subpastas: Callable[[], None] | None = None,
        on_open_lixeira: Callable[[], None] | None = None,
        on_obrigacoes: Callable[[], None] | None = None,
        app: Any | None = None,
        order_choices: dict[str, tuple[str | None, bool]] | None = None,
        default_order_label: str = DEFAULT_ORDER_LABEL,
        on_upload_folder: Callable[[], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, **kwargs)  # pyright: ignore[reportCallIssue] - tb.Frame aceita master posicional

        # Atributos básicos (callbacks e configuração)
        self.app: Any | None = app
        self.on_new: Callable[[], None] | None = on_new
        self.on_edit: Callable[[], None] | None = on_edit
        self.on_delete: Callable[[], None] | None = on_delete
        self.on_upload: Callable[[], None] | None = on_upload
        self.on_upload_folder: Callable[[], None] | None = on_upload_folder
        self.on_open_subpastas: Callable[[], None] | None = on_open_subpastas
        self.on_open_lixeira: Callable[[], None] | None = on_open_lixeira
        self.on_obrigacoes: Callable[[], None] | None = on_obrigacoes

        self._order_choices: dict[str, tuple[str | None, bool]] = normalize_order_choices(
            order_choices or ORDER_CHOICES
        )

        self._default_order_label: str = normalize_order_label(default_order_label) or DEFAULT_ORDER_LABEL
        if self._default_order_label not in self._order_choices:
            self._default_order_label = DEFAULT_ORDER_LABEL

        self._buscar_after: str | None = None
        self._uploading_busy: bool = False
        self._last_cloud_state: str = "unknown"
        self._current_order_by: str | None = None
        self._status_menu_row: str | None = None
        self._status_menu_cliente: int | None = None

        # ViewModel e managers headless
        self._vm: ClientesViewModel = ClientesViewModel(
            order_choices=self._order_choices,
            default_order_label=self._default_order_label,
            author_resolver=self._resolve_author_initial,
        )

        self._batch_coordinator = BatchOperationsCoordinator(self._vm)
        self._selection_manager = SelectionManager(all_clients=[])
        # MS-32: UiStateManager removido - lógica migrada para MainScreenController
        # MS-34: FilterSortManager removido - lógica migrada para MainScreenController
        self._connectivity_state_manager = ConnectivityStateManager()
        self._pick_mode_manager = PickModeManager()
        self._event_router: EventRouter = EventRouter()

        # Controllers com conhecimento de Tk
        self._pick_controller: PickModeController = PickModeController(self)
        self._connectivity: ClientesConnectivityController = ClientesConnectivityController(self)

        # Actions Controller (delegação de lógica de botões principais)
        self._actions = MainScreenActions(
            vm=self._vm,
            batch=self._batch_coordinator,
            selection=self._selection_manager,
            view=self,
            on_new_callback=on_new,
            on_edit_callback=on_edit,
            on_open_subpastas_callback=on_open_subpastas,
            on_upload_callback=on_upload,
            on_upload_folder_callback=on_upload_folder,
            on_open_lixeira_callback=on_open_lixeira,
            on_obrigacoes_callback=on_obrigacoes,
        )

        # Atributos de estado interno
        self._pick_mode: bool = False
        self._on_pick: Callable[[dict[str, Any]], None] | None = None
        self._return_to: Callable[[], None] | None = None
        self._saved_toolbar_state: dict[tk.Misc, dict[str, Any] | None] = {}
        self._current_rows: list[ClienteRow] = []

        # Construção da UI via builders
        from src.modules.clientes.views.main_screen_ui_builder import (
            bind_main_events,
            build_footer,
            build_pick_mode_banner,
            build_toolbar,
            build_tree_and_column_controls,
            setup_app_references,
        )

        build_toolbar(self)
        build_tree_and_column_controls(self)
        build_footer(self)
        build_pick_mode_banner(self)
        bind_main_events(self)
        setup_app_references(self)

        # Inicialização final
        self._update_main_buttons_state()
        self._connectivity.start()

    def destroy(self) -> None:
        """Cleanup ao destruir o frame.

        Garante que os menus da topbar sejam reabilitados caso o usuário
        saia do modo seleção navegando para outro módulo (FIX-CLIENTES-007).
        """
        snapshot = self._pick_mode_manager.get_snapshot()
        if snapshot.is_pick_mode_active and self.app and hasattr(self.app, "topbar"):
            try:
                self.app.topbar.set_pick_mode_active(False)
            except Exception as exc:  # noqa: BLE001
                log.debug("Erro ao reabilitar menus da topbar no destroy: %s", exc)

        # Chama o destroy original do ttk.Frame
        super().destroy()

    def set_uploading(self, busy: bool) -> None:
        """Desabilita ações de upload enquanto um job de upload está em execução."""

        busy = bool(busy)

        if busy == self._uploading_busy:
            return

        self._uploading_busy = busy

        self._update_main_buttons_state()

    def _enter_pick_mode_ui(self) -> None:
        """Configura a tela para o modo seleção de clientes.

        Desabilita botões de CRUD e menus da topbar (FIX-CLIENTES-005/007).
        """
        log.debug("FIX-007: entrando em pick mode na tela de clientes")

        # Obter estado atual da lixeira antes de entrar em pick mode
        trash_button = getattr(self, "btn_lixeira", None)
        current_trash_state: str | None = None
        if trash_button is not None:
            try:
                current_trash_state = str(trash_button["state"])
            except Exception as exc:  # noqa: BLE001
                log.debug("Falha ao obter estado do botão lixeira: %s", exc)

        # Entrar em pick mode e obter snapshot
        snapshot = self._pick_mode_manager.enter_pick_mode(trash_button_current_state=current_trash_state)

        # Aplicar snapshot: Footer
        if snapshot.should_disable_crud_buttons:
            if hasattr(self, "footer") and hasattr(self.footer, "enter_pick_mode"):  # pyright: ignore[reportAttributeAccessIssue]
                try:
                    self.footer.enter_pick_mode()  # pyright: ignore[reportAttributeAccessIssue]
                except Exception as exc:  # noqa: BLE001
                    log.debug("Falha ao entrar em pick mode no footer: %s", exc)

        # Aplicar snapshot: Lixeira (fica VISÍVEL mas DESABILITADA)
        if snapshot.should_disable_trash_button and trash_button is not None:
            try:
                trash_button.configure(state="disabled")
            except Exception as exc:  # noqa: BLE001
                log.debug("Falha ao desabilitar botão lixeira: %s", exc)

        # Aplicar snapshot: Menus da topbar (Conversor PDF, etc.)
        if snapshot.should_disable_topbar_menus:
            if self.app is not None and hasattr(self.app, "topbar"):
                try:
                    self.app.topbar.set_pick_mode_active(True)
                except Exception as exc:  # noqa: BLE001
                    log.debug("Falha ao desabilitar menus no pick mode: %s", exc)

    def _leave_pick_mode_ui(self) -> None:
        """Restaura a tela para o modo normal após sair do modo seleção.

        Reabilita botões de CRUD e menus da topbar (FIX-CLIENTES-005/007).
        """
        # Sair de pick mode e obter snapshot
        snapshot = self._pick_mode_manager.exit_pick_mode()

        # Restaurar estados dos botões via atualização central
        try:
            self._update_main_buttons_state()
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao restaurar estados dos botões: %s", exc)

        # FIX-CLIENTES-007: Restaurar estado da Lixeira após _update_main_buttons_state
        # para garantir que nosso estado salvo prevaleça sobre a lógica de conectividade
        trash_button = getattr(self, "btn_lixeira", None)
        if trash_button is not None:
            try:
                previous_state = self._pick_mode_manager.get_saved_trash_button_state()
                trash_button.configure(state=previous_state)
            except Exception as exc:  # noqa: BLE001
                log.debug("Falha ao restaurar botão lixeira: %s", exc)

        # Aplicar snapshot: Footer
        if not snapshot.should_disable_crud_buttons:
            if hasattr(self, "footer") and hasattr(self.footer, "leave_pick_mode"):  # pyright: ignore[reportAttributeAccessIssue]
                try:
                    self.footer.leave_pick_mode()  # pyright: ignore[reportAttributeAccessIssue]
                except Exception as exc:  # noqa: BLE001
                    log.debug("Falha ao sair de pick mode no footer: %s", exc)

        # Aplicar snapshot: Menus da topbar
        if not snapshot.should_disable_topbar_menus:
            if self.app is not None and hasattr(self.app, "topbar"):
                try:
                    self.app.topbar.set_pick_mode_active(False)
                except Exception as exc:  # noqa: BLE001
                    log.debug("Falha ao reabilitar menus após pick mode: %s", exc)

        # Restaurar bind de duplo clique para usar o EventRouter após sair do pick mode
        self._rebind_double_click_handler()

    def enter_pick_mode(self) -> None:
        """API pública para ativar modo pick (usado por PickModeController)."""
        self._enter_pick_mode_ui()

    def exit_pick_mode(self) -> None:
        """API pública para desativar modo pick (usado por PickModeController)."""
        self._leave_pick_mode_ui()

    def is_pick_mode_active(self) -> bool:
        """API pública para verificar se pick mode está ativo.

        Returns:
            True se pick mode está ativo, False caso contrário.
        """
        snapshot = self._pick_mode_manager.get_snapshot()
        return snapshot.is_pick_mode_active

    def _start_connectivity_monitor(self) -> None:
        self._connectivity.start()

    def _get_selected_values(self) -> Sequence[Any] | None:
        try:
            selection = self.client_list.selection()  # pyright: ignore[reportAttributeAccessIssue]

        except Exception:
            return None

        if not selection:
            return None

        item_id = selection[0]

        try:
            return self.client_list.item(item_id, "values")  # pyright: ignore[reportAttributeAccessIssue]

        except Exception:
            return None

    def _resolve_author_initial(self, email: str) -> str:
        """Resolve inicial do autor reutilizando os helpers do hub."""

        raw = email or ""

        try:
            from src.modules.hub.services.authors_service import get_author_display_name

            display = get_author_display_name(self, raw, start_async_fetch=False)

            return display or raw

        except Exception:
            return raw

    def on_delete_selected_clients(self) -> None:
        """Aciona a exclusão (envio para lixeira) dos clientes selecionados."""
        if self.on_delete:
            self._invoke_safe(self.on_delete)

    # =========================================================================
    # Modo de seleção para integração com Senhas
    # =========================================================================

    def start_pick(
        self,
        on_pick: Callable[[dict[str, Any]], None],
        return_to: Callable[[], None] | None = None,
        *,
        banner_text: str | None = None,
    ) -> None:
        """API pública usada pelo router para modo pick (Senhas)."""

        self._pick_controller.start_pick(on_pick=on_pick, return_to=return_to, banner_text=banner_text)
        # Garantir que o duplo clique continue roteando via EventRouter mesmo em pick mode
        self._rebind_double_click_handler()

    def _on_pick_cancel(self, *_: object) -> None:
        self._pick_controller.cancel_pick()

    def _on_pick_confirm(self, *_: object) -> None:
        self._pick_controller.confirm_pick()

    @staticmethod
    def _invoke(callback: Callable[[], None] | None) -> None:
        if callable(callback):
            callback()

    def _invoke_safe(self, callback: Callable[[], None] | None) -> None:
        """Invoca callback apenas se NÃO estiver em modo seleção."""
        snapshot = self._pick_mode_manager.get_snapshot()
        if snapshot.is_pick_mode_active:
            return

        if callable(callback):
            callback()

    def _handle_action_result(self, result: Any, context: str = "ação") -> None:
        """Interpreta ActionResult e mostra messagebox apropriada.

        Args:
            result: ActionResult retornado pelo controller
            context: Contexto da ação (usado em mensagens de erro)
        """
        from src.modules.clientes.controllers.main_screen_actions import ActionResult

        if not isinstance(result, ActionResult):
            return

        # kind="ok" → nenhuma mensagem (ação executada com sucesso)
        if result.kind == "ok":
            return

        # kind="no_callback" → erro de configuração (não deveria acontecer)
        if result.kind == "no_callback":
            messagebox.showerror(
                "Erro de Configuração",
                result.message or f"Callback não configurado para {context}.",
                parent=self,
            )
            return

        # kind="error" → erro durante execução
        if result.kind == "error":
            messagebox.showerror(
                "Erro",
                result.message or f"Erro ao executar {context}.",
                parent=self,
            )
            return

        # kind="no_selection" → aviso de seleção necessária
        if result.kind == "no_selection":
            messagebox.showinfo(
                "Clientes",
                result.message or "Selecione um cliente.",
                parent=self,
            )
            return

        # kind="cancelled" → operação cancelada (sem mensagem)
        if result.kind == "cancelled":
            return
