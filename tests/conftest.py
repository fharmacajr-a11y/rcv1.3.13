"""
Configuração do pytest para testes.

Este arquivo garante que o pytest reconheça a pasta tests/ como um pacote
e configure corretamente os caminhos para importar módulos do projeto.
"""

import pytest


# ============================================================================
# FIXTURES DE SEGURANÇA - Valores FAKE para testes
# ============================================================================
# ⚠️ IMPORTANTE: Estes valores são FICTÍCIOS e não devem ser usados em produção
# Propósito: Evitar hardcoding de URLs/keys reais nos testes
# ============================================================================


@pytest.fixture
def fake_supabase_url() -> str:
    """
    URL fake do Supabase para testes.

    ⚠️ ATENÇÃO: Este é um valor FICTÍCIO e não funcional.
    Usado apenas para testes que mockam chamadas HTTP.
    """
    return "https://test-fake-project.supabase.co"


@pytest.fixture
def fake_supabase_key() -> str:
    """
    Chave fake do Supabase para testes.

    ⚠️ ATENÇÃO: Este é um valor FICTÍCIO e não funcional.
    Usado apenas para testes que mockam autenticação.
    """
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.FAKE_TEST_KEY_DO_NOT_USE"


@pytest.fixture
def fake_env_vars(fake_supabase_url: str, fake_supabase_key: str) -> dict[str, str]:
    """
    Dicionário completo de variáveis de ambiente fake para testes.

    ⚠️ ATENÇÃO: Todos os valores são FICTÍCIOS e não funcionais.
    Use com `patch.dict("os.environ", fake_env_vars)` nos testes.
    """
    return {
        "SUPABASE_URL": fake_supabase_url,
        "SUPABASE_KEY": fake_supabase_key,
        "RC_LOG_LEVEL": "DEBUG",
        "ENVIRONMENT": "test",
    }
