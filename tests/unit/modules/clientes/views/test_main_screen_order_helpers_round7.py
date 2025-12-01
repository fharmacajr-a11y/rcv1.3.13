# -*- coding: utf-8 -*-

"""Testes unitários para helpers de ordenação de main_screen.

Round 7 - Fase 1: Testes para lógica de normalização de rótulos e opções de ordenação.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

from src.modules.clientes.views.main_screen_helpers import (
    DEFAULT_ORDER_LABEL,
    ORDER_CHOICES,
    ORDER_LABEL_CNPJ,
    ORDER_LABEL_ID_ASC,
    ORDER_LABEL_ID_DESC,
    ORDER_LABEL_NOME,
    ORDER_LABEL_RAZAO,
    ORDER_LABEL_UPDATED_OLD,
    ORDER_LABEL_UPDATED_RECENT,
    normalize_order_choices,
    normalize_order_label,
)


class TestNormalizeOrderLabel:
    """Testes para normalize_order_label."""

    def test_normalize_order_label_aliases(self) -> None:
        """Testa normalização de aliases conhecidos para labels canônicos."""
        assert normalize_order_label("Razao Social (A->Z)") == ORDER_LABEL_RAZAO
        assert normalize_order_label("CNPJ (A->Z)") == ORDER_LABEL_CNPJ
        assert normalize_order_label("Nome (A->Z)") == ORDER_LABEL_NOME
        assert normalize_order_label("Ultima Alteracao (mais recente)") == ORDER_LABEL_UPDATED_RECENT
        assert normalize_order_label("Ultima Alteracao (mais antiga)") == ORDER_LABEL_UPDATED_OLD
        assert normalize_order_label("ID (1->9)") == ORDER_LABEL_ID_ASC
        assert normalize_order_label("ID (9->1)") == ORDER_LABEL_ID_DESC

    def test_normalize_order_label_with_arrow_variants(self) -> None:
        """Testa que ambos os formatos de seta (-> e →) funcionam."""
        # Formato com ->
        assert normalize_order_label("ID (1->9)") == ORDER_LABEL_ID_ASC
        assert normalize_order_label("ID (9->1)") == ORDER_LABEL_ID_DESC

        # Formato com → (já é o canônico)
        assert normalize_order_label("ID (1→9)") == ORDER_LABEL_ID_ASC
        assert normalize_order_label("ID (9→1)") == ORDER_LABEL_ID_DESC

    def test_normalize_order_label_generic_and_empty(self) -> None:
        """Testa casos genéricos e de borda (strings vazias, None, etc)."""
        assert normalize_order_label("  Outro label  ") == "Outro label"
        assert normalize_order_label("") == ""
        assert normalize_order_label(None) == ""

    def test_normalize_order_label_preserves_unknown_labels(self) -> None:
        """Testa que labels desconhecidos são preservados (apenas com strip)."""
        assert normalize_order_label("Custom Label") == "Custom Label"
        assert normalize_order_label("  Custom with spaces  ") == "Custom with spaces"

    def test_normalize_order_label_with_whitespace(self) -> None:
        """Testa que whitespace é tratado corretamente."""
        assert normalize_order_label("   ") == ""
        assert normalize_order_label("\t\n") == ""


class TestNormalizeOrderChoices:
    """Testes para normalize_order_choices."""

    def test_normalize_order_choices_normalizes_keys(self) -> None:
        """Testa que normalize_order_choices normaliza as chaves do dicionário."""
        raw: Dict[str, Tuple[Optional[str], bool]] = {
            "Razao Social (A->Z)": ("razao_social", False),
            "ID (9->1)": ("id", True),
            "Custom": ("custom_field", False),
        }

        normalized = normalize_order_choices(raw)

        # Verifica que as chaves foram normalizadas
        assert ORDER_LABEL_RAZAO in normalized
        assert ORDER_LABEL_ID_DESC in normalized
        assert "Custom" in normalized

        # Verifica que os valores foram preservados
        assert normalized[ORDER_LABEL_RAZAO] == ("razao_social", False)
        assert normalized[ORDER_LABEL_ID_DESC] == ("id", True)
        assert normalized["Custom"] == ("custom_field", False)

    def test_normalize_order_choices_preserves_values(self) -> None:
        """Testa que os valores (campo, reverse) não são alterados."""
        raw: Dict[str, Tuple[Optional[str], bool]] = {
            "CNPJ (A->Z)": ("cnpj", False),
            "ID (1->9)": ("id", False),
            "Ultima Alteracao (mais antiga)": ("ultima_alteracao", True),
        }

        normalized = normalize_order_choices(raw)

        assert normalized[ORDER_LABEL_CNPJ] == ("cnpj", False)
        assert normalized[ORDER_LABEL_ID_ASC] == ("id", False)
        assert normalized[ORDER_LABEL_UPDATED_OLD] == ("ultima_alteracao", True)

    def test_normalize_order_choices_empty_dict(self) -> None:
        """Testa que um dicionário vazio retorna um dicionário vazio."""
        assert normalize_order_choices({}) == {}

    def test_normalize_order_choices_with_mixed_keys(self) -> None:
        """Testa normalização com mix de aliases e labels já canônicos."""
        raw: Dict[str, Tuple[Optional[str], bool]] = {
            "Razao Social (A->Z)": ("razao_social", False),
            ORDER_LABEL_CNPJ: ("cnpj", False),  # Já canônico
            "Nome (A->Z)": ("nome", False),
        }

        normalized = normalize_order_choices(raw)

        assert ORDER_LABEL_RAZAO in normalized
        assert ORDER_LABEL_CNPJ in normalized
        assert ORDER_LABEL_NOME in normalized
        assert len(normalized) == 3


class TestOrderChoicesConstants:
    """Testes de sanity check para as constantes ORDER_CHOICES e DEFAULT_ORDER_LABEL."""

    def test_default_order_choices_have_expected_keys(self) -> None:
        """Garante que o dicionário padrão ORDER_CHOICES contém as chaves esperadas."""
        keys = set(ORDER_CHOICES.keys())

        assert ORDER_LABEL_RAZAO in keys
        assert ORDER_LABEL_CNPJ in keys
        assert ORDER_LABEL_NOME in keys
        assert ORDER_LABEL_ID_ASC in keys
        assert ORDER_LABEL_ID_DESC in keys
        assert ORDER_LABEL_UPDATED_RECENT in keys
        assert ORDER_LABEL_UPDATED_OLD in keys

    def test_default_order_choices_values_are_tuples(self) -> None:
        """Verifica que todos os valores de ORDER_CHOICES são tuplas (campo, reverse)."""
        for label, value in ORDER_CHOICES.items():
            assert isinstance(value, tuple), f"Valor para '{label}' não é tupla"
            assert len(value) == 2, f"Valor para '{label}' não tem 2 elementos"
            field, reverse = value
            assert field is None or isinstance(field, str), f"Campo para '{label}' não é str ou None"
            assert isinstance(reverse, bool), f"Reverse para '{label}' não é bool"

    def test_default_order_label_is_in_order_choices(self) -> None:
        """Verifica que DEFAULT_ORDER_LABEL existe em ORDER_CHOICES."""
        assert DEFAULT_ORDER_LABEL in ORDER_CHOICES

    def test_default_order_label_is_razao_social(self) -> None:
        """Verifica que o padrão é ordenar por Razão Social."""
        assert DEFAULT_ORDER_LABEL == ORDER_LABEL_RAZAO

    def test_order_choices_razao_maps_correctly(self) -> None:
        """Verifica mapeamento específico de Razão Social."""
        assert ORDER_CHOICES[ORDER_LABEL_RAZAO] == ("razao_social", False)

    def test_order_choices_id_asc_and_desc(self) -> None:
        """Verifica que ID ascendente e descendente têm reverse correto."""
        assert ORDER_CHOICES[ORDER_LABEL_ID_ASC] == ("id", False)
        assert ORDER_CHOICES[ORDER_LABEL_ID_DESC] == ("id", True)

    def test_order_choices_updated_recent_and_old(self) -> None:
        """Verifica ordenação por última alteração (recente vs antiga)."""
        assert ORDER_CHOICES[ORDER_LABEL_UPDATED_RECENT] == ("ultima_alteracao", False)
        assert ORDER_CHOICES[ORDER_LABEL_UPDATED_OLD] == ("ultima_alteracao", True)


class TestOrderLabelConstants:
    """Testes para verificar que as constantes de label estão corretas."""

    def test_order_label_values_have_correct_format(self) -> None:
        """Verifica que os labels têm o formato esperado."""
        assert "Razão Social" in ORDER_LABEL_RAZAO
        assert "A→Z" in ORDER_LABEL_RAZAO

        assert "CNPJ" in ORDER_LABEL_CNPJ
        assert "A→Z" in ORDER_LABEL_CNPJ

        assert "Nome" in ORDER_LABEL_NOME
        assert "A→Z" in ORDER_LABEL_NOME

        assert "ID" in ORDER_LABEL_ID_ASC
        assert "1→9" in ORDER_LABEL_ID_ASC

        assert "ID" in ORDER_LABEL_ID_DESC
        assert "9→1" in ORDER_LABEL_ID_DESC

        assert "Última Alteração" in ORDER_LABEL_UPDATED_RECENT
        assert "mais recente" in ORDER_LABEL_UPDATED_RECENT

        assert "Última Alteração" in ORDER_LABEL_UPDATED_OLD
        assert "mais antiga" in ORDER_LABEL_UPDATED_OLD

    def test_all_labels_are_unique(self) -> None:
        """Verifica que todos os labels são únicos."""
        labels = [
            ORDER_LABEL_RAZAO,
            ORDER_LABEL_CNPJ,
            ORDER_LABEL_NOME,
            ORDER_LABEL_ID_ASC,
            ORDER_LABEL_ID_DESC,
            ORDER_LABEL_UPDATED_RECENT,
            ORDER_LABEL_UPDATED_OLD,
        ]
        assert len(labels) == len(set(labels)), "Há labels duplicados"
