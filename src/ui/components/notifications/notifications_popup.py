# -*- coding: utf-8 -*-
"""Componente de popup de notificações."""

from __future__ import annotations

import logging
import os
import tkinter as tk
from typing import Any, Callable, Optional

from src.ui.dialogs.rc_dialogs import show_info, show_error, show_warning, ask_yes_no

from src.ui.controllers import NotificationVM, TopbarNotificationsController
from src.ui.ctk_config import ctk
from src.ui.widgets.ctk_tableview import CTkTableView
from src.ui.widgets.button_factory import make_btn
from src.utils.resource_path import resource_path

_log = logging.getLogger(__name__)


class NotificationsPopup:
    """Popup de notificações com Treeview, detalhes e ações.

    Gerencia o Toplevel de notificações, incluindo:
    - Treeview com lista de notificações
    - Detalhes ao duplo clique
    - Botões: Marcar Tudo como Lido, Silenciar, Fechar
    """

    def __init__(
        self,
        parent_widget,
        on_mark_all_read: Optional[Callable[[], bool]] = None,
        on_reload_notifications: Optional[Callable[[], None]] = None,
        on_update_count: Optional[Callable[[int], None]] = None,
        on_delete_selected: Optional[Callable[[str], bool]] = None,
        on_delete_all: Optional[Callable[[], bool]] = None,
    ):
        """Inicializa o gerenciador de popup.

        Args:
            parent_widget: Widget pai (para criar Toplevel)
            on_mark_all_read: Callback para marcar tudo como lido (retorna bool)
            on_reload_notifications: Callback para recarregar notificações
            on_update_count: Callback para atualizar contador (zerar badge)
            on_delete_selected: Callback para excluir notificação selecionada (pra mim)
            on_delete_all: Callback para excluir todas notificações (pra mim)
        """
        self._parent = parent_widget
        self._on_mark_all_read = on_mark_all_read
        self._on_reload_notifications = on_reload_notifications
        self._on_update_count = on_update_count
        self._on_delete_selected = on_delete_selected
        self._on_delete_all = on_delete_all

        # Estado interno
        self._popup: tk.Toplevel | None = None
        self._tree: CTkTableView | None = None
        self._notifications_data: list[dict[str, Any]] = []
        self._notifications_items: list[NotificationVM] = []  # ViewModels do controller
        self._notifications_by_id: dict[str, NotificationVM] = {}  # id -> ViewModel
        self._controller: TopbarNotificationsController | None = None  # Controller headless
        self._mute_var: tk.BooleanVar | None = None
        self._mute_callback: Any = None

    def is_open(self) -> bool:
        """Verifica se o popup está aberto.

        Returns:
            True se popup existe e está visível
        """
        return self._popup is not None and self._popup.winfo_exists()

    def open(self) -> None:
        """Abre o popup de notificações."""
        if self.is_open():
            # Já está aberto, apenas trazer para frente
            if self._popup is not None:
                try:
                    self._popup.lift()
                    self._popup.focus_force()
                except Exception as exc:
                    # Popup pode ter sido destruído
                    _log.debug("focus_force popup falhou: %s", type(exc).__name__)
            return

        self._create_popup()

    def close(self) -> None:
        """Fecha o popup de notificações."""
        if self.is_open() and self._popup is not None:
            try:
                self._popup.destroy()
            except Exception as exc:
                # Popup pode já ter sido destruído
                _log.debug("destroy popup falhou: %s", type(exc).__name__)
        self._popup = None
        self._tree = None

    def toggle(self) -> None:
        """Alterna entre abrir e fechar o popup."""
        if self.is_open():
            self.close()
        else:
            self.open()

    def set_notifications_data(
        self,
        notifications: list[dict[str, Any]],
        controller: TopbarNotificationsController | None = None,
        mute_callback: Any = None,
    ) -> None:
        """Atualiza dados das notificações.

        Args:
            notifications: Lista de notificações (dicts brutos)
            controller: Controller headless para formatar dados (opcional)
            mute_callback: Callback para toggle de mute (recebe bool)
        """
        self._notifications_data = notifications
        self._controller = controller
        self._mute_callback = mute_callback

        # Processar com controller se disponível
        if self._controller:
            self._notifications_items = self._controller.build_items(notifications)
            self._notifications_by_id = {item.id: item for item in self._notifications_items}
        else:
            # Fallback: manter compatibilidade sem controller
            self._notifications_items = []
            self._notifications_by_id = {}

        # Se popup estiver aberto, atualizar
        if self.is_open():
            self._refresh_tree()

    def _create_popup(self) -> None:
        """Cria e exibe o popup de notificações."""
        from src.ui.window_utils import prepare_hidden_window, show_centered_no_flash

        # Criar popup
        popup = ctk.CTkToplevel(self._parent)
        popup.title("Notificações")
        popup.geometry("520x330")
        popup.minsize(480, 300)
        popup.transient(self._parent.winfo_toplevel())

        # Aplicar ícone do app
        try:
            icon_path = resource_path("rc.ico")
            if os.path.exists(icon_path):
                popup.iconbitmap(icon_path)
        except Exception:
            # Fallback para PNG com iconphoto
            try:
                png_path = resource_path("rc.png")
                if os.path.exists(png_path):
                    icon_img = tk.PhotoImage(file=png_path)
                    popup.iconphoto(True, icon_img)
                    # Guardar referência para evitar garbage collection
                    popup._icon_img = icon_img  # type: ignore[attr-defined]
            except Exception as exc:
                # Sem ícone, continua sem problemas
                _log.debug("icon loading popup falhou: %s", type(exc).__name__)

        # Preparar janela oculta para evitar flash
        prepare_hidden_window(popup)

        # Container principal
        main_frame = ctk.CTkFrame(popup)  # TODO: padding=10 -> usar padx/pady no pack/grid
        main_frame.pack(fill="both", expand=True)

        # Título
        title_label = ctk.CTkLabel(
            main_frame,
            text="Notificações Recentes",
            font=("Arial", 12, "bold"),
        )
        title_label.pack(anchor="w", pady=(0, 10))

        # Frame da Treeview
        tree_frame = ctk.CTkFrame(main_frame)
        tree_frame.pack(fill="both", expand=True)

        # Treeview (CTkTableView)
        columns = ("data", "mensagem", "por")
        tree = CTkTableView(
            tree_frame,
            columns=columns,
            show="headings",
            height=12,
            zebra=True,
        )

        tree.heading("data", text="Data/Hora", anchor="center")
        tree.heading("mensagem", text="Mensagem", anchor="center")
        tree.heading("por", text="Por", anchor="center")

        tree.column("data", width=120, anchor="center", stretch=False)
        tree.column("mensagem", width=420, anchor="center", stretch=True)
        tree.column("por", width=140, anchor="center", stretch=False)

        tree.pack(fill="both", expand=True)

        # Adicionar handler de duplo clique para mostrar detalhes
        tree.bind("<Double-Button-1>", lambda e: self._show_details(tree))

        self._tree = tree

        # Botões
        buttons_frame = ctk.CTkFrame(main_frame)
        buttons_frame.pack(fill="x", pady=(10, 0))

        btn_mark_read = make_btn(
            buttons_frame,
            text="Marcar Tudo como Lido",
            command=self._handle_mark_all_read,
            fg_color="#28a745",
            hover_color="#1e7e34",
            text_color="white",
        )
        btn_mark_read.pack(side="left", padx=(0, 10))

        # Botão Excluir Selecionada (pra mim)
        btn_delete_selected = make_btn(
            buttons_frame,
            text="Excluir Selecionada",
            command=self._handle_delete_selected,
        )
        btn_delete_selected.pack(side="left", padx=(0, 10))

        # Botão Excluir Todas (pra mim)
        btn_delete_all = make_btn(
            buttons_frame,
            text="Excluir Todas (pra mim)",
            command=self._handle_delete_all,
            fg_color="#dc3545",
            hover_color="#c82333",
            text_color="white",
        )
        btn_delete_all.pack(side="left", padx=(0, 10))

        # Checkbutton para silenciar notificações
        self._mute_var = tk.BooleanVar(value=False)
        chk_mute = ctk.CTkCheckBox(
            buttons_frame,
            text="🔕 Silenciar",
            variable=self._mute_var,
            command=self._handle_mute_toggled,
        )
        chk_mute.pack(side="left")

        btn_close = make_btn(
            buttons_frame,
            text="Fechar",
            command=self.close,
        )
        btn_close.pack(side="right")

        # Preencher dados
        self._refresh_tree()

        # Guardar referência
        self._popup = popup  # pyright: ignore[reportAttributeAccessIssue]

        # Mostrar janela centralizada
        show_centered_no_flash(popup, parent=self._parent.winfo_toplevel())

    def _refresh_tree(self) -> None:
        """Atualiza conteúdo da Treeview com notificações."""
        if not self._tree:
            return

        # Limpar árvore
        for item in self._tree.get_children():
            self._tree.delete(item)

        # Preencher com ViewModels
        if not self._notifications_items:
            # Sem notificações
            self._tree.insert(
                "",
                "end",
                values=("--", "Nenhuma notificação recente", "--"),
            )
        else:
            for item in self._notifications_items:
                # Usar controller para formatar linha
                if self._controller:
                    date_str, message, por = self._controller.tree_row(item)
                else:
                    # Fallback sem controller (não deve acontecer)
                    date_str = item.created_at_display
                    message = item.message_display
                    por = item.actor_display

                # Inserir com iid = id da notificação
                self._tree.insert(
                    "",
                    "end",
                    iid=item.id,
                    values=(date_str, message, por),
                )

    def _show_details(self, tree: Any) -> None:
        """Mostra detalhes completos de uma notificação ao dar duplo clique.

        Args:
            tree: Treeview/TableView com notificações
        """
        # Obter item selecionado
        selection = tree.selection()
        if not selection:
            return

        iid = selection[0]

        # Buscar ViewModel pelo iid
        vm = self._notifications_by_id.get(iid)
        if not vm:
            return

        # Usar controller para montar payload de detalhes
        if self._controller:
            payload = self._controller.detail_payload(vm)
        else:
            # Fallback sem controller (não deve acontecer)
            payload = {
                "created_at": vm.created_at_display,
                "module": vm.module or "--",
                "event": vm.event or "--",
                "message": vm.raw.get("message", ""),
                "request_id": vm.request_id or "--",
                "user": vm.actor_display,
            }

        # Formatar mensagem de detalhes
        details = (
            f"Data/Hora: {payload['created_at']}\n"
            f"Módulo: {payload['module']}\n"
            f"Evento: {payload['event']}\n"
            f"Mensagem: {payload['message']}\n\n"
            f"Request ID: {payload['request_id']}\n"
            f"Usuário: {payload['user']}"
        )

        show_info(self._popup, "Detalhes da Notificação", details)

    def _handle_mute_toggled(self) -> None:
        """Callback quando usuário alterna o estado de silenciar."""
        if not self._mute_var:
            return

        is_muted = self._mute_var.get()

        # Chamar callback para atualizar flag
        if callable(self._mute_callback):
            try:
                self._mute_callback(is_muted)
            except Exception as exc:  # noqa: BLE001
                _log.debug("Falha ao executar mute_callback: %s", exc)

    def _handle_mark_all_read(self) -> None:
        """Marca todas notificações como lidas."""
        # Chamar callback para executar mark_all_read
        if callable(self._on_mark_all_read):
            try:
                success = self._on_mark_all_read()
                if not success:
                    show_error(
                        self._popup,
                        "Erro",
                        "Falha ao marcar notificações como lidas. Tente novamente.",
                    )
                    return
            except Exception as exc:  # noqa: BLE001
                _log.exception("Falha ao executar on_mark_all_read: %s", exc)
                show_error(
                    self._popup,
                    "Erro",
                    f"Erro ao marcar notificações como lidas: {exc}",
                )
                return

        # Sucesso: zerar badge imediatamente
        if callable(self._on_update_count):
            try:
                self._on_update_count(0)
            except Exception as exc:  # noqa: BLE001
                _log.debug("Falha ao atualizar contador: %s", exc)

        # Recarregar lista
        if callable(self._on_reload_notifications):
            try:
                self._on_reload_notifications()
            except Exception as exc:  # noqa: BLE001
                _log.debug("Falha ao recarregar notificações: %s", exc)

    def _handle_delete_selected(self) -> None:
        """Exclui a notificação selecionada (apenas para o usuário atual)."""
        if not self._tree:
            return

        # Obter item selecionado
        selection = self._tree.selection()
        if not selection:
            show_warning(
                self._popup,
                "Aviso",
                "Selecione uma notificação para excluir.",
            )
            return

        iid = selection[0]

        # Verificar se é placeholder
        values = self._tree.item(iid, "values")
        if values and "Nenhuma notificação recente" in str(values):
            return

        # Confirmar exclusão
        confirm = ask_yes_no(
            self._popup,
            "Confirmar Exclusão",
            "Excluir esta notificação da SUA lista?\n\n(Outros usuários ainda verão esta notificação)",
        )
        if not confirm:
            return

        # Chamar callback para excluir
        if callable(self._on_delete_selected):
            try:
                success = self._on_delete_selected(iid)
                if not success:
                    show_error(
                        self._popup,
                        "Erro",
                        "Falha ao excluir notificação. Tente novamente.",
                    )
                    return
            except Exception as exc:  # noqa: BLE001
                _log.exception("Falha ao executar on_delete_selected: %s", exc)
                show_error(
                    self._popup,
                    "Erro",
                    f"Erro ao excluir notificação: {exc}",
                )
                return

        # Sucesso: recarregar lista
        if callable(self._on_reload_notifications):
            try:
                self._on_reload_notifications()
            except Exception as exc:  # noqa: BLE001
                _log.debug("Falha ao recarregar notificações: %s", exc)

    def _handle_delete_all(self) -> None:
        """Exclui todas as notificações (apenas para o usuário atual)."""
        # Confirmar exclusão
        confirm = ask_yes_no(
            self._popup,
            "Confirmar Exclusão",
            "Excluir TODAS as notificações da SUA lista?\n\n"
            "⚠️ Isso limpa apenas a SUA lista de notificações.\n"
            "Outros usuários não serão afetados.\n\n"
            "Novas notificações continuarão aparecendo normalmente.",
        )
        if not confirm:
            return

        # Chamar callback para excluir todas
        if callable(self._on_delete_all):
            try:
                success = self._on_delete_all()
                if not success:
                    show_error(
                        self._popup,
                        "Erro",
                        "Falha ao excluir notificações. Tente novamente.",
                    )
                    return
            except Exception as exc:  # noqa: BLE001
                _log.exception("Falha ao executar on_delete_all: %s", exc)
                show_error(
                    self._popup,
                    "Erro",
                    f"Erro ao excluir notificações: {exc}",
                )
                return

        # Sucesso: recarregar lista
        if callable(self._on_reload_notifications):
            try:
                self._on_reload_notifications()
            except Exception as exc:  # noqa: BLE001
                _log.debug("Falha ao recarregar notificações: %s", exc)
