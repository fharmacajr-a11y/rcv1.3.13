# -*- coding: utf-8 -*-
"""Smoke tests de migração CTk do módulo Anvisa.

Valida que:
1. Nenhum import de ttkbootstrap existe no módulo Anvisa
2. AnvisaScreen instancia sem exceção usando CTk
3. AnvisaFooter instancia sem exceção usando CTk
4. Callbacks principais não explodem com dependências mockadas
"""

from __future__ import annotations

import importlib
import pkgutil

import pytest


# ===== 1. ZERO ttkbootstrap no módulo =====


def test_no_ttkbootstrap_imports_in_anvisa_module():
    """Nenhum arquivo do módulo Anvisa deve importar ttkbootstrap."""
    import src.modules.anvisa as anvisa_pkg

    pkg_path = anvisa_pkg.__path__
    violations: list[str] = []

    for importer, modname, ispkg in pkgutil.walk_packages(pkg_path, prefix="src.modules.anvisa."):
        try:
            spec = importlib.util.find_spec(modname)
            if spec is None or spec.origin is None:
                continue
            with open(spec.origin, encoding="utf-8", errors="ignore") as f:
                source = f.read()
            if "ttkbootstrap" in source or "bootstyle" in source:
                violations.append(modname)
        except Exception:
            pass  # Módulos sem source (compiled, etc.)

    assert not violations, f"Módulos com referência a ttkbootstrap: {violations}"


# ===== 2. Smoke: AnvisaScreen instancia e destrói sem exceção =====


@pytest.fixture
def anvisa_screen_ctk(tk_root_session, monkeypatch):
    """Instancia AnvisaScreen com mocks essenciais (sem I/O)."""
    from src.modules.anvisa.views.anvisa_screen import AnvisaScreen

    # Mock da carga de dados (evitar chamada real ao Supabase)
    monkeypatch.setattr(AnvisaScreen, "_load_requests_from_cloud", lambda self: None)

    screen = AnvisaScreen(tk_root_session)
    yield screen
    # Cleanup: destruir widgets (tk_root_session é session-scoped)
    screen.destroy()


def test_anvisa_screen_creates_without_error(anvisa_screen_ctk):
    """AnvisaScreen deve instanciar sem exceção."""
    assert anvisa_screen_ctk is not None


def test_anvisa_screen_update_idletasks(anvisa_screen_ctk):
    """update_idletasks não deve explodir (requisito smoke)."""
    anvisa_screen_ctk.update_idletasks()


def test_anvisa_screen_has_paned_widget(anvisa_screen_ctk):
    """Deve conter PanedWindow com duas metades."""
    assert hasattr(anvisa_screen_ctk, "paned")
    assert anvisa_screen_ctk.paned is not None


def test_anvisa_screen_has_content_frame(anvisa_screen_ctk):
    """Deve ter content_frame para conteúdo dinâmico."""
    assert hasattr(anvisa_screen_ctk, "content_frame")
    assert anvisa_screen_ctk.content_frame is not None


def test_anvisa_screen_show_home_does_not_crash(anvisa_screen_ctk):
    """show_home() não deve explodir ao limpar e reexibir conteúdo."""
    anvisa_screen_ctk.show_home()
    assert anvisa_screen_ctk.current_page.get() == "home"


def test_anvisa_screen_show_subpage_does_not_crash(anvisa_screen_ctk):
    """_show_subpage() não deve explodir (labels sem bootstyle)."""
    anvisa_screen_ctk._show_subpage("teste", "Teste Page")
    assert anvisa_screen_ctk.current_page.get() == "teste"


def test_anvisa_screen_clear_content_does_not_crash(anvisa_screen_ctk):
    """_clear_content() não deve explodir."""
    anvisa_screen_ctk._clear_content()
    children = anvisa_screen_ctk.content_frame.winfo_children()
    assert len(children) == 0


# ===== 3. Smoke: AnvisaFooter instancia e destrói sem exceção =====


@pytest.fixture
def anvisa_footer_ctk(tk_root_session):
    """Instancia AnvisaFooter com parâmetros mínimos."""
    from src.modules.anvisa.views.anvisa_footer import AnvisaFooter

    footer = AnvisaFooter(
        tk_root_session,
        base_prefix="org1/client1",
        org_id="org1",
    )
    yield footer
    footer.destroy()


def test_anvisa_footer_creates_without_error(anvisa_footer_ctk):
    """AnvisaFooter deve instanciar sem exceção."""
    assert anvisa_footer_ctk is not None


def test_anvisa_footer_update_idletasks(anvisa_footer_ctk):
    """update_idletasks não deve explodir."""
    anvisa_footer_ctk.update_idletasks()


def test_anvisa_footer_has_process_combo(anvisa_footer_ctk):
    """Deve ter combobox de processos."""
    assert hasattr(anvisa_footer_ctk, "_process_combo")
    assert anvisa_footer_ctk._process_var.get() != ""


def test_anvisa_footer_has_upload_button(anvisa_footer_ctk):
    """Deve ter botão de upload (desabilitado por default)."""
    assert hasattr(anvisa_footer_ctk, "_btn_upload")
    assert str(anvisa_footer_ctk._btn_upload.cget("state")) == "disabled"


# ===== 4. Callbacks mockados =====


def test_handle_back_home_calls_on_back(tk_root_session, monkeypatch):
    """_handle_back em home deve chamar on_back callback."""
    from src.modules.anvisa.views.anvisa_screen import AnvisaScreen

    monkeypatch.setattr(AnvisaScreen, "_load_requests_from_cloud", lambda self: None)

    called = []
    screen = AnvisaScreen(tk_root_session, on_back=lambda: called.append(True))
    screen.current_page.set("home")
    screen._handle_back()
    assert called == [True]
    screen.destroy()


def test_handle_back_subpage_returns_home(anvisa_screen_ctk):
    """_handle_back em subpágina deve voltar para home."""
    anvisa_screen_ctk.current_page.set("teste1")
    anvisa_screen_ctk._handle_back()
    assert anvisa_screen_ctk.current_page.get() == "home"
