# -*- coding: utf-8 -*-
"""
Testes para hub_screen_helpers.py - Fase 01 + Round 5 + Fase 02.

Cobertura de funções puras extraídas de HubScreen:
- calculate_module_button_style
- calculate_notes_ui_state
- calculate_notes_content_hash
- should_skip_refresh_by_cooldown
- normalize_note_dict
- build_module_buttons (Round 5)
- is_auth_ready (Round 5)
- extract_email_prefix (Round 5)
- format_author_fallback (Round 5)
- format_timestamp (Round 5 Fase 02)
- format_note_line (Round 5 Fase 02)
- should_show_notes_section (Round 5 Fase 02)
- format_notes_count (Round 5 Fase 02)
- is_notes_list_empty (Round 5 Fase 02)
- should_skip_render_empty_notes (Round 5 Fase 02)
- calculate_retry_delay_ms (Round 5 Fase 02)
"""

from __future__ import annotations

import time

import pytest

from src.modules.hub.views.hub_screen_helpers import (
    build_module_buttons,
    calculate_module_button_style,
    calculate_notes_content_hash,
    calculate_notes_ui_state,
    calculate_retry_delay_ms,
    extract_email_prefix,
    format_author_fallback,
    format_note_line,
    format_notes_count,
    format_timestamp,
    is_auth_ready,
    is_notes_list_empty,
    normalize_note_dict,
    should_skip_refresh_by_cooldown,
    should_skip_render_empty_notes,
    should_show_notes_section,
)


class TestCalculateModuleButtonStyle:
    """Testes para calculate_module_button_style."""

    def test_default_no_flags(self):
        """Sem flags, retorna 'secondary'."""
        assert calculate_module_button_style() == "secondary"

    def test_highlight_only(self):
        """Com highlight=True, retorna 'success'."""
        assert calculate_module_button_style(highlight=True) == "success"

    def test_yellow_only(self):
        """Com yellow=True, retorna 'warning'."""
        assert calculate_module_button_style(yellow=True) == "warning"

    def test_bootstyle_overrides_all(self):
        """bootstyle tem prioridade máxima."""
        assert calculate_module_button_style(bootstyle="danger") == "danger"
        assert calculate_module_button_style(highlight=True, bootstyle="info") == "info"
        assert calculate_module_button_style(yellow=True, bootstyle="primary") == "primary"

    def test_yellow_overrides_highlight(self):
        """yellow tem prioridade sobre highlight."""
        assert calculate_module_button_style(highlight=True, yellow=True) == "warning"

    def test_all_false(self):
        """Explicitamente False retorna 'secondary'."""
        assert calculate_module_button_style(highlight=False, yellow=False, bootstyle=None) == "secondary"

    def test_custom_bootstyle(self):
        """Aceita qualquer string em bootstyle."""
        assert calculate_module_button_style(bootstyle="custom-style") == "custom-style"


class TestCalculateNotesUiState:
    """Testes para calculate_notes_ui_state."""

    def test_with_org_id(self):
        """Com org_id, botão habilitado e sem placeholder."""
        result = calculate_notes_ui_state(has_org_id=True)
        assert result["button_enabled"] is True
        assert result["placeholder_message"] == ""
        assert result["text_field_enabled"] is True

    def test_without_org_id(self):
        """Sem org_id, botão desabilitado e com mensagem."""
        result = calculate_notes_ui_state(has_org_id=False)
        assert result["button_enabled"] is False
        assert "Sessão sem organização" in result["placeholder_message"]
        assert "Faça login novamente" in result["placeholder_message"]
        assert result["text_field_enabled"] is False

    def test_returns_dict_with_all_keys(self):
        """Retorna dict com todas as chaves necessárias."""
        result = calculate_notes_ui_state(has_org_id=True)
        assert "button_enabled" in result
        assert "placeholder_message" in result
        assert "text_field_enabled" in result

    def test_boolean_coercion(self):
        """Aceita valores truthy/falsy convertidos para bool."""
        # Truthy (string não-vazia convertida para True)
        result = calculate_notes_ui_state(has_org_id=bool("org-123"))
        assert result["button_enabled"] is True

        # Falsy (None convertido para False)
        result = calculate_notes_ui_state(has_org_id=bool(None))
        assert result["button_enabled"] is False


