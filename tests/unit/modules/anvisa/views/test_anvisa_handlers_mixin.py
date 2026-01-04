# -*- coding: utf-8 -*-
"""Testes para _anvisa_handlers_mixin.py - HEADLESS."""

from unittest.mock import MagicMock


from src.modules.anvisa.views._anvisa_handlers_mixin import AnvisaHandlersMixin
from tests.unit.fakes.test_tk_fakes import FakeButton, FakeMenu, FakeTreeview, FakeVar


class DummyHandlersMixin(AnvisaHandlersMixin):
    """Dummy class para testar mixin sem UI."""

    def __init__(self):
        self.tree_requests = FakeTreeview()
        self._btn_excluir = FakeButton(state="disabled")
        self._main_ctx_menu = FakeMenu()
        self._requests_by_client = {}
        self._demandas_cache = {}
        self.last_action = FakeVar()
        self._controller = MagicMock()
        self._load_requests_from_cloud = MagicMock()
        self._open_history_popup = MagicMock()
        self._refresh_hub_dashboard_if_present = MagicMock()
        self._update_history_popup = MagicMock()
        self._resolve_org_id = MagicMock(return_value="org123")
        self._history_tree_popup = None
        self._ctx_client_id = None
        self._ctx_razao = None
        self._ctx_cnpj = None
        self._ctx_request_type = None
        self._ctx_request_id = None

    def winfo_toplevel(self):
        """Fake winfo_toplevel para permitir testes de sucesso."""
        return MagicMock()


def test_on_tree_select_enables_button_when_selection():
    """_on_tree_select deve habilitar botão quando há seleção."""
    dummy = DummyHandlersMixin()
    dummy.tree_requests._selection = ["item1"]

    event = MagicMock()
    dummy._on_tree_select(event)

    assert dummy._btn_excluir.state_value == "normal"


def test_on_tree_select_disables_button_when_no_selection():
    """_on_tree_select deve desabilitar botão quando não há seleção."""
    dummy = DummyHandlersMixin()
    dummy.tree_requests._selection = []

    event = MagicMock()
    dummy._on_tree_select(event)

    assert dummy._btn_excluir.state_value == "disabled"


def test_on_tree_right_click_sets_context_and_shows_menu():
    """_on_tree_right_click deve setar contexto e mostrar menu."""
    dummy = DummyHandlersMixin()

    # Configurar fake tree
    dummy.tree_requests.set_identify_row_result("client123")
    dummy.tree_requests._items["client123"] = {
        "values": ["123", "ACME Corp", "12.345.678/0001-90", "AFE", "28/12/2025"]
    }

    event = MagicMock(x=10, y=20, x_root=100, y_root=200)
    dummy._on_tree_right_click(event)

    # Validar contexto
    assert dummy._ctx_client_id == "123"
    assert dummy._ctx_razao == "ACME Corp"
    assert dummy._ctx_cnpj == "12.345.678/0001-90"
    assert dummy._ctx_request_type == "AFE"

    # Validar menu popup
    assert dummy._main_ctx_menu.popup_called
    assert dummy._main_ctx_menu.popup_x == 100
    assert dummy._main_ctx_menu.popup_y == 200


def test_ctx_delete_request_no_demands_shows_info(monkeypatch):
    """_ctx_delete_request sem demandas deve mostrar messagebox info."""
    dummy = DummyHandlersMixin()

    showinfo_called = []

    def fake_showinfo(title, message):
        showinfo_called.append((title, message))

    monkeypatch.setattr("tkinter.messagebox.showinfo", fake_showinfo)

    dummy._ctx_client_id = "client1"
    dummy._requests_by_client = {"client1": []}

    dummy._ctx_delete_request()

    assert len(showinfo_called) == 1
    assert "não possui demandas" in showinfo_called[0][1]


def test_ctx_delete_request_single_demand_confirm_false_no_action(monkeypatch):
    """_ctx_delete_request com 1 demanda e confirm=False não deve chamar controller."""
    dummy = DummyHandlersMixin()

    # Mock askyesno -> False
    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *args, **kwargs: False)

    dummy._ctx_client_id = "client1"
    dummy._ctx_razao = "ACME Corp"
    dummy._ctx_cnpj = "12.345.678/0001-90"
    dummy._requests_by_client = {"client1": [{"id": "req1", "request_type": "AFE"}]}

    dummy._ctx_delete_request()

    # Validar: controller NÃO chamado
    assert not dummy._controller.delete_request.called


def test_ctx_delete_request_single_demand_confirm_true_success(monkeypatch):
    """_ctx_delete_request com 1 demanda e confirm=True + success deve invalidar cache e recarregar."""
    dummy = DummyHandlersMixin()

    # Mock askyesno -> True
    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *args, **kwargs: True)

    dummy._controller.delete_request = MagicMock(return_value=True)
    dummy._ctx_client_id = "client1"
    dummy._ctx_razao = "ACME Corp"
    dummy._ctx_cnpj = "12.345.678/0001-90"
    dummy._requests_by_client = {"client1": [{"id": "req1", "request_type": "AFE"}]}
    dummy._demandas_cache = {"client1": []}

    dummy._ctx_delete_request()

    # Validar: controller chamado
    assert dummy._controller.delete_request.called
    assert dummy._controller.delete_request.call_args[0][0] == "req1"

    # Validar: caches invalidados
    assert "client1" not in dummy._demandas_cache
    assert "client1" not in dummy._requests_by_client

    # Validar: recarregar chamado
    assert dummy._load_requests_from_cloud.called

    # Validar: refresh hub chamado
    assert dummy._refresh_hub_dashboard_if_present.called

    # Validar: last_action setado
    assert "excluída" in dummy.last_action.get()

    # Validar: botão desabilitado
    assert dummy._btn_excluir.state_value == "disabled"


