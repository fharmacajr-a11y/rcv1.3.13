# -*- coding: utf-8 -*-
"""Testes para _anvisa_history_popup_mixin.py (_update_history_popup, _on_history_select) - HEADLESS."""

from unittest.mock import MagicMock

import pytest

from src.modules.anvisa.views._anvisa_history_popup_mixin import AnvisaHistoryPopupMixin
from tests.unit.fakes.test_tk_fakes import (
    FakeButton,
    FakeFrame,
    FakeLabel,
    FakeStringVar,
    FakeToplevel,
    FakeTreeview,
    FakeVar,
)


class DummyHistoryPopupMixin(AnvisaHistoryPopupMixin):
    """Dummy class para testar mixin sem UI."""

    def __init__(self):
        self._history_tree_popup = FakeTreeview()
        self._history_popup = None
        self._history_iid_map = {}
        self._history_rows_by_id = {}
        self._history_due_var = FakeVar()
        self._history_notes_var = FakeVar()
        self._btn_finalizar = FakeButton(state="disabled")
        self._btn_cancelar = FakeButton(state="disabled")
        self._btn_excluir_popup = FakeButton(state="disabled")
        self._service = MagicMock()
        self._load_demandas_for_cliente = MagicMock()
        self._format_cnpj = MagicMock(return_value="12.345.678/0001-90")


# ============================================================================
# MF48: Testes headless para _open_history_popup
# ============================================================================


class DummyHistoryPopupMixinHeadless(AnvisaHistoryPopupMixin):
    """Dummy class estendida para testar _open_history_popup sem UI."""

    def __init__(self):
        self._history_popup = None
        self._history_tree_popup = None
        self._history_iid_map = {}
        self._history_rows_by_id = {}
        self._history_due_var = None
        self._history_notes_var = None
        self._btn_finalizar = None
        self._btn_cancelar = None
        self._btn_excluir_popup = None
        self._service = MagicMock()
        self._service.build_history_rows = MagicMock(return_value=[])
        self._load_demandas_for_cliente = MagicMock(return_value=[])
        self._format_cnpj = MagicMock(return_value="12.345.678/0001-90")
        self._lock_history_tree_columns = lambda tree: None  # Override para evitar import

    def winfo_toplevel(self):
        """Retorna toplevel fake."""
        return FakeToplevel()


@pytest.fixture
def patched_tk_modules(monkeypatch):
    """Fixture que patcha os módulos tk/ctk no mixin.

    Patcha via __globals__ do método _open_history_popup para
    garantir que funciona mesmo quando test_anvisa_lazy_imports
    trocou o módulo no sys.modules (criando objeto diferente).
    """
    # Obter o dict de globais DO MÓDULO ONDE O MÉTODO FOI DEFINIDO
    fn_globals = AnvisaHistoryPopupMixin._open_history_popup.__globals__
    tk_mod = fn_globals["tk"]
    ctk_mod = fn_globals["ctk"]

    # Patch tk
    monkeypatch.setattr(tk_mod, "Toplevel", FakeToplevel)
    monkeypatch.setattr(tk_mod, "StringVar", FakeStringVar)

    # Patch ctk (customtkinter)
    monkeypatch.setattr(ctk_mod, "CTkFrame", FakeFrame)
    monkeypatch.setattr(ctk_mod, "CTkLabel", FakeLabel)
    monkeypatch.setattr(ctk_mod, "CTkButton", FakeButton)

    # Patch CTkTableView e window utils via __globals__
    monkeypatch.setitem(fn_globals, "CTkTableView", FakeTreeview)
    monkeypatch.setitem(fn_globals, "prepare_hidden_window", lambda w: None)
    monkeypatch.setitem(fn_globals, "apply_window_icon", lambda w: None)
    monkeypatch.setitem(fn_globals, "center_window_simple", lambda w, p: None)
    monkeypatch.setitem(fn_globals, "show_centered_no_flash", lambda w, p, width, height: None)


