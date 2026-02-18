# -*- coding: utf-8 -*-
"""
MF-50: Testes para hub_helpers_modules.py (100% coverage).

Testa:
- ModuleButton dataclass
- build_module_buttons (todas as combinações de flags)
- calculate_module_button_style (hierarquia de estilos)
"""

from __future__ import annotations

import pytest

from src.modules.hub.views.hub_helpers_modules import (
    ModuleButton,
    build_module_buttons,
    calculate_module_button_style,
)


class TestModuleButton:
    """Testes para dataclass ModuleButton."""

    def test_module_button_creation(self):
        """Testa criação de ModuleButton com todos os campos."""
        btn = ModuleButton(
            text="Clientes",
            enabled=True,
            bootstyle="info",
            has_callback=True,
        )
        assert btn.text == "Clientes"
        assert btn.enabled is True
        assert btn.bootstyle == "info"
        assert btn.has_callback is True

    def test_module_button_disabled(self):
        """Testa criação de ModuleButton desabilitado."""
        btn = ModuleButton(
            text="Anvisa",
            enabled=False,
            bootstyle="secondary",
            has_callback=False,
        )
        assert btn.enabled is False
        assert btn.has_callback is False

    def test_module_button_frozen(self):
        """Testa que ModuleButton é imutável (frozen=True)."""
        btn = ModuleButton("Test", True, "info", True)
        with pytest.raises(AttributeError):
            btn.text = "Modified"


class TestBuildModuleButtons:
    """Testes para build_module_buttons."""

    def test_build_module_buttons_all_enabled(self):
        """Testa construção com todos os módulos habilitados."""
        buttons = build_module_buttons(
            has_clientes=True,
            has_cashflow=True,
            has_anvisa=True,
            has_farmacia_popular=True,
            has_sngpc=True,
            has_sifap=True,
        )

        assert len(buttons) == 6

        # Verificar ordem e configuração
        assert buttons[0].text == "Clientes"
        assert buttons[0].enabled is True
        assert buttons[0].bootstyle == "info"
        assert buttons[0].has_callback is True

        assert buttons[1].text == "Fluxo de Caixa"
        assert buttons[1].enabled is True
        assert buttons[1].bootstyle == "warning"
        assert buttons[1].has_callback is True

        assert buttons[2].text == "Anvisa"
        assert buttons[2].enabled is True
        assert buttons[2].bootstyle == "secondary"
        assert buttons[2].has_callback is True

        assert buttons[3].text == "Farmácia Popular"
        assert buttons[3].enabled is True
        assert buttons[3].bootstyle == "secondary"
        assert buttons[3].has_callback is True

        assert buttons[4].text == "Sngpc"
        assert buttons[4].enabled is True
        assert buttons[4].bootstyle == "secondary"
        assert buttons[4].has_callback is True

        assert buttons[5].text == "Sifap"
        assert buttons[5].enabled is True
        assert buttons[5].bootstyle == "secondary"
        assert buttons[5].has_callback is True

    def test_build_module_buttons_defaults(self):
        """Testa construção com valores padrão."""
        buttons = build_module_buttons()

        assert len(buttons) == 6

        # Clientes habilitado por padrão
        assert buttons[0].text == "Clientes"
        assert buttons[0].enabled is True

        # Fluxo de Caixa desabilitado por padrão
        assert buttons[1].text == "Fluxo de Caixa"
        assert buttons[1].enabled is False
        assert buttons[1].has_callback is False

        # Módulos em desenvolvimento desabilitados por padrão
        assert buttons[2].text == "Anvisa"
        assert buttons[2].enabled is False
        assert buttons[2].has_callback is False

        assert buttons[3].text == "Farmácia Popular"
        assert buttons[3].enabled is False
        assert buttons[3].has_callback is False

        assert buttons[4].text == "Sngpc"
        assert buttons[4].enabled is False
        assert buttons[4].has_callback is False

        assert buttons[5].text == "Sifap"
        assert buttons[5].enabled is False
        assert buttons[5].has_callback is False

    def test_build_module_buttons_clientes_disabled(self):
        """Testa construção sem módulo Clientes."""
        buttons = build_module_buttons(has_clientes=False)

        # Verifica que não há botão Clientes
        texts = [b.text for b in buttons]
        assert "Clientes" not in texts
        assert len(buttons) == 5

        # Fluxo de Caixa deve ser o primeiro
        assert buttons[0].text == "Fluxo de Caixa"

    @pytest.mark.skip(reason="Ação 'senhas' removida – migração CTK")
    def test_build_module_buttons_senhas_disabled(self):
        """Testa construção sem módulo Senhas."""
        buttons = build_module_buttons(has_senhas=False)

        texts = [b.text for b in buttons]
        assert "Senhas" not in texts
        assert len(buttons) == 7

        # Clientes ainda é o primeiro
        assert buttons[0].text == "Clientes"
        # Auditoria é o segundo
        assert buttons[1].text == "Auditoria"

    @pytest.mark.skip(reason="Ação 'auditoria' removida – migração CTK")
    def test_build_module_buttons_auditoria_disabled(self):
        """Testa construção sem módulo Auditoria."""
        buttons = build_module_buttons(has_auditoria=False)

        texts = [b.text for b in buttons]
        assert "Auditoria" not in texts
        assert len(buttons) == 7

        assert buttons[0].text == "Clientes"
        assert buttons[1].text == "Senhas"
        assert buttons[2].text == "Fluxo de Caixa"

    def test_build_module_buttons_only_core_modules(self):
        """Testa construção apenas com módulos principais habilitados."""
        buttons = build_module_buttons(
            has_clientes=True,
            has_cashflow=False,
            has_anvisa=False,
            has_farmacia_popular=False,
            has_sngpc=False,
            has_sifap=False,
        )

        # Total sempre 6 (módulos em dev sempre aparecem)
        assert len(buttons) == 6

        # Primeiro habilitado
        assert buttons[0].enabled is True  # Clientes

        # Resto desabilitado
        assert buttons[1].enabled is False  # Fluxo de Caixa
        assert buttons[2].enabled is False  # Anvisa
        assert buttons[3].enabled is False  # Farmácia Popular
        assert buttons[4].enabled is False  # Sngpc
        assert buttons[5].enabled is False  # Sifap

    def test_build_module_buttons_all_core_disabled(self):
        """Testa construção sem nenhum módulo principal."""
        buttons = build_module_buttons(
            has_clientes=False,
        )

        # Apenas módulos em desenvolvimento
        assert len(buttons) == 5
        assert buttons[0].text == "Fluxo de Caixa"
        assert buttons[1].text == "Anvisa"
        assert buttons[2].text == "Farmácia Popular"
        assert buttons[3].text == "Sngpc"
        assert buttons[4].text == "Sifap"


