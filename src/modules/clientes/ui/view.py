# -*- coding: utf-8 -*-
"""View principal do ClientesV2 - Padrão Hub completo.

FASE 2.5: Dados reais, busca/filtros funcionais, tema global completo.
"""

from __future__ import annotations

import logging
import threading
import time
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk
from typing import Any, Optional, List

from src.ui.ctk_config import ctk
from src.ui.widgets.button_factory import make_btn
from src.ui.ui_tokens import APP_BG, SURFACE, SURFACE_DARK, TEXT_PRIMARY, BORDER
from src.ui.ttk_treeview_theme import apply_zebra
from src.ui.widgets.ctk_treeview_container import CTkTreeviewContainer
from src.ui.dialogs.rc_dialogs import (
    ask_yes_no as _ask_yes_no,
    show_info as _show_info,
    show_error as _show_error,
    show_warning as _show_warning,
)
from src.utils.formatters import format_cnpj as _fmt_cnpj, format_whatsapp as _fmt_whatsapp
from src.modules.clientes.ui.views.toolbar import ClientesV2Toolbar
from src.modules.clientes.ui.views.actionbar import ClientesV2ActionBar

# Importar ViewModel e dados reais do legacy
from src.modules.clientes.core.viewmodel import ClientesViewModel, ClienteRow
from src.modules.clientes.core.ui_helpers import ORDER_CHOICES, DEFAULT_ORDER_LABEL

log = logging.getLogger(__name__)

