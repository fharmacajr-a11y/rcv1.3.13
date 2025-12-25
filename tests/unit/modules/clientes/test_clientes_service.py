import types

import pytest

from src.core.services import clientes_service


def test_count_clients_success_updates_cache(monkeypatch):
    calls = []

    def fake_count():
        calls.append("count")
        return 42

    monkeypatch.setattr(clientes_service, "_count_clients_raw", fake_count)
    # Reseta o cache para 0 antes do teste
    clientes_service._clients_cache.count = 0

    assert clientes_service.count_clients() == 42
    assert clientes_service.count_clients() == 42
    assert calls  # foi chamado ao menos uma vez

    # Se a chamada falhar após cache, retorna last-known (42)
    def raise_error():
        raise RuntimeError("boom")

    monkeypatch.setattr(clientes_service, "_count_clients_raw", raise_error)
    assert clientes_service.count_clients(max_retries=0) == 42


def test_count_clients_socket_10035_uses_last_known(monkeypatch):
    # Define o cache com valor conhecido antes do teste
    clientes_service._clients_cache.count = 10

    def fake_raise():
        err = OSError("blocked")
        err.winerror = 10035
        raise err

    monkeypatch.setattr(clientes_service, "_count_clients_raw", fake_raise)
    monkeypatch.setattr(clientes_service.time, "sleep", lambda _: None)

    assert clientes_service.count_clients(max_retries=1, base_delay=0) == 10


def test_count_clients_other_oserror_uses_last_known(monkeypatch):
    # Define o cache com valor conhecido antes do teste
    clientes_service._clients_cache.count = 7

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
    monkeypatch.setattr(clientes_service, "CLOUD_ONLY", False)

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

    pk, pasta = clientes_service.salvar_cliente(None, {"Razão Social": "Acme", "CNPJ": "  ", "Nome": "João"})
    assert pk == 123
    assert pasta == "C:/fake/path"
    assert inserted
    assert inserted[0]["nome"] == "João"


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
    pk, pasta = clientes_service.salvar_cliente(row, {"Razão Social": "Acme", "CNPJ": "123", "Nome": "Nome"})
    assert pk == 5
    assert pasta == "C:/fake/path"
    assert updates and updates[0][0] == 5


def test_salvar_cliente_bloqueia_cnpj_duplicado(monkeypatch):
    conflict = types.SimpleNamespace(id=9, razao_social="Acme", cnpj="123", cnpj_norm="123")
    monkeypatch.setattr(clientes_service, "find_cliente_by_cnpj_norm", lambda *a, **k: conflict)

    with pytest.raises(ValueError) as excinfo:
        clientes_service.salvar_cliente(None, {"Razão Social": "Acme", "CNPJ": "123", "Nome": "Nome"})
    assert "CNPJ já cadastrado" in str(excinfo.value)


def test_salvar_cliente_requer_algum_campo():
    with pytest.raises(ValueError) as excinfo:
        clientes_service.salvar_cliente(None, {"Razão Social": "", "CNPJ": "", "Nome": "", "WhatsApp": ""})
    assert str(excinfo.value) == "Preencha pelo menos Razão Social, CNPJ, Nome ou WhatsApp."


# ========== Testes Expandidos (Fase 21) ==========


def test_count_clients_retry_success_after_10035(monkeypatch):
    """Testa retry bem-sucedido após erro 10035 (linhas 39-40)"""
    attempts = []

    def fake_count():
        attempts.append(1)
        if len(attempts) == 1:
            err = OSError("blocked")
            err.winerror = 10035
            raise err
        return 50

    monkeypatch.setattr(clientes_service, "_count_clients_raw", fake_count)
    # Reseta o cache para 0 antes do teste
    clientes_service._clients_cache.count = 0
    monkeypatch.setattr(clientes_service.time, "sleep", lambda _: None)

    result = clientes_service.count_clients(max_retries=2, base_delay=0.1)
    assert result == 50
    assert len(attempts) == 2


def test_count_clients_raw_executa_query_real(monkeypatch):
    """Testa _count_clients_raw para cobrir linhas 39-40"""
    import types

    # Mock do supabase.table() que retorna query builder
    class MockQuery:
        def select(self, *args, **kwargs):
            return self

        def is_(self, *args, **kwargs):
            return self

    class MockResponse:
        count = 42

    monkeypatch.setattr(clientes_service, "supabase", types.SimpleNamespace(table=lambda t: MockQuery()))
    monkeypatch.setattr(clientes_service, "exec_postgrest", lambda q: MockResponse())

    result = clientes_service._count_clients_raw()
    assert result == 42


def test_count_clients_raw_retorna_zero_quando_count_none(monkeypatch):
    """Testa _count_clients_raw quando resp.count é None"""
    import types

    class MockQuery:
        def select(self, *args, **kwargs):
            return self

        def is_(self, *args, **kwargs):
            return self

    class MockResponse:
        count = None

    monkeypatch.setattr(clientes_service, "supabase", types.SimpleNamespace(table=lambda t: MockQuery()))
    monkeypatch.setattr(clientes_service, "exec_postgrest", lambda q: MockResponse())

    result = clientes_service._count_clients_raw()
    assert result == 0


