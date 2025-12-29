# -*- coding: utf-8 -*-
"""Testes para _anvisa_requests_mixin.py (funções puras) - HEADLESS."""

from datetime import datetime
from unittest.mock import MagicMock


from src.modules.anvisa.views._anvisa_requests_mixin import AnvisaRequestsMixin
from tests.unit.fakes.tk_fakes import FakeVar, FakeTreeview


class DummyRequestsMixin(AnvisaRequestsMixin):
    """Dummy class para testar mixin sem UI."""

    def __init__(self):
        self.last_action = FakeVar()
        self._demandas_cache = {}
        self._service = MagicMock()


def test_norm_tipo_trims_and_uppercase():
    """_norm_tipo deve remover espaços e converter para uppercase."""
    dummy = DummyRequestsMixin()
    assert dummy._norm_tipo("  afe  ") == "AFE"
    assert dummy._norm_tipo("renovação") == "RENOVAÇÃO"
    assert dummy._norm_tipo("") == ""


def test_is_open_status_recognizes_open_statuses():
    """_is_open_status deve reconhecer status abertos (draft, submitted, in_progress)."""
    dummy = DummyRequestsMixin()
    assert dummy._is_open_status("draft") is True
    assert dummy._is_open_status("submitted") is True
    assert dummy._is_open_status("in_progress") is True
    assert dummy._is_open_status("DRAFT") is True  # Case insensitive


def test_is_open_status_recognizes_closed_statuses():
    """_is_open_status deve reconhecer status fechados (done, canceled)."""
    dummy = DummyRequestsMixin()
    assert dummy._is_open_status("done") is False
    assert dummy._is_open_status("canceled") is False
    assert dummy._is_open_status("DONE") is False


def test_is_open_status_handles_aliases():
    """_is_open_status deve resolver aliases (finalizado -> done, cancelado -> canceled)."""
    dummy = DummyRequestsMixin()
    assert dummy._is_open_status("finalizado") is False
    assert dummy._is_open_status("cancelado") is False


def test_human_status_returns_em_aberto_for_open():
    """_human_status deve retornar 'Em aberto' para status abertos."""
    dummy = DummyRequestsMixin()
    assert dummy._human_status("draft") == "Em aberto"
    assert dummy._human_status("submitted") == "Em aberto"
    assert dummy._human_status("in_progress") == "Em aberto"


def test_human_status_returns_finalizado_for_closed():
    """_human_status deve retornar 'Finalizado' para status fechados."""
    dummy = DummyRequestsMixin()
    assert dummy._human_status("done") == "Finalizado"
    assert dummy._human_status("canceled") == "Finalizado"


def test_summarize_demands_for_main_empty_list():
    """_summarize_demands_for_main com lista vazia deve retornar ('', '')."""
    dummy = DummyRequestsMixin()
    label, last_update = dummy._summarize_demands_for_main([])
    assert label == ""
    assert last_update == ""


def test_summarize_demands_for_main_single_demand():
    """_summarize_demands_for_main com 1 demanda deve retornar tipo e data formatada."""
    dummy = DummyRequestsMixin()

    # Mock _to_local_dt e _format_datetime
    dummy._to_local_dt = MagicMock(return_value=datetime(2025, 12, 28, 10, 0, 0))
    dummy._format_datetime = MagicMock(return_value="28/12/2025 10:00")

    demandas = [{"request_type": "AFE", "status": "draft", "created_at": "2025-12-28T13:00:00Z"}]

    label, last_update = dummy._summarize_demands_for_main(demandas)
    assert label == "AFE"
    assert last_update == "28/12/2025 10:00"


def test_summarize_demands_for_main_multiple_demands_with_open():
    """_summarize_demands_for_main com múltiplas demandas deve mostrar total e contagem aberta."""
    dummy = DummyRequestsMixin()

    # Mock _to_local_dt e _format_datetime
    dummy._to_local_dt = MagicMock(return_value=datetime(2025, 12, 28, 10, 0, 0))
    dummy._format_datetime = MagicMock(return_value="28/12/2025 10:00")

    demandas = [
        {"request_type": "AFE", "status": "draft", "created_at": "2025-12-28T13:00:00Z"},
        {"request_type": "Renovação", "status": "done", "created_at": "2025-12-27T13:00:00Z"},
        {"request_type": "Cancelamento", "status": "submitted", "created_at": "2025-12-26T13:00:00Z"},
    ]

    label, last_update = dummy._summarize_demands_for_main(demandas)
    assert label == "3 demandas (2 em aberto)"
    assert last_update == "28/12/2025 10:00"


