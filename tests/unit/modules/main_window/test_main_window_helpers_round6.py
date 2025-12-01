# -*- coding: utf-8 -*-
"""
Testes para state_helpers.py - Round 6 (status/health/user-state).

Cobertura de funções puras extraídas da classe App relacionadas a:
- build_user_status_suffix
- combine_status_display
- compute_status_dot_style
"""

from __future__ import annotations

import pytest

from src.modules.main_window.views.state_helpers import (
    StatusDotStyle,
    build_user_status_suffix,
    combine_status_display,
    compute_status_dot_style,
)


class TestBuildUserStatusSuffix:
    """Testes para build_user_status_suffix."""

    def test_with_email_and_role(self):
        """Com email e role, retorna sufixo formatado."""
        result = build_user_status_suffix("user@example.com", "admin")
        assert result == " | Usuário: user@example.com (admin)"

    def test_with_email_default_role(self):
        """Com email e role padrão."""
        result = build_user_status_suffix("test@test.com")
        assert result == " | Usuário: test@test.com (user)"

    def test_empty_email(self):
        """Email vazio retorna string vazia."""
        result = build_user_status_suffix("")
        assert result == ""

    def test_empty_email_with_role(self):
        """Email vazio retorna string vazia mesmo com role."""
        result = build_user_status_suffix("", "admin")
        assert result == ""

    def test_various_roles(self):
        """Testa diferentes roles."""
        result1 = build_user_status_suffix("admin@test.com", "superuser")
        assert "superuser" in result1

        result2 = build_user_status_suffix("viewer@test.com", "readonly")
        assert "readonly" in result2


class TestCombineStatusDisplay:
    """Testes para combine_status_display."""

    def test_base_and_suffix(self):
        """Base + suffix sem modificação."""
        result = combine_status_display("LOCAL", " | Usuário: user@test.com (admin)")
        assert result == "LOCAL | Usuário: user@test.com (admin)"

    def test_empty_base_with_pipe_suffix(self):
        """Base vazia remove " | " do início do suffix."""
        result = combine_status_display("", " | Usuário: user@test.com (admin)")
        assert result == "Usuário: user@test.com (admin)"
        assert not result.startswith(" | ")

    def test_base_only(self):
        """Apenas base, sem suffix."""
        result = combine_status_display("PROD", "")
        assert result == "PROD"

    def test_both_empty(self):
        """Ambos vazios."""
        result = combine_status_display("", "")
        assert result == ""

    def test_suffix_without_pipe_prefix(self):
        """Suffix sem " | " prefix com base vazia."""
        result = combine_status_display("", "Status: OK")
        assert result == "Status: OK"

    def test_complex_base_and_suffix(self):
        """Base complexa + suffix."""
        result = combine_status_display("SUPABASE (online)", " | Usuário: admin@app.com (superuser)")
        assert result == "SUPABASE (online) | Usuário: admin@app.com (superuser)"


class TestComputeStatusDotStyle:
    """Testes para compute_status_dot_style."""

    def test_online_true(self):
        """Online = True → success (verde)."""
        result = compute_status_dot_style(True)
        assert isinstance(result, StatusDotStyle)
        assert result.symbol == "•"
        assert result.bootstyle == "success"

    def test_offline_false(self):
        """Online = False → danger (vermelho)."""
        result = compute_status_dot_style(False)
        assert result.symbol == "•"
        assert result.bootstyle == "danger"

    def test_unknown_none(self):
        """Online = None → warning (amarelo/cinza)."""
        result = compute_status_dot_style(None)
        assert result.symbol == "•"
        assert result.bootstyle == "warning"

    def test_symbol_consistency(self):
        """Símbolo sempre é '•' independente do estado."""
        assert compute_status_dot_style(True).symbol == "•"
        assert compute_status_dot_style(False).symbol == "•"
        assert compute_status_dot_style(None).symbol == "•"

    def test_immutability(self):
        """StatusDotStyle é imutável (frozen dataclass)."""
        style = compute_status_dot_style(True)
        with pytest.raises(Exception):  # FrozenInstanceError
            style.bootstyle = "danger"


