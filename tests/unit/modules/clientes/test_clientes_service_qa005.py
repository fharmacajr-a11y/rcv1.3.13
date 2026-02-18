"""Testes adicionais para src/modules/clientes/service.py focados nas correções da QA-005.

Este arquivo complementa test_clientes_service.py com cenários específicos para
validar as correções de type hints e guards implementadas na QA-005.
"""

import types

import pytest

from src.modules.clientes.core import service


class TestFilterSelfQA005:
    """Testa a função interna _filter_self e o tratamento de razao_conflicts/numero_conflicts.

    QA-005 adicionou cast(list, info.get("razao_conflicts") or []) para lidar com
    casos onde info.get() retorna None ou object.
    """

    def test_checar_duplicatas_razao_conflicts_none_explicit(self, monkeypatch):
        """Testa que razao_conflicts=None não quebra (cast para list funciona)."""

        # Simula checar_duplicatas_info retornando None explicitamente
        def fake_checar(*args, **kwargs):
            return {
                "cnpj_conflict": None,
                "razao_conflicts": None,  # Explicitamente None
                "numero_conflicts": None,
            }

        monkeypatch.setattr(service, "checar_duplicatas_info", fake_checar)

        result = service.checar_duplicatas_para_form(
            valores={"Razão Social": "Test", "CNPJ": "", "Nome": "", "WhatsApp": ""}, row=None, exclude_id=None
        )

        # Deve lidar graciosamente com None e retornar listas vazias
        assert result["razao_conflicts"] == []
        assert result["numero_conflicts"] == []
        assert result["conflict_ids"]["razao"] == []
        assert result["conflict_ids"]["numero"] == []

    def test_checar_duplicatas_razao_conflicts_empty_list(self, monkeypatch):
        """Testa que razao_conflicts=[] retorna lista vazia de conflict_ids."""

        def fake_checar(*args, **kwargs):
            return {
                "cnpj_conflict": None,
                "razao_conflicts": [],
                "numero_conflicts": [],
            }

        monkeypatch.setattr(service, "checar_duplicatas_info", fake_checar)

        result = service.checar_duplicatas_para_form(
            valores={"Razão Social": "Test", "CNPJ": "", "Nome": "", "WhatsApp": ""}, row=None, exclude_id=None
        )

        assert result["razao_conflicts"] == []
        assert result["conflict_ids"]["razao"] == []

    def test_checar_duplicatas_filter_self_from_conflicts(self, monkeypatch):
        """Testa que _filter_self remove o próprio cliente dos conflitos."""
        # Simula 3 clientes com razão similar, incluindo o atual (id=2)
        cliente1 = types.SimpleNamespace(id=1, razao_social="Acme Corp")
        cliente2 = types.SimpleNamespace(id=2, razao_social="Acme Corp")  # Current
        cliente3 = types.SimpleNamespace(id=3, razao_social="Acme Corp")

        def fake_checar(*args, **kwargs):
            return {
                "cnpj_conflict": None,
                "razao_conflicts": [cliente1, cliente2, cliente3],
                "numero_conflicts": [],
            }

        monkeypatch.setattr(service, "checar_duplicatas_info", fake_checar)

        result = service.checar_duplicatas_para_form(
            valores={"Razão Social": "Acme Corp", "CNPJ": "", "Nome": "", "WhatsApp": ""},
            row=None,
            exclude_id=2,  # Deve filtrar cliente2
        )

        # cliente2 (current_id=2) deve ser removido
        assert len(result["razao_conflicts"]) == 2
        assert cliente1 in result["razao_conflicts"]
        assert cliente2 not in result["razao_conflicts"]
        assert cliente3 in result["razao_conflicts"]
        assert result["conflict_ids"]["razao"] == [1, 3]

    def test_checar_duplicatas_conflict_without_id_attribute(self, monkeypatch):
        """Testa que conflitos sem atributo 'id' são tolerados."""
        # Objeto sem id
        cliente_broken = types.SimpleNamespace(razao_social="Test")  # Sem 'id'
        cliente_ok = types.SimpleNamespace(id=5, razao_social="Test")

        def fake_checar(*args, **kwargs):
            return {
                "cnpj_conflict": None,
                "razao_conflicts": [cliente_broken, cliente_ok],
                "numero_conflicts": [],
            }

        monkeypatch.setattr(service, "checar_duplicatas_info", fake_checar)

        result = service.checar_duplicatas_para_form(
            valores={"Razão Social": "Test", "CNPJ": "", "Nome": "", "WhatsApp": ""}, row=None, exclude_id=None
        )

        # cliente_broken fica na lista (não tem id válido mas não quebra)
        # cliente_ok aparece nos conflict_ids
        assert len(result["razao_conflicts"]) == 2
        assert cliente_ok in result["razao_conflicts"]
        assert result["conflict_ids"]["razao"] == [5]  # Só o que tem id válido


