"""
Testes para infra/net_status.py - probe() com monkeypatch
"""


def test_probe_with_can_resolve_true(monkeypatch):
    """Simula resolução DNS bem-sucedida"""
    import infra.net_status as ns

    # Mock httpx.get para simular resposta online
    class MockResponse:
        status_code = 200

    def fake_get(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr("infra.net_status.httpx.get", fake_get)
    monkeypatch.setattr(ns, "_can_resolve", lambda _: True)

    result = ns.probe(timeout=0.1)
    assert result == ns.Status.ONLINE


def test_probe_with_can_resolve_false(monkeypatch):
    """Simula falha na resolução DNS"""
    import infra.net_status as ns

    monkeypatch.setattr(ns, "_can_resolve", lambda _: False)

    result = ns.probe(timeout=0.1)
    assert result == ns.Status.OFFLINE


def test_probe_with_http_failure(monkeypatch):
    """Simula falha HTTP em todos os fallbacks"""
    import infra.net_status as ns
    import httpx

    monkeypatch.setattr(ns, "_can_resolve", lambda _: True)

    def fake_get(*args, **kwargs):
        raise httpx.ConnectError("Network error")

    # Mock httpx.Client para sempre falhar
    class MockClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def get(self, *args, **kwargs):
            raise httpx.ConnectError("Network error")

    monkeypatch.setattr("infra.net_status.httpx.Client", lambda **kw: MockClient())

    result = ns.probe(timeout=0.1)
    assert result == ns.Status.OFFLINE
