# -*- coding: utf-8 -*-
"""
MF-53: Testes para hub_helpers_session.py

Testa helpers de sessão, autenticação e utilitários do Hub:
- is_auth_ready
- extract_email_prefix
- format_author_fallback
- should_skip_refresh_by_cooldown
- calculate_retry_delay_ms

Meta: 100% de cobertura (branches + statements).
"""

from __future__ import annotations

import time

from src.modules.hub.views.hub_helpers_session import (
    calculate_retry_delay_ms,
    extract_email_prefix,
    format_author_fallback,
    is_auth_ready,
    should_skip_refresh_by_cooldown,
)


# ==============================================================================
# is_auth_ready
# ==============================================================================
class TestIsAuthReady:
    """Testa verificação de prontidão da autenticação."""

    def test_all_true_returns_true(self) -> None:
        """Quando todos os flags são True, retorna True."""
        assert is_auth_ready(has_app=True, has_auth=True, is_authenticated=True) is True

    def test_has_app_false_returns_false(self) -> None:
        """Quando has_app é False, retorna False mesmo com outros True."""
        assert is_auth_ready(has_app=False, has_auth=True, is_authenticated=True) is False

    def test_has_auth_false_returns_false(self) -> None:
        """Quando has_auth é False, retorna False mesmo com outros True."""
        assert is_auth_ready(has_app=True, has_auth=False, is_authenticated=True) is False

    def test_is_authenticated_false_returns_false(self) -> None:
        """Quando is_authenticated é False, retorna False."""
        assert is_auth_ready(has_app=True, has_auth=True, is_authenticated=False) is False

    def test_all_false_returns_false(self) -> None:
        """Quando todos os flags são False, retorna False."""
        assert is_auth_ready(has_app=False, has_auth=False, is_authenticated=False) is False


# ==============================================================================
# extract_email_prefix
# ==============================================================================
class TestExtractEmailPrefix:
    """Testa extração de prefixo de email."""

    def test_normal_email_returns_prefix(self) -> None:
        """Email normal retorna parte antes do @."""
        assert extract_email_prefix("user@example.com") == "user"
        assert extract_email_prefix("joao.silva@empresa.com.br") == "joao.silva"

    def test_email_with_whitespace_strips_result(self) -> None:
        """Email com espaços retorna prefixo sem espaços."""
        assert extract_email_prefix("  user@test.com  ") == "user"
        assert extract_email_prefix("nome @example.com") == "nome"

    def test_email_without_at_returns_full_email(self) -> None:
        """Email sem @ retorna email completo (após strip)."""
        assert extract_email_prefix("sem-arroba") == "sem-arroba"
        assert extract_email_prefix("usuario") == "usuario"

    def test_empty_string_returns_empty(self) -> None:
        """String vazia retorna vazio."""
        assert extract_email_prefix("") == ""

    def test_none_returns_empty(self) -> None:
        """None retorna string vazia."""
        assert extract_email_prefix(None) == ""

    def test_whitespace_only_returns_empty(self) -> None:
        """String só com espaços retorna vazio."""
        assert extract_email_prefix("   ") == ""

    def test_unicode_email_prefix(self) -> None:
        """Email com unicode no prefixo funciona corretamente."""
        assert extract_email_prefix("joão@test.com") == "joão"
        assert extract_email_prefix("maría@example.com") == "maría"

    def test_multiple_at_signs_uses_first(self) -> None:
        """Email com múltiplos @ usa o primeiro."""
        assert extract_email_prefix("user@@example.com") == "user"
        assert extract_email_prefix("a@b@c") == "a"


