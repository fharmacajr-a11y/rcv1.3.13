# -*- coding: utf-8 -*-
"""Testes unitários para client_form_ui_builders.

Testa os builders de UI extraídos do client_form para garantir
que a criação padronizada de widgets funciona corretamente.

Refatoração: TEST-001 (client_form_adapters + client_form_ui_builders)
"""

from __future__ import annotations

import sys
import tkinter as tk
from typing import TYPE_CHECKING

import pytest

from tests.helpers.skip_conditions import SKIP_PY313_TKINTER
from src.modules.clientes.forms.client_form_ui_builders import (
    apply_light_selection,
    bind_dirty_tracking,
    create_button_bar,
    create_labeled_entry,
    create_labeled_text,
    create_status_dropdown,
)

if TYPE_CHECKING:
    pass

# Skip todos os testes de Tkinter em Windows + Python 3.13 devido a bug conhecido
# Usa decorator centralizado para manutenção fácil quando o bug for corrigido
skip_tk_windows_313 = SKIP_PY313_TKINTER


# =============================================================================
# Fixtures de Setup
# =============================================================================


@pytest.fixture()
def tk_root() -> tk.Tk:
    """Cria uma janela Tkinter para testes."""
    if sys.platform == "win32" and sys.version_info >= (3, 13):
        pytest.skip("Tkinter bug no Python 3.13+ em Windows (ver skip_conditions.SKIP_PY313_TKINTER)")
    root = tk.Tk()
    root.withdraw()  # Não mostrar janela
    yield root
    try:
        root.destroy()
    except tk.TclError:
        pass


# =============================================================================
# Testes para create_labeled_entry
# =============================================================================


class TestCreateLabeledEntry:
    """Testes para a função create_labeled_entry."""

    @skip_tk_windows_313
    def test_creates_label_and_entry(self, tk_root: tk.Tk) -> None:
        """create_labeled_entry deve retornar tupla (Label, Entry, next_row)."""
        label, entry, next_row = create_labeled_entry(
            parent=tk_root,
            label_text="Razão Social:",
            row_idx=0,
        )

        assert isinstance(label, tk.Label)
        assert hasattr(entry, "get")  # Entry-like widget
        assert next_row == 2  # row_idx + 2

    @skip_tk_windows_313
    def test_label_has_correct_text(self, tk_root: tk.Tk) -> None:
        """Label deve ter texto correto."""
        label, _entry, _next_row = create_labeled_entry(
            parent=tk_root,
            label_text="CNPJ:",
            row_idx=0,
        )

        assert label.cget("text") == "CNPJ:"

    @skip_tk_windows_313
    def test_next_row_calculation(self, tk_root: tk.Tk) -> None:
        """next_row deve ser row_idx + 2."""
        _label, _entry, next_row = create_labeled_entry(
            parent=tk_root,
            label_text="Nome:",
            row_idx=5,
        )

        assert next_row == 7

    @skip_tk_windows_313
    def test_custom_column(self, tk_root: tk.Tk) -> None:
        """Deve aceitar coluna customizada."""
        label, entry, next_row = create_labeled_entry(
            parent=tk_root,
            label_text="WhatsApp:",
            row_idx=0,
            column=1,
        )

        assert isinstance(label, tk.Label)
        assert hasattr(entry, "get")
        assert next_row == 2


# =============================================================================
# Testes para create_labeled_text
# =============================================================================


class TestCreateLabeledText:
    """Testes para a função create_labeled_text."""

    @skip_tk_windows_313
    def test_creates_label_and_text_widget(self, tk_root: tk.Tk) -> None:
        """create_labeled_text deve retornar tupla (Label, Text, text_row, next_row)."""
        label, text_widget, text_row, next_row = create_labeled_text(
            parent=tk_root,
            label_text="Observações:",
            row_idx=0,
        )

        assert isinstance(label, tk.Label)
        assert isinstance(text_widget, tk.Text)
        assert text_row == 1
        assert next_row == 2

    @skip_tk_windows_313
    def test_label_has_correct_text(self, tk_root: tk.Tk) -> None:
        """Label deve ter texto correto."""
        label, _text, _text_row, _next_row = create_labeled_text(
            parent=tk_root,
            label_text="Endereço:",
            row_idx=0,
        )

        assert label.cget("text") == "Endereço:"

    @skip_tk_windows_313
    def test_text_widget_height(self, tk_root: tk.Tk) -> None:
        """Text widget deve ter altura configurada."""
        _label, text_widget, _text_row, _next_row = create_labeled_text(
            parent=tk_root,
            label_text="Observações:",
            row_idx=0,
            height=10,
        )

        # Text widget criado com height=10
        assert text_widget.cget("height") == 10

    @skip_tk_windows_313
    def test_text_widget_width(self, tk_root: tk.Tk) -> None:
        """Text widget deve ter largura configurada."""
        _label, text_widget, _text_row, _next_row = create_labeled_text(
            parent=tk_root,
            label_text="Observações:",
            row_idx=0,
            width=60,
        )

        # Text widget criado com width=60
        assert text_widget.cget("width") == 60


