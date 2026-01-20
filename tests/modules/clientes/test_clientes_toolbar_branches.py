# -*- coding: utf-8 -*-
"""
MICROFASE 14 (Clientes) — COBRIR TOOLBAR_CTK BRANCHES (TRACE)

Coverage gaps identificados:
- toolbar_ctk.py: 255 linhas, 14% coverage (~36 linhas cobertas)
- Gaps principais: __init__, criação de widgets, callbacks, refresh_colors, fallback

Este módulo cria testes para cobrir os branches não testados no toolbar_ctk.py:
1. Instanciação com CustomTkinter (bloco principal do __init__)
2. Callbacks de busca (_trigger_search, _clear_search)
3. Callbacks de filtros (_trigger_order_change, _trigger_status_change)
4. Criação condicional do botão lixeira (if on_open_trash)
5. refresh_colors() para atualização dinâmica de tema
6. _build_fallback_toolbar() quando HAS_CUSTOMTKINTER=False

Estratégia:
- Testes com Tk root real (evita AttributeError em widgets)
- Mock mínimo para callbacks
- Validar criação de widgets críticos
- Testar branches condicionais (lixeira, fallback)
"""

from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING, Any, Generator
from unittest.mock import Mock

import pytest

if TYPE_CHECKING:
    from src.modules.clientes.views.toolbar_ctk import ClientesToolbarCtk


@pytest.fixture(scope="module")
def tk_root() -> Generator[Any, Any, None]:  # Use Any para evitar erro de Pylance com tk.Tk
    """Cria Tk root para testes (escopo module para reutilização)."""
    root = tk.Tk()  # type: ignore[attr-defined]
    root.withdraw()  # Esconde janela
    yield root
    try:
        root.destroy()
    except Exception:  # noqa: BLE001
        pass


def test_toolbar_ctk_instantiation_with_customtkinter(tk_root: Any) -> None:  # type: ignore[misc]
    """
    Testa instanciação da toolbar CustomTkinter com todos os widgets.
    
    Gap coberto: toolbar_ctk.py linhas ~73-260 (__init__ completo)
    
    Fluxo:
    1. Cria toolbar com callbacks mock
    2. Valida criação de widgets principais (entry, comboboxes)
    3. Verifica variáveis Tkinter inicializadas
    
    Critério de aceite:
    - toolbar instanciada sem exceções
    - entry_busca, order_combobox, status_combobox existem
    - var_busca, var_ordem, var_status existem
    """
    from src.modules.clientes.views.toolbar_ctk import ClientesToolbarCtk, HAS_CUSTOMTKINTER

    if not HAS_CUSTOMTKINTER:
        pytest.skip("CustomTkinter não disponível, teste skipped")

    # Callbacks mock
    on_search = Mock()
    on_clear = Mock()
    on_order = Mock()
    on_status = Mock()

    toolbar = ClientesToolbarCtk(
        tk_root,
        order_choices=["Nome A-Z", "Nome Z-A", "Última Alteração"],
        default_order="Nome A-Z",
        status_choices=["Todos", "Ativo", "Inativo"],
        on_search_changed=on_search,
        on_clear_search=on_clear,
        on_order_changed=on_order,
        on_status_changed=on_status,
        on_open_trash=None,  # SEM lixeira neste teste
        theme_manager=None,  # SEM tema
    )

    toolbar.update_idletasks()

    # Valida criação de widgets
    assert hasattr(toolbar, "entry_busca"), "entry_busca deveria existir"
    assert hasattr(toolbar, "order_combobox"), "order_combobox deveria existir"
    assert hasattr(toolbar, "status_combobox"), "status_combobox deveria existir"

    # Valida variáveis Tkinter
    assert hasattr(toolbar, "var_busca"), "var_busca deveria existir"
    assert hasattr(toolbar, "var_ordem"), "var_ordem deveria existir"
    assert hasattr(toolbar, "var_status"), "var_status deveria existir"

    # Valida valores iniciais
    assert toolbar.var_ordem.get() == "Nome A-Z"
    assert toolbar.var_status.get() == "Todos"

    # Cleanup
    toolbar.destroy()