# Constantes para padding visual das colunas (respiro interno)
CELL_PAD_PX = 12  # Padding interno nas bordas das colunas (como ID)


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
        self._tree_colors: Any = None  # TreeColors do tema atual
        self._theme_bind_id: Optional[str] = None
        self._selected_client_id: Optional[int] = None  # Cliente selecionado
        self._trash_mode: bool = False  # Modo lixeira ativo

        # Guard para evitar duplicação de editor (single instance)
        self._editor_dialog: Optional[Any] = None  # Referência ao diálogo aberto
        self._opening_editor: bool = False  # Flag reentrante: bloqueia durante criação

        # FASE 3.4: Modo pick (para integração com ANVISA)
        self._pick_mode: bool = pick_mode
        self._on_cliente_selected: Optional[Any] = on_cliente_selected

        # ViewModel com dados reais (mesmo usado pelo legacy)
        self._vm = ClientesViewModel(order_choices=ORDER_CHOICES, default_order_label=DEFAULT_ORDER_LABEL)

        # Estado de controles
        self._search_debounce_job: Optional[str] = None
        self._load_job: Optional[str] = None
        self._load_gen: int = 0  # Geração de load p/ descartar resultados obsoletos
        self._row_data_map: dict[str, ClienteRow] = {}  # iid -> ClienteRow

        self._build_ui()
        self._setup_theme_integration()

        # FASE 3.8: Atalhos de teclado
        self._setup_keyboard_shortcuts()

        # Carregar dados reais (assíncrono)
        self.after(100, self._initial_load)

        log.info("✅ [Clientes] Frame inicializado")

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
        self.toolbar.pack(side="top", fill="x", padx=10, pady=(0, 5))
        # Forçar aplicação do tema ANTES de renderizar (evita flash branco no entry)
        self.toolbar.refresh_theme()

        # Container da lista (centro) - usar SURFACE_DARK para consistência com editor
        list_container = ctk.CTkFrame(self, fg_color=SURFACE_DARK, corner_radius=10, border_width=0)
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
                on_delete=self._on_delete_client,
                on_restore=self._on_restore_client,
            )
            self.actionbar.pack(side="bottom", fill="x", padx=10, pady=(5, 10))

    def _create_treeview(self, parent: tk.Misc) -> None:
        """Cria Treeview com configuração completa de tema.

        TAREFA 3: ttk.Treeview com background E fieldbackground configurados.
        FASE 5: Migrado para CTkTreeviewContainer.
        """
        # Colunas do Treeview
        # FASE C: Adicionar colunas observacoes e ultima_alteracao
        columns = ("id", "razao_social", "cnpj", "nome", "whatsapp", "status", "observacoes", "ultima_alteracao")

        # FASE 5: Usar CTkTreeviewContainer (substitui criação manual de Treeview + Scrollbar)
        self._tree_container = CTkTreeviewContainer(
            parent,
            columns=columns,
            show="headings",
            selectmode="browse",
            rowheight=24,
            zebra=True,
            style_name="RC.Treeview",
            fg_color="transparent",  # Transparente para não sobrepor o fundo do list_container
            show_hscroll=False,  # Não mostrar scrollbar horizontal (tabela já é responsiva)
            tree_padx=0,  # Sem padding extra: colunas encostam nas bordas (simetria com ID)
        )
        self._tree_container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Obter referência ao Treeview interno (preserva API existente)
        self.tree = self._tree_container.get_treeview()

        # Obter cores do tema (CTkTreeviewContainer já registrou no manager)
        self._tree_colors = self._tree_container.get_colors()

        # Calcular largura ideal para coluna ultima_alteracao com base na fonte real
        ultima_alt_width = self._calculate_ultima_alteracao_width()

        # Specs de colunas para layout responsívo
        # Estrutura: (base_width, min_width, stretch, weight)
        # IMPORTANTE: razao_social com prioridade máxima, observacoes compacta
        # ATUALIZADO: Nome e WhatsApp reduzidos, Observações aumentadas para melhor distribuição
        self._column_specs = {
            "id": (70, 60, False, 0),
            "razao_social": (520, 340, True, 0.80),  # Coluna FLEX principal (80% do espaço) - prioridade máxima
            "cnpj": (190, 170, False, 0),
            "nome": (220, 165, True, 0.20),  # Coluna FLEX secundária (20% do espaço) - reduzida
            "whatsapp": (150, 135, False, 0),  # Reduzida para dar espaço a Observações
            "status": (210, 180, False, 0),
            "observacoes": (135, 110, False, 0),  # Coluna FIXA aumentada para melhor visualização
            "ultima_alteracao": (
                ultima_alt_width,
                max(ultima_alt_width - 10, 180),
                False,
                0,
            ),  # Calculada com respiro, min=180
        }

        # Aplicar configuração inicial das colunas
        self._apply_columns_layout()

        # Configurar grid do parent
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        # Guardar referência ao widget ttk interno
        self.tree_widget = self.tree

        # Binds para seleção e atalhos (unbind antes para evitar acúmulo)
        self.tree.unbind("<<TreeviewSelect>>")
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        # Bind para travar colunas (bloquear resize e reorder)
        # IMPORTANTE: bindar em AMBOS os eventos para bloquear completamente
        self.tree.unbind("<ButtonPress-1>", funcid=None)
        self.tree.unbind("<B1-Motion>", funcid=None)
        self.tree.bind("<ButtonPress-1>", self._on_column_lock, add="+")
        self.tree.bind("<B1-Motion>", self._on_column_lock, add="+")  # Bloqueia drag durante movimento

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

        # Bind para resize responsívo (recalcula larguras quando o tree redimensiona)
        self.tree.unbind("<Configure>", funcid=None)
        self.tree.bind("<Configure>", self._resize_columns, add="+")

        # Aplicar resize inicial após renderização
        self.after(50, self._resize_columns)

        log.info("✅ [Clientes] Treeview criada com style RC.ClientesV2.Treeview")

    def _apply_columns_layout(self) -> None:
        """Aplica configuração inicial das colunas (headings, anchor, larguras).

        Configura:
        - Headings centralizados
        - Anchor das células centralizados
        - Larguras base (width) e mínimas (minwidth)
        - Stretch (True para colunas flex, False para fixas)
        """
        # Configurar headings (todos centralizados)
        self.tree.heading("id", text="ID", anchor="center")
        self.tree.heading("razao_social", text="Razão Social", anchor="center")
        self.tree.heading("cnpj", text="CNPJ", anchor="center")
        self.tree.heading("nome", text="Nome", anchor="center")
        self.tree.heading("whatsapp", text="WhatsApp", anchor="center")
        self.tree.heading("status", text="Status", anchor="center")
        self.tree.heading("observacoes", text="Observações", anchor="center")
        self.tree.heading("ultima_alteracao", text="Última Alteração", anchor="center")  # Centralizado como ID

        # Configurar colunas usando specs (todas centralizadas para respiro visual)
        for col_id, (base_width, min_width, stretch, _) in self._column_specs.items():
            self.tree.column(
                col_id,
                width=base_width,
                minwidth=min_width,
                anchor="center",  # Todas centralizadas (respiro visual igual ao ID)
                stretch=stretch,
            )

        log.debug("[Clientes] Layout inicial das colunas aplicado")

    def _calculate_ultima_alteracao_width(self) -> int:
        """Calcula largura ideal para coluna ultima_alteracao baseada na fonte real.

        Usa o maior formato possível ("00/00/0000 - 00:00:00 (J)") + padding
        para garantir que o texto fique com respiro igual ao ID.

        Returns:
            Largura em pixels (width e minwidth serão iguais)
        """
        try:
            # Obter fonte do Treeview
            style = ttk.Style(self.tree)
            font_name = style.lookup("Treeview", "font") or "TkDefaultFont"
            font_obj = tkfont.nametofont(font_name)

            # Sample do maior formato que aparece na coluna
            sample = "00/00/0000 - 00:00:00 (J)"
            text_width = font_obj.measure(sample)

            # Adicionar padding interno (respiro dos dois lados)
            ideal_width = text_width + (2 * CELL_PAD_PX)

            log.debug(
                f"[Clientes] Calculada largura ultima_alteracao: {ideal_width}px (texto: {text_width}px + pad: {2 * CELL_PAD_PX}px)"
            )
            return ideal_width

        except Exception as e:
            log.warning(f"[Clientes] Erro ao calcular largura ultima_alteracao: {e}, usando fallback 215px")
            return 215  # Fallback

    def _resize_columns(self, event: Any = None) -> None:
        """Recalcula larguras das colunas flex baseado no espaço disponível.

        IMPORTANTE: Garante que sum(widths) <= tree_width para evitar corte de colunas.
        Algoritmo:
        1) Começa com minwidth de TODAS as colunas
        2) Calcula espaço extra disponível (tree_width - soma_minwidths)
        3) Completa colunas fixas até base_width (opcional)
        4) Distribui restante entre colunas flex por weight

        Args:
            event: Evento de Configure (opcional)
        """
        try:
            tree_width = self.tree.winfo_width()
            if tree_width <= 1:
                return  # Tree ainda não foi renderizado

            # Manter ordem das colunas como no dict (inserção)
            cols = list(self._column_specs.keys())
            specs = self._column_specs

            # 1) Começa pelos mínimos
            widths = {c: int(specs[c][1]) for c in cols}  # min_width
            total_min = sum(widths.values())

            # Se nem os mínimos cabem, aplica mínimos e deixa o Treeview clipar
            if tree_width <= total_min:
                for c in cols:
                    base_w, min_w, stretch, _ = specs[c]
                    self.tree.column(c, width=widths[c], minwidth=min_w, stretch=stretch, anchor="center")
                log.debug(f"[Clientes] Largura insuficiente: tree={tree_width}px < min={total_min}px")
                return

            extra = tree_width - total_min

            # 2) Opcional: completar colunas fixas até base_width
            fixed_cols = [c for c in cols if not specs[c][2]]  # stretch=False
            for c in fixed_cols:
                base_w, _, _, _ = specs[c]
                need = max(0, int(base_w) - widths[c])
                add = min(extra, need)
                widths[c] += add
                extra -= add
                if extra <= 0:
                    break

            # 3) Distribuir restante nas colunas flex por weight
            flex_cols = [c for c in cols if specs[c][2]]  # stretch=True
            if flex_cols and extra > 0:
                total_weight = sum(float(specs[c][3]) for c in flex_cols) or float(len(flex_cols))
                remaining = extra
                for i, c in enumerate(flex_cols):
                    w = float(specs[c][3]) or 1.0
                    if i == len(flex_cols) - 1:
                        # Joga o resto na última para fechar certinho
                        add = remaining
                    else:
                        add = int(extra * (w / total_weight))
                        add = min(add, remaining)
                    widths[c] += add
                    remaining -= add

            # 4) Aplicar widths finais
            for c in cols:
                base_w, min_w, stretch, _ = specs[c]
                self.tree.column(c, width=widths[c], minwidth=min_w, stretch=stretch, anchor="center")

            log.debug(f"[Clientes] Colunas redimensionadas: tree={tree_width}px, total={sum(widths.values())}px")

        except Exception as e:
            log.error(f"[Clientes] Erro ao redimensionar colunas: {e}", exc_info=True)

    def _sync_tree_theme_and_zebra(self) -> None:
        """Reaplica tema do ttk + zebra usando o modo ATUAL.
        Evita tree branca no Dark ao alternar Lixeira/Ativos e mantém listras.
        """
        if not self.tree_widget:
            return

        try:
            mode = ctk.get_appearance_mode()  # "Dark" / "Light"
        except Exception:
            mode = "Light"

        # Import local para evitar circular
        from src.ui.ttk_treeview_manager import get_treeview_manager

        manager = get_treeview_manager()

        # Reaplica o style e pega as cores corretas do modo atual
        colors = manager.apply_to(
            tree=self.tree_widget,
            master=self.tree_widget.master,  # precisa ser o mesmo "master" do ttk.Style
            style_name="RC.Treeview",
            mode=mode,
            zebra=False,
        )

        # Zebra precisa ser aplicado após inserir/atualizar itens
        apply_zebra(self.tree_widget, colors)

        # Seleção agora é aplicada automaticamente via TtkTreeviewManager bind
        # (não precisa chamar apply_selected_tag manualmente)

        # Atualiza cache pra qualquer uso legado
        self._tree_colors = colors

    def force_redraw(self) -> None:
        """Força redraw leve da Treeview (sem recarregar dados).

        FASE 3.3: Chamado no restore da janela para eliminar tela preta.
        Apenas reaplicar style + zebra, sem I/O.
        """
        if not self.tree_widget:
            return

        # Usar helper que detecta modo atual e reaplica tudo
        self._sync_tree_theme_and_zebra()

        # Forçar update
        self.tree_widget.update_idletasks()

        log.debug("[Clientes] force_redraw() completo")

    @staticmethod
    def _one_line(text: str | None) -> str:
        """Sanitiza texto para garantir que aparece em uma única linha.

        Remove caracteres \r, \n e múltiplos espaços, garantindo que o texto
        não quebre em várias linhas na Treeview.

        Args:
            text: Texto a ser sanitizado

        Returns:
            Texto em uma única linha
        """
        if not text:
            return ""
        # Substituir \r e \n por espaço, depois remover múltiplos espaços
        return " ".join(str(text).replace("\r", " ").replace("\n", " ").split())

    @staticmethod
    def _first_line_preview(text: str | None, max_len: int = 40) -> str:
        """Extrai primeira linha do texto para preview na TreeView.

        Mostra apenas a primeira linha, adicionando "…" se houver mais conteúdo
        ou se o texto exceder max_len caracteres.

        Args:
            text: Texto completo (pode ter múltiplas linhas)
            max_len: Comprimento máximo antes de truncar

        Returns:
            Primeira linha truncada com "…" se necessário
        """
        if not text:
            return ""

        # Normalizar quebras de linha
        normalized = str(text).replace("\r\n", "\n").replace("\r", "\n")

        # Separar em linhas
        lines = normalized.split("\n")

        # Pegar primeira linha (strip para remover espaços)
        first_line = lines[0].strip() if lines else ""

        # Verificar se há mais conteúdo além da primeira linha
        has_more_lines = len(lines) > 1 and any(line.strip() for line in lines[1:])

        # Truncar se necessário
        if len(first_line) > max_len:
            # Truncar e adicionar "…"
            return first_line[: max_len - 1].rstrip() + "…"
        elif has_more_lines:
            # Tem mais linhas, adicionar "…"
            return first_line + "…" if first_line else ""
        else:
            # Apenas uma linha, sem truncamento
            return first_line

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
                    log.debug(f"[Clientes] Cliente selecionado: ID={self._selected_client_id}")

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

            # Seleção visível agora é aplicada automaticamente via TtkTreeviewManager bind
            # (não precisa chamar apply_selected_tag manualmente)

        except Exception as e:
            log.error(f"[Clientes] Erro no handler de seleção: {e}", exc_info=True)
            self._selected_client_id = None

    def _get_selected_values(self) -> tuple | None:
        """Retorna os valores da linha selecionada, compatível com a interface legada.

        Returns:
            Tupla onde [0] = client_id (str), [1] = razao_social, demais colunas
            conforme a Treeview; ou None se nenhum cliente estiver selecionado.
        """
        if not self._selected_client_id:
            return None
        # Primeira escolha: valores direto da Treeview (exato para _excluir_cliente)
        try:
            if hasattr(self, "tree") and self.tree:
                selection = self.tree.selection()
                if selection:
                    values = self.tree.item(selection[0], "values")
                    if values:
                        return tuple(values)
        except Exception:
            pass
        # Fallback: reconstruir a partir de _row_data_map
        for row in self._row_data_map.values():
            try:
                if int(row.id) == self._selected_client_id:
                    return (str(self._selected_client_id), row.razao_social or "")
            except (ValueError, TypeError):
                continue
        # ID conhecido mas fora do mapa (ex.: linha ainda carregando)
        return (str(self._selected_client_id),)

    def _on_column_lock(self, event: Any) -> str | None:
        """Handler para bloquear resize e reorder de colunas.

        Args:
            event: Evento de clique do mouse

        Returns:
            "break" se bloqueou a ação, None caso contrário
        """
        try:
            region = self.tree.identify_region(event.x, event.y)

            # Bloquear resize (separador entre colunas)
            if region == "separator":
                return "break"

            # Bloquear clique no heading (impede reordenação e clique)
            if region == "heading":
                return "break"

            # Permitir outras ações (seleção de linha, clique em célula)
            return None

        except Exception as e:
            log.error(f"[Clientes] Erro no handler de bloqueio de coluna: {e}", exc_info=True)
            return None

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

            make_btn(
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

            make_btn(
                container,
                text=" Enviar documentos",
                command=lambda: [menu.destroy(), self._on_enviar_documentos()],
                width=btn_width,
                height=btn_height,
                fg_color="transparent",
                hover_color=BORDER,
                text_color=TEXT_PRIMARY,
                anchor="w",
            ).pack(padx=4, pady=2)

            delete_text = "🗑️ Excluir definitivamente" if self._trash_mode else "🗑️ Enviar para Lixeira"
            make_btn(
                container,
                text=delete_text,
                command=lambda: [menu.destroy(), self._on_delete_client()],
                width=btn_width,
                height=btn_height,
                fg_color="transparent",
                hover_color=BORDER,
                text_color=TEXT_PRIMARY,
                anchor="w",
            ).pack(padx=4, pady=(2, 4 if not self._trash_mode else 2))

            # Botão Restaurar (somente em modo LIXEIRA)
            if self._trash_mode:
                make_btn(
                    container,
                    text="♻️ Restaurar",
                    command=lambda: [menu.destroy(), self._on_restore_client()],
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
            log.error(f"[Clientes] Erro ao abrir context menu: {e}", exc_info=True)

    def _setup_theme_integration(self) -> None:
        """Integra com sistema de temas global.

        FASE B: Usa APENAS AppearanceModeTracker (elimina duplicidade).
        FIX: Callback compatível com versões que passam mode como parâmetro.
        """
        self._last_applied_mode = None  # Guard para evitar double apply

        try:
            # AppearanceModeTracker do CustomTkinter (ÚNICA fonte de verdade)
            AppearanceModeTracker = ctk.AppearanceModeTracker  # type: ignore[attr-defined]  # noqa: N806

            def on_appearance_change(mode: str | None = None) -> None:
                """Callback do AppearanceModeTracker.

                Compatível com versões antigas (sem parâmetro) e novas (com mode).
                """
                new_mode = mode or ctk.get_appearance_mode()
                self._on_theme_changed(new_mode)

            AppearanceModeTracker.add(on_appearance_change, self)
            log.debug("[Clientes] AppearanceModeTracker registrado")

            # Aplicar tema inicial imediatamente (importante se já está em Dark ao abrir)
            initial_mode = ctk.get_appearance_mode()
            self._on_theme_changed(initial_mode)
            log.debug(f"[Clientes] Tema inicial aplicado: {initial_mode}")
        except Exception as exc:
            log.warning(f"[Clientes] Falha ao registrar AppearanceModeTracker: {exc}")

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

            # BUGFIX: Chamar _sync_tree_theme_and_zebra() para obter cores atualizadas
            # do novo tema, em vez de usar cache antigo (_tree_colors)
            if self.tree_widget:
                self._sync_tree_theme_and_zebra()

            # Atualizar toolbar e actionbar
            if hasattr(self, "toolbar") and self.toolbar:
                self.toolbar.refresh_theme()

            if hasattr(self, "actionbar") and self.actionbar:
                self.actionbar.refresh_theme()

            self.update_idletasks()

        except Exception:
            log.exception("[Clientes] Erro ao processar mudança de tema")

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

        log.info(f"✅ [Clientes] {len(sample_data)} registros de exemplo carregados")

    def _initial_load(self) -> None:
        """Carga inicial de dados reais."""
        log.info("[Clientes] Iniciando carga de dados reais...")
        try:
            self._vm.refresh_from_service()
            self._render_rows()
            log.info(f"[Clientes] Dados carregados: {len(self._vm.get_rows())} clientes")

            # Atualizar lista de status do toolbar com dados do ViewModel
            self.after(500, self._update_toolbar_status_list)
        except Exception as e:
            log.error(f"[Clientes] Erro ao carregar dados: {e}", exc_info=True)

    def carregar(self) -> None:
        """Recarrega a lista respeitando filtros e modo (lixeira/ativo) atuais."""
        search_text = self.toolbar.get_search_text()
        order_label = self.toolbar.get_order()
        status = self.toolbar.get_status()
        self.load_async(
            search=search_text,
            order_label=order_label,
            status=status,
            show_trash=self._trash_mode,
        )

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
        """Carrega dados com filtros aplicados (assíncrono via thread).

        O fetch de dados roda em background thread para não congelar a UI.
        Somente a renderização roda na main thread (via self.after).

        Args:
            search: Texto de busca
            order_label: Label de ordenação (ORDER_CHOICES)
            status: Filtro de status
            show_trash: Se True, mostra apenas lixeira; se False, mostra clientes ativos
        """
        # Cancelar job pendente (after timer)
        if self._load_job:
            try:
                self.after_cancel(self._load_job)
            except Exception:
                pass
            self._load_job = None

        # Incrementar geração — descarta resultados de loads anteriores
        self._load_gen += 1
        gen = self._load_gen

        def _fetch_data() -> None:
            """Busca dados em background thread."""
            t0 = time.perf_counter()
            mode = "LIXEIRA" if show_trash else "ATIVOS"
            log.debug(f"[Clientes] fetch_start mode={mode} gen={gen}")
            try:
                if show_trash:
                    from src.modules.clientes.core import service as clientes_service
                    from src.modules.clientes.core.viewmodel import ClienteRow as _Row

                    order_by, descending = self._map_order_label_to_params(order_label)
                    deleted_clients = clientes_service.listar_clientes_na_lixeira(
                        order_by=order_by, descending=descending
                    )
                    t_fetch = time.perf_counter()
                    log.debug(f"[Clientes] fetch_end rows={len(deleted_clients)} elapsed={t_fetch - t0:.3f}s")

                    # Pipeline idêntico ao modo ATIVOS:
                    # _build_row_from_cliente usa normalize_br_whatsapp, fmt_datetime_br,
                    # format_cnpj e extract_status_and_observacoes — exatamente como a treeview normal.
                    rows: list[_Row] = []
                    for client in deleted_clients:
                        row = self._vm._build_row_from_cliente(client)
                        # Se obs não tinha prefixo [status], marcar como lixeira
                        if not row.status:
                            row.status = "[LIXEIRA]"
                        rows.append(row)

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

                    if status:
                        status_norm = status.strip().lower()
                        rows = [r for r in rows if r.status.strip().lower() == status_norm]

                    # Agendar render na main thread (só se geração ainda é válida)
                    if gen == self._load_gen:
                        self.after(0, lambda: self._finish_load_trash(gen, rows, search, status))
                else:
                    # Modo normal: refresh + rebuild no ViewModel
                    self._vm.refresh_from_service()
                    t_fetch = time.perf_counter()
                    log.debug(f"[Clientes] fetch_end elapsed={t_fetch - t0:.3f}s")
                    self._vm.set_search_text(search if search else None, rebuild=False)
                    self._vm.set_status_filter(status if status else None, rebuild=False)
                    if order_label:
                        self._vm.set_order_label(order_label, rebuild=False)
                    self._vm._rebuild_rows()

                    if gen == self._load_gen:
                        self.after(0, lambda: self._finish_load_normal(gen, search, status))

            except Exception as e:
                log.error(f"[Clientes] Erro ao carregar dados: {e}", exc_info=True)
                if gen == self._load_gen:
                    self.after(0, self._re_enable_trash_btn)

        # Disparar em background thread
        t = threading.Thread(target=_fetch_data, daemon=True, name="clientes-load")
        t.start()

    # ── Callbacks de render (rodam na main thread) ────────────────

    def _re_enable_trash_btn(self) -> None:
        """Reabilita o botão lixeira após término do load."""
        try:
            if hasattr(self, "toolbar") and self.toolbar and hasattr(self.toolbar, "trash_btn"):
                self.toolbar.trash_btn.configure(state="normal")
        except Exception:
            pass

    def _finish_load_trash(self, gen: int, rows: list, search: str, status: str) -> None:
        """Renderiza resultado da lixeira na main thread."""
        if gen != self._load_gen:
            self._re_enable_trash_btn()
            return  # Resultado obsoleto
        t0 = time.perf_counter()
        self._render_rows_from_list(rows)
        log.debug(
            f"[Clientes] render_end LIXEIRA rows={len(rows)} elapsed={time.perf_counter() - t0:.3f}s "
            f"(busca='{search}', status='{status}')"
        )
        self._re_enable_trash_btn()

    def _finish_load_normal(self, gen: int, search: str, status: str) -> None:
        """Renderiza resultado normal na main thread."""
        if gen != self._load_gen:
            self._re_enable_trash_btn()
            return  # Resultado obsoleto
        t0 = time.perf_counter()
        self._render_rows()
        log.debug(
            f"[Clientes] render_end ATIVOS rows={len(self._vm.get_rows())} elapsed={time.perf_counter() - t0:.3f}s "
            f"(busca='{search}', status='{status}')"
        )
        self._re_enable_trash_btn()

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

            # Sanitizar textos para evitar quebras de linha
            razao_social = self._one_line(row.razao_social)
            nome = self._one_line(row.nome)
            # AJUSTE 2: Mostrar apenas primeira linha das observações
            observacoes = self._first_line_preview(row.observacoes)

            iid = self.tree_widget.insert(
                "",
                "end",
                values=(
                    row.id,
                    razao_social,
                    _fmt_cnpj(row.cnpj) or row.cnpj,
                    nome,
                    _fmt_whatsapp(row.whatsapp) or row.whatsapp,
                    row.status,
                    observacoes or "",  # FASE C: Observações (primeira linha)
                    ultima_alt_str,  # FASE C: Última alteração formatada
                ),
            )
            self._row_data_map[iid] = row

        # ANTI-FLASH: Reaplicar style + zebra com cores do modo ATUAL
        # (evita ficar branco se self._tree_colors foi cached do Light)
        self._sync_tree_theme_and_zebra()

        log.debug(f"[Clientes] Renderizados {len(rows)} clientes")

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

            # Sanitizar textos para evitar quebras de linha
            razao_social = self._one_line(row.razao_social)
            nome = self._one_line(row.nome)
            # AJUSTE 2: Mostrar apenas primeira linha das observações
            observacoes = self._first_line_preview(row.observacoes)

            iid = self.tree_widget.insert(
                "",
                "end",
                values=(
                    row.id,
                    razao_social,
                    _fmt_cnpj(row.cnpj) or row.cnpj,
                    nome,
                    _fmt_whatsapp(row.whatsapp) or row.whatsapp,
                    row.status,
                    observacoes or "",
                    ultima_alt_str,
                ),
            )
            self._row_data_map[iid] = row

        # ANTI-FLASH: Reaplicar style + zebra com cores do modo ATUAL
        # (evita ficar branco se self._tree_colors foi cached do Light)
        self._sync_tree_theme_and_zebra()

        log.debug(f"[Clientes] Renderizados {len(rows)} itens (modo customizado)")

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
            log.debug(f"[Clientes] Erro ao formatar data '{dt_str}': {e}")
            return dt_str

    # Callbacks (implementados com dados reais)
    def _on_search(self, text: str) -> None:
        """Handler para botão Buscar."""
        search_text = self.toolbar.get_search_text()
        order_label = self.toolbar.get_order()
        status = self.toolbar.get_status()
        log.debug(f"[Clientes] Buscar: '{search_text}'")
        self.load_async(search=search_text, order_label=order_label, status=status)

    def _on_clear_search(self) -> None:
        """Handler para botão Limpar busca."""
        log.debug("[Clientes] Limpar busca")
        self.toolbar.clear_search()
        self.load_async()

    def _on_order_changed(self, order: str) -> None:
        """Handler para mudança de ordenação."""
        # Normalizar order label para garantir compatibilidade
        from src.modules.clientes.core.ui_helpers import normalize_order_label

        normalized_order = normalize_order_label(order)

        log.debug(f"[Clientes] Ordenação alterada: {order} -> normalizado: {normalized_order}")
        search_text = self.toolbar.get_search_text()
        status = self.toolbar.get_status()
        self.load_async(search=search_text, order_label=normalized_order, status=status)

    def _on_status_changed(self, status: str) -> None:
        """Handler para mudança de filtro de status.

        IMPORTANTE: Sempre usa self.toolbar.get_status() que converte 'Todos' -> ''.
        Não use o argumento 'status' diretamente pois ele vem do callback antes da conversão.
        """
        # CRITICAL: usar get_status() para converter "Todos" -> ""
        status_filter = self.toolbar.get_status()
        log.info(f"[Clientes] Status alterado: {status} -> filtro: '{status_filter}'")
        search_text = self.toolbar.get_search_text()
        order_label = self.toolbar.get_order()
        self.load_async(search=search_text, order_label=order_label, status=status_filter)

    def _on_export(self) -> None:
        """Handler para exportação de dados (FASE 3.5).

        Abre diálogo para escolher formato (CSV/XLSX) e local de salvamento.
        Exporta dados visíveis/filtrados da tree usando src/modules/clientes/export.py
        """
        from tkinter import filedialog
        from pathlib import Path
        from src.modules.clientes.core import export

        try:
            # Verificar se há dados para exportar
            if not self._row_data_map:
                _show_info(
                    self.winfo_toplevel(),  # type: ignore[attr-defined]
                    "Exportação",
                    "Nenhum dado disponível para exportar.",
                )
                return

            # Obter dados visíveis na tree (respeitando filtros)
            rows_to_export = list(self._row_data_map.values())

            if not rows_to_export:
                _show_info(
                    self.winfo_toplevel(),  # type: ignore[attr-defined]
                    "Exportação",
                    "Nenhum cliente para exportar.",
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
                log.debug("[Clientes] Exportação cancelada pelo usuário")
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
            _show_info(
                self.winfo_toplevel(),  # type: ignore[attr-defined]
                "Sucesso",
                f"Dados exportados com sucesso!\n\n"
                f"Arquivo: {filepath_obj.name}\n"
                f"Formato: {format_name}\n"
                f"Clientes: {len(rows_to_export)}",
            )

            log.info(f"[Clientes] Exportados {len(rows_to_export)} clientes para {filepath_obj}")

        except ImportError as e:
            log.error(f"[Clientes] Erro de importação ao exportar: {e}")
            _show_error(
                self.winfo_toplevel(),  # type: ignore[attr-defined]
                "Erro",
                f"Biblioteca necessária não está disponível:\n{e}",
            )
        except Exception as e:
            log.error(f"[Clientes] Erro ao exportar: {e}", exc_info=True)
            _show_error(
                self.winfo_toplevel(),  # type: ignore[attr-defined]
                "Erro",
                f"Erro ao exportar dados:\n{e}",
            )

    def _update_toolbar_status_list(self) -> None:
        """Atualiza lista de status do toolbar com dados do ViewModel."""
        try:
            extra_statuses = self._vm.get_status_choices()
            self.toolbar.update_status_values(extra_statuses)
            log.debug(f"[Clientes] Lista de status atualizada: {len(extra_statuses)} extras do ViewModel")
        except Exception as e:
            log.debug(f"[Clientes] Erro ao atualizar lista de status: {e}")

    def _on_toggle_trash(self) -> None:
        """Handler para botão Lixeira - alterna entre clientes ativos e lixeira."""
        self._trash_mode = not self._trash_mode

        # IMPORTANTE: Ao entrar na lixeira, resetar filtro de status para "Todos"
        # porque status de lixeira são diferentes dos status de clientes ativos
        if self._trash_mode:
            self.toolbar.status_var.set("Todos")
            log.debug("[Clientes] Entrando no modo LIXEIRA - status resetado para 'Todos'")

        mode_str = "LIXEIRA" if self._trash_mode else "ATIVOS"
        log.info(f"[Clientes] Modo alterado: {mode_str}")

        # Atualizar label do botão na toolbar
        if hasattr(self.toolbar, "update_trash_mode"):
            self.toolbar.update_trash_mode(self._trash_mode)

        # Atualizar label do botão Excluir na actionbar
        if hasattr(self, "actionbar") and self.actionbar:
            delete_label = "Excluir definitivamente" if self._trash_mode else "Excluir"
            self.actionbar.set_delete_label(delete_label)
            self.actionbar.set_trash_mode(self._trash_mode)

        # Desabilitar botão durante o load para evitar toggles duplos
        if hasattr(self.toolbar, "trash_btn"):
            try:
                self.toolbar.trash_btn.configure(state="disabled")
            except Exception:
                pass

        # Recarregar com filtro de lixeira
        t_toggle = time.perf_counter()
        log.debug(f"[Clientes] toggle_start mode={'LIXEIRA' if self._trash_mode else 'ATIVOS'} t={t_toggle:.3f}")
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

        log.info("✅ [Clientes] Atalhos de teclado configurados (F5, Ctrl+N, Ctrl+E, Delete)")

    def _on_reload_shortcut(self, event: Any = None) -> str:
        """Handler para atalho F5 (recarregar lista).

        Args:
            event: Evento de teclado (opcional)

        Returns:
            'break' para evitar propagação do evento
        """
        log.info("[Clientes] F5 pressionado - recarregando lista")
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
            log.error("[Clientes] App não disponível para novo cliente")
            _show_error(
                self.winfo_toplevel(),  # type: ignore[attr-defined]
                "Erro",
                "Não foi possível acessar o controlador do aplicativo.\nTente recarregar o módulo.",
            )
            return "break" if event else None

        log.info("[Clientes] Novo cliente - abrindo diálogo")

        try:
            from src.modules.clientes.ui.views.client_editor_dialog import ClientEditorDialog

            def on_saved(data: dict) -> None:
                """Callback após salvar."""
                log.info(f"[Clientes] Cliente criado: {data.get('Razão Social')}")
                self.load_async()

            # Abrir diálogo modal
            dialog = ClientEditorDialog(
                parent=self.winfo_toplevel(),  # type: ignore[attr-defined]
                client_id=None,
                on_save=on_saved,
            )
            dialog.focus()  # type: ignore[attr-defined]

        except Exception as e:
            log.error(f"[Clientes] Erro ao abrir diálogo de novo cliente: {e}", exc_info=True)

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
                log.debug(f"[Clientes] Duplo clique: cliente ID={self._selected_client_id}")

            # Abrir editor (centralizado)
            self._open_client_editor(source="doubleclick")

        except Exception as e:
            log.error(f"[Clientes] Erro no duplo clique: {e}", exc_info=True)

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

        log.info(f"[Clientes:{session_id}] Solicitação de abertura do editor (source={source})")

        # GUARD 1: Se já estamos criando um editor, ignorar
        if self._opening_editor:
            log.debug(f"[Clientes:{session_id}] Abertura bloqueada: já criando editor")
            return

        # GUARD 2: Se diálogo já existe e está visível, apenas dar foco
        if self._editor_dialog is not None:
            try:
                if self._editor_dialog.winfo_exists():
                    log.info(f"[Clientes:{session_id}] Diálogo já aberto, dando foco")
                    self._editor_dialog.lift()
                    self._editor_dialog.focus_force()
                    return
            except Exception:
                # Diálogo foi destruído mas referência não foi limpa
                log.debug(f"[Clientes:{session_id}] Referência obsoleta, limpando")
                self._editor_dialog = None

        # Validações
        if not self.app:
            log.error(f"[Clientes:{session_id}] App não disponível")
            _show_error(
                self.winfo_toplevel(),  # type: ignore[attr-defined]
                "Erro",
                "Não foi possível acessar o controlador do aplicativo.\nTente recarregar o módulo.",
            )
            return

        if not self._selected_client_id:
            log.warning(f"[Clientes:{session_id}] Nenhum cliente selecionado")
            _show_warning(
                self.winfo_toplevel(),  # type: ignore[attr-defined]
                "Atenção",
                "Selecione um cliente para editar.",
            )
            return

        # Ativar flag de reentrância
        self._opening_editor = True
        log.info(f"[Clientes:{session_id}] Criando editor para cliente ID={self._selected_client_id}")

        try:
            from src.modules.clientes.ui.views.client_editor_dialog import ClientEditorDialog

            def on_saved(data: dict) -> None:
                """Callback após salvar."""
                log.info(f"[Clientes:{session_id}] Cliente {self._selected_client_id} salvo")
                self.load_async()

            def on_closed() -> None:
                """Callback quando diálogo é fechado."""
                log.info(f"[Clientes:{session_id}] Diálogo fechado, limpando referências")
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
            log.info(f"[Clientes:{session_id}] Editor criado com sucesso")

        except Exception as e:
            log.error(f"[Clientes:{session_id}] Erro ao criar editor: {e}", exc_info=True)
            self._editor_dialog = None
            self._opening_editor = False

    def _on_enviar_documentos(self) -> None:
        """Handler para enviar documentos do cliente (via context menu).

        Abre o dialog de editor com foco no botão de upload.
        """
        if not self._selected_client_id:
            _show_warning(
                self.winfo_toplevel(),  # type: ignore[attr-defined]
                "Atenção",
                "Selecione um cliente para enviar documentos.",
            )
            return

        log.info(f"[Clientes] Enviar documentos para cliente ID={self._selected_client_id}")

        try:
            from src.modules.clientes.ui.views.client_editor_dialog import ClientEditorDialog

            def on_saved(data: dict) -> None:
                """Callback após salvar."""
                log.info(f"[Clientes] Cliente {self._selected_client_id} atualizado após upload")
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
                    log.error(f"[Clientes] Erro ao acionar upload automaticamente: {e}")

            dialog.after(200, trigger_upload)
            dialog.focus()  # type: ignore[attr-defined]

        except Exception as e:
            log.error(f"[Clientes] Erro ao abrir diálogo para upload: {e}", exc_info=True)

    def _on_delete_client(self, event: Any = None) -> str | None:
        """Handler para botão Excluir Cliente.

        Modo ATIVOS  → soft delete (mover para lixeira).
        Modo LIXEIRA → hard delete (exclusão definitiva no banco + storage).
        Aceita event opcional para atalho Delete.

        Args:
            event: Evento de teclado (opcional)

        Returns:
            'break' se event fornecido, None caso contrário
        """
        if not self._selected_client_id:
            return "break" if event else None

        # Pegar dados do cliente selecionado
        row_data = None
        for _iid, data in self._row_data_map.items():
            if int(data.id) == self._selected_client_id:
                row_data = data
                break

        razao = row_data.razao_social if row_data else ""
        label_cli = f"{razao} (ID {self._selected_client_id})" if razao else f"ID {self._selected_client_id}"
        client_id = self._selected_client_id

        from src.modules.clientes.core import service as clientes_service
        from src.modules.lixeira import refresh_if_open as refresh_lixeira_if_open

        top = self.winfo_toplevel()

        if self._trash_mode:
            # ── MODO LIXEIRA: exclusão definitiva ──────────────────────────────
            confirm = _ask_yes_no(
                top,
                "Excluir definitivamente",
                f"Tem certeza que deseja EXCLUIR DEFINITIVAMENTE o cliente {label_cli}?\n\nEsta ação não pode ser desfeita.",
            )
            if not confirm:
                return "break" if event else None

            log.info(f"[Clientes] Hard delete: cliente ID={client_id}")
            try:
                ok, errs = clientes_service.excluir_clientes_definitivamente([client_id])
                if errs:
                    msgs = "\n".join(f"  • {e}" for _, e in errs)
                    _show_error(
                        top,
                        "Erro ao excluir",
                        f"Falha ao excluir cliente {label_cli}:\n{msgs}",
                    )
                    log.error("[Clientes] Hard delete falhou para ID=%s: %s", client_id, errs)
                    return "break" if event else None

                _show_info(
                    top,
                    "Excluído",
                    f"Cliente {label_cli} excluído definitivamente.",
                )
                log.info("[Clientes] Hard delete OK: cliente ID=%s", client_id)

                # Refresh da lista permanecendo em modo LIXEIRA
                self._selected_client_id = None
                self.carregar()

            except Exception as e:
                log.error(f"[Clientes] Erro no hard delete do cliente ID={client_id}: {e}", exc_info=True)
                _show_error(
                    top,
                    "Erro",
                    f"Erro ao excluir definitivamente: {e}",
                )
        else:
            # ── MODO ATIVOS: soft delete (mover para lixeira) ──────────────────
            confirm = _ask_yes_no(
                top,
                "Enviar para Lixeira",
                f"Deseja enviar o cliente {label_cli} para a Lixeira?",
            )
            if not confirm:
                return "break" if event else None

            log.info(f"[Clientes] Soft delete: cliente ID={client_id}")
            try:
                clientes_service.mover_cliente_para_lixeira(client_id)

                _show_info(
                    top,
                    "Lixeira",
                    f"Cliente {label_cli} movido para a Lixeira.",
                )
                log.info("[Clientes] Soft delete OK: cliente ID=%s", client_id)

                refresh_lixeira_if_open()

                # Refresh da lista permanecendo em modo ATIVOS
                self._selected_client_id = None
                self.carregar()

            except Exception as e:
                log.error(f"[Clientes] Erro ao mover cliente para lixeira ID={client_id}: {e}", exc_info=True)
                _show_error(
                    top,
                    "Erro",
                    f"Erro ao enviar cliente para lixeira: {e}",
                )

        return "break" if event else None

    def _on_restore_client(self) -> None:
        """Restaura cliente da lixeira (undo soft delete)."""
        if not self._selected_client_id or not self._trash_mode:
            return

        row_data = None
        for _iid, data in self._row_data_map.items():
            if int(data.id) == self._selected_client_id:
                row_data = data
                break

        razao = row_data.razao_social if row_data else ""
        label_cli = f"{razao} (ID {self._selected_client_id})" if razao else f"ID {self._selected_client_id}"
        client_id = self._selected_client_id

        top = self.winfo_toplevel()

        confirm = _ask_yes_no(
            top,
            "Restaurar Cliente",
            f"Deseja restaurar o cliente {label_cli} para a lista de ativos?",
        )
        if not confirm:
            return

        from src.modules.clientes.core import service as clientes_service

        log.info("[Clientes] Restaurando cliente ID=%s da lixeira", client_id)
        try:
            clientes_service.restaurar_clientes_da_lixeira([client_id])

            _show_info(
                top,
                "Restaurado",
                f"Cliente {label_cli} restaurado com sucesso.\n\nEle voltará a aparecer na lista de ativos.",
            )
            log.info("[Clientes] Restauração OK: cliente ID=%s", client_id)

            self._selected_client_id = None
            self.carregar()

        except Exception as e:
            log.error("[Clientes] Erro ao restaurar cliente ID=%s: %s", client_id, e, exc_info=True)
            _show_error(
                top,
                "Erro",
                f"Erro ao restaurar cliente: {e}",
            )

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
                log.info(f"[Clientes] Abrindo WhatsApp: {url}")

                import webbrowser

                webbrowser.open(url)

        except Exception as e:
            log.error(f"[Clientes] Erro ao processar clique no WhatsApp: {e}", exc_info=True)

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
            AppearanceModeTracker = ctk.AppearanceModeTracker  # type: ignore[attr-defined]  # noqa: N806

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
        btn_select = make_btn(
            btn_container,
            text="✓ Selecionar Cliente",
            command=self._on_pick_confirm,
            height=36,
            font=("Segoe UI", 13, "bold"),
            fg_color="#28a745",
            hover_color="#218838",
        )
        btn_select.pack(side="left", padx=5)

        # Botão Cancelar (cinza)
        btn_cancel = make_btn(
            btn_container,
            text="✕ Cancelar",
            command=self._on_pick_cancel,
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
            _show_warning(
                self.winfo_toplevel(),  # type: ignore[attr-defined]
                "Atenção",
                "Selecione um cliente primeiro.",
            )
            return

        # Obter dados do cliente via _row_data_map
        iid = selection[0]
        client_row = self._row_data_map.get(iid)

        if not client_row:
            log.warning(f"[Clientes][Pick] Cliente {iid} não encontrado no mapa")
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

        log.info(f"[Clientes][Pick] Cliente selecionado: {client_data['razao_social']} (ID: {client_data['id']})")

        # Chamar callback se fornecido
        if self._on_cliente_selected:
            try:
                self._on_cliente_selected(client_data)
            except Exception as e:
                log.error(f"[Clientes][Pick] Erro no callback: {e}", exc_info=True)

    def _on_pick_cancel(self) -> None:
        """Cancela seleção no pick_mode (não chama callback)."""
        if not self._pick_mode:
            return

        log.info("[Clientes][Pick] Seleção cancelada pelo usuário")