class TestCalculateNotesContentHash:
    """Testes para calculate_notes_content_hash."""

    def test_empty_list(self):
        """Lista vazia gera hash consistente."""
        hash1 = calculate_notes_content_hash([])
        hash2 = calculate_notes_content_hash([])
        assert hash1 == hash2
        assert len(hash1) == 32  # MD5 hex = 32 caracteres

    def test_same_content_same_hash(self):
        """Mesmo conteúdo gera mesmo hash."""
        notes = [
            {
                "author_email": "user@test.com",
                "created_at": "2025-01-01T10:00:00Z",
                "body": "Test message",
                "author_name": "Test User",
            }
        ]
        hash1 = calculate_notes_content_hash(notes)
        hash2 = calculate_notes_content_hash(notes)
        assert hash1 == hash2

    def test_different_body_different_hash(self):
        """Mudança no body gera hash diferente."""
        notes1 = [{"author_email": "user@test.com", "created_at": "2025-01-01", "body": "Original"}]
        notes2 = [{"author_email": "user@test.com", "created_at": "2025-01-01", "body": "Changed"}]
        assert calculate_notes_content_hash(notes1) != calculate_notes_content_hash(notes2)

    def test_different_author_different_hash(self):
        """Mudança no autor gera hash diferente."""
        notes1 = [{"author_email": "user1@test.com", "body": "Test"}]
        notes2 = [{"author_email": "user2@test.com", "body": "Test"}]
        assert calculate_notes_content_hash(notes1) != calculate_notes_content_hash(notes2)

    def test_different_timestamp_different_hash(self):
        """Mudança no timestamp gera hash diferente."""
        notes1 = [{"author_email": "user@test.com", "created_at": "2025-01-01T10:00:00Z", "body": "Test"}]
        notes2 = [{"author_email": "user@test.com", "created_at": "2025-01-01T11:00:00Z", "body": "Test"}]
        assert calculate_notes_content_hash(notes1) != calculate_notes_content_hash(notes2)

    def test_email_case_normalization(self):
        """Email é normalizado para lowercase."""
        notes1 = [{"author_email": "USER@test.com", "body": "Test"}]
        notes2 = [{"author_email": "user@test.com", "body": "Test"}]
        assert calculate_notes_content_hash(notes1) == calculate_notes_content_hash(notes2)

    def test_missing_fields_use_defaults(self):
        """Campos ausentes usam strings vazias."""
        notes = [{}]  # Todos os campos ausentes
        hash_result = calculate_notes_content_hash(notes)
        assert len(hash_result) == 32

    def test_multiple_notes(self):
        """Múltiplas notas são processadas."""
        notes = [
            {"author_email": "user1@test.com", "body": "First"},
            {"author_email": "user2@test.com", "body": "Second"},
            {"author_email": "user3@test.com", "body": "Third"},
        ]
        hash_result = calculate_notes_content_hash(notes)
        assert len(hash_result) == 32

    def test_order_matters(self):
        """Ordem das notas afeta o hash."""
        notes1 = [
            {"author_email": "user1@test.com", "body": "First"},
            {"author_email": "user2@test.com", "body": "Second"},
        ]
        notes2 = [
            {"author_email": "user2@test.com", "body": "Second"},
            {"author_email": "user1@test.com", "body": "First"},
        ]
        # Ordem diferente = hash diferente (porque usamos lista, não conjunto)
        assert calculate_notes_content_hash(notes1) != calculate_notes_content_hash(notes2)


class TestShouldSkipRefreshByCooldown:
    """Testes para should_skip_refresh_by_cooldown."""

    def test_force_always_allows(self):
        """force=True sempre permite refresh (retorna False)."""
        now = time.time()
        # Refresh recente (1s atrás)
        assert should_skip_refresh_by_cooldown(now - 1, 30, force=True) is False
        # Refresh muito antigo
        assert should_skip_refresh_by_cooldown(now - 100, 30, force=True) is False

    def test_recent_refresh_skips(self):
        """Refresh recente (dentro do cooldown) pula."""
        now = time.time()
        # 5 segundos atrás, cooldown de 30s
        assert should_skip_refresh_by_cooldown(now - 5, 30, force=False) is True

    def test_old_refresh_allows(self):
        """Refresh antigo (fora do cooldown) permite."""
        now = time.time()
        # 35 segundos atrás, cooldown de 30s
        assert should_skip_refresh_by_cooldown(now - 35, 30, force=False) is False

    def test_first_refresh_allows(self):
        """Primeiro refresh (last_refresh=0) sempre permite."""
        assert should_skip_refresh_by_cooldown(0, 30, force=False) is False

    def test_zero_cooldown_always_allows(self):
        """Cooldown de 0 sempre permite."""
        now = time.time()
        assert should_skip_refresh_by_cooldown(now, 0, force=False) is False

    def test_negative_cooldown_always_allows(self):
        """Cooldown negativo sempre permite."""
        now = time.time()
        assert should_skip_refresh_by_cooldown(now, -10, force=False) is False

    def test_exact_cooldown_boundary(self):
        """Exatamente no limite do cooldown pula."""
        now = time.time()
        # Exatamente 30s atrás, cooldown de 30s
        # elapsed = 30, cooldown = 30 → 30 < 30 é False, então permite
        assert should_skip_refresh_by_cooldown(now - 30, 30, force=False) is False

    def test_one_second_before_cooldown(self):
        """1 segundo antes do cooldown expirar ainda pula."""
        now = time.time()
        # 29 segundos atrás, cooldown de 30s
        assert should_skip_refresh_by_cooldown(now - 29, 30, force=False) is True