# =============================================================================
# Testes para create_status_dropdown
# =============================================================================


class TestCreateStatusDropdown:
    """Testes para a função create_status_dropdown."""

    @skip_tk_windows_313
    def test_creates_frame_combobox_and_button(self, tk_root: tk.Tk) -> None:
        """create_status_dropdown deve retornar (frame, combo, var, button)."""
        callback_called = []

        def on_senhas() -> None:
            callback_called.append(True)

        frame, combo, var, btn = create_status_dropdown(
            parent=tk_root,
            label_text="Status:",
            status_choices=["ATIVO", "INATIVO"],
            on_senhas_clicked=on_senhas,
        )

        assert hasattr(frame, "winfo_class")  # Frame-like
        assert hasattr(combo, "get")  # Combobox-like
        assert isinstance(var, tk.StringVar)
        assert hasattr(btn, "invoke")  # Button-like

    @skip_tk_windows_313
    def test_combobox_has_values(self, tk_root: tk.Tk) -> None:
        """Combobox deve ter valores configurados."""
        _frame, combo, _var, _btn = create_status_dropdown(
            parent=tk_root,
            label_text="Status:",
            status_choices=["ATIVO", "INATIVO", "SUSPENSO"],
            on_senhas_clicked=lambda: None,
        )

        values = combo.cget("values")
        assert "ATIVO" in values
        assert "INATIVO" in values
        assert "SUSPENSO" in values

    @skip_tk_windows_313
    def test_button_callback_works(self, tk_root: tk.Tk) -> None:
        """Botão Senhas deve chamar callback ao ser invocado."""
        callback_called = []

        def on_senhas() -> None:
            callback_called.append(True)

        _frame, _combo, _var, btn = create_status_dropdown(
            parent=tk_root,
            label_text="Status:",
            status_choices=["ATIVO"],
            on_senhas_clicked=on_senhas,
        )

        btn.invoke()

        assert len(callback_called) == 1

    @skip_tk_windows_313
    def test_string_var_initial_value(self, tk_root: tk.Tk) -> None:
        """StringVar deve ter valor inicial vazio."""
        _frame, _combo, var, _btn = create_status_dropdown(
            parent=tk_root,
            label_text="Status:",
            status_choices=["ATIVO", "INATIVO"],
            on_senhas_clicked=lambda: None,
        )

        assert var.get() == ""


# =============================================================================
# Testes para create_button_bar
# =============================================================================


class TestCreateButtonBar:
    """Testes para a função create_button_bar."""

    @skip_tk_windows_313
    def test_creates_four_buttons(self, tk_root: tk.Tk) -> None:
        """create_button_bar deve retornar dict com 4 botões."""
        buttons = create_button_bar(
            parent=tk_root,
            on_save=lambda: None,
            on_save_and_upload=lambda: None,
            on_cartao_cnpj=lambda: None,
            on_cancel=lambda: None,
        )

        assert "save" in buttons
        assert "upload" in buttons
        assert "cartao_cnpj" in buttons
        assert "cancel" in buttons

    @skip_tk_windows_313
    def test_save_button_callback(self, tk_root: tk.Tk) -> None:
        """Botão Salvar deve chamar callback correto."""
        save_called = []

        def on_save() -> None:
            save_called.append(True)

        buttons = create_button_bar(
            parent=tk_root,
            on_save=on_save,
            on_save_and_upload=lambda: None,
            on_cartao_cnpj=lambda: None,
            on_cancel=lambda: None,
        )

        buttons["save"].invoke()

        assert len(save_called) == 1

    @skip_tk_windows_313
    def test_upload_button_callback(self, tk_root: tk.Tk) -> None:
        """Botão Upload deve chamar callback correto."""
        upload_called = []

        def on_upload() -> None:
            upload_called.append(True)

        buttons = create_button_bar(
            parent=tk_root,
            on_save=lambda: None,
            on_save_and_upload=on_upload,
            on_cartao_cnpj=lambda: None,
            on_cancel=lambda: None,
        )

        buttons["upload"].invoke()

        assert len(upload_called) == 1

    @skip_tk_windows_313
    def test_cartao_cnpj_button_callback(self, tk_root: tk.Tk) -> None:
        """Botão Cartão CNPJ deve chamar callback correto."""
        cartao_called = []

        def on_cartao() -> None:
            cartao_called.append(True)

        buttons = create_button_bar(
            parent=tk_root,
            on_save=lambda: None,
            on_save_and_upload=lambda: None,
            on_cartao_cnpj=on_cartao,
            on_cancel=lambda: None,
        )

        buttons["cartao_cnpj"].invoke()

        assert len(cartao_called) == 1

    @skip_tk_windows_313
    def test_cancel_button_callback(self, tk_root: tk.Tk) -> None:
        """Botão Cancelar deve chamar callback correto."""
        cancel_called = []

        def on_cancel() -> None:
            cancel_called.append(True)

        buttons = create_button_bar(
            parent=tk_root,
            on_save=lambda: None,
            on_save_and_upload=lambda: None,
            on_cartao_cnpj=lambda: None,
            on_cancel=on_cancel,
        )

        buttons["cancel"].invoke()

        assert len(cancel_called) == 1


