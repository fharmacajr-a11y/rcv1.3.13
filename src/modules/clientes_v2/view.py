# -*- coding: utf-8 -*-
"""View principal do ClientesV2 - Padrão Hub completo.

FASE 2.5: Dados reais, busca/filtros funcionais, tema global completo.
"""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import ttk
from typing import Any, Optional, List

from src.ui.ctk_config import ctk
from src.ui.ui_tokens import APP_BG, SURFACE, SURFACE_DARK, TEXT_PRIMARY, BORDER
from src.modules.clientes_v2.views.toolbar import ClientesV2Toolbar
from src.modules.clientes_v2.views.actionbar import ClientesV2ActionBar
from src.modules.clientes_v2.tree_theme import apply_clients_v2_treeview_theme, apply_treeview_zebra_tags

# Importar ViewModel e dados reais do legacy
from src.modules.clientes.viewmodel import ClientesViewModel, ClienteRow
from src.modules.clientes.views.main_screen_helpers import ORDER_CHOICES, DEFAULT_ORDER_LABEL

log = logging.getLogger(__name__)


class ClientesV2Frame(ctk.CTkFrame):
    """Frame principal do módulo ClientesV2.

    FASE 2.5: Dados reais, busca/filtros, tema instant neo.
    """

    def __init__(
        self,
        master: tk.Misc,
        app: Optional[Any] = None,
        pick_mode: bool = False,
        on_cliente_selected: Optional[Any] = None,
        **kwargs: Any,
    ):
        """Inicializa ClientesV2Frame.

        Args:
            master: Widget pai
            app: Referência ao MainWindow (para acessar ações legacy)
            pick_mode: Se True, ativa modo seleção (oculta ActionBar, adiciona botões pick)
            on_cliente_selected: Callback chamado quando cliente é selecionado (pick_mode=True)
            **kwargs: Argumentos adicionais
        """
        # Container principal com APP_BG (igual Hub)
        super().__init__(master, fg_color=APP_BG, corner_radius=0, border_width=0)

        self.app = app  # Referência ao MainWindow
        self.current_mode = "Light"
        self.tree_widget: Optional[ttk.Treeview] = None
        self._theme_bind_id: Optional[str] = None
        self._selected_client_id: Optional[int] = None  # Cliente selecionado
        self._trash_mode: bool = False  # Modo lixeira ativo

        # Guard para evitar duplicação de editor (single instance)
        self._editor_dialog: Optional[Any] = None  # Referência ao diálogo aberto
        self._opening_editor: bool = False  # Flag reentrante: bloqueia durante criação

        # FASE 3.4: Modo pick (para integração com ANVISA)
        self._pick_mode: bool = pick_mode
        self._on_cliente_selected: Optional[Any] = on_cliente_selected

        # Cache de tema para evitar re-aplicar desnecessariamente
        self._cached_theme_colors: Optional[tuple] = None
        self._cached_theme_mode: Optional[str] = None

        # ViewModel com dados reais (mesmo usado pelo legacy)
        self._vm = ClientesViewModel(order_choices=ORDER_CHOICES, default_order_label=DEFAULT_ORDER_LABEL)

        # Estado de controles
        self._search_debounce_job: Optional[str] = None
        self._load_job: Optional[str] = None
        self._row_data_map: dict[str, ClienteRow] = {}  # iid -> ClienteRow

        self._build_ui()
        self._setup_theme_integration()

        # FASE 3.8: Atalhos de teclado
        self._setup_keyboard_shortcuts()

        # Carregar dados reais (assíncrono)
        self.after(100, self._initial_load)

        log.info("✅ [ClientesV2] Frame inicializado")

    def _build_ui(self) -> None:
        """Constrói interface do ClientesV2."""
        # Toolbar no topo
        self.toolbar = ClientesV2Toolbar(
            self,
            on_search=self._on_search,
            on_clear=self._on_clear_search,
            on_order_change=self._on_order_changed,
            on_status_change=self._on_status_changed,
            on_trash=self._on_toggle_trash,
            on_export=self._on_export,  # FASE 3.5
        )
        self.toolbar.pack(side="top", fill="x", padx=10, pady=(10, 5))

        # Container da lista (centro)
        list_container = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=10, border_width=0)
        list_container.pack(side="top", fill="both", expand=True, padx=10, pady=5)

        # Criar Treeview com style correto
        self._create_treeview(list_container)

        # FASE 3.4: ActionBar ou PickBar no rodapé
        if self._pick_mode:
            # Modo pick: botões Selecionar/Cancelar
            self._create_pick_bar()
        else:
            # Modo normal: ActionBar completa
            self.actionbar = ClientesV2ActionBar(
                self,
                on_new=self._on_new_client,
                on_edit=self._on_edit_client,
                on_files=self._on_client_files,
                on_upload=self._on_upload_client,
                on_delete=self._on_delete_client,
            )
            self.actionbar.pack(side="bottom", fill="x", padx=10, pady=(5, 10))

    def _create_treeview(self, parent: tk.Misc) -> None:
        """Cria Treeview com configuração completa de tema.

        TAREFA 3: ttk.Treeview com background E fieldbackground configurados.
        """
        # Obter modo atual
        try:
            self.current_mode = ctk.get_appearance_mode()
        except Exception:
            self.current_mode = "Light"

        # Aplicar tema ttk ANTES de criar a Treeview
        even_bg, odd_bg, fg, heading_bg, heading_fg = apply_clients_v2_treeview_theme(self.current_mode)

        # Criar Treeview usando ttk direto (sem wrapper que possa interferir)
        # FASE C: Adicionar colunas observacoes e ultima_alteracao
        columns = ("id", "razao_social", "cnpj", "nome", "whatsapp", "status", "observacoes", "ultima_alteracao")

        self.tree = ttk.Treeview(
            parent,
            columns=columns,
            show="headings",
            selectmode="browse",
            style="RC.ClientesV2.Treeview",  # Style customizado
        )

        # Configurar headings
        self.tree.heading("id", text="ID", anchor="center")
        self.tree.heading("razao_social", text="Razão Social", anchor="center")
        self.tree.heading("cnpj", text="CNPJ", anchor="center")
        self.tree.heading("nome", text="Nome", anchor="center")
        self.tree.heading("whatsapp", text="WhatsApp", anchor="w")
        self.tree.heading("status", text="Status", anchor="center")
        self.tree.heading("observacoes", text="Observações", anchor="w")
        self.tree.heading("ultima_alteracao", text="Última Alteração", anchor="center")

        # Configurar colunas
        self.tree.column("id", width=50, minwidth=45, anchor="center", stretch=False)
        self.tree.column("razao_social", width=280, minwidth=200, anchor="center", stretch=True)
        self.tree.column("cnpj", width=140, minwidth=120, anchor="center", stretch=False)
        self.tree.column("nome", width=180, minwidth=150, anchor="center", stretch=True)
        self.tree.column("whatsapp", width=120, minwidth=110, anchor="w", stretch=False)
        self.tree.column("status", width=150, minwidth=130, anchor="center", stretch=False)
        self.tree.column("observacoes", width=250, minwidth=180, anchor="w", stretch=True)
        self.tree.column("ultima_alteracao", width=150, minwidth=130, anchor="center", stretch=False)

        # Grid com scrollbar
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=self.tree.yview)  # type: ignore[attr-defined]
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)  # type: ignore[attr-defined]
        scrollbar.grid(row=0, column=1, sticky="ns", pady=5)

        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        # Aplicar tags zebra
        apply_treeview_zebra_tags(self.tree, even_bg, odd_bg, fg)

        # Guardar referência ao widget ttk interno
        self.tree_widget = self.tree

        # Binds para seleção e atalhos (unbind antes para evitar acúmulo)
        self.tree.unbind("<<TreeviewSelect>>")
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        # FASE 3.4: Em pick_mode, duplo clique seleciona; caso contrário, edita
        if self._pick_mode:
            self.tree.unbind("<Double-Button-1>")
            self.tree.bind("<Double-Button-1>", lambda e: self._on_pick_confirm())
        else:
            # Unbind todos os eventos relacionados
            self.tree.unbind("<Double-Button-1>")
            self.tree.unbind("<Return>")
            self.tree.unbind("<Button-3>")
            self.tree.unbind("<Button-1>")

            # Método único para duplo clique (sem lambda, mais determinístico)
            self.tree.bind("<Double-Button-1>", self._on_tree_double_click)
            self.tree.bind("<Return>", lambda e: self._open_client_editor(source="keyboard"))
            self.tree.bind("<Button-3>", self._on_tree_right_click)  # Context menu
            # FASE 3.9: Clique na coluna WhatsApp
            self.tree.bind("<Button-1>", self._on_tree_click)

        log.info("✅ [ClientesV2] Treeview criada com style RC.ClientesV2.Treeview")

    def force_redraw(self) -> None:
        """Força redraw leve da Treeview (sem recarregar dados).

        FASE 3.3: Chamado no restore da janela para eliminar tela preta.
        Apenas reaplicar style + zebra, sem I/O.
        """
        if not self.tree_widget:
            return

        try:
            mode = ctk.get_appearance_mode()
        except AttributeError:
            mode = "Light"

        # Reaplicar style ttk
        even_bg, odd_bg, fg, _, _ = apply_clients_v2_treeview_theme(mode)

        # Reaplicar zebra tags
        apply_treeview_zebra_tags(self.tree_widget, even_bg, odd_bg, fg)

        # Forçar update
        self.tree_widget.update_idletasks()

        log.debug("[ClientesV2] force_redraw() completo")

    def _on_tree_select(self, event: Any = None) -> None:
        """Handler quando uma linha é selecionada na Treeview.

        Atualiza self._selected_client_id e habilita/desabilita botões.
        """
        try:
            selection = self.tree.selection()

            if selection:
                # Pegar item selecionado
                item_id = selection[0]
                values = self.tree.item(item_id, "values")

                if values:
                    # ID está na primeira coluna
                    self._selected_client_id = int(values[0])
                    log.debug(f"[ClientesV2] Cliente selecionado: ID={self._selected_client_id}")

                    # Habilitar botões
                    if hasattr(self, "actionbar") and self.actionbar:
                        self.actionbar.set_selection_state(True)
                else:
                    self._selected_client_id = None
                    if hasattr(self, "actionbar") and self.actionbar:
                        self.actionbar.set_selection_state(False)
            else:
                # Nada selecionado
                self._selected_client_id = None
                if hasattr(self, "actionbar") and self.actionbar:
                    self.actionbar.set_selection_state(False)

        except Exception as e:
            log.error(f"[ClientesV2] Erro no handler de seleção: {e}", exc_info=True)
            self._selected_client_id = None

    def _on_tree_right_click(self, event: Any) -> None:
        """Handler para botão direito do mouse (context menu).

        Seleciona a linha sob o cursor e abre menu com ações.
        """
        try:
            # Identificar linha sob o cursor
            item_id = self.tree.identify_row(event.y)  # type: ignore[attr-defined]

            if not item_id:
                return  # Clique fora de uma linha

            # Selecionar a linha
            self.tree.selection_set(item_id)  # type: ignore[attr-defined]
            self.tree.focus(item_id)  # type: ignore[attr-defined]
            self._on_tree_select()  # Atualizar seleção

            # Criar menu CTk
            menu = ctk.CTkToplevel(self)
            menu.withdraw()  # type: ignore[attr-defined]
            menu.overrideredirect(True)  # type: ignore[attr-defined]
            menu.configure(fg_color=SURFACE_DARK, corner_radius=8)

            # Container com padding
            container = ctk.CTkFrame(menu, fg_color=SURFACE_DARK, corner_radius=8, border_width=1, border_color=BORDER)
            container.pack(fill="both", expand=True, padx=2, pady=2)

            # Botões do menu
            btn_width = 180
            btn_height = 32

            ctk.CTkButton(
                container,
                text="✏️ Editar",
                command=lambda: [menu.destroy(), self._on_edit_client()],
                width=btn_width,
                height=btn_height,
                fg_color="transparent",
                hover_color=BORDER,
                text_color=TEXT_PRIMARY,
                anchor="w",
            ).pack(padx=4, pady=(4, 2))

            ctk.CTkButton(
                container,
                text="📁 Arquivos",
                command=lambda: [menu.destroy(), self._on_client_files()],
                width=btn_width,
                height=btn_height,
                fg_color="transparent",
                hover_color=BORDER,
                text_color=TEXT_PRIMARY,
                anchor="w",
            ).pack(padx=4, pady=2)

            ctk.CTkButton(
                container,
                text="📤 Enviar documentos",
                command=lambda: [menu.destroy(), self._on_enviar_documentos()],
                width=btn_width,
                height=btn_height,
                fg_color="transparent",
                hover_color=BORDER,
                text_color=TEXT_PRIMARY,
                anchor="w",
            ).pack(padx=4, pady=2)

            ctk.CTkButton(
                container,
                text="🗑️ Excluir / Lixeira",
                command=lambda: [menu.destroy(), self._on_delete_client()],
                width=btn_width,
                height=btn_height,
                fg_color="transparent",
                hover_color=BORDER,
                text_color=TEXT_PRIMARY,
                anchor="w",
            ).pack(padx=4, pady=(2, 4))

            # Posicionar menu no cursor
            menu.update_idletasks()
            x = event.x_root
            y = event.y_root
            menu.geometry(f"+{x}+{y}")
            menu.deiconify()  # type: ignore[attr-defined]
            menu.lift()  # type: ignore[attr-defined]
            menu.focus_force()  # type: ignore[attr-defined]

            # Fechar ao clicar fora
            def close_on_focus_out(e: Any = None) -> None:
                try:
                    menu.destroy()
                except Exception:
                    pass

            menu.bind("<FocusOut>", close_on_focus_out)
            menu.bind("<Escape>", close_on_focus_out)

        except Exception as e:
            log.error(f"[ClientesV2] Erro ao abrir context menu: {e}", exc_info=True)

    def _setup_theme_integration(self) -> None:
        """Integra com sistema de temas global.

        FASE B: Usa APENAS AppearanceModeTracker (elimina duplicidade).
        """
        self._last_applied_mode = None  # Guard para evitar double apply

        try:
            # AppearanceModeTracker do CustomTkinter (ÚNICA fonte de verdade)
            AppearanceModeTracker = ctk.AppearanceModeTracker  # type: ignore[attr-defined]

            def on_appearance_change() -> None:
                """Callback do AppearanceModeTracker."""
                new_mode = ctk.get_appearance_mode()
                self._on_theme_changed(new_mode)

            AppearanceModeTracker.add(on_appearance_change, self)
            log.debug("[ClientesV2] AppearanceModeTracker registrado")
        except Exception as exc:
            log.warning(f"[ClientesV2] Falha ao registrar AppearanceModeTracker: {exc}")

    def _on_theme_changed(self, new_mode: str) -> None:
        """Handler quando tema muda - OTIMIZADO (sem rebuild).

        FASE B: Guard de modo duplicado para evitar double apply.
        """
        try:
            if not self.winfo_exists():
                return

            # FASE B: Guard - não reaplicar se já foi aplicado
            if hasattr(self, "_last_applied_mode") and self._last_applied_mode == new_mode:
                return

            self.current_mode = new_mode
            self._last_applied_mode = new_mode

            # APENAS reaplicar style + zebra (SEM rebuild)
            if self.tree_widget:
                even_bg, odd_bg, fg, _, _ = apply_clients_v2_treeview_theme(new_mode)
                apply_treeview_zebra_tags(self.tree_widget, even_bg, odd_bg, fg)

            # Atualizar toolbar e actionbar
            if hasattr(self, "toolbar") and self.toolbar:
                self.toolbar.refresh_theme()

            if hasattr(self, "actionbar") and self.actionbar:
                self.actionbar.refresh_theme()

            self.update_idletasks()

        except Exception:
            log.exception("[ClientesV2] Erro ao processar mudança de tema")

    def _load_sample_data(self) -> None:
        """Carrega dados de exemplo na Treeview."""
        if not self.tree_widget:
            return

        # Dados de exemplo
        sample_data = [
            ("1", "FARMACIA EXEMPLO LTDA", "12.345.678/0001-90", "João Silva", "(11) 98765-4321", "Novo Cliente"),
            ("2", "DROGARIA MODELO S.A.", "98.765.432/0001-10", "Maria Santos", "(21) 99876-5432", "Cadastro Pendente"),
            (
                "3",
                "FARMA MAIS COMERCIO",
                "11.222.333/0001-44",
                "Pedro Costa",
                "(31) 97654-3210",
                "Análise Do Ministério",
            ),
            ("4", "MEDICAMENTOS BRASIL", "22.333.444/0001-55", "Ana Oliveira", "(41) 96543-2109", "Novo Cliente"),
            ("5", "SAUDE E VIDA FARMA", "33.444.555/0001-66", "Carlos Lima", "(51) 95432-1098", "Cadastro Pendente"),
        ]

        for idx, row in enumerate(sample_data):
            tag = "even" if idx % 2 == 0 else "odd"
            self.tree_widget.insert("", "end", values=row, tags=(tag,))

        log.info(f"✅ [ClientesV2] {len(sample_data)} registros de exemplo carregados")

    def _initial_load(self) -> None:
        """Carga inicial de dados reais."""
        log.info("[ClientesV2] Iniciando carga de dados reais...")
        try:
            self._vm.refresh_from_service()
            self._render_rows()
            log.info(f"[ClientesV2] Dados carregados: {len(self._vm.get_rows())} clientes")
        except Exception as e:
            log.error(f"[ClientesV2] Erro ao carregar dados: {e}", exc_info=True)

    def _safe_get(self, obj: Any, key: str, default: Any = "") -> Any:
        """Extrai valor de dict OU objeto (suporta ambos).

        Args:
            obj: Dict ou objeto (dataclass, model, etc.)
            key: Chave/atributo a buscar
            default: Valor padrão se não encontrar

        Returns:
            Valor extraído ou default
        """
        if obj is None:
            return default

        # Tentar como dict primeiro
        if isinstance(obj, dict):
            return obj.get(key, default)

        # Tentar como objeto (getattr)
        return getattr(obj, key, default)

    def _map_order_label_to_params(self, order_label: str) -> tuple[str, bool]:
        """Mapeia label de ordenação para order_by e descending.

        Args:
            order_label: Label da ordenação ("Razão Social (A→Z)", etc.)

        Returns:
            Tupla (order_by, descending) para o service
        """
        # Mapa de labels para parâmetros do service
        mapping = {
            "ID (↑)": ("id", False),  # Menor para maior
            "ID (↓)": ("id", True),  # Maior para menor
            "Razão Social (A→Z)": ("razao_social", False),
            "Razão Social (Z→A)": ("razao_social", True),
            "Última Alteração ↓": ("ultima_alteracao", True),  # Mais recente primeiro
            "Última Alteração ↑": ("ultima_alteracao", False),  # Mais antiga primeiro
        }

        return mapping.get(order_label, ("id", True))  # Default: ID descendente

    def load_async(self, search: str = "", order_label: str = "", status: str = "", show_trash: bool = False) -> None:
        """Carrega dados com filtros aplicados (assíncrono).

        Args:
            search: Texto de busca
            order_label: Label de ordenação (ORDER_CHOICES)
            status: Filtro de status
            show_trash: Se True, mostra apenas lixeira; se False, mostra clientes ativos
        """
        # Cancelar job pendente
        if self._load_job:
            try:
                self.after_cancel(self._load_job)
            except Exception:
                pass
            self._load_job = None

        def _do_load():
            try:
                if show_trash:
                    # Modo lixeira: usar serviço específico
                    from src.modules.clientes import service as clientes_service

                    # Mapear ordenação do toolbar para parâmetros do service
                    order_by, descending = self._map_order_label_to_params(order_label)

                    deleted_clients = clientes_service.listar_clientes_na_lixeira(
                        order_by=order_by, descending=descending
                    )

                    # Converter para ClienteRow (suporta dict E objeto)
                    from src.modules.clientes.viewmodel import ClienteRow

                    rows = []
                    for idx, client in enumerate(deleted_clients):
                        row = ClienteRow(
                            id=str(self._safe_get(client, "id", "")),
                            razao_social=self._safe_get(client, "razao_social", ""),
                            cnpj=self._safe_get(client, "cnpj", ""),
                            nome=self._safe_get(client, "nome", ""),
                            whatsapp=self._safe_get(client, "numero", ""),
                            observacoes=self._safe_get(client, "obs", ""),
                            status="[LIXEIRA]",
                            ultima_alteracao=self._safe_get(client, "deleted_at", ""),
                            search_norm="",
                            raw=client,
                        )
                        rows.append(row)

                    # Filtro client-side: busca (caso o service não suporte)
                    if search:
                        search_lower = search.lower()
                        rows = [
                            r
                            for r in rows
                            if search_lower in (r.razao_social or "").lower()
                            or search_lower in (r.cnpj or "").lower()
                            or search_lower in (r.nome or "").lower()
                            or search_lower in (r.whatsapp or "").lower()
                        ]

                    # Filtro client-side: status (caso necessário)
                    if status and status != "Todos":
                        rows = [r for r in rows if status in (r.observacoes or "")]

                    # Renderizar diretamente
                    self._render_rows_from_list(rows)
                    log.debug(
                        f"[ClientesV2] Lixeira carregada: {len(rows)} clientes (busca='{search}', status='{status}')"
                    )
                else:
                    # Modo normal: usar ViewModel
                    self._vm.set_search_text(search if search else None, rebuild=False)
                    self._vm.set_status_filter(status if status else None, rebuild=False)
                    if order_label:
                        self._vm.set_order_label(order_label, rebuild=False)

                    # Rebuild com todos filtros aplicados
                    self._vm._rebuild_rows()

                    # Renderizar
                    self._render_rows()

                    log.debug(
                        f"[ClientesV2] Carregado: {len(self._vm.get_rows())} clientes (busca='{search}', status='{status}')"
                    )
            except Exception as e:
                log.error(f"[ClientesV2] Erro ao carregar dados: {e}", exc_info=True)
            finally:
                self._load_job = None

        # Agendar load
        self._load_job = self.after(50, _do_load)

    def _render_rows(self) -> None:
        """Renderiza rows do ViewModel na Treeview com zebra tags.

        FASE C: Incluindo observacoes e ultima_alteracao.
        """
        if not self.tree_widget:
            return

        # Limpar tree
        for item in self.tree_widget.get_children():
            self.tree_widget.delete(item)

        # Limpar mapa
        self._row_data_map.clear()

        # Inserir rows
        rows = self._vm.get_rows()
        for row in rows:
            # FASE C: Formatar data de ultima_alteracao
            ultima_alt_str = self._format_datetime(row.ultima_alteracao)

            iid = self.tree_widget.insert(
                "",
                "end",
                values=(
                    row.id,
                    row.razao_social,
                    row.cnpj,
                    row.nome,
                    row.whatsapp,
                    row.status,
                    row.observacoes or "",  # FASE C: Observações
                    ultima_alt_str,  # FASE C: Última alteração formatada
                ),
            )
            self._row_data_map[iid] = row

        # Aplicar zebra striping
        try:
            mode = ctk.get_appearance_mode()
        except AttributeError:
            mode = "Light"

        # Apenas aplicar tema se mudou (otimização)
        if self._cached_theme_mode != mode or not self._cached_theme_colors:
            even_bg, odd_bg, fg, _, _ = apply_clients_v2_treeview_theme(mode)
            self._cached_theme_colors = (even_bg, odd_bg, fg)
            self._cached_theme_mode = mode
        else:
            even_bg, odd_bg, fg = self._cached_theme_colors

        apply_treeview_zebra_tags(self.tree_widget, even_bg, odd_bg, fg)

        log.debug(f"[ClientesV2] Renderizados {len(rows)} clientes")

    def _render_rows_from_list(self, rows: List[ClienteRow]) -> None:
        """Renderiza rows de lista customizada (ex: lixeira).

        Args:
            rows: Lista de ClienteRow para renderizar
        """
        if not self.tree_widget:
            return

        # Limpar tree
        for item in self.tree_widget.get_children():
            self.tree_widget.delete(item)

        # Limpar mapa
        self._row_data_map.clear()

        # Inserir rows
        for row in rows:
            ultima_alt_str = self._format_datetime(row.ultima_alteracao)

            iid = self.tree_widget.insert(
                "",
                "end",
                values=(
                    row.id,
                    row.razao_social,
                    row.cnpj,
                    row.nome,
                    row.whatsapp,
                    row.status,
                    row.observacoes or "",
                    ultima_alt_str,
                ),
            )
            self._row_data_map[iid] = row

        # Aplicar zebra striping
        try:
            mode = ctk.get_appearance_mode()
        except AttributeError:
            mode = "Light"

        # Apenas aplicar tema se mudou (otimização)
        if self._cached_theme_mode != mode or not self._cached_theme_colors:
            even_bg, odd_bg, fg, _, _ = apply_clients_v2_treeview_theme(mode)
            self._cached_theme_colors = (even_bg, odd_bg, fg)
            self._cached_theme_mode = mode
        else:
            even_bg, odd_bg, fg = self._cached_theme_colors

        apply_treeview_zebra_tags(self.tree_widget, even_bg, odd_bg, fg)

        log.debug(f"[ClientesV2] Renderizados {len(rows)} itens (modo customizado)")

    def _format_datetime(self, dt_str: str) -> str:
        """Formata data/hora para pt-BR.

        FASE C: dd/MM/yyyy HH:mm ou dd/MM/yyyy se sem hora.

        Args:
            dt_str: String de data/hora (ISO ou vazio)

        Returns:
            Data formatada ou vazio
        """
        if not dt_str or dt_str == "":
            return ""

        try:
            from datetime import datetime

            # Tentar parsear ISO (com ou sem timezone)
            dt_str_clean = dt_str.replace("Z", "+00:00") if "Z" in dt_str else dt_str

            # Tentar diversos formatos
            for fmt in [
                "%Y-%m-%dT%H:%M:%S.%f%z",  # ISO com microsegundos e timezone
                "%Y-%m-%dT%H:%M:%S%z",  # ISO com timezone
                "%Y-%m-%dT%H:%M:%S.%f",  # ISO com microsegundos
                "%Y-%m-%dT%H:%M:%S",  # ISO simples
                "%Y-%m-%d %H:%M:%S",  # SQL datetime
                "%Y-%m-%d",  # Apenas data
            ]:
                try:
                    dt = datetime.strptime(dt_str_clean, fmt)

                    # Formatar em pt-BR
                    if dt.hour == 0 and dt.minute == 0 and dt.second == 0:
                        # Apenas data
                        return dt.strftime("%d/%m/%Y")
                    else:
                        # Data e hora
                        return dt.strftime("%d/%m/%Y %H:%M")
                except ValueError:
                    continue

            # Se não conseguiu parsear, retornar como está
            return dt_str

        except Exception as e:
            log.debug(f"[ClientesV2] Erro ao formatar data '{dt_str}': {e}")
            return dt_str

    # Callbacks (implementados com dados reais)
    def _on_search(self, text: str) -> None:
        """Handler para botão Buscar."""
        search_text = self.toolbar.get_search_text()
        order_label = self.toolbar.get_order()
        status = self.toolbar.get_status()
        log.info(f"[ClientesV2] Buscar: '{search_text}'")
        self.load_async(search=search_text, order_label=order_label, status=status)

    def _on_clear_search(self) -> None:
        """Handler para botão Limpar busca."""
        log.info("[ClientesV2] Limpar busca")
        self.toolbar.clear_search()
        self.load_async()

    def _on_order_changed(self, order: str) -> None:
        """Handler para mudança de ordenação."""
        log.info(f"[ClientesV2] Ordenação alterada: {order}")
        search_text = self.toolbar.get_search_text()
        status = self.toolbar.get_status()
        self.load_async(search=search_text, order_label=order, status=status)

    def _on_status_changed(self, status: str) -> None:
        """Handler para mudança de filtro de status."""
        log.info(f"[ClientesV2] Status alterado: {status}")
        search_text = self.toolbar.get_search_text()
        order_label = self.toolbar.get_order()
        self.load_async(search=search_text, order_label=order_label, status=status)

    def _on_export(self) -> None:
        """Handler para exportação de dados (FASE 3.5).

        Abre diálogo para escolher formato (CSV/XLSX) e local de salvamento.
        Exporta dados visíveis/filtrados da tree usando src/modules/clientes/export.py
        """
        from tkinter import filedialog, messagebox
        from pathlib import Path
        from src.modules.clientes import export

        try:
            # Verificar se há dados para exportar
            if not self._row_data_map:
                messagebox.showinfo(
                    "Exportação",
                    "Nenhum dado disponível para exportar.",
                    parent=self.winfo_toplevel(),  # type: ignore[attr-defined]
                )
                return

            # Obter dados visíveis na tree (respeitando filtros)
            rows_to_export = list(self._row_data_map.values())

            if not rows_to_export:
                messagebox.showinfo(
                    "Exportação",
                    "Nenhum cliente para exportar.",
                    parent=self.winfo_toplevel(),  # type: ignore[attr-defined]
                )
                return

            # Determinar tipos de arquivo disponíveis
            filetypes = [("CSV (separado por vírgulas)", "*.csv")]

            if export.is_xlsx_available():
                filetypes.append(("Excel (XLSX)", "*.xlsx"))

            # Abrir diálogo de salvamento
            filepath = filedialog.asksaveasfilename(
                parent=self.winfo_toplevel(),  # type: ignore[attr-defined]
                title="Exportar Clientes",
                defaultextension=".csv",
                filetypes=filetypes,
                initialfile="clientes_export",
            )

            if not filepath:
                # Usuário cancelou
                log.info("[ClientesV2] Exportação cancelada pelo usuário")
                return

            filepath_obj = Path(filepath)

            # Exportar baseado na extensão escolhida
            if filepath_obj.suffix.lower() == ".xlsx":
                export.export_clients_to_xlsx(rows_to_export, filepath_obj)
                format_name = "Excel"
            else:
                export.export_clients_to_csv(rows_to_export, filepath_obj)
                format_name = "CSV"

            # Sucesso
            messagebox.showinfo(
                "Sucesso",
                f"Dados exportados com sucesso!\n\n"
                f"Arquivo: {filepath_obj.name}\n"
                f"Formato: {format_name}\n"
                f"Clientes: {len(rows_to_export)}",
                parent=self.winfo_toplevel(),  # type: ignore[attr-defined]
            )

            log.info(f"[ClientesV2] Exportados {len(rows_to_export)} clientes para {filepath_obj}")

        except ImportError as e:
            log.error(f"[ClientesV2] Erro de importação ao exportar: {e}")
            messagebox.showerror(
                "Erro",
                f"Biblioteca necessária não está disponível:\n{e}",
                parent=self.winfo_toplevel(),  # type: ignore[attr-defined]
            )
        except Exception as e:
            log.error(f"[ClientesV2] Erro ao exportar: {e}", exc_info=True)
            messagebox.showerror(
                "Erro",
                f"Erro ao exportar dados:\n{e}",
                parent=self.winfo_toplevel(),  # type: ignore[attr-defined]
            )

    def _on_toggle_trash(self) -> None:
        """Handler para botão Lixeira - alterna entre clientes ativos e lixeira."""
        self._trash_mode = not self._trash_mode

        mode_str = "LIXEIRA" if self._trash_mode else "ATIVOS"
        log.info(f"[ClientesV2] Modo alterado: {mode_str}")

        # Atualizar label do botão na toolbar
        if hasattr(self.toolbar, "update_trash_mode"):
            self.toolbar.update_trash_mode(self._trash_mode)

        # Recarregar com filtro de lixeira
        search_text = self.toolbar.get_search_text() if self.toolbar else ""
        order_label = self.toolbar.get_order() if self.toolbar else ""
        status = self.toolbar.get_status() if self.toolbar else ""
        self.load_async(search=search_text, order_label=order_label, status=status, show_trash=self._trash_mode)

    def _setup_keyboard_shortcuts(self) -> None:
        """Configura atalhos de teclado (FASE 3.8).

        Atalhos disponíveis:
        - F5: Recarregar lista
        - Ctrl+N: Novo cliente
        - Ctrl+E: Editar cliente
        - Delete: Excluir/mover para lixeira
        """
        # Bind no frame para capturar eventos de teclado
        self.bind("<F5>", self._on_reload_shortcut)
        self.bind("<Control-n>", self._on_new_client)
        self.bind("<Control-N>", self._on_new_client)
        self.bind("<Control-e>", self._on_edit_client)
        self.bind("<Control-E>", self._on_edit_client)
        self.bind("<Delete>", self._on_delete_client)

        # Focar o frame para receber eventos de teclado
        self.focus_set()

        log.info("✅ [ClientesV2] Atalhos de teclado configurados (F5, Ctrl+N, Ctrl+E, Delete)")

    def _on_reload_shortcut(self, event: Any = None) -> str:
        """Handler para atalho F5 (recarregar lista).

        Args:
            event: Evento de teclado (opcional)

        Returns:
            'break' para evitar propagação do evento
        """
        log.info("[ClientesV2] F5 pressionado - recarregando lista")
        self.load_async()
        return "break"

    def _on_new_client(self, event: Any = None) -> str | None:
        """Handler para botão Novo Cliente.

        FASE 4 FINAL: Abre diálogo CustomTkinter (100% CTk).
        FASE 3.8: Aceita event opcional para atalho Ctrl+N.

        Args:
            event: Evento de teclado (opcional)

        Returns:
            'break' se event fornecido, None caso contrário
        """
        if not self.app:
            log.error("[ClientesV2] App não disponível para novo cliente")
            from tkinter import messagebox

            messagebox.showerror(
                "Erro",
                "Não foi possível acessar o controlador do aplicativo.\nTente recarregar o módulo.",
                parent=self.winfo_toplevel(),  # type: ignore[attr-defined]
            )
            return "break" if event else None

        log.info("[ClientesV2] Novo cliente - abrindo diálogo")

        try:
            from src.modules.clientes_v2.views.client_editor_dialog import ClientEditorDialog

            def on_saved(data: dict) -> None:
                """Callback após salvar."""
                log.info(f"[ClientesV2] Cliente criado: {data.get('Razão Social')}")
                self.load_async()

            # Abrir diálogo modal
            dialog = ClientEditorDialog(
                parent=self.winfo_toplevel(),  # type: ignore[attr-defined]
                client_id=None,
                on_save=on_saved,
            )
            dialog.focus()  # type: ignore[attr-defined]

        except Exception as e:
            log.error(f"[ClientesV2] Erro ao abrir diálogo de novo cliente: {e}", exc_info=True)

        return "break" if event else None

    def _on_tree_double_click(self, event: tk.Event) -> str:
        """Handler dedicado para duplo clique na lista.

        Identifica a linha clicada, seleciona e abre o editor.
        Retorna 'break' para impedir propagação.
        """
        if not self.tree:
            return "break"

        # Identificar linha clicada
        try:
            region = self.tree.identify("region", event.x, event.y)
            if region != "cell":  # Clicou fora das células
                return "break"

            item_id = self.tree.identify_row(event.y)
            if not item_id:
                return "break"

            # Selecionar linha clicada
            self.tree.selection_set(item_id)
            self.tree.focus(item_id)

            # Atualizar ID selecionado
            row_data = self._row_data_map.get(item_id)
            if row_data:
                self._selected_client_id = row_data.id
                log.debug(f"[ClientesV2] Duplo clique: cliente ID={self._selected_client_id}")

            # Abrir editor (centralizado)
            self._open_client_editor(source="doubleclick")

        except Exception as e:
            log.error(f"[ClientesV2] Erro no duplo clique: {e}", exc_info=True)

        return "break"  # Impedir propagação

    def _on_edit_client(self, event: Any = None) -> str | None:
        """Handler para botão Editar Cliente ou atalho Ctrl+E.

        Delega para _open_client_editor (método centralizado).

        Args:
            event: Evento de teclado (opcional)

        Returns:
            'break' se event fornecido, None caso contrário
        """
        self._open_client_editor(source="button" if not event else "shortcut")
        return "break" if event else None

    def _open_client_editor(self, source: str = "unknown") -> None:
        """Centraliza lógica de abertura do editor (single instance com guard reentrante).

        Args:
            source: Origem da chamada (doubleclick, button, shortcut, etc.) para logs
        """
        import uuid

        session_id = str(uuid.uuid4())[:8]

        log.info(f"[ClientesV2:{session_id}] Solicitação de abertura do editor (source={source})")

        # GUARD 1: Se já estamos criando um editor, ignorar
        if self._opening_editor:
            log.debug(f"[ClientesV2:{session_id}] Abertura bloqueada: já criando editor")
            return

        # GUARD 2: Se diálogo já existe e está visível, apenas dar foco
        if self._editor_dialog is not None:
            try:
                if self._editor_dialog.winfo_exists():
                    log.info(f"[ClientesV2:{session_id}] Diálogo já aberto, dando foco")
                    self._editor_dialog.lift()
                    self._editor_dialog.focus_force()
                    return
            except Exception:
                # Diálogo foi destruído mas referência não foi limpa
                log.debug(f"[ClientesV2:{session_id}] Referência obsoleta, limpando")
                self._editor_dialog = None

        # Validações
        if not self.app:
            log.error(f"[ClientesV2:{session_id}] App não disponível")
            from tkinter import messagebox

            messagebox.showerror(
                "Erro",
                "Não foi possível acessar o controlador do aplicativo.\nTente recarregar o módulo.",
                parent=self.winfo_toplevel(),  # type: ignore[attr-defined]
            )
            return

        if not self._selected_client_id:
            log.warning(f"[ClientesV2:{session_id}] Nenhum cliente selecionado")
            from tkinter import messagebox

            messagebox.showwarning(
                "Atenção",
                "Selecione um cliente para editar.",
                parent=self.winfo_toplevel(),  # type: ignore[attr-defined]
            )
            return

        # Ativar flag de reentrância
        self._opening_editor = True
        log.info(f"[ClientesV2:{session_id}] Criando editor para cliente ID={self._selected_client_id}")

        try:
            from src.modules.clientes_v2.views.client_editor_dialog import ClientEditorDialog

            def on_saved(data: dict) -> None:
                """Callback após salvar."""
                log.info(f"[ClientesV2:{session_id}] Cliente {self._selected_client_id} salvo")
                self.load_async()

            def on_closed() -> None:
                """Callback quando diálogo é fechado."""
                log.info(f"[ClientesV2:{session_id}] Diálogo fechado, limpando referências")
                self._editor_dialog = None
                self._opening_editor = False

            # Criar diálogo modal
            self._editor_dialog = ClientEditorDialog(
                parent=self.winfo_toplevel(),  # type: ignore[attr-defined]
                client_id=self._selected_client_id,
                on_save=on_saved,
                on_close=on_closed,
                session_id=session_id,  # Passar session_id para logs
            )

            # Desativar flag após criação (diálogo já está em withdraw/deiconify)
            self._opening_editor = False
            log.info(f"[ClientesV2:{session_id}] Editor criado com sucesso")

        except Exception as e:
            log.error(f"[ClientesV2:{session_id}] Erro ao criar editor: {e}", exc_info=True)
            self._editor_dialog = None
            self._opening_editor = False

    def _on_client_files(self) -> None:
        """Handler para botão Arquivos do Cliente.

        FASE 4: Abre gerenciador de arquivos via diálogo CTk.
        """
        if not self.app:
            log.error("[ClientesV2] App não disponível para arquivos")
            from tkinter import messagebox

            messagebox.showerror(
                "Erro",
                "Não foi possível acessar o controlador do aplicativo.\nTente recarregar o módulo.",
                parent=self.winfo_toplevel(),  # type: ignore[attr-defined]
            )
            return

        if not self._selected_client_id:
            from tkinter import messagebox

            messagebox.showwarning(
                "Atenção",
                "Selecione um cliente para ver os arquivos.",
                parent=self.winfo_toplevel(),  # type: ignore[attr-defined]
            )
            return

        log.info(f"[ClientesV2] Arquivos do cliente ID={self._selected_client_id} (abrindo ClientFilesDialog)")

        try:
            # Buscar dados do cliente
            from src.modules.clientes import service as clientes_service

            cliente = clientes_service.fetch_cliente_by_id(self._selected_client_id)

            if not cliente:
                from tkinter import messagebox

                messagebox.showerror(
                    "Erro",
                    "Cliente não encontrado.",
                    parent=self.winfo_toplevel(),  # type: ignore[attr-defined]
                )
                return

            # Abrir diálogo de arquivos funcional (browser real de Supabase Storage)
            from src.modules.clientes_v2.views.client_files_dialog import ClientFilesDialog

            ClientFilesDialog(
                parent=self.winfo_toplevel(),  # type: ignore[attr-defined]
                client_id=self._selected_client_id,
                client_name=cliente.get("razao_social", "Cliente"),
            )
            # Não precisa chamar focus() - diálogo já faz grab_set no __init__

        except Exception as e:
            log.error(f"[ClientesV2] Erro ao abrir arquivos: {e}", exc_info=True)
            from tkinter import messagebox

            messagebox.showerror(
                "Erro",
                f"Erro ao abrir arquivos: {e}",
                parent=self.winfo_toplevel(),  # type: ignore[attr-defined]
            )

    def _on_upload_client(self) -> None:
        """Handler para botão Upload de arquivos (FASE 3.3).

        Abre diálogo de upload para o cliente selecionado.
        """
        if not self._selected_client_id:
            from tkinter import messagebox

            messagebox.showwarning(
                "Atenção",
                "Selecione um cliente para fazer upload de arquivos.",
                parent=self.winfo_toplevel(),  # type: ignore[attr-defined]
            )
            return

        try:
            # Buscar dados do cliente
            from src.modules.clientes import service as clientes_service

            cliente = clientes_service.fetch_cliente_by_id(self._selected_client_id)

            if not cliente:
                from tkinter import messagebox

                messagebox.showerror(
                    "Erro",
                    "Cliente não encontrado.",
                    parent=self.winfo_toplevel(),  # type: ignore[attr-defined]
                )
                return

            # Abrir diálogo de upload
            from src.modules.clientes_v2.views.upload_dialog import ClientUploadDialog

            dialog = ClientUploadDialog(
                parent=self.winfo_toplevel(),  # type: ignore[attr-defined]
                client_id=self._selected_client_id,
                client_name=cliente.get("razao_social", "Cliente"),
                on_complete=lambda: self.load_async(),  # Refresh após upload
            )
            dialog.focus()  # type: ignore[attr-defined]

        except Exception as e:
            log.error(f"[ClientesV2] Erro ao abrir upload: {e}", exc_info=True)
            from tkinter import messagebox

            messagebox.showerror(
                "Erro",
                f"Erro ao abrir diálogo de upload: {e}",
                parent=self.winfo_toplevel(),  # type: ignore[attr-defined]
            )

    def _on_enviar_documentos(self) -> None:
        """Handler para enviar documentos do cliente (via context menu).

        Abre o dialog de editor com foco no botão de upload.
        """
        if not self._selected_client_id:
            from tkinter import messagebox

            messagebox.showwarning(
                "Atenção",
                "Selecione um cliente para enviar documentos.",
                parent=self.winfo_toplevel(),  # type: ignore[attr-defined]
            )
            return

        log.info(f"[ClientesV2] Enviar documentos para cliente ID={self._selected_client_id}")

        try:
            from src.modules.clientes_v2.views.client_editor_dialog import ClientEditorDialog

            def on_saved(data: dict) -> None:
                """Callback após salvar."""
                log.info(f"[ClientesV2] Cliente {self._selected_client_id} atualizado após upload")
                self.load_async()

            # Abrir diálogo e automaticamente clicar "Enviar documentos"
            dialog = ClientEditorDialog(
                parent=self.winfo_toplevel(),  # type: ignore[attr-defined]
                client_id=self._selected_client_id,
                on_save=on_saved,
            )

            # Aguardar diálogo renderizar e depois acionar upload
            def trigger_upload():
                try:
                    if hasattr(dialog, "_on_enviar_documentos"):
                        dialog._on_enviar_documentos()
                except Exception as e:
                    log.error(f"[ClientesV2] Erro ao acionar upload automaticamente: {e}")

            dialog.after(200, trigger_upload)
            dialog.focus()  # type: ignore[attr-defined]

        except Exception as e:
            log.error(f"[ClientesV2] Erro ao abrir diálogo para upload: {e}", exc_info=True)

    def _on_delete_client(self, event: Any = None) -> str | None:
        """Handler para botão Excluir Cliente.

        FASE 4: Move para lixeira usando fluxo legacy.
        FASE 3.8: Aceita event opcional para atalho Delete.

        Args:
            event: Evento de teclado (opcional)

        Returns:
            'break' se event fornecido, None caso contrário
        """
        if not self.app:
            log.error("[ClientesV2] App não disponível para excluir")
            from tkinter import messagebox

            messagebox.showerror(
                "Erro",
                "Não foi possível acessar o controlador do aplicativo.\nTente recarregar o módulo.",
                parent=self.winfo_toplevel(),  # type: ignore[attr-defined]
            )
            return "break" if event else None

        if not self._selected_client_id:
            # Sem seleção: ignora silenciosamente (comportamento legacy)
            return "break" if event else None

        # Pegar dados do cliente selecionado
        row_data = None
        for iid, data in self._row_data_map.items():
            if int(data.id) == self._selected_client_id:
                row_data = data
                break

        razao = row_data.razao_social if row_data else ""
        label_cli = f"{razao} (ID {self._selected_client_id})" if razao else f"ID {self._selected_client_id}"

        from tkinter import messagebox

        confirm = messagebox.askyesno(
            "Enviar para Lixeira",
            f"Deseja enviar o cliente {label_cli} para a Lixeira?",
            parent=self.winfo_toplevel(),  # type: ignore[attr-defined]
        )

        if not confirm:
            return "break" if event else None

        log.info(f"[ClientesV2] Excluir cliente ID={self._selected_client_id}")

        try:
            # Chamar service legacy
            from src.modules.clientes import service as clientes_service
            from src.modules.lixeira import refresh_if_open as refresh_lixeira_if_open

            clientes_service.mover_cliente_para_lixeira(self._selected_client_id)

            messagebox.showinfo(
                "Sucesso",
                f"Cliente {label_cli} movido para a Lixeira.",
                parent=self.winfo_toplevel(),  # type: ignore[attr-defined]
            )

            # Refresh lixeira se aberta
            refresh_lixeira_if_open()

            # Refresh lista
            self._selected_client_id = None
            self.load_async()

        except Exception as e:
            log.error(f"[ClientesV2] Erro ao excluir cliente: {e}", exc_info=True)
            messagebox.showerror(
                "Erro",
                f"Erro ao enviar cliente para lixeira: {e}",
                parent=self.winfo_toplevel(),  # type: ignore[attr-defined]
            )

        return "break" if event else None

    def _on_tree_click(self, event: Any) -> None:
        """Handler para clique simples na Treeview.

        FASE 3.9: Detecta clique na coluna WhatsApp e abre URL wa.me.

        Args:
            event: Evento de clique do mouse
        """
        try:
            # Identificar linha e coluna clicadas
            region = self.tree.identify_region(event.x, event.y)

            if region != "cell":
                return

            row_id = self.tree.identify_row(event.y)
            column_id = self.tree.identify_column(event.x)

            if not row_id or not column_id:
                return

            # Verificar se é a coluna WhatsApp (coluna #5)
            if column_id != "#5":
                return

            # Pegar valor do WhatsApp
            values = self.tree.item(row_id, "values")
            if not values or len(values) < 5:
                return

            whatsapp_raw = str(values[4])  # Índice 4 = coluna WhatsApp

            if not whatsapp_raw or whatsapp_raw.strip() == "":
                return

            # Normalizar telefone e abrir WhatsApp
            phone_normalized = self._normalize_phone_for_whatsapp(whatsapp_raw)

            if phone_normalized:
                url = self._whatsapp_url(phone_normalized)
                log.info(f"[ClientesV2] Abrindo WhatsApp: {url}")

                import webbrowser

                webbrowser.open(url)

        except Exception as e:
            log.error(f"[ClientesV2] Erro ao processar clique no WhatsApp: {e}", exc_info=True)

    @staticmethod
    def _normalize_phone_for_whatsapp(raw: str) -> str | None:
        """Normaliza número de telefone para formato WhatsApp.

        FASE 3.9: Remove formatação e adiciona código do país (55) se necessário.

        Args:
            raw: Número bruto (ex: '(11) 98765-4321', '+55 11 98765-4321')

        Returns:
            Número normalizado apenas com dígitos e prefixo 55, ou None se inválido

        Examples:
            >>> _normalize_phone_for_whatsapp('(11) 98765-4321')
            '5511987654321'
            >>> _normalize_phone_for_whatsapp('+55 11 98765-4321')
            '5511987654321'
            >>> _normalize_phone_for_whatsapp('11987654321')
            '5511987654321'
            >>> _normalize_phone_for_whatsapp('')
            None
        """
        if not raw or not raw.strip():
            return None

        # Remover tudo que não é dígito
        digits = "".join(c for c in raw if c.isdigit())

        if not digits:
            return None

        # Se não começa com 55, adicionar (código do Brasil)
        if not digits.startswith("55"):
            digits = "55" + digits

        # Validação básica: mínimo 12 dígitos (55 + DDD + número)
        if len(digits) < 12:
            return None

        return digits

    @staticmethod
    def _whatsapp_url(phone_digits: str) -> str:
        """Gera URL do WhatsApp Web/App.

        FASE 3.9: Cria URL wa.me para abrir conversa.

        Args:
            phone_digits: Número normalizado apenas com dígitos (ex: '5511987654321')

        Returns:
            URL completa do WhatsApp

        Examples:
            >>> _whatsapp_url('5511987654321')
            'https://wa.me/5511987654321'
        """
        return f"https://wa.me/{phone_digits}"

    def destroy(self) -> None:
        """Cleanup antes de destruir."""
        # Cancelar jobs pendentes
        if self._search_debounce_job:
            try:
                self.after_cancel(self._search_debounce_job)
            except Exception:
                pass

        if self._load_job:
            try:
                self.after_cancel(self._load_job)
            except Exception:
                pass

        # Remover do AppearanceModeTracker
        try:
            AppearanceModeTracker = ctk.AppearanceModeTracker  # type: ignore[attr-defined]

            AppearanceModeTracker.remove(self)
        except Exception:
            pass

        # Não precisa unbind porque bindamos no root, não no self

        super().destroy()

    # ========================================================================
    # FASE 3.4: Métodos de Pick Mode (integração com ANVISA)
    # ========================================================================

    def _create_pick_bar(self) -> None:
        """Cria barra com botões Selecionar/Cancelar para pick_mode."""
        pick_bar = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=10, border_width=0)
        pick_bar.pack(side="bottom", fill="x", padx=10, pady=(5, 10))

        # Container centralizado para os botões
        btn_container = ctk.CTkFrame(pick_bar, fg_color="transparent")
        btn_container.pack(expand=True, pady=10)

        # Botão Selecionar (verde)
        btn_select = ctk.CTkButton(
            btn_container,
            text="✓ Selecionar Cliente",
            command=self._on_pick_confirm,
            width=180,
            height=36,
            font=("Segoe UI", 13, "bold"),
            fg_color="#28a745",
            hover_color="#218838",
        )
        btn_select.pack(side="left", padx=5)

        # Botão Cancelar (cinza)
        btn_cancel = ctk.CTkButton(
            btn_container,
            text="✕ Cancelar",
            command=self._on_pick_cancel,
            width=140,
            height=36,
            font=("Segoe UI", 13),
            fg_color="#6c757d",
            hover_color="#5a6268",
        )
        btn_cancel.pack(side="left", padx=5)

    def _on_pick_confirm(self) -> None:
        """Confirma seleção de cliente no pick_mode."""
        if not self._pick_mode:
            return

        # Obter seleção atual
        selection = self.tree.selection()
        if not selection:
            from tkinter import messagebox

            messagebox.showwarning(
                "Atenção",
                "Selecione um cliente primeiro.",
                parent=self.winfo_toplevel(),  # type: ignore[attr-defined]
            )
            return

        # Obter dados do cliente via _row_data_map
        iid = selection[0]
        client_row = self._row_data_map.get(iid)

        if not client_row:
            log.warning(f"[ClientesV2][Pick] Cliente {iid} não encontrado no mapa")
            return

        # Converter ClienteRow para dict para compatibilidade com ANVISA
        client_data = {
            "id": client_row.id,
            "razao_social": client_row.razao_social,
            "cnpj": client_row.cnpj or "",
            "nome": client_row.nome or "",
            "whatsapp": client_row.whatsapp or "",
            "status": client_row.status or "",
        }

        log.info(f"[ClientesV2][Pick] Cliente selecionado: {client_data['razao_social']} (ID: {client_data['id']})")

        # Chamar callback se fornecido
        if self._on_cliente_selected:
            try:
                self._on_cliente_selected(client_data)
            except Exception as e:
                log.error(f"[ClientesV2][Pick] Erro no callback: {e}", exc_info=True)

    def _on_pick_cancel(self) -> None:
        """Cancela seleção no pick_mode (não chama callback)."""
        if not self._pick_mode:
            return

        log.info("[ClientesV2][Pick] Seleção cancelada pelo usuário")