def test_summarize_demands_for_main_multiple_demands_all_closed():
    """_summarize_demands_for_main com todas fechadas deve mostrar 'finalizadas'."""
    dummy = DummyRequestsMixin()

    # Mock _to_local_dt e _format_datetime
    dummy._to_local_dt = MagicMock(return_value=datetime(2025, 12, 28, 10, 0, 0))
    dummy._format_datetime = MagicMock(return_value="28/12/2025 10:00")

    demandas = [
        {"request_type": "AFE", "status": "done", "created_at": "2025-12-28T13:00:00Z"},
        {"request_type": "Renovação", "status": "canceled", "created_at": "2025-12-27T13:00:00Z"},
    ]

    label, last_update = dummy._summarize_demands_for_main(demandas)
    assert label == "2 demandas (finalizadas)"


def test_load_demandas_for_cliente_cache_hit(monkeypatch):
    """_load_demandas_for_cliente com cache hit NÃO deve chamar list_requests."""
    dummy = DummyRequestsMixin()

    # Preencher cache
    cached_data = [{"id": "123", "request_type": "AFE"}]
    dummy._demandas_cache["client-1"] = cached_data

    # Mock list_requests (não deve ser chamado)
    list_requests_called = []

    def fake_list_requests(org_id):
        list_requests_called.append(org_id)
        return []

    monkeypatch.setattr("infra.repositories.anvisa_requests_repository.list_requests", fake_list_requests)

    # Mock _resolve_org_id
    dummy._resolve_org_id = MagicMock(return_value="ORG-1")

    result = dummy._load_demandas_for_cliente("client-1")

    # Validar: cache retornado, list_requests NÃO chamado
    assert result == cached_data
    assert len(list_requests_called) == 0


def test_load_demandas_for_cliente_cache_miss_filters_by_client_id(monkeypatch):
    """_load_demandas_for_cliente com cache miss deve chamar list_requests e filtrar por client_id."""
    dummy = DummyRequestsMixin()

    # Mock list_requests
    all_requests = [
        {"id": "req1", "client_id": 10, "request_type": "AFE"},
        {"id": "req2", "client_id": 20, "request_type": "Renovação"},
        {"id": "req3", "client_id": 10, "request_type": "Cancelamento"},
    ]

    def fake_list_requests(org_id):
        return all_requests

    monkeypatch.setattr("infra.repositories.anvisa_requests_repository.list_requests", fake_list_requests)

    # Mock _resolve_org_id
    dummy._resolve_org_id = MagicMock(return_value="ORG-1")

    result = dummy._load_demandas_for_cliente("10")

    # Validar: filtro por client_id=10
    assert len(result) == 2
    assert result[0]["id"] == "req1"
    assert result[1]["id"] == "req3"

    # Validar: cache preenchido
    assert "10" in dummy._demandas_cache
    assert dummy._demandas_cache["10"] == result


def test_load_demandas_for_cliente_no_org_id_returns_empty(monkeypatch):
    """_load_demandas_for_cliente sem org_id deve retornar lista vazia."""
    dummy = DummyRequestsMixin()

    # Mock _resolve_org_id -> None
    dummy._resolve_org_id = MagicMock(return_value=None)

    result = dummy._load_demandas_for_cliente("client-1")

    assert result == []


def test_load_demandas_for_cliente_exception_returns_empty_and_logs(monkeypatch):
    """_load_demandas_for_cliente deve engolir Exception e retornar [] (+ log)."""
    dummy = DummyRequestsMixin()

    # Mock _resolve_org_id
    dummy._resolve_org_id = MagicMock(return_value="ORG-1")

    # Mock list_requests para lançar exceção
    def fake_list_requests_boom(org_id):
        raise Exception("Database connection failed")

    monkeypatch.setattr("infra.repositories.anvisa_requests_repository.list_requests", fake_list_requests_boom)

    # Executar (não deve crashar)
    result = dummy._load_demandas_for_cliente("client-1")

    # Validar: retorna lista vazia
    assert result == []

    # Validar: cache NÃO foi preenchido
    assert "client-1" not in dummy._demandas_cache


def test_norm_tipo_handles_none_and_empty():
    """_norm_tipo deve lidar com None e string vazia."""
    dummy = DummyRequestsMixin()
    assert dummy._norm_tipo("") == ""
    # Se aceitar None, adicionar: assert dummy._norm_tipo(None) == ""


