import types

import pytest

from src.core.services import clientes_service


def test_count_clients_success_updates_cache(monkeypatch):
    calls = []

    def fake_count():
        calls.append("count")
        return 42

    monkeypatch.setattr(clientes_service, "_count_clients_raw", fake_count)
    monkeypatch.setattr(clientes_service, "_LAST_CLIENTS_COUNT", 0)

    assert clientes_service.count_clients() == 42
    assert clientes_service.count_clients() == 42
    assert calls  # foi chamado ao menos uma vez

    # Se a chamada falhar após cache, retorna last-known (42)
    def raise_error():
        raise RuntimeError("boom")

    monkeypatch.setattr(clientes_service, "_count_clients_raw", raise_error)
    assert clientes_service.count_clients(max_retries=0) == 42


def test_count_clients_socket_10035_uses_last_known(monkeypatch):
    monkeypatch.setattr(clientes_service, "_LAST_CLIENTS_COUNT", 10)

    def fake_raise():
        err = OSError("blocked")
        err.winerror = 10035
        raise err

    monkeypatch.setattr(clientes_service, "_count_clients_raw", fake_raise)
    monkeypatch.setattr(clientes_service.time, "sleep", lambda _: None)

    assert clientes_service.count_clients(max_retries=1, base_delay=0) == 10


def test_count_clients_other_oserror_uses_last_known(monkeypatch):
    monkeypatch.setattr(clientes_service, "_LAST_CLIENTS_COUNT", 7)

    def fake_raise():
        raise OSError("other")

    monkeypatch.setattr(clientes_service, "_count_clients_raw", fake_raise)
    assert clientes_service.count_clients(max_retries=0) == 7


def test_checar_duplicatas_info_sem_conflitos(monkeypatch):
    monkeypatch.setattr(clientes_service, "find_cliente_by_cnpj_norm", lambda *a, **k: None)
    monkeypatch.setattr(clientes_service, "list_clientes", lambda: [])

    result = clientes_service.checar_duplicatas_info("", "", "", "")
    assert result["cnpj_conflict"] is None
    assert result["razao_conflicts"] == []
    assert result["numero_conflicts"] == []


def test_checar_duplicatas_info_com_cnpj_conflict(monkeypatch):
    conflict = types.SimpleNamespace(id=1, cnpj="1", cnpj_norm="abc", razao_social="X")
    monkeypatch.setattr(clientes_service, "find_cliente_by_cnpj_norm", lambda cnpj_norm, exclude_id=None: conflict)
    monkeypatch.setattr(clientes_service, "list_clientes", lambda: [])

    result = clientes_service.checar_duplicatas_info("", "abc", "", "")
    assert result["cnpj_conflict"] is conflict


def test_checar_duplicatas_info_com_razao_conflicts(monkeypatch):
    cliente_ok = types.SimpleNamespace(id=1, razao_social="A", cnpj="1", cnpj_norm="111")
    cliente_conf = types.SimpleNamespace(id=2, razao_social="Acme", cnpj="2", cnpj_norm="222")
    cliente_conf2 = types.SimpleNamespace(id=3, razao_social="Acme ", cnpj="3", cnpj_norm="333")

    monkeypatch.setattr(clientes_service, "find_cliente_by_cnpj_norm", lambda *a, **k: None)
    monkeypatch.setattr(clientes_service, "list_clientes", lambda: [cliente_ok, cliente_conf, cliente_conf2])

    result = clientes_service.checar_duplicatas_info("", "", "", "Acme")
    assert cliente_conf in result["razao_conflicts"]
    assert cliente_conf2 in result["razao_conflicts"]
    assert cliente_ok not in result["razao_conflicts"]


def test_checar_duplicatas_info_exclude_id(monkeypatch):
    cliente_conf = types.SimpleNamespace(id=5, razao_social="Acme", cnpj="2", cnpj_norm="abc")
    monkeypatch.setattr(
        clientes_service,
        "find_cliente_by_cnpj_norm",
        lambda cnpj_norm, exclude_id=None: None if exclude_id == cliente_conf.id else cliente_conf,
    )
    monkeypatch.setattr(clientes_service, "list_clientes", lambda: [cliente_conf])

    result = clientes_service.checar_duplicatas_info("", "abc", "", "Acme", exclude_id=cliente_conf.id)
    assert result["cnpj_conflict"] is None
    assert result["razao_conflicts"] == []


def test_salvar_cliente_cria_novo_quando_row_none(monkeypatch):
    inserted = []

    def fake_insert(**kw):
        inserted.append(kw)
        return 123

    monkeypatch.setattr(clientes_service, "insert_cliente", fake_insert)
    monkeypatch.setattr(clientes_service, "update_cliente", lambda *a, **k: None)
    monkeypatch.setattr(clientes_service, "_pasta_do_cliente", lambda *a, **k: "C:/fake/path")
    monkeypatch.setattr(clientes_service, "_migrar_pasta_se_preciso", lambda *a, **k: None)
    monkeypatch.setattr(clientes_service, "log_client_action", lambda *a, **k: None)
    monkeypatch.setattr(clientes_service, "get_current_user", lambda: "user")
    monkeypatch.setattr(clientes_service, "find_cliente_by_cnpj_norm", lambda *a, **k: None)

    pk, pasta = clientes_service.salvar_cliente(None, {"Raz�o Social": "Acme", "CNPJ": "  ", "Nome": "Jo�o"})
    assert pk == 123
    assert pasta == "C:/fake/path"
    assert inserted
    assert inserted[0]["nome"] == "Jo�o"


def test_salvar_cliente_atualiza_quando_row_preenchido(monkeypatch):
    updates = []

    monkeypatch.setattr(clientes_service, "insert_cliente", lambda **kw: 999)
    monkeypatch.setattr(clientes_service, "update_cliente", lambda pk, **kw: updates.append((pk, kw)))
    monkeypatch.setattr(clientes_service, "_pasta_do_cliente", lambda *a, **k: "C:/fake/path")
    monkeypatch.setattr(clientes_service, "_migrar_pasta_se_preciso", lambda *a, **k: None)
    monkeypatch.setattr(clientes_service, "log_client_action", lambda *a, **k: None)
    monkeypatch.setattr(clientes_service, "get_current_user", lambda: "user")
    monkeypatch.setattr(clientes_service, "find_cliente_by_cnpj_norm", lambda *a, **k: None)

    row = (5, "Acme", "123", "Nome", "999", "obs")
    pk, pasta = clientes_service.salvar_cliente(row, {"Raz�o Social": "Acme", "CNPJ": "123", "Nome": "Nome"})
    assert pk == 5
    assert pasta == "C:/fake/path"
    assert updates and updates[0][0] == 5


def test_salvar_cliente_bloqueia_cnpj_duplicado(monkeypatch):
    conflict = types.SimpleNamespace(id=9, razao_social="Acme", cnpj="123", cnpj_norm="123")
    monkeypatch.setattr(clientes_service, "find_cliente_by_cnpj_norm", lambda *a, **k: conflict)

    with pytest.raises(ValueError) as excinfo:
        clientes_service.salvar_cliente(None, {"Raz�o Social": "Acme", "CNPJ": "123", "Nome": "Nome"})
    assert "CNPJ j� cadastrado" in str(excinfo.value)


def test_salvar_cliente_requer_algum_campo():
    with pytest.raises(ValueError) as excinfo:
        clientes_service.salvar_cliente(None, {"Raz�o Social": "", "CNPJ": "", "Nome": "", "WhatsApp": ""})
    assert str(excinfo.value) == "Preencha pelo menos Raz�o Social, CNPJ, Nome ou WhatsApp."
