"""View do painel de Quick Actions (módulos) do Hub.

Extraído de HubScreen na MF-25 para reduzir o tamanho do monolito.
Este módulo é responsável APENAS pela construção visual do painel lateral
esquerdo com os botões de acesso rápido aos módulos.
"""

from typing import Any, Callable, Optional
import tkinter as tk

from src.ui.ctk_config import ctk, HAS_CUSTOMTKINTER
from src.ui.ui_tokens import APP_BG, SURFACE_DARK, TITLE_FONT, CARD_RADIUS, TEXT_PRIMARY


class HubQuickActionsView:
    """View do painel de Quick Actions / Módulos do Hub.

    Responsabilidades:
    - Criar o frame visual do painel de módulos
    - Criar botões de acesso rápido aos módulos
    - Conectar cada botão à callback apropriada

    Esta classe NÃO conhece HubScreen diretamente, apenas recebe:
    - parent: widget pai onde o painel será anexado
    - callbacks: funções a serem chamadas quando botões são clicados
    """

    def __init__(
        self,
        parent: Any,  # tk.Widget ou tk.Frame
        *,
        on_open_clientes: Optional[Callable[[], None]] = None,
        on_open_cashflow: Optional[Callable[[], None]] = None,
        on_open_anvisa: Optional[Callable[[], None]] = None,
        on_open_farmacia_popular: Optional[Callable[[], None]] = None,
        on_open_sngpc: Optional[Callable[[], None]] = None,
        on_open_mod_sifap: Optional[Callable[[], None]] = None,
    ):
        """Inicializa a view do painel de Quick Actions.

        Args:
            parent: Widget pai (onde o painel será criado)
            on_open_clientes: Callback para abrir módulo Clientes
            on_open_cashflow: Callback para abrir módulo Fluxo de Caixa
            on_open_anvisa: Callback para abrir módulo Anvisa
            on_open_farmacia_popular: Callback para abrir módulo Farmácia Popular
            on_open_sngpc: Callback para abrir módulo Sngpc
            on_open_mod_sifap: Callback para abrir módulo Sifap
        """
        self._parent = parent
        self._on_open_clientes = on_open_clientes
        self._on_open_cashflow = on_open_cashflow
        self._on_open_anvisa = on_open_anvisa
        self._on_open_farmacia_popular = on_open_farmacia_popular
        self._on_open_sngpc = on_open_sngpc
        self._on_open_mod_sifap = on_open_mod_sifap

        self.modules_panel: Optional[tk.LabelFrame] = None

    def build(self) -> tk.LabelFrame:
        """Constrói e retorna o frame do painel de Quick Actions.

        Este método cria toda a estrutura visual do painel:
        - Frame principal (Labelframe com título)
        - 3 blocos de botões: Cadastros/Acesso, Gestão/Auditoria, Regulatório/Programas
        - Botões individuais com suas callbacks

        Returns:
            O frame principal do painel de Quick Actions (pronto para ser anexado ao layout)
        """
        from src.modules.hub.constants import (
            MODULES_TITLE,
            PAD_OUTER,
        )

        # Helper para criar botão compatível CTk/Tk com estilo
        def mk_btn(parent, text, command=None):
            if HAS_CUSTOMTKINTER and ctk is not None:
                return ctk.CTkButton(
                    parent,
                    text=text,
                    command=command,
                    fg_color=("#3b82f6", "#2563eb"),
                    hover_color=("#2563eb", "#1d4ed8"),
                    text_color="#ffffff",
                    corner_radius=6,
                    height=32,
                )
            else:
                return tk.Button(parent, text=text, command=command)

        # Painel principal - MICROFASE 35: fundo cinza escuro sem borda
        if HAS_CUSTOMTKINTER and ctk is not None:
            self.modules_panel = ctk.CTkFrame(
                self._parent,
                fg_color=SURFACE_DARK,
                bg_color=APP_BG,  # MICROFASE 35: evita vazamento nos cantos
                border_width=0,
                corner_radius=CARD_RADIUS,
            )
        else:
            self.modules_panel = ctk.CTkFrame(self._parent)

        # Container interno com title - fonte maior
        title_label = ctk.CTkLabel(
            self.modules_panel,
            text=MODULES_TITLE,
            font=TITLE_FONT,
            text_color=TEXT_PRIMARY,
        )
        title_label.pack(fill="x", padx=PAD_OUTER, pady=(PAD_OUTER, 4))

        # Container de conteúdo com padding
        content_container = ctk.CTkFrame(self.modules_panel, fg_color="transparent")
        content_container.pack(fill="both", expand=True, padx=PAD_OUTER, pady=(0, PAD_OUTER))

        # BLOCO 1: Cadastros / Acesso
        # Título da seção
        lbl_cadastros = ctk.CTkLabel(
            content_container,
            text="Cadastros / Acesso",
            font=("Arial", 12, "bold"),
            text_color=("#374151", "#d1d5db"),
        )
        lbl_cadastros.pack(fill="x", pady=(8, 2))

        # Frame de conteúdo - transparente para manter fundo do painel
        frame_cadastros = ctk.CTkFrame(content_container, fg_color="transparent")
        frame_cadastros.pack(fill="x", padx=8, pady=(0, 8))
        frame_cadastros.columnconfigure(0, weight=1)
        frame_cadastros.columnconfigure(1, weight=1)

        btn_clientes = mk_btn(frame_cadastros, "Clientes", self._on_open_clientes)
        btn_clientes.grid(row=0, column=0, sticky="ew", padx=6, pady=6)

        # BLOCO 2: Gestão
        # Título da seção
        lbl_gestao = ctk.CTkLabel(
            content_container,
            text="Gestão",
            font=("Arial", 12, "bold"),
            text_color=("#374151", "#d1d5db"),
        )
        lbl_gestao.pack(fill="x", pady=(0, 2))

        # Frame de conteúdo - transparente para manter fundo do painel
        frame_gestao = ctk.CTkFrame(content_container, fg_color="transparent")
        frame_gestao.pack(fill="x", padx=8, pady=(0, 8))
        frame_gestao.columnconfigure(0, weight=1)

        btn_fluxo_caixa = mk_btn(frame_gestao, "Fluxo de Caixa", self._on_open_cashflow)
        btn_fluxo_caixa.grid(row=0, column=0, sticky="ew", padx=6, pady=6)

        # BLOCO 3: Regulatório / Programas
        # Título da seção
        lbl_regulatorio = ctk.CTkLabel(
            content_container,
            text="Regulatório / Programas",
            font=("Arial", 12, "bold"),
            text_color=("#374151", "#d1d5db"),
        )
        lbl_regulatorio.pack(fill="x", pady=(0, 2))

        # Frame de conteúdo - transparente para manter fundo do painel
        frame_regulatorio = ctk.CTkFrame(content_container, fg_color="transparent")
        frame_regulatorio.pack(fill="x", padx=8, pady=(0, 0))
        frame_regulatorio.columnconfigure(0, weight=1)
        frame_regulatorio.columnconfigure(1, weight=1)

        btn_anvisa = mk_btn(frame_regulatorio, "Anvisa", self._on_open_anvisa)
        btn_anvisa.grid(row=0, column=0, sticky="ew", padx=6, pady=6)

        btn_farmacia_popular = mk_btn(frame_regulatorio, "Farmácia Popular", self._on_open_farmacia_popular)
        btn_farmacia_popular.grid(row=0, column=1, sticky="ew", padx=6, pady=6)

        return self.modules_panel
