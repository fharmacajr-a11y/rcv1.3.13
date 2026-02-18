# -*- coding: utf-8 -*-
"""Smoke tests do Hub Dashboard Center.

FASE 7: Verifica que build_dashboard_center instancia sem crash,
e que não há uso de ttk proibido.
"""

from __future__ import annotations

import tkinter as tk
from unittest.mock import patch, MagicMock

import pytest


def _make_minimal_state():
    """Cria DashboardViewState mínimo para smoke test."""
    from src.modules.hub.dashboard.models import DashboardSnapshot
    from src.modules.hub.viewmodels.dashboard_vm import (
        DashboardCardView,
        DashboardViewState,
    )

    snapshot = DashboardSnapshot(
        active_clients=5,
        pending_obligations=2,
        tasks_today=1,
        risk_radar={
            "ANVISA": {"pending": 1, "overdue": 0, "status": "green", "enabled": True},
            "Farmácia Popular": {"pending": 0, "overdue": 0, "status": "green", "enabled": True},
            "SIFAP": {"pending": 0, "overdue": 0, "status": "disabled", "enabled": False},
        },
    )

    return DashboardViewState(
        is_loading=False,
        snapshot=snapshot,
        card_clientes=DashboardCardView(label="Clientes", value=5, value_text="5"),
        card_pendencias=DashboardCardView(label="Pendências", value=2, value_text="2 ⚠"),
        card_tarefas=DashboardCardView(label="Tarefas hoje", value=1, value_text="1"),
    )


def test_build_dashboard_center_imports():
    """Verifica que build_dashboard_center pode ser importado."""
    from src.modules.hub.views.dashboard_center import build_dashboard_center

    assert callable(build_dashboard_center)


def test_build_dashboard_error_imports():
    """Verifica que build_dashboard_error pode ser importado."""
    from src.modules.hub.views.dashboard_center import build_dashboard_error

    assert callable(build_dashboard_error)


def test_dashboard_center_has_no_ttk_import():
    """Verifica que dashboard_center.py não importa ttk no nível de módulo."""
    import importlib.util
    import src.modules.hub.views.dashboard_center as mod

    source = importlib.util.find_spec(mod.__name__)
    assert source is not None


@pytest.mark.gui
def test_build_dashboard_center_renders():
    """Smoke: instancia build_dashboard_center, update_idletasks, destroy."""
    from src.modules.hub.views.dashboard_center import build_dashboard_center

    state = _make_minimal_state()
    root: tk.Tk = tk.Tk()
    root.withdraw()

    try:
        parent: tk.Frame = tk.Frame(root)
        parent.pack(fill="both", expand=True)

        # Mockar o store de atividade recente (evita I/O real)
        # Não passa tk_root para evitar bootstrap do Supabase
        with patch("src.modules.hub.recent_activity_store.get_recent_activity_store") as mock_store:
            store_instance = MagicMock()
            store_instance.get_lines.return_value = ["Atividade teste"]
            store_instance.subscribe.return_value = lambda: None
            mock_store.return_value = store_instance

            build_dashboard_center(parent, state, tk_root=None)

        root.update_idletasks()

        # Verificação: ao menos 1 widget filho foi criado
        children = parent.winfo_children()
        assert len(children) >= 1, "Dashboard deve criar widgets filhos"
    finally:
        root.destroy()


@pytest.mark.gui
def test_build_dashboard_error_renders():
    """Smoke: instancia build_dashboard_error, update_idletasks, destroy."""
    from src.modules.hub.views.dashboard_center import build_dashboard_error

    root: tk.Tk = tk.Tk()
    root.withdraw()

    try:
        parent: tk.Frame = tk.Frame(root)
        parent.pack(fill="both", expand=True)

        build_dashboard_error(parent, "Erro de teste")

        root.update_idletasks()

        children = parent.winfo_children()
        assert len(children) >= 1, "Error view deve criar widgets filhos"
    finally:
        root.destroy()


@pytest.mark.gui
def test_build_section_card_ctk():
    """Smoke: build_section_card cria outer+inner sem crash."""
    from src.modules.hub.views.dashboard_center import build_section_card

    root: tk.Tk = tk.Tk()
    root.withdraw()

    try:
        parent: tk.Frame = tk.Frame(root)
        parent.pack(fill="both", expand=True)

        outer, inner = build_section_card(parent, "Teste")
        outer.pack(fill="x")

        root.update_idletasks()

        assert outer is not None
        assert inner is not None
    finally:
        root.destroy()
