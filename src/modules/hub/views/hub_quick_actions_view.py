"""View do painel de Quick Actions (módulos) do Hub.

Extraído de HubScreen na MF-25 para reduzir o tamanho do monolito.
Este módulo é responsável APENAS pela construção visual do painel lateral
esquerdo com os botões de acesso rápido aos módulos.
"""

from typing import Any, Callable, Optional
import tkinter as tk

from src.ui.ctk_config import ctk, HAS_CUSTOMTKINTER
from src.ui.ui_tokens import APP_BG, SURFACE_DARK, CARD_RADIUS
from src.ui.widgets.button_factory import make_btn


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
        on_open_farmacia_popular: Optional[Callable[[], None]] = None,
        on_open_sngpc: Optional[Callable[[], None]] = None,
        on_open_mod_sifap: Optional[Callable[[], None]] = None,
    ):
        """Inicializa a view do painel de Quick Actions.

        Args:
            parent: Widget pai (onde o painel será criado)
            on_open_clientes: Callback para abrir módulo Clientes
            on_open_cashflow: Callback para abrir módulo Fluxo de Caixa
            on_open_farmacia_popular: Callback para abrir módulo Farmácia Popular
            on_open_sngpc: Callback para abrir módulo Sngpc
            on_open_mod_sifap: Callback para abrir módulo Sifap
        """
        self._parent = parent
        self._on_open_clientes = on_open_clientes
        self._on_open_cashflow = on_open_cashflow
        self._on_open_farmacia_popular = on_open_farmacia_popular
        self._on_open_sngpc = on_open_sngpc
        self._on_open_mod_sifap = on_open_mod_sifap

        self.modules_panel: Optional[tk.LabelFrame] = None

    def build(self) -> tk.LabelFrame:
        """Constrói e retorna o frame do painel de Quick Actions.

        Returns:
            O frame principal do painel de Quick Actions (pronto para ser anexado ao layout)
        """
        from src.modules.hub.constants import PAD_OUTER
        from src.ui.ui_tokens import SURFACE

        # Helper para criar botão compatível CTk/Tk com estilo e largura fixa
        def mk_btn(parent, text, command=None):
            if HAS_CUSTOMTKINTER and ctk is not None:
                return make_btn(
                    parent,
                    text=text,
                    command=command,
                    width=140,  # Largura específica para botões do Hub (um pouco maior que padrão)
                    fg_color=("#3b82f6", "#2563eb"),
                    hover_color=("#2563eb", "#1d4ed8"),
                    text_color="#ffffff",
                )
            else:
                return tk.Button(parent, text=text, command=command, width=20)

        # Helper para criar um bloco (caixa) de seção
        def mk_section(parent_frame, title_text):
            if HAS_CUSTOMTKINTER and ctk is not None:
                box = ctk.CTkFrame(
                    parent_frame,
                    fg_color=SURFACE,
                    corner_radius=8,
                    border_width=0,
                )
            else:
                box = tk.LabelFrame(parent_frame, text=title_text, padding=(8, 6))
                return box, box  # para tk.LabelFrame o conteúdo vai direto

            # Título dentro da caixa
            lbl = ctk.CTkLabel(
                box,
                text=f"► {title_text}",
                font=("Arial", 12, "bold"),
                text_color=("#374151", "#d1d5db"),
                fg_color="transparent",
            )
            lbl.pack(anchor="w", padx=10, pady=(3, 0))

            # Container interno para botões
            inner = ctk.CTkFrame(box, fg_color="transparent")
            inner.pack(fill="x", padx=10, pady=(0, 8))
            return box, inner

        # Painel principal - fundo cinza escuro sem borda
        if HAS_CUSTOMTKINTER and ctk is not None:
            self.modules_panel = ctk.CTkFrame(
                self._parent,
                fg_color=SURFACE_DARK,
                bg_color=APP_BG,
                border_width=0,
                corner_radius=CARD_RADIUS,
            )
        else:
            self.modules_panel = tk.Frame(self._parent)

        # Container de conteúdo com padding (sem título "Módulos")
        if HAS_CUSTOMTKINTER and ctk is not None:
            content_container = ctk.CTkFrame(self.modules_panel, fg_color="transparent")
        else:
            content_container = tk.Frame(self.modules_panel)
        content_container.pack(fill="both", expand=True, padx=PAD_OUTER, pady=PAD_OUTER)

        # BLOCO 1: Cadastros / Acesso
        box_cadastros, inner_cadastros = mk_section(content_container, "Cadastros / Acesso")
        box_cadastros.pack(fill="x", pady=(0, 8))

        btn_clientes = mk_btn(inner_cadastros, "Clientes", self._on_open_clientes)
        btn_clientes.pack(pady=4)

        # BLOCO 2: Gestão
        box_gestao, inner_gestao = mk_section(content_container, "Gestão")
        box_gestao.pack(fill="x", pady=(0, 8))

        btn_fluxo_caixa = mk_btn(inner_gestao, "Fluxo de Caixa", self._on_open_cashflow)
        btn_fluxo_caixa.pack(pady=4)

        # BLOCO 3: Regulatório / Programas
        box_regulatorio, inner_regulatorio = mk_section(content_container, "Regulatório / Programas")
        box_regulatorio.pack(fill="x", pady=(0, 0))

        btn_farmacia_popular = mk_btn(inner_regulatorio, "Farmácia Popular", self._on_open_farmacia_popular)
        btn_farmacia_popular.pack(pady=4)

        btn_anvisa = mk_btn(inner_regulatorio, "Anvisa", None)  # Anvisa sem callback (módulo removido)
        btn_anvisa.pack(pady=4)

        return self.modules_panel
