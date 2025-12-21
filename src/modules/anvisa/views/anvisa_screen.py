"""Tela principal do módulo ANVISA.

Tela com layout dividido: tabela de demandas (esquerda) e conteúdo (direita).
"""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import messagebox
from typing import Any, Callable, Optional

import ttkbootstrap as ttk
from ttkbootstrap.constants import BOTH, LEFT, YES, HORIZONTAL, NSEW

from ._anvisa_requests_mixin import AnvisaRequestsMixin
from ._anvisa_history_popup_mixin import AnvisaHistoryPopupMixin
from ._anvisa_handlers_mixin import AnvisaHandlersMixin
from ..controllers.anvisa_controller import AnvisaController
from ..services.anvisa_service import AnvisaService
from infra.repositories.anvisa_requests_repository import AnvisaRequestsRepositoryAdapter
from src.ui.window_utils import (
    apply_window_icon,
    prepare_hidden_window,
    show_centered_no_flash,
)

log = logging.getLogger(__name__)


class AnvisaScreen(AnvisaRequestsMixin, AnvisaHistoryPopupMixin, AnvisaHandlersMixin, ttk.Frame):
    """Tela ANVISA - Layout dividido com ações e conteúdo.

    Layout em duas colunas usando PanedWindow:
    - Esquerda: ações (botão selecionar cliente + info do cliente)
    - Direita: conteúdo atual (Em desenvolvimento + testes + feedback)

    Args:
        master: Widget pai (geralmente o root Tk)
        main_window: Referência à janela principal (para navegação)
        on_back: Callback opcional chamado quando "Voltar" é clicado em home
        on_test_1: Callback opcional para botão Teste 1
        on_test_2: Callback opcional para botão Teste 2
        on_test_3: Callback opcional para botão Teste 3
        **kwargs: Argumentos adicionais para ttk.Frame
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
        self.current_page = ttk.StringVar(value="home")

        # StringVar para feedback de última ação
        self.last_action = ttk.StringVar(value="Nenhuma ação ainda")

        # StringVar para cliente selecionado
        self.selected_client_var = ttk.StringVar(value="Nenhum cliente selecionado")

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
        self._history_tree_popup: Optional[tk.ttk.Treeview] = None
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
    def _lock_treeview_columns(tree: ttk.Treeview) -> None:
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
        container = ttk.Frame(self, padding=20)
        container.pack(fill=BOTH, expand=YES)

        # PanedWindow para dividir a tela em duas colunas (50/50)
        self.paned = ttk.PanedWindow(container, orient=HORIZONTAL)
        self.paned.pack(fill=BOTH, expand=YES)

        # COLUNA ESQUERDA: Tabela de demandas + botão no rodapé
        left_frame = ttk.Frame(self.paned, padding=10)
        self.paned.add(left_frame, weight=1)

        # Configurar grid do left_frame
        left_frame.rowconfigure(0, weight=1)  # Treeview principal (expande)
        left_frame.rowconfigure(1, weight=0)  # Botões no rodapé
        left_frame.columnconfigure(0, weight=1)

        # Row 0: Labelframe com Treeview (caixinha "Anvisa")
        list_group = ttk.Labelframe(left_frame, text="Anvisa", padding=(8, 6))
        list_group.grid(row=0, column=0, sticky=NSEW, pady=(0, 10))

        columns = ("client_id", "razao_social", "cnpj", "request_type", "updated_at")
        self.tree_requests = tk.ttk.Treeview(
            list_group,
            columns=columns,
            show="headings",
            selectmode="browse",
            height=15,
        )

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

        scrollbar = tk.ttk.Scrollbar(list_group, orient="vertical", command=self.tree_requests.yview)
        self.tree_requests.configure(yscrollcommand=scrollbar.set)

        self.tree_requests.pack(side="left", fill=BOTH, expand=True)
        scrollbar.pack(side="right", fill="y")

        # Bind de eventos na Treeview (garantir bind único)
        self.tree_requests.unbind("<Double-1>")
        self.tree_requests.bind("<Double-1>", self._on_tree_double_click)
        self.tree_requests.unbind("<<TreeviewSelect>>")
        self.tree_requests.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree_requests.unbind("<Button-3>")
        self.tree_requests.bind("<Button-3>", self._on_tree_right_click)

        # Travar redimensionamento de colunas
        self._lock_treeview_columns(self.tree_requests)

        # Menu de contexto
        self._main_ctx_menu = tk.Menu(self, tearoff=0)
        self._main_ctx_menu.add_command(label="Histórico de demandas", command=self._ctx_open_history)
        self._main_ctx_menu.add_separator()
        self._main_ctx_menu.add_command(label="Excluir", command=self._ctx_delete_request)

        # Row 1: Botões Nova e Excluir no rodapé (ações principais)
        actions_bottom = ttk.Frame(left_frame)
        actions_bottom.grid(row=1, column=0, sticky="w", pady=(10, 0))

        self._btn_nova = ttk.Button(
            actions_bottom,
            text="Nova",
            bootstyle="success",
            command=self._on_new_anvisa_clicked,
            width=10,
        )
        self._btn_nova.pack(side=LEFT, padx=(0, 6))

        self._btn_excluir = ttk.Button(
            actions_bottom,
            text="Excluir",
            bootstyle="danger",
            command=self._on_delete_request_clicked,
            width=10,
            state="disabled",
        )
        self._btn_excluir.pack(side=LEFT)

        # COLUNA DIREITA: Conteúdo (será substituído conforme navegação)
        self.content_frame = ttk.Frame(self.paned, padding=10)
        self.paned.add(self.content_frame, weight=1)

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
        placeholder = ttk.Label(
            self.content_frame,
            text="Em desenvolvimento.",
            font=("Segoe UI", 11),
            bootstyle="secondary",
        )
        placeholder.place(relx=0.5, rely=0.2, anchor="center")

    def _show_subpage(self, page_name: str, title: str) -> None:
        """Exibe uma subpágina genérica."""
        self.current_page.set(page_name)
        self._clear_content()

        # Título da subpágina
        page_title = ttk.Label(
            self.content_frame,
            text=title,
            font=("Segoe UI", 16, "bold"),  # type: ignore[arg-type]
            bootstyle="info",
        )
        page_title.pack(pady=(20, 10))

        # Texto informativo
        info_text = ttk.Label(
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
                # Aguardar 50ms para garantir que a tela trocou antes de abrir modal
                app.after(50, self._consume_pending_pick)

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
            request_type = self._open_new_anvisa_request_dialog(client_data)
            if not request_type:
                # Usuário cancelou
                self.last_action.set("Seleção cancelada")
                return

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

            # Criar demanda via Controller
            request_id = self._controller.create_request(
                org_id=org_id,
                client_id=str(client_id),
                request_type=tipo_normalizado,
                created_by=None,  # TODO: passar user_id se disponível
                payload={},
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

    def _open_new_anvisa_request_dialog(self, client_data: dict[str, Any]) -> Optional[str]:
        """Abre janela modal para escolher tipo de demanda ANVISA.

        Args:
            client_data: Dict com dados do cliente

        Returns:
            String com tipo de demanda escolhido, ou None se cancelou
        """
        # Criar janela modal fixa
        dlg = tk.Toplevel(self)

        # IMEDIATAMENTE preparar como hidden/offscreen para evitar flash
        prepare_hidden_window(dlg)

        dlg.title("Nova Demanda ANVISA")
        dlg.resizable(False, False)
        dlg.transient(self.winfo_toplevel())
        dlg.grab_set()

        # Aplicar ícone do app
        apply_window_icon(dlg)

        # Container principal (padding menor no topo para subir conteúdo)
        main_frame = ttk.Frame(dlg, padding=(16, 8, 16, 16))
        main_frame.pack(fill=BOTH, expand=True)

        # A) Título (menos espaço embaixo)
        ttk.Label(
            main_frame,
            text="Nova Demanda ANVISA",
            font=("Segoe UI", 16, "bold"),  # type: ignore[arg-type]
            bootstyle="primary",
        ).pack(pady=(0, 12))

        # B) Caixinha "Cliente" com 3 campos readonly
        lf_client = ttk.Labelframe(main_frame, text="Cliente", padding=(12, 10))
        lf_client.pack(fill="x", pady=(0, 10))
        lf_client.columnconfigure(1, weight=0)
        lf_client.columnconfigure(3, weight=0)
        lf_client.columnconfigure(5, weight=1)

        # Linha 0: ID e CNPJ lado a lado
        client_id = str(client_data.get("id", ""))
        cnpj = client_data.get("cnpj", "")

        ttk.Label(lf_client, text="ID:").grid(row=0, column=0, sticky="w", pady=(0, 8))
        id_var = tk.StringVar(value=client_id)
        e_id = ttk.Entry(lf_client, textvariable=id_var, state="readonly", width=10, justify="left")
        e_id.grid(row=0, column=1, sticky="w", padx=(8, 20), pady=(0, 8))

        ttk.Label(lf_client, text="CNPJ:").grid(row=0, column=2, sticky="w", pady=(0, 8))
        cnpj_var = tk.StringVar(value=cnpj)
        e_cnpj = ttk.Entry(lf_client, textvariable=cnpj_var, state="readonly", width=20, justify="left")
        e_cnpj.grid(row=0, column=3, sticky="w", padx=(8, 0), pady=(0, 8))

        # Linha 1: Razão Social (ocupa toda largura)
        ttk.Label(lf_client, text="Razão Social:").grid(row=1, column=0, sticky="w")
        razao = client_data.get("razao_social", "")
        razao_var = tk.StringVar(value=razao)
        e_razao = ttk.Entry(lf_client, textvariable=razao_var, state="readonly")
        e_razao.grid(row=1, column=1, columnspan=5, sticky="ew", padx=(8, 0))

        # C) Separator
        ttk.Separator(main_frame, orient="horizontal").pack(fill="x", pady=(0, 10))

        # D) Caixinha "Tipo de Demanda"
        lf_tipo = ttk.Labelframe(main_frame, text="Tipo de Demanda", padding=(12, 10))
        lf_tipo.pack(fill="both", expand=True, pady=(0, 10))

        from ..constants import REQUEST_TYPES

        selected_type = tk.StringVar(value=REQUEST_TYPES[0])

        for req_type in REQUEST_TYPES:
            ttk.Radiobutton(
                lf_tipo,
                text=req_type,
                variable=selected_type,
                value=req_type,
                bootstyle="primary",
            ).pack(anchor="w", pady=3)

        # E) Botões (mesmo padrão Nova/Excluir: width=10)
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x")

        result = {"value": None}

        def on_create():
            # Desabilitar botão para evitar double-submit
            btn_create.configure(state="disabled")
            btn_cancel.configure(state="disabled")

            result["value"] = selected_type.get()
            dlg.destroy()

        def on_cancel():
            result["value"] = None
            dlg.destroy()

        btn_create = ttk.Button(
            btn_frame,
            text="Criar",
            bootstyle="success",
            width=10,
            command=on_create,
        )
        btn_create.pack(side="left", padx=(0, 6), ipady=2)

        btn_cancel = ttk.Button(
            btn_frame,
            text="Cancelar",
            bootstyle="secondary",
            width=10,
            command=on_cancel,
        )
        btn_cancel.pack(side="left", padx=(6, 0), ipady=2)

        # Centralizar janela SEM FLASH
        show_centered_no_flash(dlg, self.winfo_toplevel(), width=680, height=420)

        # Aguardar fechamento da janela (modal)
        self.wait_window(dlg)

        return result["value"]

    def _center_paned_sash(self) -> None:
        """Centraliza o divisor do PanedWindow (50/50)."""
        if self._sash_centered:
            return

        try:
            # Forçar atualização do layout
            self.paned.update_idletasks()

            # Obter largura total do PanedWindow
            width = self.paned.winfo_width()

            if width > 1:
                # Centralizar sash na metade
                self.paned.sashpos(0, width // 2)
                self._sash_centered = True
                log.debug(f"Sash centralizado em {width // 2}px")
        except Exception as e:
            log.warning(f"Erro ao centralizar sash: {e}")

    def _get_main_app(self) -> Optional[Any]:
        """Retorna referência à aplicação principal."""
        return self.main_window