class TestCalculateModuleButtonStyle:
    """Testes para calculate_module_button_style."""

    def test_calculate_module_button_style_default(self):
        """Testa estilo padrão sem nenhuma flag."""
        result = calculate_module_button_style()
        assert result == "secondary"

    def test_calculate_module_button_style_highlight(self):
        """Testa estilo com highlight=True."""
        result = calculate_module_button_style(highlight=True)
        assert result == "success"

    def test_calculate_module_button_style_yellow(self):
        """Testa estilo com yellow=True."""
        result = calculate_module_button_style(yellow=True)
        assert result == "warning"

    def test_calculate_module_button_style_bootstyle_explicit(self):
        """Testa estilo com bootstyle explícito."""
        result = calculate_module_button_style(bootstyle="danger")
        assert result == "danger"

    def test_calculate_module_button_style_priority_bootstyle_over_yellow(self):
        """Testa que bootstyle tem prioridade sobre yellow."""
        result = calculate_module_button_style(yellow=True, bootstyle="info")
        assert result == "info"

    def test_calculate_module_button_style_priority_bootstyle_over_highlight(self):
        """Testa que bootstyle tem prioridade sobre highlight."""
        result = calculate_module_button_style(highlight=True, bootstyle="info")
        assert result == "info"

    def test_calculate_module_button_style_priority_yellow_over_highlight(self):
        """Testa que yellow tem prioridade sobre highlight."""
        result = calculate_module_button_style(highlight=True, yellow=True)
        assert result == "warning"

    def test_calculate_module_button_style_priority_all_flags(self):
        """Testa hierarquia completa: bootstyle > yellow > highlight."""
        result = calculate_module_button_style(
            highlight=True,
            yellow=True,
            bootstyle="danger",
        )
        assert result == "danger"

    def test_calculate_module_button_style_yellow_only(self):
        """Testa yellow sem outras flags."""
        result = calculate_module_button_style(
            highlight=False,
            yellow=True,
            bootstyle=None,
        )
        assert result == "warning"

    def test_calculate_module_button_style_highlight_only(self):
        """Testa highlight sem outras flags."""
        result = calculate_module_button_style(
            highlight=True,
            yellow=False,
            bootstyle=None,
        )
        assert result == "success"

    def test_calculate_module_button_style_all_false(self):
        """Testa com todas as flags explicitamente False/None."""
        result = calculate_module_button_style(
            highlight=False,
            yellow=False,
            bootstyle=None,
        )
        assert result == "secondary"