class TestNormalizeNoteDict:
    """Testes para normalize_note_dict."""

    def test_dict_with_all_fields(self):
        """Dict completo é normalizado."""
        note = {
            "author_email": "user@test.com",
            "created_at": "2025-01-01T10:00:00Z",
            "body": "Test message",
            "author_name": "Test User",
        }
        result = normalize_note_dict(note)
        assert result["author_email"] == "user@test.com"
        assert result["created_at"] == "2025-01-01T10:00:00Z"
        assert result["body"] == "Test message"
        assert result["author_name"] == "Test User"

    def test_dict_with_alternative_keys(self):
        """Dict com chaves alternativas é mapeado."""
        note = {
            "author": "user@test.com",  # Alternativa para author_email
            "timestamp": "2025-01-01",  # Alternativa para created_at
            "text": "Test",  # Alternativa para body
            "display_name": "User",  # Alternativa para author_name
        }
        result = normalize_note_dict(note)
        assert result["author_email"] == "user@test.com"
        assert result["created_at"] == "2025-01-01"
        assert result["body"] == "Test"
        assert result["author_name"] == "User"

    def test_empty_dict(self):
        """Dict vazio retorna campos com strings vazias."""
        result = normalize_note_dict({})
        assert result["author_email"] == ""
        assert result["created_at"] == ""
        assert result["body"] == ""
        assert result["author_name"] == ""

    def test_tuple_three_elements(self):
        """Tupla (created_at, author, body) é normalizada."""
        note = ("2025-01-01T10:00:00Z", "user@test.com", "Test message")
        result = normalize_note_dict(note)
        assert result["author_email"] == "user@test.com"
        assert result["created_at"] == "2025-01-01T10:00:00Z"
        assert result["body"] == "Test message"
        assert result["author_name"] == ""

    def test_list_two_elements(self):
        """Lista [author, body] é normalizada."""
        note = ["user@test.com", "Test message"]
        result = normalize_note_dict(note)
        assert result["author_email"] == "user@test.com"
        assert result["created_at"] == ""
        assert result["body"] == "Test message"

    def test_list_one_element(self):
        """Lista [body] é normalizada."""
        note = ["Solo message"]
        result = normalize_note_dict(note)
        assert result["author_email"] == ""
        assert result["created_at"] == ""
        assert result["body"] == "Solo message"

    def test_string_fallback(self):
        """String é convertida para body."""
        result = normalize_note_dict("Plain string message")
        assert result["author_email"] == ""
        assert result["created_at"] == ""
        assert result["body"] == "Plain string message"
        assert result["author_name"] == ""

    def test_none_fallback(self):
        """None é convertido para strings vazias."""
        result = normalize_note_dict(None)
        assert result["author_email"] == ""
        assert result["created_at"] == ""
        assert result["body"] == ""

    def test_integer_fallback(self):
        """Integer é convertido para body string."""
        result = normalize_note_dict(12345)
        assert result["body"] == "12345"