def test_normalize_payload_extrai_campos_corretamente(monkeypatch):
    """Testa extração de campos do payload"""
    valores = {
        "Razão Social": "  Acme Inc  ",
        "CNPJ": "12345678000190",
        "Nome": "João",
        "WhatsApp": "11999999999",
        "Observações": "Cliente VIP",
    }

    monkeypatch.setattr(clientes_service, "normalize_cnpj_norm", lambda cnpj: cnpj.strip())

    razao, cnpj, cnpj_norm, nome, numero, obs = clientes_service._normalize_payload(valores)

    assert razao == "Acme Inc"
    assert cnpj == "12345678000190"
    assert nome == "João"
    assert numero == "11999999999"
    assert obs == "Cliente VIP"


def test_normalize_payload_com_campos_vazios():
    """Testa normalização quando campos estão vazios"""
    valores = {"Razão Social": "   ", "CNPJ": "", "Nome": "", "WhatsApp": ""}

    razao, cnpj, cnpj_norm, nome, numero, obs = clientes_service._normalize_payload(valores)

    assert razao == ""
    assert cnpj == ""
    assert nome == ""
    assert numero == ""
    assert obs == ""


def test_normalize_payload_usa_alias_de_campos():
    """Testa que _normalize_payload aceita vários aliases de campos"""
    valores = {"razao_social": "Empresa X", "cnpj": "123", "nome": "Pedro", "Telefone": "999", "Obs": "teste"}

    razao, cnpj, cnpj_norm, nome, numero, obs = clientes_service._normalize_payload(valores)

    assert razao == "Empresa X"
    assert cnpj == "123"
    assert nome == "Pedro"
    assert numero == "999"
    assert obs == "teste"


def test_checar_duplicatas_razao_sem_cnpj_norm_ambos(monkeypatch):
    """Testa conflito de razão quando ambos clientes não têm CNPJ normalizado (linhas 153-155)"""
    cliente_sem_cnpj = types.SimpleNamespace(id=10, razao_social="Acme", cnpj="", cnpj_norm="")

    monkeypatch.setattr(clientes_service, "find_cliente_by_cnpj_norm", lambda *a, **k: None)
    monkeypatch.setattr(clientes_service, "list_clientes", lambda: [cliente_sem_cnpj])

    # Buscar cliente com mesma razão mas sem CNPJ em ambos
    result = clientes_service.checar_duplicatas_info("", "", "", "Acme")

    # Deve retornar lista vazia porque ambos não têm CNPJ normalizado
    assert result["razao_conflicts"] == []


def test_checar_duplicatas_razao_com_cnpj_norm_diferente(monkeypatch):
    """Testa conflito de razão quando cliente tem cnpj_norm no atributo"""
    cliente_com_attr = types.SimpleNamespace(id=11, razao_social="Acme Corp", cnpj="999", cnpj_norm="999norm")

    monkeypatch.setattr(clientes_service, "find_cliente_by_cnpj_norm", lambda *a, **k: None)
    monkeypatch.setattr(clientes_service, "list_clientes", lambda: [cliente_com_attr])
    monkeypatch.setattr(clientes_service, "normalize_cnpj_norm", lambda cnpj: f"{cnpj}norm")
    monkeypatch.setattr(clientes_service, "CLOUD_ONLY", False)

    # Buscar com razão igual mas CNPJ diferente
    result = clientes_service.checar_duplicatas_info("", "888", "", "Acme Corp")

    # Deve detectar conflito porque razão é igual mas CNPJs diferentes
    assert cliente_com_attr in result["razao_conflicts"]


def test_checar_duplicatas_razao_mesmo_cnpj_nao_conflita(monkeypatch):
    """Testa que clientes com mesma razão e mesmo CNPJ não geram conflito"""
    cliente_ok = types.SimpleNamespace(id=12, razao_social="Acme", cnpj="123", cnpj_norm="123norm")

    monkeypatch.setattr(clientes_service, "find_cliente_by_cnpj_norm", lambda *a, **k: None)
    monkeypatch.setattr(clientes_service, "list_clientes", lambda: [cliente_ok])
    monkeypatch.setattr(clientes_service, "normalize_cnpj_norm", lambda cnpj: f"{cnpj}norm")

    # Buscar com mesma razão e mesmo CNPJ
    result = clientes_service.checar_duplicatas_info("", "123", "", "Acme")

    # Não deve gerar conflito
    assert result["razao_conflicts"] == []


