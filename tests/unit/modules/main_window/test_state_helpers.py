"""Testes unitários para state_helpers do módulo main_window.

MICROFASE 04 - Round 4: Extração de lógica de estado/tema/navegação
Cobertura: compute_theme_config, build_app_title, resolve_initial_section,
           compute_connectivity_state, format_status_text, etc.
"""

from __future__ import annotations

from src.modules.main_window.views.state_helpers import (
    ConnectivityState,
    MainWindowSection,
    build_app_title,
    build_section_navigation_map,
    compute_connectivity_state,
    compute_theme_config,
    format_clients_count_display,
    format_status_text,
    format_version_string,
    parse_clients_count_display,
    resolve_initial_section,
    should_show_offline_alert,
    validate_theme_name,
)


# ============================================================================
# TEMA / ESTILO
# ============================================================================


class TestComputeThemeConfig:
    """Testes para compute_theme_config."""

    def test_first_theme_application(self):
        """Deve retornar config para primeira aplicação de tema."""
        config = compute_theme_config("darkly", None)

        assert config is not None
        assert config.name == "darkly"
        assert config.should_persist is True
        assert config.is_change is False  # Não havia tema anterior

    def test_theme_change(self):
        """Deve retornar config para mudança de tema."""
        config = compute_theme_config("darkly", "flatly")

        assert config is not None
        assert config.name == "darkly"
        assert config.should_persist is True
        assert config.is_change is True  # Mudança de tema

    def test_same_theme_returns_none(self):
        """Deve retornar None quando tema solicitado é igual ao atual."""
        config = compute_theme_config("flatly", "flatly")
        assert config is None

    def test_empty_theme_returns_none(self):
        """Deve retornar None quando tema solicitado é vazio."""
        config = compute_theme_config("", "flatly")
        assert config is None

        config = compute_theme_config(None, "flatly")
        assert config is None

    def test_no_persistence_mode(self):
        """Deve desabilitar persistência quando allow_persistence=False."""
        config = compute_theme_config("darkly", "flatly", allow_persistence=False)

        assert config is not None
        assert config.should_persist is False

    def test_whitespace_normalization(self):
        """Deve normalizar espaços no nome do tema."""
        config = compute_theme_config("  darkly  ", "flatly")

        assert config is not None
        assert config.name == "darkly"


class TestValidateThemeName:
    """Testes para validate_theme_name."""

    def test_valid_theme_exact_match(self):
        """Deve retornar tema quando há match exato."""
        result = validate_theme_name("darkly", ["flatly", "darkly", "superhero"])
        assert result == "darkly"

    def test_valid_theme_case_insensitive(self):
        """Deve fazer match case-insensitive."""
        result = validate_theme_name("DARKLY", ["flatly", "darkly"])
        assert result == "darkly"

    def test_invalid_theme_returns_fallback(self):
        """Deve retornar fallback para tema inválido."""
        result = validate_theme_name("invalid", ["flatly", "darkly"])
        assert result == "flatly"

    def test_empty_theme_returns_fallback(self):
        """Deve retornar fallback para tema vazio."""
        result = validate_theme_name("", ["flatly"])
        assert result == "flatly"

    def test_custom_fallback(self):
        """Deve usar fallback customizado."""
        result = validate_theme_name("invalid", ["flatly", "superhero"], fallback="superhero")
        assert result == "superhero"

    def test_whitespace_normalization(self):
        """Deve normalizar espaços."""
        result = validate_theme_name("  darkly  ", ["flatly", "darkly"])
        assert result == "darkly"


# ============================================================================
# TÍTULO DA JANELA
# ============================================================================