def test_ctx_delete_request_single_demand_controller_failure_shows_warning(monkeypatch):
    """_ctx_delete_request com controller retornando False deve mostrar showwarning."""
    dummy = DummyHandlersMixin()

    # Mock askyesno -> True
    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *args, **kwargs: True)

    # Mock showwarning
    showwarning_called = []

    def fake_showwarning(title, message):
        showwarning_called.append((title, message))

    monkeypatch.setattr("tkinter.messagebox.showwarning", fake_showwarning)

    dummy._controller.delete_request = MagicMock(return_value=False)
    dummy._ctx_client_id = "client1"
    dummy._ctx_razao = "ACME Corp"
    dummy._ctx_cnpj = "12.345.678/0001-90"
    dummy._requests_by_client = {"client1": [{"id": "req1", "request_type": "AFE"}]}

    dummy._ctx_delete_request()

    # Validar: showwarning chamado
    assert len(showwarning_called) == 1


def test_ctx_delete_request_multiple_demands_opens_history(monkeypatch):
    """_ctx_delete_request com 2+ demandas deve abrir histórico e mostrar info."""
    dummy = DummyHandlersMixin()

    showinfo_called = []

    def fake_showinfo(title, message):
        showinfo_called.append((title, message))

    monkeypatch.setattr("tkinter.messagebox.showinfo", fake_showinfo)

    dummy._ctx_client_id = "client1"
    dummy._ctx_razao = "ACME Corp"
    dummy._ctx_cnpj = "12.345.678/0001-90"
    dummy._requests_by_client = {
        "client1": [{"id": "req1", "request_type": "AFE"}, {"id": "req2", "request_type": "Renovação"}]
    }

    dummy._ctx_delete_request()

    # Validar: showinfo chamado
    assert len(showinfo_called) == 1
    assert "múltiplas demandas" in showinfo_called[0][1] or "histórico" in showinfo_called[0][1].lower()

    # Validar: _open_history_popup chamado
    assert dummy._open_history_popup.called


def test_get_client_info_for_event_from_embed():
    """_get_client_info_for_event deve obter dados do embed (prioridade 1)."""
    dummy = DummyHandlersMixin()

    dummy._requests_by_client = {
        "client1": [
            {"id": "req1", "clients": {"cnpj": "12345678000190", "razao_social": "ACME Corp"}},
            {"id": "req2", "clients": {"cnpj": "98765432000111", "razao_social": "Other Corp"}},
        ]
    }

    cnpj, razao = dummy._get_client_info_for_event("client1", "req1", "org1")

    assert cnpj == "12345678000190"
    assert razao == "ACME Corp"


def test_get_client_info_for_event_from_lookup(monkeypatch):
    """_get_client_info_for_event deve fazer lookup na tabela clients (prioridade 2)."""
    dummy = DummyHandlersMixin()

    dummy._requests_by_client = {"client1": [{"id": "req1"}]}  # Sem embed

    # Mock Supabase
    fake_resp = MagicMock()
    fake_resp.data = [{"cnpj": "11111111000111", "razao_social": "Lookup Corp"}]

    fake_table = MagicMock()
    fake_table.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = fake_resp

    fake_sb = MagicMock()
    fake_sb.table.return_value = fake_table

    monkeypatch.setattr("src.infra.supabase_client.get_supabase", lambda: fake_sb)

    cnpj, razao = dummy._get_client_info_for_event("client1", "req1", "org1")

    assert cnpj == "11111111000111"
    assert razao == "Lookup Corp"


def test_finalizar_demanda_already_finalized_shows_info_no_controller_call(monkeypatch):
    """_finalizar_demanda não deve chamar controller se status já é 'Finalizado'."""
    dummy = DummyHandlersMixin()

    # Criar popup tree fake
    from tests.unit.fakes.test_tk_fakes import FakeTreeview

    popup_tree = FakeTreeview()
    dummy._history_tree_popup = popup_tree

    # Inserir item com status "Finalizado"
    iid = popup_tree.insert("", "end", values=("RFB", "Finalizado", "2025-01-01", "obs"))
    popup_tree._selection = [iid]

    # Monkeypatch messagebox
    showinfo_called = []
    monkeypatch.setattr("tkinter.messagebox.showinfo", lambda title, msg: showinfo_called.append((title, msg)))

    # Executar
    dummy._finalizar_demanda("client1")

    # Validar: showinfo chamado
    assert len(showinfo_called) == 1
    assert "Demanda Finalizada" in showinfo_called[0][0] or "finalizada" in showinfo_called[0][1].lower()

    # Validar: controller NÃO foi chamado
    assert not dummy._controller.close_request.called


def test_finalizar_demanda_confirm_false_no_controller_call(monkeypatch):
    """_finalizar_demanda não deve chamar controller se usuário cancela confirmação."""
    dummy = DummyHandlersMixin()

    from tests.unit.fakes.test_tk_fakes import FakeTreeview

    popup_tree = FakeTreeview()
    dummy._history_tree_popup = popup_tree

    # Inserir item com status "Aguardando"
    iid = popup_tree.insert("", "end", values=("RFB", "Aguardando", "2025-01-01", "obs"))
    popup_tree._selection = [iid]

    # Monkeypatch askyesno retorna False
    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda title, msg, **kw: False)

    # Executar
    dummy._finalizar_demanda("client1")

    # Validar: controller NÃO foi chamado
    assert not dummy._controller.close_request.called


