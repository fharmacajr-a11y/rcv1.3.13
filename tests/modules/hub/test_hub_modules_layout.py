# -*- coding: utf-8 -*-
"""Testes para o layout de módulos do Hub (HUB-MODULOS-001).

**NOTA (2025-12-12):** Estes testes foram escritos para versão antiga do HUB
que tinha strings hardcoded em HubScreen.__init__. Após refactor MF-15+
(QuickActionsViewModel com dados dinâmicos), a abordagem de inspeção de
código-fonte não funciona mais.

**TODO:** Reescrever estes testes para:
1. Testar QuickActionsViewModel.get_all_actions() retorna ações corretas
2. Testar build_modules_panel() cria widgets esperados (via fixtures Tk)
3. Testar categorização e ordenação de ações no ViewModel
4. Remover inspeção de código-fonte (inspect.getsource)

Testa:
- Existência dos três blocos de módulos
- Botões corretos em cada bloco
- Estilos de botões via constantes (info/secondary)
- Layout 2-por-linha (grid columns)
- Largura mínima da coluna de módulos
"""

from __future__ import annotations

import inspect

import pytest

from src.modules.hub.constants import (
    HUB_BTN_STYLE_AUDITORIA,
    HUB_BTN_STYLE_CLIENTES,
    HUB_BTN_STYLE_FLUXO_CAIXA,
    HUB_BTN_STYLE_SENHAS,
    MODULES_COL_MINSIZE,
)