class TestBuildAppTitle:
    """Testes para build_app_title."""

    def test_basic_title(self):
        """Deve construir título básico com versão."""
        title = build_app_title("RC Gestor", "v1.3.28")
        assert title == "RC Gestor - v1.3.28"

    def test_title_with_profile(self):
        """Deve incluir nome do perfil quando fornecido."""
        title = build_app_title("RC Gestor", "v1.3.28", profile_name="Admin")
        assert title == "RC Gestor - v1.3.28 (Admin)"

    def test_title_with_empty_profile(self):
        """Deve ignorar perfil vazio."""
        title = build_app_title("RC Gestor", "v1.3.28", profile_name="")
        assert title == "RC Gestor - v1.3.28"

        title = build_app_title("RC Gestor", "v1.3.28", profile_name="   ")
        assert title == "RC Gestor - v1.3.28"

    def test_custom_separator(self):
        """Deve usar separador customizado."""
        title = build_app_title("RC Gestor", "v1.3.28", separator=" | ")
        assert title == "RC Gestor | v1.3.28"

    def test_profile_whitespace_trimming(self):
        """Deve remover espaços do nome do perfil."""
        title = build_app_title("RC Gestor", "v1.3.28", profile_name="  Admin  ")
        assert title == "RC Gestor - v1.3.28 (Admin)"


class TestFormatVersionString:
    """Testes para format_version_string."""

    def test_add_prefix(self):
        """Deve adicionar prefixo 'v' quando ausente."""
        result = format_version_string("1.3.28")
        assert result == "v1.3.28"

    def test_preserve_existing_prefix(self):
        """Deve preservar prefixo existente."""
        result = format_version_string("v1.3.28")
        assert result == "v1.3.28"

    def test_custom_prefix(self):
        """Deve usar prefixo customizado."""
        result = format_version_string("1.3.28", prefix="version ")
        assert result == "version 1.3.28"

    def test_empty_version(self):
        """Deve retornar apenas prefixo para versão vazia."""
        result = format_version_string("")
        assert result == "v"

    def test_case_insensitive_prefix_detection(self):
        """Deve detectar prefixo case-insensitive."""
        result = format_version_string("V1.3.28", prefix="v")
        assert result == "V1.3.28"


# ============================================================================
# NAVEGAÇÃO / SEÇÕES
# ============================================================================


class TestResolveInitialSection:
    """Testes para resolve_initial_section."""

    def test_with_session_returns_default(self):
        """Deve retornar seção padrão quando há sessão."""
        section = resolve_initial_section(has_session=True)
        assert section == MainWindowSection.HUB

    def test_without_session_returns_default(self):
        """Deve retornar seção padrão mesmo sem sessão (atualmente)."""
        section = resolve_initial_section(has_session=False)
        assert section == MainWindowSection.HUB

    def test_custom_default_section(self):
        """Deve usar seção padrão customizada."""
        section = resolve_initial_section(
            has_session=True,
            default_section=MainWindowSection.CLIENTES,
        )
        assert section == MainWindowSection.CLIENTES


class TestBuildSectionNavigationMap:
    """Testes para build_section_navigation_map."""

    def test_basic_map(self):
        """Deve construir mapa de navegação básico."""
        sections = [MainWindowSection.HUB, MainWindowSection.CLIENTES]
        nav_map = build_section_navigation_map(sections)

        assert nav_map["hub"] == MainWindowSection.HUB
        assert nav_map["clientes"] == MainWindowSection.CLIENTES

    def test_all_sections(self):
        """Deve mapear todas as seções."""
        sections = list(MainWindowSection)
        nav_map = build_section_navigation_map(sections)

        assert len(nav_map) == len(sections)
        assert "hub" in nav_map
        assert "clientes" in nav_map
        assert "senhas" in nav_map

    def test_empty_list(self):
        """Deve retornar mapa vazio para lista vazia."""
        nav_map = build_section_navigation_map([])
        assert nav_map == {}


# ============================================================================
# ESTADO DE CONECTIVIDADE
# ============================================================================


class TestComputeConnectivityState:
    """Testes para compute_connectivity_state."""

    def test_stays_online(self):
        """Deve manter estado online."""
        state = compute_connectivity_state(True, True, False)

        assert state.is_online is True
        assert state.offline_alerted is False

    def test_stays_offline(self):
        """Deve manter estado offline."""
        state = compute_connectivity_state(False, False, True)

        assert state.is_online is False
        assert state.offline_alerted is True

    def test_goes_offline(self):
        """Deve mudar para offline."""
        state = compute_connectivity_state(True, False, False)

        assert state.is_online is False
        assert state.offline_alerted is False

    def test_goes_online_resets_alert(self):
        """Deve resetar flag de alerta ao voltar online."""
        state = compute_connectivity_state(False, True, True)

        assert state.is_online is True
        assert state.offline_alerted is False