def test_finalizar_demanda_controller_returns_false_shows_warning(monkeypatch):
    """_finalizar_demanda deve mostrar showwarning se controller retorna False."""
    dummy = DummyHandlersMixin()

    from tests.unit.fakes.test_tk_fakes import FakeTreeview

    popup_tree = FakeTreeview()
    dummy._history_tree_popup = popup_tree

    iid = popup_tree.insert("", "end", values=("RFB", "Aguardando", "2025-01-01", "obs"))
    popup_tree._selection = [iid]

    # Monkeypatch askyesno retorna True
    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda title, msg, **kw: True)

    # Controller retorna False
    dummy._controller.close_request.return_value = False

    # Monkeypatch showwarning
    showwarning_called = []
    monkeypatch.setattr("tkinter.messagebox.showwarning", lambda title, msg: showwarning_called.append((title, msg)))

    # Executar
    dummy._finalizar_demanda("client1")

    # Validar: showwarning chamado
    assert len(showwarning_called) == 1
    assert "Aviso" in showwarning_called[0][0] or "não foi possível" in showwarning_called[0][1].lower()

    # Validar: caches NÃO foram invalidados (nenhum método foi chamado)
    assert not dummy._load_requests_from_cloud.called


def test_finalizar_demanda_controller_raises_exception_shows_error(monkeypatch):
    """_finalizar_demanda deve mostrar showerror se controller lança exceção."""
    dummy = DummyHandlersMixin()

    from tests.unit.fakes.test_tk_fakes import FakeTreeview

    popup_tree = FakeTreeview()
    dummy._history_tree_popup = popup_tree

    iid = popup_tree.insert("", "end", values=("RFB", "Aguardando", "2025-01-01", "obs"))
    popup_tree._selection = [iid]

    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda title, msg, **kw: True)

    # Controller lança exceção
    dummy._controller.close_request.side_effect = Exception("DB Error")

    # Monkeypatch showerror
    showerror_called = []
    monkeypatch.setattr("tkinter.messagebox.showerror", lambda title, msg: showerror_called.append((title, msg)))

    # Monkeypatch log_exception para aceitar **kwargs
    monkeypatch.setattr(
        "src.modules.anvisa.views._anvisa_handlers_mixin.log_exception", lambda log, msg, exc, **kw: None
    )

    # Executar (não deve crashar)
    dummy._finalizar_demanda("client1")

    # Validar: showerror chamado
    assert len(showerror_called) == 1
    assert "Erro" in showerror_called[0][0] or "erro" in showerror_called[0][1].lower()


def test_cancelar_demanda_confirm_false_no_controller_call(monkeypatch):
    """_cancelar_demanda não deve chamar controller se usuário cancela confirmação."""
    dummy = DummyHandlersMixin()

    from tests.unit.fakes.test_tk_fakes import FakeTreeview

    popup_tree = FakeTreeview()
    dummy._history_tree_popup = popup_tree

    iid = popup_tree.insert("", "end", values=("RFB", "Aguardando", "2025-01-01", "obs"))
    popup_tree._selection = [iid]

    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda title, msg, **kw: False)

    # Executar
    dummy._cancelar_demanda("client1")

    # Validar: controller NÃO foi chamado
    assert not dummy._controller.cancel_request.called


def test_cancelar_demanda_controller_returns_false_shows_warning(monkeypatch):
    """_cancelar_demanda deve mostrar showwarning se controller retorna False."""
    dummy = DummyHandlersMixin()

    from tests.unit.fakes.test_tk_fakes import FakeTreeview

    popup_tree = FakeTreeview()
    dummy._history_tree_popup = popup_tree

    iid = popup_tree.insert("", "end", values=("RFB", "Aguardando", "2025-01-01", "obs"))
    popup_tree._selection = [iid]

    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda title, msg, **kw: True)

    # Controller retorna False
    dummy._controller.cancel_request.return_value = False

    showwarning_called = []
    monkeypatch.setattr("tkinter.messagebox.showwarning", lambda title, msg: showwarning_called.append((title, msg)))

    # Executar
    dummy._cancelar_demanda("client1")

    # Validar: showwarning chamado
    assert len(showwarning_called) == 1
    assert "Aviso" in showwarning_called[0][0] or "não foi possível" in showwarning_called[0][1].lower()

    assert not dummy._load_requests_from_cloud.called


def test_cancelar_demanda_controller_raises_exception_shows_error(monkeypatch):
    """_cancelar_demanda deve mostrar showerror se controller lança exceção."""
    dummy = DummyHandlersMixin()

    from tests.unit.fakes.test_tk_fakes import FakeTreeview

    popup_tree = FakeTreeview()
    dummy._history_tree_popup = popup_tree

    iid = popup_tree.insert("", "end", values=("RFB", "Aguardando", "2025-01-01", "obs"))
    popup_tree._selection = [iid]

    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda title, msg, **kw: True)

    dummy._controller.cancel_request.side_effect = Exception("Network Error")

    showerror_called = []
    monkeypatch.setattr("tkinter.messagebox.showerror", lambda title, msg: showerror_called.append((title, msg)))

    monkeypatch.setattr(
        "src.modules.anvisa.views._anvisa_handlers_mixin.log_exception", lambda log, msg, exc, **kw: None
    )

    # Executar (não deve crashar)
    dummy._cancelar_demanda("client1")

    # Validar: showerror chamado
    assert len(showerror_called) == 1
    assert "Erro" in showerror_called[0][0] or "erro" in showerror_called[0][1].lower()


