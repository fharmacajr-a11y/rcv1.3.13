"""Configuração de testes para módulo HUB.

Este arquivo força o uso de tk/ttk em testes unitários ao invés de CustomTkinter,
pois os testes legados foram escritos para widgets tkinter padrão.

Estratégia:
- Desabilita HAS_CUSTOMTKINTER globalmente em testes
- Força ctk=None para garantir fallback
- Patches são aplicados antes de qualquer import dos módulos do HUB
"""

import tkinter
from tkinter import Tk, TclError  # type: ignore[attr-defined]
import pytest

# PASSO 1A: Blindagem precoce (antes de qualquer import dos testes)
import src.ui.ctk_config as ctk_config
ctk_config.HAS_CUSTOMTKINTER = False
ctk_config.ctk = None


@pytest.fixture(autouse=True, scope="function")
def force_tk_fallback(monkeypatch):
    """Force tk/ttk fallback in all HUB tests.
    
    This fixture runs automatically for every test in the hub module.
    It patches the SSoT to disable CustomTkinter, ensuring tests
    receive tk/ttk widgets which are easier to mock and assert.
    
    Without this, conditional inheritance creates CTkFrame instances
    that are incompatible with legacy test expectations.
    """
    # Patch SSoT global flags BEFORE any module imports them
    monkeypatch.setattr("src.ui.ctk_config.HAS_CUSTOMTKINTER", False, raising=False)
    monkeypatch.setattr("src.ui.ctk_config.ctk", None, raising=False)
    
    # PASSO 1B: Patch módulos já importados que cached o valor
    # (Importante: patch o nome usado pelo SUT, não um alias antigo)
    try:
        import src.modules.hub.views.hub_screen
        monkeypatch.setattr(src.modules.hub.views.hub_screen, "HAS_CUSTOMTKINTER", False)
        monkeypatch.setattr(src.modules.hub.views.hub_screen, "ctk", None)
    except (ImportError, AttributeError):
        pass
    
    try:
        import src.modules.hub.views.dashboard_center
        monkeypatch.setattr(src.modules.hub.views.dashboard_center, "HAS_CUSTOMTKINTER", False)
        monkeypatch.setattr(src.modules.hub.views.dashboard_center, "ctk", None)
    except (ImportError, AttributeError):
        pass
    
    try:
        import src.modules.hub.views.hub_quick_actions_view
        monkeypatch.setattr(src.modules.hub.views.hub_quick_actions_view, "HAS_CUSTOMTKINTER", False)
        monkeypatch.setattr(src.modules.hub.views.hub_quick_actions_view, "ctk", None)
    except (ImportError, AttributeError):
        pass
    
    try:
        import src.modules.hub.views.modules_panel
        monkeypatch.setattr(src.modules.hub.views.modules_panel, "HAS_CUSTOMTKINTER", False)
        monkeypatch.setattr(src.modules.hub.views.modules_panel, "ctk", None)
    except (ImportError, AttributeError):
        pass
    
    try:
        import src.modules.hub.views.notes_panel_view
        monkeypatch.setattr(src.modules.hub.views.notes_panel_view, "HAS_CUSTOMTKINTER", False)
        monkeypatch.setattr(src.modules.hub.views.notes_panel_view, "ctk", None)
    except (ImportError, AttributeError):
        pass
    
    try:
        import src.modules.hub.views.hub_screen_view_pure
        monkeypatch.setattr(src.modules.hub.views.hub_screen_view_pure, "HAS_CUSTOMTKINTER", False)
        monkeypatch.setattr(src.modules.hub.views.hub_screen_view_pure, "ctk", None)
    except (ImportError, AttributeError):
        pass
    
    try:
        import src.modules.hub.views.hub_dialogs
        monkeypatch.setattr(src.modules.hub.views.hub_dialogs, "HAS_CUSTOMTKINTER", False)
        monkeypatch.setattr(src.modules.hub.views.hub_dialogs, "ctk", None)
    except (ImportError, AttributeError):
        pass


# PASSO 5: tk_root real para testes que precisam de widgets Tkinter funcionais
@pytest.fixture(scope="function")
def tk_root():
    """Fornece uma janela Tkinter real para testes que criam widgets.
    
    Usar tk_root real ao invés de FakeWidget/MagicMock elimina:
    - AttributeError: '_last_child_ids', '.tk', '.children'
    - Necessidade de mockar APIs internas do Tkinter
    
    A janela fica hidden (withdrawn) e é destruída após cada teste.
    """
    root = Tk()
    root.withdraw()  # Não mostrar janela
    yield root
    try:
        root.destroy()
    except TclError:
        pass  # Já foi destruída
