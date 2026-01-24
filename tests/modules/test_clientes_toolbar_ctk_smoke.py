# -*- coding: utf-8 -*-
"""Smoke tests para toolbar CustomTkinter do módulo Clientes."""

from __future__ import annotations

import pytest

from tests.helpers.skip_conditions import SKIP_PY313_TKINTER


def test_toolbar_ctk_import():
    """Verifica que toolbar_ctk pode ser importada."""
    try:
        from src.modules.clientes.views.toolbar_ctk import ClientesToolbarCtk, HAS_CUSTOMTKINTER

        assert ClientesToolbarCtk is not None
        assert isinstance(HAS_CUSTOMTKINTER, bool)
    except ImportError as e:
        pytest.fail(f"Falha ao importar toolbar_ctk: {e}")


def test_toolbar_legacy_still_works():
    """Verifica que toolbar legada ainda funciona."""
    try:
        from src.modules.clientes.views.toolbar import ClientesToolbar

        assert ClientesToolbar is not None
    except ImportError as e:
        pytest.fail(f"Falha ao importar toolbar legada: {e}")


def test_builder_imports_with_ctk():
    """Verifica que builder importa corretamente com CTK."""
    try:
        from src.modules.clientes.views import main_screen_ui_builder

        assert hasattr(main_screen_ui_builder, "build_toolbar")
        assert hasattr(main_screen_ui_builder, "USE_CTK_TOOLBAR")
    except ImportError as e:
        pytest.fail(f"Falha ao importar builder: {e}")


def test_toolbar_ctk_creation_with_mocks():
    """Testa criação da toolbar CTK com mocks."""
    import tkinter as tk

    try:
        from src.modules.clientes.appearance import ClientesThemeManager
        from src.modules.clientes.views.toolbar_ctk import ClientesToolbarCtk, HAS_CUSTOMTKINTER

        if not HAS_CUSTOMTKINTER:
            pytest.skip("CustomTkinter não disponível")

        root = tk.Tk()  # type: ignore[attr-defined]
        try:
            theme_manager = ClientesThemeManager()

            toolbar = ClientesToolbarCtk(
                root,
                order_choices=["Nome", "ID", "CNPJ"],
                default_order="Nome",
                status_choices=["Todos", "Ativo", "Inativo"],
                on_search_changed=lambda text: None,
                on_clear_search=lambda: None,
                on_order_changed=lambda order: None,
                on_status_changed=lambda status: None,
                on_open_trash=lambda: None,
                theme_manager=theme_manager,
            )

            assert toolbar is not None
            assert hasattr(toolbar, "var_busca")
            assert hasattr(toolbar, "var_ordem")
            assert hasattr(toolbar, "var_status")
            assert hasattr(toolbar, "entry_busca")
            assert hasattr(toolbar, "order_combobox")
            assert hasattr(toolbar, "status_combobox")

        finally:
            root.destroy()

    except Exception as e:
        pytest.fail(f"Erro ao criar toolbar CTK: {e}")


@SKIP_PY313_TKINTER
def test_toolbar_ctk_fallback():
    """Testa fallback quando CustomTkinter não está disponível."""
    import tkinter as tk  # noqa: F401

    try:
        # Força uso do fallback
        from src.modules.clientes.views import toolbar_ctk

        original_has_ctk = toolbar_ctk.HAS_CUSTOMTKINTER
        toolbar_ctk.HAS_CUSTOMTKINTER = False

        try:
            root = tk.Tk()  # type: ignore[attr-defined]
            try:
                toolbar = toolbar_ctk.ClientesToolbarCtk(
                    root,
                    order_choices=["Nome", "ID"],
                    default_order="Nome",
                    status_choices=["Todos", "Ativo"],
                    on_search_changed=lambda text: None,
                    on_clear_search=lambda: None,
                    on_order_changed=lambda order: None,
                    on_status_changed=lambda status: None,
                )

                # Deve funcionar via fallback
                assert toolbar is not None
                assert hasattr(toolbar, "var_busca")

                # Fix Microfase 19.2: Garantir que widgets são processados antes de destruir
                root.update_idletasks()

            finally:
                try:
                    root.destroy()
                except Exception:  # noqa: BLE001
                    pass
        finally:
            toolbar_ctk.HAS_CUSTOMTKINTER = original_has_ctk

    except Exception as e:
        pytest.fail(f"Erro no fallback da toolbar: {e}")


def test_toolbar_refresh_colors():
    """Testa método refresh_colors da toolbar CTK."""
    import tkinter as tk

    try:
        from src.modules.clientes.appearance import ClientesThemeManager
        from src.modules.clientes.views.toolbar_ctk import ClientesToolbarCtk, HAS_CUSTOMTKINTER

        if not HAS_CUSTOMTKINTER:
            pytest.skip("CustomTkinter não disponível")

        root = tk.Tk()  # type: ignore[attr-defined]
        try:
            theme_manager = ClientesThemeManager()

            toolbar = ClientesToolbarCtk(
                root,
                order_choices=["Nome"],
                default_order="Nome",
                status_choices=["Todos"],
                on_search_changed=lambda text: None,
                on_clear_search=lambda: None,
                on_order_changed=lambda order: None,
                on_status_changed=lambda status: None,
                theme_manager=theme_manager,
            )

            # Testa refresh
            theme_manager.save_mode("dark")
            toolbar.refresh_colors(theme_manager)

            theme_manager.save_mode("light")
            toolbar.refresh_colors(theme_manager)

        finally:
            root.destroy()

    except Exception as e:
        pytest.fail(f"Erro ao testar refresh_colors: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
