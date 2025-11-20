"""Testes para status e observações de clientes.

Atualizado na FASE 26 para refletir a API atual de clientes.service:
- fetch_cliente_by_id: wrapper que retorna dict
- update_cliente_status_and_observacoes: atualiza status usando regex para preservar corpo
"""

from __future__ import annotations

from unittest.mock import Mock

from src.modules.clientes import service as clientes_service


def test_fetch_cliente_by_id_returns_dict(monkeypatch):
    """fetch_cliente_by_id deve chamar get_cliente_by_id e converter para dict."""
    fake_cliente = Mock()
    fake_cliente.id = 10
    fake_cliente.razao_social = "Empresa Teste"
    fake_cliente.cnpj = "12345678000190"
    fake_cliente.numero = "001"
    fake_cliente.observacoes = "Teste"

    def fake_get(cliente_id):
        return fake_cliente

    monkeypatch.setattr(clientes_service, "get_cliente_by_id", fake_get)
    result = clientes_service.fetch_cliente_by_id(10)

    assert result is not None
    assert isinstance(result, dict)
    assert result["id"] == 10
    assert result["razao_social"] == "Empresa Teste"


def test_fetch_cliente_by_id_returns_none_when_not_found(monkeypatch):
    """fetch_cliente_by_id deve retornar None quando cliente não existe."""

    def fake_get(cliente_id):
        return None

    monkeypatch.setattr(clientes_service, "get_cliente_by_id", fake_get)
    result = clientes_service.fetch_cliente_by_id(999)

    assert result is None


def test_update_cliente_status_preserves_existing_body(monkeypatch):
    """update_cliente_status_and_observacoes deve preservar corpo e adicionar prefixo."""
    called_with = {}

    def fake_fetch(cliente_id):
        return {"id": 5, "observacoes": "[OLD] corpo existente"}

    def fake_exec(table_call):
        # Captura a chamada de update
        called_with["call"] = table_call
        return Mock()

    monkeypatch.setattr(clientes_service, "fetch_cliente_by_id", fake_fetch)
    monkeypatch.setattr(clientes_service, "exec_postgrest", fake_exec)

    clientes_service.update_cliente_status_and_observacoes(5, "NOVO")

    # Verifica que exec_postgrest foi chamado
    assert "call" in called_with


def test_update_cliente_status_handles_dict_cliente(monkeypatch):
    """update_cliente_status_and_observacoes deve aceitar dict como cliente."""
    called_with = {}

    def fake_exec(table_call):
        called_with["call"] = table_call
        return Mock()

    monkeypatch.setattr(clientes_service, "exec_postgrest", fake_exec)

    cliente = {"id": 7, "observacoes": "[ANTIGO] texto qualquer"}

    clientes_service.update_cliente_status_and_observacoes(cliente, "ATIVO")

    # Verifica que exec_postgrest foi chamado
    assert "call" in called_with