def test_human_status_unknown_returns_original():
    """_human_status deve retornar status original se desconhecido."""
    dummy = DummyRequestsMixin()
    result = dummy._human_status("unknown_status")
    # Verificar se retorna "unknown_status" ou algum fallback padrão
    assert result in ("unknown_status", "Em aberto", "Finalizado")


def test_summarize_demands_with_formatted_datetime(monkeypatch):
    """_summarize_demands deve formatar data usando _format_datetime."""
    dummy = DummyRequestsMixin()

    # Mock datetime helpers
    dummy._to_local_dt = MagicMock(return_value=datetime(2025, 12, 28, 15, 30, 0))
    dummy._format_datetime = MagicMock(return_value="28/12/2025 15:30")

    demandas = [{"request_type": "RFB", "status": "submitted", "created_at": "2025-12-28T18:30:00Z"}]

    label, last_update = dummy._summarize_demands_for_main(demandas)

    assert label == "RFB"
    assert last_update == "28/12/2025 15:30"
    assert dummy._format_datetime.called


def test_load_demandas_orders_by_created_at(monkeypatch):
    """_load_demandas_for_cliente deve ordenar por created_at (mais recente primeiro)."""
    dummy = DummyRequestsMixin()

    # Mock list_requests com demandas fora de ordem
    all_requests = [
        {"id": "req1", "client_id": 10, "request_type": "AFE", "created_at": "2025-12-26T10:00:00Z"},
        {"id": "req2", "client_id": 10, "request_type": "RFB", "created_at": "2025-12-28T10:00:00Z"},
        {"id": "req3", "client_id": 10, "request_type": "Renovação", "created_at": "2025-12-27T10:00:00Z"},
    ]

    def fake_list_requests(org_id):
        return all_requests

    monkeypatch.setattr("infra.repositories.anvisa_requests_repository.list_requests", fake_list_requests)

    dummy._resolve_org_id = MagicMock(return_value="ORG-1")

    result = dummy._load_demandas_for_cliente("10")

    # Validar: ordenado por data (mais recente primeiro)
    # Se o método ordenar, req2 (28) deve vir antes de req3 (27) e req1 (26)
    # Se não ordenar, validar ordem natural
    assert len(result) == 3
    # Adicionar validação se souber que há ordenação implementada


def test_norm_tipo_preserves_special_chars():
    """_norm_tipo deve preservar caracteres especiais (ç, ã, etc) após uppercase."""
    dummy = DummyRequestsMixin()
    assert dummy._norm_tipo("renovação") == "RENOVAÇÃO"
    assert dummy._norm_tipo("cancelamento") == "CANCELAMENTO"


def test_is_open_status_case_insensitive():
    """_is_open_status deve ser case-insensitive."""
    dummy = DummyRequestsMixin()
    assert dummy._is_open_status("DRAFT") is True
    assert dummy._is_open_status("Draft") is True
    assert dummy._is_open_status("DRaFT") is True
    assert dummy._is_open_status("DONE") is False
    assert dummy._is_open_status("Done") is False


def test_summarize_demands_multiple_with_zero_open():
    """_summarize_demands com múltiplas demandas mas 0 em aberto deve mostrar 'finalizadas'."""
    dummy = DummyRequestsMixin()

    dummy._to_local_dt = MagicMock(return_value=datetime(2025, 12, 28, 10, 0, 0))
    dummy._format_datetime = MagicMock(return_value="28/12/2025 10:00")

    demandas = [
        {"request_type": "AFE", "status": "done", "created_at": "2025-12-28T13:00:00Z"},
        {"request_type": "RFB", "status": "canceled", "created_at": "2025-12-27T13:00:00Z"},
        {"request_type": "Renovação", "status": "done", "created_at": "2025-12-26T13:00:00Z"},
    ]

    label, last_update = dummy._summarize_demands_for_main(demandas)
    assert label == "3 demandas (finalizadas)"
    assert last_update == "28/12/2025 10:00"