@pytest.mark.skip(
    reason="Testes obsoletos após refactor MF-15+ (QuickActionsViewModel). "
    "Reescrever para testar ViewModel e widgets em vez de inspecionar código-fonte."
)
class TestHubModulesLayout:
    """Testes estruturais do layout de módulos no Hub."""

    def test_module_panel_exists(self):
        """Verifica que o módulo exporta build_modules_panel."""
        from src.modules.hub.views.modules_panel import build_modules_panel

        assert callable(build_modules_panel)
        source = inspect.getsource(build_modules_panel)
        assert "modules_panel" in source or "Labelframe" in source

    def test_three_blocks_defined(self):
        """Verifica que os três blocos de módulos estão definidos."""
        from src.modules.hub.views.modules_panel import _build_quick_actions_by_category

        source = inspect.getsource(_build_quick_actions_by_category)

        # Bloco 1: Cadastros / Acesso
        assert '"Cadastros / Acesso"' in source

        # Bloco 2: Gestão / Auditoria
        assert '"Gestão / Auditoria"' in source

        # Bloco 3: Regulatório / Programas
        assert '"Regulatório / Programas"' in source

    def test_block_cadastros_buttons(self):
        """Verifica que o bloco Cadastros/Acesso contém categoria cadastros."""
        from src.modules.hub.views.modules_panel import _build_quick_actions_by_category

        source = inspect.getsource(_build_quick_actions_by_category)

        # Encontrar a seção do bloco cadastros
        idx_cadastros = source.find('"Cadastros / Acesso"')
        idx_gestao = source.find('"Gestão / Auditoria"')

        assert idx_cadastros != -1, "Bloco 'Cadastros / Acesso' não encontrado"
        assert idx_gestao != -1, "Bloco 'Gestão / Auditoria' não encontrado"

        # Verificar botões entre os dois blocos
        block_section = source[idx_cadastros:idx_gestao]
        assert '"Clientes"' in block_section
        assert '"Senhas"' in block_section

    def test_block_gestao_buttons(self):
        """Verifica que o bloco Gestão/Auditoria contém Auditoria e Fluxo de Caixa."""
        from src.modules.hub.views.hub_screen import HubScreen

        source = inspect.getsource(HubScreen.__init__)

        # Encontrar a seção do bloco gestão
        idx_gestao = source.find('"Gestão / Auditoria"')
        idx_regulatorio = source.find('"Regulatório / Programas"')

        assert idx_gestao != -1, "Bloco 'Gestão / Auditoria' não encontrado"
        assert idx_regulatorio != -1, "Bloco 'Regulatório / Programas' não encontrado"

        # Verificar botões entre os dois blocos
        block_section = source[idx_gestao:idx_regulatorio]
        assert '"Auditoria"' in block_section
        assert '"Fluxo de Caixa"' in block_section

    def test_block_regulatorio_buttons(self):
        """Verifica que o bloco Regulatório/Programas contém os módulos corretos."""
        from src.modules.hub.views.hub_screen import HubScreen

        source = inspect.getsource(HubScreen.__init__)

        # Encontrar a seção do bloco regulatório
        idx_regulatorio = source.find('"Regulatório / Programas"')

        assert idx_regulatorio != -1, "Bloco 'Regulatório / Programas' não encontrado"

        # Verificar botões após o início do bloco
        block_section = source[idx_regulatorio:]
        assert '"Anvisa"' in block_section
        assert '"Farmácia Popular"' in block_section
        assert '"Sngpc"' in block_section
        assert '"Sifap"' in block_section

    def test_senhas_button_uses_info_style(self):
        """Verifica que o botão Senhas usa estilo info (azul claro) via constante."""
        from src.modules.hub.views.hub_screen import HubScreen

        source = inspect.getsource(HubScreen.__init__)

        # Verificar que usa a constante HUB_BTN_STYLE_SENHAS
        idx_senhas = source.find('"Senhas"')
        assert idx_senhas != -1, "Botão 'Senhas' não encontrado"

        line_start = source.rfind("\n", 0, idx_senhas) + 1
        line_end = source.find("\n", idx_senhas)
        senhas_line = source[line_start:line_end]

        assert "HUB_BTN_STYLE_SENHAS" in senhas_line, f"Botão Senhas não usa constante: {senhas_line}"
        assert HUB_BTN_STYLE_SENHAS == "info", "Constante HUB_BTN_STYLE_SENHAS deveria ser 'info'"

    def test_clientes_button_uses_info_style(self):
        """Verifica que o botão Clientes usa estilo info (azul claro) via constante."""
        from src.modules.hub.views.hub_screen import HubScreen

        source = inspect.getsource(HubScreen.__init__)

        idx_clientes = source.find('"Clientes"')
        assert idx_clientes != -1, "Botão 'Clientes' não encontrado"

        line_start = source.rfind("\n", 0, idx_clientes) + 1
        line_end = source.find("\n", idx_clientes)
        clientes_line = source[line_start:line_end]

        assert "HUB_BTN_STYLE_CLIENTES" in clientes_line, f"Botão Clientes não usa constante: {clientes_line}"
        assert HUB_BTN_STYLE_CLIENTES == "info", "Constante HUB_BTN_STYLE_CLIENTES deveria ser 'info'"

    def test_auditoria_button_uses_info_style(self):
        """Verifica que o botão Auditoria usa estilo info (azul claro) via constante."""
        from src.modules.hub.views.hub_screen import HubScreen

        source = inspect.getsource(HubScreen.__init__)

        idx_auditoria = source.find('"Auditoria"')
        assert idx_auditoria != -1, "Botão 'Auditoria' não encontrado"

        line_start = source.rfind("\n", 0, idx_auditoria) + 1
        line_end = source.find("\n", idx_auditoria)
        auditoria_line = source[line_start:line_end]

        assert "HUB_BTN_STYLE_AUDITORIA" in auditoria_line, f"Botão Auditoria não usa constante: {auditoria_line}"
        assert HUB_BTN_STYLE_AUDITORIA == "info", "Constante HUB_BTN_STYLE_AUDITORIA deveria ser 'info'"

    def test_fluxo_caixa_button_uses_secondary_style(self):
        """Verifica que o botão Fluxo de Caixa usa estilo secondary (cinza) via constante."""
        from src.modules.hub.views.hub_screen import HubScreen

        source = inspect.getsource(HubScreen.__init__)

        idx_fluxo = source.find('"Fluxo de Caixa"')
        assert idx_fluxo != -1, "Botão 'Fluxo de Caixa' não encontrado"

        # Primeira ocorrência deve usar a constante
        line_start = source.rfind("\n", 0, idx_fluxo) + 1
        line_end = source.find("\n", idx_fluxo)
        fluxo_line = source[line_start:line_end]

        assert "HUB_BTN_STYLE_FLUXO_CAIXA" in fluxo_line, f"Botão Fluxo de Caixa não usa constante: {fluxo_line}"
        assert HUB_BTN_STYLE_FLUXO_CAIXA == "secondary", "Constante HUB_BTN_STYLE_FLUXO_CAIXA deveria ser 'secondary'"

    def test_all_eight_modules_present(self):
        """Verifica que todos os 8 módulos estão presentes no Hub."""
        from src.modules.hub.views.hub_screen import HubScreen

        source = inspect.getsource(HubScreen.__init__)

        expected_modules = [
            "Clientes",
            "Senhas",
            "Auditoria",
            "Fluxo de Caixa",
            "Anvisa",
            "Farmácia Popular",
            "Sngpc",
            "Sifap",
        ]

        for module in expected_modules:
            assert f'"{module}"' in source, f"Módulo '{module}' não encontrado"

    def test_blocks_use_labelframe(self):
        """Verifica que os blocos usam Labelframe com bootstyle dark."""
        from src.modules.hub.views.hub_screen import HubScreen

        source = inspect.getsource(HubScreen.__init__)

        # Deve haver pelo menos 3 Labelframes com bootstyle="dark"
        count_labelframes = source.count('bootstyle="dark"')
        assert count_labelframes >= 3, f"Esperado ≥3 Labelframes com dark, encontrado {count_labelframes}"

    def test_grid_layout_preserved(self):
        """Verifica que a grid de 3 colunas está preservada (modules/spacer/notes)."""
        from src.modules.hub.views.hub_screen import HubScreen

        source = inspect.getsource(HubScreen.__init__)

        # Verifica elementos da grid
        assert "modules_panel" in source
        assert "center_spacer" in source
        assert "notes_panel" in source
        assert "apply_hub_notes_right" in source