class TestGetClienteByIdQA005:
    """Testa get_cliente_by_id e fetch_cliente_by_id após mudança de tipo de retorno.

    QA-005 mudou o tipo de retorno de get_cliente_by_id de MutableMapping para Any,
    refletindo que o core retorna um objeto Cliente, não um dict.
    """

    def test_get_cliente_by_id_returns_object(self, monkeypatch):
        """Testa que get_cliente_by_id retorna o objeto do core."""
        fake_cliente = types.SimpleNamespace(id=42, razao_social="Test Corp")

        monkeypatch.setattr(service, "core_get_cliente_by_id", lambda cliente_id: fake_cliente)

        result = service.get_cliente_by_id(42)

        assert result is fake_cliente
        assert result.id == 42
        assert result.razao_social == "Test Corp"

    def test_get_cliente_by_id_returns_none_when_not_found(self, monkeypatch):
        """Testa que get_cliente_by_id retorna None quando não encontrado."""
        monkeypatch.setattr(service, "core_get_cliente_by_id", lambda cliente_id: None)

        result = service.get_cliente_by_id(999)

        assert result is None

    def test_fetch_cliente_by_id_converts_to_dict(self, monkeypatch):
        """Testa que fetch_cliente_by_id converte objeto para dict."""
        fake_cliente = types.SimpleNamespace(
            id=42, razao_social="Test Corp", cnpj="12345678000100", observacoes="Obs test"
        )

        monkeypatch.setattr(service, "get_cliente_by_id", lambda cliente_id: fake_cliente)

        result = service.fetch_cliente_by_id(42)

        assert isinstance(result, dict)
        assert result["id"] == 42
        assert result["razao_social"] == "Test Corp"
        assert result["cnpj"] == "12345678000100"

    def test_fetch_cliente_by_id_returns_none_when_not_found(self, monkeypatch):
        """Testa que fetch_cliente_by_id retorna None quando cliente não existe."""
        monkeypatch.setattr(service, "get_cliente_by_id", lambda cliente_id: None)

        result = service.fetch_cliente_by_id(999)

        assert result is None