def test_open_history_popup_creates_popup_and_tree_headless_mf48(patched_tk_modules):
    """_open_history_popup deve criar popup e tree quando não existe (headless)."""
    dummy = DummyHistoryPopupMixinHeadless()

    # Chamar _open_history_popup
    dummy._open_history_popup("c1", "RAZAO SOCIAL TESTE", "12345678000190", center=True)

    # Validar que popup foi criado
    assert dummy._history_popup is not None
    assert isinstance(dummy._history_popup, FakeToplevel)

    # Validar que tree foi criado
    assert dummy._history_tree_popup is not None
    assert isinstance(dummy._history_tree_popup, FakeTreeview)

    # Validar que vars foram criados
    assert dummy._history_due_var is not None
    assert dummy._history_notes_var is not None

    # Validar que botões foram criados
    assert dummy._btn_finalizar is not None
    assert dummy._btn_cancelar is not None
    assert dummy._btn_excluir_popup is not None


def test_open_history_popup_when_popup_exists_updates_and_focuses_mf48(patched_tk_modules):
    """_open_history_popup com popup existente deve atualizar e focar."""
    dummy = DummyHistoryPopupMixinHeadless()

    # Criar popup existente
    existing_popup = FakeToplevel(exists=True)
    dummy._history_popup = existing_popup
    dummy._history_tree_popup = FakeTreeview()

    # Spy para _update_history_popup
    update_called = []

    def spy_update(client_id, razao, cnpj):
        update_called.append((client_id, razao, cnpj))
        # Não chamar original pois vai tentar acessar popup.winfo_children

    dummy._update_history_popup = spy_update

    # Chamar _open_history_popup
    dummy._open_history_popup("c2", "NOVA RAZAO", "98765432000100", center=True)

    # Validar que update foi chamado
    assert len(update_called) == 1
    assert update_called[0] == ("c2", "NOVA RAZAO", "98765432000100")

    # Validar que popup foi trazido para frente
    assert existing_popup.lift_called is True
    assert existing_popup.focus_called is True


def test_open_history_popup_with_coordinates_uses_geometry_mf48(patched_tk_modules):
    """_open_history_popup com center=False deve usar x/y para posicionar."""
    dummy = DummyHistoryPopupMixinHeadless()

    # Chamar _open_history_popup sem centralizar
    dummy._open_history_popup("c1", "RAZAO", "123", center=False, x=100, y=200)

    # Validar que popup foi criado e posicionado
    assert dummy._history_popup is not None
    assert dummy._history_popup._geometry == "750x480+100+200"
    assert dummy._history_popup.deiconify_called is True
    assert dummy._history_popup.lift_called is True
    assert dummy._history_popup.focus_called is True


# ============================================================================
# Testes originais
# ============================================================================


def test_update_history_popup_none_tree_returns_early():
    """_update_history_popup com tree None deve retornar early."""
    dummy = DummyHistoryPopupMixin()
    dummy._history_tree_popup = None

    # Não deve lançar exceção
    dummy._update_history_popup("client1", "ACME Corp", "12345678000190")


def test_update_history_popup_empty_demandas_inserts_sem_demandas():
    """_update_history_popup com demandas vazio deve inserir 'Sem demandas'."""
    dummy = DummyHistoryPopupMixin()
    dummy._load_demandas_for_cliente = MagicMock(return_value=[])

    dummy._update_history_popup("client1", "ACME Corp", "12345678000190")

    # Validar insert
    assert len(dummy._history_tree_popup._items) == 1
    first_item = list(dummy._history_tree_popup._items.values())[0]
    assert first_item["values"][0] == "Sem demandas"


