# -*- coding: utf-8 -*-
"""Tela de gerenciamento de senhas com filtros, tabela e diálogo modal."""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable, Optional

import ttkbootstrap as tb

from data.domain_types import ClientRow, PasswordRow
from src.modules.passwords.controller import ClientPasswordsSummary, PasswordsController
from src.modules.passwords.views.client_passwords_dialog import ClientPasswordsDialog
from src.modules.passwords.views.password_dialog import PasswordDialog

log = logging.getLogger(__name__)
logger = log


# Classes ClientPasswordsDialog e PasswordDialog foram movidas para arquivos separados
# FIX-SENHAS-004: Refatoração para reduzir tamanho do arquivo


class PasswordsScreen(tb.Frame):
    """Tela de gerenciamento de senhas com layout master-detail (clientes → senhas)."""

    def __init__(
        self,
        master,
        main_window: Optional[Any] = None,
        *,
        controller: Optional[PasswordsController] = None,
        **kwargs,
    ) -> None:
        super().__init__(master, padding=16, **kwargs)

        self.main_window = main_window
        self.controller = controller or PasswordsController()
        self.org_id: Optional[str] = None
        self.user_id: Optional[str] = None
        self.clients: list[ClientRow] = []
        self.passwords: list[PasswordRow] = []
        self._all_passwords: list[PasswordRow] = []
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
            self._all_passwords = self.controller.load_all_passwords(self.org_id)
        except Exception as e:
            log.exception("Erro ao carregar senhas")
            messagebox.showerror("Erro", f"Falha ao carregar senhas: {e}")

    def _build_ui(self) -> None:
        """Constrói a interface principal com lista única de clientes (FIX-SENHAS-002)."""
        # Filtros no topo
        filters_frame = tb.Frame(self)
        filters_frame.pack(fill="x", pady=(0, 10))

        # FIX-SENHAS-014: Buscar e Serviço lado a lado, à esquerda, larguras fixas

        # Busca
        tb.Label(filters_frame, text="Buscar:").grid(row=0, column=0, sticky="w", padx=(0, 4), pady=4)
        self.search_var = tk.StringVar()
        self.search_entry = tb.Entry(filters_frame, textvariable=self.search_var, width=40)
        self.search_entry.grid(row=0, column=1, sticky="w", padx=(0, 12), pady=4)
        self.search_entry.bind("<KeyRelease>", lambda e: self._on_search_changed())

        # Serviço
        tb.Label(filters_frame, text="Serviço:").grid(row=0, column=2, sticky="w", padx=(0, 4), pady=4)
        self.service_filter_var = tk.StringVar(value="Todos")
        self.service_filter_combo = tb.Combobox(
            filters_frame,
            textvariable=self.service_filter_var,
            values=["Todos", "SIFAP", "CRF", "GOV.BR", "E-mail", "Banco", "Outro"],
            state="readonly",  # FIX-SENHAS-015: Somente seleção, sem digitar
            width=20,  # FIX-SENHAS-014: Largura pequena ao lado do Buscar
        )
        self.service_filter_combo.grid(row=0, column=3, sticky="w", padx=(0, 0), pady=4)
        self.service_filter_combo.bind("<<ComboboxSelected>>", lambda e: self._on_search_changed())

        # FIX-SENHAS-014: Nenhuma coluna expande (tudo grudado à esquerda)
        for col in range(4):
            filters_frame.columnconfigure(col, weight=0)

        # ===== Lista única de Clientes com Senhas (FIX-SENHAS-002) =====
        clients_frame = tb.LabelFrame(self, text="Clientes com Senhas", padding=5)
        clients_frame.pack(fill="both", expand=True, pady=(0, 10))

        clients_table_frame = tb.Frame(clients_frame)
        clients_table_frame.pack(fill="both", expand=True)

        # FIX-SENHAS-006: Colunas idênticas à tela de Clientes + Qtd. Senhas e Serviços
        clients_columns = ("id", "razao_social", "cnpj", "nome", "whatsapp", "qtd_senhas", "servicos")
        self.tree_clients = ttk.Treeview(
            clients_table_frame,
            columns=clients_columns,
            show="headings",
            selectmode="browse",
            height=15,
        )

        # Mostra apenas os headings, sem coluna raiz (#0)
        self.tree_clients["show"] = "headings"
        self.tree_clients.column("#0", width=0, stretch=False)

        # Cabeçalhos centralizados
        self.tree_clients.heading("id", text="ID", anchor="center")
        self.tree_clients.heading("razao_social", text="Razão Social", anchor="center")
        self.tree_clients.heading("cnpj", text="CNPJ", anchor="center")
        self.tree_clients.heading("nome", text="Nome", anchor="center")
        self.tree_clients.heading("whatsapp", text="WhatsApp", anchor="center")
        self.tree_clients.heading("qtd_senhas", text="Qtd. Senhas", anchor="center")
        self.tree_clients.heading("servicos", text="Serviços", anchor="center")

        # Larguras base mais equilibradas (todas centralizadas)
        self.tree_clients.column("id", width=60, anchor="center", stretch=False)
        self.tree_clients.column("razao_social", width=230, anchor="center", stretch=False)
        self.tree_clients.column("cnpj", width=150, anchor="center", stretch=False)
        self.tree_clients.column("nome", width=200, anchor="center", stretch=False)
        self.tree_clients.column("whatsapp", width=170, anchor="center", stretch=False)
        self.tree_clients.column("qtd_senhas", width=90, anchor="center", stretch=False)
        self.tree_clients.column("servicos", width=200, anchor="center", stretch=False)

        clients_scrollbar = ttk.Scrollbar(clients_table_frame, orient="vertical", command=self.tree_clients.yview)
        self.tree_clients.configure(yscrollcommand=clients_scrollbar.set)

        # Double-click abre o diálogo de senhas do cliente
        self.tree_clients.bind("<Double-1>", lambda e: self._on_manage_client_passwords_clicked())

        # Bloqueia redimensionamento de colunas
        self.tree_clients.bind("<Button-1>", self._on_clients_tree_heading_click)

        # Ajusta a largura da coluna "servicos" para ocupar o espaço restante
        self.tree_clients.bind("<Configure>", self._on_clients_tree_configure)

        self.tree_clients.pack(side="left", fill="both", expand=True)
        clients_scrollbar.pack(side="right", fill="y")

        # Barra de ações
        actions_frame = tb.Frame(self)
        actions_frame.pack(fill="x", pady=(10, 0))

        tb.Button(
            actions_frame,
            text="Nova Senha",
            bootstyle="success",
            command=self._on_new_password_clicked,
            width=14,
        ).pack(side="left", padx=5)

        tb.Button(
            actions_frame,
            text="Gerenciar Senhas",
            bootstyle="secondary",
            command=self._on_manage_client_passwords_clicked,
            width=16,
        ).pack(side="left", padx=5)

        # FIX-SENHAS-006: Botão Excluir na tela principal
        tb.Button(
            actions_frame,
            text="Excluir",
            bootstyle="danger",
            command=self._on_delete_client_passwords_clicked,
            width=14,
        ).pack(side="left", padx=5)

    def _on_search_changed(self) -> None:
        """Handler chamado quando o filtro de busca ou serviço muda."""
        self._refresh_clients_list()

    def _get_selected_client_id(self) -> Optional[str]:
        """Retorna o client_id do cliente selecionado na tree de clientes."""
        selection = self.tree_clients.selection()
        if not selection:
            return None
        # O iid do item é o client_id (FIX-SENHAS-005: sempre string)
        return selection[0]

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
        for item in self.tree_clients.get_children():
            self.tree_clients.delete(item)

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
                values=(
                    summary.client_external_id,  # ID
                    summary.razao_social,  # Razão Social
                    summary.cnpj,  # CNPJ
                    summary.contato_nome,  # Nome
                    summary.whatsapp,  # WhatsApp
                    summary.passwords_count,  # Qtd. Senhas
                    services_text,  # Serviços
                ),
            )

    def _refresh_clients_list(self) -> None:
        """Atualiza a lista de clientes com base nos filtros."""
        if not self.org_id:
            return

        # FIX-SENHAS-004: Criar _client_summaries e _client_summaries_by_id de TODAS as senhas
        # para que os diálogos sempre encontrem o cliente, independente dos filtros
        from collections import defaultdict

        # 1. Cria summaries de TODAS as senhas (para _client_summaries e _client_summaries_by_id)
        all_grouped: dict[str, list[PasswordRow]] = defaultdict(list)
        for pwd in self._all_passwords:
            client_id = pwd.get("client_id", "")
            if client_id:
                all_grouped[client_id].append(pwd)

        all_summaries: list[ClientPasswordsSummary] = []
        for client_id, passwords in all_grouped.items():
            first = passwords[0]

            # FIX-SENHAS-006: Extrai todos os campos necessários
            razao_social = first.get("razao_social", first.get("client_name", ""))
            cnpj = first.get("cnpj", "")
            contato_nome = first.get("nome", "")
            whatsapp = first.get("whatsapp", first.get("numero", ""))

            try:
                client_external_id = int(first.get("client_external_id", client_id))
            except (ValueError, TypeError):
                try:
                    client_external_id = int(client_id)
                except (ValueError, TypeError):
                    client_external_id = 0

            services = sorted(set(p.get("service", "") for p in passwords if p.get("service")))

            all_summaries.append(
                ClientPasswordsSummary(
                    client_id=client_id,
                    client_external_id=client_external_id,
                    razao_social=razao_social,
                    cnpj=cnpj,
                    contato_nome=contato_nome,
                    whatsapp=whatsapp,
                    passwords_count=len(passwords),
                    services=services,
                )
            )

        # Ordena por nome
        all_summaries.sort(key=lambda s: s.razao_social.lower())
        self._client_summaries = all_summaries

        # FIX-SENHAS-004: Popula dict para busca rápida por client_id
        # FIX-SENHAS-005: Chaves em string porque Treeview.selection() retorna strings
        self._client_summaries_by_id = {str(s.client_id): s for s in all_summaries}

        # 2. Aplica filtros para a EXIBIÇÃO na árvore
        raw_search = self.search_var.get().strip()
        search_text = raw_search if raw_search else None
        service_filter = self.service_filter_var.get()

        # Filtra senhas
        filtered_passwords = self.controller.filter_passwords(search_text, service_filter)

        # Agrupa senhas filtradas (para exibir na árvore)
        filtered_grouped: dict[str, list[PasswordRow]] = defaultdict(list)
        for pwd in filtered_passwords:
            client_id = pwd.get("client_id", "")
            if client_id:
                filtered_grouped[client_id].append(pwd)

        display_summaries: list[ClientPasswordsSummary] = []
        for client_id, passwords in filtered_grouped.items():
            first = passwords[0]

            # FIX-SENHAS-006: Extrai todos os campos necessários
            razao_social = first.get("razao_social", first.get("client_name", ""))
            cnpj = first.get("cnpj", "")
            contato_nome = first.get("nome", "")
            whatsapp = first.get("whatsapp", first.get("numero", ""))

            try:
                client_external_id = int(first.get("client_external_id", client_id))
            except (ValueError, TypeError):
                try:
                    client_external_id = int(client_id)
                except (ValueError, TypeError):
                    client_external_id = 0

            services = sorted(set(p.get("service", "") for p in passwords if p.get("service")))

            display_summaries.append(
                ClientPasswordsSummary(
                    client_id=client_id,
                    client_external_id=client_external_id,
                    razao_social=razao_social,
                    cnpj=cnpj,
                    contato_nome=contato_nome,
                    whatsapp=whatsapp,
                    passwords_count=len(passwords),
                    services=services,
                )
            )

        # Ordena por nome
        display_summaries.sort(key=lambda s: s.razao_social.lower())

        # Atualiza UI (exibe apenas summaries filtrados)
        previous_selection = self._selected_client_id
        self._populate_clients_tree(display_summaries)

        # Tenta manter a seleção anterior
        if previous_selection and self.tree_clients.exists(previous_selection):
            self.tree_clients.selection_set(previous_selection)
            self.tree_clients.see(previous_selection)
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

        from src.modules.main_window.controller import navigate_to

        navigate_to(app, "clients_picker", on_pick=self._handle_client_picked_for_new_password)

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
            count = self.controller.delete_all_passwords_for_client(
                org_id=self.org_id,
                client_id=summary.client_id,
            )

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

        from src.modules.main_window.controller import navigate_to

        navigate_to(app, "clients_picker", on_pick=self._handle_client_picked)

    def _handle_client_picked(self, client_data: dict[str, Any]) -> None:
        """Callback vindo do pick mode de Clientes."""
        self._last_selected_client_data = client_data

        # Garante que existe um dialog (se usuário fechou, recria)
        if self._password_dialog is None or not self._password_dialog.is_visible():
            self._open_new_password_dialog(client_data=client_data)
        else:
            self._password_dialog.set_client_from_data(client_data)

    def _on_clients_tree_heading_click(self, event: tk.Event) -> str | None:
        """Impede redimensionar e clicar no cabeçalho da lista de clientes.

        - separator: bloqueia resize de coluna
        - heading: bloqueia qualquer ação (sort, pulo de scroll) - FIX-SENHAS-014
        """
        region = self.tree_clients.identify_region(event.x, event.y)
        if region in {"separator", "heading"}:
            return "break"
        return None

    def _on_clients_tree_configure(self, event: tk.Event) -> None:
        """Redistribui a largura extra da tree entre Razão Social, Nome e Serviços.

        Evita que apenas a coluna 'servicos' fique gigante em telas mais largas.
        """
        try:
            total_width = int(event.width)

            # Larguras base, devem bater com as usadas em self.tree_clients.column(...)
            base_widths: dict[str, int] = {
                "id": 60,
                "razao_social": 230,
                "cnpj": 150,
                "nome": 200,
                "whatsapp": 170,
                "qtd_senhas": 90,
                "servicos": 200,
            }

            base_total = sum(base_widths.values())

            # Pequena folga para bordas/scrollbar
            extra = total_width - base_total - 4
            if extra < 0:
                extra = 0

            # Distribui o extra entre Razão Social, Nome e Serviços
            share_cols = ("razao_social", "nome", "servicos")
            share_count = len(share_cols)

            per_col = extra // share_count if share_count else 0
            remainder = extra - per_col * share_count

            widths: dict[str, int] = {}
            for col, base in base_widths.items():
                width = base
                if col in share_cols:
                    width += per_col
                    # joga o resto na última coluna de share (servicos)
                    if col == "servicos":
                        width += remainder
                widths[col] = max(width, 60)  # largura mínima por segurança

            # Aplica as larguras calculadas
            for col, width in widths.items():
                self.tree_clients.column(col, width=width)

        except Exception:
            # Não queremos quebrar a tela por causa de erro de layout
            return

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
            # Obter org_id e user_id
            from infra.supabase_client import supabase

            user = supabase.auth.get_user()
            if user and hasattr(user, "user") and user.user:
                self.user_id = user.user.id

                app = self.winfo_toplevel()
                if hasattr(app, "_get_org_id_cached"):
                    self.org_id = app._get_org_id_cached(self.user_id)

            if not self.org_id:
                messagebox.showerror("Erro", "Organização não identificada.")
                return

            # Carregar clientes
            self.clients = self.controller.list_clients(self.org_id)

            # Carregar senhas e popular a lista de clientes
            self._load_all_passwords()
            self._refresh_clients_list()
        except Exception as e:
            log.exception("Erro ao inicializar tela de senhas")
            messagebox.showerror("Erro", f"Falha ao inicializar: {e}")