def test_ctx_delete_request_controller_raises_exception_shows_error(monkeypatch):
    """_ctx_delete_request deve mostrar showerror se controller lança exceção."""
    dummy = DummyHandlersMixin()

    dummy._ctx_client_id = "client1"
    dummy._ctx_razao = "ACME Corp"
    dummy._ctx_cnpj = "12345678000190"
    dummy._ctx_request_type = "RFB"
    dummy._ctx_request_id = "req1"

    # 1 demanda na lista
    dummy._requests_by_client = {
        "client1": [
            {"id": "req1", "tipo": "RFB", "status": "Aguardando"},
        ]
    }

    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda title, msg, **kw: True)

    # Controller lança exceção
    dummy._controller.delete_request.side_effect = Exception("RLS Violation")

    showerror_called = []
    monkeypatch.setattr("tkinter.messagebox.showerror", lambda title, msg: showerror_called.append((title, msg)))

    monkeypatch.setattr(
        "src.modules.anvisa.views._anvisa_handlers_mixin.log_exception", lambda log, msg, exc, **kw: None
    )
    monkeypatch.setattr(
        "src.modules.anvisa.views._anvisa_handlers_mixin.extract_postgrest_error", lambda exc: {"code": "42501"}
    )
    monkeypatch.setattr(
        "src.modules.anvisa.views._anvisa_handlers_mixin.user_message_from_error", lambda err, default: default
    )

    # Executar (não deve crashar)
    dummy._ctx_delete_request()

    # Validar: showerror chamado
    assert len(showerror_called) == 1
    assert "Erro" in showerror_called[0][0] or "erro" in showerror_called[0][1].lower()


def test_on_tree_right_click_no_iid_returns_early():
    """_on_tree_right_click sem iid deve retornar early sem crashar."""
    dummy = DummyHandlersMixin()
    dummy.tree_requests.set_identify_row_result("")

    event = MagicMock(x=10, y=20, x_root=100, y_root=200)

    # Não deve crashar
    dummy._on_tree_right_click(event)

    # Menu não deve ser mostrado
    assert not dummy._main_ctx_menu.popup_called


def test_on_tree_right_click_short_values_returns_early():
    """_on_tree_right_click com values < 3 deve retornar early."""
    dummy = DummyHandlersMixin()
    dummy.tree_requests.set_identify_row_result("client1")
    dummy.tree_requests._items["client1"] = {"values": ["123", "ACME"]}  # Só 2 valores

    event = MagicMock(x=10, y=20, x_root=100, y_root=200)

    dummy._on_tree_right_click(event)

    # Menu não deve ser mostrado
    assert not dummy._main_ctx_menu.popup_called


def test_ctx_open_history_calls_open_history_popup():
    """_ctx_open_history deve chamar _open_history_popup com dados de contexto."""
    dummy = DummyHandlersMixin()
    dummy._ctx_client_id = "client1"
    dummy._ctx_razao = "ACME Corp"
    dummy._ctx_cnpj = "12345678000190"

    dummy._ctx_open_history()

    # Validar chamada
    dummy._open_history_popup.assert_called_once_with("client1", "ACME Corp", "12345678000190", center=True)


def test_ctx_open_history_no_context_no_action():
    """_ctx_open_history sem contexto não deve chamar nada."""
    dummy = DummyHandlersMixin()
    dummy._ctx_client_id = None

    dummy._ctx_open_history()

    # Não deve crashar, não deve chamar popup
    dummy._open_history_popup.assert_not_called()


def test_on_delete_request_no_selection_returns_early():
    """_on_delete_request_clicked sem seleção deve retornar early."""
    dummy = DummyHandlersMixin()
    dummy.tree_requests._selection = []

    # Não deve crashar
    dummy._on_delete_request_clicked()

    # Controller não deve ser chamado
    dummy._controller.delete_request.assert_not_called()


def test_on_delete_request_short_values_safe():
    """_on_delete_request com values curtos não deve crashar."""
    dummy = DummyHandlersMixin()
    dummy.tree_requests._selection = ["client1"]
    dummy.tree_requests._items["client1"] = {"values": ["123"]}  # Só 1 valor
    dummy._requests_by_client = {"client1": [{"id": "req1"}]}

    # Não deve crashar (razao/cnpj vazios)
    # Mock askyesno para não travar
    import tkinter.messagebox

    original_askyesno = tkinter.messagebox.askyesno
    tkinter.messagebox.askyesno = MagicMock(return_value=False)

    dummy._on_delete_request_clicked()

    tkinter.messagebox.askyesno = original_askyesno


def test_finalizar_demanda_no_tree_returns_early():
    """_finalizar_demanda sem tree popup deve retornar early."""
    dummy = DummyHandlersMixin()
    dummy._history_tree_popup = None

    # Não deve crashar
    dummy._finalizar_demanda("client1")

    # Controller não chamado
    dummy._controller.finalize_request.assert_not_called()


def test_finalizar_demanda_no_selection_returns_early():
    """_finalizar_demanda sem seleção deve retornar early."""
    dummy = DummyHandlersMixin()
    dummy._history_tree_popup = FakeTreeview()
    dummy._history_tree_popup._selection = []

    dummy._finalizar_demanda("client1")

    dummy._controller.finalize_request.assert_not_called()


def test_finalizar_demanda_sem_demandas_row_returns_early():
    """_finalizar_demanda com row 'Sem demandas' deve retornar early."""
    dummy = DummyHandlersMixin()
    dummy._history_tree_popup = FakeTreeview()
    dummy._history_tree_popup._selection = ["iid1"]
    dummy._history_tree_popup._items["iid1"] = {"values": ["Sem demandas", "", "", ""]}

    dummy._finalizar_demanda("client1")

    dummy._controller.finalize_request.assert_not_called()


def test_finalizar_demanda_already_done_shows_info(monkeypatch):
    """_finalizar_demanda com status 'Finalizado' deve mostrar info."""
    dummy = DummyHandlersMixin()
    dummy._history_tree_popup = FakeTreeview()
    dummy._history_tree_popup._selection = ["req1"]
    dummy._history_tree_popup._items["req1"] = {"values": ["AFE", "Finalizado", "28/12", "29/12"]}

    showinfo_called = []
    monkeypatch.setattr("tkinter.messagebox.showinfo", lambda title, msg: showinfo_called.append((title, msg)))

    dummy._finalizar_demanda("client1")

    assert len(showinfo_called) == 1
    assert "já está finalizada" in showinfo_called[0][1]
    dummy._controller.finalize_request.assert_not_called()