def test_update_history_popup_with_demandas_populates_tree():
    """_update_history_popup com demandas deve popular tree com rows."""
    dummy = DummyHistoryPopupMixin()

    demandas = [
        {"id": "req1", "request_type": "AFE", "status": "draft"},
        {"id": "req2", "request_type": "Renovação", "status": "done"},
    ]

    dummy._load_demandas_for_cliente = MagicMock(return_value=demandas)

    # Mock service.build_history_rows
    rows = [
        {
            "request_id": "req1",
            "tipo": "AFE",
            "status_humano": "Em aberto",
            "criada_em": "28/12/2025",
            "atualizada_em": "28/12/2025",
            "actions": {"close": True, "cancel": True, "delete": True},
            "prazo": "31/12/2025",
            "observacoes": "Observação 1",
        },
        {
            "request_id": "req2",
            "tipo": "Renovação",
            "status_humano": "Finalizado",
            "criada_em": "27/12/2025",
            "atualizada_em": "28/12/2025",
            "actions": {"close": False, "cancel": False, "delete": True},
            "prazo": "",
            "observacoes": "",
        },
    ]

    dummy._service.build_history_rows = MagicMock(return_value=rows)

    dummy._update_history_popup("client1", "ACME Corp", "12345678000190")

    # Validar tree population
    assert len(dummy._history_tree_popup._items) == 2
    assert "req1" in dummy._history_tree_popup._items
    assert "req2" in dummy._history_tree_popup._items

    # Validar _history_rows_by_id
    assert "req1" in dummy._history_rows_by_id
    assert "req2" in dummy._history_rows_by_id

    # Validar iid_map
    assert "req1" in dummy._history_iid_map
    assert dummy._history_iid_map["req1"] == "req1"


def test_update_history_popup_auto_selects_first_row():
    """_update_history_popup deve auto-selecionar primeira linha."""
    dummy = DummyHistoryPopupMixin()

    demandas = [{"id": "req1", "request_type": "AFE"}]
    dummy._load_demandas_for_cliente = MagicMock(return_value=demandas)

    rows = [
        {
            "request_id": "req1",
            "tipo": "AFE",
            "status_humano": "Em aberto",
            "criada_em": "28/12/2025",
            "atualizada_em": "28/12/2025",
            "actions": {"close": True, "cancel": True, "delete": True},
        }
    ]

    dummy._service.build_history_rows = MagicMock(return_value=rows)

    # Mock _on_history_select
    on_history_select_called = []

    def fake_on_history_select():
        on_history_select_called.append(True)

    dummy._on_history_select = fake_on_history_select

    dummy._update_history_popup("client1", "ACME Corp", "12345678000190")

    # Validar seleção
    assert dummy._history_tree_popup.selection() == ["req1"]

    # Validar _on_history_select chamado
    assert len(on_history_select_called) == 1


def test_on_history_select_no_selection_disables_buttons():
    """_on_history_select sem seleção deve desabilitar botões e limpar detalhes."""
    dummy = DummyHistoryPopupMixin()
    dummy._history_tree_popup._selection = []

    dummy._on_history_select()

    # Validar botões desabilitados
    assert dummy._btn_finalizar.state_value == "disabled"
    assert dummy._btn_cancelar.state_value == "disabled"
    assert dummy._btn_excluir_popup.state_value == "disabled"

    # Validar detalhes limpos
    assert dummy._history_due_var.get() == "-"
    assert dummy._history_notes_var.get() == "-"


def test_on_history_select_sem_demandas_disables_buttons():
    """_on_history_select com 'Sem demandas' deve desabilitar botões."""
    dummy = DummyHistoryPopupMixin()
    dummy._history_tree_popup._selection = ["item1"]
    dummy._history_tree_popup._items["item1"] = {"values": ["Sem demandas", "", "", ""]}

    dummy._on_history_select()

    # Validar botões desabilitados
    assert dummy._btn_finalizar.state_value == "disabled"
    assert dummy._btn_cancelar.state_value == "disabled"
    assert dummy._btn_excluir_popup.state_value == "disabled"


def test_on_history_select_with_actions_enables_appropriate_buttons():
    """_on_history_select com actions deve habilitar/desabilitar botões conforme actions."""
    dummy = DummyHistoryPopupMixin()

    dummy._history_tree_popup._selection = ["req1"]
    dummy._history_tree_popup._items["req1"] = {"values": ["AFE", "Em aberto", "28/12/2025", "28/12/2025"]}

    # Configurar _history_rows_by_id
    dummy._history_rows_by_id = {
        "req1": {
            "request_id": "req1",
            "tipo": "AFE",
            "actions": {"close": True, "cancel": False, "delete": True},
            "prazo": "31/12/2025",
            "observacoes": "Observação teste",
        }
    }

    dummy._on_history_select()

    # Validar botões conforme actions
    assert dummy._btn_finalizar.state_value == "normal"  # close=True
    assert dummy._btn_cancelar.state_value == "disabled"  # cancel=False
    assert dummy._btn_excluir_popup.state_value == "normal"  # delete=True


