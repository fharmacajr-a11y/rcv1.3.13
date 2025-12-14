# -*- coding: utf-8 -*-
"""
MF-18: Helpers para sessão, autenticação e utilitários gerais do Hub.

Este módulo contém funções relacionadas à autenticação, formatação de
autores e lógica de cooldown/retry.

Extraído de hub_screen_helpers.py na MF-18 para melhor organização.
"""

from __future__ import annotations

import time


def is_auth_ready(has_app: bool, has_auth: bool, is_authenticated: bool) -> bool:
    """
    Verifica se autenticação está pronta sem levantar exceção.

    Centraliza a lógica de verificação de autenticação para evitar
    duplicação e facilitar testes.

    Args:
        has_app: Se objeto app existe
        has_auth: Se app.auth existe
        is_authenticated: Se app.auth.is_authenticated é True

    Returns:
        True se autenticação está pronta, False caso contrário

    Examples:
        >>> is_auth_ready(True, True, True)
        True
        >>> is_auth_ready(True, True, False)
        False
        >>> is_auth_ready(True, False, True)
        False
        >>> is_auth_ready(False, True, True)
        False
    """
    return has_app and has_auth and is_authenticated


def extract_email_prefix(email: str | None) -> str:
    """
    Extrai o prefixo de um email (parte antes do @).

    Usado para criar nomes curtos a partir de emails quando
    display_name não está disponível.

    Args:
        email: Endereço de email completo ou None

    Returns:
        Prefixo do email (antes do @) ou string vazia

    Examples:
        >>> extract_email_prefix("usuario@example.com")
        'usuario'
        >>> extract_email_prefix("joao.silva@empresa.com.br")
        'joao.silva'
        >>> extract_email_prefix("sem-arroba")
        'sem-arroba'
        >>> extract_email_prefix("")
        ''
        >>> extract_email_prefix(None)
        ''
        >>> extract_email_prefix("  user@test.com  ")
        'user'
    """
    if not email:
        return ""

    email = email.strip()
    if "@" in email:
        return email.split("@")[0].strip()

    return email


def format_author_fallback(
    email: str | None,
    display_name: str | None = None,
) -> str:
    """
    Formata nome de autor com fallback para email/prefixo.

    Hierarquia de prioridade:
    1. display_name (se não vazio)
    2. prefixo do email
    3. email completo
    4. "Anônimo"

    Args:
        email: Endereço de email do autor
        display_name: Nome de exibição preferido (opcional)

    Returns:
        Nome formatado para exibição

    Examples:
        >>> format_author_fallback("user@test.com", "João Silva")
        'João Silva'
        >>> format_author_fallback("user@test.com", "")
        'user'
        >>> format_author_fallback("user@test.com", None)
        'user'
        >>> format_author_fallback("user@test.com")
        'user'
        >>> format_author_fallback("", "")
        'Anônimo'
        >>> format_author_fallback(None, None)
        'Anônimo'
        >>> format_author_fallback("sem-arroba@", "")
        'sem-arroba'
    """
    # Prioridade 1: display_name
    if display_name and display_name.strip():
        return display_name.strip()

    # Prioridade 2/3: prefixo ou email completo
    if email:
        prefix = extract_email_prefix(email)
        if prefix:
            return prefix
        # Se não tem @, usar email completo
        if email.strip():
            return email.strip()

    # Fallback final
    return "Anônimo"


def should_skip_refresh_by_cooldown(
    last_refresh: float,
    cooldown_seconds: int,
    force: bool = False,
) -> bool:
    """
    Determina se deve pular refresh baseado em cooldown e flag force.

    Implementa lógica de cooldown para evitar requisições duplicadas:
    - Se force=True, sempre refresha (ignora cooldown)
    - Se tempo desde último refresh < cooldown, pula
    - Caso contrário, permite refresh

    Args:
        last_refresh: Timestamp Unix (time.time()) do último refresh
        cooldown_seconds: Segundos mínimos entre refreshes
        force: Se True, ignora cooldown e sempre refresha

    Returns:
        bool: True se deve PULAR refresh, False se deve PERMITIR refresh

    Examples:
        >>> now = time.time()
        >>> # Força sempre permite
        >>> should_skip_refresh_by_cooldown(now, 30, force=True)
        False
        >>> # Refresh recente (5s atrás) com cooldown de 30s
        >>> should_skip_refresh_by_cooldown(now - 5, 30, force=False)
        True
        >>> # Refresh antigo (35s atrás) com cooldown de 30s
        >>> should_skip_refresh_by_cooldown(now - 35, 30, force=False)
        False
        >>> # Primeiro refresh (last_refresh=0)
        >>> should_skip_refresh_by_cooldown(0, 30, force=False)
        False
        >>> # Cooldown de 0 sempre permite
        >>> should_skip_refresh_by_cooldown(now, 0, force=False)
        False
    """
    if force:
        return False  # force=True sempre permite refresh

    now = time.time()
    elapsed = now - last_refresh

    # Se cooldown é 0 ou negativo, sempre permite
    if cooldown_seconds <= 0:
        return False

    # Se elapsed < cooldown, deve pular (True)
    return elapsed < cooldown_seconds


def calculate_retry_delay_ms(
    retry_count: int,
    base_delay_ms: int = 60000,
    max_delay_ms: int = 300000,
) -> int:
    """
    Calcula delay para retry com backoff exponencial.

    Implementa estratégia de backoff exponencial para retry de operações
    falhadas (ex: tabela de notas ausente).

    Args:
        retry_count: Número de tentativas já realizadas (0 = primeira tentativa)
        base_delay_ms: Delay base em milissegundos (padrão 60s)
        max_delay_ms: Delay máximo em milissegundos (padrão 5min)

    Returns:
        int: Delay em milissegundos para próximo retry

    Examples:
        >>> calculate_retry_delay_ms(0)
        60000
        >>> calculate_retry_delay_ms(1)
        120000
        >>> calculate_retry_delay_ms(2)
        240000
        >>> calculate_retry_delay_ms(10)
        300000
        >>> calculate_retry_delay_ms(0, base_delay_ms=1000, max_delay_ms=5000)
        1000
    """
    delay = base_delay_ms * (2**retry_count)
    return min(delay, max_delay_ms)