def test_cancelar_demanda_no_tree_returns_early():
    """_cancelar_demanda sem tree popup deve retornar early."""
    dummy = DummyHandlersMixin()
    dummy._history_tree_popup = None

    dummy._cancelar_demanda("client1")

    dummy._controller.cancel_request.assert_not_called()


def test_cancelar_demanda_no_selection_returns_early():
    """_cancelar_demanda sem seleção deve retornar early."""
    dummy = DummyHandlersMixin()
    dummy._history_tree_popup = FakeTreeview()
    dummy._history_tree_popup._selection = []

    dummy._cancelar_demanda("client1")

    dummy._controller.cancel_request.assert_not_called()


def test_excluir_demanda_popup_no_tree_returns_early():
    """_excluir_demanda_popup sem tree deve retornar early."""
    dummy = DummyHandlersMixin()
    dummy._history_tree_popup = None

    dummy._excluir_demanda_popup("client1")

    dummy._controller.delete_request.assert_not_called()


def test_excluir_demanda_popup_no_selection_returns_early():
    """_excluir_demanda_popup sem seleção deve retornar early."""
    dummy = DummyHandlersMixin()
    dummy._history_tree_popup = FakeTreeview()
    dummy._history_tree_popup._selection = []

    dummy._excluir_demanda_popup("client1")

    dummy._controller.delete_request.assert_not_called()


def test_on_delete_request_clicked_multiple_demands_opens_history(monkeypatch):
    """_on_delete_request_clicked com 2+ demandas deve abrir histórico."""
    dummy = DummyHandlersMixin()
    dummy.tree_requests._selection = ["client1"]
    dummy.tree_requests._items["client1"] = {"values": ["123", "ACME Corp", "12.345.678/0001-90"]}
    dummy._requests_by_client = {"client1": [{"id": "req1"}, {"id": "req2"}]}

    showinfo_called = []
    monkeypatch.setattr("tkinter.messagebox.showinfo", lambda title, msg: showinfo_called.append((title, msg)))

    dummy._on_delete_request_clicked()

    # Deve abrir histórico
    dummy._open_history_popup.assert_called_once()
    # Deve mostrar aviso
    assert len(showinfo_called) == 1
    assert "2 demandas" in showinfo_called[0][1] or "múltiplas" in showinfo_called[0][1].lower()


def test_ctx_delete_request_single_demand_confirm_true_calls_controller(monkeypatch):
    """_ctx_delete_request com 1 demanda e confirm=True deve chamar controller."""
    dummy = DummyHandlersMixin()
    dummy._ctx_client_id = "client1"
    dummy._ctx_razao = "ACME Corp"
    dummy._ctx_cnpj = "12345678000190"
    dummy._requests_by_client = {"client1": [{"id": "req1", "request_type": "AFE"}]}

    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *args, **kwargs: True)
    dummy._controller.delete_request.return_value = True

    dummy._ctx_delete_request()

    # Controller deve ser chamado
    dummy._controller.delete_request.assert_called_once_with("req1", client_id="client1", request_type="AFE")
    dummy._load_requests_from_cloud.assert_called_once()


def test_ctx_delete_request_multiple_demands_opens_history_and_shows_info(monkeypatch):
    """_ctx_delete_request com 2+ demandas deve abrir histórico e avisar."""
    dummy = DummyHandlersMixin()
    dummy._ctx_client_id = "client1"
    dummy._ctx_razao = "ACME Corp"
    dummy._ctx_cnpj = "12345678000190"
    dummy._requests_by_client = {"client1": [{"id": "req1"}, {"id": "req2"}]}

    showinfo_called = []
    monkeypatch.setattr("tkinter.messagebox.showinfo", lambda title, msg: showinfo_called.append((title, msg)))

    dummy._ctx_delete_request()

    # Deve abrir histórico
    dummy._open_history_popup.assert_called_once()
    # Deve mostrar aviso
    assert len(showinfo_called) == 1


def test_finalizar_demanda_confirm_false_no_action(monkeypatch):
    """_finalizar_demanda com confirm=False não deve chamar controller."""
    dummy = DummyHandlersMixin()
    dummy._history_tree_popup = FakeTreeview()
    dummy._history_tree_popup._selection = ["req1"]
    dummy._history_tree_popup._items["req1"] = {"values": ["AFE", "Em aberto", "28/12", "29/12"]}

    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *args, **kwargs: False)

    dummy._finalizar_demanda("client1")

    dummy._controller.finalize_request.assert_not_called()


def test_cancelar_demanda_confirm_false_no_action(monkeypatch):
    """_cancelar_demanda com confirm=False não deve chamar controller."""
    dummy = DummyHandlersMixin()
    dummy._history_tree_popup = FakeTreeview()
    dummy._history_tree_popup._selection = ["req1"]
    dummy._history_tree_popup._items["req1"] = {"values": ["AFE", "Em aberto", "28/12", "29/12"]}

    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *args, **kwargs: False)

    dummy._cancelar_demanda("client1")

    dummy._controller.cancel_request.assert_not_called()


def test_excluir_demanda_popup_confirm_false_no_action(monkeypatch):
    """_excluir_demanda_popup com confirm=False não deve chamar controller."""
    dummy = DummyHandlersMixin()
    dummy._history_tree_popup = FakeTreeview()
    dummy._history_tree_popup._selection = ["req1"]
    dummy._history_tree_popup._items["req1"] = {"values": ["AFE", "Em aberto", "28/12", "29/12"]}

    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *args, **kwargs: False)

    dummy._excluir_demanda_popup("client1")

    dummy._controller.delete_request.assert_not_called()