def test_on_history_select_updates_details_vars():
    """_on_history_select deve atualizar vars de detalhes (prazo, observações)."""
    dummy = DummyHistoryPopupMixin()

    dummy._history_tree_popup._selection = ["req1"]
    dummy._history_tree_popup._items["req1"] = {"values": ["AFE", "Em aberto", "28/12/2025", "28/12/2025"]}

    # Configurar _history_rows_by_id
    dummy._history_rows_by_id = {
        "req1": {
            "request_id": "req1",
            "actions": {"close": True, "cancel": True, "delete": True},
            "prazo": "31/12/2025",
            "observacoes": "Observação teste",
        }
    }

    dummy._on_history_select()

    # Validar vars atualizadas
    assert dummy._history_due_var.get() == "31/12/2025"
    assert dummy._history_notes_var.get() == "Observação teste"


def test_on_history_select_no_row_found_disables_finalizar_cancelar_enables_excluir():
    """_on_history_select sem row encontrado deve desabilitar finalizar/cancelar, habilitar excluir."""
    dummy = DummyHistoryPopupMixin()

    dummy._history_tree_popup._selection = ["req1"]
    dummy._history_tree_popup._items["req1"] = {"values": ["AFE", "Em aberto", "28/12/2025", "28/12/2025"]}

    # Não configurar _history_rows_by_id (row não encontrado)
    dummy._history_rows_by_id = {}

    dummy._on_history_select()

    # Validar botões
    assert dummy._btn_finalizar.state_value == "disabled"
    assert dummy._btn_cancelar.state_value == "disabled"
    assert dummy._btn_excluir_popup.state_value == "normal"

    # Validar vars limpas
    assert dummy._history_due_var.get() == "-"
    assert dummy._history_notes_var.get() == "-"


def test_update_history_popup_with_multiple_items_different_actions():
    """_update_history_popup deve popular tree com múltiplos itens e actions variados."""
    dummy = DummyHistoryPopupMixin()

    # Mock demandas (2 itens)
    dummy._load_demandas_for_cliente = MagicMock(
        return_value=[
            {"id": "req1", "tipo": "RFB", "status": "Aguardando"},
            {"id": "req2", "tipo": "AFE", "status": "Finalizado"},
        ]
    )

    # Mock build_history_rows
    dummy._service.build_history_rows.return_value = [
        {
            "request_id": "req1",
            "tipo": "RFB",
            "status_humano": "Em aberto",
            "criada_em": "01/12/2025",
            "atualizada_em": "31/12/2025",
            "prazo": "31/12/2025",
            "observacoes": "Obs 1",
            "actions": {"close": True, "cancel": True, "delete": True},
        },
        {
            "request_id": "req2",
            "tipo": "AFE",
            "status_humano": "Finalizado",
            "criada_em": "01/11/2025",
            "atualizada_em": "15/12/2025",
            "prazo": "15/12/2025",
            "observacoes": "Obs 2",
            "actions": {"close": False, "cancel": False, "delete": True},
        },
    ]

    dummy._update_history_popup("client1", "ACME Corp", "12345678000190")

    # Validar: 2 itens inseridos
    assert len(dummy._history_tree_popup._items) == 2

    # Validar _history_rows_by_id
    assert "req1" in dummy._history_rows_by_id
    assert "req2" in dummy._history_rows_by_id
    assert dummy._history_rows_by_id["req1"]["actions"]["close"] is True
    assert dummy._history_rows_by_id["req2"]["actions"]["close"] is False