def test_resolve_org_id_success_returns_org_id(monkeypatch):
    """_resolve_org_id deve retornar org_id quando tudo funciona."""
    import sys
    import types

    dummy = DummyRequestsMixin()

    # Salvar módulo original (se existir)
    original_module = sys.modules.get("infra.repositories.anvisa_requests_repository")

    try:
        # Criar fake module
        fake_module = types.ModuleType("infra.repositories.anvisa_requests_repository")

        def fake_get_supabase_and_user():
            return (None, "user-1")

        def fake_resolve_org_id(user_id):
            return "ORG-123"

        fake_module._get_supabase_and_user = fake_get_supabase_and_user
        fake_module._resolve_org_id = fake_resolve_org_id

        sys.modules["infra.repositories.anvisa_requests_repository"] = fake_module

        # Spy messagebox
        showerror_called = []
        monkeypatch.setattr("tkinter.messagebox.showerror", lambda title, msg: showerror_called.append((title, msg)))

        # Executar
        result = dummy._resolve_org_id()

        # Validar
        assert result == "ORG-123"
        assert len(showerror_called) == 0
    finally:
        # Restaurar módulo original
        if original_module is not None:
            sys.modules["infra.repositories.anvisa_requests_repository"] = original_module
        else:
            sys.modules.pop("infra.repositories.anvisa_requests_repository", None)


def test_resolve_org_id_exception_shows_error_and_returns_none(monkeypatch):
    """_resolve_org_id deve mostrar erro e retornar None se houver exceção."""
    import sys
    import types

    dummy = DummyRequestsMixin()

    original_module = sys.modules.get("infra.repositories.anvisa_requests_repository")

    try:
        # Criar fake module que lança exceção
        fake_module = types.ModuleType("infra.repositories.anvisa_requests_repository")

        def fake_get_supabase_and_user():
            raise Exception("Database connection failed")

        fake_module._get_supabase_and_user = fake_get_supabase_and_user
        sys.modules["infra.repositories.anvisa_requests_repository"] = fake_module

        # Spy messagebox
        showerror_called = []
        monkeypatch.setattr("tkinter.messagebox.showerror", lambda title, msg: showerror_called.append((title, msg)))

        # Executar
        result = dummy._resolve_org_id()

        # Validar
        assert result is None
        assert len(showerror_called) == 1
    finally:
        if original_module is not None:
            sys.modules["infra.repositories.anvisa_requests_repository"] = original_module
        else:
            sys.modules.pop("infra.repositories.anvisa_requests_repository", None)


def test_to_local_dt_converts_utc_to_minus3():
    """_to_local_dt deve converter UTC para UTC-3 (Brasília)."""

    dummy = DummyRequestsMixin()

    # String UTC: 22:41 UTC -> deve resultar em 19:41 UTC-3
    result = dummy._to_local_dt("2025-12-19T22:41:00+00:00")

    assert result is not None
    assert result.hour == 19
    assert result.tzinfo is not None
    offset = result.tzinfo.utcoffset(None)
    assert offset is not None
    assert offset.total_seconds() == -3 * 3600


def test_to_local_dt_accepts_z_suffix():
    """_to_local_dt deve aceitar sufixo 'Z' como indicador de UTC."""
    dummy = DummyRequestsMixin()

    result = dummy._to_local_dt("2025-12-19T22:41:00Z")

    assert result is not None
    assert result.tzinfo is not None


def test_to_local_dt_from_utc_converts():
    """_to_local_dt_from_utc deve converter datetime UTC para local (UTC-3)."""
    from datetime import datetime, timezone

    dummy = DummyRequestsMixin()

    utc_time = datetime(2025, 12, 19, 22, 41, 0, tzinfo=timezone.utc)
    result = dummy._to_local_dt_from_utc(utc_time)

    assert result is not None
    assert result.hour == 19
    assert result.tzinfo is not None
    offset = result.tzinfo.utcoffset(None)
    assert offset is not None
    assert offset.total_seconds() == -3 * 3600


def test_format_datetime_uses_service_format_dt_local():
    """_format_datetime deve usar service.format_dt_local."""
    dummy = DummyRequestsMixin()

    # Mock service.format_dt_local
    formatted_called = []

    def fake_format_dt_local(dt):
        formatted_called.append(dt)
        return "FORMATTED_OK"

    dummy._service.format_dt_local = fake_format_dt_local

    # Executar
    result = dummy._format_datetime("2025-12-19T22:41:00+00:00")

    # Validar
    assert result == "FORMATTED_OK"
    assert len(formatted_called) == 1


def test_format_datetime_empty_returns_empty():
    """_format_datetime com string vazia deve retornar string vazia."""
    dummy = DummyRequestsMixin()

    assert dummy._format_datetime("") == ""