class TestIntegrationScenarios:
    """Testes de integração entre funções."""

    def test_button_style_workflow(self):
        """Workflow completo de estilo de botões."""
        # Módulo principal (Clientes) - highlight
        assert calculate_module_button_style(highlight=True) == "success"

        # Módulo em desenvolvimento - padrão
        assert calculate_module_button_style() == "secondary"

        # Módulo de atenção (Senhas) - yellow
        assert calculate_module_button_style(yellow=True) == "warning"

        # Override direto
        assert calculate_module_button_style(bootstyle="danger") == "danger"

    def test_notes_hash_stability(self):
        """Hash de notas é estável entre chamadas."""
        notes = [
            {"author_email": "user1@test.com", "body": "First"},
            {"author_email": "user2@test.com", "body": "Second"},
        ]
        hash1 = calculate_notes_content_hash(notes)
        hash2 = calculate_notes_content_hash(notes)
        hash3 = calculate_notes_content_hash(notes)
        assert hash1 == hash2 == hash3

    def test_cooldown_refresh_cycle(self):
        """Ciclo completo de cooldown."""
        now = time.time()
        cooldown = 10

        # Primeiro refresh (last_refresh=0)
        assert should_skip_refresh_by_cooldown(0, cooldown) is False

        # Logo após refresh (1s)
        assert should_skip_refresh_by_cooldown(now - 1, cooldown) is True

        # Meio do cooldown (5s)
        assert should_skip_refresh_by_cooldown(now - 5, cooldown) is True

        # Após cooldown (11s)
        assert should_skip_refresh_by_cooldown(now - 11, cooldown) is False

    def test_normalize_and_hash_workflow(self):
        """Normalizar notas e calcular hash."""
        raw_notes = [
            ("2025-01-01T10:00:00Z", "user1@test.com", "First"),
            {"author": "user2@test.com", "text": "Second"},
            ["user3@test.com", "Third"],
        ]

        # Normalizar todas
        normalized = [normalize_note_dict(n) for n in raw_notes]

        # Calcular hash
        hash_result = calculate_notes_content_hash(normalized)
        assert len(hash_result) == 32

        # Hash é estável
        assert hash_result == calculate_notes_content_hash(normalized)

    def test_ui_state_consistency(self):
        """Estado de UI é consistente."""
        # Com org_id
        state_on = calculate_notes_ui_state(True)
        assert state_on["button_enabled"] is True
        assert state_on["text_field_enabled"] is True

        # Sem org_id
        state_off = calculate_notes_ui_state(False)
        assert state_off["button_enabled"] is False
        assert state_off["text_field_enabled"] is False
        assert len(state_off["placeholder_message"]) > 0


# ============================================================================
# ROUND 5 - NOVOS HELPERS
# ============================================================================


class TestBuildModuleButtons:
    """Testes para build_module_buttons."""

    def test_default_all_enabled(self):
        """Configuração padrão habilita módulos principais."""
        buttons = build_module_buttons()
        assert len(buttons) == 6

        # Verificar ordem (senhas/auditoria removidos)
        texts = [b.text for b in buttons]
        assert texts[0] == "Clientes"
        assert texts[1] == "Fluxo de Caixa"

    def test_clientes_enabled(self):
        """Módulo Clientes habilitado."""
        buttons = build_module_buttons(has_clientes=True)
        clientes = [b for b in buttons if b.text == "Clientes"][0]
        assert clientes.enabled is True
        assert clientes.bootstyle == "info"
        assert clientes.has_callback is True

    @pytest.mark.skip(reason="Ação 'senhas' removida – migração CTK")
    def test_senhas_enabled(self):
        """Módulo Senhas habilitado."""
        buttons = build_module_buttons(has_senhas=True)
        senhas = [b for b in buttons if b.text == "Senhas"][0]
        assert senhas.enabled is True
        assert senhas.bootstyle == "info"

    @pytest.mark.skip(reason="Ação 'auditoria' removida – migração CTK")
    def test_auditoria_enabled(self):
        """Módulo Auditoria habilitado."""
        buttons = build_module_buttons(has_auditoria=True)
        auditoria = [b for b in buttons if b.text == "Auditoria"][0]
        assert auditoria.enabled is True
        assert auditoria.bootstyle == "success"

    def test_cashflow_disabled_by_default(self):
        """Fluxo de Caixa desabilitado por padrão."""
        buttons = build_module_buttons(has_cashflow=False)
        cashflow = [b for b in buttons if b.text == "Fluxo de Caixa"][0]
        assert cashflow.enabled is False
        assert cashflow.has_callback is False
        assert cashflow.bootstyle == "secondary"  # secondary quando disabled

    def test_cashflow_enabled(self):
        """Fluxo de Caixa habilitado quando especificado."""
        buttons = build_module_buttons(has_cashflow=True)
        cashflow = [b for b in buttons if b.text == "Fluxo de Caixa"][0]
        assert cashflow.enabled is True
        assert cashflow.has_callback is True

    def test_development_modules_present(self):
        """Módulos em desenvolvimento sempre aparecem."""
        buttons = build_module_buttons()
        texts = [b.text for b in buttons]
        assert "Anvisa" in texts
        assert "Farmácia Popular" in texts
        assert "Sngpc" in texts
        assert "Sifap" in texts

    def test_development_modules_disabled(self):
        """Módulos em desenvolvimento desabilitados por padrão."""
        buttons = build_module_buttons()
        anvisa = [b for b in buttons if b.text == "Anvisa"][0]
        farmacia = [b for b in buttons if b.text == "Farmácia Popular"][0]
        sngpc = [b for b in buttons if b.text == "Sngpc"][0]
        sifap = [b for b in buttons if b.text == "Sifap"][0]

        assert anvisa.enabled is False
        assert farmacia.enabled is False
        assert sngpc.enabled is False
        assert sifap.enabled is False

    def test_all_buttons_have_required_fields(self):
        """Todos os botões têm campos obrigatórios."""
        buttons = build_module_buttons()
        for btn in buttons:
            assert hasattr(btn, "text")
            assert hasattr(btn, "enabled")
            assert hasattr(btn, "bootstyle")
            assert hasattr(btn, "has_callback")
            assert isinstance(btn.text, str)
            assert isinstance(btn.enabled, bool)
            assert isinstance(btn.bootstyle, str)
            assert isinstance(btn.has_callback, bool)

    def test_button_order_stability(self):
        """Ordem dos botões é estável."""
        buttons1 = build_module_buttons()
        buttons2 = build_module_buttons()
        texts1 = [b.text for b in buttons1]
        texts2 = [b.text for b in buttons2]
        assert texts1 == texts2


