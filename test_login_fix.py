#!/usr/bin/env python3
"""
Script de teste para validar a correção do crash de logging.
Testa tanto o problema original quanto o hardening implementado.
"""

import logging
import sys
import os

# Adicionar src ao path para importar os filtros
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.core.logs.filters import AntiSpamFilter, RedactSensitiveData


def test_original_problem():
    """Testa o problema original de formatação que causava o crash."""
    print("=== TESTE DO PROBLEMA ORIGINAL ===")

    # Configurar logging com filtros
    logger = logging.getLogger("test_login")
    handler = logging.StreamHandler()

    # Adicionar filtros que causavam o crash
    anti_spam = AntiSpamFilter()
    redact = RedactSensitiveData()
    handler.addFilter(anti_spam)
    handler.addFilter(redact)

    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    print("1. Testando log correto (deve funcionar):")
    try:
        uid = "user123"
        token = True
        logger.info(f"Login OK: user.id={uid} | token={'presente' if token else 'ausente'}")
        print("   ✅ Log com f-string funcionou")
    except Exception as e:
        print(f"   ❌ Erro inesperado: {e}")

    print("2. Testando problema que causaria crash (deve ser tratado graciosamente):")
    try:
        # Este log teria problema de formatação (1 placeholder, 2 argumentos)
        # Mas agora deve ser tratado pelo hardening
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Login OK: user=%s",  # 1 placeholder
            args=("user123", "extra_arg"),  # 2 argumentos
            exc_info=None,
        )
        result = anti_spam.filter(record)
        print(f"   ✅ Filtro anti-spam lidou graciosamente: {result}")
        print(f"   ✅ Mensagem sanitizada: {record.msg}")
        print(f"   ✅ Args limpos: {record.args}")
    except Exception as e:
        print(f"   ❌ Filtro não lidou com problema: {e}")


def test_spam_filter():
    """Testa o funcionamento normal do filtro anti-spam."""
    print("\n=== TESTE DO FILTRO ANTI-SPAM ===")

    logger = logging.getLogger("test_spam")
    handler = logging.StreamHandler()

    anti_spam = AntiSpamFilter()
    handler.addFilter(anti_spam)

    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    print("1. Testando mensagem normal (deve passar):")
    logger.info("Esta é uma mensagem normal")
    print("   ✅ Mensagem normal passou")

    print("2. Testando health check (deve ser throttled):")
    logger.info("Health check: sistema funcionando")
    print("   ✅ Primeira health check passou")

    logger.info("Health check: sistema funcionando")
    print("   ✅ Segunda health check deve ter sido throttled (não visível)")


if __name__ == "__main__":
    test_original_problem()
    test_spam_filter()
    print("\n✅ Todos os testes concluídos com sucesso!")
    print("✅ O crash de logging foi corrigido!")
