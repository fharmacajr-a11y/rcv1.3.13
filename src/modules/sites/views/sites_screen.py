from __future__ import annotations

import logging
import tkinter as tk
import webbrowser
from dataclasses import dataclass

from src.ui.ctk_config import ctk
from src.ui.ui_tokens import (
    APP_BG,
    BORDER,
    BUTTON_H,
    CARD_PADDING,
    FONT_BODY_SM,
    FONT_SECTION,
    FONT_TITLE,
    PRIMARY_BLUE,
    SECTION_GAP,
    SURFACE,
    SURFACE_2,
    TEXT_MUTED,
    TEXT_PRIMARY,
)
from src.ui.widgets.ctk_section import CTkSection

logger = logging.getLogger(__name__)

# Largura mínima (px) do frame para ativar layout de 2 colunas
_TWO_COL_MIN_WIDTH = 700

# Constantes locais de visual dos cards.
# corner_radius=0: borda reta elimina o artefato de corner-gap-fill do CTk5.
# Dentro do CTkScrollableFrame, o canvas interno tem `bg` resolvido como string
# plana em criação; qualquer drift gera pixels de cor errada nos cantos de cards
# com corner_radius>0. Borda reta não preenche cantos → zero artefatos possíveis.
_CARD_BORDER: tuple[str, str] = ("#a0a0a0", "#484848")
_CARD_BORDER_W: int = 1
_CARD_CORNER_R: int = 0


@dataclass(frozen=True)
class SiteLink:
    name: str
    url: str


@dataclass(frozen=True)
class SiteCategory:
    name: str
    bootstyle: str  # mantido para compatibilidade de API; não usado visualmente
    sites: tuple[SiteLink, ...]


CATEGORY_EMPRESA = SiteCategory(
    name="Empresa / CNPJ / Registro",
    bootstyle="info",
    sites=(
        SiteLink(
            "Receita Federal – Consulta CNPJ",
            "https://servicos.receita.fazenda.gov.br/Servicos/cnpjreva/Cnpjreva_Solicitacao.asp",
        ),
        SiteLink("Jucesp – Portal", "https://www.jucesp.sp.gov.br/"),
        SiteLink(
            "Jucesp – Viabilidade (nome empresarial)",
            "https://www.jucesp.sp.gov.br/viabilidade",
        ),
        SiteLink(
            "Jucesp – Consulta Empresa",
            "https://www.jucesp.sp.gov.br/consultaempresa",
        ),
    ),
)

CATEGORY_CONVENIOS = SiteCategory(
    name="Convênios / Operadoras / Drogarias",
    bootstyle="secondary",
    sites=(
        SiteLink("Functional Card", "https://functionalcardsaude.com.br/"),
        SiteLink("ePharma", "https://www.epharma.com.br/"),
        SiteLink("Portal da Drogaria", "https://www.portaldadrogaria.com.br/"),
    ),
)

CATEGORY_ANVISA = SiteCategory(
    name="Anvisa",
    bootstyle="info",
    sites=(
        SiteLink(
            "Anvisa – Consulta situação de documentos",
            "https://consultas.anvisa.gov.br/#/documentos/",
        ),
        SiteLink(
            "Anvisa – Cadastro de Empresa (AFE / Autorização especial)",
            "https://www.gov.br/pt-br/servicos/obter-autorizacao-de-funcionamento-de-empresa-afe-ou-autorizacao-especial-afe-para-farmcias-e-drogarias",
        ),
        SiteLink(
            "Anvisa – Peticionamento Eletrônico (Solicita)",
            "https://www.gov.br/anvisa/pt-br/assuntos/regulados/peticionamento-eletronico",
        ),
        SiteLink(
            "Anvisa – Atendimento ao Público",
            "https://www.gov.br/anvisa/pt-br/canais_atendimento/atendimento-ao-publico",
        ),
    ),
)