class TestIsAuthReady:
    """Testes para is_auth_ready."""

    def test_all_true(self):
        """Tudo pronto retorna True."""
        assert is_auth_ready(True, True, True) is True

    def test_no_app(self):
        """Sem app retorna False."""
        assert is_auth_ready(False, True, True) is False

    def test_no_auth(self):
        """Sem auth retorna False."""
        assert is_auth_ready(True, False, True) is False

    def test_not_authenticated(self):
        """Não autenticado retorna False."""
        assert is_auth_ready(True, True, False) is False

    def test_all_false(self):
        """Nada pronto retorna False."""
        assert is_auth_ready(False, False, False) is False

    def test_only_app(self):
        """Apenas app sem auth retorna False."""
        assert is_auth_ready(True, False, False) is False


class TestExtractEmailPrefix:
    """Testes para extract_email_prefix."""

    def test_standard_email(self):
        """Email padrão retorna prefixo."""
        assert extract_email_prefix("usuario@example.com") == "usuario"

    def test_complex_prefix(self):
        """Prefixo com pontos/hífens é preservado."""
        assert extract_email_prefix("joao.silva@empresa.com.br") == "joao.silva"
        assert extract_email_prefix("user-name@test.com") == "user-name"

    def test_no_at_sign(self):
        """Sem @ retorna string completa."""
        assert extract_email_prefix("sem-arroba") == "sem-arroba"

    def test_empty_string(self):
        """String vazia retorna vazio."""
        assert extract_email_prefix("") == ""

    def test_none(self):
        """None retorna vazio."""
        assert extract_email_prefix(None) == ""

    def test_whitespace_trimming(self):
        """Espaços são removidos."""
        assert extract_email_prefix("  user@test.com  ") == "user"
        assert extract_email_prefix("user  @  test.com") == "user"

    def test_multiple_at_signs(self):
        """Múltiplos @ usa primeiro."""
        assert extract_email_prefix("user@domain@extra.com") == "user"

    def test_at_at_start(self):
        """@ no início retorna vazio."""
        assert extract_email_prefix("@domain.com") == ""

    def test_at_at_end(self):
        """@ no final retorna prefixo completo."""
        result = extract_email_prefix("username@")
        assert result == "username"