def test_toolbar_ctk_with_trash_button(tk_root: Any) -> None:
    """
    Testa criação condicional do botão lixeira quando on_open_trash fornecido.
    
    Gap coberto: toolbar_ctk.py linhas ~244-252 (if on_open_trash)
    
    Fluxo:
    1. Cria toolbar COM on_open_trash callback
    2. Valida que lixeira_button foi criado
    3. Simula clique no botão e verifica callback chamado
    
    Critério de aceite:
    - lixeira_button existe quando on_open_trash fornecido
    - Clique no botão invoca on_open_trash
    """
    from src.modules.clientes.views.toolbar_ctk import ClientesToolbarCtk, HAS_CUSTOMTKINTER

    if not HAS_CUSTOMTKINTER:
        pytest.skip("CustomTkinter não disponível, teste skipped")

    on_trash = Mock()

    toolbar = ClientesToolbarCtk(
        tk_root,
        order_choices=["Nome A-Z"],
        default_order="Nome A-Z",
        status_choices=["Todos"],
        on_search_changed=lambda text: None,
        on_clear_search=lambda: None,
        on_order_changed=lambda order: None,
        on_status_changed=lambda status: None,
        on_open_trash=on_trash,  # COM lixeira
        theme_manager=None,
    )

    toolbar.update_idletasks()

    # Valida que botão lixeira foi criado
    assert hasattr(toolbar, "lixeira_button"), "lixeira_button deveria existir quando on_open_trash fornecido"

    # Simula clique no botão
    toolbar.lixeira_button.invoke()
    toolbar.update_idletasks()

    # Valida que callback foi chamado
    on_trash.assert_called_once()

    # Cleanup
    toolbar.destroy()


def test_toolbar_ctk_search_callback(tk_root: Any) -> None:
    """
    Testa callback de busca quando texto muda.
    
    Gap coberto: toolbar_ctk.py linhas ~272-278 (_trigger_search)
    
    Fluxo:
    1. Cria toolbar com callback de busca mock
    2. Altera var_busca
    3. Chama _trigger_search()
    4. Valida que callback foi chamado com texto correto
    
    Critério de aceite:
    - _trigger_search() chama on_search_changed com texto da busca
    """
    from src.modules.clientes.views.toolbar_ctk import ClientesToolbarCtk, HAS_CUSTOMTKINTER

    if not HAS_CUSTOMTKINTER:
        pytest.skip("CustomTkinter não disponível, teste skipped")

    on_search = Mock()

    toolbar = ClientesToolbarCtk(
        tk_root,
        order_choices=["Nome A-Z"],
        default_order="Nome A-Z",
        status_choices=["Todos"],
        on_search_changed=on_search,
        on_clear_search=lambda: None,
        on_order_changed=lambda order: None,
        on_status_changed=lambda status: None,
        on_open_trash=None,
        theme_manager=None,
    )

    toolbar.update_idletasks()

    # Define texto de busca
    toolbar.var_busca.set("cliente teste")

    # Chama _trigger_search
    toolbar._trigger_search()  # pyright: ignore[reportPrivateUsage]

    # Valida callback
    on_search.assert_called_with("cliente teste")

    # Cleanup
    toolbar.destroy()


def test_toolbar_ctk_clear_search_callback(tk_root: Any) -> None:
    """
    Testa callback de limpar busca.
    
    Gap coberto: toolbar_ctk.py linhas ~280-287 (_clear_search)
    
    Fluxo:
    1. Cria toolbar com callback de limpar mock
    2. Define texto de busca
    3. Chama _clear_search()
    4. Valida que var_busca foi limpa e callback chamado
    
    Critério de aceite:
    - _clear_search() limpa var_busca
    - _clear_search() chama on_clear_search
    """
    from src.modules.clientes.views.toolbar_ctk import ClientesToolbarCtk, HAS_CUSTOMTKINTER

    if not HAS_CUSTOMTKINTER:
        pytest.skip("CustomTkinter não disponível, teste skipped")

    on_clear = Mock()

    toolbar = ClientesToolbarCtk(
        tk_root,
        order_choices=["Nome A-Z"],
        default_order="Nome A-Z",
        status_choices=["Todos"],
        on_search_changed=lambda text: None,
        on_clear_search=on_clear,
        on_order_changed=lambda order: None,
        on_status_changed=lambda status: None,
        on_open_trash=None,
        theme_manager=None,
    )

    toolbar.update_idletasks()

    # Define texto de busca
    toolbar.var_busca.set("texto para limpar")

    # Chama _clear_search
    toolbar._clear_search()  # pyright: ignore[reportPrivateUsage]

    # Valida que var_busca foi limpa
    assert toolbar.var_busca.get() == ""

    # Valida que callback foi chamado
    on_clear.assert_called_once()

    # Cleanup
    toolbar.destroy()


