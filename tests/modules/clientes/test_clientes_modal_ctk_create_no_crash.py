# -*- coding: utf-8 -*-
"""Testes de criação do modal CustomTkinter de Clientes (sem crash).

Microfase: 6 (Subdialogs CustomTkinter)
"""

import tkinter as tk

import pytest

pytest.importorskip("customtkinter")


@pytest.mark.gui
def test_clientes_modal_ctk_alert_no_crash() -> None:
    """Testa se ClientesModalCTK.alert() pode ser criado sem crash (modo não-interativo)."""
    from src.modules.clientes.ui import ClientesModalCTK

    root = tk.Tk()
    root.withdraw()

    try:
        # Criar modal (não interativo - fecha imediatamente)
        def close_after_100ms():
            # Busca todos os Toplevels e fecha
            for widget in root.winfo_children():
                if isinstance(widget, tk.Toplevel):
                    widget.destroy()

        root.after(100, close_after_100ms)

        # Este deve criar modal e fechar rapidamente
        ClientesModalCTK.alert(root, "Test", "Test message")

        # Se chegou aqui, não crashou
        assert True

    finally:
        root.destroy()


@pytest.mark.gui
def test_clientes_modal_ctk_error_no_crash() -> None:
    """Testa se ClientesModalCTK.error() pode ser criado sem crash (modo não-interativo)."""
    from src.modules.clientes.ui import ClientesModalCTK

    root = tk.Tk()
    root.withdraw()

    try:

        def close_after_100ms():
            for widget in root.winfo_children():
                if isinstance(widget, tk.Toplevel):
                    widget.destroy()

        root.after(100, close_after_100ms)

        ClientesModalCTK.error(root, "Test", "Test error")

        assert True

    finally:
        root.destroy()


@pytest.mark.gui
def test_clientes_modal_ctk_info_no_crash() -> None:
    """Testa se ClientesModalCTK.info() pode ser criado sem crash (modo não-interativo)."""
    from src.modules.clientes.ui import ClientesModalCTK

    root = tk.Tk()
    root.withdraw()

    try:

        def close_after_100ms():
            for widget in root.winfo_children():
                if isinstance(widget, tk.Toplevel):
                    widget.destroy()

        root.after(100, close_after_100ms)

        ClientesModalCTK.info(root, "Test", "Test info")

        assert True

    finally:
        root.destroy()


@pytest.mark.gui
def test_clientes_modal_ctk_confirm_no_crash() -> None:
    """Testa se ClientesModalCTK.confirm() pode ser criado sem crash (modo não-interativo)."""
    from src.modules.clientes.ui import ClientesModalCTK

    root = tk.Tk()
    root.withdraw()

    try:

        def close_after_100ms():
            for widget in root.winfo_children():
                if isinstance(widget, tk.Toplevel):
                    widget.destroy()

        root.after(100, close_after_100ms)

        # Confirm retorna bool
        result = ClientesModalCTK.confirm(root, "Test", "Test confirm?")

        # Deve ser bool (False pois fechamos sem clicar em Sim)
        assert isinstance(result, bool)

    finally:
        root.destroy()