# ==============================================================================
# format_author_fallback
# ==============================================================================
class TestFormatAuthorFallback:
    """Testa formatação de autor com fallback."""

    def test_display_name_priority_when_present(self) -> None:
        """Quando display_name existe e não é vazio, usa ele."""
        assert format_author_fallback("user@test.com", "João Silva") == "João Silva"
        assert format_author_fallback("", "Maria Santos") == "Maria Santos"
        assert format_author_fallback(None, "Pedro Oliveira") == "Pedro Oliveira"

    def test_display_name_with_whitespace_strips(self) -> None:
        """Display name com espaços extras é normalizado."""
        assert format_author_fallback("user@test.com", "  João Silva  ") == "João Silva"

    def test_empty_display_name_falls_back_to_email_prefix(self) -> None:
        """Display name vazio ou só espaços usa prefixo do email."""
        assert format_author_fallback("user@test.com", "") == "user"
        assert format_author_fallback("user@test.com", "   ") == "user"
        assert format_author_fallback("joao.silva@example.com", None) == "joao.silva"

    def test_no_display_name_uses_email_prefix(self) -> None:
        """Sem display_name, usa prefixo do email."""
        assert format_author_fallback("user@test.com") == "user"
        assert format_author_fallback("admin@system.net", None) == "admin"

    def test_email_without_at_uses_full_email(self) -> None:
        """Email sem @ usa email completo como fallback."""
        assert format_author_fallback("usuario", "") == "usuario"
        assert format_author_fallback("nome-completo", None) == "nome-completo"

    def test_empty_email_and_display_name_returns_anonimo(self) -> None:
        """Sem email e display_name retorna 'Anônimo'."""
        assert format_author_fallback("", "") == "Anônimo"
        assert format_author_fallback(None, None) == "Anônimo"
        assert format_author_fallback("   ", "  ") == "Anônimo"

    def test_email_with_at_only_uses_prefix(self) -> None:
        """Email terminando em @ usa prefixo antes do @."""
        assert format_author_fallback("sem-arroba@", "") == "sem-arroba"

    def test_email_only_at_symbol_returns_at(self) -> None:
        """Email que é só @ retorna @ (prefix vazio, email.strip() é '@')."""
        # extract_email_prefix("@") retorna "" (vazio antes do @)
        # mas email.strip() é "@", então retorna "@"
        assert format_author_fallback("@", "") == "@"

    def test_unicode_display_name(self) -> None:
        """Display name com unicode funciona corretamente."""
        assert format_author_fallback("user@test.com", "José María") == "José María"
        assert format_author_fallback("", "Ángel López") == "Ángel López"


# ==============================================================================
# should_skip_refresh_by_cooldown
# ==============================================================================
class TestShouldSkipRefreshByCooldown:
    """Testa lógica de cooldown para refresh."""

    def test_force_true_always_allows_refresh(self) -> None:
        """force=True sempre retorna False (permite refresh)."""
        now = time.time()
        # Mesmo com refresh recente
        assert should_skip_refresh_by_cooldown(now, 30, force=True) is False
        # Mesmo com cooldown alto
        assert should_skip_refresh_by_cooldown(now, 999999, force=True) is False
        # Mesmo com refresh há 1 segundo
        assert should_skip_refresh_by_cooldown(now - 1, 30, force=True) is False

    def test_recent_refresh_skips(self) -> None:
        """Refresh recente (dentro do cooldown) retorna True (pula)."""
        now = time.time()
        # 5s atrás, cooldown de 30s → pula
        assert should_skip_refresh_by_cooldown(now - 5, 30, force=False) is True
        # 10s atrás, cooldown de 60s → pula
        assert should_skip_refresh_by_cooldown(now - 10, 60, force=False) is True

    def test_old_refresh_allows(self) -> None:
        """Refresh antigo (fora do cooldown) retorna False (permite)."""
        now = time.time()
        # 35s atrás, cooldown de 30s → permite
        assert should_skip_refresh_by_cooldown(now - 35, 30, force=False) is False
        # 70s atrás, cooldown de 60s → permite
        assert should_skip_refresh_by_cooldown(now - 70, 60, force=False) is False

    def test_first_refresh_allows(self) -> None:
        """Primeiro refresh (last_refresh=0) sempre permite."""
        assert should_skip_refresh_by_cooldown(0, 30, force=False) is False
        assert should_skip_refresh_by_cooldown(0, 999, force=False) is False

    def test_zero_cooldown_always_allows(self) -> None:
        """Cooldown de 0 sempre retorna False (permite)."""
        now = time.time()
        assert should_skip_refresh_by_cooldown(now, 0, force=False) is False
        assert should_skip_refresh_by_cooldown(now - 1000, 0, force=False) is False

    def test_negative_cooldown_always_allows(self) -> None:
        """Cooldown negativo sempre retorna False (permite)."""
        now = time.time()
        assert should_skip_refresh_by_cooldown(now, -1, force=False) is False
        assert should_skip_refresh_by_cooldown(now - 100, -999, force=False) is False

    def test_exactly_at_cooldown_boundary_skips(self) -> None:
        """No limite exato do cooldown, deve pular (elapsed < cooldown)."""
        now = time.time()
        # Exatamente 30s atrás, cooldown 30s → elapsed == 30, então permite
        # (porque a condição é elapsed < cooldown)
        assert should_skip_refresh_by_cooldown(now - 30, 30, force=False) is False

    def test_just_before_cooldown_expires_skips(self) -> None:
        """Um pouco antes de expirar cooldown, ainda pula."""
        now = time.time()
        # 29.5s atrás, cooldown 30s → pula
        assert should_skip_refresh_by_cooldown(now - 29.5, 30, force=False) is True