def test_on_delete_request_clicked_success_reloads(monkeypatch):
    """_on_delete_request_clicked com sucesso deve recarregar lista."""
    dummy = DummyHandlersMixin()
    dummy.tree_requests._selection = ["client1"]
    dummy.tree_requests._items["client1"] = {"values": ["123", "ACME Corp", "12.345.678/0001-90"]}
    dummy._requests_by_client = {"client1": [{"id": "req1", "request_type": "AFE"}]}
    dummy._demandas_cache = {"client1": []}

    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *args, **kwargs: True)
    dummy._controller.delete_request.return_value = True

    dummy._on_delete_request_clicked()

    # Validar recarregamento
    dummy._load_requests_from_cloud.assert_called_once()
    dummy._refresh_hub_dashboard_if_present.assert_called_once()
    # Cache deve ser limpo
    assert "client1" not in dummy._demandas_cache
    assert "client1" not in dummy._requests_by_client


def test_on_delete_request_clicked_warning_shown(monkeypatch):
    """_on_delete_request_clicked com controller retornando False deve mostrar warning."""
    dummy = DummyHandlersMixin()
    dummy.tree_requests._selection = ["client1"]
    dummy.tree_requests._items["client1"] = {"values": ["123", "ACME Corp", "12.345.678/0001-90"]}
    dummy._requests_by_client = {"client1": [{"id": "req1", "request_type": "AFE"}]}

    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *args, **kwargs: True)
    dummy._controller.delete_request.return_value = False

    showwarning_called = []
    monkeypatch.setattr("tkinter.messagebox.showwarning", lambda title, msg: showwarning_called.append((title, msg)))

    dummy._on_delete_request_clicked()

    # Deve mostrar warning
    assert len(showwarning_called) == 1
    assert "não encontrada" in showwarning_called[0][1].lower() or "excluída" in showwarning_called[0][1].lower()


# ────────────────────────────────────────────────────────────────────────────────
# MF49: Novos testes para cobrir branches em falta
# ────────────────────────────────────────────────────────────────────────────────


def test_get_client_info_for_event_lookup_empty_response(monkeypatch):
    """_get_client_info_for_event com lookup retornando vazio deve retornar None/''."""
    dummy = DummyHandlersMixin()
    dummy._requests_by_client = {"client1": [{"id": "req1"}]}  # Sem embed

    # Mock Supabase com resposta vazia
    fake_resp = MagicMock()
    fake_resp.data = []

    fake_table = MagicMock()
    fake_table.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = fake_resp

    fake_sb = MagicMock()
    fake_sb.table.return_value = fake_table

    monkeypatch.setattr("src.infra.supabase_client.get_supabase", lambda: fake_sb)

    cnpj, razao = dummy._get_client_info_for_event("client1", "req1", "org1")

    # Lookup vazio retorna None e ""
    assert cnpj is None
    assert razao == ""


def test_get_client_info_for_event_lookup_exception(monkeypatch):
    """_get_client_info_for_event com exceção no lookup deve retornar None/'' e não crashar."""
    dummy = DummyHandlersMixin()
    dummy._requests_by_client = {"client1": [{"id": "req1"}]}  # Sem embed

    # Mock Supabase que lança exceção
    def raise_exception():
        raise RuntimeError("DB error")

    monkeypatch.setattr("src.infra.supabase_client.get_supabase", raise_exception)

    cnpj, razao = dummy._get_client_info_for_event("client1", "req1", "org1")

    # Exceção retorna valores default
    assert cnpj is None
    assert razao == ""


def test_on_tree_right_click_values_too_short_returns_early():
    """_on_tree_right_click com values < 3 deve retornar sem mostrar menu."""
    dummy = DummyHandlersMixin()

    # Configurar item com apenas 2 values
    dummy.tree_requests.set_identify_row_result("client123")
    dummy.tree_requests._items["client123"] = {"values": ["valor1", "valor2"]}  # Só 2

    event = MagicMock(x=10, y=20, x_root=100, y_root=200)
    dummy._on_tree_right_click(event)

    # Menu NÃO deve ser aberto
    assert not dummy._main_ctx_menu.popup_called


def test_on_tree_right_click_no_identify_returns_early():
    """_on_tree_right_click sem identify_row retorna antes de tudo."""
    dummy = DummyHandlersMixin()

    # identify_row retorna None
    dummy.tree_requests.set_identify_row_result(None)

    event = MagicMock(x=10, y=20, x_root=100, y_root=200)
    dummy._on_tree_right_click(event)

    # Menu NÃO deve ser aberto
    assert not dummy._main_ctx_menu.popup_called


def test_finalizar_demanda_no_popup_tree_returns_early():
    """_finalizar_demanda sem _history_tree_popup deve retornar imediatamente."""
    dummy = DummyHandlersMixin()
    dummy._history_tree_popup = None

    # Não deve crashar
    dummy._finalizar_demanda("client1")

    # Controller não foi chamado
    dummy._controller.close_request.assert_not_called()


def test_finalizar_demanda_sem_demandas_item_returns_early():
    """_finalizar_demanda com item 'Sem demandas' deve retornar."""
    dummy = DummyHandlersMixin()
    popup_tree = FakeTreeview()
    iid = popup_tree.insert("", "end", values=("Sem demandas", "", "", ""))
    popup_tree._selection = [iid]
    dummy._history_tree_popup = popup_tree

    dummy._finalizar_demanda("client1")

    dummy._controller.close_request.assert_not_called()