def test_toolbar_ctk_order_change_callback(tk_root: Any) -> None:
    """
    Testa callback de mudança de ordenação.
    
    Gap coberto: toolbar_ctk.py linhas ~289-295 (_trigger_order_change)
    
    Fluxo:
    1. Cria toolbar com callback de ordenação mock
    2. Altera var_ordem
    3. Chama _trigger_order_change()
    4. Valida que callback foi chamado com nova ordenação
    
    Critério de aceite:
    - _trigger_order_change() chama on_order_changed com nova ordenação
    """
    from src.modules.clientes.views.toolbar_ctk import ClientesToolbarCtk, HAS_CUSTOMTKINTER

    if not HAS_CUSTOMTKINTER:
        pytest.skip("CustomTkinter não disponível, teste skipped")

    on_order = Mock()

    toolbar = ClientesToolbarCtk(
        tk_root,
        order_choices=["Nome A-Z", "Nome Z-A"],
        default_order="Nome A-Z",
        status_choices=["Todos"],
        on_search_changed=lambda text: None,
        on_clear_search=lambda: None,
        on_order_changed=on_order,
        on_status_changed=lambda status: None,
        on_open_trash=None,
        theme_manager=None,
    )

    toolbar.update_idletasks()

    # Altera ordenação
    toolbar.var_ordem.set("Nome Z-A")

    # Chama _trigger_order_change
    toolbar._trigger_order_change()  # pyright: ignore[reportPrivateUsage]

    # Valida callback
    on_order.assert_called_with("Nome Z-A")

    # Cleanup
    toolbar.destroy()


def test_toolbar_ctk_status_change_callback(tk_root: Any) -> None:
    """
    Testa callback de mudança de status.
    
    Gap coberto: toolbar_ctk.py linhas ~297-305 (_trigger_status_change)
    
    Fluxo:
    1. Cria toolbar com callback de status mock
    2. Altera var_status
    3. Chama _trigger_status_change()
    4. Valida que callback foi chamado com novo status
    
    Critério de aceite:
    - _trigger_status_change() chama on_status_changed com novo status
    """
    from src.modules.clientes.views.toolbar_ctk import ClientesToolbarCtk, HAS_CUSTOMTKINTER

    if not HAS_CUSTOMTKINTER:
        pytest.skip("CustomTkinter não disponível, teste skipped")

    on_status = Mock()

    toolbar = ClientesToolbarCtk(
        tk_root,
        order_choices=["Nome A-Z"],
        default_order="Nome A-Z",
        status_choices=["Todos", "Ativo", "Inativo"],
        on_search_changed=lambda text: None,
        on_clear_search=lambda: None,
        on_order_changed=lambda order: None,
        on_status_changed=on_status,
        on_open_trash=None,
        theme_manager=None,
    )

    toolbar.update_idletasks()

    # Altera status
    toolbar.var_status.set("Ativo")

    # Chama _trigger_status_change
    toolbar._trigger_status_change()  # pyright: ignore[reportPrivateUsage]

    # Valida callback
    on_status.assert_called_with("Ativo")

    # Cleanup
    toolbar.destroy()


