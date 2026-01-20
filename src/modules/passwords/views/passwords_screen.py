# -*- coding: utf-8 -*-
"""Tela de gerenciamento de senhas com filtros, tabela e diálogo modal."""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import messagebox
from typing import Any, Callable, Optional

from src.ui.ctk_config import ctk
from src.ui.widgets import CTkTableView

from src.db.domain_types import ClientRow, PasswordRow
from src.modules.passwords.controller import ClientPasswordsSummary, PasswordsController
from src.modules.passwords.passwords_actions import PasswordsActions, PasswordsScreenState
from src.modules.passwords.views.client_passwords_dialog import ClientPasswordsDialog
from src.modules.passwords.views.password_dialog import PasswordDialog

log = logging.getLogger(__name__)
logger = log


# Classes ClientPasswordsDialog e PasswordDialog foram movidas para arquivos separados
# FIX-SENHAS-004: Refatoração para reduzir tamanho do arquivo


class PasswordsScreen(ctk.CTkFrame):
    """Tela de gerenciamento de senhas com layout master-detail (clientes → senhas)."""

    def __init__(
        self,
        master,
        main_window: Optional[Any] = None,
        *,
        controller: Optional[PasswordsController] = None,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        
        # Aplicar padding via geometry manager (pack/grid) dependendo do uso

        self.main_window = main_window
        self.controller = controller or PasswordsController()
        self.actions = PasswordsActions(controller=self.controller)
        self.org_id: Optional[str] = None
        self.user_id: Optional[str] = None
        self.clients: list[ClientRow] = []
        self.passwords: list[PasswordRow] = []
        self._all_passwords: list[PasswordRow] = []
        self._screen_state: Optional[PasswordsScreenState] = None
        self.password_cache: dict[str, str] = {}  # id -> decrypted password
        self._sort_column: Optional[str] = None
        self._sort_order: str = "asc"

        # FIX-SENHAS-001: Cliente selecionado no master-detail
        self._selected_client_id: Optional[str] = None
        self._client_summaries: list[ClientPasswordsSummary] = []

        # FIX-SENHAS-004: Dict para busca rápida de summaries por client_id
        self._client_summaries_by_id: dict[str, ClientPasswordsSummary] = {}

        # Referência ao diálogo aberto (para orquestração do pick mode)
        self._password_dialog: Optional[PasswordDialog] = None
        # Último cliente selecionado durante pick mode
        self._last_selected_client_data: Optional[dict[str, Any]] = None

        self._build_ui()

    def _refresh_data(self) -> None:
        """Recarrega dados do servidor e atualiza a UI master-detail."""
        self._load_all_passwords()
        self._refresh_clients_list()

    def _load_all_passwords(self) -> None:
        """Carrega todas as senhas do servidor."""
        if not self.org_id:
            return
        try:
            self._all_passwords = self.actions.reload_passwords(self.org_id)
        except Exception as e:
            log.exception("Erro ao carregar senhas")
            messagebox.showerror("Erro", f"Falha ao carregar senhas: {e}")

    def _build_ui(self) -> None:
        """Constrói a interface principal com lista única de clientes (FIX-SENHAS-002)."""
        # Filtros no topo
        filters_frame = ctk.CTkFrame(self)
        filters_frame.pack(fill="x", pady=(0, 10))

        # FIX-SENHAS-014: Buscar e Serviço lado a lado, à esquerda, larguras fixas

        # Busca
        ctk.CTkLabel(filters_frame, text="Buscar:").grid(row=0, column=0, sticky="w", padx=(0, 4), pady=4)
        self.search_var = tk.StringVar()
        self.search_entry = ctk.CTkEntry(filters_frame, textvariable=self.search_var, width=300)
        self.search_entry.grid(row=0, column=1, sticky="w", padx=(0, 12), pady=4)
        self.search_entry.bind("<KeyRelease>", lambda e: self._on_search_changed())

        # Serviço
        ctk.CTkLabel(filters_frame, text="Serviço:").grid(row=0, column=2, sticky="w", padx=(0, 4), pady=4)
        self.service_filter_var = tk.StringVar(value="Todos")
        self.service_filter_combo = ctk.CTkComboBox(
            filters_frame,
            variable=self.service_filter_var,
            values=["Todos", "SIFAP", "CRF", "GOV.BR", "E-mail", "Banco", "Outro"],
            state="readonly",
            width=150,
            command=lambda _: self._on_search_changed()
        )
        self.service_filter_combo.grid(row=0, column=3, sticky="w", padx=(0, 0), pady=4)

        # FIX-SENHAS-014: Nenhuma coluna expande (tudo grudado à esquerda)
        for col in range(4):
            filters_frame.columnconfigure(col, weight=0)

        # ===== Lista única de Clientes com Senhas (FIX-SENHAS-002) =====
        clients_frame = ctk.CTkFrame(self)
        clients_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # Label do frame
        ctk.CTkLabel(clients_frame, text="Clientes com Senhas", font=("Arial", 12, "bold")).pack(pady=(5, 5))

        clients_table_frame = ctk.CTkFrame(clients_frame)
        clients_table_frame.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        # FIX-SENHAS-006: Colunas idênticas à tela de Clientes + Qtd. Senhas e Serviços
        clients_columns = ["id", "razao_social", "cnpj", "nome", "whatsapp", "qtd_senhas", "servicos"]
        self.tree_clients = CTkTableView(
            clients_table_frame,
            columns=clients_columns,
            height=15,
            zebra=True
        )
        
        # Cabeçalhos
        self.tree_clients.set_columns([
            "ID",
            "Razão Social",
            "CNPJ",
            "Nome",
            "WhatsApp",
            "Qtd. Senhas",
            "Serviços"
        ])

        # Double-click abre o diálogo de senhas do cliente
        self.tree_clients.bind("<Double-Button-1>", lambda e: self._on_manage_client_passwords_clicked())

        self.tree_clients.pack(fill="both", expand=True)

        # Barra de ações
        actions_frame = ctk.CTkFrame(self)
        actions_frame.pack(fill="x", pady=(10, 0))

        ctk.CTkButton(
            actions_frame,
            text="Nova Senha",
            fg_color=("#2E7D32", "#1B5E20"),
            hover_color=("#1B5E20", "#0D4A11"),
            command=self._on_new_password_clicked,
            width=140,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            actions_frame,
            text="Gerenciar Senhas",
            fg_color=("#757575", "#616161"),
            hover_color=("#616161", "#424242"),
            command=self._on_manage_client_passwords_clicked,
            width=160,
        ).pack(side="left", padx=5)

        # FIX-SENHAS-006: Botão Excluir na tela principal
        ctk.CTkButton(
            actions_frame,
            text="Excluir",
            fg_color=("#D32F2F", "#B71C1C"),
            hover_color=("#B71C1C", "#8B0000"),
            command=self._on_delete_client_passwords_clicked,
            width=140,
        ).pack(side="left", padx=5)

    def _on_search_changed(self) -> None:
        """Handler chamado quando o filtro de busca ou serviço muda."""
        self._refresh_clients_list()

    def _get_selected_client_id(self) -> Optional[str]:
        """Retorna o client_id do cliente selecionado na tree de clientes."""
        iid = self.tree_clients.get_selected_iid()
        if not iid:
            return None
        # O iid do item é o client_id (FIX-SENHAS-005: sempre string)
        return iid

    def _get_selected_client_summary(self) -> Optional[ClientPasswordsSummary]:
        """Retorna o ClientPasswordsSummary do cliente selecionado.

        FIX-SENHAS-004: Usa _client_summaries_by_id para busca O(1).
        """
        client_id = self._get_selected_client_id()
        if not client_id:
            return None
        return self._client_summaries_by_id.get(client_id)

    def _populate_clients_tree(self, summaries: list[ClientPasswordsSummary]) -> None:
        """Preenche a árvore de clientes com os resumos."""
        # Limpa a árvore
        self.tree_clients.clear()

        for summary in summaries:
            # FIX-SENHAS-006: Formata a lista de serviços
            if len(summary.services) <= 3:
                services_text = ", ".join(summary.services)
            else:
                services_text = f"{len(summary.services)} serviços"

            # Insere com as colunas: ID, Razão Social, CNPJ, Nome, WhatsApp, Qtd. Senhas, Serviços
            self.tree_clients.insert(
                "",
                "end",
                iid=str(summary.client_id),  # FIX-SENHAS-005: Converte para string (Treeview sempre retorna str)
                values=[
                    str(summary.client_external_id),  # ID
                    summary.razao_social,  # Razão Social
                    summary.cnpj,  # CNPJ
                    summary.contato_nome,  # Nome
                    summary.whatsapp,  # WhatsApp
                    str(summary.passwords_count),  # Qtd. Senhas
                    services_text,  # Serviços
                ],
            )

    def _refresh_clients_list(self) -> None:
        """Atualiza a lista de clientes com base nos filtros."""
        if not self.org_id:
            return

        raw_search = self.search_var.get().strip()
        search_text = raw_search if raw_search else None
        service_filter = self.service_filter_var.get()

        summaries = self.actions.build_summaries(
            self._all_passwords,
            search_text=search_text,
            service_filter=service_filter,
        )

        self._client_summaries = summaries.all_summaries
        self._client_summaries_by_id = summaries.summaries_by_id

        previous_selection = self._selected_client_id
        self._populate_clients_tree(summaries.filtered_summaries)

        if previous_selection and self.tree_clients.exists(previous_selection):
            self.tree_clients.selection_set(previous_selection)
            self._selected_client_id = previous_selection
        else:
            self._selected_client_id = None

    def _open_edit_password_dialog(
        self, password_data: PasswordRow, *, on_save_callback: Optional[Callable[[], None]] = None
    ) -> None:
        """Abre diálogo de edição para uma senha específica."""
        if not self.org_id or not self.user_id:
            messagebox.showerror("Erro", "Usuário não autenticado.")
            return

        callback = on_save_callback or self._refresh_data

        # Extrai client_id e display do password_data
        client_id = password_data.get("client_id")
        client_display = password_data.get("client_name", "")

        self._password_dialog = PasswordDialog(
            self,
            self.org_id,
            self.user_id,
            self.clients,
            callback,
            password_data,
            controller=self.controller,
            on_select_client=self._on_select_client_from_dialog,
            client_id=client_id,
            client_display=client_display,
        )

    def _on_new_password_clicked(self) -> None:
        """Handler do botão Nova Senha (FIX-SENHAS-004).

        SEMPRE abre o fluxo de pick-mode para seleção de cliente,
        independente de haver ou não cliente selecionado na lista.
        """
        # FIX-SENHAS-004: Sempre usar pick-mode, não depende de seleção
        self._open_new_password_flow_with_client_picker()

    def _open_new_password_dialog_for_client(
        self, client_id: str, *, on_save_callback: Optional[Callable[[], None]] = None
    ) -> None:
        """Abre diálogo de nova senha já travado no cliente especificado."""
        if not self.org_id or not self.user_id:
            messagebox.showerror("Erro", "Usuário não autenticado.")
            return

        # FIX-SENHAS-004: Busca no dict para O(1)
        # FIX-SENHAS-005: Converte client_id para string (dict usa chaves string)
        summary = self._client_summaries_by_id.get(str(client_id))
        if not summary:
            messagebox.showerror("Erro", "Cliente não encontrado na lista de resumos.")
            return

        callback = on_save_callback or self._refresh_data

        # FIX-SENHAS-006: Usa razao_social ao invés de display_name
        self._password_dialog = PasswordDialog(
            self,
            self.org_id,
            self.user_id,
            self.clients,
            callback,
            controller=self.controller,
            on_select_client=self._on_select_client_from_dialog,
            client_id=client_id,
            client_display=f"{summary.razao_social} ({summary.cnpj})" if summary.cnpj else summary.razao_social,
        )

    def _open_new_password_flow_with_client_picker(self) -> None:
        """Abre o pick mode de Clientes para escolher cliente antes de criar senha."""
        app = self._get_main_app()
        if not app:
            messagebox.showerror("Erro", "Não foi possível acessar a tela de clientes.")
            return

        from src.modules.main_window.controller import start_client_pick_mode, navigate_to

        # Usar nova API explícita para modo seleção de Senhas
        start_client_pick_mode(
            app,
            on_client_picked=self._handle_client_picked_for_new_password,
            banner_text="🔍 Modo seleção: escolha um cliente para criar nova senha",
            return_to=lambda: navigate_to(app, "passwords"),
        )

    def _handle_client_picked_for_new_password(self, client_data: dict[str, Any]) -> None:
        """Callback chamado pelo pick mode de Clientes ao escolher cliente para Nova Senha."""
        # Abre o diálogo de Nova Senha já com o cliente preenchido
        self._open_new_password_dialog(client_data=client_data)

    def _open_new_password_dialog(self, *, client_data: Optional[dict[str, Any]] = None) -> None:
        """Abre diálogo para nova senha, opcionalmente com cliente pré-selecionado."""
        if not self.org_id or not self.user_id:
            messagebox.showerror("Erro", "Usuário não autenticado.")
            return
        if self.org_id is None or self.user_id is None:
            logger.error("PasswordsScreen._open_new_password_dialog chamado sem org_id ou user_id definidos.")
            return

        # Extrai client_id e display se houver dados
        client_id = None
        client_display = None
        if client_data:
            client_id = str(client_data.get("id", ""))
            razao = client_data.get("razao_social", "")
            cnpj = client_data.get("cnpj", "")
            client_display = f"ID {client_id} – {razao} ({cnpj})" if cnpj else f"ID {client_id} – {razao}"

        self._password_dialog = PasswordDialog(
            self,
            self.org_id,
            self.user_id,
            self.clients,
            self._refresh_data,
            controller=self.controller,
            on_select_client=self._on_select_client_from_dialog,
            client_id=client_id,
            client_display=client_display,
        )

    def _on_manage_client_passwords_clicked(self) -> None:
        """Handler do botão Gerenciar Senhas: abre diálogo com todas as senhas do cliente (FIX-SENHAS-004)."""
        summary = self._get_selected_client_summary()

        if not summary:
            messagebox.showerror("Erro", "Selecione um cliente na lista.")
            return

        if not self.org_id or not self.user_id:
            messagebox.showerror("Erro", "Usuário não autenticado.")
            return

        try:
            ClientPasswordsDialog(
                self,
                self.controller,
                summary,
                self.org_id,
                self.user_id,
                self.clients,
                on_close_refresh=self._refresh_data,
            )
        except Exception as e:
            logger.exception("Erro ao abrir diálogo de gerenciamento de senhas")
            messagebox.showerror("Erro", f"Falha ao abrir diálogo: {e}")

    def _on_delete_client_passwords_clicked(self) -> None:
        """Handler do botão Excluir: apaga todas as senhas do cliente selecionado (FIX-SENHAS-006)."""
        summary = self._get_selected_client_summary()
        if summary is None:
            messagebox.showerror("Erro", "Selecione um cliente na lista para excluir as senhas.")
            return

        # Formata label do cliente para confirmação
        client_label = f"ID {summary.client_external_id} – {summary.razao_social} ({summary.cnpj})"

        if not messagebox.askyesno(
            "Confirmar exclusão",
            (
                "Deseja realmente excluir TODAS as senhas desse cliente?\n\n"
                f"{client_label}\n\n"
                "Esta ação não pode ser desfeita."
            ),
            parent=self,
        ):
            return

        if not self.org_id:
            messagebox.showerror("Erro", "Organização não identificada.")
            return

        try:
            count = self.actions.delete_client_passwords(self.org_id, summary.client_id)

            # Recarrega lista de clientes com senhas
            self._load_all_passwords()
            self._refresh_clients_list()

            messagebox.showinfo(
                "Sucesso",
                f"{count} senha(s) excluída(s) com sucesso.",
                parent=self,
            )
        except Exception as e:
            logger.exception("Erro ao excluir senhas do cliente")
            messagebox.showerror("Erro", f"Falha ao excluir senhas: {e}", parent=self)

    def _on_select_client_from_dialog(self) -> None:
        """Chamado pelo dialog quando o usuário clica no botão 'Selecionar...'."""
        app = self._get_main_app()
        if not app:
            return

        from src.modules.main_window.controller import start_client_pick_mode, navigate_to

        # Usar nova API explícita para modo seleção de Senhas
        start_client_pick_mode(
            app,
            on_client_picked=self._handle_client_picked,
            banner_text="🔍 Modo seleção: escolha um cliente para gerenciar senhas",
            return_to=lambda: navigate_to(app, "passwords"),
        )

    def _handle_client_picked(self, client_data: dict[str, Any]) -> None:
        """Callback vindo do pick mode de Clientes."""
        self._last_selected_client_data = client_data

        # Garante que existe um dialog (se usuário fechou, recria)
        if self._password_dialog is None or not self._password_dialog.is_visible():
            self._open_new_password_dialog(client_data=client_data)
        else:
            self._password_dialog.set_client_from_data(client_data)

    def _get_main_app(self) -> Optional[Any]:
        """Obtém referência ao app principal."""
        if self.main_window:
            return self.main_window
        # Fallback: navegar pela hierarquia
        widget = self.master
        while widget:
            if hasattr(widget, "show_frame") and hasattr(widget, "_main_frame_ref"):
                return widget
            widget = getattr(widget, "master", None)
        return None

    def reload_passwords(self) -> None:
        """Recarrega as senhas e atualiza a lista de clientes."""
        self._refresh_clients_list()

    def on_show(self) -> None:
        """Callback chamado ao exibir a tela."""
        try:
            main_app = self._get_main_app() or self.winfo_toplevel()
            state = self.actions.bootstrap_screen(main_app)
        except Exception as e:
            log.exception("Erro ao inicializar tela de senhas")
            messagebox.showerror("Erro", f"Falha ao inicializar: {e}")
            return

        self._screen_state = state
        self.org_id = state.org_id
        self.user_id = state.user_id
        self.clients = state.clients
        self._all_passwords = state.all_passwords
        self._refresh_clients_list()