def test_cancelar_demanda_no_popup_tree_returns_early():
    """_cancelar_demanda sem _history_tree_popup deve retornar."""
    dummy = DummyHandlersMixin()
    dummy._history_tree_popup = None

    dummy._cancelar_demanda("client1")

    dummy._controller.cancel_request.assert_not_called()


def test_cancelar_demanda_sem_demandas_item_returns_early():
    """_cancelar_demanda com item 'Sem demandas' deve retornar."""
    dummy = DummyHandlersMixin()
    popup_tree = FakeTreeview()
    iid = popup_tree.insert("", "end", values=("Sem demandas", "", "", ""))
    popup_tree._selection = [iid]
    dummy._history_tree_popup = popup_tree

    dummy._cancelar_demanda("client1")

    dummy._controller.cancel_request.assert_not_called()


def test_cancelar_demanda_already_finalizado_shows_info(monkeypatch):
    """_cancelar_demanda com status 'Finalizado' deve mostrar info."""
    dummy = DummyHandlersMixin()
    popup_tree = FakeTreeview()
    iid = popup_tree.insert("", "end", values=("AFE", "Finalizado", "28/12", "obs"))
    popup_tree._selection = [iid]
    dummy._history_tree_popup = popup_tree

    showinfo_called = []
    monkeypatch.setattr("tkinter.messagebox.showinfo", lambda title, msg: showinfo_called.append((title, msg)))

    dummy._cancelar_demanda("client1")

    assert len(showinfo_called) == 1
    assert "finalizada" in showinfo_called[0][1].lower()
    dummy._controller.cancel_request.assert_not_called()


def test_excluir_demanda_popup_no_popup_tree_returns_early():
    """_excluir_demanda_popup sem _history_tree_popup deve retornar."""
    dummy = DummyHandlersMixin()
    dummy._history_tree_popup = None

    dummy._excluir_demanda_popup("client1")

    dummy._controller.delete_request.assert_not_called()


def test_excluir_demanda_popup_sem_demandas_item_returns_early():
    """_excluir_demanda_popup com item 'Sem demandas' deve retornar."""
    dummy = DummyHandlersMixin()
    popup_tree = FakeTreeview()
    iid = popup_tree.insert("", "end", values=("Sem demandas", "", "", ""))
    popup_tree._selection = [iid]
    dummy._history_tree_popup = popup_tree

    dummy._excluir_demanda_popup("client1")

    dummy._controller.delete_request.assert_not_called()


def test_on_delete_request_clicked_no_selection_returns_early():
    """_on_delete_request_clicked sem seleção deve retornar."""
    dummy = DummyHandlersMixin()
    dummy.tree_requests._selection = []

    dummy._on_delete_request_clicked()

    dummy._controller.delete_request.assert_not_called()


def test_on_delete_request_clicked_no_demands_shows_info(monkeypatch):
    """_on_delete_request_clicked sem demandas deve mostrar info."""
    dummy = DummyHandlersMixin()
    dummy.tree_requests._selection = ["client1"]
    dummy.tree_requests._items["client1"] = {"values": ["123", "ACME Corp", "12.345.678/0001-90"]}
    dummy._requests_by_client = {"client1": []}

    showinfo_called = []
    monkeypatch.setattr("tkinter.messagebox.showinfo", lambda title, msg: showinfo_called.append((title, msg)))

    dummy._on_delete_request_clicked()

    assert len(showinfo_called) == 1
    assert "não possui demandas" in showinfo_called[0][1]


def test_on_delete_request_clicked_confirm_false_no_action(monkeypatch):
    """_on_delete_request_clicked com confirm=False não deve chamar controller."""
    dummy = DummyHandlersMixin()
    dummy.tree_requests._selection = ["client1"]
    dummy.tree_requests._items["client1"] = {"values": ["123", "ACME Corp", "12.345.678/0001-90"]}
    dummy._requests_by_client = {"client1": [{"id": "req1", "request_type": "AFE"}]}

    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *args, **kwargs: False)

    dummy._on_delete_request_clicked()

    dummy._controller.delete_request.assert_not_called()


# ────────────────────────────────────────────────────────────────────────────────
# MF49: Testes de caminhos de sucesso (linhas 386-469, 554-637, 700-815)
# ────────────────────────────────────────────────────────────────────────────────


def test_finalizar_demanda_success_path(monkeypatch):
    """_finalizar_demanda caminho de sucesso completo."""
    dummy = DummyHandlersMixin()
    popup_tree = FakeTreeview()
    iid = popup_tree.insert("", "end", values=("AFE", "Aguardando", "28/12", "obs"))
    popup_tree._selection = [iid]
    dummy._history_tree_popup = popup_tree
    dummy._ctx_razao = "ACME Corp"
    dummy._ctx_cnpj = "12345678000190"
    dummy._requests_by_client = {"client1": [{"id": iid, "due_date": "2025-12-28"}]}

    # Mock dos messageboxes
    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *args, **kwargs: True)
    showinfo_called = []
    monkeypatch.setattr("tkinter.messagebox.showinfo", lambda title, msg: showinfo_called.append((title, msg)))

    # Mock do controller retornando sucesso
    dummy._controller.close_request.return_value = True

    # Mock das importações do hub (evitar side-effects)
    monkeypatch.setattr(
        "src.modules.anvisa.views._anvisa_handlers_mixin.log_exception",
        lambda *args, **kwargs: None,
    )

    # Mock do recent_activity_store para evitar imports complexos
    fake_store = MagicMock()
    monkeypatch.setattr(
        "src.modules.hub.recent_activity_store.get_recent_activity_store",
        lambda: fake_store,
    )
    monkeypatch.setattr(
        "src.modules.hub.async_runner.HubAsyncRunner",
        MagicMock,
    )
    monkeypatch.setattr(
        "src.core.session.get_current_user",
        lambda: MagicMock(email="user@test.com", uid="user123"),
    )

    # Executar
    dummy._finalizar_demanda("client1")

    # Validar: controller chamado
    dummy._controller.close_request.assert_called_once()

    # Validar: caches invalidados
    assert "client1" not in dummy._demandas_cache
    assert "client1" not in dummy._requests_by_client

    # Validar: reload chamado
    dummy._load_requests_from_cloud.assert_called_once()

    # Validar: refresh hub chamado
    dummy._refresh_hub_dashboard_if_present.assert_called_once()

    # Validar: showinfo de sucesso
    assert len(showinfo_called) == 1
    assert "sucesso" in showinfo_called[0][1].lower()