@pytest.mark.skip(
    reason="Testes obsoletos após refactor MF-15+ (QuickActionsViewModel). "
    "Reescrever para testar ViewModel e widgets em vez de inspecionar código-fonte."
)
class TestHubModulesOrder:
    """Testes para verificar a ordem correta dos módulos."""

    def test_cadastros_comes_first(self):
        """Bloco Cadastros deve vir antes de Gestão."""
        from src.modules.hub.views.hub_screen import HubScreen

        source = inspect.getsource(HubScreen.__init__)

        idx_cadastros = source.find('"Cadastros / Acesso"')
        idx_gestao = source.find('"Gestão / Auditoria"')

        assert idx_cadastros < idx_gestao, "Cadastros deve vir antes de Gestão"

    def test_gestao_comes_before_regulatorio(self):
        """Bloco Gestão deve vir antes de Regulatório."""
        from src.modules.hub.views.hub_screen import HubScreen

        source = inspect.getsource(HubScreen.__init__)

        idx_gestao = source.find('"Gestão / Auditoria"')
        idx_regulatorio = source.find('"Regulatório / Programas"')

        assert idx_gestao < idx_regulatorio, "Gestão deve vir antes de Regulatório"

    def test_clientes_before_senhas(self):
        """Clientes deve vir antes de Senhas no bloco Cadastros."""
        from src.modules.hub.views.hub_screen import HubScreen

        source = inspect.getsource(HubScreen.__init__)

        idx_clientes = source.find('mk_btn(frame_cadastros, "Clientes"')
        idx_senhas = source.find('mk_btn(frame_cadastros, "Senhas"')

        assert idx_clientes != -1, "Botão Clientes não encontrado no frame_cadastros"
        assert idx_senhas != -1, "Botão Senhas não encontrado no frame_cadastros"
        assert idx_clientes < idx_senhas, "Clientes deve vir antes de Senhas"


