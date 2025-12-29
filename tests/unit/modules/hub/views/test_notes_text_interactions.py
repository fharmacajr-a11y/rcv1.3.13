# -*- coding: utf-8 -*-
"""Testes para notes_text_interactions.py (menu de contexto) - HEADLESS."""

import sys
from unittest.mock import MagicMock

import pytest

from tests.unit.fakes.test_tk_fakes import FakeMenu, FakeTextWidget


@pytest.fixture
def fake_text_widget():
    """Cria FakeTextWidget para testes."""
    widget = FakeTextWidget()
    widget._note_meta = {
        "note123": {
            "body": "Conteúdo da nota 123",
            "author_name": "João",
            "author_email": "joao@example.com",
            "created_at": "2025-12-28T10:00:00",
            "is_deleted": False,
        },
        "note456": {
            "body": "Nota apagada",
            "author_name": "Maria",
            "author_email": "maria@example.com",
            "created_at": "2025-12-28T11:00:00",
            "is_deleted": True,
        },
    }
    return widget


@pytest.fixture
def fake_menu():
    """Cria FakeMenu para testes."""
    return FakeMenu()


def test_click_on_note_with_noteid_tag_creates_menu_with_copy_options(fake_text_widget, monkeypatch):
    """Clique em nota com tag noteid_123 deve criar menu com 'Copiar mensagem' e 'Copiar tudo'."""
    from src.modules.hub.views import notes_text_interactions

    # Monkeypatch tkinter.Menu para retornar FakeMenu
    fake_menu = FakeMenu()
    monkeypatch.setattr("tkinter.Menu", lambda *args, **kwargs: fake_menu)

    # Instalar menu
    notes_text_interactions.install_notes_context_menu(fake_text_widget)

    # Configurar fake: clique retorna noteid_note123
    fake_text_widget.set_tag_names("1.0", ("noteid_note123",))

    # Simular clique direito
    event = MagicMock(x=10, y=20, x_root=100, y_root=200)
    callback = fake_text_widget._binds.get("<Button-3>")
    assert callback is not None

    callback(event)

    # Validar menu
    labels = [cmd["label"] for cmd in fake_menu.commands]
    assert "Copiar mensagem" in labels
    assert "Copiar tudo" in labels
    assert fake_menu.popup_called


def test_click_on_deleted_note_copies_message_apagada(fake_text_widget, monkeypatch):
    """Clique em nota deletada deve copiar 'Mensagem apagada'."""
    from src.modules.hub.views import notes_text_interactions

    fake_menu = FakeMenu()
    monkeypatch.setattr("tkinter.Menu", lambda *args, **kwargs: fake_menu)

    notes_text_interactions.install_notes_context_menu(fake_text_widget)

    # Configurar fake: clique retorna noteid_note456 (deletada)
    fake_text_widget.set_tag_names("1.0", ("noteid_note456",))

    event = MagicMock(x=10, y=20, x_root=100, y_root=200)
    callback = fake_text_widget._binds["<Button-3>"]
    callback(event)

    # Executar "Copiar mensagem"
    copy_cmd = next((c for c in fake_menu.commands if c["label"] == "Copiar mensagem"), None)
    assert copy_cmd is not None
    copy_cmd["command"]()

    # Validar clipboard
    assert fake_text_widget._clipboard == "Mensagem apagada"


def test_copy_all_formats_with_timestamp_and_author(fake_text_widget, monkeypatch):
    """'Copiar tudo' deve formatar com timestamp e autor."""
    from src.modules.hub.views import notes_text_interactions

    fake_menu = FakeMenu()
    monkeypatch.setattr("tkinter.Menu", lambda *args, **kwargs: fake_menu)

    notes_text_interactions.install_notes_context_menu(fake_text_widget)

    fake_text_widget.set_tag_names("1.0", ("noteid_note123",))

    event = MagicMock(x=10, y=20, x_root=100, y_root=200)
    callback = fake_text_widget._binds["<Button-3>"]
    callback(event)

    # Executar "Copiar tudo"
    copy_all_cmd = next((c for c in fake_menu.commands if c["label"] == "Copiar tudo"), None)
    assert copy_all_cmd is not None
    copy_all_cmd["command"]()

    # Validar formato: [timestamp] Autor: corpo
    assert "João" in fake_text_widget._clipboard
    assert "Conteúdo da nota 123" in fake_text_widget._clipboard