def test_on_history_select_all_actions_disabled():
    """_on_history_select deve desabilitar todos os botões se actions = {close:False, cancel:False, delete:False}."""
    dummy = DummyHistoryPopupMixin()

    dummy._history_tree_popup._selection = ["req1"]
    dummy._history_tree_popup._items["req1"] = {"values": ["RFB", "Finalizado", "01/01/2025", "01/01/2025"]}

    dummy._history_rows_by_id = {
        "req1": {
            "request_id": "req1",
            "actions": {"close": False, "cancel": False, "delete": False},
            "prazo": "01/01/2025",
            "observacoes": "-",
        }
    }

    dummy._on_history_select()

    # Validar: todos desabilitados
    assert dummy._btn_finalizar.state_value == "disabled"
    assert dummy._btn_cancelar.state_value == "disabled"
    assert dummy._btn_excluir_popup.state_value == "disabled"


def test_on_history_select_only_cancel_enabled():
    """_on_history_select deve habilitar apenas botão cancelar se actions = {close:False, cancel:True, delete:False}."""
    dummy = DummyHistoryPopupMixin()

    dummy._history_tree_popup._selection = ["req1"]
    dummy._history_tree_popup._items["req1"] = {"values": ["RFB", "Aguardando", "31/12/2025", "31/12/2025"]}

    dummy._history_rows_by_id = {
        "req1": {
            "request_id": "req1",
            "actions": {"close": False, "cancel": True, "delete": False},
            "prazo": "31/12/2025",
            "observacoes": "Apenas cancelamento permitido",
        }
    }

    dummy._on_history_select()

    # Validar
    assert dummy._btn_finalizar.state_value == "disabled"
    assert dummy._btn_cancelar.state_value == "normal"
    assert dummy._btn_excluir_popup.state_value == "disabled"


def test_update_history_popup_clears_previous_items():
    """_update_history_popup deve limpar itens anteriores antes de popular novos."""
    dummy = DummyHistoryPopupMixin()

    # Inserir itens antigos
    dummy._history_tree_popup.insert("", "end", values=("OLD", "OLD", "OLD", "OLD"))
    dummy._history_iid_map = {"old_id": "old_iid"}

    # Mock nova carga (1 item)
    dummy._load_demandas_for_cliente = MagicMock(return_value=[{"id": "req1", "tipo": "RFB", "status": "Aguardando"}])

    dummy._service.build_history_rows.return_value = [
        {
            "request_id": "req1",
            "tipo": "RFB",
            "status_humano": "Em aberto",
            "criada_em": "01/12/2025",
            "atualizada_em": "31/12/2025",
            "prazo": "31/12/2025",
            "observacoes": "Nova obs",
            "actions": {"close": True, "cancel": True, "delete": True},
        }
    ]

    dummy._update_history_popup("client1", "ACME Corp", "12345678000190")

    # Validar: antigos limpos, novo inserido
    assert len(dummy._history_tree_popup._items) == 1
    assert "old_id" not in dummy._history_iid_map
    assert "req1" in dummy._history_rows_by_id


def test_on_history_select_no_selection_disables_all_buttons():
    """_on_history_select sem seleção deve desabilitar todos os botões."""
    dummy = DummyHistoryPopupMixin()
    dummy._history_tree_popup._selection = []

    dummy._on_history_select()

    assert dummy._btn_finalizar.state_value == "disabled"
    assert dummy._btn_cancelar.state_value == "disabled"
    assert dummy._btn_excluir_popup.state_value == "disabled"


def test_on_history_select_sem_demandas_row_disables_all_buttons():
    """_on_history_select com row 'Sem demandas' deve desabilitar todos os botões."""
    dummy = DummyHistoryPopupMixin()
    dummy._history_tree_popup._selection = ["iid1"]
    dummy._history_tree_popup._items["iid1"] = {"values": ["Sem demandas", "", "", ""]}

    dummy._on_history_select()

    assert dummy._btn_finalizar.state_value == "disabled"
    assert dummy._btn_cancelar.state_value == "disabled"
    assert dummy._btn_excluir_popup.state_value == "disabled"