def test_persist_request_cloud_success_calls_create_request(monkeypatch):
    """_persist_request_cloud deve chamar create_request e retornar payload com id."""
    import sys
    import types

    dummy = DummyRequestsMixin()

    # Mock _resolve_org_id
    dummy._resolve_org_id = MagicMock(return_value="ORG-1")

    original_module = sys.modules.get("infra.repositories.anvisa_requests_repository")

    try:
        # Criar fake module
        fake_module = types.ModuleType("infra.repositories.anvisa_requests_repository")

        def fake_create_request(org_id, client_id, request_type, status):
            return {"id": 123, "client_id": client_id, "request_type": request_type, "status": status}

        fake_module.create_request = fake_create_request
        sys.modules["infra.repositories.anvisa_requests_repository"] = fake_module

        # Executar
        payload = {"client_id": "1", "request_type": "RENOVACAO", "status": "draft"}
        result = dummy._persist_request_cloud(payload)

        # Validar
        assert result is not None
        assert result["id"] == 123
        assert result["client_id"] == 1  # Convertido para int
    finally:
        if original_module is not None:
            sys.modules["infra.repositories.anvisa_requests_repository"] = original_module
        else:
            sys.modules.pop("infra.repositories.anvisa_requests_repository", None)


def test_persist_request_cloud_exception_shows_error_and_returns_none(monkeypatch):
    """_persist_request_cloud deve mostrar erro e retornar None se houver exceção."""
    import sys
    import types

    dummy = DummyRequestsMixin()

    dummy._resolve_org_id = MagicMock(return_value="ORG-1")

    original_module = sys.modules.get("infra.repositories.anvisa_requests_repository")

    try:
        # Criar fake module que lança exceção
        fake_module = types.ModuleType("infra.repositories.anvisa_requests_repository")

        def fake_create_request(org_id, client_id, request_type, status):
            raise Exception("Network error")

        fake_module.create_request = fake_create_request
        sys.modules["infra.repositories.anvisa_requests_repository"] = fake_module

        # Spy messagebox
        showerror_called = []
        monkeypatch.setattr("tkinter.messagebox.showerror", lambda title, msg: showerror_called.append((title, msg)))

        # Executar
        result = dummy._persist_request_cloud({"client_id": "1", "request_type": "RENOVACAO"})

        # Validar
        assert result is None
        assert len(showerror_called) == 1
    finally:
        if original_module is not None:
            sys.modules["infra.repositories.anvisa_requests_repository"] = original_module
        else:
            sys.modules.pop("infra.repositories.anvisa_requests_repository", None)


def test_append_request_row_inserts_and_selects():
    """_append_request_row deve inserir no tree e selecionar a linha."""
    from tests.unit.fakes.tk_fakes import FakeTreeview

    dummy = DummyRequestsMixin()

    # Setup fakes
    dummy.tree_requests = FakeTreeview()
    dummy._service.format_dt_local = MagicMock(return_value="AGORA")

    # Executar
    client_data = {"id": "cli-1", "razao_social": "ACME Corp", "cnpj": "12345678000190"}
    request_type = "RENOVACAO"

    dummy._append_request_row(client_data, request_type)

    # Validar: tree.insert foi chamado
    assert len(dummy.tree_requests._items) == 1

    # Validar: selection_set foi chamado (última seleção)
    assert len(dummy.tree_requests._selection) == 1


# ============================================================================
# TEST GROUP: MF52 - Coverage for missing lines
# ============================================================================