class TestShouldShowOfflineAlert:
    """Testes para should_show_offline_alert."""

    def test_transition_to_offline_first_time(self):
        """Deve mostrar alerta na primeira transição para offline."""
        should_alert = should_show_offline_alert(True, False, False)
        assert should_alert is True

    def test_transition_to_offline_already_alerted(self):
        """Não deve mostrar alerta se já foi alertado."""
        should_alert = should_show_offline_alert(True, False, True)
        assert should_alert is False

    def test_stays_offline(self):
        """Não deve mostrar alerta se já estava offline."""
        should_alert = should_show_offline_alert(False, False, False)
        assert should_alert is False

    def test_goes_online(self):
        """Não deve mostrar alerta ao voltar online."""
        should_alert = should_show_offline_alert(False, True, True)
        assert should_alert is False

    def test_stays_online(self):
        """Não deve mostrar alerta se continua online."""
        should_alert = should_show_offline_alert(True, True, False)
        assert should_alert is False


# ============================================================================
# STATUS DISPLAY
# ============================================================================


class TestFormatStatusText:
    """Testes para format_status_text."""

    def test_online_status(self):
        """Deve formatar status online sem sufixo."""
        text = format_status_text("Supabase", True)
        assert text == "Supabase"

    def test_offline_status(self):
        """Deve adicionar sufixo offline."""
        text = format_status_text("Supabase", False)
        assert text == "Supabase (offline)"

    def test_custom_offline_suffix(self):
        """Deve usar sufixo customizado."""
        text = format_status_text("DB", False, offline_suffix=" [sem conexão]")
        assert text == "DB [sem conexão]"

    def test_custom_online_suffix(self):
        """Deve usar sufixo online customizado."""
        text = format_status_text("DB", True, online_suffix=" [conectado]")
        assert text == "DB [conectado]"


class TestParseClientsCountDisplay:
    """Testes para parse_clients_count_display."""

    def test_parse_multiple_clients(self):
        """Deve extrair número de múltiplos clientes."""
        count = parse_clients_count_display("150 clientes")
        assert count == 150

    def test_parse_single_client(self):
        """Deve extrair número de 1 cliente."""
        count = parse_clients_count_display("1 cliente")
        assert count == 1

    def test_parse_zero_clients(self):
        """Deve extrair zero clientes."""
        count = parse_clients_count_display("0 clientes")
        assert count == 0

    def test_parse_invalid_text(self):
        """Deve retornar 0 para texto inválido."""
        count = parse_clients_count_display("invalid")
        assert count == 0

    def test_parse_empty_text(self):
        """Deve retornar 0 para texto vazio."""
        count = parse_clients_count_display("")
        assert count == 0

    def test_parse_with_extra_whitespace(self):
        """Deve lidar com espaços extras."""
        count = parse_clients_count_display("  150   clientes  ")
        assert count == 150


class TestFormatClientsCountDisplay:
    """Testes para format_clients_count_display."""

    def test_format_multiple_clients(self):
        """Deve formatar múltiplos clientes."""
        text = format_clients_count_display(150)
        assert text == "150 clientes"

    def test_format_single_client(self):
        """Deve formatar 1 cliente no singular."""
        text = format_clients_count_display(1)
        assert text == "1 cliente"

    def test_format_zero_clients(self):
        """Deve formatar zero clientes."""
        text = format_clients_count_display(0)
        assert text == "0 clientes"

    def test_format_two_clients(self):
        """Deve usar plural para 2 clientes."""
        text = format_clients_count_display(2)
        assert text == "2 clientes"


# ============================================================================
# TESTES DE INTEGRAÇÃO
# ============================================================================