def test_on_history_select_with_actions_enables_buttons():
    """_on_history_select com actions deve habilitar botões correspondentes."""
    dummy = DummyHistoryPopupMixin()
    dummy._history_tree_popup._selection = ["req1"]
    dummy._history_tree_popup._items["req1"] = {"values": ["AFE", "Em aberto", "28/12", "29/12"]}

    # Mock _history_rows_by_id
    dummy._history_rows_by_id = {
        "req1": {
            "request_id": "req1",
            "tipo": "AFE",
            "status_humano": "Em aberto",
            "prazo": "31/12/2025",
            "observacoes": "Obs 1",
            "actions": {"close": True, "cancel": True, "delete": True},
        }
    }

    dummy._on_history_select()

    assert dummy._btn_finalizar.state_value == "normal"
    assert dummy._btn_cancelar.state_value == "normal"
    assert dummy._btn_excluir_popup.state_value == "normal"
    assert dummy._history_due_var._value == "31/12/2025"
    assert dummy._history_notes_var._value == "Obs 1"


def test_on_history_select_no_close_action_disables_finalizar():
    """_on_history_select com close=False deve desabilitar botão finalizar."""
    dummy = DummyHistoryPopupMixin()
    dummy._history_tree_popup._selection = ["req1"]
    dummy._history_tree_popup._items["req1"] = {"values": ["Renovação", "Finalizado", "27/12", "28/12"]}

    dummy._history_rows_by_id = {
        "req1": {
            "request_id": "req1",
            "tipo": "Renovação",
            "status_humano": "Finalizado",
            "prazo": "",
            "observacoes": "",
            "actions": {"close": False, "cancel": False, "delete": True},
        }
    }

    dummy._on_history_select()

    assert dummy._btn_finalizar.state_value == "disabled"
    assert dummy._btn_cancelar.state_value == "disabled"
    assert dummy._btn_excluir_popup.state_value == "normal"


def test_on_history_select_missing_actions_disables_all():
    """_on_history_select sem actions no row deve usar defaults (delete=True)."""
    dummy = DummyHistoryPopupMixin()
    dummy._history_tree_popup._selection = ["req1"]
    dummy._history_tree_popup._items["req1"] = {"values": ["AFE", "Em aberto", "28/12", "29/12"]}

    dummy._history_rows_by_id = {
        "req1": {
            "request_id": "req1",
            "tipo": "AFE",
            "status_humano": "Em aberto",
            "prazo": "31/12/2025",
            "observacoes": "Obs 1",
            # Sem "actions"
        }
    }

    dummy._on_history_select()

    # Deve usar default (close=False, cancel=False, delete=True)
    assert dummy._btn_finalizar.state_value == "disabled"
    assert dummy._btn_cancelar.state_value == "disabled"
    assert dummy._btn_excluir_popup.state_value == "normal"  # delete default=True


def test_on_history_select_updates_due_and_notes():
    """_on_history_select deve atualizar prazo e observações."""
    dummy = DummyHistoryPopupMixin()
    dummy._history_tree_popup._selection = ["req2"]
    dummy._history_tree_popup._items["req2"] = {"values": ["RFB", "Cancelado", "01/01", "02/01"]}

    dummy._history_rows_by_id = {
        "req2": {
            "request_id": "req2",
            "prazo": "05/01/2026",
            "observacoes": "Aguardando documento",
            "actions": {"close": False, "cancel": False, "delete": False},
        }
    }

    dummy._on_history_select()

    assert dummy._history_due_var._value == "05/01/2026"
    assert dummy._history_notes_var._value == "Aguardando documento"


def test_on_history_select_empty_prazo_and_notes():
    """_on_history_select com prazo e observações vazios deve setar '-' por default."""
    dummy = DummyHistoryPopupMixin()
    dummy._history_tree_popup._selection = ["req3"]
    dummy._history_tree_popup._items["req3"] = {"values": ["AFE", "Em aberto", "28/12", "29/12"]}

    dummy._history_rows_by_id = {
        "req3": {
            "request_id": "req3",
            "prazo": "",
            "observacoes": "",
            "actions": {"close": True, "cancel": True, "delete": True},
        }
    }

    dummy._on_history_select()

    # Valores vazios são convertidos para "-"
    assert dummy._history_due_var._value == "-"
    assert dummy._history_notes_var._value == "-"