CATEGORY_FARMACIA_POPULAR = SiteCategory(
    name="Farmácia Popular",
    bootstyle="secondary",
    sites=(
        SiteLink(
            "Farmácia Popular – Login credenciados",
            "https://aqui-tem-farmacia-popular.saude.gov.br/acesso",
        ),
        SiteLink(
            "Farmácia Popular – Portal gov.br",
            "https://www.gov.br/saude/pt-br/assuntos/farmacia-popular",
        ),
        SiteLink(
            "Aqui Tem Farmácia Popular",
            "https://aqui-tem-farmacia-popular.saude.gov.br/",
        ),
    ),
)

CATEGORY_FINANCAS = SiteCategory(
    name="Finanças / Notas",
    bootstyle="info",
    sites=(
        SiteLink(
            "Fundo Nacional de Saúde (FNS)",
            "https://www.gov.br/saude/pt-br/composicao/fns",
        ),
        SiteLink("NFS-e Nacional", "https://www.nfse.gov.br/"),
    ),
)


CATEGORIES: tuple[SiteCategory, ...] = (
    CATEGORY_EMPRESA,
    CATEGORY_CONVENIOS,
    CATEGORY_ANVISA,
    CATEGORY_FARMACIA_POPULAR,
    CATEGORY_FINANCAS,
)

SITES: tuple[SiteLink, ...] = tuple(site for category in CATEGORIES for site in category.sites)


