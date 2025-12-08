# -*- coding: utf-8 -*-

from __future__ import annotations

from pytest import MonkeyPatch

from src.modules.clientes.viewmodel import ClienteRow
from src.modules.clientes.views.main_screen_state_builder import build_main_screen_state


def _make_row(row_id: str = "1") -> ClienteRow:
    return ClienteRow(
        id=row_id,
        razao_social=f"Cliente {row_id}",
        cnpj="00.000.000/0000-00",
        nome=f"Contato {row_id}",
        whatsapp="55999999999",
        observacoes="",
        status="Ativo",
        ultima_alteracao="2024-01-01T10:00:00",
    )


def test_build_main_screen_state_normalizes_labels(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        "src.modules.clientes.views.main_screen_state_builder.get_supabase_state",
        lambda: ("online", "Conectado"),
    )
    rows = [_make_row("10")]

    state = build_main_screen_state(
        clients=rows,
        raw_order_label=" Razão Social (A→Z) ",
        raw_filter_label="  Ativos  ",
        raw_search_text="  teste  ",
        selected_ids={"1", "2"},
        is_trash_screen=False,
    )

    assert state.order_label == "Razão Social (A→Z)"
    assert state.filter_label == "Ativos"
    assert state.search_text == "teste"
    assert set(state.selected_ids) == {"1", "2"}
    assert state.clients == rows
    assert state.is_online is True
    assert state.is_trash_screen is False


def test_build_main_screen_state_handles_supabase_errors(monkeypatch: MonkeyPatch) -> None:
    """MS-12: is_online agora é parâmetro explícito, não mais calculado internamente."""

    # Nota: Após mudança, is_online é parâmetro explícito
    # O caller é que deve determinar is_online antes de chamar build_main_screen_state

    state = build_main_screen_state(
        clients=[_make_row("20")],
        raw_order_label=None,
        raw_filter_label=None,
        raw_search_text=None,
        selected_ids=[],
        is_trash_screen=True,
        is_online=False,  # Caller determina o estado
    )

    assert state.is_online is False
    assert state.is_trash_screen is True