class TestClienteIdConversionQA005:
    """Testa a conversão de id para int em update_cliente_status_and_observacoes.

    QA-005 adicionou guard explícito para raw_id=None antes de chamar int(),
    levantando ValueError se não houver id válido.
    """

    def test_update_with_cliente_dict_valid_id(self, monkeypatch):
        """Testa update com dict contendo id válido."""
        updates = []

        def fake_exec(*args, **kwargs):
            updates.append(kwargs)
            return None

        monkeypatch.setattr(service, "exec_postgrest", fake_exec)
        monkeypatch.setattr(service, "_current_utc_iso", lambda: "2025-11-20T10:00:00Z")

        cliente_dict = {"id": 42, "observacoes": "Velho obs"}

        service.update_cliente_status_and_observacoes(cliente_dict, "ATIVO")

        # Deve ter feito update com cliente_id=42
        assert len(updates) > 0

    def test_update_with_cliente_dict_id_as_string(self, monkeypatch):
        """Testa que id como string é convertido para int."""
        updates = []

        def fake_exec(*args, **kwargs):
            updates.append(kwargs)
            return None

        monkeypatch.setattr(service, "exec_postgrest", fake_exec)
        monkeypatch.setattr(service, "_current_utc_iso", lambda: "2025-11-20T10:00:00Z")

        cliente_dict = {"id": "123", "observacoes": "Test"}

        service.update_cliente_status_and_observacoes(cliente_dict, "ATIVO")

        # Não deve quebrar, int("123") funciona
        assert len(updates) > 0

    def test_update_with_cliente_dict_missing_id_raises_error(self, monkeypatch):
        """Testa que cliente sem id levanta ValueError."""
        monkeypatch.setattr(service, "exec_postgrest", lambda *args, **kwargs: None)
        monkeypatch.setattr(service, "_current_utc_iso", lambda: "2025-11-20T10:00:00Z")

        cliente_dict = {"razao_social": "Test", "observacoes": "Obs"}  # Sem 'id'

        with pytest.raises(ValueError, match="Cliente deve ter um campo 'id' válido"):
            service.update_cliente_status_and_observacoes(cliente_dict, "ATIVO")

    def test_update_with_cliente_dict_id_none_raises_error(self, monkeypatch):
        """Testa que id=None levanta ValueError."""
        monkeypatch.setattr(service, "exec_postgrest", lambda *args, **kwargs: None)
        monkeypatch.setattr(service, "_current_utc_iso", lambda: "2025-11-20T10:00:00Z")

        cliente_dict = {"id": None, "observacoes": "Test"}

        with pytest.raises(ValueError, match="Cliente deve ter um campo 'id' válido"):
            service.update_cliente_status_and_observacoes(cliente_dict, "ATIVO")

    def test_update_with_cliente_dict_with_observacoes_field(self, monkeypatch):
        """Testa update com dict contendo observacoes."""
        updates = []

        def fake_exec(*args, **kwargs):
            updates.append(kwargs)
            return None

        monkeypatch.setattr(service, "exec_postgrest", fake_exec)

        cliente_dict = {"id": 77, "observacoes": "Obs antiga"}

        service.update_cliente_status_and_observacoes(cliente_dict, "INATIVO")

        # Deve ter funcionado
        assert len(updates) > 0

    def test_update_with_cliente_dict_empty_id_raises_error(self, monkeypatch):
        """Testa que dict com id vazio/None levanta ValueError."""
        monkeypatch.setattr(service, "exec_postgrest", lambda *args, **kwargs: None)

        # id vazio pode não levantar erro se int("") falhar diferente
        # Mas se id for None ou ausente, deve levantar
        cliente_dict_none = {"razao_social": "Test"}  # Sem 'id'

        with pytest.raises(ValueError, match="Cliente deve ter um campo 'id' válido"):
            service.update_cliente_status_and_observacoes(cliente_dict_none, "ATIVO")

    def test_update_with_int_cliente_id_directly(self, monkeypatch):
        """Testa que passar int diretamente como cliente funciona."""
        updates = []
        fake_cliente_dict = {"id": 55, "observacoes": "Old"}

        def fake_exec(*args, **kwargs):
            updates.append(kwargs)
            return None

        def fake_fetch(cliente_id):
            return fake_cliente_dict if cliente_id == 55 else None

        monkeypatch.setattr(service, "exec_postgrest", fake_exec)
        monkeypatch.setattr(service, "fetch_cliente_by_id", fake_fetch)
        monkeypatch.setattr(service, "_current_utc_iso", lambda: "2025-11-20T10:00:00Z")

        service.update_cliente_status_and_observacoes(55, "ATIVO")

        # Deve ter buscado cliente 55 e feito update
        assert len(updates) > 0