def test_delete_permission_denied_shows_messagebox(fake_text_widget, monkeypatch):
    """Usuário sem permissão não pode apagar nota de outro autor."""
    from src.modules.hub.views import notes_text_interactions

    fake_menu = FakeMenu()
    monkeypatch.setattr("tkinter.Menu", lambda *args, **kwargs: fake_menu)

    # Mock messagebox.showinfo
    showinfo_called = []

    def fake_showinfo(title, message):
        showinfo_called.append((title, message))

    monkeypatch.setattr("tkinter.messagebox.showinfo", fake_showinfo)

    # Mock callback de delete
    delete_called = []

    def on_delete(note_id):
        delete_called.append(note_id)

    # Instalar com email diferente do autor
    notes_text_interactions.install_notes_context_menu(
        fake_text_widget, on_delete_note_click=on_delete, current_user_email="outro@example.com"
    )

    fake_text_widget.set_tag_names("1.0", ("noteid_note123",))

    event = MagicMock(x=10, y=20, x_root=100, y_root=200)
    callback = fake_text_widget._binds["<Button-3>"]
    callback(event)

    # Executar "Apagar mensagem"
    delete_cmd = next((c for c in fake_menu.commands if c["label"] == "Apagar mensagem"), None)
    assert delete_cmd is not None
    delete_cmd["command"]()

    # Validar: messagebox chamado, callback NÃO chamado
    assert len(showinfo_called) == 1
    assert "Permissão negada" in showinfo_called[0][0]
    assert len(delete_called) == 0


def test_delete_permission_granted_calls_callback(fake_text_widget, monkeypatch):
    """Usuário com permissão pode apagar própria nota."""
    from src.modules.hub.views import notes_text_interactions

    fake_menu = FakeMenu()
    monkeypatch.setattr("tkinter.Menu", lambda *args, **kwargs: fake_menu)

    delete_called = []

    def on_delete(note_id):
        delete_called.append(note_id)

    # Instalar com mesmo email do autor
    notes_text_interactions.install_notes_context_menu(
        fake_text_widget, on_delete_note_click=on_delete, current_user_email="joao@example.com"
    )

    fake_text_widget.set_tag_names("1.0", ("noteid_note123",))

    event = MagicMock(x=10, y=20, x_root=100, y_root=200)
    callback = fake_text_widget._binds["<Button-3>"]
    callback(event)

    # Executar "Apagar mensagem"
    delete_cmd = next((c for c in fake_menu.commands if c["label"] == "Apagar mensagem"), None)
    assert delete_cmd is not None
    delete_cmd["command"]()

    # Validar: callback chamado
    assert delete_called == ["note123"]


def test_click_outside_note_with_selection_shows_copy_selection(fake_text_widget, monkeypatch):
    """Clique fora de nota COM seleção deve mostrar 'Copiar seleção'."""
    from src.modules.hub.views import notes_text_interactions

    fake_menu = FakeMenu()
    monkeypatch.setattr("tkinter.Menu", lambda *args, **kwargs: fake_menu)

    notes_text_interactions.install_notes_context_menu(fake_text_widget)

    # Configurar: sem tag noteid, mas COM seleção
    fake_text_widget.set_tag_names("1.0", ())
    fake_text_widget.set_selection("Texto selecionado")

    event = MagicMock(x=10, y=20, x_root=100, y_root=200)
    callback = fake_text_widget._binds["<Button-3>"]
    callback(event)

    # Validar menu
    labels = [cmd["label"] for cmd in fake_menu.commands]
    assert "Copiar seleção" in labels

    # Executar e validar clipboard
    copy_sel_cmd = next((c for c in fake_menu.commands if c["label"] == "Copiar seleção"), None)
    assert copy_sel_cmd is not None
    copy_sel_cmd["command"]()
    assert fake_text_widget._clipboard == "Texto selecionado"


def test_click_outside_note_without_selection_shows_disabled_menu(fake_text_widget, monkeypatch):
    """Clique fora de nota SEM seleção deve mostrar menu disabled."""
    from src.modules.hub.views import notes_text_interactions

    fake_menu = FakeMenu()
    monkeypatch.setattr("tkinter.Menu", lambda *args, **kwargs: fake_menu)

    notes_text_interactions.install_notes_context_menu(fake_text_widget)

    # Configurar: sem tag noteid, SEM seleção
    fake_text_widget.set_tag_names("1.0", ())
    fake_text_widget.set_selection("")  # Sem seleção -> TclError em selection_get

    event = MagicMock(x=10, y=20, x_root=100, y_root=200)
    callback = fake_text_widget._binds["<Button-3>"]
    callback(event)

    # Validar menu
    labels = [cmd["label"] for cmd in fake_menu.commands]
    assert "(Nenhuma ação disponível)" in labels

    # Validar state disabled
    disabled_cmd = next((c for c in fake_menu.commands if "(Nenhuma ação disponível)" in c["label"]), None)
    assert disabled_cmd is not None
    assert disabled_cmd["state"] == "disabled"


def test_macos_binds_button2(fake_text_widget, monkeypatch):
    """macOS deve bindar <Button-2> além de <Button-3>."""
    from src.modules.hub.views import notes_text_interactions

    fake_menu = FakeMenu()
    monkeypatch.setattr("tkinter.Menu", lambda *args, **kwargs: fake_menu)

    # Monkeypatch sys.platform
    monkeypatch.setattr(sys, "platform", "darwin")

    notes_text_interactions.install_notes_context_menu(fake_text_widget)

    # Validar binds
    assert "<Button-3>" in fake_text_widget._binds
    assert "<Button-2>" in fake_text_widget._binds