# ==============================================================================
# calculate_retry_delay_ms
# ==============================================================================
class TestCalculateRetryDelayMs:
    """Testa cálculo de delay para retry com backoff exponencial."""

    def test_first_retry_returns_base_delay(self) -> None:
        """Primeira tentativa (retry_count=0) retorna base_delay_ms."""
        assert calculate_retry_delay_ms(0) == 60000
        assert calculate_retry_delay_ms(0, base_delay_ms=1000, max_delay_ms=5000) == 1000

    def test_exponential_backoff(self) -> None:
        """Delay dobra a cada retry (backoff exponencial)."""
        assert calculate_retry_delay_ms(1) == 120000  # 60000 * 2^1
        assert calculate_retry_delay_ms(2) == 240000  # 60000 * 2^2
        # retry_count=3 → 60000 * 2^3 = 480000, mas max padrão é 300000
        assert calculate_retry_delay_ms(3) == 300000

    def test_max_delay_caps_result(self) -> None:
        """Delay não ultrapassa max_delay_ms."""
        # 60000 * 2^10 = 61440000, mas max é 300000
        assert calculate_retry_delay_ms(10) == 300000
        assert calculate_retry_delay_ms(100) == 300000

    def test_custom_base_and_max(self) -> None:
        """Parâmetros customizados funcionam corretamente."""
        # base=1000, max=5000
        assert calculate_retry_delay_ms(0, base_delay_ms=1000, max_delay_ms=5000) == 1000
        assert calculate_retry_delay_ms(1, base_delay_ms=1000, max_delay_ms=5000) == 2000
        assert calculate_retry_delay_ms(2, base_delay_ms=1000, max_delay_ms=5000) == 4000
        # 2^3 = 8000, mas max é 5000
        assert calculate_retry_delay_ms(3, base_delay_ms=1000, max_delay_ms=5000) == 5000

    def test_high_retry_count_hits_max(self) -> None:
        """Retry count alto sempre retorna max_delay_ms."""
        result = calculate_retry_delay_ms(50, base_delay_ms=100, max_delay_ms=10000)
        assert result == 10000


# ==============================================================================
# Testes de integração (edge cases combinados)
# ==============================================================================
class TestIntegrationEdgeCases:
    """Testa casos de borda e integrações entre funções."""

    def test_format_author_with_unicode_email_and_empty_display_name(self) -> None:
        """Unicode no email com display name vazio usa prefixo unicode."""
        assert format_author_fallback("josé@test.com", "") == "josé"
        assert format_author_fallback("maría@example.com", None) == "maría"

    def test_cooldown_with_exactly_elapsed_time(self) -> None:
        """Elapsed exatamente igual ao cooldown permite refresh."""
        now = time.time()
        # Se cooldown é 10 e elapsed é 10, elapsed < cooldown é False → permite
        assert should_skip_refresh_by_cooldown(now - 10, 10, force=False) is False

    def test_extract_email_prefix_with_multiple_dots(self) -> None:
        """Email com múltiplos pontos no prefixo mantém todos."""
        assert extract_email_prefix("joao.da.silva@example.com") == "joao.da.silva"

    def test_calculate_retry_at_exact_max_boundary(self) -> None:
        """Quando 2^n * base == max, retorna max (não ultrapassa)."""
        # base=100, 2^3=8 → 800, max=800
        assert calculate_retry_delay_ms(3, base_delay_ms=100, max_delay_ms=800) == 800