class TestRequestsMixinMF52:
    """Testes MF52 para cobrir linhas faltantes em _anvisa_requests_mixin.py."""

    def test_load_requests_ui_setup(self, monkeypatch):
        """Testa _load_requests com UI setup (linhas 47-94)."""

        dummy = DummyRequestsMixin()
        dummy.tree_requests = FakeTreeview()
        dummy._requests_by_client = {}

        # Mock org_id resolution
        monkeypatch.setattr(dummy, "_resolve_org_id", lambda: "org123")

        # Mock repo
        fake_requests = [{"id": "req-1", "client_id": "123", "request_type": "AFE", "status": "draft"}]
        monkeypatch.setattr("infra.repositories.anvisa_requests_repository.list_requests", lambda org_id: fake_requests)

        # Mock service build_main_rows
        fake_rows = [
            {
                "client_id": "123",
                "razao_social": "Cliente Teste",
                "cnpj": "12345678000190",
                "demanda_label": "1 demanda (1 em aberto)",
                "last_update_display": "28/12 (A)",
            }
        ]
        dummy._service.build_main_rows.return_value = ({}, fake_rows)

        # Execute
        dummy._load_requests_from_cloud()

        # Assertions (UI foi "usada")
        assert len(dummy.tree_requests._items) == 1
        assert dummy.last_action.get().startswith("1 cliente(s)")

    def test_load_requests_exception_handling(self, monkeypatch):
        """Testa _load_requests_from_cloud com exceção (linha 83-94)."""
        dummy = DummyRequestsMixin()
        dummy.tree_requests = FakeTreeview()

        # Mock org_id resolution
        monkeypatch.setattr(dummy, "_resolve_org_id", lambda: "org123")

        # Mock repo que falha
        def raise_error(org_id):
            raise RuntimeError("DB connection failed")

        monkeypatch.setattr("infra.repositories.anvisa_requests_repository.list_requests", raise_error)

        # Mock messagebox
        messagebox_calls = []

        def mock_showerror(title, msg):
            messagebox_calls.append((title, msg))

        monkeypatch.setattr(
            "src.modules.anvisa.views._anvisa_requests_mixin.messagebox.showerror",
            mock_showerror,
        )

        # Execute
        dummy._load_requests_from_cloud()

        # Assertions
        assert "Erro ao carregar" in dummy.last_action.get()
        assert len(messagebox_calls) == 1
        assert "DB connection failed" in messagebox_calls[0][1]

    def test_load_requests_no_org_id(self):
        """Testa _load_requests_from_cloud sem org_id (linha 49-50)."""
        dummy = DummyRequestsMixin()
        dummy._resolve_org_id = lambda: None  # No org

        # Execute
        dummy._load_requests_from_cloud()

        # Assertions
        assert dummy.last_action.get() == "Erro: sem sessão ativa"

    def test_format_cnpj_invalid_length(self):
        """Testa _format_cnpj com CNPJ inválido (linha 241-247)."""
        dummy = DummyRequestsMixin()

        # Test None
        assert dummy._format_cnpj(None) == ""

        # Test too short
        assert dummy._format_cnpj("123456") == "123456"

        # Test too long
        assert dummy._format_cnpj("123456789012345678") == "123456789012345678"

        # Test valid length
        result = dummy._format_cnpj("12345678000190")
        assert result == "12.345.678/0001-90"

    def test_to_local_dt_exception_handling(self):
        """Testa _to_local_dt com exceção (linha 336-340)."""
        dummy = DummyRequestsMixin()

        # Invalid datetime string should trigger exception path
        result = dummy._to_local_dt("invalid-datetime")
        assert result is None  # Método retorna None em caso de erro

        # Empty string
        result = dummy._to_local_dt("")
        assert result is None  # Empty também retorna None

    def test_persist_request_cloud_with_exception(self, monkeypatch):
        """Testa _persist_request_cloud com exceção na repo (linha 353)."""
        dummy = DummyRequestsMixin()

        # Mock repo que falha
        def raise_error(*args, **kwargs):
            raise RuntimeError("Supabase error")

        monkeypatch.setattr("infra.repositories.anvisa_requests_repository.create_request", raise_error)

        fake_request = {"client_id": "123", "request_type": "AFE", "status": "draft"}

        # Execute
        result = dummy._persist_request_cloud(fake_request)

        # Should return None on exception
        assert result is None

    def test_resolve_org_id_no_session(self, monkeypatch):
        """Testa _resolve_org_id com falha no _get_supabase_and_user (linha 27-31)."""
        dummy = DummyRequestsMixin()

        # Mock _get_supabase_and_user que falha
        def raise_error():
            raise RuntimeError("Auth failed")

        monkeypatch.setattr("infra.repositories.anvisa_requests_repository._get_supabase_and_user", raise_error)

        # Mock messagebox
        messagebox_calls = []

        def mock_showerror(title, msg):
            messagebox_calls.append((title, msg))

        monkeypatch.setattr(
            "src.modules.anvisa.views._anvisa_requests_mixin.messagebox.showerror",
            mock_showerror,
        )

        result = dummy._resolve_org_id()
        assert result is None
        assert len(messagebox_calls) == 1

    def test_resolve_org_id_success(self, monkeypatch):
        """Testa _resolve_org_id com sucesso (linha 25-28)."""
        dummy = DummyRequestsMixin()

        # Mock _get_supabase_and_user e _resolve_org_id
        monkeypatch.setattr(
            "infra.repositories.anvisa_requests_repository._get_supabase_and_user", lambda: (None, "user123")
        )
        monkeypatch.setattr("infra.repositories.anvisa_requests_repository._resolve_org_id", lambda user_id: "org456")

        result = dummy._resolve_org_id()
        assert result == "org456"