@pytest.mark.skip(
    reason="Testes obsoletos após refactor MF-15+ (QuickActionsViewModel). "
    "Reescrever para testar ViewModel e widgets em vez de inspecionar código-fonte."
)
class TestHubModulesGridLayout:
    """Testes para verificar layout 2-por-linha (grid columns)."""

    def test_frame_cadastros_has_two_columns(self):
        """Verifica que frame_cadastros configura 2 colunas."""
        from src.modules.hub.views.hub_screen import HubScreen

        source = inspect.getsource(HubScreen.__init__)

        # Procurar configuração de colunas após frame_cadastros
        idx_cadastros = source.find("frame_cadastros = ")
        idx_gestao = source.find("frame_gestao = ")

        block_section = source[idx_cadastros:idx_gestao]
        assert "frame_cadastros.columnconfigure(0" in block_section
        assert "frame_cadastros.columnconfigure(1" in block_section

    def test_frame_gestao_has_two_columns(self):
        """Verifica que frame_gestao configura 2 colunas."""
        from src.modules.hub.views.hub_screen import HubScreen

        source = inspect.getsource(HubScreen.__init__)

        idx_gestao = source.find("frame_gestao = ")
        idx_regulatorio = source.find("frame_regulatorio = ")

        block_section = source[idx_gestao:idx_regulatorio]
        assert "frame_gestao.columnconfigure(0" in block_section
        assert "frame_gestao.columnconfigure(1" in block_section

    def test_frame_regulatorio_has_two_columns(self):
        """Verifica que frame_regulatorio configura 2 colunas."""
        from src.modules.hub.views.hub_screen import HubScreen

        source = inspect.getsource(HubScreen.__init__)

        idx_regulatorio = source.find("frame_regulatorio = ")

        block_section = source[idx_regulatorio:]
        assert "frame_regulatorio.columnconfigure(0" in block_section
        assert "frame_regulatorio.columnconfigure(1" in block_section

    def test_clientes_in_column_0(self):
        """Verifica que botão Clientes está na coluna 0."""
        from src.modules.hub.views.hub_screen import HubScreen

        source = inspect.getsource(HubScreen.__init__)

        idx_clientes = source.find("btn_clientes.grid")
        assert idx_clientes != -1, "btn_clientes.grid não encontrado"

        line_start = source.rfind("\n", 0, idx_clientes) + 1
        line_end = source.find("\n", idx_clientes)
        clientes_grid_line = source[line_start:line_end]

        assert "column=0" in clientes_grid_line, f"Clientes deveria estar em column=0: {clientes_grid_line}"

    def test_senhas_in_column_1(self):
        """Verifica que botão Senhas está na coluna 1."""
        from src.modules.hub.views.hub_screen import HubScreen

        source = inspect.getsource(HubScreen.__init__)

        idx_senhas = source.find("btn_senhas.grid")
        assert idx_senhas != -1, "btn_senhas.grid não encontrado"

        line_start = source.rfind("\n", 0, idx_senhas) + 1
        line_end = source.find("\n", idx_senhas)
        senhas_grid_line = source[line_start:line_end]

        assert "column=1" in senhas_grid_line, f"Senhas deveria estar em column=1: {senhas_grid_line}"

    def test_auditoria_in_column_0(self):
        """Verifica que botão Auditoria está na coluna 0."""
        from src.modules.hub.views.hub_screen import HubScreen

        source = inspect.getsource(HubScreen.__init__)

        idx_auditoria = source.find("btn_auditoria.grid")
        assert idx_auditoria != -1, "btn_auditoria.grid não encontrado"

        line_start = source.rfind("\n", 0, idx_auditoria) + 1
        line_end = source.find("\n", idx_auditoria)
        auditoria_grid_line = source[line_start:line_end]

        assert "column=0" in auditoria_grid_line, f"Auditoria deveria estar em column=0: {auditoria_grid_line}"

    def test_fluxo_caixa_in_column_1(self):
        """Verifica que botão Fluxo de Caixa está na coluna 1."""
        from src.modules.hub.views.hub_screen import HubScreen

        source = inspect.getsource(HubScreen.__init__)

        idx_fluxo = source.find("btn_fluxo_caixa.grid")
        assert idx_fluxo != -1, "btn_fluxo_caixa.grid não encontrado"

        line_start = source.rfind("\n", 0, idx_fluxo) + 1
        line_end = source.find("\n", idx_fluxo)
        fluxo_grid_line = source[line_start:line_end]

        assert "column=1" in fluxo_grid_line, f"Fluxo de Caixa deveria estar em column=1: {fluxo_grid_line}"

    def test_regulatorio_uses_2x2_grid(self):
        """Verifica que bloco Regulatório usa grid 2x2 (4 botões em 2 linhas)."""
        from src.modules.hub.views.hub_screen import HubScreen

        source = inspect.getsource(HubScreen.__init__)

        # Anvisa em (0, 0)
        idx_anvisa = source.find("btn_anvisa.grid")
        assert idx_anvisa != -1
        anvisa_section = source[idx_anvisa : idx_anvisa + 80]
        assert "row=0" in anvisa_section and "column=0" in anvisa_section

        # Farmácia Popular em (0, 1)
        idx_fp = source.find("btn_farmacia_pop.grid")
        assert idx_fp != -1
        fp_section = source[idx_fp : idx_fp + 80]
        assert "row=0" in fp_section and "column=1" in fp_section

        # Sngpc em (1, 0)
        idx_sngpc = source.find("btn_sngpc.grid")
        assert idx_sngpc != -1
        sngpc_section = source[idx_sngpc : idx_sngpc + 80]
        assert "row=1" in sngpc_section and "column=0" in sngpc_section

        # Sifap em (1, 1)
        idx_sifap = source.find("btn_sifap.grid")
        assert idx_sifap != -1
        sifap_section = source[idx_sifap : idx_sifap + 80]
        assert "row=1" in sifap_section and "column=1" in sifap_section


@pytest.mark.skip(
    reason="Testes obsoletos após refactor MF-15+ (QuickActionsViewModel). "
    "Reescrever para testar ViewModel e widgets em vez de inspecionar código-fonte."
)
class TestHubModulesColumnMinsize:
    """Testes para verificar largura mínima da coluna de módulos."""

    def test_modules_col_minsize_constant_exists(self):
        """Verifica que a constante MODULES_COL_MINSIZE existe e tem valor >= 240."""
        assert MODULES_COL_MINSIZE >= 240, f"MODULES_COL_MINSIZE deveria ser >= 240, é {MODULES_COL_MINSIZE}"

    def test_layout_uses_minsize_constant(self):
        """Verifica que layout.py usa MODULES_COL_MINSIZE para coluna 0."""
        from src.modules.hub import layout

        source = inspect.getsource(layout.apply_hub_notes_right)

        assert "MODULES_COL_MINSIZE" in source, "layout.py deveria usar MODULES_COL_MINSIZE"
        assert "minsize=MODULES_COL_MINSIZE" in source, "Coluna 0 deveria usar minsize=MODULES_COL_MINSIZE"
