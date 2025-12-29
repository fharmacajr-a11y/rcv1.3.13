"""View do painel de Quick Actions (módulos) do Hub.

Extraído de HubScreen na MF-25 para reduzir o tamanho do monolito.
Este módulo é responsável APENAS pela construção visual do painel lateral
esquerdo com os botões de acesso rápido aos módulos.
"""

from typing import Any, Callable, Optional

import ttkbootstrap as tb


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
        parent: Any,  # tk.Widget ou tb.Frame
        *,
        on_open_clientes: Optional[Callable[[], None]] = None,
        on_open_senhas: Optional[Callable[[], None]] = None,
        on_open_auditoria: Optional[Callable[[], None]] = None,
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
            on_open_senhas: Callback para abrir módulo Senhas
            on_open_auditoria: Callback para abrir módulo Auditoria
            on_open_cashflow: Callback para abrir módulo Fluxo de Caixa
            on_open_anvisa: Callback para abrir módulo Anvisa
            on_open_farmacia_popular: Callback para abrir módulo Farmácia Popular
            on_open_sngpc: Callback para abrir módulo Sngpc
            on_open_mod_sifap: Callback para abrir módulo Sifap
        """
        self._parent = parent
        self._on_open_clientes = on_open_clientes
        self._on_open_senhas = on_open_senhas
        self._on_open_auditoria = on_open_auditoria
        self._on_open_cashflow = on_open_cashflow
        self._on_open_anvisa = on_open_anvisa
        self._on_open_farmacia_popular = on_open_farmacia_popular
        self._on_open_sngpc = on_open_sngpc
        self._on_open_mod_sifap = on_open_mod_sifap

        self.modules_panel: Optional[tb.Labelframe] = None

    def build(self) -> tb.Labelframe:
        """Constrói e retorna o frame do painel de Quick Actions.

        Este método cria toda a estrutura visual do painel:
        - Frame principal (Labelframe com título)
        - 3 blocos de botões: Cadastros/Acesso, Gestão/Auditoria, Regulatório/Programas
        - Botões individuais com suas callbacks

        Returns:
            O frame principal do painel de Quick Actions (pronto para ser anexado ao layout)
        """
        from src.modules.hub.constants import (
            HUB_BTN_STYLE_AUDITORIA,
            HUB_BTN_STYLE_CLIENTES,
            HUB_BTN_STYLE_FLUXO_CAIXA,
            HUB_BTN_STYLE_SENHAS,
            MODULES_TITLE,
            PAD_OUTER,
        )

        # Helper para criar botão com bootstyle
        def mk_btn(parent, text, command=None, bootstyle="secondary"):
            return tb.Button(parent, text=text, command=command, bootstyle=bootstyle)

        # Painel principal
        self.modules_panel = tb.Labelframe(self._parent, text=MODULES_TITLE, padding=PAD_OUTER)

        # BLOCO 1: Cadastros / Acesso
        frame_cadastros = tb.Labelframe(
            self.modules_panel,
            text="Cadastros / Acesso",
            padding=(8, 6),
        )
        frame_cadastros.pack(fill="x", pady=(0, 8))
        frame_cadastros.columnconfigure(0, weight=1)
        frame_cadastros.columnconfigure(1, weight=1)

        btn_clientes = mk_btn(frame_cadastros, "Clientes", self._on_open_clientes, HUB_BTN_STYLE_CLIENTES)
        btn_clientes.grid(row=0, column=0, sticky="ew", padx=3, pady=3)

        btn_senhas = mk_btn(frame_cadastros, "Senhas", self._on_open_senhas, HUB_BTN_STYLE_SENHAS)
        btn_senhas.grid(row=0, column=1, sticky="ew", padx=3, pady=3)

        # BLOCO 2: Gestão / Auditoria
        frame_gestao = tb.Labelframe(
            self.modules_panel,
            text="Gestão / Auditoria",
            padding=(8, 6),
        )
        frame_gestao.pack(fill="x", pady=(0, 8))
        frame_gestao.columnconfigure(0, weight=1)
        frame_gestao.columnconfigure(1, weight=1)

        btn_auditoria = mk_btn(frame_gestao, "Auditoria", self._on_open_auditoria, HUB_BTN_STYLE_AUDITORIA)
        btn_auditoria.grid(row=0, column=0, sticky="ew", padx=3, pady=3)

        btn_fluxo_caixa = mk_btn(frame_gestao, "Fluxo de Caixa", self._on_open_cashflow, HUB_BTN_STYLE_FLUXO_CAIXA)
        btn_fluxo_caixa.grid(row=0, column=1, sticky="ew", padx=3, pady=3)

        # BLOCO 3: Regulatório / Programas
        frame_regulatorio = tb.Labelframe(
            self.modules_panel,
            text="Regulatório / Programas",
            padding=(8, 6),
        )
        frame_regulatorio.pack(fill="x", pady=(0, 0))
        frame_regulatorio.columnconfigure(0, weight=1)
        frame_regulatorio.columnconfigure(1, weight=1)

        btn_anvisa = mk_btn(frame_regulatorio, "Anvisa", self._on_open_anvisa, "info")
        btn_anvisa.grid(row=0, column=0, sticky="ew", padx=3, pady=3)

        btn_farmacia_popular = mk_btn(frame_regulatorio, "Farmácia Popular", self._on_open_sngpc, "secondary")
        btn_farmacia_popular.grid(row=0, column=1, sticky="ew", padx=3, pady=3)

        return self.modules_panel
