"""Tela principal do módulo ANVISA.

Tela com layout dividido: tabela de demandas (esquerda) e conteúdo (direita).
"""

from __future__ import annotations

import logging
import tkinter as tk
from datetime import date, datetime
from tkinter import messagebox
from typing import Any, Callable, Optional

import customtkinter as ctk
from src.ui.ctk_config import *
from src.ui.widgets import CTkDatePicker, CTkTableView

from ._anvisa_requests_mixin import AnvisaRequestsMixin
from ._anvisa_history_popup_mixin import AnvisaHistoryPopupMixin
from ._anvisa_handlers_mixin import AnvisaHandlersMixin
from ..controllers.anvisa_controller import AnvisaController
from ..services.anvisa_service import AnvisaService
from src.infra.repositories.anvisa_requests_repository import AnvisaRequestsRepositoryAdapter
from src.utils.auth_utils import current_user_id
from src.ui.window_utils import (
    apply_window_icon,
    prepare_hidden_window,
    show_centered_no_flash,
)

log = logging.getLogger(__name__)


class AnvisaScreen(AnvisaRequestsMixin, AnvisaHistoryPopupMixin, AnvisaHandlersMixin, ctk.CTkFrame):
    """Tela ANVISA - Layout dividido com ações e conteúdo.

    Layout em duas colunas usando Panedwindow:
    - Esquerda: ações (botão selecionar cliente + info do cliente)
    - Direita: conteúdo atual (Em desenvolvimento + testes + feedback)

    Args:
        master: Widget pai (geralmente o root Tk)
        main_window: Referência à janela principal (para navegação)
        on_back: Callback opcional chamado quando "Voltar" é clicado em home
        on_test_1: Callback opcional para botão Teste 1
        on_test_2: Callback opcional para botão Teste 2
        on_test_3: Callback opcional para botão Teste 3
        **kwargs: Argumentos adicionais para ctk.CTkFrame
    """

    def __init__(
        self,
        master: Any,
        main_window: Optional[Any] = None,
        on_back: Optional[Callable[[], None]] = None,
        on_test_1: Optional[Callable[[], None]] = None,
        on_test_2: Optional[Callable[[], None]] = None,
        on_test_3: Optional[Callable[[], None]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, **kwargs)

        # Callbacks opcionais
        self.main_window = main_window
        self._on_back = on_back
        self._on_test_1 = on_test_1
        self._on_test_2 = on_test_2
        self._on_test_3 = on_test_3

        # Estado da navegação interna
        self.current_page = tk.StringVar(value="home")

        # StringVar para feedback de última ação
        self.last_action = tk.StringVar(value="Nenhuma ação ainda")

        # StringVar para cliente selecionado
        self.selected_client_var = tk.StringVar(value="Nenhum cliente selecionado")

        # Lista local de demandas ANVISA (cache em memória)
        self._requests: list[dict[str, Any]] = []

        # Cache de demandas por cliente (cliente_id -> list[dict])
        self._demandas_cache: dict[str, list[dict[str, Any]]] = {}

        # Índice de demandas por cliente (para handlers de exclusão)
        self._requests_by_client: dict[str, list[dict[str, Any]]] = {}

        # Janelas de browser abertas por cliente (para evitar duplicatas)
        self._anvisa_browser_windows: dict[str, tk.Toplevel] = {}

        # Popup de histórico (Toplevel)
        self._history_popup: Optional[tk.Toplevel] = None
        self._history_tree_popup: Optional[CTkTableView] = None
        self._history_iid_map: dict[str, str] = {}

        # Contexto para menu de botão direito
        self._ctx_client_id: Optional[str] = None
        self._ctx_razao: Optional[str] = None
        self._ctx_cnpj: Optional[str] = None
        self._ctx_request_id: Optional[str] = None
        self._ctx_request_type: Optional[str] = None

        # Flag para centralizar sash apenas uma vez
        self._sash_centered = False

        # Cliente pendente do modo seleção (processado após retornar à tela ANVISA)
        self._pending_client_data: Optional[dict[str, Any]] = None

        # Controller headless para operações de delete/finalizar
        # Tenta obter NotificationsService do main_window, se disponível
        notifications_service = None
        if main_window and hasattr(main_window, "notifications_service"):
            notifications_service = main_window.notifications_service

        self._controller = AnvisaController(
            repository=AnvisaRequestsRepositoryAdapter(),
            logger=log,
            notifications_service=notifications_service,
        )

        # Service headless para validação de duplicados e lógica de negócio
        self._service = AnvisaService(repository=AnvisaRequestsRepositoryAdapter())

        self._build_ui()
        self.show_home()

    @staticmethod
    def _lock_treeview_columns(tree) -> None:
        """Trava redimensionamento e arrasto de colunas da Treeview.

        Args:
            tree: Treeview para travar colunas
        """

        # Bloquear resize manual via separator
        def block_separator(event: Any) -> str:
            if tree.identify_region(event.x, event.y) == "separator":
                return "break"
            return ""

        # Bloquear cursor de resize
        def block_resize_cursor(event: Any) -> str:
            if tree.identify_region(event.x, event.y) == "separator":
                tree.config(cursor="arrow")
                return "break"
            tree.config(cursor="")
            return ""

        tree.bind("<Button-1>", block_separator)
        tree.bind("<B1-Motion>", block_separator)
        tree.bind("<Motion>", block_resize_cursor)

    def _build_ui(self) -> None:
        """Constrói a interface da tela ANVISA com layout dividido."""
        # Container principal com padding
        container = ctk.CTkFrame(self)
        container.pack(fill="both", expand=True, padx=20, pady=20)

        # Panedwindow para dividir a tela em duas colunas (50/50)
        self.paned = tk.PanedWindow(container, orient="horizontal", sashwidth=5, bg="#d9d9d9")
        self.paned.pack(fill="both", expand=True)

        # COLUNA ESQUERDA: Tabela de demandas + botão no rodapé
        left_frame = ctk.CTkFrame(self.paned)
        self.paned.add(left_frame, width=400)

        # Configurar grid do left_frame
        left_frame.rowconfigure(0, weight=1)  # Treeview principal (expande)
        left_frame.rowconfigure(1, weight=0)  # Botões no rodapé
        left_frame.columnconfigure(0, weight=1)

        # Row 0: Frame com Treeview (caixinha "Anvisa")
        list_group = ctk.CTkFrame(left_frame)
        list_group.grid(row=0, column=0, sticky="nsew", pady=(10, 10), padx=10)
        
        ctk.CTkLabel(list_group, text="Anvisa", font=("Arial", 12, "bold")).pack(pady=(5, 5))

        columns = ("client_id", "razao_social", "cnpj", "request_type", "updated_at")
        self.tree_requests = CTkTableView(
            list_group,
            columns=columns,
            show="headings",
            height=15,
            zebra=True,
        )  # TODO: selectmode="browse" -> handle in CTk way

        # Cabeçalhos e colunas centralizados
        self.tree_requests.heading("client_id", text="ID", anchor="center")
        self.tree_requests.heading("razao_social", text="Razão Social", anchor="center")
        self.tree_requests.heading("cnpj", text="CNPJ", anchor="center")
        self.tree_requests.heading("request_type", text="Demanda", anchor="center")
        self.tree_requests.heading("updated_at", text="Última Alteração", anchor="center")

        self.tree_requests.column("client_id", width=50, anchor="center", stretch=False)
        self.tree_requests.column("razao_social", width=200, anchor="center")
        self.tree_requests.column("cnpj", width=150, anchor="center", stretch=False)
        self.tree_requests.column("request_type", width=180, anchor="center")
        self.tree_requests.column("updated_at", width=140, anchor="center", stretch=False)

        self.tree_requests.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        # Bind de eventos na Treeview (garantir bind único)
        self.tree_requests.unbind("<Double-1>")
        self.tree_requests.bind("<Double-1>", self._on_tree_double_click)
        self.tree_requests.unbind("<<TreeviewSelect>>")
        self.tree_requests.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree_requests.unbind("<Button-3>")
        self.tree_requests.bind("<Button-3>", self._on_tree_right_click)

        # Bind Delete para excluir demanda (intercepta antes do bind global do root)
        def _handle_delete_key(event: Any) -> str:
            self._on_delete_request_clicked()
            return "break"

        self.tree_requests.unbind("<Delete>")
        self.tree_requests.bind("<Delete>", _handle_delete_key)

        # Travar redimensionamento de colunas
        self._lock_treeview_columns(self.tree_requests)

        # Menu de contexto
        self._main_ctx_menu = tk.Menu(self, tearoff=0)
        self._main_ctx_menu.add_command(label="Histórico de regularizações", command=self._ctx_open_history)
        self._main_ctx_menu.add_separator()
        self._main_ctx_menu.add_command(label="Excluir", command=self._ctx_delete_request)

        # Row 1: Botões Nova e Excluir no rodapé (ações principais)
        actions_bottom = ctk.CTkFrame(left_frame)
        actions_bottom.grid(row=1, column=0, sticky="w", pady=(10, 10), padx=10)

        self._btn_nova = ctk.CTkButton(
            actions_bottom,
            text="Nova",
            fg_color=("#2E7D32", "#1B5E20"),
            hover_color=("#1B5E20", "#0D4A11"),
            command=self._on_new_anvisa_clicked,
            width=100,
        )
        self._btn_nova.pack(side="left", padx=(0, 6))

        self._btn_excluir = ctk.CTkButton(
            actions_bottom,
            text="Excluir",
            fg_color=("#D32F2F", "#B71C1C"),
            hover_color=("#B71C1C", "#8B0000"),
            command=self._on_delete_request_clicked,
            width=100,
            state="disabled",
        )
        self._btn_excluir.pack(side="left")

        # COLUNA DIREITA: Conteúdo (será substituído conforme navegação)
        self.content_frame = ctk.CTkFrame(self.paned)
        self.paned.add(self.content_frame, width=400)

        # Agendar centralização do sash após renderização
        self.after(100, self._center_paned_sash)

    def _clear_content(self) -> None:
        """Limpa o content_frame destruindo todos os widgets filhos."""
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def show_home(self) -> None:
        """Exibe a página inicial - apenas texto 'Em desenvolvimento.' no painel direito."""
        self.current_page.set("home")
        self._clear_content()

        # Carregar demandas do Supabase ao exibir a tela
        self._load_requests_from_cloud()

        # Texto informativo centralizado
        placeholder = ctk.CTkLabel(
            self.content_frame,
            text="Em desenvolvimento.",
            font=("Segoe UI", 11),
            text_color=("#757575", "#BDBDBD"),
        )
        placeholder.place(relx=0.5, rely=0.2, anchor="center")

    def open_history_for_client(self, client_id: str) -> None:
        """Abre popup de histórico de regularizações para um cliente específico.

        Método público chamado por HubScreen.open_anvisa_history().

        Args:
            client_id: ID do cliente para abrir histórico.
        """
        try:
            # Garantir que tree está populada
            if not self.tree_requests.get_children():
                self._load_requests_from_cloud()

            # Buscar cliente na tree
            client_iid = str(client_id)
            if client_iid not in self.tree_requests.get_children():
                # Tentar recarregar e buscar novamente
                self._load_requests_from_cloud()
                if client_iid not in self.tree_requests.get_children():
                    messagebox.showwarning("Histórico", "Cliente não encontrado na lista da ANVISA.")
                    return

            # Obter dados do cliente da tree
            item = self.tree_requests.item(client_iid)
            values = item["values"]
            if len(values) >= 3:
                razao = str(values[1])
                cnpj = str(values[2])

                # Abrir popup de histórico
                self._open_history_popup(client_id, razao, cnpj, center=True)
            else:
                messagebox.showwarning("Histórico", "Dados do cliente incompletos.")
        except Exception as e:
            log.exception(f"Erro ao abrir histórico para cliente {client_id}")
            messagebox.showerror("Erro", f"Não foi possível abrir o histórico: {e}")

    def _show_subpage(self, page_name: str, title: str) -> None:
        """Exibe uma subpágina genérica."""
        self.current_page.set(page_name)
        self._clear_content()

        # Título da subpágina
        page_title = ctk.CTkLabel(
            self.content_frame,
            text=title,
            font=("Segoe UI", 16, "bold"),  # type: ignore[arg-type]
            bootstyle="info",
        )
        page_title.pack(pady=(20, 10))

        # Texto informativo
        info_text = ctk.CTkLabel(
            self.content_frame,
            text="Em desenvolvimento.",
            font=("Segoe UI", 11),
            bootstyle="secondary",
        )
        info_text.pack(pady=10)

    def _handle_back(self) -> None:
        """Handler do botão Voltar."""
        current = self.current_page.get()

        if current == "home":
            # Em home: chamar callback on_back se fornecido
            if self._on_back:
                self._on_back()
        else:
            # Em subpágina: voltar para home
            self.show_home()

    def _handle_test_1(self) -> None:
        """Handler do botão Teste 1."""
        self.last_action.set("Teste 1 clicado")
        if self._on_test_1:
            self._on_test_1()
        self._show_subpage("teste1", "Teste 1")

    def _handle_test_2(self) -> None:
        """Handler do botão Teste 2."""
        self.last_action.set("Teste 2 clicado")
        if self._on_test_2:
            self._on_test_2()
        self._show_subpage("teste2", "Teste 2")

    def _handle_test_3(self) -> None:
        """Handler do botão Teste 3."""
        self.last_action.set("Teste 3 clicado")
        if self._on_test_3:
            self._on_test_3()
        self._show_subpage("teste3", "Teste 3")

    def _on_new_anvisa_clicked(self) -> None:
        """Handler do botão Nova ANVISA - inicia modo seleção de cliente."""
        app = self._get_main_app()
        if not app:
            log.warning("Não foi possível acessar a aplicação principal")
            return

        try:
            from src.modules.main_window.controller import start_client_pick_mode, navigate_to

            # Callback: apenas salva dados pendentes (não abre modal ainda)
            def _on_picked(client_data: dict[str, Any]) -> None:
                self._pending_client_data = client_data

            # Return: volta para ANVISA e agenda processamento do pending
            def _return_to_anvisa() -> None:
                navigate_to(app, "anvisa")

                # Garantir layout pronto antes de abrir modal (evita "sumir/descer")
                def _deferred():
                    try:
                        app.update_idletasks()
                    except Exception as e:
                        log.warning(f"Erro ao atualizar idletasks: {e}")
                    self._consume_pending_pick()

                # after_idle garante que Tk finalize layout/geometry primeiro
                # 150ms é conservador e evita parent com width/height == 1
                app.after_idle(lambda: app.after(150, _deferred))

            start_client_pick_mode(
                app,
                on_client_picked=_on_picked,
                banner_text="🔍 Modo seleção: escolha um cliente para criar nova ANVISA",
                return_to=_return_to_anvisa,
            )
        except Exception as e:
            log.exception("Erro ao iniciar modo seleção de cliente")
            self.last_action.set(f"Erro: {e}")

    def _consume_pending_pick(self) -> None:
        """Processa cliente pendente do modo seleção (após retornar à tela ANVISA)."""
        if self._pending_client_data is None:
            # Usuário cancelou ou não havia pending
            return

        # Consumir dados pendentes
        client_data = self._pending_client_data
        self._pending_client_data = None

        # Processar seleção normalmente
        self._handle_client_picked_for_anvisa(client_data)

    def _handle_client_picked_for_anvisa(self, client_data: dict[str, Any]) -> None:
        """Callback chamado quando um cliente é selecionado no modo pick.

        Abre janela modal para escolher tipo de demanda e cria registro na Treeview.

        Args:
            client_data: Dict com dados do cliente (id, razao_social, cnpj, etc)
        """
        try:
            client_id = str(client_data.get("id", ""))
            razao = client_data.get("razao_social", "")
            cnpj = client_data.get("cnpj", "")

            # Abrir dialog para escolher tipo de demanda
            dlg_result = self._open_new_anvisa_request_dialog(client_data)
            if not dlg_result:
                # Usuário cancelou
                self.last_action.set("Seleção cancelada")
                return

            request_type = str(dlg_result.get("request_type") or "")
            payload = dlg_result.get("payload") or {}

            # VALIDAÇÃO: usar Service para validar (tipo + duplicado)
            demandas_cliente = self._requests_by_client.get(str(client_id), [])
            ok, duplicado, msg = self._service.validate_new_request_in_memory(demandas_cliente, request_type)

            if not ok:
                # Validação falhou: mostrar mensagem
                messagebox.showwarning("Validação de Demanda", msg)

                # Se existe duplicado, focar no histórico
                if duplicado:
                    dup_id = str(duplicado.get("id", ""))
                    self._focus_history_item(dup_id)
                    self.last_action.set(f"Bloqueado: demanda {request_type} já existe (aberta)")

                return

            # Validação passou: criar via Controller
            org_id = self._resolve_org_id()
            if not org_id:
                messagebox.showerror("Erro", "Não foi possível identificar a organização.")
                return

            # Normalizar tipo (Service já validou, mas é bom garantir formato oficial)
            tipo_normalizado = self._service.normalize_request_type(request_type)

            # Obter user_id se disponível (para auditoria)
            user_id = current_user_id()

            # Criar demanda via Controller
            request_id = self._controller.create_request(
                org_id=org_id,
                client_id=str(client_id),
                request_type=tipo_normalizado,
                created_by=user_id,  # Preenche com user_id quando disponível
                payload=payload,
            )

            if request_id:
                # Sucesso: invalidar caches e recarregar
                self._demandas_cache.pop(client_id, None)
                self._requests_by_client.pop(client_id, None)

                # Recarregar lista completa da cloud
                self._load_requests_from_cloud()

                # Selecionar cliente na tree principal (sem abrir histórico)
                iid = str(client_id)
                if iid in self.tree_requests.get_children(""):
                    self.tree_requests.selection_set(iid)
                    self.tree_requests.focus(iid)
                    self.tree_requests.see(iid)

                # Se popup histórico já está aberto para este cliente, atualizar
                if self._history_popup and self._history_popup.winfo_exists():
                    # Verificar se é do mesmo cliente (via dados no popup)
                    self._update_history_popup(client_id, razao, cnpj)

                # Refresh Hub dashboard para atualizar Pendências/Radar
                self._refresh_hub_dashboard_if_present()

                self.last_action.set(f"Demanda ANVISA criada: {tipo_normalizado}")
                log.info(f"[ANVISA] Demanda criada para cliente {client_id}: {tipo_normalizado}")
            else:
                # Falha: mostrar erro
                messagebox.showerror(
                    "Erro ao Criar Demanda",
                    "Não foi possível criar a demanda.\n\nVerifique os logs para mais detalhes.",
                )
                self.last_action.set("Erro ao salvar demanda")

        except Exception as e:
            log.exception("Erro ao processar cliente selecionado")
            self.last_action.set(f"Erro ao processar cliente: {e}")

            # Verificar se é erro de constraint de tipo de demanda
            err_str = str(e)
            if "23514" in err_str or "request_type_chk" in err_str:
                messagebox.showerror(
                    "Tipo de Demanda Não Permitido",
                    "Seu banco ainda não permite esse tipo de demanda.\n\n"
                    "Atualize a constraint no Supabase executando a migration:\n"
                    "migrations/2025-12-27_anvisa_request_type_chk.sql",
                )

    def _open_new_anvisa_request_dialog(self, client_data: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Abre janela modal para escolher tipo de regularização ANVISA.

        Args:
            client_data: Dict com dados do cliente

        Returns:
            Dict com {"request_type": str, "payload": dict} ou None se cancelou
        """
        # Criar janela modal fixa
        dlg = tk.Toplevel(self)

        # IMEDIATAMENTE preparar como hidden/offscreen para evitar flash
        prepare_hidden_window(dlg)

        dlg.title("Regularização ANVISA")
        dlg.resizable(False, False)
        dlg.transient(self.winfo_toplevel())
        dlg.grab_set()

        # Aplicar ícone do app
        apply_window_icon(dlg)

        # Container principal (padding via pack ao invés de kwargs)
        main_frame = ctk.CTkFrame(dlg)
        main_frame.pack(fill=BOTH, expand=True, padx=16, pady=(8, 16))

        # A) Título (menos espaço embaixo)
        ctk.CTkLabel(
            main_frame,
            text="Regularização ANVISA",
            font=("Segoe UI", 16, "bold"),  # type: ignore[arg-type]
            bootstyle="primary",
        ).pack(pady=(0, 12))

        # B) Caixinha "Cliente" com 3 campos readonly  
        from src.ui.widgets.ctk_section import CTkSection
        lf_client = CTkSection(main_frame, title="Cliente")
        lf_client.pack(fill="x", pady=(0, 10))
        lf_client.content_frame.columnconfigure(1, weight=0)
        lf_client.content_frame.columnconfigure(3, weight=0)
        lf_client.content_frame.columnconfigure(5, weight=1)

        # Linha 0: ID e CNPJ lado a lado
        client_id = str(client_data.get("id", ""))
        cnpj = client_data.get("cnpj", "")

        ctk.CTkLabel(lf_client.content_frame, text="ID:").grid(row=0, column=0, sticky="w", pady=(0, 8))
        id_var = tk.StringVar(value=client_id)
        e_id = ctk.CTkEntry(lf_client.content_frame, textvariable=id_var, state="readonly", width=10, justify="left")
        e_id.grid(row=0, column=1, sticky="w", padx=(8, 20), pady=(0, 8))

        ctk.CTkLabel(lf_client.content_frame, text="CNPJ:").grid(row=0, column=2, sticky="w", pady=(0, 8))
        cnpj_var = tk.StringVar(value=cnpj)
        e_cnpj = ctk.CTkEntry(lf_client.content_frame, textvariable=cnpj_var, state="readonly", width=20, justify="left")
        e_cnpj.grid(row=0, column=3, sticky="w", padx=(8, 0), pady=(0, 8))

        # Linha 1: Razão Social (ocupa toda largura)
        ctk.CTkLabel(lf_client.content_frame, text="Razão Social:").grid(row=1, column=0, sticky="w")
        razao = client_data.get("razao_social", "")
        razao_var = tk.StringVar(value=razao)
        e_razao = ctk.CTkEntry(lf_client.content_frame, textvariable=razao_var, state="readonly")
        e_razao.grid(row=1, column=1, columnspan=5, sticky="ew", padx=(8, 0))

        # C) Separator
        ctk.CTkFrame(main_frame, height=2)  # Separador horizontal.pack(fill="x", pady=(0, 10))

        # D) Caixinha "Tipo de Regularização"
        lf_tipo = CTkSection(main_frame, title="Tipo de Regularização")
        lf_tipo.pack(fill="x", expand=False, pady=(0, 10))

        from ..constants import REQUEST_TYPES

        selected_type = tk.StringVar(value=REQUEST_TYPES[0])

        # Configurar estilo para radiobutton em negrito (tipo especial)
        special_type = "Concessão de AE Manipulação"
        from tkinter import font as tkfont

        base_font = tkfont.nametofont("TkDefaultFont")
        bold_font = base_font.copy()
        bold_font.configure(weight="bold")

        # Manter referência viva (evita GC)
        dlg._anvisa_bold_font = bold_font  # type: ignore[attr-defined]

        # Layout em 2 colunas para reduzir altura
        types_frame = ctk.CTkFrame(lf_tipo.content_frame)
        types_frame.pack(fill="x")
        types_frame.columnconfigure(0, weight=1)
        types_frame.columnconfigure(1, weight=1)

        for i, req_type in enumerate(REQUEST_TYPES):
            r = i // 2
            c = i % 2
            # CTkRadioButton não suporta style= custom, usar font padrão
            ctk.CTkRadioButton(
                types_frame,
                text=req_type,
                variable=selected_type,
                value=req_type,
            ).grid(row=r, column=c, sticky="w", padx=(0, 18), pady=3)

        # E) Caixinha "Detalhes" (prazo OBRIGATÓRIO)
        lf_details = CTkSection(main_frame, title="Detalhes")
        lf_details.pack(fill="x", pady=(0, 10))

        # Prazo obrigatório com CTkDatePicker (calendário)
        ctk.CTkLabel(lf_details.content_frame, text="Prazo *:").grid(row=0, column=0, sticky="w", pady=(0, 6))

        # Calcular data default baseado no tipo selecionado
        today = date.today()
        default_iso = self._service.default_due_date_iso_for_type(selected_type.get(), today)
        default_date = datetime.strptime(default_iso, "%Y-%m-%d").date()

        due_entry = CTkDatePicker(lf_details.content_frame, date_format="%d/%m/%Y")
        due_entry.set(default_date.strftime("%d/%m/%Y"))
        due_entry.grid(row=0, column=1, sticky="w", padx=(8, 0), pady=(0, 6))

        # Flag para detectar se usuário já editou manualmente o prazo
        user_edited_date = {"value": False}

        def on_date_selected(event=None):
            user_edited_date["value"] = True

        due_entry.bind("<Return>", on_date_selected)
        due_entry.bind("<FocusOut>", on_date_selected)

        # Atualizar default ao mudar tipo (se usuário não editou manualmente)
        def on_type_changed(*args):
            if not user_edited_date["value"]:
                new_default_iso = self._service.default_due_date_iso_for_type(selected_type.get(), today)
                new_default_date = datetime.strptime(new_default_iso, "%Y-%m-%d").date()
                due_entry.set(new_default_date.strftime("%d/%m/%Y"))

        selected_type.trace_add("write", on_type_changed)

        # Observações (multi-linha, opcional)
        ctk.CTkLabel(lf_details.content_frame, text="Observações:").grid(row=1, column=0, sticky="nw", pady=(6, 0))
        notes_text = tk.Text(lf_details.content_frame, height=3, width=46, wrap="word")
        notes_text.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(6, 0))

        # F) Botões (mesmo padrão Nova/Excluir: width=10)
        btn_frame = ctk.CTkFrame(main_frame)
        btn_frame.pack(fill="x", pady=(10, 0))

        result: dict[str, Any] = {"value": None}

        def on_create():
            # Desabilitar botão para evitar double-submit
            btn_create.configure(state="disabled")
            btn_cancel.configure(state="disabled")

            tipo = selected_type.get()
            notes = notes_text.get("1.0", "end").strip()

            # Obter prazo do CTkDatePicker (obrigatório)
            try:
                dt = due_entry.get_date()
                due_iso = dt.isoformat()
            except Exception as e:
                log.warning(f"Erro ao obter prazo: {e}")
                messagebox.showwarning(
                    "Prazo obrigatório",
                    "Por favor, informe o prazo utilizando o calendário.",
                    parent=dlg,
                )
                # Re-habilitar botões
                btn_create.configure(state="normal")
                btn_cancel.configure(state="normal")
                return

            payload = self._service.build_payload_for_new_request(
                request_type=tipo,
                due_date_iso=due_iso,
                notes=notes,
            )

            result["value"] = {"request_type": tipo, "payload": payload}
            dlg.destroy()

        def on_cancel():
            result["value"] = None
            dlg.destroy()

        btn_create = ctk.CTkButton(
            btn_frame,
            text="Criar",
            width=12,
            command=on_create,
        )
        btn_create.pack(side="left", padx=(10, 6), pady=6)

        btn_cancel = ctk.CTkButton(
            btn_frame,
            text="Cancelar",
            width=12,
            command=on_cancel,
        )
        btn_cancel.pack(side="left", padx=(6, 10), pady=6)

        # Centralizar janela SEM FLASH (altura calculada automaticamente)
        show_centered_no_flash(dlg, self.winfo_toplevel(), width=740, height=None)

        # Aguardar fechamento da janela (modal)
        self.wait_window(dlg)

        return result["value"]

    def _center_paned_sash(self) -> None:
        """Centraliza o divisor do Panedwindow (50/50)."""
        if self._sash_centered:
            return

        try:
            # Forçar atualização do layout
            self.paned.update_idletasks()

            # Obter largura total do Panedwindow
            width = self.paned.winfo_width()

            if width > 1:
                # Verificar se é ttk.PanedWindow (tem sashpos) ou tk.PanedWindow (tem sash_place)
                if hasattr(self.paned, 'sashpos'):
                    # TTK PanedWindow
                    self.paned.sashpos(0, width // 2)
                elif hasattr(self.paned, 'sash_place'):
                    # TK PanedWindow
                    try:
                        pos = self.paned.sash_coord(0)  # (x, y)
                        novo_x = width // 2
                        self.paned.sash_place(0, novo_x, pos[1])
                    except Exception:
                        # Se sash_coord falhar, tentar posição padrão
                        self.paned.sash_place(0, width // 2, 0)
                
                self._sash_centered = True
                log.debug(f"Sash centralizado em {width // 2}px")
        except Exception as e:
            log.debug(f"Erro ao centralizar sash: {e}")  # debug em vez de warning

    def _get_main_app(self) -> Optional[Any]:
        """Retorna referência à aplicação principal."""
        return self.main_window

    def _refresh_hub_dashboard_if_present(self) -> None:
        """Força refresh do Hub dashboard após mudanças em demandas ANVISA.

        Tenta acessar a instância do Hub via múltiplos caminhos (legado + router cache)
        e chama reload_dashboard() se disponível.
        """
        app = self._get_main_app()
        if not app:
            return

        # Caso legado (MainWindow/controller.py usa _hub_screen_instance)
        hub = getattr(app, "_hub_screen_instance", None)
        if hub and hasattr(hub, "reload_dashboard"):
            try:
                hub.reload_dashboard()
                log.debug("[ANVISA] Hub dashboard refreshed (via _hub_screen_instance)")
                return
            except Exception as e:
                log.warning(f"[ANVISA] Erro ao refresh hub via _hub_screen_instance: {e}")

        # Fallback: se existir router/cache no app
        router = getattr(app, "_router", None)
        cache = getattr(router, "_cache", None) if router else None
        if isinstance(cache, dict):
            hub2 = cache.get("hub")
            if hub2 and hasattr(hub2, "reload_dashboard"):
                try:
                    hub2.reload_dashboard()
                    log.debug("[ANVISA] Hub dashboard refreshed (via router cache)")
                except Exception as e:
                    log.warning(f"[ANVISA] Erro ao refresh hub via router cache: {e}")