def test_cancelar_demanda_success_path(monkeypatch):
    """_cancelar_demanda caminho de sucesso completo."""
    dummy = DummyHandlersMixin()
    popup_tree = FakeTreeview()
    iid = popup_tree.insert("", "end", values=("AFE", "Aguardando", "28/12", "obs"))
    popup_tree._selection = [iid]
    dummy._history_tree_popup = popup_tree
    dummy._ctx_razao = "ACME Corp"
    dummy._ctx_cnpj = "12345678000190"
    dummy._requests_by_client = {"client1": [{"id": iid, "due_date": "2025-12-28"}]}

    # Mock dos messageboxes
    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *args, **kwargs: True)
    showinfo_called = []
    monkeypatch.setattr("tkinter.messagebox.showinfo", lambda title, msg: showinfo_called.append((title, msg)))

    # Mock do controller retornando sucesso
    dummy._controller.cancel_request.return_value = True

    # Mocks para evitar imports complexos
    fake_store = MagicMock()
    monkeypatch.setattr(
        "src.modules.hub.recent_activity_store.get_recent_activity_store",
        lambda: fake_store,
    )
    monkeypatch.setattr(
        "src.modules.hub.async_runner.HubAsyncRunner",
        MagicMock,
    )
    monkeypatch.setattr(
        "src.core.session.get_current_user",
        lambda: MagicMock(email="user@test.com", uid="user123"),
    )

    # Executar
    dummy._cancelar_demanda("client1")

    # Validar: controller chamado
    dummy._controller.cancel_request.assert_called_once()

    # Validar: caches invalidados
    assert "client1" not in dummy._demandas_cache
    assert "client1" not in dummy._requests_by_client

    # Validar: reload chamado
    dummy._load_requests_from_cloud.assert_called_once()

    # Validar: showinfo de sucesso
    assert len(showinfo_called) == 1
    assert "sucesso" in showinfo_called[0][1].lower()


def test_excluir_demanda_popup_success_path(monkeypatch):
    """_excluir_demanda_popup caminho de sucesso completo."""
    dummy = DummyHandlersMixin()
    popup_tree = FakeTreeview()
    iid = popup_tree.insert("", "end", values=("AFE", "Aguardando", "28/12", "obs"))
    popup_tree._selection = [iid]
    dummy._history_tree_popup = popup_tree
    dummy._ctx_razao = "ACME Corp"
    dummy._ctx_cnpj = "12345678000190"
    dummy._requests_by_client = {"client1": [{"id": iid, "due_date": "2025-12-28"}]}

    # Mock dos messageboxes
    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *args, **kwargs: True)
    showinfo_called = []
    monkeypatch.setattr("tkinter.messagebox.showinfo", lambda title, msg: showinfo_called.append((title, msg)))

    # Mock do controller retornando sucesso
    dummy._controller.delete_request.return_value = True

    # Mocks para evitar imports complexos
    fake_store = MagicMock()
    monkeypatch.setattr(
        "src.modules.hub.recent_activity_store.get_recent_activity_store",
        lambda: fake_store,
    )
    monkeypatch.setattr(
        "src.modules.hub.async_runner.HubAsyncRunner",
        MagicMock,
    )
    monkeypatch.setattr(
        "src.core.session.get_current_user",
        lambda: MagicMock(email="user@test.com", uid="user123"),
    )

    # Executar
    dummy._excluir_demanda_popup("client1")

    # Validar: controller chamado
    dummy._controller.delete_request.assert_called_once()

    # Validar: caches invalidados
    assert "client1" not in dummy._demandas_cache
    assert "client1" not in dummy._requests_by_client

    # Validar: reload chamado
    dummy._load_requests_from_cloud.assert_called_once()

    # Validar: showinfo de sucesso
    assert len(showinfo_called) == 1
    assert "sucesso" in showinfo_called[0][1].lower()


def test_ctx_delete_request_exception_path(monkeypatch):
    """_ctx_delete_request com exceção no controller deve mostrar showerror."""
    dummy = DummyHandlersMixin()
    dummy._ctx_client_id = "client1"
    dummy._ctx_razao = "ACME Corp"
    dummy._ctx_cnpj = "12345678000190"
    dummy._requests_by_client = {"client1": [{"id": "req1", "request_type": "AFE"}]}

    # Mock askyesno -> True
    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *args, **kwargs: True)

    # Mock controller que lança exceção
    dummy._controller.delete_request.side_effect = Exception("DB Error")

    # Mock log_exception
    monkeypatch.setattr(
        "src.modules.anvisa.views._anvisa_handlers_mixin.log_exception",
        lambda *args, **kwargs: None,
    )

    # Mock showerror
    showerror_called = []
    monkeypatch.setattr("tkinter.messagebox.showerror", lambda title, msg: showerror_called.append((title, msg)))

    # Executar
    dummy._ctx_delete_request()

    # Validar: showerror chamado
    assert len(showerror_called) == 1
    assert "Erro" in showerror_called[0][0]