class TestStateHelpersIntegration:
    """Testes de integração entre helpers."""

    def test_theme_workflow(self):
        """Simula workflow completo de mudança de tema."""
        # 1. Primeira aplicação de tema
        config = compute_theme_config("flatly", None)
        assert config is not None
        assert config.is_change is False

        # 2. Validar tema
        valid_theme = validate_theme_name(config.name, ["flatly", "darkly"])
        assert valid_theme == "flatly"

        # 3. Mudança de tema
        config2 = compute_theme_config("darkly", "flatly")
        assert config2 is not None
        assert config2.is_change is True

    def test_connectivity_workflow(self):
        """Simula workflow completo de mudança de conectividade."""
        # 1. Estado inicial online
        state = compute_connectivity_state(True, True, False)
        assert state.is_online is True

        # 2. Vai offline (primeira vez)
        should_alert = should_show_offline_alert(True, False, False)
        assert should_alert is True

        state = compute_connectivity_state(True, False, False)
        assert state.is_online is False

        # 3. Formatar status
        status_text = format_status_text("Supabase", state.is_online)
        assert status_text == "Supabase (offline)"

        # 4. Volta online
        state = compute_connectivity_state(False, True, True)
        assert state.is_online is True
        assert state.offline_alerted is False

    def test_title_and_version_workflow(self):
        """Simula construção completa de título."""
        # 1. Formatar versão
        version = format_version_string("1.3.28")
        assert version == "v1.3.28"

        # 2. Construir título sem perfil
        title = build_app_title("RC Gestor", version)
        assert title == "RC Gestor - v1.3.28"

        # 3. Construir título com perfil
        title_with_profile = build_app_title("RC Gestor", version, profile_name="Admin")
        assert title_with_profile == "RC Gestor - v1.3.28 (Admin)"

    def test_navigation_workflow(self):
        """Simula workflow completo de navegação."""
        # 1. Resolver seção inicial
        section = resolve_initial_section(has_session=True)
        assert section == MainWindowSection.HUB

        # 2. Construir mapa de navegação
        sections = [MainWindowSection.HUB, MainWindowSection.CLIENTES, MainWindowSection.SENHAS]
        nav_map = build_section_navigation_map(sections)

        # 3. Usar mapa para navegação
        assert nav_map["hub"] == MainWindowSection.HUB
        assert nav_map["clientes"] == MainWindowSection.CLIENTES

    def test_clients_count_roundtrip(self):
        """Testa ida e volta de formatação de contagem."""
        # Formatar
        formatted = format_clients_count_display(150)
        assert formatted == "150 clientes"

        # Parse
        parsed = parse_clients_count_display(formatted)
        assert parsed == 150

        # Roundtrip singular
        formatted_single = format_clients_count_display(1)
        parsed_single = parse_clients_count_display(formatted_single)
        assert parsed_single == 1


# ============================================================================
# TESTES DE EDGE CASES
# ============================================================================


class TestStateHelpersEdgeCases:
    """Testes de casos extremos."""

    def test_theme_config_with_none_values(self):
        """Deve lidar com valores None."""
        config = compute_theme_config(None, None)
        assert config is None

    def test_validate_theme_with_empty_list(self):
        """Deve retornar fallback para lista vazia."""
        result = validate_theme_name("darkly", [])
        assert result == "flatly"  # fallback padrão

    def test_build_title_with_special_characters(self):
        """Deve lidar com caracteres especiais."""
        title = build_app_title("RC Gestor™", "v1.3.28", profile_name="João Silva")
        assert "™" in title
        assert "João Silva" in title

    def test_connectivity_state_all_combinations(self):
        """Testa todas as combinações de estado de conectividade."""
        combinations = [
            (True, True, False),
            (True, True, True),
            (True, False, False),
            (True, False, True),
            (False, True, False),
            (False, True, True),
            (False, False, False),
            (False, False, True),
        ]

        for current, new, alerted in combinations:
            state = compute_connectivity_state(current, new, alerted)
            assert isinstance(state, ConnectivityState)
            assert isinstance(state.is_online, bool)
            assert isinstance(state.offline_alerted, bool)

    def test_format_status_with_empty_base_text(self):
        """Deve lidar com texto base vazio."""
        text = format_status_text("", True)
        assert text == ""

        text = format_status_text("", False)
        assert text == " (offline)"

    def test_parse_clients_count_with_non_numeric(self):
        """Deve retornar 0 para texto não numérico."""
        assert parse_clients_count_display("abc clientes") == 0
        assert parse_clients_count_display("- clientes") == 0
