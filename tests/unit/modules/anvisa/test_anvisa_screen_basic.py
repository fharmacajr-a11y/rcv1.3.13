"""Testes básicos da tela ANVISA.

Validam apenas renderização e smoke tests da View.
Lógica de negócio (status, actions, summary) é testada em test_anvisa_service.py.
"""

from __future__ import annotations


import pytest


def test_format_cnpj_with_raw_digits():
    """Deve formatar CNPJ sem máscara."""
    from src.modules.anvisa.views.anvisa_screen import AnvisaScreen

    screen = AnvisaScreen.__new__(AnvisaScreen)
    assert screen._format_cnpj("12862364000674") == "12.862.364/0006-74"


def test_format_cnpj_with_existing_mask():
    """Deve manter CNPJ já formatado."""
    from src.modules.anvisa.views.anvisa_screen import AnvisaScreen

    screen = AnvisaScreen.__new__(AnvisaScreen)
    assert screen._format_cnpj("72.800.550/0001-04") == "72.800.550/0001-04"


def test_format_cnpj_with_invalid_length():
    """Deve retornar valor original se não tiver 14 dígitos."""
    from src.modules.anvisa.views.anvisa_screen import AnvisaScreen

    screen = AnvisaScreen.__new__(AnvisaScreen)
    assert screen._format_cnpj("123456") == "123456"


def test_format_cnpj_with_none():
    """Deve retornar string vazia para None."""
    from src.modules.anvisa.views.anvisa_screen import AnvisaScreen

    screen = AnvisaScreen.__new__(AnvisaScreen)
    assert screen._format_cnpj(None) == ""


@pytest.fixture
def anvisa_screen(tk_root_session, monkeypatch):
    """Instancia AnvisaScreen para testes de smoke."""
    from src.modules.anvisa import AnvisaScreen

    # Mockar _load_requests_from_cloud para evitar chamadas reais ao Supabase
    def mock_load_requests():
        pass

    monkeypatch.setattr(AnvisaScreen, "_load_requests_from_cloud", lambda self: mock_load_requests())

    screen = AnvisaScreen(tk_root_session)
    return screen


# ===== SMOKE TESTS - Renderização Básica =====


def test_anvisa_screen_renders_without_errors(anvisa_screen):
    """Deve renderizar sem exceções (smoke test)."""
    assert anvisa_screen is not None
    assert hasattr(anvisa_screen, "tree_requests")


def test_anvisa_screen_starts_on_home(anvisa_screen):
    """Deve iniciar na página home."""
    assert anvisa_screen.current_page.get() == "home"


def test_anvisa_screen_has_treeview_with_columns(anvisa_screen):
    """Deve ter Treeview com colunas corretas."""
    assert anvisa_screen.tree_requests is not None
    # CTkTableView usa _columns; ttk.Treeview usa ["columns"]
    tree = anvisa_screen.tree_requests
    columns = getattr(tree, "_columns", None) or tree["columns"]
    assert "client_id" in columns
    assert "razao_social" in columns
    assert "cnpj" in columns


def test_anvisa_screen_has_no_fixed_history_panel(anvisa_screen):
    """Não deve ter painel fixo de histórico (agora é popup)."""
    assert anvisa_screen._history_popup is None
    assert anvisa_screen._history_tree_popup is None


def test_anvisa_screen_has_required_buttons(tk_root_session, monkeypatch):
    """Deve renderizar botões principais."""
    from src.modules.anvisa import AnvisaScreen

    monkeypatch.setattr(AnvisaScreen, "_load_requests_from_cloud", lambda self: None)
    screen = AnvisaScreen(tk_root_session)

    buttons = []
    for widget in screen.winfo_children():
        buttons.extend(_find_buttons_recursive(widget))

    button_texts = [btn.cget("text") for btn in buttons]

    # Deve ter botão Nova
    assert any("Nova" == text for text in button_texts), "Botão Nova não encontrado"

    # NÃO deve ter botões de teste antigos
    assert "Teste 1" not in button_texts
    assert "Teste 2" not in button_texts
    assert "Teste 3" not in button_texts


def test_anvisa_screen_no_back_button_present(anvisa_screen):
    """Botão Voltar não deve existir."""
    all_buttons = []
    for widget in anvisa_screen.winfo_children():
        all_buttons.extend(_find_buttons_recursive(widget))

    button_texts = [btn.cget("text") for btn in all_buttons]
    assert "← Voltar" not in button_texts
    assert "Voltar" not in button_texts


def _find_buttons_recursive(widget) -> list:
    """Busca recursiva de botões Button (CTk ou ttk)."""
    import tkinter as tk

    buttons = []

    # Detectar CTkButton ou ttk.Button
    try:
        from customtkinter import CTkButton

        is_button = isinstance(widget, (CTkButton, tk.Button))
    except ImportError:
        from tkinter import ttk

        is_button = isinstance(widget, (ttk.Button, tk.Button))

    if is_button:
        buttons.append(widget)

    try:
        for child in widget.winfo_children():
            buttons.extend(_find_buttons_recursive(child))
    except Exception:
        pass

    return buttons


# ===== TESTES DE CONSUMO DE VIEW MODEL =====
# View deve usar dados do Service sem revalidar lógica


def test_anvisa_screen_uses_service_for_main_rows(tk_root_session, monkeypatch):
    """View deve consumir build_main_rows do Service."""
    from src.modules.anvisa import AnvisaScreen

    # Mock durante init
    monkeypatch.setattr(AnvisaScreen, "_load_requests_from_cloud", lambda self: None)
    screen = AnvisaScreen(tk_root_session)

    # Verificar que tem acesso ao service
    assert hasattr(screen, "_service")
    assert screen._service is not None

    # Verificar que service tem build_main_rows
    assert hasattr(screen._service, "build_main_rows")


def test_anvisa_screen_consumes_pending_client_data(tk_root_session, monkeypatch):
    """View deve processar dados pendentes corretamente."""
    from src.modules.anvisa import AnvisaScreen

    monkeypatch.setattr(AnvisaScreen, "_load_requests_from_cloud", lambda self: None)
    screen = AnvisaScreen(tk_root_session)

    # Dados pendentes iniciam como None
    assert hasattr(screen, "_pending_client_data")
    assert screen._pending_client_data is None

    # Simular dados pendentes
    screen._pending_client_data = {
        "client_id": "456",
        "razao_social": "Cliente Teste",
        "cnpj": "11.222.333/0001-44",
    }

    # Mock do modal
    called = []

    def mock_open_modal(client_data):
        called.append(client_data)

    monkeypatch.setattr(screen, "_open_new_anvisa_request_dialog", mock_open_modal)

    # Consumir
    screen._consume_pending_pick()

    # Verificar que chamou modal e limpou pending
    assert len(called) == 1
    assert screen._pending_client_data is None
