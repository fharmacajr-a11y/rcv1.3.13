from __future__ import annotations

import tkinter as tk

from src.modules.clientes.views.main_screen import MainScreenFrame
from src.modules.clientes.views.footer import ClientesFooter


def test_excluir_button_calls_delete_handler(tk_root_session):
    """Testa que o botão Excluir no footer chama o handler de exclusão."""
    called: list[bool] = []

    def fake_delete():
        called.append(True)

    # Botão Excluir agora está no footer, não na toolbar
    footer = ClientesFooter(
        tk_root_session,
        on_novo=lambda: None,
        on_editar=lambda: None,
        on_subpastas=lambda: None,
        on_enviar_supabase=lambda: None,
        on_enviar_pasta=lambda: None,
        on_excluir=fake_delete,
        on_batch_delete=lambda: None,
        on_batch_restore=lambda: None,
        on_batch_export=lambda: None,
    )

    # Verifica que o botão excluir existe
    assert footer.btn_excluir is not None

    # Simula clique no botão
    footer.btn_excluir.invoke()

    # Verifica que o handler foi chamado
    assert called == [True]

    try:
        footer.destroy()
    except Exception:
        pass


def test_delete_key_triggers_delete_handler(tk_root_session):
    called: list[bool] = []

    dummy = object.__new__(MainScreenFrame)

    def fake_delete():
        called.append(True)

    dummy.on_delete_selected_clients = fake_delete  # type: ignore[attr-defined]

    MainScreenFrame._on_tree_delete_key(dummy, tk.Event())

    assert called == [True]
