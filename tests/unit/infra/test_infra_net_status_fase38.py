# tests/test_infra_net_status_fase38.py
"""
Testes para o módulo infra/net_status.py (COV-INFRA-004).
Objetivo: Aumentar cobertura para 100%.

Funções testadas:
- _can_resolve(): Verificação de DNS
- _pick_base(): Seleção de URL base para probe
- _ok(): Validação de código HTTP
- probe(): Função principal de sondagem de rede
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch


# ========================================
# Testes de _can_resolve
# ========================================


def test_can_resolve_success():
    """Testa _can_resolve quando DNS funciona."""
    from infra.net_status import _can_resolve

    with patch("socket.gethostbyname", return_value="8.8.8.8"):
        result = _can_resolve("google.com")

    assert result is True


def test_can_resolve_failure():
    """Testa _can_resolve quando DNS falha."""
    from infra.net_status import _can_resolve

    with patch("socket.gethostbyname", side_effect=Exception("DNS resolution failed")):
        result = _can_resolve("invalid.domain.xyz")

    assert result is False


# ========================================
# Testes de _ok
# ========================================


def test_ok_code_204():
    """Testa _ok com código 204."""
    from infra.net_status import _ok

    assert _ok(204) is True


def test_ok_code_200():
    """Testa _ok com código 200."""
    from infra.net_status import _ok

    assert _ok(200) is True


def test_ok_code_299():
    """Testa _ok com código 299 (limite superior de 2xx)."""
    from infra.net_status import _ok

    assert _ok(299) is True


def test_ok_code_301():
    """Testa _ok com código 301 (redirect, ainda considerado OK)."""
    from infra.net_status import _ok

    assert _ok(301) is True


def test_ok_code_399():
    """Testa _ok com código 399 (limite superior de 3xx)."""
    from infra.net_status import _ok

    assert _ok(399) is True


def test_ok_code_400():
    """Testa _ok com código 400 (erro cliente)."""
    from infra.net_status import _ok

    assert _ok(400) is False


def test_ok_code_404():
    """Testa _ok com código 404."""
    from infra.net_status import _ok

    assert _ok(404) is False


def test_ok_code_500():
    """Testa _ok com código 500 (erro servidor)."""
    from infra.net_status import _ok

    assert _ok(500) is False


def test_ok_code_199():
    """Testa _ok com código 199 (abaixo de 200)."""
    from infra.net_status import _ok

    assert _ok(199) is False


# ========================================
# Testes de _pick_base
# ========================================


def test_pick_base_with_url_hint_https():
    """Testa _pick_base com url_hint já com https."""
    from infra.net_status import _pick_base

    result = _pick_base("https://example.com/path/")
    assert result == "https://example.com/path"


def test_pick_base_with_url_hint_no_protocol():
    """Testa _pick_base com url_hint sem protocolo."""
    from infra.net_status import _pick_base

    result = _pick_base("example.com")
    assert result == "https://example.com"


def test_pick_base_with_url_hint_trailing_slash():
    """Testa _pick_base remove trailing slash."""
    from infra.net_status import _pick_base

    result = _pick_base("https://api.example.com/")
    assert result == "https://api.example.com"


def test_pick_base_with_url_hint_empty_string():
    """Testa _pick_base com url_hint vazio cai para SUPABASE_URL."""
    from infra.net_status import _pick_base

    with patch.dict(os.environ, {"SUPABASE_URL": "my-project.supabase.co"}):
        result = _pick_base("")

    assert result == "https://my-project.supabase.co"


def test_pick_base_with_url_hint_whitespace():
    """Testa _pick_base com url_hint apenas espaços (strip vira vazio, retorna vazio)."""
    from infra.net_status import _pick_base

    # url_hint="   " é truthy, então entra no if url_hint:
    # u = "   ".strip() = ""
    # if u: é False, então não adiciona https://
    # return u.rstrip("/") = "" (vazio)
    result = _pick_base("   ")

    assert result == ""


def test_pick_base_from_env_supabase_url():
    """Testa _pick_base usando SUPABASE_URL."""
    from infra.net_status import _pick_base

    with patch.dict(os.environ, {"SUPABASE_URL": "https://my-env.supabase.co"}):
        result = _pick_base(None)

    assert result == "https://my-env.supabase.co"


def test_pick_base_from_env_no_protocol():
    """Testa _pick_base quando SUPABASE_URL não tem protocolo."""
    from infra.net_status import _pick_base

    with patch.dict(os.environ, {"SUPABASE_URL": "no-protocol.supabase.co"}):
        result = _pick_base(None)

    assert result == "https://no-protocol.supabase.co"


def test_pick_base_from_supabase_client_supabase_url():
    """Testa _pick_base usando supabase_url do supabase_client."""
    from infra.net_status import _pick_base

    mock_supabase = MagicMock()
    mock_supabase.supabase_url = "https://client-url.supabase.co/"

    with patch.dict(os.environ, {}, clear=True):
        with patch.dict("sys.modules", {"infra.supabase_client": MagicMock(supabase=mock_supabase)}):
            result = _pick_base(None)

    assert result == "https://client-url.supabase.co"


def test_pick_base_from_supabase_client_url():
    """Testa _pick_base usando atributo url do supabase_client."""
    from infra.net_status import _pick_base

    mock_supabase = MagicMock()
    mock_supabase.url = "https://client-url-attr.supabase.co"
    del mock_supabase.supabase_url
    del mock_supabase._supabase_url

    with patch.dict(os.environ, {}, clear=True):
        with patch.dict("sys.modules", {"infra.supabase_client": MagicMock(supabase=mock_supabase)}):
            result = _pick_base(None)

    assert result == "https://client-url-attr.supabase.co"


def test_pick_base_from_supabase_client_private_supabase_url():
    """Testa _pick_base usando _supabase_url do supabase_client."""
    from infra.net_status import _pick_base

    mock_supabase = MagicMock()
    mock_supabase._supabase_url = "private-url.supabase.co"
    del mock_supabase.supabase_url
    del mock_supabase.url

    with patch.dict(os.environ, {}, clear=True):
        with patch.dict("sys.modules", {"infra.supabase_client": MagicMock(supabase=mock_supabase)}):
            result = _pick_base(None)

    assert result == "https://private-url.supabase.co"


def test_pick_base_fallback_google():
    """Testa _pick_base fallback para Google quando não há outras opções."""
    from infra.net_status import _pick_base

    with patch.dict(os.environ, {}, clear=True):
        # Mock import de supabase_client para causar falha
        import sys
        from types import ModuleType

        fake_module = ModuleType("fake_supabase_client")
        with patch.dict(sys.modules, {"infra.supabase_client": fake_module}):
            # Remove atributo supabase do fake module para cair no except
            result = _pick_base(None)

    assert result == "https://www.google.com/generate_204"


def test_pick_base_supabase_client_exception():
    """Testa _pick_base quando import de supabase_client levanta exceção."""
    from infra.net_status import _pick_base

    with patch.dict(os.environ, {}, clear=True):
        with patch.dict("sys.modules", {"infra.supabase_client": None}):
            result = _pick_base(None)

    assert result == "https://www.google.com/generate_204"


def test_pick_base_supabase_client_no_valid_attr():
    """Testa _pick_base quando supabase_client não tem atributos válidos."""
    from infra.net_status import _pick_base

    mock_supabase = MagicMock()
    # Atributos existem mas não são strings válidas
    mock_supabase._supabase_url = None
    mock_supabase.supabase_url = ""
    mock_supabase.url = 12345  # int ao invés de str

    with patch.dict(os.environ, {}, clear=True):
        with patch.dict("sys.modules", {"infra.supabase_client": MagicMock(supabase=mock_supabase)}):
            result = _pick_base(None)

    assert result == "https://www.google.com/generate_204"


# ========================================
# Testes de probe
# ========================================


def test_probe_online_with_google_fallback():
    """Testa probe retornando ONLINE via fallback Google."""
    from infra.net_status import Status, probe

    mock_response = MagicMock()
    mock_response.status_code = 204

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_response

    with patch.dict(os.environ, {}, clear=True):
        with patch("socket.gethostbyname", return_value="142.250.185.46"):
            with patch("httpx.Client", return_value=mock_client):
                result = probe()

    assert result == Status.ONLINE


def test_probe_online_with_supabase_health():
    """Testa probe retornando ONLINE via Supabase health endpoint."""
    from infra.net_status import Status, probe

    mock_response = MagicMock()
    mock_response.status_code = 200

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_response

    with patch.dict(os.environ, {"SUPABASE_ANON_KEY": "test-anon-key"}):
        with patch("socket.gethostbyname", return_value="1.2.3.4"):
            with patch("httpx.Client", return_value=mock_client):
                result = probe("https://my-project.supabase.co")

    assert result == Status.ONLINE


def test_probe_offline_dns_failure():
    """Testa probe retornando OFFLINE quando DNS falha."""
    from infra.net_status import Status, probe

    with patch("socket.gethostbyname", side_effect=Exception("DNS failed")):
        result = probe()

    assert result == Status.OFFLINE


def test_probe_offline_all_targets_fail():
    """Testa probe retornando OFFLINE quando todas as tentativas HTTP falham."""
    from infra.net_status import Status, probe

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.side_effect = Exception("Connection refused")

    with patch("socket.gethostbyname", return_value="8.8.8.8"):
        with patch("httpx.Client", return_value=mock_client):
            result = probe()

    assert result == Status.OFFLINE


def test_probe_offline_http_400_codes():
    """Testa probe retornando OFFLINE quando recebe códigos 4xx."""
    from infra.net_status import Status, probe

    mock_response = MagicMock()
    mock_response.status_code = 404

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_response

    with patch("socket.gethostbyname", return_value="1.2.3.4"):
        with patch("httpx.Client", return_value=mock_client):
            result = probe()

    assert result == Status.OFFLINE


def test_probe_offline_http_500_codes():
    """Testa probe retornando OFFLINE quando recebe códigos 5xx."""
    from infra.net_status import Status, probe

    mock_response = MagicMock()
    mock_response.status_code = 500

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_response

    with patch("socket.gethostbyname", return_value="1.2.3.4"):
        with patch("httpx.Client", return_value=mock_client):
            result = probe()

    assert result == Status.OFFLINE


def test_probe_online_with_custom_url():
    """Testa probe com URL customizada."""
    from infra.net_status import Status, probe

    mock_response = MagicMock()
    mock_response.status_code = 200

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_response

    with patch("socket.gethostbyname", return_value="5.6.7.8"):
        with patch("httpx.Client", return_value=mock_client):
            result = probe(url="https://custom-api.example.com")

    assert result == Status.ONLINE


def test_probe_with_custom_timeout():
    """Testa probe com timeout customizado."""
    from infra.net_status import Status, probe

    mock_response = MagicMock()
    mock_response.status_code = 204

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_response

    with patch("socket.gethostbyname", return_value="8.8.8.8"):
        with patch("httpx.Client", return_value=mock_client) as mock_client_class:
            result = probe(timeout=5.0)

    # Verificar que Client foi criado com timeout correto
    mock_client_class.assert_called_once()
    call_kwargs = mock_client_class.call_args[1]
    assert call_kwargs["timeout"] == 5.0
    assert result == Status.ONLINE


def test_probe_supabase_without_anon_key():
    """Testa probe com Supabase mas sem ANON_KEY."""
    from infra.net_status import Status, probe

    mock_response_health = MagicMock()
    mock_response_health.status_code = 200

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_response_health

    with patch.dict(os.environ, {}, clear=True):  # Sem SUPABASE_ANON_KEY
        with patch("socket.gethostbyname", return_value="1.2.3.4"):
            with patch("httpx.Client", return_value=mock_client):
                result = probe("https://project.supabase.co")

    assert result == Status.ONLINE
    # Verificar que foi chamado sem apikey
    calls = mock_client.get.call_args_list
    assert len(calls) >= 1
    # Primeira chamada deve ser health sem key
    first_call = calls[0]
    assert "auth/v1/health" in first_call[0][0]
    assert "apikey" not in first_call[1]["headers"]


def test_probe_supabase_with_anon_key():
    """Testa probe com Supabase e ANON_KEY presente."""
    from infra.net_status import Status, probe

    mock_response = MagicMock()
    mock_response.status_code = 200

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_response

    with patch.dict(os.environ, {"SUPABASE_ANON_KEY": "my-anon-key-12345"}):
        with patch("socket.gethostbyname", return_value="1.2.3.4"):
            with patch("httpx.Client", return_value=mock_client):
                result = probe("https://project.supabase.co")

    assert result == Status.ONLINE
    # Verificar que foi chamado com apikey
    calls = mock_client.get.call_args_list
    assert len(calls) >= 1
    first_call = calls[0]
    assert first_call[1]["headers"]["apikey"] == "my-anon-key-12345"


def test_probe_supabase_first_target_fails_fallback_works():
    """Testa probe quando primeiro target Supabase falha mas fallback Google funciona."""
    from infra.net_status import Status, probe

    mock_response_google = MagicMock()
    mock_response_google.status_code = 204

    call_count = 0

    def side_effect_get(url, headers):
        nonlocal call_count
        call_count += 1
        if "supabase.co" in url:
            raise Exception("Supabase unreachable")
        # Google fallback
        return mock_response_google

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.side_effect = side_effect_get

    with patch.dict(os.environ, {"SUPABASE_ANON_KEY": "test-key"}):
        with patch("socket.gethostbyname", return_value="1.2.3.4"):
            with patch("httpx.Client", return_value=mock_client):
                result = probe("https://project.supabase.co")

    assert result == Status.ONLINE
    assert call_count >= 2  # Tentou Supabase + Google


def test_probe_dns_exception_handling():
    """Testa probe quando parsing de host para DNS levanta exceção."""
    from infra.net_status import Status, probe

    mock_response = MagicMock()
    mock_response.status_code = 204

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_response

    # URL malformada causa exceção no split, função pega a exceção e continua
    # Mas se DNS também falha, retorna OFFLINE antes de tentar HTTP
    with patch("socket.gethostbyname", side_effect=Exception("DNS error")):
        with patch("httpx.Client", return_value=mock_client):
            result = probe("malformed://url")

    # DNS falhou, então retorna OFFLINE (linha 64: return Status.OFFLINE)
    assert result == Status.OFFLINE


def test_probe_host_parsing_exception_continues():
    """Testa probe quando parsing de host falha mas HTTP ainda funciona."""
    from infra.net_status import Status, probe

    mock_response = MagicMock()
    mock_response.status_code = 204

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_response

    # Forçar exceção no split causando IndexError
    def mock_pick_base(url):
        return "no-double-slash"  # Causa IndexError em split("//", 1)[1]

    with patch("infra.net_status._pick_base", side_effect=mock_pick_base):
        with patch("httpx.Client", return_value=mock_client):
            result = probe("test")

    # Exceção no DNS parsing é capturada (linhas 65-66), continua e HTTP funciona
    assert result == Status.ONLINE


def test_probe_httpx_client_creation_fails():
    """Testa probe quando criação do httpx.Client falha."""
    from infra.net_status import Status, probe

    with patch("socket.gethostbyname", return_value="8.8.8.8"):
        with patch("httpx.Client", side_effect=Exception("SSL error")):
            result = probe()

    assert result == Status.OFFLINE


def test_probe_httpx_client_context_manager_fails():
    """Testa probe quando context manager do Client falha."""
    from infra.net_status import Status, probe

    mock_client = MagicMock()
    mock_client.__enter__.side_effect = Exception("Connection pool error")

    with patch("socket.gethostbyname", return_value="8.8.8.8"):
        with patch("httpx.Client", return_value=mock_client):
            result = probe()

    assert result == Status.OFFLINE


def test_probe_online_with_redirect_code():
    """Testa probe considerando código 3xx como OK."""
    from infra.net_status import Status, probe

    mock_response = MagicMock()
    mock_response.status_code = 301

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_response

    with patch("socket.gethostbyname", return_value="8.8.8.8"):
        with patch("httpx.Client", return_value=mock_client):
            result = probe()

    assert result == Status.ONLINE


def test_probe_supabase_rest_endpoint():
    """Testa probe usando endpoint /rest/v1 do Supabase."""
    from infra.net_status import Status, probe

    call_count = 0
    mock_response_rest = MagicMock()
    mock_response_rest.status_code = 200

    def side_effect_get(url, headers):
        nonlocal call_count
        call_count += 1
        if "auth/v1/health" in url:
            # Primeira chamada falha
            raise Exception("Health endpoint down")
        elif "rest/v1" in url:
            # Segunda chamada funciona
            return mock_response_rest
        else:
            raise Exception("Unknown endpoint")

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.side_effect = side_effect_get

    with patch.dict(os.environ, {"SUPABASE_ANON_KEY": "test-key"}):
        with patch("socket.gethostbyname", return_value="1.2.3.4"):
            with patch("httpx.Client", return_value=mock_client):
                result = probe("https://project.supabase.co")

    assert result == Status.ONLINE
    assert call_count >= 2  # Tentou health + rest


# ========================================
# Testes de Status Enum
# ========================================


def test_status_enum_values():
    """Testa valores do enum Status."""
    from infra.net_status import Status

    assert Status.ONLINE.value == 1
    assert Status.OFFLINE.value == 2
    assert Status.LOCAL.value == 3


def test_status_enum_members():
    """Testa membros do enum Status."""
    from infra.net_status import Status

    assert len(Status) == 3
    assert Status.ONLINE in Status
    assert Status.OFFLINE in Status
    assert Status.LOCAL in Status