class SitesScreen(ctk.CTkFrame):
    """Tela de atalhos para sites e portais externos úteis.

    Layout:
    - row=0: Cabeçalho com título e subtítulo
    - row=1: Área rolável com cards de categorias em grid de 1 ou 2 colunas
             (responsivo: ≥700 px → 2 colunas; < 700 px → 1 coluna)
    """

    def __init__(self, master: tk.Misc, *args: object, **kwargs: object) -> None:
        # fg_color=APP_BG evita flash cinza padrão do CTkFrame (BUG #3)
        kwargs.setdefault("fg_color", APP_BG)  # type: ignore[arg-type]
        super().__init__(master, *args, **kwargs)

        # Coluna 0 expande toda a largura disponível; linha 1 (scroll) expande verticalmente
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self._col_count: int = 0
        self._category_cards: list[ctk.CTkFrame] = []

        self._build_header()
        self._build_categories_area()

        self.bind("<Configure>", self._on_resize, add="+")

    # ------------------------------------------------------------------
    # Construção da UI
    # ------------------------------------------------------------------

    def _build_header(self) -> None:
        """Cabeçalho com título da página e subtítulo descritivo."""
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=CARD_PADDING, pady=(CARD_PADDING, 0))

        ctk.CTkLabel(
            header,
            text="Sites Úteis",
            font=FONT_TITLE,
            text_color=TEXT_PRIMARY,
            anchor="w",
        ).pack(side="left")

        ctk.CTkLabel(
            header,
            text="  ·  Atalhos para portais e sistemas externos",
            font=FONT_BODY_SM,
            text_color=TEXT_MUTED,
            anchor="w",
        ).pack(side="left")

    def _build_categories_area(self) -> None:
        """Área rolável com cards de categorias em grid adaptativo (1 ou 2 colunas)."""
        # fg_color="transparent": herda de SitesScreen (APP_BG) em vez de hardcodar
        # a tupla. O canvas interno do CTkScrollableFrame resolve a cor dinamicamente,
        # eliminando o mismatch que causa artefato de canto nos cards filhos.
        self._scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            corner_radius=0,
            border_width=0,
            scrollbar_button_color=BORDER,
            scrollbar_button_hover_color=SURFACE_2,
        )
        self._scroll.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=CARD_PADDING,
            pady=(SECTION_GAP // 2, CARD_PADDING),
        )
        self._scroll.columnconfigure(0, weight=1)
        self._scroll.columnconfigure(1, weight=1)

        for category in CATEGORIES:
            card = self._build_category_card(self._scroll, category)
            self._category_cards.append(card)

        # Posicionamento inicial: 2 colunas por padrão
        self._place_cards(2)

    def _build_category_card(self, parent: tk.Misc, category: SiteCategory) -> ctk.CTkFrame:
        """Cria o card visual de uma categoria com title e links estilo âncora."""
        # bg_color="transparent": CTk5 resolve dinamicamente a partir da cadeia
        # de pais em cada repaint; corner_radius=0 (borda reta): evita que o CTk5
        # precise preencher áreas de canto com bg_color, eliminando qualquer
        # artefato de cor quando o canvas interno do CTkScrollableFrame não
        # coincide pixel-a-pixel com o bg_color declarado.
        card = CTkSection(
            parent,
            title=category.name,
            title_font=FONT_SECTION,
            fg_color=SURFACE,
            bg_color="transparent",
            corner_radius=_CARD_CORNER_R,
            border_width=_CARD_BORDER_W,
            border_color=_CARD_BORDER,
        )

        # Linha separadora fina abaixo do título
        ctk.CTkFrame(
            card.content_frame,
            fg_color=BORDER,
            height=1,
            corner_radius=0,
        ).pack(fill="x", pady=(0, 4))

        # Link buttons: fundo transparente, cor azul, hover sutil
        for site in category.sites:
            ctk.CTkButton(
                card.content_frame,
                text=f"  {site.name}",
                command=lambda url=site.url: self._open_site(url),
                anchor="w",
                fg_color="transparent",
                hover_color=SURFACE_2,
                text_color=PRIMARY_BLUE,
                height=BUTTON_H,
                corner_radius=6,
            ).pack(fill="x", padx=4, pady=2)

        # Espaçamento inferior interno
        ctk.CTkFrame(card.content_frame, fg_color="transparent", height=CARD_PADDING // 2).pack()

        return card  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Layout responsivo
    # ------------------------------------------------------------------

    def _place_cards(self, cols: int) -> None:
        """Distribui os cards de categoria no grid com `cols` colunas."""
        if cols == self._col_count:
            return
        self._col_count = cols

        # Atualizar pesos: colunas em uso recebem weight=1; demais weight=0
        for c in range(2):
            self._scroll.columnconfigure(c, weight=1 if c < cols else 0)

        # _HALF: metade do gutter central (col=0 contribui _HALF à direita,
        #        col=1 contribui _HALF à esquerda → total 12 px entre cards).
        # _RMARGIN: folga entre o último card e o trilho da scrollbar.
        # Padding assimétrico anterior (0, gap) causava "seam" porque col=1
        # ficava sem margem esquerda, colando no boundary da célula.
        half: int = 6
        rmargin: int = 6
        vgap: int = SECTION_GAP // 2

        for i, card in enumerate(self._category_cards):
            row = i // cols
            col = i % cols

            if cols == 1:
                px: tuple[int, int] = (0, rmargin)
            elif col == 0:
                px = (0, half)
            else:
                px = (half, rmargin)

            card.grid(
                row=row,
                column=col,
                sticky="nsew",
                padx=px,
                pady=(0, vgap),
            )

    def _on_resize(self, event: tk.Event) -> None:  # type: ignore[override]
        """Alterna entre 1 e 2 colunas conforme a largura disponível do frame.

        Ignora eventos espúrios com width<=1 que o Tk dispara ao montar o
        widget (antes do geometry manager calcular o tamanho real). Sem esse
        guard, o layout colapsaria para 1 coluna momentaneamente, gerando um
        flash/bounce visual logo na primeira exibição da tela.
        """
        if event.width <= 1:
            return
        cols = 2 if event.width >= _TWO_COL_MIN_WIDTH else 1
        self._place_cards(cols)

    # ------------------------------------------------------------------
    # Ações
    # ------------------------------------------------------------------

    def _open_site(self, url: str) -> None:
        """Abre URL no navegador padrão; registra falha em debug."""
        try:
            webbrowser.open_new_tab(url)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao abrir URL %s: %s", url, exc)