class TestRound6Integration:
    """Testes de integração para workflows de Round 6."""

    def test_full_status_display_workflow(self):
        """Workflow completo de montagem de status display."""
        # 1. Construir suffix de usuário
        email = "admin@company.com"
        role = "superuser"
        suffix = build_user_status_suffix(email, role)
        assert "admin@company.com" in suffix
        assert "superuser" in suffix

        # 2. Combinar com base
        base = "PROD"
        display = combine_status_display(base, suffix)
        assert display.startswith("PROD")
        assert "admin@company.com" in display

        # 3. Calcular estilo do dot
        dot_style = compute_status_dot_style(True)
        assert dot_style.bootstyle == "success"

    def test_offline_status_workflow(self):
        """Workflow de status offline."""
        # Usuário offline
        suffix = build_user_status_suffix("user@test.com", "user")
        display = combine_status_display("LOCAL", suffix)
        dot_style = compute_status_dot_style(False)

        assert "LOCAL" in display
        assert "user@test.com" in display
        assert dot_style.bootstyle == "danger"

    def test_no_user_status_workflow(self):
        """Workflow sem usuário autenticado."""
        # Sem email
        suffix = build_user_status_suffix("", "admin")
        assert suffix == ""

        # Display com base apenas
        display = combine_status_display("LOCAL", suffix)
        assert display == "LOCAL"

        # Dot em estado unknown
        dot_style = compute_status_dot_style(None)
        assert dot_style.bootstyle == "warning"

    def test_empty_base_user_only_workflow(self):
        """Workflow com base vazia, apenas info de usuário."""
        suffix = build_user_status_suffix("test@app.com", "viewer")
        display = combine_status_display("", suffix)

        # Deve remover " | " do início
        assert display == "Usuário: test@app.com (viewer)"
        assert not display.startswith(" | ")

    def test_status_transitions(self):
        """Testa transições de estado."""
        # Online → success
        online_style = compute_status_dot_style(True)
        assert online_style.bootstyle == "success"

        # Unknown → warning
        unknown_style = compute_status_dot_style(None)
        assert unknown_style.bootstyle == "warning"

        # Offline → danger
        offline_style = compute_status_dot_style(False)
        assert offline_style.bootstyle == "danger"

    def test_multiple_users_different_roles(self):
        """Testa múltiplos usuários com roles diferentes."""
        users = [
            ("admin@test.com", "admin"),
            ("user@test.com", "user"),
            ("viewer@test.com", "readonly"),
        ]

        for email, role in users:
            suffix = build_user_status_suffix(email, role)
            assert email in suffix
            assert role in suffix

            display = combine_status_display("PROD", suffix)
            assert "PROD" in display
            assert email in display


class TestEdgeCases:
    """Testes de edge cases e comportamentos extremos."""

    def test_whitespace_handling(self):
        """Testa tratamento de whitespace."""
        # Email com espaços (edge case improvável mas possível)
        result = build_user_status_suffix("  user@test.com  ", "admin")
        # Helper não faz strip, assume input limpo
        assert "user@test.com" in result

    def test_special_characters_in_email(self):
        """Emails com caracteres especiais."""
        email = "user+tag@sub.example.com"
        result = build_user_status_suffix(email, "user")
        assert email in result

    def test_very_long_email(self):
        """Email muito longo."""
        long_email = "very.long.email.address.with.many.dots@subdomain.example.corporation.com"
        result = build_user_status_suffix(long_email, "admin")
        assert long_email in result

    def test_unicode_in_role(self):
        """Role com caracteres unicode."""
        result = build_user_status_suffix("user@test.com", "administrador")
        assert "administrador" in result

    def test_combine_with_special_base(self):
        """Base com caracteres especiais."""
        result = combine_status_display("CLOUD-PROD (região: BR)", " | Usuário: x@y.z (user)")
        assert "CLOUD-PROD" in result
        assert "região: BR" in result
        assert "x@y.z" in result
