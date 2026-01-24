# -*- coding: utf-8 -*-
"""Testes do click-to-chat WhatsApp (FASE 3.9).

Valida normalização de telefone, geração de URL e clique na coluna WhatsApp.
"""

from __future__ import annotations

import logging
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.modules.clientes_v2.view import ClientesV2Frame

log = logging.getLogger(__name__)


class TestWhatsAppClickToChat:
    """Testes do click-to-chat WhatsApp."""

    # ===== Testes de normalização de telefone =====

    def test_normalize_phone_basic_format(self) -> None:
        """Testa normalização com formato básico brasileiro.

        FASE 3.9: (11) 98765-4321 -> 5511987654321
        """
        # Act
        result = ClientesV2Frame._normalize_phone_for_whatsapp("(11) 98765-4321")

        # Assert
        assert result == "5511987654321"

    def test_normalize_phone_with_plus_55(self) -> None:
        """Testa normalização com +55 já presente.

        FASE 3.9: +55 11 98765-4321 -> 5511987654321
        """
        # Act
        result = ClientesV2Frame._normalize_phone_for_whatsapp("+55 11 98765-4321")

        # Assert
        assert result == "5511987654321"

    def test_normalize_phone_only_digits(self) -> None:
        """Testa normalização com apenas dígitos sem 55.

        FASE 3.9: 11987654321 -> 5511987654321
        """
        # Act
        result = ClientesV2Frame._normalize_phone_for_whatsapp("11987654321")

        # Assert
        assert result == "5511987654321"

    def test_normalize_phone_already_with_55(self) -> None:
        """Testa normalização com 55 já presente (sem +).

        FASE 3.9: 5511987654321 -> 5511987654321 (não duplica)
        """
        # Act
        result = ClientesV2Frame._normalize_phone_for_whatsapp("5511987654321")

        # Assert
        assert result == "5511987654321"

    def test_normalize_phone_with_spaces_and_dashes(self) -> None:
        """Testa normalização com espaços e traços.

        FASE 3.9: (11) 9 8765-4321 -> 5511987654321
        """
        # Act
        result = ClientesV2Frame._normalize_phone_for_whatsapp("(11) 9 8765-4321")

        # Assert
        assert result == "5511987654321"

    def test_normalize_phone_empty_string_returns_none(self) -> None:
        """Testa normalização com string vazia.

        FASE 3.9: '' -> None
        """
        # Act
        result = ClientesV2Frame._normalize_phone_for_whatsapp("")

        # Assert
        assert result is None

    def test_normalize_phone_whitespace_returns_none(self) -> None:
        """Testa normalização com apenas espaços.

        FASE 3.9: '   ' -> None
        """
        # Act
        result = ClientesV2Frame._normalize_phone_for_whatsapp("   ")

        # Assert
        assert result is None

    def test_normalize_phone_no_digits_returns_none(self) -> None:
        """Testa normalização com texto sem dígitos.

        FASE 3.9: 'abc-def' -> None
        """
        # Act
        result = ClientesV2Frame._normalize_phone_for_whatsapp("abc-def")

        # Assert
        assert result is None

    def test_normalize_phone_too_short_returns_none(self) -> None:
        """Testa normalização com número muito curto.

        FASE 3.9: '123' -> None (menos de 12 dígitos após adicionar 55)
        """
        # Act
        result = ClientesV2Frame._normalize_phone_for_whatsapp("123")

        # Assert
        assert result is None

    def test_normalize_phone_landline_format(self) -> None:
        """Testa normalização com telefone fixo.

        FASE 3.9: (11) 3456-7890 -> 551134567890
        """
        # Act
        result = ClientesV2Frame._normalize_phone_for_whatsapp("(11) 3456-7890")

        # Assert
        assert result == "551134567890"  # 12 dígitos total (55 + DDD + 8 dígitos)
        # Note: Número fixo tem 10 dígitos (DDD + 8 dígitos)

    def test_normalize_phone_with_parentheses_only(self) -> None:
        """Testa normalização com parênteses mas sem hífen.

        FASE 3.9: (11)987654321 -> 5511987654321
        """
        # Act
        result = ClientesV2Frame._normalize_phone_for_whatsapp("(11)987654321")

        # Assert
        assert result == "5511987654321"

    # ===== Testes de geração de URL =====

    def test_whatsapp_url_generation(self) -> None:
        """Testa geração de URL do WhatsApp.

        FASE 3.9: 5511987654321 -> https://wa.me/5511987654321
        """
        # Act
        url = ClientesV2Frame._whatsapp_url("5511987654321")

        # Assert
        assert url == "https://wa.me/5511987654321"

    def test_whatsapp_url_with_different_number(self) -> None:
        """Testa geração de URL com número diferente.

        FASE 3.9: 5521123456789 -> https://wa.me/5521123456789
        """
        # Act
        url = ClientesV2Frame._whatsapp_url("5521123456789")

        # Assert
        assert url == "https://wa.me/5521123456789"

    # ===== Testes de clique na coluna WhatsApp =====

    def test_click_on_whatsapp_column_opens_url(self, root: Any) -> None:
        """Testa clique na coluna WhatsApp que abre navegador.

        FASE 3.9: Validar que clique na coluna WhatsApp abre wa.me.
        """
        # Arrange
        frame = ClientesV2Frame(root)
        frame.app = MagicMock()

        # Inserir dados de teste na tree
        frame.tree.insert(
            "",
            "end",
            values=(
                "1",
                "EMPRESA TESTE LTDA",
                "12.345.678/0001-90",
                "Empresa Teste",
                "(11) 98765-4321",
                "Ativo",
                "Observações",
                "2024-01-01",
            ),
        )

        # Mock webbrowser.open
        with patch("webbrowser.open") as mock_open:
            # Criar evento fake para coluna WhatsApp (#5)
            mock_event = MagicMock()
            mock_event.x = 500  # Posição X aproximada da coluna WhatsApp
            mock_event.y = 50  # Posição Y de uma linha

            # Mock identify methods
            frame.tree.identify_region = MagicMock(return_value="cell")
            frame.tree.identify_row = MagicMock(return_value=frame.tree.get_children()[0])
            frame.tree.identify_column = MagicMock(return_value="#5")

            # Act
            frame._on_tree_click(mock_event)

            # Assert
            mock_open.assert_called_once_with("https://wa.me/5511987654321")

    def test_click_on_other_column_does_nothing(self, root: Any) -> None:
        """Testa clique em outra coluna (não WhatsApp).

        FASE 3.9: Validar que clique em outras colunas não abre navegador.
        """
        # Arrange
        frame = ClientesV2Frame(root)
        frame.app = MagicMock()

        # Inserir dados de teste
        frame.tree.insert(
            "",
            "end",
            values=(
                "1",
                "EMPRESA TESTE LTDA",
                "12.345.678/0001-90",
                "Empresa Teste",
                "(11) 98765-4321",
                "Ativo",
                "Observações",
                "2024-01-01",
            ),
        )

        # Mock webbrowser.open
        with patch("webbrowser.open") as mock_open:
            # Criar evento fake para coluna ID (#1)
            mock_event = MagicMock()
            mock_event.x = 50
            mock_event.y = 50

            # Mock identify methods
            frame.tree.identify_region = MagicMock(return_value="cell")
            frame.tree.identify_row = MagicMock(return_value=frame.tree.get_children()[0])
            frame.tree.identify_column = MagicMock(return_value="#1")

            # Act
            frame._on_tree_click(mock_event)

            # Assert
            mock_open.assert_not_called()

    def test_click_on_empty_whatsapp_does_nothing(self, root: Any) -> None:
        """Testa clique na coluna WhatsApp com valor vazio.

        FASE 3.9: Validar que campo vazio não tenta abrir navegador.
        """
        # Arrange
        frame = ClientesV2Frame(root)
        frame.app = MagicMock()

        # Inserir dados com WhatsApp vazio
        frame.tree.insert(
            "",
            "end",
            values=(
                "1",
                "EMPRESA SEM WHATSAPP",
                "12.345.678/0001-90",
                "Empresa",
                "",  # WhatsApp vazio
                "Ativo",
                "Observações",
                "2024-01-01",
            ),
        )

        # Mock webbrowser.open
        with patch("webbrowser.open") as mock_open:
            # Criar evento fake
            mock_event = MagicMock()
            mock_event.x = 500
            mock_event.y = 50

            # Mock identify methods
            frame.tree.identify_region = MagicMock(return_value="cell")
            frame.tree.identify_row = MagicMock(return_value=frame.tree.get_children()[0])
            frame.tree.identify_column = MagicMock(return_value="#5")

            # Act
            frame._on_tree_click(mock_event)

            # Assert
            mock_open.assert_not_called()

    def test_click_on_invalid_region_does_nothing(self, root: Any) -> None:
        """Testa clique fora de uma célula.

        FASE 3.9: Validar que clique em região não-cell é ignorado.
        """
        # Arrange
        frame = ClientesV2Frame(root)
        frame.app = MagicMock()

        # Mock webbrowser.open
        with patch("webbrowser.open") as mock_open:
            # Criar evento fake para região de cabeçalho
            mock_event = MagicMock()
            mock_event.x = 500
            mock_event.y = 10

            # Mock identify_region para retornar "heading"
            frame.tree.identify_region = MagicMock(return_value="heading")

            # Act
            frame._on_tree_click(mock_event)

            # Assert
            mock_open.assert_not_called()

    def test_click_handles_normalize_failure_gracefully(self, root: Any) -> None:
        """Testa tratamento quando normalização retorna None.

        FASE 3.9: Validar que número inválido não causa erro.
        """
        # Arrange
        frame = ClientesV2Frame(root)
        frame.app = MagicMock()

        # Inserir dados com número inválido
        frame.tree.insert(
            "",
            "end",
            values=(
                "1",
                "EMPRESA TESTE",
                "12.345.678/0001-90",
                "Empresa",
                "abc123",  # Número inválido
                "Ativo",
                "Observações",
                "2024-01-01",
            ),
        )

        # Mock webbrowser.open
        with patch("webbrowser.open") as mock_open:
            # Criar evento fake
            mock_event = MagicMock()
            mock_event.x = 500
            mock_event.y = 50

            # Mock identify methods
            frame.tree.identify_region = MagicMock(return_value="cell")
            frame.tree.identify_row = MagicMock(return_value=frame.tree.get_children()[0])
            frame.tree.identify_column = MagicMock(return_value="#5")

            # Act (não deve lançar exceção)
            try:
                frame._on_tree_click(mock_event)
            except Exception as e:
                pytest.fail(f"Clique com número inválido lançou exceção: {e}")

            # Assert
            mock_open.assert_not_called()

    def test_click_with_multiple_formats_in_tree(self, root: Any) -> None:
        """Testa clique com diferentes formatos de telefone.

        FASE 3.9: Validar que todos os formatos são normalizados corretamente.
        """
        # Arrange
        frame = ClientesV2Frame(root)
        frame.app = MagicMock()

        # Inserir múltiplos formatos
        test_cases = [
            ("(11) 98765-4321", "5511987654321"),
            ("+55 11 98765-4321", "5511987654321"),
            ("11987654321", "5511987654321"),
            ("5511987654321", "5511987654321"),
        ]

        for phone_raw, phone_expected in test_cases:
            item_id = frame.tree.insert(
                "",
                "end",
                values=("1", "EMPRESA", "12.345.678/0001-90", "Nome", phone_raw, "Ativo", "Obs", "2024-01-01"),
            )

            # Mock webbrowser.open
            with patch("webbrowser.open") as mock_open:
                # Criar evento fake
                mock_event = MagicMock()
                mock_event.x = 500
                mock_event.y = 50

                # Mock identify methods
                frame.tree.identify_region = MagicMock(return_value="cell")
                frame.tree.identify_row = MagicMock(return_value=item_id)
                frame.tree.identify_column = MagicMock(return_value="#5")

                # Act
                frame._on_tree_click(mock_event)

                # Assert
                expected_url = f"https://wa.me/{phone_expected}"
                mock_open.assert_called_once_with(expected_url)