# =============================================================================
# Testes para apply_light_selection
# =============================================================================


class TestApplyLightSelection:
    """Testes para a função apply_light_selection."""

    @skip_tk_windows_313
    def test_applies_selection_color_to_entry(self, tk_root: tk.Tk) -> None:
        """apply_light_selection deve configurar cores de seleção em Entry."""
        entry = tk.Entry(tk_root)

        apply_light_selection(entry)

        # Tk.Entry suporta selectbackground/selectforeground
        assert entry.cget("selectbackground") == "#5bc0de"
        assert entry.cget("selectforeground") == "#000000"

    @skip_tk_windows_313
    def test_applies_selection_color_to_text(self, tk_root: tk.Tk) -> None:
        """apply_light_selection deve configurar cores de seleção em Text."""
        text = tk.Text(tk_root)

        apply_light_selection(text)

        # Text também suporta selectbackground/selectforeground
        assert text.cget("selectbackground") == "#5bc0de"
        assert text.cget("selectforeground") == "#000000"

    @skip_tk_windows_313
    def test_ignores_unsupported_widgets(self, tk_root: tk.Tk) -> None:
        """apply_light_selection não deve lançar exceção em widgets sem suporte."""
        # ttk widgets geralmente não suportam selectbackground
        from tkinter import ttk

        combo = ttk.Combobox(tk_root)

        # Não deve lançar exceção
        apply_light_selection(combo)


# =============================================================================
# Testes para bind_dirty_tracking
# =============================================================================


class TestBindDirtyTracking:
    """Testes para a função bind_dirty_tracking."""

    @skip_tk_windows_313
    def test_binds_keyrelease_event(self, tk_root: tk.Tk) -> None:
        """bind_dirty_tracking deve conectar evento <KeyRelease>."""
        entry = tk.Entry(tk_root)
        change_called = []

        def on_change(*_args, **_kwargs) -> None:  # noqa: ARG001
            change_called.append(True)

        bind_dirty_tracking(entry, on_change)

        # Simular KeyRelease
        entry.event_generate("<KeyRelease>")
        tk_root.update_idletasks()

        assert len(change_called) >= 1

    @skip_tk_windows_313
    def test_binds_paste_event(self, tk_root: tk.Tk) -> None:
        """bind_dirty_tracking deve conectar evento <<Paste>>."""
        entry = tk.Entry(tk_root)
        change_called = []

        def on_change(*_args, **_kwargs) -> None:  # noqa: ARG001
            change_called.append(True)

        bind_dirty_tracking(entry, on_change)

        # Simular Paste
        entry.event_generate("<<Paste>>")
        tk_root.update_idletasks()

        assert len(change_called) >= 1

    @skip_tk_windows_313
    def test_binds_cut_event(self, tk_root: tk.Tk) -> None:
        """bind_dirty_tracking deve conectar evento <<Cut>>."""
        entry = tk.Entry(tk_root)
        change_called = []

        def on_change(*_args, **_kwargs) -> None:  # noqa: ARG001
            change_called.append(True)

        bind_dirty_tracking(entry, on_change)

        # Simular Cut
        entry.event_generate("<<Cut>>")
        tk_root.update_idletasks()

        assert len(change_called) >= 1

    @skip_tk_windows_313
    def test_handles_unsupported_widgets_gracefully(self, tk_root: tk.Tk) -> None:
        """bind_dirty_tracking não deve lançar exceção em widgets sem suporte."""
        from tkinter import ttk

        # Alguns widgets podem não suportar todos os eventos
        label = ttk.Label(tk_root, text="Test")

        # Não deve lançar exceção
        bind_dirty_tracking(label, lambda: None)

    @skip_tk_windows_313
    def test_callback_receives_event(self, tk_root: tk.Tk) -> None:
        """Callback deve receber objeto de evento."""
        entry = tk.Entry(tk_root)
        received_events = []

        def on_change(event, *_args, **_kwargs) -> None:  # noqa: ARG001
            received_events.append(event)

        bind_dirty_tracking(entry, on_change)

        entry.event_generate("<KeyRelease>")
        tk_root.update_idletasks()

        assert len(received_events) >= 1
        # Event object deve ter type attribute
        assert hasattr(received_events[0], "type")