def test_toolbar_ctk_refresh_colors(tk_root: Any) -> None:
    """
    Testa refresh_colors() para atualização dinâmica de tema.
    
    Gap coberto: toolbar_ctk.py linhas ~337-380 (refresh_colors)
    
    Fluxo:
    1. Cria toolbar
    2. Chama refresh_colors() com theme_manager mock
    3. Valida que não levanta exceção
    
    Critério de aceite:
    - refresh_colors() executa sem exceções
    
    Nota: Teste minimal pois não temos theme_manager real completo
    """
    from src.modules.clientes.views.toolbar_ctk import ClientesToolbarCtk, HAS_CUSTOMTKINTER

    if not HAS_CUSTOMTKINTER:
        pytest.skip("CustomTkinter não disponível, teste skipped")

    toolbar = ClientesToolbarCtk(
        tk_root,
        order_choices=["Nome A-Z"],
        default_order="Nome A-Z",
        status_choices=["Todos"],
        on_search_changed=lambda text: None,
        on_clear_search=lambda: None,
        on_order_changed=lambda order: None,
        on_status_changed=lambda status: None,
        on_open_trash=None,
        theme_manager=None,  # SEM tema real
    )

    toolbar.update_idletasks()

    # Mock theme_manager simples
    mock_theme = Mock()
    mock_theme.get_palette.return_value = {
        "toolbar_bg": "#F5F5F5",
        "input_text": "#000000",
        "input_bg": "#FFFFFF",
        "input_border": "#C8C8C8",
        "input_placeholder": "#999999",
        "dropdown_bg": "#E8E8E8",
        "dropdown_hover": "#D0D0D0",
        "accent": "#0078D7",
        "accent_hover": "#0056B3",
        "neutral_btn": "#E0E0E0",
        "neutral_hover": "#C0C0C0",
        "danger": "#F44336",
        "danger_hover": "#D32F2F",
    }

    # Chama refresh_colors (não deve explodir)
    try:
        toolbar.refresh_colors(mock_theme)
        toolbar.update_idletasks()
    except Exception as exc:
        pytest.fail(f"refresh_colors() não deveria falhar: {exc}")

    # Cleanup
    toolbar.destroy()


def test_toolbar_ctk_fallback_when_customtkinter_missing(tk_root: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Testa fallback para ttk quando CustomTkinter não está disponível.
    
    Gap coberto: toolbar_ctk.py linhas ~100-104 (_build_fallback_toolbar)
    
    Fluxo:
    1. Mock HAS_CUSTOMTKINTER = False (forçar fallback)
    2. Mock create_search_controls para evitar TclError de imagem
    3. Cria toolbar
    4. Valida que _build_fallback_toolbar foi chamado
    5. Valida widgets básicos criados
    
    Critério de aceite:
    - Quando HAS_CUSTOMTKINTER=False, usa ttk widgets
    
    Nota: Teste complexo de mockar - simplificado para validar apenas 
    que o código não explode quando HAS_CUSTOMTKINTER=False
    """
    from unittest.mock import Mock
    from src.modules.clientes.views import toolbar_ctk
    from src.modules.clientes.views.toolbar_ctk import ClientesToolbarCtk

    # Backup valor original
    original_has_ctk = toolbar_ctk.HAS_CUSTOMTKINTER

    try:
        # Força fallback
        toolbar_ctk.HAS_CUSTOMTKINTER = False

        # Mock create_search_controls para evitar TclError de imagem ("pyimage1" doesn't exist)
        # IMPORTANTE: Mock no módulo correto (src.ui.components)
        mock_controls = Mock()
        mock_controls.frame = tk.Frame(tk_root)
        mock_controls.entry = tk.Entry(mock_controls.frame, textvariable=tk.StringVar())  # type: ignore[attr-defined]
        mock_controls.order_combobox = tk.Entry(mock_controls.frame)  # type: ignore[attr-defined]
        mock_controls.status_combobox = tk.Entry(mock_controls.frame)  # type: ignore[attr-defined]
        mock_controls.lixeira_button = None
        mock_controls.obrigacoes_button = None
        
        def fake_create_search_controls(*args, **kwargs):
            return mock_controls
        
        monkeypatch.setattr(
            "src.ui.components.create_search_controls",
            fake_create_search_controls
        )

        # Tenta criar toolbar (deve usar fallback)
        toolbar = ClientesToolbarCtk(
            tk_root,
            order_choices=["Nome A-Z"],
            default_order="Nome A-Z",
            status_choices=["Todos"],
            on_search_changed=lambda text: None,
            on_clear_search=lambda: None,
            on_order_changed=lambda order: None,
            on_status_changed=lambda status: None,
            on_open_trash=None,
            theme_manager=None,
        )

        toolbar.update_idletasks()

        # Valida que widgets básicos existem (mesmo no fallback)
        assert hasattr(toolbar, "entry_busca"), "entry_busca deveria existir no fallback"
        assert hasattr(toolbar, "var_busca"), "var_busca deveria existir no fallback"

        # Cleanup
        toolbar.destroy()
        mock_controls.frame.destroy()

    finally:
        # Restaura valor original
        toolbar_ctk.HAS_CUSTOMTKINTER = original_has_ctk
