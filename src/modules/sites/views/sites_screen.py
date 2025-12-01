from __future__ import annotations

import logging
import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk
import webbrowser


@dataclass(frozen=True)
class SiteLink:
    name: str
    url: str


@dataclass(frozen=True)
class SiteCategory:
    name: str
    bootstyle: str
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
            "Anvisa – Chat / Atendimento ao público",
            "https://www.gov.br/anvisa/pt-br/canais_atendimento/atendimento-ao-publico",
        ),
    ),
)

CATEGORY_FARMACIA_POPULAR = SiteCategory(
    name="Farmácia Popular",
    bootstyle="secondary",
    sites=(
        SiteLink(
            "Farmácia Popular – Sistema de Registro e Auditoria (login credenciados)",
            "https://aqui-tem-farmacia-popular.saude.gov.br/acesso",
        ),
        SiteLink(
            "Farmácia Popular – Portal público (gov.br)",
            "https://www.gov.br/saude/pt-br/assuntos/farmacia-popular",
        ),
        SiteLink(
            "Farmácia Popular – Portal Aqui Tem Farmácia Popular",
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


class SitesScreen(ttk.Frame):
    """Tela simples de atalhos para sites úteis (apenas botões)."""

    def __init__(self, master: tk.Misc, *args: object, **kwargs: object) -> None:
        super().__init__(master, *args, **kwargs)

        self.empresa_buttons: list[ttk.Button] = []
        self.convenios_buttons: list[ttk.Button] = []
        self.anvisa_buttons: list[ttk.Button] = []
        self.farmacia_popular_buttons: list[ttk.Button] = []
        self.financas_buttons: list[ttk.Button] = []

        category_button_map = {
            CATEGORY_EMPRESA.name: self.empresa_buttons,
            CATEGORY_CONVENIOS.name: self.convenios_buttons,
            CATEGORY_ANVISA.name: self.anvisa_buttons,
            CATEGORY_FARMACIA_POPULAR.name: self.farmacia_popular_buttons,
            CATEGORY_FINANCAS.name: self.financas_buttons,
        }

        title = ttk.Label(self, text="Sites úteis", font=("TkDefaultFont", 12, "bold"))
        title.pack(anchor="w", padx=15, pady=(10, 5))

        content = ttk.Frame(self)
        content.pack(anchor="n", pady=(5, 15), expand=True)
        content.columnconfigure(0, weight=1)

        for row_index, category in enumerate(CATEGORIES):
            category_frame = ttk.Labelframe(
                content,
                text=category.name,
                bootstyle="dark",
                padding=(10, 8),
            )
            category_frame.grid(row=row_index, column=0, sticky="n", pady=(0, 12))
            category_frame.columnconfigure(0, weight=1)

            for i, site in enumerate(category.sites):
                btn = ttk.Button(
                    category_frame,
                    text=site.name,
                    width=80,
                    bootstyle=category.bootstyle,
                    command=lambda url=site.url: self._open_site(url),
                )
                btn.grid(row=i, column=0, sticky="ew", pady=3, padx=(5, 5))
                if category.name in category_button_map:
                    category_button_map[category.name].append(btn)

    def _open_site(self, url: str) -> None:
        try:
            webbrowser.open_new_tab(url)
        except Exception as exc:  # noqa: BLE001
            logger = logging.getLogger(__name__)
            logger.debug("Falha ao abrir URL %s: %s", url, exc)
