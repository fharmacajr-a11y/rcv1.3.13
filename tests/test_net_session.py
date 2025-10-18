#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Testes para infra/net_session.py - Sessão requests com retry e timeout.
"""
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_make_session_defaults():
    """Testa que make_session() cria sessão com adapters montados."""
    from infra.net_session import make_session

    session = make_session()

    # Verifica que adapters estão montados para https:// e http://
    assert "https://" in session.adapters, "Adapter https:// não montado"
    assert "http://" in session.adapters, "Adapter http:// não montado"

    print("✓ Adapters https:// e http:// montados")


def test_retry_configuration():
    """Testa configuração de retry no adapter."""
    from infra.net_session import make_session

    session = make_session()

    # Obtém adapter https
    adapter = session.adapters["https://"]

    # Verifica que tem max_retries configurado
    assert hasattr(adapter, "max_retries"), "Adapter não tem max_retries"

    retry = adapter.max_retries

    # Verifica configurações de retry
    assert retry.total == 3, f"retry.total={retry.total}, esperado 3"
    assert retry.connect == 3, f"retry.connect={retry.connect}, esperado 3"
    assert retry.read == 3, f"retry.read={retry.read}, esperado 3"
    assert (
        retry.backoff_factor == 0.5
    ), f"retry.backoff_factor={retry.backoff_factor}, esperado 0.5"

    # Verifica status_forcelist
    expected_status = {413, 429, 500, 502, 503, 504}
    assert (
        set(retry.status_forcelist) == expected_status
    ), f"status_forcelist={retry.status_forcelist}, esperado {expected_status}"

    # Verifica que respect_retry_after_header está ativo
    assert (
        retry.respect_retry_after_header is True
    ), "respect_retry_after_header deve ser True"

    print("✓ Retry configurado: total=3, backoff=0.5s, status_forcelist correto")
    print(f"✓ allowed_methods: {retry.allowed_methods}")


def test_timeout_adapter():
    """Testa que TimeoutHTTPAdapter está configurado."""
    from infra.net_session import make_session, DEFAULT_TIMEOUT

    session = make_session()
    adapter = session.adapters["https://"]

    # Verifica que é TimeoutHTTPAdapter
    assert hasattr(
        adapter, "_timeout"
    ), "Adapter não tem _timeout (não é TimeoutHTTPAdapter)"

    # Verifica timeout padrão
    assert (
        adapter._timeout == DEFAULT_TIMEOUT
    ), f"Timeout={adapter._timeout}, esperado {DEFAULT_TIMEOUT}"

    print(f"✓ TimeoutHTTPAdapter configurado com timeout={DEFAULT_TIMEOUT}")


def test_default_timeout_value():
    """Testa que DEFAULT_TIMEOUT tem valores razoáveis."""
    from infra.net_session import DEFAULT_TIMEOUT

    assert isinstance(DEFAULT_TIMEOUT, tuple), "DEFAULT_TIMEOUT deve ser tuple"
    assert (
        len(DEFAULT_TIMEOUT) == 2
    ), "DEFAULT_TIMEOUT deve ter 2 elementos (connect, read)"

    connect, read = DEFAULT_TIMEOUT
    assert connect > 0, f"connect timeout={connect} deve ser > 0"
    assert read > 0, f"read timeout={read} deve ser > 0"
    assert connect <= read, f"connect={connect} deve ser <= read={read}"

    print(f"✓ DEFAULT_TIMEOUT={DEFAULT_TIMEOUT} (connect, read) válido")


def main():
    """Executa todos os testes."""
    print("=" * 60)
    print("Testes - infra/net_session.py")
    print("=" * 60)
    print()

    tests = [
        ("Criar sessão com adapters", test_make_session_defaults),
        ("Configuração de retry", test_retry_configuration),
        ("TimeoutHTTPAdapter", test_timeout_adapter),
        ("DEFAULT_TIMEOUT válido", test_default_timeout_value),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        print(f"Teste: {name}")
        print("-" * 60)
        try:
            test_func()
            passed += 1
            print()
        except AssertionError as e:
            print(f"✗ FALHOU: {e}")
            print()
            failed += 1
        except Exception as e:
            print(f"✗ ERRO: {e}")
            print()
            failed += 1

    print("=" * 60)
    print(f"Resultados: {passed} passou, {failed} falhou")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)

    print()
    print("✓ TODOS OS TESTES PASSARAM!")


if __name__ == "__main__":
    main()