def test_pasta_do_cliente_quando_cloud_only_false(monkeypatch):
    """Testa _pasta_do_cliente com CLOUD_ONLY=False (linhas 169-174)"""
    calls = {"ensure": [], "write": []}

    monkeypatch.setattr(clientes_service, "safe_base_from_fields", lambda *a: "base_123")
    monkeypatch.setattr(clientes_service, "DOCS_DIR", "C:/docs")
    monkeypatch.setattr(clientes_service, "CLOUD_ONLY", False)
    monkeypatch.setattr(clientes_service, "ensure_subpastas", lambda p: calls["ensure"].append(p))
    monkeypatch.setattr(clientes_service, "write_marker", lambda p, pk: calls["write"].append((p, pk)))

    result = clientes_service._pasta_do_cliente(123, "cnpj", "numero", "razao")

    assert result == "C:/docs\\base_123"
    assert len(calls["ensure"]) == 1
    assert calls["write"][0] == ("C:/docs\\base_123", 123)


def test_pasta_do_cliente_quando_cloud_only_true(monkeypatch):
    """Testa _pasta_do_cliente com CLOUD_ONLY=True (não chama ensure/write)"""
    calls = {"ensure": [], "write": []}

    monkeypatch.setattr(clientes_service, "safe_base_from_fields", lambda *a: "base_456")
    monkeypatch.setattr(clientes_service, "DOCS_DIR", "C:/docs")
    monkeypatch.setattr(clientes_service, "CLOUD_ONLY", True)
    monkeypatch.setattr(clientes_service, "ensure_subpastas", lambda p: calls["ensure"].append(p))
    monkeypatch.setattr(clientes_service, "write_marker", lambda p, pk: calls["write"].append((p, pk)))

    result = clientes_service._pasta_do_cliente(456, "cnpj", "numero", "razao")

    assert result == "C:/docs\\base_456"
    assert len(calls["ensure"]) == 0  # não deve chamar
    assert len(calls["write"]) == 0  # não deve chamar


def test_migrar_pasta_old_path_none():
    """Testa _migrar_pasta_se_preciso com old_path None (retorna early)"""
    # Não deve fazer nada
    clientes_service._migrar_pasta_se_preciso(None, "C:/nova")
    # Se não lançar exceção, passou


def test_migrar_pasta_old_path_nao_existe(monkeypatch):
    """Testa _migrar_pasta_se_preciso quando old_path não é diretório"""
    monkeypatch.setattr(clientes_service.os.path, "isdir", lambda p: False)

    # Não deve fazer nada
    clientes_service._migrar_pasta_se_preciso("C:/nao_existe", "C:/nova")
    # Se não lançar exceção, passou


def test_migrar_pasta_copia_arquivos_e_diretorios(monkeypatch, tmp_path):
    """Testa _migrar_pasta_se_preciso copiando arquivos e diretórios (linhas 178-190)"""

    # Criar estrutura temporária
    old = tmp_path / "old"
    old.mkdir()
    (old / "arquivo.txt").write_text("conteudo")
    subdir = old / "subdir"
    subdir.mkdir()
    (subdir / "nested.txt").write_text("nested")

    nova = tmp_path / "nova"
    nova.mkdir()

    # Executar migração real
    clientes_service._migrar_pasta_se_preciso(str(old), str(nova))

    # Verificar cópias
    assert (nova / "arquivo.txt").exists()
    assert (nova / "arquivo.txt").read_text() == "conteudo"
    assert (nova / "subdir" / "nested.txt").exists()
    assert (nova / "subdir" / "nested.txt").read_text() == "nested"


def test_migrar_pasta_com_erro_loga_exception(monkeypatch):
    """Testa que _migrar_pasta_se_preciso captura exceções e loga"""
    logs = []

    monkeypatch.setattr(clientes_service.os.path, "isdir", lambda p: True)
    monkeypatch.setattr(clientes_service.os, "listdir", lambda p: ["file.txt"])
    monkeypatch.setattr(clientes_service.os.path, "join", lambda *a: "/".join(a))
    monkeypatch.setattr(clientes_service.shutil, "copy2", lambda *a: (_ for _ in ()).throw(OSError("disk full")))
    monkeypatch.setattr(clientes_service.log, "exception", lambda msg, *args: logs.append(msg))

    # Não deve lançar exceção para fora
    clientes_service._migrar_pasta_se_preciso("C:/old", "C:/nova")

    # Deve ter logado
    assert len(logs) > 0


def test_salvar_cliente_auditoria_falha_nao_quebra(monkeypatch):
    """Testa que falha na auditoria não quebra salvar_cliente (linhas 235-236)"""
    monkeypatch.setattr(clientes_service, "insert_cliente", lambda **kw: 789)
    monkeypatch.setattr(clientes_service, "_pasta_do_cliente", lambda *a, **k: "C:/path")
    monkeypatch.setattr(clientes_service, "_migrar_pasta_se_preciso", lambda *a, **k: None)
    monkeypatch.setattr(clientes_service, "find_cliente_by_cnpj_norm", lambda *a, **k: None)

    # Auditoria que lança exceção
    monkeypatch.setattr(clientes_service, "get_current_user", lambda: "user")
    monkeypatch.setattr(
        clientes_service, "log_client_action", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("audit fail"))
    )

    # Deve completar sem lançar exceção
    pk, pasta = clientes_service.salvar_cliente(None, {"Nome": "Test"})
    assert pk == 789
    assert pasta == "C:/path"