class TestFormatAuthorFallback:
    """Testes para format_author_fallback."""

    def test_with_display_name(self):
        """Display name tem prioridade."""
        assert format_author_fallback("user@test.com", "João Silva") == "João Silva"

    def test_empty_display_name_uses_prefix(self):
        """Display name vazio usa prefixo do email."""
        assert format_author_fallback("user@test.com", "") == "user"

    def test_none_display_name_uses_prefix(self):
        """Display name None usa prefixo do email."""
        assert format_author_fallback("user@test.com", None) == "user"

    def test_no_display_name_param(self):
        """Sem display_name usa prefixo do email."""
        assert format_author_fallback("user@test.com") == "user"

    def test_empty_email_empty_name(self):
        """Email e nome vazios retorna 'Anônimo'."""
        assert format_author_fallback("", "") == "Anônimo"

    def test_none_email_none_name(self):
        """Email e nome None retorna 'Anônimo'."""
        assert format_author_fallback(None, None) == "Anônimo"

    def test_email_without_at(self):
        """Email sem @ é usado como está."""
        assert format_author_fallback("username", "") == "username"

    def test_whitespace_display_name(self):
        """Display name só com espaços usa email."""
        assert format_author_fallback("user@test.com", "   ") == "user"

    def test_whitespace_trimming_in_display_name(self):
        """Espaços em display name são removidos."""
        assert format_author_fallback("user@test.com", "  João Silva  ") == "João Silva"

    def test_complex_email_prefix(self):
        """Prefixo complexo é extraído corretamente."""
        assert format_author_fallback("joao.silva@empresa.com.br", "") == "joao.silva"

    def test_priority_hierarchy(self):
        """Hierarquia de prioridade está correta."""
        # 1. display_name
        assert format_author_fallback("user@test.com", "Nome") == "Nome"

        # 2. prefixo do email
        assert format_author_fallback("user@test.com", "") == "user"

        # 3. Anônimo (sem nada)
        assert format_author_fallback("", "") == "Anônimo"


class TestRound5Integration:
    """Testes de integração para helpers do Round 5."""

    def test_module_buttons_workflow(self):
        """Workflow completo de criação de módulos."""
        # Criar botões com cashflow habilitado
        buttons = build_module_buttons(has_cashflow=True)

        # Verificar que Clientes tem estilo info
        clientes = [b for b in buttons if b.text == "Clientes"][0]
        expected_style = calculate_module_button_style(bootstyle="info")
        assert clientes.bootstyle == expected_style

        # Verificar que Fluxo de Caixa tem estilo warning
        cashflow = [b for b in buttons if b.text == "Fluxo de Caixa"][0]
        expected_style = calculate_module_button_style(yellow=True)
        assert cashflow.bootstyle == expected_style

    def test_auth_and_ui_state_workflow(self):
        """Workflow de autenticação e estado de UI."""
        # Sem autenticação
        auth_ready = is_auth_ready(False, False, False)
        assert auth_ready is False

        # UI sem org_id
        ui_state = calculate_notes_ui_state(has_org_id=False)
        assert ui_state["button_enabled"] is False

        # Com autenticação
        auth_ready = is_auth_ready(True, True, True)
        assert auth_ready is True

        # UI com org_id
        ui_state = calculate_notes_ui_state(has_org_id=True)
        assert ui_state["button_enabled"] is True

    def test_author_formatting_chain(self):
        """Cadeia de formatação de autores."""
        # Com display_name
        formatted = format_author_fallback("user@test.com", "João Silva")
        assert formatted == "João Silva"

        # Sem display_name, extrair prefixo
        prefix = extract_email_prefix("user@test.com")
        formatted = format_author_fallback("user@test.com", None)
        assert formatted == prefix

        # Email completo sem @
        formatted = format_author_fallback("username", "")
        assert formatted == "username"

    def test_notes_rendering_workflow(self):
        """Workflow completo de renderização de notas."""
        # Normalizar notas
        raw_notes = [
            ("2025-01-01T10:00:00Z", "user1@test.com", "First note"),
            {"author_email": "user2@test.com", "body": "Second note"},
        ]
        normalized = [normalize_note_dict(n) for n in raw_notes]

        # Calcular hash para skip
        hash1 = calculate_notes_content_hash(normalized)
        hash2 = calculate_notes_content_hash(normalized)
        assert hash1 == hash2  # Sem mudança, pode skip

        # Formatar autores
        author1 = format_author_fallback(normalized[0]["author_email"])
        assert author1 == "user1"

        author2 = format_author_fallback(normalized[1]["author_email"])
        assert author2 == "user2"

    def test_cooldown_and_refresh_workflow(self):
        """Workflow de cooldown e refresh."""
        now = time.time()
        cooldown = 30

        # Primeiro refresh
        should_skip = should_skip_refresh_by_cooldown(0, cooldown)
        assert should_skip is False  # Permite

        # Logo após (dentro do cooldown)
        should_skip = should_skip_refresh_by_cooldown(now - 5, cooldown)
        assert should_skip is True  # Bloqueia

        # Forçar ignora cooldown
        should_skip = should_skip_refresh_by_cooldown(now - 5, cooldown, force=True)
        assert should_skip is False  # Permite mesmo recente