def test_update_history_popup_with_multiple_actions():
    """_update_history_popup com múltiplas demandas deve configurar botões."""
    dummy = DummyHistoryPopupMixin()

    demandas = [
        {"id": "req1", "request_type": "AFE", "status": "draft"},
        {"id": "req2", "request_type": "Renovação", "status": "done"},
        {"id": "req3", "request_type": "RFB", "status": "cancelled"},
    ]

    dummy._load_demandas_for_cliente = MagicMock(return_value=demandas)

    rows = [
        {
            "request_id": "req1",
            "tipo": "AFE",
            "status_humano": "Em aberto",
            "criada_em": "28/12",
            "atualizada_em": "28/12",
            "actions": {"close": True, "cancel": True, "delete": True},
            "prazo": "31/12",
            "observacoes": "Aguardando",
        },
        {
            "request_id": "req2",
            "tipo": "Renovação",
            "status_humano": "Finalizado",
            "criada_em": "27/12",
            "atualizada_em": "28/12",
            "actions": {"close": False, "cancel": False, "delete": True},
            "prazo": "",
            "observacoes": "",
        },
        {
            "request_id": "req3",
            "tipo": "RFB",
            "status_humano": "Cancelado",
            "criada_em": "26/12",
            "atualizada_em": "27/12",
            "actions": {"close": False, "cancel": False, "delete": False},
            "prazo": "",
            "observacoes": "Cancelado pelo cliente",
        },
    ]

    dummy._service.build_history_rows = MagicMock(return_value=rows)

    dummy._update_history_popup("client1", "ACME Corp", "12345678000190")

    # Validar 3 items no tree
    assert len(dummy._history_tree_popup._items) == 3
    assert "req1" in dummy._history_rows_by_id
    assert "req2" in dummy._history_rows_by_id
    assert "req3" in dummy._history_rows_by_id


def test_on_history_select_invalid_iid():
    """_on_history_select com iid não existente no _history_rows_by_id deve desabilitar botões."""
    dummy = DummyHistoryPopupMixin()
    dummy._history_tree_popup._selection = ["invalid_req"]
    dummy._history_tree_popup._items["invalid_req"] = {"values": ["AFE", "Em aberto", "28/12", "29/12"]}
    dummy._history_rows_by_id = {}  # Não tem invalid_req

    dummy._on_history_select()

    # Sem row, excluir fica normal (fallback)
    assert dummy._btn_finalizar.state_value == "disabled"
    assert dummy._btn_cancelar.state_value == "disabled"
    assert dummy._btn_excluir_popup.state_value == "normal"


def test_update_history_popup_loads_demandas():
    """_update_history_popup deve chamar _load_demandas_for_cliente."""
    dummy = DummyHistoryPopupMixin()

    demandas = [{"id": "req1", "request_type": "AFE"}]
    dummy._load_demandas_for_cliente = MagicMock(return_value=demandas)

    rows = [
        {
            "request_id": "req1",
            "tipo": "AFE",
            "status_humano": "Em aberto",
            "criada_em": "28/12",
            "atualizada_em": "29/12",
            "actions": {"close": True, "cancel": True, "delete": True},
            "prazo": "31/12",
            "observacoes": "Teste",
        }
    ]
    dummy._service.build_history_rows = MagicMock(return_value=rows)

    dummy._update_history_popup("client1", "ACME", "12345678000190")

    # Validar load foi chamado
    dummy._load_demandas_for_cliente.assert_called_once_with("client1")
    dummy._service.build_history_rows.assert_called_once()


def test_on_history_select_updates_vars_with_missing_keys():
    """_on_history_select deve lidar com row sem prazo/observacoes keys."""
    dummy = DummyHistoryPopupMixin()
    dummy._history_tree_popup._selection = ["req1"]
    dummy._history_tree_popup._items["req1"] = {"values": ["AFE", "Em aberto", "28/12", "29/12"]}

    # Row sem prazo/observacoes
    dummy._history_rows_by_id = {
        "req1": {
            "request_id": "req1",
            "actions": {"close": True, "cancel": False, "delete": True},
        }
    }

    dummy._on_history_select()

    # Deve usar "-" como default
    assert dummy._history_due_var._value == "-"
    assert dummy._history_notes_var._value == "-"
