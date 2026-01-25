# -*- coding: utf-8 -*-
"""Testes unitários para CTkDatePicker.

OBJETIVO: Validar widget customizado CTkDatePicker criado na migração CTK.
BASELINE: Respeita fallback de CustomTkinter (skip se não disponível).
"""

from __future__ import annotations

import tkinter as tk
from datetime import date, datetime

import pytest

# Importar via ctk_config para respeitar SSoT
from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk

# Skip todos os testes se CustomTkinter não estiver disponível
pytestmark = pytest.mark.skipif(
    not HAS_CUSTOMTKINTER or ctk is None,
    reason="CustomTkinter não disponível - CTkDatePicker requer CustomTkinter",
)


@pytest.fixture
def root():
    """Fixture para criar janela root Tkinter."""
    if HAS_CUSTOMTKINTER and ctk is not None:
        root_window = tk.Tk()
        root_window.withdraw()  # Não mostrar janela durante testes
        yield root_window
        root_window.destroy()
    else:
        yield None


class TestCTkDatePicker:
    """Testes para o widget CTkDatePicker."""

    def test_criacao_sem_excecao(self, root):
        """Test 1: Widget pode ser criado sem exceção."""
        from src.ui.widgets import CTkDatePicker

        # Criar widget com parâmetros default
        picker = CTkDatePicker(root)
        assert picker is not None
        assert isinstance(picker, ctk.CTkFrame)

    def test_criacao_com_dateformat_custom(self, root):
        """Test 2: Widget aceita formato customizado."""
        from src.ui.widgets import CTkDatePicker

        picker = CTkDatePicker(root, dateformat="%d/%m/%Y")
        assert picker.dateformat == "%d/%m/%Y"

    def test_get_retorna_string(self, root):
        """Test 3: get() retorna string formatada."""
        from src.ui.widgets import CTkDatePicker

        test_date = date(2026, 1, 25)
        picker = CTkDatePicker(root, startdate=test_date, dateformat="%Y-%m-%d")

        result = picker.get()
        assert isinstance(result, str)
        assert result == "2026-01-25"

    def test_get_date_retorna_date_object(self, root):
        """Test 4: get_date() retorna objeto date."""
        from src.ui.widgets import CTkDatePicker

        test_date = date(2026, 1, 25)
        picker = CTkDatePicker(root, startdate=test_date)

        result = picker.get_date()
        assert isinstance(result, date)
        assert result == test_date

    def test_set_com_date_object(self, root):
        """Test 5: set() aceita objeto date."""
        from src.ui.widgets import CTkDatePicker

        picker = CTkDatePicker(root, dateformat="%d/%m/%Y")
        new_date = date(2026, 3, 15)

        picker.set(new_date)

        assert picker.get_date() == new_date
        assert picker.get() == "15/03/2026"

    def test_set_com_string_valida(self, root):
        """Test 6: set() aceita string no formato correto."""
        from src.ui.widgets import CTkDatePicker

        picker = CTkDatePicker(root, dateformat="%d/%m/%Y")

        picker.set("20/12/2025")

        assert picker.get() == "20/12/2025"
        assert picker.get_date() == date(2025, 12, 20)

    def test_set_com_string_invalida_nao_crash(self, root):
        """Test 7: set() com string inválida não causa exceção."""
        from src.ui.widgets import CTkDatePicker

        picker = CTkDatePicker(root, dateformat="%Y-%m-%d", startdate=date(2026, 1, 25))
        original_date = picker.get_date()

        # Tentar set com string inválida (não deve crashar)
        picker.set("data-invalida")

        # Data deve permanecer inalterada
        assert picker.get_date() == original_date

    def test_validate_entry_com_input_invalido(self, root):
        """Test 8: _validate_entry restaura data anterior se input inválido."""
        from src.ui.widgets import CTkDatePicker

        picker = CTkDatePicker(root, dateformat="%d/%m/%Y", startdate=date(2026, 1, 25))

        # Simular input inválido no Entry
        picker.entry_var.set("99/99/9999")
        picker._validate_entry()

        # Deve restaurar para data válida anterior
        assert picker.get() == "25/01/2026"
        assert picker.get_date() == date(2026, 1, 25)

    def test_validate_entry_com_input_vazio_nao_crash(self, root):
        """Test 9: _validate_entry com string vazia não causa exceção."""
        from src.ui.widgets import CTkDatePicker

        picker = CTkDatePicker(root, dateformat="%d/%m/%Y", startdate=date(2026, 1, 25))
        original_date = picker.get_date()

        # Simular input vazio
        picker.entry_var.set("")
        picker._validate_entry()

        # Não deve crashar, data permanece
        assert picker.get_date() == original_date

    def test_startdate_default_e_hoje(self, root):
        """Test 10: startdate default é date.today()."""
        from src.ui.widgets import CTkDatePicker

        picker = CTkDatePicker(root)
        today = date.today()

        # Deve inicializar com data de hoje
        assert picker.get_date() == today

    def test_command_callback_chamado(self, root):
        """Test 11: command callback é invocado ao validar entry com data diferente."""
        from src.ui.widgets import CTkDatePicker

        callback_called = []

        def on_date_selected(selected_date: date):
            callback_called.append(selected_date)

        # Criar picker com data inicial específica
        initial_date = date(2026, 1, 1)
        picker = CTkDatePicker(root, startdate=initial_date, dateformat="%Y-%m-%d", command=on_date_selected)

        # Simular entrada manual de nova data no Entry
        new_date_str = "2026-06-10"
        picker.entry_var.set(new_date_str)
        picker._validate_entry()

        # Callback deve ter sido chamado com a nova data
        assert len(callback_called) == 1
        assert callback_called[0] == date(2026, 6, 10)

    def test_formatos_diferentes(self, root):
        """Test 12: Widget suporta diferentes formatos de data."""
        from src.ui.widgets import CTkDatePicker

        formatos = [
            ("%Y-%m-%d", date(2026, 1, 25), "2026-01-25"),
            ("%d/%m/%Y", date(2026, 1, 25), "25/01/2026"),
            ("%m/%d/%Y", date(2026, 1, 25), "01/25/2026"),
            ("%Y%m%d", date(2026, 1, 25), "20260125"),
        ]

        for fmt, test_date, expected_str in formatos:
            picker = CTkDatePicker(root, dateformat=fmt, startdate=test_date)
            assert picker.get() == expected_str
            assert picker.get_date() == test_date