# ============================================================================
# ROUND 5 - FASE 02: FORMATAÇÃO E VALIDAÇÃO DE NOTAS
# ============================================================================


class TestFormatTimestamp:
    """Testes para format_timestamp."""

    def test_empty_string(self):
        """String vazia retorna '?'."""
        assert format_timestamp("") == "?"

    def test_none(self):
        """None retorna '?'."""
        assert format_timestamp(None) == "?"

    def test_invalid_format(self):
        """Formato inválido retorna string original."""
        assert format_timestamp("invalid") == "invalid"

    def test_valid_iso_format(self):
        """ISO válido é convertido (formato dd/mm/YYYY - HH:MM)."""
        result = format_timestamp("2025-01-15T14:30:00Z")
        # Verificar apenas estrutura (timezone pode variar)
        assert "/" in result
        assert "-" in result
        assert ":" in result

    def test_iso_without_z(self):
        """ISO sem Z é normalizado."""
        result = format_timestamp("2025-01-15T14:30:00+00:00")
        assert "/" in result


class TestFormatNoteLine:
    """Testes para format_note_line."""

    def test_complete_line(self):
        """Linha completa com todos os campos."""
        result = format_note_line("2025-01-15T14:30:00Z", "João Silva", "Reunião às 15h")
        assert "João Silva" in result
        assert "Reunião às 15h" in result
        assert "[" in result
        assert "]" in result
        assert ":" in result

    def test_empty_timestamp(self):
        """Timestamp vazio usa '?'."""
        result = format_note_line("", "Usuário", "Nota sem timestamp")
        assert "[?]" in result
        assert "Usuário" in result
        assert "Nota sem timestamp" in result

    def test_none_timestamp(self):
        """None timestamp usa '?'."""
        result = format_note_line(None, "Anônimo", "Teste")
        assert "[?]" in result

    def test_format_structure(self):
        """Verifica estrutura geral do formato."""
        result = format_note_line("2025-01-01T10:00:00Z", "User", "Text")
        # [timestamp] autor: texto
        assert result.count("[") == 1
        assert result.count("]") == 1
        assert result.count(":") >= 2  # timestamp + separador


class TestShouldShowNotesSection:
    """Testes para should_show_notes_section."""

    def test_zero_notes(self):
        """Zero notas ainda mostra seção."""
        assert should_show_notes_section(0) is True

    def test_one_note(self):
        """Uma nota mostra seção."""
        assert should_show_notes_section(1) is True

    def test_many_notes(self):
        """Muitas notas mostra seção."""
        assert should_show_notes_section(100) is True

    def test_always_true(self):
        """Seção sempre visível independente da contagem."""
        for count in [0, 1, 5, 10, 100]:
            assert should_show_notes_section(count) is True


class TestFormatNotesCount:
    """Testes para format_notes_count."""

    def test_zero_notes(self):
        """Zero notas usa plural."""
        assert format_notes_count(0) == "0 notas"

    def test_one_note(self):
        """Uma nota usa singular."""
        assert format_notes_count(1) == "1 nota"

    def test_two_notes(self):
        """Duas notas usa plural."""
        assert format_notes_count(2) == "2 notas"

    def test_many_notes(self):
        """Muitas notas usa plural."""
        assert format_notes_count(100) == "100 notas"

    def test_negative_edge_case(self):
        """Valores negativos (edge case)."""
        result = format_notes_count(-1)
        assert "nota" in result.lower()


class TestIsNotesListEmpty:
    """Testes para is_notes_list_empty."""

    def test_none_list(self):
        """None é considerado vazio."""
        assert is_notes_list_empty(None) is True

    def test_empty_list(self):
        """Lista vazia é considerada vazia."""
        assert is_notes_list_empty([]) is True

    def test_list_with_items(self):
        """Lista com itens não é vazia."""
        assert is_notes_list_empty([{"body": "test"}]) is False

    def test_list_with_multiple_items(self):
        """Lista com múltiplos itens não é vazia."""
        assert is_notes_list_empty([{"a": 1}, {"b": 2}]) is False


class TestShouldSkipRenderEmptyNotes:
    """Testes para should_skip_render_empty_notes."""

    def test_none_skips(self):
        """None deve pular render."""
        assert should_skip_render_empty_notes(None) is True

    def test_empty_list_skips(self):
        """Lista vazia deve pular render."""
        assert should_skip_render_empty_notes([]) is True

    def test_non_empty_renders(self):
        """Lista com itens não pula render."""
        assert should_skip_render_empty_notes([{"body": "test"}]) is False

    def test_defensive_behavior(self):
        """Comportamento defensivo evita 'branco' na UI."""
        # Vazio → skip (mantém conteúdo anterior)
        assert should_skip_render_empty_notes([]) is True
        # Com dados → render
        assert should_skip_render_empty_notes([{"note": "data"}]) is False


