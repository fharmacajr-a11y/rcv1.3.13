import types

import pytest

from src.modules.passwords import service


def _patch_supabase(monkeypatch, user_obj):
    import infra.supabase_client as supabase_client

    fake_supabase = types.SimpleNamespace(auth=types.SimpleNamespace(get_user=lambda: user_obj))
    monkeypatch.setattr(supabase_client, "supabase", fake_supabase)


def test_group_passwords_by_client_sorts_and_aggregates():
    data = [
        {
            "client_id": "2",
            "razao_social": "Beta Ltda",
            "cnpj": "44",
            "nome": "Maria",
            "whatsapp": "999",
            "service": "CRF",
            "username": "beta",
        },
        {
            "client_id": "1",
            "razao_social": "Alpha S.A.",
            "cnpj": "11",
            "nome": "João",
            "whatsapp": "888",
            "service": "SIFAP",
            "username": "alpha",
        },
        {
            "client_id": "1",
            "razao_social": "Alpha S.A.",
            "cnpj": "11",
            "nome": "João",
            "whatsapp": "888",
            "service": "Banco",
            "username": "alpha",
        },
        {
            "client_id": "",
            "razao_social": "Ignorado",
            "service": "Outro",
        },
    ]

    summaries = service.group_passwords_by_client(data)

    assert [summary.client_id for summary in summaries] == ["1", "2"]
    alpha = summaries[0]
    assert alpha.razao_social == "Alpha S.A."
    assert alpha.passwords_count == 2
    assert alpha.services == ["Banco", "SIFAP"]
    assert alpha.display_name.startswith("ID")


def test_filter_passwords_applies_search_and_service_filter():
    passwords = [
        {"client_name": "Alpha", "service": "GOV.BR", "username": "alpha@example.com"},
        {"client_name": "Beta", "service": "SIFAP", "username": "beta@example.com"},
        {"client_name": "Gamma", "service": "Banco", "username": "banker"},
    ]

    result = service.filter_passwords(passwords, "alpha", None)
    assert len(result) == 1
    assert result[0]["client_name"] == "Alpha"

    result = service.filter_passwords(passwords, "example", "SIFAP")
    assert len(result) == 1
    assert result[0]["service"] == "SIFAP"

    result = service.filter_passwords(passwords, "", "Banco")
    assert len(result) == 1
    assert result[0]["username"] == "banker"


def test_resolve_user_context_uses_cached_org_id(monkeypatch):
    fake_user = types.SimpleNamespace(user=types.SimpleNamespace(id="user-123"))
    _patch_supabase(monkeypatch, fake_user)

    class FakeMainWindow:
        def __init__(self):
            self.received = None

        def _get_org_id_cached(self, user_id):
            self.received = user_id
            return "ORG-999"

    ctx = service.resolve_user_context(FakeMainWindow())

    assert ctx.user_id == "user-123"
    assert ctx.org_id == "ORG-999"


def test_resolve_user_context_falls_back_to_client_service(monkeypatch):
    fake_user = types.SimpleNamespace(user=types.SimpleNamespace(id="user-321"))
    _patch_supabase(monkeypatch, fake_user)

    class NoOrgWindow:
        def _get_org_id_cached(self, user_id):
            return None

    import src.modules.clientes.service as clientes_service

    monkeypatch.setattr(clientes_service, "_resolve_current_org_id", lambda: "ORG-FALLBACK")

    ctx = service.resolve_user_context(NoOrgWindow())

    assert ctx.org_id == "ORG-FALLBACK"
    assert ctx.user_id == "user-321"


def test_resolve_user_context_without_user_raises(monkeypatch):
    fake_user = types.SimpleNamespace(user=None)
    _patch_supabase(monkeypatch, fake_user)

    class FakeWindow:
        def _get_org_id_cached(self, user_id):
            return "ORG-X"

    with pytest.raises(RuntimeError) as exc:
        service.resolve_user_context(FakeWindow())

    assert "Usuário" in str(exc.value)