class TestCalculateRetryDelayMs:
    """Testes para calculate_retry_delay_ms."""

    def test_first_retry(self):
        """Primeiro retry usa delay base."""
        assert calculate_retry_delay_ms(0) == 60000

    def test_second_retry(self):
        """Segundo retry dobra o delay."""
        assert calculate_retry_delay_ms(1) == 120000

    def test_third_retry(self):
        """Terceiro retry quadruplica o delay."""
        assert calculate_retry_delay_ms(2) == 240000

    def test_max_delay_limit(self):
        """Delay não excede máximo configurado."""
        assert calculate_retry_delay_ms(10) == 300000  # max

    def test_custom_base_delay(self):
        """Delay base customizado."""
        assert calculate_retry_delay_ms(0, base_delay_ms=1000) == 1000

    def test_custom_max_delay(self):
        """Delay máximo customizado."""
        result = calculate_retry_delay_ms(0, base_delay_ms=1000, max_delay_ms=5000)
        assert result == 1000
        result = calculate_retry_delay_ms(10, base_delay_ms=1000, max_delay_ms=5000)
        assert result == 5000

    def test_exponential_backoff(self):
        """Verifica progressão exponencial."""
        # Usar valores menores para não atingir o max
        delays = [calculate_retry_delay_ms(i, base_delay_ms=1000, max_delay_ms=100000) for i in range(5)]
        # Cada delay deve ser 2x o anterior (antes do max)
        assert delays[1] == delays[0] * 2
        assert delays[2] == delays[0] * 4
        assert delays[3] == delays[0] * 8
        assert delays[4] == delays[0] * 16


class TestRound5Fase02Integration:
    """Testes de integração para workflows de Round 5 Fase 02."""

    def test_notes_formatting_workflow(self):
        """Workflow completo de formatação de notas."""
        # Formatar timestamp
        ts = format_timestamp("2025-01-15T10:00:00Z")
        assert "/" in ts

        # Formatar linha
        line = format_note_line("2025-01-15T10:00:00Z", "User", "Message")
        assert "User" in line
        assert "Message" in line

        # Contar notas
        count_text = format_notes_count(5)
        assert count_text == "5 notas"

    def test_empty_notes_handling_workflow(self):
        """Workflow de tratamento de notas vazias."""
        # Verificar vazio
        assert is_notes_list_empty([]) is True

        # Deve pular render
        assert should_skip_render_empty_notes([]) is True

        # Seção ainda deve ser mostrada
        assert should_show_notes_section(0) is True

    def test_retry_backoff_workflow(self):
        """Workflow de retry com backoff."""
        # Calcular delays progressivos
        delay1 = calculate_retry_delay_ms(0)
        delay2 = calculate_retry_delay_ms(1)
        delay3 = calculate_retry_delay_ms(2)

        # Verificar progressão
        assert delay2 > delay1
        assert delay3 > delay2

        # Máximo respeitado
        delay_max = calculate_retry_delay_ms(100)
        assert delay_max == 300000

    def test_complete_notes_rendering_pipeline(self):
        """Pipeline completo de renderização de notas."""
        # 1. Verificar se lista não está vazia
        notes = [{"author_email": "user@test.com", "body": "Test", "created_at": "2025-01-01T10:00:00Z"}]
        assert not should_skip_render_empty_notes(notes)

        # 2. Formatar timestamp
        ts = format_timestamp(notes[0]["created_at"])
        assert ts != "?"

        # 3. Formatar autor
        author = format_author_fallback(notes[0]["author_email"])
        assert author == "user"

        # 4. Formatar linha completa
        line = format_note_line(notes[0]["created_at"], author, notes[0]["body"])
        assert "Test" in line

        # 5. Contar notas
        count = format_notes_count(len(notes))
        assert count == "1 nota"

    def test_edge_cases_combined(self):
        """Combinação de edge cases."""
        # Timestamp inválido
        assert format_timestamp("invalid") == "invalid"

        # Lista None
        assert should_skip_render_empty_notes(None) is True

        # Contagem zero
        assert format_notes_count(0) == "0 notas"

        # Retry máximo
        assert calculate_retry_delay_ms(999) == 300000
